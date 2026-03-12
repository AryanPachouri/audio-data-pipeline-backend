# 🎧 Audio Data Pipeline for AI Wearable Devices

> A production-style backend system that ingests audio from wearable devices, transcribes it locally using **Faster-Whisper**, and generates structured datasets for AI/ML training — built with **FastAPI**, **SQLite**, and clean modular architecture.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Project Overview

Wearable AI devices (smart glasses, earbuds, health monitors) continuously capture audio data. This backend system provides the infrastructure to:

1. **Ingest** audio uploads from multiple wearable devices via REST API
2. **Transcribe** audio automatically using a local Speech-to-Text model (no cloud APIs)
3. **Organize** recordings by device with full metadata tracking
4. **Export** a structured, download-ready dataset for AI model training

The system is designed to run entirely offline — no external API calls, no cloud dependencies.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CLIENT / WEARABLE DEVICE                          │
│              (Simulated via API calls / Swagger UI)                   │
└──────────────────────┬───────────────────────────────────────────────┘
                       │  HTTP (multipart/form-data)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       FastAPI Application                            │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Audio Upload    │  │  Device Query    │  │  Dataset Download  │  │
│  │  POST /api/      │  │  GET /api/device │  │  GET /api/dataset  │  │
│  │  audio/upload    │  │  /{id}/audio     │  │  /download         │  │
│  └────────┬─────┬──┘  └────────┬─────────┘  └────────┬───────────┘  │
│           │     │              │                      │              │
│           ▼     ▼              ▼                      ▼              │
│  ┌────────────────┐   ┌──────────────┐      ┌────────────────────┐  │
│  │ Audio Storage   │   │  SQLite DB   │      │  Dataset Generator │  │
│  │ Service         │   │  (SQLAlchemy) │      │  (ZIP + CSV)       │  │
│  └────────┬───────┘   └──────────────┘      └────────────────────┘  │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────────┐                                        │
│  │ Transcription Service   │                                        │
│  │ (Faster-Whisper, local) │                                        │
│  └─────────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

| Step | Action | Detail |
|------|--------|--------|
| 1 | **Upload** | Client sends audio + `device_id` → file saved to `audio_storage/{device_id}/` |
| 2 | **Transcribe** | Faster-Whisper processes the audio locally → returns text + language + duration |
| 3 | **Store** | Record persisted in SQLite with file path, transcription, and metadata |
| 4 | **Query** | Device-wise records retrieved via REST API with pagination |
| 5 | **Export** | All records packaged as `dataset.zip` with audio files + `metadata.csv` |

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | FastAPI (Python) | Async-capable REST API with auto-generated Swagger docs |
| **Database** | SQLite + SQLAlchemy ORM | Lightweight relational storage with WAL mode |
| **Speech-to-Text** | Faster-Whisper | CTranslate2-optimized Whisper model, runs 100% locally |
| **File Storage** | Local Filesystem | Device-organized directory structure |
| **API Documentation** | Swagger UI (OpenAPI) | Interactive API explorer at `/docs` |

---

## 📁 Project Structure

```
task/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, Swagger config, lifespan startup
│   ├── config.py               # Centralized settings (paths, DB, model config)
│   ├── database.py             # SQLAlchemy engine, session factory, get_db
│   ├── models.py               # ORM model: AudioRecord
│   ├── schemas.py              # Pydantic request/response schemas
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── audio.py            # POST /api/audio/upload
│   │   ├── device.py           # GET  /api/device/{device_id}/audio
│   │   └── dataset.py          # GET  /api/dataset/download
│   │
│   └── services/
│       ├── __init__.py
│       ├── audio_storage.py    # File save & path management
│       └── transcription.py    # Faster-Whisper singleton wrapper
│
├── device_simulator/
│   └── simulate_device.py      # Multi-device upload simulator
│
├── audio_storage/               # Runtime: uploaded audio files (per device)
├── data/                        # Runtime: SQLite database
├── requirements.txt
└── README.md
```

---

## 🗄️ Database Schema

**Table: `audio_records`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-incrementing primary key |
| `device_id` | TEXT (indexed) | Wearable device identifier |
| `file_path` | TEXT | Relative path to stored audio file |
| `file_name` | TEXT | Original uploaded filename |
| `file_size` | INTEGER | File size in bytes |
| `duration` | REAL | Audio duration in seconds |
| `transcription` | TEXT | Faster-Whisper transcription output |
| `language` | TEXT | Detected language code (e.g., `en`) |
| `created_at` | DATETIME | Upload timestamp (UTC) |

---

## 🗣️ Speech-to-Text Integration (Faster-Whisper)

The system uses [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), a CTranslate2 re-implementation of OpenAI's Whisper model that runs **4x faster** with comparable accuracy.

### Key Design Decisions

- **Lazy Loading** — The model loads on the first transcription request, not at server startup, keeping cold starts fast
- **Singleton Pattern** — A single model instance is shared across all requests to avoid redundant memory usage
- **VAD Filtering** — Voice Activity Detection is enabled to skip silent segments and improve transcription quality
- **Configurable** — Model size, device, and compute type are controlled via environment variables

