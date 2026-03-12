"""
Wearable Device Simulator
=========================

Simulates multiple wearable devices uploading audio files
to the Audio Data Pipeline backend.

Usage:
    python device_simulator/simulate_device.py

    # Custom options
    python device_simulator/simulate_device.py --base-url http://localhost:8000 --uploads 5
"""

import argparse
import io
import math
import struct
import sys
import time
import wave
from typing import List

import requests

# ── Configuration ────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = "/api/audio/upload"

DEVICE_IDS: List[str] = [
    "device_101",
    "device_202",
    "device_303",
]


# ── Synthetic Audio Generator ────────────────────────────────────────

def generate_test_wav(
    duration_sec: float = 2.0,
    frequency_hz: float = 440.0,
    sample_rate: int = 16000,
) -> bytes:
    """
    Generate a simple sine-wave WAV file in memory.

    This creates a valid audio file that Faster-Whisper can process,
    simulating real audio from a wearable device microphone.

    Args:
        duration_sec:  Length of audio in seconds.
        frequency_hz:  Tone frequency (Hz). 440 = A4 note.
        sample_rate:   Samples per second.

    Returns:
        WAV file contents as bytes.
    """
    num_samples: int = int(sample_rate * duration_sec)
    amplitude: int = 16000  # ~50% of int16 max

    # Generate sine wave samples
    samples: List[int] = []
    for i in range(num_samples):
        value = int(amplitude * math.sin(2.0 * math.pi * frequency_hz * i / sample_rate))
        samples.append(value)

    # Pack into WAV format
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)          # Mono
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))

    return buffer.getvalue()


# ── Upload Function ──────────────────────────────────────────────────

def upload_audio(
    base_url: str,
    device_id: str,
    audio_bytes: bytes,
    filename: str,
) -> dict | None:
    """
    Upload a single audio file to the backend API.

    Args:
        base_url:    Server base URL (e.g. http://localhost:8000).
        device_id:   Wearable device identifier.
        audio_bytes: Raw WAV file content.
        filename:    Name to assign to the uploaded file.

    Returns:
        Parsed JSON response or None on failure.
    """
    url: str = f"{base_url}{UPLOAD_ENDPOINT}"

    try:
        response = requests.post(
            url,
            data={"device_id": device_id},
            files={"file": (filename, audio_bytes, "audio/wav")},
            timeout=120,  # Transcription can take time on first load
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text}")
            return None

    except requests.ConnectionError:
        print(f"  ✗ Connection failed — is the server running at {base_url}?")
        return None
    except requests.Timeout:
        print(f"  ✗ Request timed out (model loading may take a while on first run)")
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return None


# ── Simulation Runner ────────────────────────────────────────────────

def run_simulation(base_url: str, uploads_per_device: int) -> None:
    """
    Simulate multiple devices each uploading several audio clips.

    Args:
        base_url:            Server URL.
        uploads_per_device:  How many audio files each device uploads.
    """
    # Frequencies to make each upload slightly different
    frequencies: List[float] = [261.63, 329.63, 392.00, 440.00, 523.25]

    total_uploads: int = len(DEVICE_IDS) * uploads_per_device
    success_count: int = 0
    fail_count: int = 0

    print("=" * 65)
    print("  🎧  Wearable Device Audio Simulator")
    print("=" * 65)
    print(f"  Server     : {base_url}")
    print(f"  Devices    : {', '.join(DEVICE_IDS)}")
    print(f"  Uploads    : {uploads_per_device} per device ({total_uploads} total)")
    print("=" * 65)
    print()

    # ── Check server health first ────────────────────────────────────
    try:
        health = requests.get(f"{base_url}/", timeout=5)
        if health.status_code == 200:
            print("✅ Server is reachable\n")
        else:
            print(f"⚠️  Server returned {health.status_code}, proceeding anyway…\n")
    except requests.ConnectionError:
        print(f"❌ Cannot connect to {base_url}")
        print("   Start the server first:  uvicorn app.main:app --reload")
        sys.exit(1)

    # ── Upload loop ──────────────────────────────────────────────────
    for device_id in DEVICE_IDS:
        print(f"📱 Device: {device_id}")
        print("-" * 45)

        for i in range(1, uploads_per_device + 1):
            freq = frequencies[(i - 1) % len(frequencies)]
            duration = 1.5 + (i * 0.5)  # Vary duration: 2s, 2.5s, 3s, …
            filename = f"{device_id}_recording_{i}.wav"

            print(f"  [{i}/{uploads_per_device}] Uploading {filename} "
                  f"({duration:.1f}s, {freq:.0f}Hz)…", end=" ")

            audio_data: bytes = generate_test_wav(
                duration_sec=duration,
                frequency_hz=freq,
            )

            start_time = time.time()
            result = upload_audio(base_url, device_id, audio_data, filename)
            elapsed = time.time() - start_time

            if result:
                success_count += 1
                transcription = result.get("transcription", "")
                # Truncate long transcriptions for display
                display_text = (transcription[:60] + "…") if len(transcription) > 60 else transcription
                print(f"✓ ({elapsed:.1f}s)")
                print(f"       ID: {result.get('id')}  |  Transcription: \"{display_text}\"")
            else:
                fail_count += 1

        print()

    # ── Summary ──────────────────────────────────────────────────────
    print("=" * 65)
    print(f"  Simulation Complete")
    print(f"  ✓ Successful : {success_count}/{total_uploads}")
    if fail_count:
        print(f"  ✗ Failed     : {fail_count}/{total_uploads}")
    print("=" * 65)
    print()
    print("Next steps:")
    print(f"  • Query device records : GET {base_url}/api/device/device_101/audio")
    print(f"  • Download dataset     : GET {base_url}/api/dataset/download")
    print(f"  • Swagger UI           : {base_url}/docs")


# ── Entry Point ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate wearable devices uploading audio to the pipeline."
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_BASE_URL,
        help=f"Backend server URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--uploads",
        type=int,
        default=3,
        help="Number of audio uploads per device (default: 3)",
    )

    args = parser.parse_args()
    run_simulation(base_url=args.base_url, uploads_per_device=args.uploads)


if __name__ == "__main__":
    main()
