"""
Application configuration settings.
"""

import os
from pathlib import Path

# ── Base Paths ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_STORAGE_DIR = BASE_DIR / "audio_storage"
DATABASE_DIR = BASE_DIR / "data"

# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'audio_pipeline.db'}"

# ── Faster-Whisper Model ─────────────────────────────────────────────
# Model sizes: "tiny", "base", "small", "medium", "large-v2", "large-v3"
# Use "medium" or "large-v3" for accurate multilingual (Hindi + English) support
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")          # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # "int8", "float16", "float32"

# ── Multilingual Support ─────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "auto": None,   # Auto-detect
    "en": "en",     # English
    "hi": "hi",     # Hindi
}

# ── Audio Upload Constraints ─────────────────────────────────────────
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}
MAX_FILE_SIZE_MB = 50
