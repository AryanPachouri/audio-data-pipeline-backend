"""
Transcription service using Faster-Whisper.

Lazily loads the model on first use to avoid slow startup
when the endpoint isn't immediately needed.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from app.config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Singleton-style wrapper around the Faster-Whisper model."""

    _instance: Optional["TranscriptionService"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        """Lazy-load the Faster-Whisper model."""
        if self._model is None:
            logger.info(
                "Loading Faster-Whisper model: size=%s, device=%s, compute=%s",
                WHISPER_MODEL_SIZE,
                WHISPER_DEVICE,
                WHISPER_COMPUTE_TYPE,
            )
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            logger.info("Faster-Whisper model loaded successfully.")

    def transcribe(self, file_path: str) -> Tuple[str, str, float]:
        """
        Transcribe an audio file.

        Args:
            file_path: Absolute or relative path to the audio file.

        Returns:
            Tuple of (transcription_text, detected_language, duration_seconds)
        """
        self._load_model()

        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            # Resolve relative to project root
            from app.config import BASE_DIR
            abs_path = BASE_DIR / file_path

        logger.info("Transcribing: %s", abs_path)

        segments, info = self._model.transcribe(
            str(abs_path),
            beam_size=5,
            vad_filter=True,
        )

        # Collect all segment texts
        transcription_parts = []
        for segment in segments:
            transcription_parts.append(segment.text.strip())

        transcription_text = " ".join(transcription_parts)
        detected_language = info.language
        duration = info.duration

        logger.info(
            "Transcription complete: lang=%s, duration=%.2fs, chars=%d",
            detected_language,
            duration,
            len(transcription_text),
        )

        return transcription_text, detected_language, duration


# Module-level singleton
transcription_service = TranscriptionService()
