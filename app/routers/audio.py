"""
Audio upload router.

POST /api/audio/upload
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import ALLOWED_AUDIO_EXTENSIONS, MAX_FILE_SIZE_MB
from app.database import get_db
from app.models import AudioRecord
from app.schemas import AudioUploadResponse
from app.services.audio_storage import save_audio_file
from app.services.transcription import transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["Audio"])


@router.post(
    "/upload",
    response_model=AudioUploadResponse,
    summary="Upload audio from a wearable device",
    description=(
        "Accepts an audio file and a device ID. The file is saved to the local "
        "filesystem, automatically transcribed using Faster-Whisper, and a "
        "database record is created."
    ),
)
async def upload_audio(
    device_id: str = Form(..., description="Unique identifier of the wearable device"),
    file: UploadFile = File(..., description="Audio file to upload (.wav, .mp3, .flac, .ogg, .m4a, .webm)"),
    db: Session = Depends(get_db),
) -> AudioUploadResponse:
    """Upload an audio file, transcribe it, and store the record."""

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
    try:
        transcription, language, duration = transcription_service.transcribe(
            file_info["file_path"]
        )
        logger.info(
            "Transcription successful: device=%s, lang=%s, duration=%.2fs",
            device_id,
            language,
            duration or 0,
        )
    except Exception as e:
        logger.error("Transcription failed for device %s: %s", device_id, e, exc_info=True)
        transcription = f"[Transcription failed: {e}]"
        language = None
        duration = None

    # ── Persist database record ──────────────────────────────────────
    record = AudioRecord(
        device_id=device_id,
        file_path=file_info["file_path"],
        file_name=file_info["file_name"],
        file_size=file_info["file_size"],
        duration=duration,
        transcription=transcription,
        language=language,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("Audio record created: id=%d, device=%s", record.id, device_id)

    return record
