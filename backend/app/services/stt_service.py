"""
Speech-to-Text service using OpenAI Whisper (local, offline).
Falls back to mock transcript when Whisper is unavailable.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_AUDIO_DURATION = 600  # 10 minutes in seconds


def _get_audio_duration(path: str) -> float:
    """Measure audio duration with ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception as exc:
        logger.warning("ffprobe failed: %s", exc)
        return 0.0


def _validate_audio(path: str) -> tuple[float, str]:
    """
    Validate audio file. Returns (duration, error_message).
    Empty error_message means OK.
    """
    if not os.path.exists(path):
        return 0.0, "Audio file not found."
    if os.path.getsize(path) == 0:
        return 0.0, "Audio file is empty."

    duration = _get_audio_duration(path)
    if duration == 0.0:
        return 0.0, "Could not determine audio duration — file may be corrupt or unsupported."
    if duration > MAX_AUDIO_DURATION:
        return duration, f"Audio duration {duration:.1f}s exceeds maximum {MAX_AUDIO_DURATION}s (10 minutes)."

    return duration, ""


async def transcribe_audio(audio_path: str) -> Dict:
    """
    Transcribe audio file using Whisper.
    Returns dict with 'text', 'segments' (list of {text, start, end}), 'duration'.
    """
    duration, err = _validate_audio(audio_path)
    if err:
        raise ValueError(err)

    settings = get_settings()

    if settings.stt_provider == "mock":
        return _mock_transcript(duration)

    def _sync_whisper():
        try:
            import whisper
            model = whisper.load_model(settings.whisper_model)
            result = model.transcribe(audio_path, word_timestamps=False, verbose=False)
            segments = [
                {"text": seg["text"].strip(), "start": seg["start"], "end": seg["end"]}
                for seg in result.get("segments", [])
            ]
            return {
                "text": result.get("text", "").strip(),
                "segments": segments,
                "duration": duration,
            }
        except ImportError:
            logger.warning("Whisper not installed; using mock transcript.")
            return None
        except Exception as exc:
            logger.error("Whisper transcription failed: %s", exc)
            return None

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_whisper)

    if result is None:
        return _mock_transcript(duration)

    logger.info("Transcribed %s: %.2fs, %d segments", audio_path, duration, len(result["segments"]))
    return result


def _mock_transcript(duration: float) -> Dict:
    """Generate a placeholder transcript for mock mode."""
    return {
        "text": "This is a placeholder transcript generated in mock mode. Configure Whisper for real transcription.",
        "segments": [
            {
                "text": "This is a placeholder transcript generated in mock mode.",
                "start": 0.0,
                "end": min(duration / 2, 5.0),
            },
            {
                "text": "Configure Whisper for real transcription.",
                "start": min(duration / 2, 5.0),
                "end": duration,
            },
        ],
        "duration": duration,
    }


async def download_audio(url: str, dest_path: str, max_mb: int = 100) -> str:
    """
    Download audio from URL with size limits and SSRF protection.
    Returns the local path.
    """
    import ipaddress, socket
    from urllib.parse import urlparse
    import httpx

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    # SSRF protection
    try:
        host = parsed.hostname
        addr_infos = socket.getaddrinfo(host, None)
        for info in addr_infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"URL resolves to private/internal address: {ip}")
    except (socket.gaierror, OSError):
        raise ValueError(f"Cannot resolve host: {parsed.hostname}")

    max_bytes = max_mb * 1024 * 1024
    downloaded = 0

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            allowed = ("audio/", "video/", "application/octet-stream")
            if not any(content_type.startswith(a) for a in allowed):
                raise ValueError(f"Unsupported content type: {content_type}")

            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise ValueError(f"Download exceeded {max_mb} MB limit.")
                    f.write(chunk)

    return dest_path
