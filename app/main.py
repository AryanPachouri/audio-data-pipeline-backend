"""
FastAPI application entry point.

Configures Swagger docs, mounts routers, and initialises
the database + storage directories on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import AUDIO_STORAGE_DIR
from app.database import Base, engine
from app.routers import audio, device, dataset

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: create tables and ensure storage directory exists."""
    logger.info("Creating database tables (if not exist)…")
    Base.metadata.create_all(bind=engine)

    logger.info("Ensuring audio storage directory: %s", AUDIO_STORAGE_DIR)
    AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("🚀  Audio Data Pipeline is ready.")
    yield
    logger.info("Shutting down Audio Data Pipeline.")


# ── FastAPI App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Audio Data Pipeline for AI Wearable Devices",
    description=(
        "A backend system that simulates audio uploads from wearable devices, "
        "transcribes audio using Faster-Whisper (local STT model), maintains "
        "device-wise audio records in SQLite, and generates structured datasets "
        "for AI/ML training."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc
    openapi_url="/openapi.json",
)

# ── Mount Routers ────────────────────────────────────────────────────
app.include_router(audio.router)
app.include_router(device.router)
app.include_router(dataset.router)


# ── Root health check ───────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="Health check")
def health_check():
    return {
        "status": "healthy",
        "service": "Audio Data Pipeline for AI Wearable Devices",
        "version": "1.0.0",
    }
