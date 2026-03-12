"""
Audio upload router.

POST /api/audio/upload

Supports multilingual transcription with optional language parameter:
    - "auto" (default) → automatic language detection
    - "en"             → force English
    - "hi"             → force Hindi
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import ALLOWED_AUDIO_EXTENSIONS, MAX_FILE_SIZE_MB, SUPPORTED_LANGUAGES
from app.database import get_db
from app.models import AudioRecord
from app.schemas import AudioUploadResponse
from app.services.audio_storage import save_audio_file
from app.services.transcription import transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["Audio Upload"])


@router.post(
    "/upload",
    response_model=AudioUploadResponse,
    summary="Upload audio from a wearable device",
    description=(
        "Accepts an audio file and a device ID. The file is saved to the local "
        "filesystem, automatically transcribed using Faster-Whisper, and a "
        "database record is created.\n\n"
        "**Multilingual support:** Set `language` to `auto` (default) for "
        "automatic detection, `en` for English, or `hi` for Hindi."
    ),
)
async def upload_audio(
    device_id: str = Form(..., description="Unique identifier of the wearable device"),
    file: UploadFile = File(..., description="Audio file (.wav, .mp3, .flac, .ogg, .m4a, .webm)"),
    language: str = Form(
        "auto",
        description="Language hint: 'auto' (detect), 'en' (English), 'hi' (Hindi)",
    ),
    db: Session = Depends(get_db),
) -> AudioUploadResponse:
    """Upload an audio file, transcribe it, and store the record."""

    # ── Validate language parameter ──────────────────────────────────
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported language '{language}'. "
                f"Allowed: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            ),
        )

    # ── Validate file extension ──────────────────────────────────────
    ext: str = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        logger.warning("Rejected upload: unsupported format '%s' from device %s", ext, device_id)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported audio format '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
            ),
        )

    # ── Save file to disk ────────────────────────────────────────────
    try:
        file_info = await save_audio_file(device_id, file)
    except IOError as e:
        logger.error("Failed to save audio file: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save audio file.") from e

    # ── Check file size ──────────────────────────────────────────────
    if file_info["file_size"] > MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.warning(
            "Rejected upload: file too large (%d bytes) from device %s",
            file_info["file_size"],
            device_id,
        )
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB} MB.",
        )

    # ── Transcribe using Faster-Whisper ──────────────────────────────
    transcription_text: Optional[str] = None
    detected_lang: Optional[str] = None
    lang_confidence: Optional[float] = None
    duration: Optional[float] = None

    try:
        result = transcription_service.transcribe(
            file_path=file_info["file_path"],
            language=language,
        )
        transcription_text = result.text
        detected_lang = result.detected_language
        lang_confidence = result.language_confidence
        duration = result.duration

        logger.info(
            "Transcription successful: device=%s, detected_lang=%s, "
            "confidence=%.2f%%, duration=%.2fs",
            device_id,
            detected_lang,
            (lang_confidence or 0) * 100,
            duration or 0,
        )
    except Exception as e:
        logger.error("Transcription failed for device %s: %s", device_id, e, exc_info=True)
        transcription_text = f"[Transcription failed: {e}]"

    # ── Persist database record ──────────────────────────────────────
    record = AudioRecord(
        device_id=device_id,
        file_path=file_info["file_path"],
        file_name=file_info["file_name"],
        file_size=file_info["file_size"],
        duration=duration,
        transcription=transcription_text,
        language=detected_lang,
        language_confidence=lang_confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("Audio record created: id=%d, device=%s, lang=%s", record.id, device_id, detected_lang)

    return record
