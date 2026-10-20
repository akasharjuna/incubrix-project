"""
Timeline and manifest generators.
Produces structured JSON artifacts that document exactly how
each scene was constructed and what processing was done.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.models.job import Job, SceneMatch


def generate_timeline(job: Job, scenes: List[SceneMatch], output_path: str) -> dict:
    """Generate timeline.json with full scene provenance."""
    timeline = {
        "job_id": job.job_id,
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "input_mode": job.input_mode.value,
        "aspect_ratios": [ar.value for ar in job.aspect_ratios],
        "total_duration": max((s.end for s in scenes), default=0.0),
        "scenes": [],
    }

    for scene in scenes:
        scene_data = {
            "scene_id": scene.scene_id,
            "text": scene.text,
            "visual_hint": scene.visual_hint,
            "start": scene.start,
            "end": scene.end,
            "duration": round(scene.end - scene.start, 3),
            "relevance_score": scene.relevance_score,
            "selection_reason": scene.selection_reason,
            "search_queries": scene.search_queries,
            "fallback_used": scene.fallback_used,
            "fallback_reason": scene.fallback_reason,
            "recovery_attempts": scene.recovery_attempts,
        }

        if scene.clip:
            scene_data["clip"] = {
                "asset_id": scene.clip.asset_id,
                "provider": scene.clip.provider,
                "source_url": scene.clip.source_url,
                "download_url": scene.clip.download_url,
                "width": scene.clip.width,
                "height": scene.clip.height,
                "duration": scene.clip.duration,
                "thumbnail_url": scene.clip.thumbnail_url,
                "license": {
                    "name": scene.clip.license.name,
                    "url": scene.clip.license.url,
                    "commercial_use": scene.clip.license.commercial_use,
                    "attribution_required": scene.clip.license.attribution_required,
                },
                "ai_generated": scene.clip.license.ai_generated,
            }
        else:
            scene_data["clip"] = None

        # Include alternative clips (for explainable matching UI)
        alternatives = []
        for alt in scene.alternative_clips[:3]:
            alternatives.append({
                "asset_id": alt.asset_id,
                "provider": alt.provider,
                "source_url": alt.source_url,
                "thumbnail_url": alt.thumbnail_url,
                "duration": alt.duration,
                "license": alt.license.name,
            })
        scene_data["alternatives"] = alternatives

        timeline["scenes"].append(scene_data)

    Path(output_path).write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    return timeline


def generate_manifest(
    job: Job,
    timeline: dict,
    artifact_info: dict,
    output_path: str,
) -> dict:
    """Generate manifest.json with full job provenance."""
    settings = get_settings()

    manifest = {
        "job_id": job.job_id,
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "status": job.status.value,
        "input": {
            "mode": job.input_mode.value,
            "script_preview": (job.script or "")[:200] if job.script else None,
            "audio_url": job.audio_url,
            "audio_filename": job.audio_filename,
            "scenes_count": len(job.scenes_input or []),
            "aspect_ratios_requested": [ar.value for ar in job.aspect_ratios],
            "captions_enabled": job.captions_enabled,
            "burn_in_captions": job.burn_in_captions,
            "avoid_list": job.avoid_list,
        },
        "outputs": {
            "video_16_9": artifact_info.get("video_16_9"),
            "video_9_16": artifact_info.get("video_9_16"),
            "video_1_1": artifact_info.get("video_1_1"),
            "captions_srt": artifact_info.get("captions_srt"),
            "timeline_json": "timeline.json",
            "manifest_json": "manifest.json",
        },
        "processing": {
            "tts_provider": settings.tts_provider,
            "stt_provider": settings.stt_provider,
            "footage_provider": settings.footage_provider,
            "embedding_model": settings.embedding_model,
            "render_preset": settings.render_preset,
            "min_relevance_threshold": settings.min_relevance_threshold,
        },
        "statistics": {
            "total_scenes": len(timeline.get("scenes", [])),
            "total_duration": timeline.get("total_duration", 0),
            "fallbacks_used": sum(1 for s in timeline.get("scenes", []) if s.get("fallback_used")),
            "avg_relevance_score": _safe_avg(
                [s.get("relevance_score", 0) for s in timeline.get("scenes", [])]
            ),
        },
        "warnings": job.warnings,
        "software": {
            "name": "B-roll Video Engine",
            "version": "1.0.0",
            "author": "IncuBrix Assessment Submission",
        },
    }

    Path(output_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _safe_avg(values: list) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
