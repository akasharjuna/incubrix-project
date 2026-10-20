"""
Text-to-Speech service using gTTS (free, no API key).
Produces MP3 files and measures actual audio duration via ffprobe.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_audio_duration(path: str) -> float:
    """Use ffprobe to measure actual audio duration."""
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
        logger.warning("ffprobe duration failed: %s", exc)
        return 0.0


async def generate_tts(text: str, output_path: str, lang: str = "en") -> float:
    """
    Generate TTS audio for text. Returns actual duration in seconds.
    Uses gTTS (Google Text-to-Speech, free).
    """
    settings = get_settings()

    if settings.tts_provider == "mock":
        return await _generate_mock_tts(text, output_path)

    def _sync_gtts():
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            return True
        except Exception as exc:
            logger.error("gTTS failed: %s", exc)
            return False

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _sync_gtts)

    if not success:
        logger.warning("TTS failed, generating silence placeholder.")
        await _generate_silence(output_path, duration=3.0)

    duration = _get_audio_duration(output_path)
    if duration == 0.0:
        # Estimate from word count as fallback
        duration = max(1.0, len(text.split()) / 140 * 60)
    logger.info("TTS generated: %s (%.2fs)", output_path, duration)
    return duration


async def _generate_mock_tts(text: str, output_path: str) -> float:
    """Generate a short silence file as mock TTS."""
    word_count = len(text.split())
    duration = max(1.0, word_count / 140 * 60)
    await _generate_silence(output_path, duration=duration)
    return _get_audio_duration(output_path) or duration


async def _generate_silence(output_path: str, duration: float = 3.0):
    """Create a silent MP3 file using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=22050",
        "-t", str(duration),
        "-acodec", "libmp3lame", "-q:a", "4",
        output_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=30)
    except Exception as exc:
        logger.error("Silence generation failed: %s", exc)
