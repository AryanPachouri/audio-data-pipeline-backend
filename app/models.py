"""
SQLAlchemy ORM models.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime

from app.database import Base


class AudioRecord(Base):
    """Represents a single uploaded audio file and its transcription."""

    __tablename__ = "audio_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)       # Relative path under audio_storage/
    file_name = Column(String, nullable=False)        # Original uploaded filename
    file_size = Column(Integer, nullable=False)       # Size in bytes
    duration = Column(Float, nullable=True)           # Audio duration in seconds
    transcription = Column(Text, nullable=True)       # Faster-Whisper output
    language = Column(String, nullable=True)          # Detected language code
    language_confidence = Column(Float, nullable=True) # Detection confidence (0.0–1.0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<AudioRecord id={self.id} device={self.device_id} file={self.file_name}>"
