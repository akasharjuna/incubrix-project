"""
Caption/SRT generator.
Produces well-formatted SRT subtitle files from scene timing data.
Also provides burned-in caption ASS format for FFmpeg filter usage.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from app.core.logging import get_logger
from app.models.job import SceneMatch

logger = get_logger(__name__)

MAX_CHARS_PER_LINE = 42


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap_text(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> str:
    """Wrap text into lines of max_chars width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip() if current else word
    if current:
        lines.append(current)
    return "\n".join(lines[:2])  # max 2 lines per caption


def generate_srt(scenes: List[SceneMatch], output_path: str) -> str:
    """
    Generate an SRT subtitle file from scene data.
    Returns the output path.
    Validates that timestamps are valid and non-negative.
    """
    lines = []
    index = 1
    for scene in scenes:
        start = max(0.0, scene.start)
        end = max(start + 0.1, scene.end)

        text = scene.text.strip()
        if not text:
            continue

        wrapped = _wrap_text(text)
        lines.append(str(index))
        lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
        lines.append(wrapped)
        lines.append("")
        index += 1

    srt_content = "\n".join(lines)
    Path(output_path).write_text(srt_content, encoding="utf-8")
    logger.info("SRT generated: %s (%d entries)", output_path, index - 1)
    return output_path


def generate_ass_subtitle_filter(scenes: List[SceneMatch]) -> str:
    """
    Generate FFmpeg drawtext filter chain for burned-in captions.
    Returns a filter_complex string.
    """
    # We'll use the subtitle filter with a temporary ASS file
    # This function returns the ASS content to be written to a temp file
    ass_lines = [
        "[Script Info]",
        "Title: B-roll Captions",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,32,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,2,2,10,10,30,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def _ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    for scene in scenes:
        start = max(0.0, scene.start)
        end = max(start + 0.1, scene.end)
        text = scene.text.strip().replace("\n", " ").replace(",", "，")
        if not text:
            continue
        ass_lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{text}"
        )

    return "\n".join(ass_lines)
