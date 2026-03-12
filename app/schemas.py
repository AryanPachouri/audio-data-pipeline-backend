"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Single Audio Record ──────────────────────────────────────────────

class AudioRecordSchema(BaseModel):
    """Schema representing a single audio record."""

    id: int
    device_id: str
    file_path: str
    file_name: str
    file_size: int
    duration: Optional[float] = None
    transcription: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Upload Response ──────────────────────────────────────────────────

class AudioUploadResponse(BaseModel):
    """Response returned after a successful audio upload."""

    id: int
    device_id: str
    file_name: str
    file_size: int
    duration: Optional[float] = None
    transcription: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Device Audio List Response ───────────────────────────────────────

class DeviceAudioResponse(BaseModel):
    """Response containing all audio records for a specific device."""

    device_id: str
    total_records: int
    records: List[AudioRecordSchema]