### Environment Variables

| Variable | Default | Options |
|----------|---------|---------|
| `WHISPER_MODEL_SIZE` | `base` | `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` |

> **Tip:** Use `tiny` for fast testing, `base` or `small` for a good balance, and `large-v3` for maximum accuracy.

---

## 📡 API Documentation

Interactive Swagger UI is available at **`http://localhost:8000/docs`** after starting the server.

### Endpoints

#### `POST /api/audio/upload`

Upload an audio file from a wearable device. The file is saved, transcribed, and recorded.

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `device_id` | string | form-data | Wearable device identifier |
| `file` | file | form-data | Audio file (.wav, .mp3, .flac, .ogg, .m4a, .webm) |

**Response** `200 OK`:
```json
{
  "id": 1,
  "device_id": "device_101",
  "file_name": "recording.wav",
  "file_size": 64044,
  "duration": 2.0,
  "transcription": "Hello, this is a test recording.",
  "language": "en",
  "created_at": "2026-03-12T18:15:00"
}
```

---

#### `GET /api/device/{device_id}/audio`

Retrieve all audio records for a specific device, with pagination.

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `device_id` | string | path | Device identifier |
| `skip` | int | query | Records to skip (default: 0) |
| `limit` | int | query | Max records to return (default: 50, max: 200) |

**Response** `200 OK`:
```json
{
  "device_id": "device_101",
  "total_records": 3,
  "records": [
    {
      "id": 3,
      "device_id": "device_101",
      "file_path": "audio_storage/device_101/20260312_181500_a1b2c3d4_recording.wav",
      "file_name": "recording.wav",
      "file_size": 64044,
      "duration": 2.0,
      "transcription": "Hello, this is a test recording.",
      "language": "en",
      "created_at": "2026-03-12T18:15:00"
    }
  ]
}
```

---

#### `GET /api/dataset/download`

Download the complete dataset as a ZIP archive for AI/ML training.

**Response** `200 OK` — `application/zip`:
```
dataset.zip
└── dataset/
    ├── audio_1.wav
    ├── audio_2.wav
    ├── audio_3.wav
    └── metadata.csv
```

**`metadata.csv` format:**
```csv
audio_file,transcription,device_id
audio_1.wav,"Hello this is a test recording.",device_101
audio_2.wav,"Another audio sample from the device.",device_202
audio_3.wav,"Third recording captured outdoors.",device_303
```

---

## 📦 Dataset Generation Workflow

When `GET /api/dataset/download` is called, the system:

```
1. Query all audio records from SQLite (ordered by ID)
                    │
                    ▼
2. Create a temporary  dataset/  directory
                    │
                    ▼
3. Copy each audio file as  audio_1.wav, audio_2.wav, …
                    │
                    ▼
4. Generate  metadata.csv  with columns:
   audio_file, transcription, device_id
                    │
                    ▼
5. Compress the entire folder into  dataset.zip
                    │
                    ▼
6. Return ZIP as a downloadable file response
```

The resulting dataset is ready for direct use in speech recognition training pipelines, fine-tuning, or data analysis.

---

## 🤖 Device Simulation

A built-in simulator generates synthetic audio and uploads it to the backend, mimicking real wearable devices.

```bash
# Default: 3 devices × 3 uploads = 9 total
python3 device_simulator/simulate_device.py

# Custom: 5 uploads per device
python3 device_simulator/simulate_device.py --uploads 5

# Custom server URL
python3 device_simulator/simulate_device.py --base-url http://192.168.1.10:8000
```

**Simulated devices:** `device_101`, `device_202`, `device_303`

The simulator generates valid WAV files (sine waves at varying frequencies and durations), so no external audio samples are needed.

---

## ⚡ Setup Instructions

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/audio-data-pipeline.git
cd audio-data-pipeline

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the Server

```bash
# Start the development server
uvicorn app.main:app --reload

# With custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will:
- Create the SQLite database automatically on first launch
- Create the `audio_storage/` directory if it doesn't exist
- Lazy-load the Whisper model on the first audio upload

**Access points:**
| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Health check |
| `http://localhost:8000/docs` | Swagger UI (interactive API docs) |
| `http://localhost:8000/redoc` | ReDoc (alternative docs) |

---

## 🧪 Example API Requests

### Upload Audio

```bash
curl -X POST "http://localhost:8000/api/audio/upload" \
  -F "device_id=device_101" \
  -F "file=@sample_audio.wav"
```

### Query Device Records

```bash
curl "http://localhost:8000/api/device/device_101/audio?skip=0&limit=10"
```

### Download Dataset ZIP

```bash
curl -OJ "http://localhost:8000/api/dataset/download"
```

### Run Device Simulator

```bash
# Start server first, then in a second terminal:
python3 device_simulator/simulate_device.py --uploads 3
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ using FastAPI, SQLite, and Faster-Whisper
</p>
