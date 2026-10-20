"""
Video rendering engine using FFmpeg.
Downloads clips, concatenates them with narration audio, burns captions,
and produces H.264/AAC MP4 output for all requested aspect ratios.
Verifies output with ffprobe.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import AspectRatio, Job, SceneMatch
from app.rendering.caption_generator import generate_ass_subtitle_filter

logger = get_logger(__name__)


def _ffprobe_info(path: str) -> dict:
    """Run ffprobe and return stream/format info."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except Exception as exc:
        logger.warning("ffprobe failed on %s: %s", path, exc)
        return {}


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def _download_clip(url: str, dest: str, max_mb: int = 200) -> bool:
    """Download a clip from URL. Returns True on success."""
    max_bytes = max_mb * 1024 * 1024
    downloaded = 0
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise ValueError(f"Clip download exceeded {max_mb}MB")
                        f.write(chunk)
        return True
    except Exception as exc:
        logger.error("Clip download failed for %s: %s", url, exc)
        return False


def _create_placeholder_clip(output_path: str, duration: float, width: int, height: int):
    """Create a black placeholder clip when no footage is available."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:r=30:d={duration}",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=60, check=False)


def _prepare_clip_segment(
    input_path: str, output_path: str, duration: float, width: int, height: int
) -> bool:
    """
    Trim, scale, and crop a clip to exactly the required dimensions and duration.
    Uses smart crop to preserve the center of the frame.
    """
    # Scale to fill target size then crop to exact dimensions
    vf_chain = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps=30"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf_chain,
        "-c:v", "libx264", "-preset", "fast",
        "-an",  # No audio in clip segments
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        if result.returncode != 0:
            logger.error("ffmpeg clip prep failed: %s", result.stderr.decode()[-500:])
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg clip prep timed out")
        return False


async def render_video(
    job: Job,
    scenes: List[SceneMatch],
    audio_path: str,
    aspect_ratio: AspectRatio,
    output_path: str,
    srt_path: Optional[str] = None,
    burn_captions: bool = True,
    temp_dir: Optional[str] = None,
) -> dict:
    """
    Main rendering pipeline.
    Downloads clips, processes segments, concatenates, adds audio and captions.
    Returns verification info dict.
    """
    settings = get_settings()
    resolution = settings.render_resolution.get(aspect_ratio.value, (854, 480))
    width, height = resolution

    tmp = Path(temp_dir if temp_dir else (settings.temp_dir / job.job_id)).resolve()
    tmp.mkdir(parents=True, exist_ok=True)

    clip_paths: List[str] = []
    concat_list_path = str(tmp / "concat.txt")

    for i, scene in enumerate(scenes):
        scene_duration = max(1.0, scene.end - scene.start)
        segment_path = str(tmp / f"seg_{i:03d}.mp4")

        if scene.clip and scene.clip.download_url and not scene.clip.download_url.startswith("https://mock."):
            # Download real clip
            raw_path = str(tmp / f"raw_{i:03d}.mp4")
            logger.info("Downloading clip for scene %d: %s", i, scene.clip.download_url)
            success = await _download_clip(scene.clip.download_url, raw_path)
            if success:
                ok = _prepare_clip_segment(raw_path, segment_path, scene_duration, width, height)
                if not ok:
                    logger.warning("Clip prep failed for scene %d; using placeholder.", i)
                    _create_placeholder_clip(segment_path, scene_duration, width, height)
            else:
                _create_placeholder_clip(segment_path, scene_duration, width, height)
        else:
            # Mock/no clip — create colored placeholder
            _create_placeholder_clip(segment_path, scene_duration, width, height)

        clip_paths.append(segment_path)

    # Write concat list with ABSOLUTE POSIX paths (FFmpeg requires forward slashes on Windows)
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in clip_paths:
            abs_p = Path(p).resolve().as_posix()
            f.write(f"file '{abs_p}'\n")

    # Step 1: Concatenate video segments
    concat_video = str(tmp / "concat_video.mp4")
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264", "-preset", "fast",
        concat_video,
    ]
    proc = subprocess.run(concat_cmd, capture_output=True, timeout=300, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Concat failed: {proc.stderr.decode()[-500:]}")

    # Step 2: Mix video with narration audio
    mixed_path = str(tmp / "mixed.mp4")

    # Build filter for captions
    if burn_captions and srt_path and os.path.exists(srt_path):
        # Write ASS file for subtitle burn-in
        ass_content = generate_ass_subtitle_filter(scenes)
        ass_path = str(tmp / "captions.ass")
        Path(ass_path).write_text(ass_content, encoding="utf-8")

        # Windows FFmpeg path escaping: replace backslashes, escape colon in drive letter
        # e.g. D:/path/file.ass -> D\:/path/file.ass
        ass_posix = Path(ass_path).resolve().as_posix()
        # Escape colon in drive letter (D: -> D\:)
        if len(ass_posix) > 1 and ass_posix[1] == ":":
            ass_escaped = ass_posix[0] + "\\:" + ass_posix[2:]
        else:
            ass_escaped = ass_posix
        vf = f"subtitles='{ass_escaped}'"

        mix_cmd = [
            "ffmpeg", "-y",
            "-i", concat_video,
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", settings.video_bitrate,
            "-c:a", "aac", "-b:a", settings.audio_bitrate,
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            mixed_path,
        ]
    else:
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", concat_video,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", settings.video_bitrate,
            "-c:a", "aac", "-b:a", settings.audio_bitrate,
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            mixed_path,
        ]

    proc2 = subprocess.run(mix_cmd, capture_output=True, timeout=300, check=False)
    if proc2.returncode != 0:
        raise RuntimeError(f"Mix failed: {proc2.stderr.decode()[-500:]}")

    # Copy to final output
    shutil.copy2(mixed_path, output_path)

    # Verify with ffprobe
    info = _ffprobe_info(output_path)
    checksum = _file_sha256(output_path)

    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    return {
        "path": output_path,
        "checksum_sha256": checksum,
        "width": video_stream.get("width", width),
        "height": video_stream.get("height", height),
        "fps": video_stream.get("r_frame_rate", "30/1"),
        "video_codec": video_stream.get("codec_name", "unknown"),
        "audio_codec": audio_stream.get("codec_name", "unknown"),
        "duration": float(info.get("format", {}).get("duration", 0)),
        "file_size_bytes": os.path.getsize(output_path),
    }
