"""
Audio file storage service.

Handles saving uploaded audio files to the local filesystem
under audio_storage/{device_id}/{timestamp}_{uuid}.wav
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from fastapi import UploadFile

from app.config import AUDIO_STORAGE_DIR

logger = logging.getLogger(__name__)


async def save_audio_file(device_id: str, file: UploadFile) -> Dict[str, str | int]:
    """
    Save an uploaded audio file to disk.

    Args:
        device_id: Identifier of the wearable device.
        file:      FastAPI UploadFile object.

    Returns:
        dict with keys:
            file_path  (str) – relative path from project root
            file_name  (str) – original uploaded filename
            file_size  (int) – size in bytes

    Raises:
        IOError: If the file cannot be written to disk.
    """
    # Create device-specific directory
    device_dir: Path = AUDIO_STORAGE_DIR / device_id
    device_dir.mkdir(parents=True, exist_ok=True)

    # Build a unique filename:  {timestamp}_{uuid}_{original_name}
    timestamp: str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id: str = uuid.uuid4().hex[:8]
    original_name: str = file.filename or "audio.wav"
    safe_name: str = f"{timestamp}_{unique_id}_{original_name}"

    dest_path: Path = device_dir / safe_name

    # Stream content and write to disk
    content: bytes = await file.read()
    file_size: int = len(content)
    dest_path.write_bytes(content)

    # Relative path (from project root) for database storage
    relative_path: str = str(dest_path.relative_to(AUDIO_STORAGE_DIR.parent))

    logger.info(
        "Saved audio file: device=%s, file=%s, size=%d bytes, path=%s",
        device_id,
        original_name,
        file_size,
        relative_path,
    )

    return {
        "file_path": relative_path,
        "file_name": original_name,
        "file_size": file_size,
    }
