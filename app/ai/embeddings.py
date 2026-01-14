"""
Hugging Face MERT model integration for generating audio embeddings.
"""
import requests
import os
import logging
from typing import List
import base64

logger = logging.getLogger(__name__)

# Hugging Face configuration
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MODEL_ID = "m-a-p/MERT-v1-95M"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

EMBEDDING_DIM = 768  # MERT-v1-95M output dimension


def generate_embedding(audio_file_path: str, max_retries: int = 3) -> List[float]:
    """
    Generate 768-dimensional embedding from audio file using MERT-v1-95M.

    Args:
        audio_file_path: Path to 24kHz WAV audio file
        max_retries: Maximum number of retry attempts

    Returns:
        768-dimensional embedding vector

    Raises:
        Exception: If embedding generation fails
    """
    if not HF_API_KEY:
        raise ValueError("HUGGINGFACE_API_KEY not set in environment variables")

    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
    }

    # Read audio file
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()

    # Try to generate embedding with retries
    for attempt in range(max_retries):
        try:
            logger.info(f"Generating embedding for {audio_file_path} (attempt {attempt + 1}/{max_retries})")

            response = requests.post(
                API_URL,
                headers=headers,
                data=audio_data,
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()

                # MERT model returns embeddings in different formats depending on the endpoint
                # Handle common response formats
                if isinstance(result, list):
                    # Direct embedding list
                    if len(result) == EMBEDDING_DIM:
                        logger.info(f"Successfully generated {EMBEDDING_DIM}-dimensional embedding")
                        return result
                    elif len(result) > 0 and isinstance(result[0], list):
                        # List of embeddings (take first one)
                        embedding = result[0]
                        if len(embedding) == EMBEDDING_DIM:
                            logger.info(f"Successfully generated {EMBEDDING_DIM}-dimensional embedding")
                            return embedding

                elif isinstance(result, dict):
                    # Check for common keys
                    if "embedding" in result:
                        embedding = result["embedding"]
                        if len(embedding) == EMBEDDING_DIM:
                            logger.info(f"Successfully generated {EMBEDDING_DIM}-dimensional embedding")
                            return embedding

                    elif "embeddings" in result:
                        embeddings = result["embeddings"]
                        if isinstance(embeddings, list) and len(embeddings) > 0:
                            embedding = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                            if len(embedding) == EMBEDDING_DIM:
                                logger.info(f"Successfully generated {EMBEDDING_DIM}-dimensional embedding")
                                return embedding

                # If we got here, response format was unexpected
                logger.error(f"Unexpected response format from Hugging Face API: {result}")
                raise ValueError(f"Unexpected embedding format. Got: {type(result)}")

            elif response.status_code == 503:
                # Model is loading, retry
                logger.warning(f"Model is loading... (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(10)  # Wait 10 seconds before retry
                    continue
                else:
                    raise Exception("Model is still loading after multiple retries")

            else:
                # Other error
                error_msg = response.text
                logger.error(f"Hugging Face API error ({response.status_code}): {error_msg}")
                raise Exception(f"Hugging Face API error: {error_msg}")

        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                continue
            else:
                raise Exception("Request timed out after multiple retries")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                raise

    raise Exception("Failed to generate embedding after all retries")


def generate_dummy_embedding() -> List[float]:
    """
    Generate a dummy embedding for testing (when Hugging Face is unavailable).

    Returns:
        Random 768-dimensional vector
    """
    import random
    random.seed(42)
    return [random.random() for _ in range(EMBEDDING_DIM)]
