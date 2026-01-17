"""
Audio embedding generation using Whisper + emotion2vec models.
"""
import os
import logging
from typing import List
import torch
from transformers import WhisperProcessor, WhisperModel
import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Model names
WHISPER_MODEL_NAME = "openai/whisper-tiny"
EMOTION2VEC_MODEL_NAME = "iic/emotion2vec_plus_seed"

# Global model instances
whisper_processor = None
whisper_model = None
emotion2vec_model = None

# Embedding dimensions
WHISPER_DIM = 384  # Whisper tiny encoder hidden size
EMOTION2VEC_DIM = 768  # emotion2vec hidden layer size
EMBEDDING_DIM = WHISPER_DIM + EMOTION2VEC_DIM  # 1152 total


def _load_whisper_model():
    """Load Whisper model and processor if not already loaded."""
    global whisper_processor, whisper_model
    if whisper_processor is None or whisper_model is None:
        logger.info(f"Loading Whisper model: {WHISPER_MODEL_NAME}")
        whisper_processor = WhisperProcessor.from_pretrained(WHISPER_MODEL_NAME)
        whisper_model = WhisperModel.from_pretrained(WHISPER_MODEL_NAME)
        whisper_model.eval()  # Set to evaluation mode
        logger.info("Whisper model loaded successfully")


def _load_emotion2vec_model():
    """Load emotion2vec model if not already loaded."""
    global emotion2vec_model
    if emotion2vec_model is None:
        logger.info(f"Loading emotion2vec model: {EMOTION2VEC_MODEL_NAME}")
        try:
            from funasr import AutoModel
            emotion2vec_model = AutoModel(
                model=EMOTION2VEC_MODEL_NAME,
                hub="hf"  # Use Hugging Face hub
            )
            logger.info("emotion2vec model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load emotion2vec model: {e}")
            raise


def _generate_whisper_embedding(audio_file_path: str) -> List[float]:
    """
    Generate embedding from audio file using Whisper Tiny encoder.

    Args:
        audio_file_path: Path to audio file

    Returns:
        384-dimensional embedding vector from Whisper encoder
    """
    # Load model if needed
    _load_whisper_model()

    # Load audio file (Whisper expects 16kHz)
    logger.info(f"Loading audio for Whisper: {audio_file_path}")
    audio, sr = librosa.load(audio_file_path, sr=16000)

    # Process audio
    inputs = whisper_processor(audio, sampling_rate=16000, return_tensors="pt")

    # Generate embeddings using encoder
    with torch.no_grad():
        # Get encoder outputs (hidden states)
        encoder_outputs = whisper_model.encoder(
            inputs.input_features,
            return_dict=True
        )

        # Use the mean of the last hidden state as the embedding
        # Shape: (batch_size, sequence_length, hidden_size)
        last_hidden_state = encoder_outputs.last_hidden_state

        # Average pool over the sequence dimension to get fixed-size embedding
        # Result shape: (batch_size, hidden_size) -> (384,)
        embedding = torch.mean(last_hidden_state, dim=1).squeeze()

        # Convert to list
        embedding_list = embedding.cpu().numpy().tolist()

    logger.info(f"Generated {len(embedding_list)}-dimensional Whisper embedding")
    return embedding_list


def _generate_emotion2vec_embedding(audio_file_path: str) -> List[float]:
    """
    Generate embedding from audio file using emotion2vec encoder.

    Args:
        audio_file_path: Path to audio file

    Returns:
        768-dimensional embedding vector from emotion2vec
    """
    # Load model if needed
    _load_emotion2vec_model()

    logger.info(f"Loading audio for emotion2vec: {audio_file_path}")

    # Generate embeddings with emotion2vec
    # Use utterance-level granularity for entire cry analysis
    result = emotion2vec_model.generate(
        audio_file_path,
        granularity="utterance",  # Utterance-level features (averaged)
        extract_embedding=True    # Extract embeddings
    )

    # Extract the embedding from the result
    # The result structure contains 'feats' with the embedding
    if isinstance(result, list) and len(result) > 0:
        result = result[0]

    if isinstance(result, dict) and 'feats' in result:
        embedding_array = result['feats']

        # Convert to numpy array if needed
        if isinstance(embedding_array, torch.Tensor):
            embedding_array = embedding_array.cpu().numpy()

        # Flatten if multi-dimensional
        embedding_array = np.array(embedding_array).flatten()

        # Convert to list
        embedding_list = embedding_array.tolist()

        logger.info(f"Generated {len(embedding_list)}-dimensional emotion2vec embedding")
        return embedding_list
    else:
        raise ValueError(f"Unexpected emotion2vec output format: {type(result)}")


def generate_embedding(audio_file_path: str) -> List[float]:
    """
    Generate combined embedding from audio file using Whisper + emotion2vec.

    Args:
        audio_file_path: Path to audio file (WAV, MP3, etc.)

    Returns:
        1152-dimensional embedding vector (384 from Whisper + 768 from emotion2vec)

    Raises:
        Exception: If embedding generation fails
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    try:
        # Generate embeddings from both models
        logger.info(f"Generating combined embeddings for: {audio_file_path}")

        whisper_embedding = _generate_whisper_embedding(audio_file_path)
        emotion2vec_embedding = _generate_emotion2vec_embedding(audio_file_path)

        # Concatenate embeddings
        combined_embedding = whisper_embedding + emotion2vec_embedding

        logger.info(f"Successfully generated {len(combined_embedding)}-dimensional combined embedding "
                   f"({len(whisper_embedding)} Whisper + {len(emotion2vec_embedding)} emotion2vec)")

        return combined_embedding

    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise Exception(f"Embedding generation failed: {str(e)}")


def generate_dummy_embedding() -> List[float]:
    """
    Generate a dummy embedding for testing.

    Returns:
        Random 1152-dimensional vector matching combined embedding dimension
    """
    import random
    random.seed(42)
    return [random.random() for _ in range(EMBEDDING_DIM)]
