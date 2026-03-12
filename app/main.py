"""
FastAPI application entry point.

Configures Swagger docs with rich tag metadata, mounts routers,
and initialises the database + storage directories on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import AUDIO_STORAGE_DIR, WHISPER_MODEL_SIZE
from app.database import Base, engine
from app.routers import audio, device, dataset

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


# ── OpenAPI Tag Metadata ─────────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Server health and status checks.",
    },
    {
        "name": "Audio Upload",
        "description": (
            "Upload audio files from wearable devices. "
            "Each upload is automatically saved to disk, transcribed using "
            "Faster-Whisper (with multilingual support for **Hindi** and **English**), "
            "and recorded in the SQLite database."
        ),
    },
    {
        "name": "Device Records",
        "description": (
            "Query audio records by wearable device ID. "
            "Results are paginated and returned newest-first."
        ),
    },
    {
        "name": "Dataset Generation",
        "description": (
            "Generate and download a structured dataset for AI/ML training. "
            "The dataset is packaged as a **ZIP file** containing sequentially "
            "named audio files (`audio_1.wav`, `audio_2.wav`, …) and a "
            "`metadata.csv` with columns: `audio_file`, `transcription`, `device_id`."
        ),
    },
]


# ── Lifespan (startup / shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: create tables and ensure storage directory exists."""
    logger.info("Creating database tables (if not exist)…")
    Base.metadata.create_all(bind=engine)

    logger.info("Ensuring audio storage directory: %s", AUDIO_STORAGE_DIR)
    AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("🚀  Audio Data Pipeline is ready.  (model: %s)", WHISPER_MODEL_SIZE)
    yield
    logger.info("Shutting down Audio Data Pipeline.")


# ── FastAPI App ──────────────────────────────────────────────────────

APP_TITLE = "Audio Data Pipeline for AI Wearable Devices"
APP_DESCRIPTION = """
## Overview

Backend system for wearable audio ingestion, local speech-to-text transcription
using **Faster-Whisper**, and dataset generation for AI training.

### Key Features

- 🎙️ **Audio Upload** — accept audio from multiple wearable devices
- 🗣️ **Local STT** — transcribe using Faster-Whisper (Hindi + English + auto-detect)
- 📊 **Device Records** — query recordings by device with pagination
- 📦 **Dataset Export** — download a ZIP with sequentially named audio files + `metadata.csv`
- 🔒 **Fully Offline** — no cloud APIs, everything runs locally

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | SQLite + SQLAlchemy |
| STT Model | Faster-Whisper (medium) |
| Storage | Local filesystem |
"""

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Aryan Pachouri",
        "url": "https://github.com/AryanPachouri/audio-data-pipeline-backend",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# ── Mount Routers ────────────────────────────────────────────────────
app.include_router(audio.router)
app.include_router(device.router)
app.include_router(dataset.router)


# ── Root Health Check ────────────────────────────────────────────────

@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Returns the current server status, service name, and API version.",
    response_description="Server health status",
    responses={
        200: {
            "description": "Server is healthy and running.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "Audio Data Pipeline for AI Wearable Devices",
                        "version": "1.0.0",
                    }
                }
            },
        }
    },
)
def health_check() -> dict:
    return {
        "status": "healthy",
        "service": APP_TITLE,
        "version": "1.0.0",
    }
