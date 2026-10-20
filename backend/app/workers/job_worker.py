"""
Main job processing worker.
Orchestrates the complete pipeline:
  validate → segment → TTS → match footage → download → render → captions → timeline → manifest
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

from app.core.config import get_settings
from app.core.logging import get_logger
from app.matching.semantic_matcher import rank_clips
from app.models.job import (
    AspectRatio, ClipInfo, Job, JobStage, JobStatus,
    SceneMatch,
)
from app.providers.pexels_provider import get_provider
from app.rendering.caption_generator import generate_srt
from app.rendering.video_renderer import render_video
from app.schemas.job import CreateJobRequest
from app.services.artifact_service import generate_manifest, generate_timeline
from app.services.scene_segmenter import (
    extract_visual_concepts, segment_script,
)
from app.services.stt_service import download_audio, transcribe_audio
from app.services.tts_service import generate_tts
from app.storage.job_store import update_job

logger = get_logger(__name__)


def _job_dir(job_id: str) -> Path:
    settings = get_settings()
    path = settings.artifacts_dir / "jobs" / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _temp_dir(job_id: str) -> Path:
    settings = get_settings()
    path = settings.temp_dir / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _select_clip_for_scene(
    scene_text: str,
    visual_hint: Optional[str],
    search_queries: List[str],
    target_duration: float,
    target_ar: str,
    used_ids: Set[str],
    avoid_list: List[str],
    job_warnings: List[str],
) -> tuple[Optional[ClipInfo], float, str, List[ClipInfo], List[str]]:
    """
    For a single scene, search and rank footage candidates.
    Returns (best_clip, score, reason, alternatives, recovery_attempts).
    """
    settings = get_settings()
    provider = get_provider(settings.footage_provider)
    threshold = settings.min_relevance_threshold

    orientation_map = {
        "16:9": "landscape", "9:16": "portrait", "1:1": "square"
    }
    orientation = orientation_map.get(target_ar, "landscape")

    all_candidates = []
    recovery_attempts = []

    for query in search_queries:
        try:
            results = await provider.search(
                query, max_results=settings.provider_max_results, orientation=orientation
            )
            all_candidates.extend(results)
        except Exception as exc:
            logger.warning("Provider search failed for '%s': %s", query, exc)
            recovery_attempts.append(f"Search '{query}' failed: {exc}")

    # Remove clips from avoid_list
    filtered = [
        (title, clip) for title, clip in all_candidates
        if not any(
            avoid.lower() in title.lower() or avoid.lower() in clip.asset_id.lower()
            for avoid in avoid_list
        )
    ]

    # Remove clips without commercial license
    licensed = [
        (title, clip) for title, clip in filtered
        if clip.license.commercial_use
    ]
    if not licensed and filtered:
        job_warnings.append(
            f"Scene '{scene_text[:50]}': No commercially-licensed clips found."
        )
        recovery_attempts.append("No commercially-licensed clips — using fallback.")

    if not licensed:
        licensed = filtered  # Use all if none are licensed (mock mode)

    # Rank candidates
    ranked = rank_clips(
        scene_text, visual_hint, licensed, target_duration, target_ar, used_ids
    )

    if not ranked:
        recovery_attempts.append("No candidates from any search query.")
        return None, 0.0, "No footage found.", [], recovery_attempts

    # Try fallback query if top score too low
    top_score = ranked[0][0]
    if top_score < threshold and search_queries:
        recovery_attempts.append(
            f"Top score {top_score:.2f} below threshold {threshold}; trying fallback query."
        )
        fallback_query = "abstract background cinematic"
        try:
            fb_results = await provider.search(
                fallback_query, max_results=5, orientation=orientation
            )
            fb_ranked = rank_clips(
                scene_text, visual_hint, fb_results, target_duration, target_ar, used_ids
            )
            if fb_ranked and fb_ranked[0][0] > top_score:
                ranked = fb_ranked + ranked
                ranked.sort(key=lambda x: x[0], reverse=True)
                recovery_attempts.append("Fallback query improved top candidate.")
        except Exception as exc:
            recovery_attempts.append(f"Fallback query also failed: {exc}")

    best_score, best_reason, best_clip = ranked[0]
    alternatives = [clip for _, _, clip in ranked[1:4]]

    return best_clip, best_score, best_reason, alternatives, recovery_attempts


async def process_job(job: Job) -> None:
    """
    Main async job processor. Called from background thread pool.
    Updates job state throughout processing.
    """
    settings = get_settings()
    job_id = job.job_id
    job_dir = _job_dir(job_id)
    tmp_dir = _temp_dir(job_id)

    try:
        job.status = JobStatus.PROCESSING
        job.set_stage(JobStage.VALIDATING, 5, "Validating input...")
        update_job(job)

        # ── Stage 1: Input handling ────────────────────────────────────
        scenes_data: List[dict] = []
        audio_path: Optional[str] = None
        total_duration = 0.0

        if job.input_mode.value == "script":
            job.set_stage(JobStage.SEGMENTING, 10, "Segmenting script into scenes...")
            update_job(job)
            scenes_data = segment_script(job.script)

            # Generate TTS for whole script
            job.set_stage(JobStage.GENERATING_AUDIO, 20, "Generating narration audio...")
            update_job(job)
            audio_path = str(job_dir / "narration.mp3")
            total_duration = await generate_tts(job.script, audio_path)

            # Update scene timings from actual audio duration
            if total_duration > 0 and scenes_data:
                _redistribute_timings(scenes_data, total_duration)

        elif job.input_mode.value == "audio":
            job.set_stage(JobStage.VALIDATING, 10, "Downloading audio...")
            update_job(job)

            audio_path = str(tmp_dir / "uploaded_audio.mp3")
            if job.audio_url:
                await download_audio(job.audio_url, audio_path)
            elif job.audio_filename:
                # Already saved during upload
                audio_path = str(job_dir / job.audio_filename)

            job.set_stage(JobStage.TRANSCRIBING, 20, "Transcribing audio...")
            update_job(job)
            transcript = await transcribe_audio(audio_path)
            total_duration = transcript["duration"]

            # Convert transcript segments to scenes
            if transcript["segments"]:
                scenes_data = _transcript_to_scenes(transcript["segments"])
            else:
                scenes_data = segment_script(transcript["text"])
                if total_duration > 0:
                    _redistribute_timings(scenes_data, total_duration)

        elif job.input_mode.value == "scenes":
            # Structured scenes input
            raw_scenes = job.scenes_input or []
            scenes_data = []
            running = 0.0
            for i, raw in enumerate(raw_scenes):
                text = raw.get("text", "")
                hint = raw.get("visual_hint")
                # Generate TTS for each scene separately
                scene_audio = str(tmp_dir / f"scene_{i:03d}.mp3")
                dur = await generate_tts(text, scene_audio)
                scenes_data.append({
                    "scene_id": f"scene-{i+1:03d}",
                    "text": text,
                    "visual_hint": hint,
                    "audio_path": scene_audio,
                    "estimated_duration": dur,
                    "estimated_start": running,
                    "estimated_end": running + dur,
                })
                running += dur
                total_duration = running

            # Concatenate scene audios into one narration
            audio_path = str(job_dir / "narration.mp3")
            await _concat_audios(
                [s["audio_path"] for s in scenes_data],
                audio_path,
            )

        # ── Stage 2: Footage matching ─────────────────────────────────
        job.set_stage(JobStage.MATCHING_FOOTAGE, 35, "Matching B-roll footage...")
        job.progress.scenes_total = len(scenes_data)
        update_job(job)

        target_ar = job.aspect_ratios[0].value if job.aspect_ratios else "16:9"
        used_ids: Set[str] = set()
        scene_matches: List[SceneMatch] = []

        for i, scene_data in enumerate(scenes_data):
            scene_text = scene_data["text"]
            visual_hint = scene_data.get("visual_hint")
            start = scene_data.get("estimated_start", 0.0)
            end = scene_data.get("estimated_end", start + 5.0)
            duration = max(1.0, end - start)

            search_queries = extract_visual_concepts(scene_text)
            if visual_hint:
                search_queries.insert(0, visual_hint)

            best_clip, score, reason, alternatives, recovery = await _select_clip_for_scene(
                scene_text=scene_text,
                visual_hint=visual_hint,
                search_queries=search_queries,
                target_duration=duration,
                target_ar=target_ar,
                used_ids=used_ids,
                avoid_list=job.avoid_list,
                job_warnings=job.warnings,
            )

            fallback_used = (best_clip is None or score < settings.min_relevance_threshold)
            if best_clip and not fallback_used:
                used_ids.add(best_clip.asset_id)

            match = SceneMatch(
                scene_id=scene_data["scene_id"],
                text=scene_text,
                visual_hint=visual_hint,
                start=start,
                end=end,
                clip=best_clip,
                relevance_score=round(score, 4),
                selection_reason=reason,
                alternative_clips=alternatives,
                fallback_used=fallback_used,
                fallback_reason=(
                    f"Score {score:.2f} below threshold {settings.min_relevance_threshold}"
                    if fallback_used and best_clip else
                    "No suitable footage found"
                ) if fallback_used else None,
                recovery_attempts=recovery,
                search_queries=search_queries,
            )
            scene_matches.append(match)

            job.progress.scenes_done = i + 1
            pct = 35 + int(30 * (i + 1) / len(scenes_data))
            job.set_stage(JobStage.MATCHING_FOOTAGE, pct, f"Matched {i+1}/{len(scenes_data)} scenes")
            update_job(job)

        job.scenes = scene_matches

        # ── Stage 3: Caption generation ───────────────────────────────
        job.set_stage(JobStage.GENERATING_CAPTIONS, 67, "Generating captions...")
        update_job(job)

        srt_path = str(job_dir / "captions.srt")
        generate_srt(scene_matches, srt_path)
        job.artifacts.captions_srt = "captions.srt"

        # ── Stage 4: Rendering ────────────────────────────────────────
        job.set_stage(JobStage.RENDERING, 70, "Rendering video...")
        update_job(job)

        artifact_info = {}
        render_results = {}

        for ar in job.aspect_ratios:
            ar_label = ar.value.replace(":", "_")
            out_filename = f"video_{ar_label}.mp4"
            out_path = str(job_dir / out_filename)

            logger.info("Rendering %s -> %s", ar.value, out_path)
            try:
                result = await render_video(
                    job=job,
                    scenes=scene_matches,
                    audio_path=audio_path,
                    aspect_ratio=ar,
                    output_path=out_path,
                    srt_path=srt_path,
                    burn_captions=job.burn_in_captions,
                    temp_dir=str(tmp_dir),
                )
                render_results[ar.value] = result
                artifact_info[f"video_{ar_label}"] = out_filename

                # Set artifact field on job
                if ar == AspectRatio.R16_9:
                    job.artifacts.video_16_9 = out_filename
                elif ar == AspectRatio.R9_16:
                    job.artifacts.video_9_16 = out_filename
                elif ar == AspectRatio.R1_1:
                    job.artifacts.video_1_1 = out_filename

            except Exception as exc:
                logger.error("Render failed for %s: %s", ar.value, exc)
                job.warnings.append(f"Render failed for {ar.value}: {exc}")

        # ── Stage 5: Timeline & Manifest ──────────────────────────────
        job.set_stage(JobStage.FINALIZING, 92, "Generating timeline and manifest...")
        update_job(job)

        timeline_path = str(job_dir / "timeline.json")
        timeline = generate_timeline(job, scene_matches, timeline_path)
        job.artifacts.timeline_json = "timeline.json"

        manifest_path = str(job_dir / "manifest.json")
        generate_manifest(job, timeline, artifact_info, manifest_path)
        job.artifacts.manifest_json = "manifest.json"

        # ── Done ──────────────────────────────────────────────────────
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.set_stage(JobStage.DONE, 100, "Video ready.")
        update_job(job)
        logger.info("Job %s completed successfully.", job_id)

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.touch()
        update_job(job)

    finally:
        # Clean up temp files
        import shutil
        try:
            if tmp_dir.exists():
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
        except Exception:
            pass


def _redistribute_timings(scenes: list, total_duration: float):
    """Proportionally redistribute scene timings based on word count."""
    total_words = sum(len(s["text"].split()) for s in scenes)
    if total_words == 0:
        return
    running = 0.0
    for s in scenes:
        word_fraction = len(s["text"].split()) / total_words
        dur = word_fraction * total_duration
        s["estimated_start"] = round(running, 3)
        s["estimated_end"] = round(running + dur, 3)
        s["estimated_duration"] = round(dur, 3)
        running += dur


def _transcript_to_scenes(segments: list) -> list:
    """Convert Whisper segments to scene dicts."""
    return [
        {
            "scene_id": f"scene-{i+1:03d}",
            "text": seg["text"].strip(),
            "visual_hint": None,
            "estimated_duration": max(1.0, seg["end"] - seg["start"]),
            "estimated_start": seg["start"],
            "estimated_end": seg["end"],
        }
        for i, seg in enumerate(segments)
        if seg.get("text", "").strip()
    ]


async def _concat_audios(paths: list, output: str):
    """Concatenate multiple audio files into one."""
    if not paths:
        return
    if len(paths) == 1:
        import shutil
        shutil.copy2(paths[0], output)
        return

    concat_list = output + ".txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in paths:
            abs_p = Path(p).resolve().as_posix()
            f.write(f"file '{abs_p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-acodec", "copy",
        output,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await asyncio.wait_for(proc.wait(), timeout=60)
    os.remove(concat_list)
