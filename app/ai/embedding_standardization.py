"""
User-level embedding standardization for improved similarity matching.
"""
import json
import logging
import numpy as np
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models import CryEmbeddingRaw, UserEmbeddingStats, CryInstance
from app.vector_db import add_embedding, delete_embedding, get_collection

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1152
EPSILON = 1e-8


def store_raw_embedding(db: Session, cry_id: int, embedding: List[float]) -> None:
    """
    Store raw embedding for a cry instance.

    Args:
        db: Database session
        cry_id: Cry instance ID
        embedding: 1152-dimensional raw embedding
    """
    # Check if already exists
    existing = db.query(CryEmbeddingRaw).filter(CryEmbeddingRaw.cry_id == cry_id).first()

    if existing:
        # Update existing
        existing.embedding_json = json.dumps(embedding)
        logger.info(f"Updated raw embedding for cry_id={cry_id}")
    else:
        # Create new
        raw_embedding = CryEmbeddingRaw(
            cry_id=cry_id,
            embedding_json=json.dumps(embedding)
        )
        db.add(raw_embedding)
        logger.info(f"Stored raw embedding for cry_id={cry_id}")

    db.commit()


def get_or_initialize_user_stats(db: Session, user_id: int) -> Tuple[List[float], List[float]]:
    """
    Get user's embedding statistics (mean and std).
    Initialize with zeros and ones if not exists.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Tuple of (mean, std) as lists of 1152 floats
    """
    stats = db.query(UserEmbeddingStats).filter(UserEmbeddingStats.user_id == user_id).first()

    if not stats:
        # Initialize with mean=0, std=1 (no transformation)
        mean = [0.0] * EMBEDDING_DIM
        std = [1.0] * EMBEDDING_DIM

        stats = UserEmbeddingStats(
            user_id=user_id,
            mean_json=json.dumps(mean),
            std_json=json.dumps(std),
            cry_count=0
        )
        db.add(stats)
        db.commit()
        logger.info(f"Initialized embedding stats for user_id={user_id}")

        return mean, std

    # Parse existing stats
    mean = json.loads(stats.mean_json)
    std = json.loads(stats.std_json)

    return mean, std


def standardize_embedding(embedding: List[float], mean: List[float], std: List[float]) -> List[float]:
    """
    Standardize embedding using user-level statistics.

    Formula: (embedding - mean) / (std + epsilon)

    Args:
        embedding: Raw embedding
        mean: User's mean embedding
        std: User's std embedding

    Returns:
        Standardized embedding
    """
    embedding_array = np.array(embedding)
    mean_array = np.array(mean)
    std_array = np.array(std)

    # Standardize with epsilon to prevent division by zero
    standardized = (embedding_array - mean_array) / (std_array + EPSILON)

    return standardized.tolist()


def get_user_cry_count(db: Session, user_id: int) -> int:
    """
    Get total number of cries for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Total cry count
    """
    return db.query(CryInstance).filter(CryInstance.user_id == user_id).count()


def should_recompute_stats(db: Session, user_id: int) -> bool:
    """
    Check if user statistics should be recomputed.
    Recompute every 5 cries (5, 10, 15, ...).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        True if should recompute
    """
    cry_count = get_user_cry_count(db, user_id)

    # Recompute at 5, 10, 15, 20, ...
    return cry_count > 0 and cry_count % 5 == 0


