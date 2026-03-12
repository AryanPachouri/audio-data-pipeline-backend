"""
Transcription service using Faster-Whisper.

Supports multilingual audio (Hindi, English, auto-detect)
with confidence scoring. The model loads once and is reused
for all subsequent requests.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import (
    BASE_DIR,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger(__name__)


# ── Transcription Result ─────────────────────────────────────────────

@dataclass
class TranscriptionResult:
    """Structured result from the transcription service."""

    text: str
    detected_language: str
    language_confidence: float
    duration: float


# ── Service ──────────────────────────────────────────────────────────

class TranscriptionService:
    """
    Singleton wrapper around Faster-Whisper.

    Features:
        - Multilingual support (Hindi, English, auto-detect)
        - Language confidence scoring
        - One-time model loading (lazy, on first call)
        - VAD filtering for cleaner transcription
    """

    _instance: Optional["TranscriptionService"] = None
    _model = None

    def __new__(cls) -> "TranscriptionService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        """Load the Faster-Whisper model once. Subsequent calls are no-ops."""
        if self._model is not None:
            return

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

        logger.info(
            "Faster-Whisper model '%s' loaded successfully — multilingual ready.",
            WHISPER_MODEL_SIZE,
        )

    def transcribe(
        self,
        file_path: str,
        language: str = "auto",
    ) -> TranscriptionResult:
        """
        Transcribe an audio file with multilingual support.

        Args:
            file_path: Path to the audio file (absolute or relative to project root).
            language:  Language hint — "auto" (detect), "en" (English), "hi" (Hindi).

        Returns:
            TranscriptionResult with text, detected language, confidence, and duration.

        Raises:
            ValueError: If an unsupported language code is provided.
            FileNotFoundError: If the audio file does not exist.
            RuntimeError: If transcription fails.
        """
        # ── Validate language parameter ──────────────────────────────
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Allowed: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        # ── Resolve file path ────────────────────────────────────────
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = BASE_DIR / file_path

        if not abs_path.exists():
            raise FileNotFoundError(f"Audio file not found: {abs_path}")

        # ── Load model (once) ────────────────────────────────────────
        self._load_model()

        # ── Build transcription parameters ───────────────────────────
        whisper_lang: Optional[str] = SUPPORTED_LANGUAGES[language]

        transcribe_kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 500,
            },
        }

        if whisper_lang is not None:
            # Explicit language — skip auto-detection
            transcribe_kwargs["language"] = whisper_lang
            logger.info(
                "Transcribing (language=%s): %s", whisper_lang, abs_path.name
            )
        else:
            # Auto-detect — let Whisper identify the language
            logger.info("Transcribing (auto-detect): %s", abs_path.name)

        # ── Run transcription ────────────────────────────────────────
        segments, info = self._model.transcribe(str(abs_path), **transcribe_kwargs)

        # Collect segment texts
        transcription_parts: list[str] = []
        for segment in segments:
            transcription_parts.append(segment.text.strip())

        transcription_text: str = " ".join(transcription_parts)
        detected_language: str = info.language
        language_confidence: float = round(info.language_probability, 4)
        duration: float = info.duration

        logger.info(
            "Transcription complete: detected_lang=%s, confidence=%.2f%%, "
            "duration=%.2fs, chars=%d",
            detected_language,
            language_confidence * 100,
            duration,
            len(transcription_text),
        )

        return TranscriptionResult(
            text=transcription_text,
            detected_language=detected_language,
            language_confidence=language_confidence,
            duration=duration,
        )


# ── Module-level singleton ───────────────────────────────────────────
transcription_service = TranscriptionService()
