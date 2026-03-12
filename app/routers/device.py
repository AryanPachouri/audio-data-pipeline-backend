"""
Device audio query router.

GET /api/device/{device_id}/audio
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioRecord
from app.schemas import DeviceAudioResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device", tags=["Device"])


@router.get(
    "/{device_id}/audio",
    response_model=DeviceAudioResponse,
    summary="Get all audio records for a device",
    description=(
        "Returns a paginated list of all audio records uploaded by "
        "the specified wearable device, ordered newest-first."
    ),
)
def get_device_audio(
    device_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> DeviceAudioResponse:
    """Retrieve all audio records for a given device ID."""

    logger.info("Querying audio records: device=%s, skip=%d, limit=%d", device_id, skip, limit)

    # Total count for this device
    total: int = (
        db.query(AudioRecord)
        .filter(AudioRecord.device_id == device_id)
        .count()
    )

    # Paginated records, newest first
    records: List[AudioRecord] = (
        db.query(AudioRecord)
        .filter(AudioRecord.device_id == device_id)
        .order_by(AudioRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    logger.info("Found %d total records for device %s (returning %d)", total, device_id, len(records))

    return DeviceAudioResponse(
        device_id=device_id,
        total_records=total,
        records=records,
    )