def recompute_user_stats(db: Session, user_id: int) -> None:
    """
    Recompute user's embedding statistics from all raw embeddings.
    Then re-standardize and re-insert all embeddings to Chroma.

    Args:
        db: Database session
        user_id: User ID
    """
    logger.info(f"Recomputing embedding statistics for user_id={user_id}")

    # Get all cry IDs for this user
    cry_ids = [cry.id for cry in db.query(CryInstance).filter(CryInstance.user_id == user_id).all()]

    if len(cry_ids) == 0:
        logger.warning(f"No cries found for user_id={user_id}")
        return

    # Get all raw embeddings for this user
    raw_embeddings_records = (
        db.query(CryEmbeddingRaw)
        .filter(CryEmbeddingRaw.cry_id.in_(cry_ids))
        .all()
    )

    if len(raw_embeddings_records) == 0:
        logger.warning(f"No raw embeddings found for user_id={user_id}")
        return

    # Parse embeddings to numpy array
    embeddings_list = []
    for record in raw_embeddings_records:
        embedding = json.loads(record.embedding_json)
        embeddings_list.append(embedding)

    embeddings_array = np.array(embeddings_list)  # Shape: (n_cries, 1152)

    # Compute mean and std across all cries
    mean = np.mean(embeddings_array, axis=0)  # Shape: (1152,)
    std = np.std(embeddings_array, axis=0)    # Shape: (1152,)

    # Update user stats
    stats = db.query(UserEmbeddingStats).filter(UserEmbeddingStats.user_id == user_id).first()

    if stats:
        stats.mean_json = json.dumps(mean.tolist())
        stats.std_json = json.dumps(std.tolist())
        stats.cry_count = len(cry_ids)
        logger.info(f"Updated embedding stats for user_id={user_id} with {len(cry_ids)} cries")
    else:
        logger.error(f"No stats record found for user_id={user_id} (should have been initialized)")
        return

    db.commit()

    # Re-standardize and re-insert all embeddings to Chroma
    logger.info(f"Re-standardizing and re-inserting {len(raw_embeddings_records)} embeddings to Chroma")

    for record in raw_embeddings_records:
        cry_id = record.cry_id

        # Get cry instance for metadata
        cry = db.query(CryInstance).filter(CryInstance.id == cry_id).first()
        if not cry:
            logger.warning(f"Cry instance not found for cry_id={cry_id}")
            continue

        # Parse raw embedding
        raw_embedding = json.loads(record.embedding_json)

        # Standardize
        standardized_embedding = standardize_embedding(raw_embedding, mean.tolist(), std.tolist())

        # Delete old embedding from Chroma (if exists)
        try:
            delete_embedding(cry_id)
        except Exception as e:
            logger.warning(f"Failed to delete old embedding for cry_id={cry_id}: {e}")

        # Add new standardized embedding to Chroma
        try:
            add_embedding(
                cry_id=cry_id,
                user_id=user_id,
                embedding=standardized_embedding,
                reason=cry.reason,
                timestamp=cry.recorded_at.isoformat()
            )
            logger.info(f"Re-inserted standardized embedding for cry_id={cry_id}")
        except Exception as e:
            logger.error(f"Failed to add standardized embedding for cry_id={cry_id}: {e}")

    logger.info(f"Completed re-standardization for user_id={user_id}")


def process_and_store_embedding(
    db: Session,
    cry_id: int,
    user_id: int,
    raw_embedding: List[float],
    reason: str = None,
    timestamp: str = None
) -> None:
    """
    Complete workflow for storing and standardizing embeddings.

    1. Store raw embedding in database
    2. Get user statistics (or initialize)
    3. Standardize embedding
    4. Add to Chroma
    5. Check if should recompute statistics
    6. If yes, recompute and re-standardize all

    Args:
        db: Database session
        cry_id: Cry instance ID
        user_id: User ID
        raw_embedding: Raw 1152-dimensional embedding
        reason: Optional cry reason
        timestamp: Optional timestamp
    """
    # Step 1: Store raw embedding
    store_raw_embedding(db, cry_id, raw_embedding)

    # Step 2: Get user statistics
    mean, std = get_or_initialize_user_stats(db, user_id)

    # Step 3: Standardize embedding
    standardized_embedding = standardize_embedding(raw_embedding, mean, std)

    # Step 4: Add to Chroma
    logger.info(f"Adding standardized embedding to Chroma for cry_id={cry_id}")
    try:
        add_embedding(
            cry_id=cry_id,
            user_id=user_id,
            embedding=standardized_embedding,
            reason=reason,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"Failed to add embedding to Chroma: {e}")
        raise

    # Step 5: Check if should recompute
    if should_recompute_stats(db, user_id):
        logger.info(f"Triggering statistics recomputation for user_id={user_id}")
        recompute_user_stats(db, user_id)
