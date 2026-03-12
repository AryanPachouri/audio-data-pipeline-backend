"""
Dataset download router.

GET /api/dataset/download

Generates a ZIP file containing:
    dataset/
        audio_1.wav
        audio_2.wav
        ...
        metadata.csv

metadata.csv format:
    audio_file, transcription, device_id
"""

import csv
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.database import get_db
from app.models import AudioRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dataset", tags=["Dataset Generation"])


@router.get(
    "/download",
    summary="Download the full dataset as a ZIP",
    description=(
        "Generates a ZIP archive containing all uploaded audio files "
        "renamed sequentially (audio_1.wav, audio_2.wav, …) along with "
        "a metadata.csv mapping each file to its transcription and device ID. "
        "Designed for direct use in AI/ML training pipelines."
    ),
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "A ZIP file containing the dataset.",
        },
        404: {
            "description": "No audio records exist yet.",
        },
    },
)
def download_dataset(db: Session = Depends(get_db)) -> FileResponse:
    """Collect all audio files, generate metadata.csv, ZIP, and return."""

    # ── Fetch all records ────────────────────────────────────────────
    records: List[AudioRecord] = (
        db.query(AudioRecord)
        .order_by(AudioRecord.id.asc())
        .all()
    )

    if not records:
        logger.warning("Dataset download requested but no audio records exist.")
        raise HTTPException(
            status_code=404,
            detail="No audio records found. Upload some audio first.",
        )

    logger.info("Generating dataset ZIP with %d audio record(s)…", len(records))

    # ── Build dataset in a temp directory ────────────────────────────
    tmp_dir: str = tempfile.mkdtemp()
    dataset_dir: Path = Path(tmp_dir) / "dataset"
    dataset_dir.mkdir()

    csv_rows: List[Dict[str, str]] = []
    copied_count: int = 0

    for idx, record in enumerate(records, start=1):
        # Determine file extension from original file
        original_ext: str = Path(record.file_name).suffix or ".wav"
        new_name: str = f"audio_{idx}{original_ext}"

        # Resolve the source audio file on disk
        source_path: Path = BASE_DIR / record.file_path
        dest_path: Path = dataset_dir / new_name

        if source_path.exists():
            shutil.copy2(str(source_path), str(dest_path))
            copied_count += 1
        else:
            logger.warning(
                "Source audio file missing (skipping copy): %s (record id=%d)",
                source_path,
                record.id,
            )

        # Always include the record in metadata.csv
        csv_rows.append({
            "audio_file": new_name,
            "transcription": record.transcription or "",
            "device_id": record.device_id,
        })

    # ── Write metadata.csv ───────────────────────────────────────────
    csv_path: Path = dataset_dir / "metadata.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["audio_file", "transcription", "device_id"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    logger.info(
        "metadata.csv written: %d rows, %d audio files copied",
        len(csv_rows),
        copied_count,
    )

    # ── Create ZIP archive ───────────────────────────────────────────
    zip_base: str = str(Path(tmp_dir) / "dataset")
    archive_path: str = shutil.make_archive(zip_base, "zip", tmp_dir, "dataset")

    logger.info("Dataset ZIP created: %s", archive_path)

    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename="dataset.zip",
    )
