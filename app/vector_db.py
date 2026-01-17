"""
Chroma vector database client for storing and querying cry embeddings.
"""
import chromadb
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Chroma configuration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "baby_cry_embeddings"

# Global client instance
_chroma_client = None
_collection = None


def get_chroma_client():
    """
    Get or create Chroma client with persistence.

    Returns:
        Chroma client instance
    """
    global _chroma_client

    if _chroma_client is None:
        try:
            _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            logger.info(f"Initialized Chroma client with persistence at {CHROMA_PERSIST_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma client: {e}")
            raise

    return _chroma_client


def get_collection():
    """
    Get or create the cry embeddings collection.

    Returns:
        Chroma collection
    """
    global _collection

    if _collection is None:
        client = get_chroma_client()
        try:
            # Try to get existing collection
            _collection = client.get_collection(name=COLLECTION_NAME)
            logger.info(f"Retrieved existing collection: {COLLECTION_NAME}")
        except Exception:
            # Create new collection if it doesn't exist
            _collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Baby cry audio embeddings"},
            )
            logger.info(f"Created new collection: {COLLECTION_NAME}")

    return _collection


def add_embedding(
    cry_id: int,
    user_id: int,
    embedding: List[float],
    reason: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> None:
    """
    Add a cry embedding to the vector database.

    Args:
        cry_id: Cry instance ID
        user_id: User ID (for filtering)
        embedding: 1152-dimensional embedding vector (384 Whisper + 768 emotion2vec)
        reason: Optional cry reason (free text)
        timestamp: Optional ISO 8601 timestamp
    """
    collection = get_collection()

    try:
        collection.add(
            ids=[f"cry_{cry_id}"],
            embeddings=[embedding],
            metadatas=[
                {
                    "cry_id": cry_id,
                    "user_id": user_id,
                    "has_reason": 1 if reason else 0,
                    "timestamp": timestamp if timestamp else "",
                }
            ],
        )
        logger.info(f"Added embedding for cry_id={cry_id}")
    except Exception as e:
        logger.error(f"Failed to add embedding for cry_id={cry_id}: {e}")
        raise


def search_similar(
    user_id: int,
    embedding: List[float],
    k: int = 5,
    filter_validated: bool = True,
) -> List[Dict]:
    """
    Search for similar cry embeddings using KNN.

    Args:
        user_id: User ID to filter by
        embedding: Query embedding vector
        k: Number of nearest neighbors to return
        filter_validated: Only return validated cries (has reason assigned)

    Returns:
        List of similar cry metadata with distances
    """
    collection = get_collection()

    try:
        # Build where clause
        if filter_validated:
            # Combine conditions using $and operator for chromadb 0.4.22
            where = {
                "$and": [
                    {"user_id": user_id},
                    {"has_reason": {"$gt": 0}}
                ]
            }
        else:
            where = {"user_id": user_id}

        # Query collection
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
        )

        # Format results
        similar_cries = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            for i, cry_id in enumerate(results["ids"][0]):
                similar_cries.append(
                    {
                        "cry_id": results["metadatas"][0][i]["cry_id"],
                        "distance": results["distances"][0][i],
                        "similarity": 1 - results["distances"][0][i],  # Convert distance to similarity
                        "metadata": results["metadatas"][0][i],
                    }
                )

        logger.info(f"Found {len(similar_cries)} similar cries for user_id={user_id}")
        return similar_cries

    except Exception as e:
        logger.error(f"Failed to search similar cries for user_id={user_id}: {e}")
        return []


def update_embedding_metadata(
    cry_id: int,
    has_reason: Optional[int] = None,
) -> None:
    """
    Update metadata for an existing embedding.

    Args:
        cry_id: Cry instance ID
        has_reason: Whether the cry has a reason assigned (0 or 1)
    """
    collection = get_collection()

    try:
        # Get existing metadata
        existing = collection.get(ids=[f"cry_{cry_id}"])

        if not existing or not existing["ids"]:
            logger.warning(f"No embedding found for cry_id={cry_id}")
            return

        # Update metadata
        metadata = existing["metadatas"][0]
        if has_reason is not None:
            metadata["has_reason"] = has_reason

        collection.update(
            ids=[f"cry_{cry_id}"],
            metadatas=[metadata],
        )
        logger.info(f"Updated embedding metadata for cry_id={cry_id}")

    except Exception as e:
        logger.error(f"Failed to update embedding metadata for cry_id={cry_id}: {e}")


def delete_embedding(cry_id: int) -> None:
    """
    Delete an embedding from the database.

    Args:
        cry_id: Cry instance ID
    """
    collection = get_collection()

    try:
        collection.delete(ids=[f"cry_{cry_id}"])
        logger.info(f"Deleted embedding for cry_id={cry_id}")
    except Exception as e:
        logger.error(f"Failed to delete embedding for cry_id={cry_id}: {e}")


def get_collection_stats() -> Dict:
    """
    Get statistics about the collection.

    Returns:
        Dictionary with collection statistics
    """
    collection = get_collection()

    try:
        count = collection.count()
        return {
            "total_embeddings": count,
            "collection_name": COLLECTION_NAME,
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {}
