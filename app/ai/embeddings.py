"""
Whisper model integration for generating audio embeddings.
"""
import os
import logging
from typing import List
import torch
from transformers import WhisperProcessor, WhisperModel
import librosa

logger = logging.getLogger(__name__)

# Load model and processor once at module level
MODEL_NAME = "openai/whisper-tiny"
processor = None
model = None

# Whisper tiny encoder output dimension
EMBEDDING_DIM = 384  # Whisper tiny encoder hidden size


def _load_model():
    """Load Whisper model and processor if not already loaded."""
    global processor, model
    if processor is None or model is None:
        logger.info(f"Loading Whisper model: {MODEL_NAME}")
        processor = WhisperProcessor.from_pretrained(MODEL_NAME)
        model = WhisperModel.from_pretrained(MODEL_NAME)
        model.eval()  # Set to evaluation mode
        logger.info("Whisper model loaded successfully")


def generate_embedding(audio_file_path: str) -> List[float]:
    """
    Generate embedding from audio file using Whisper Tiny encoder.

    Args:
        audio_file_path: Path to audio file (WAV, MP3, etc.)

    Returns:
        384-dimensional embedding vector from Whisper encoder

    Raises:
        Exception: If embedding generation fails
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    try:
        # Load model if needed
        _load_model()

        # Load audio file (Whisper expects 16kHz)
        logger.info(f"Loading audio file: {audio_file_path}")
        audio, sr = librosa.load(audio_file_path, sr=16000)

        # Process audio
        logger.info("Processing audio with Whisper processor")
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

        # Generate embeddings using encoder
        logger.info("Generating embeddings from Whisper encoder")
        with torch.no_grad():
            # Get encoder outputs (hidden states)
            encoder_outputs = model.encoder(
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

        logger.info(f"Successfully generated {len(embedding_list)}-dimensional embedding")
        return embedding_list

    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise Exception(f"Embedding generation failed: {str(e)}")


def generate_dummy_embedding() -> List[float]:
    """
    Generate a dummy embedding for testing.

    Returns:
        Random 384-dimensional vector matching Whisper embedding dimension
    """
    import random
    random.seed(42)
    return [random.random() for _ in range(EMBEDDING_DIM)]
