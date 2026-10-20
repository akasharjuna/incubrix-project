"""
B-roll job API routes under /api/v1/broll/
"""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException,
    UploadFile, status
)
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import AspectRatio, InputMode, Job, JobStatus
from app.schemas.job import (
    ClipReplaceRequest, CreateJobRequest, JobStatusResponse,
)
from app.storage.job_store import create_job, get_job, list_jobs, update_job
from app.workers.job_worker import process_job

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/broll", tags=["broll"])

_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        settings = get_settings()
        _semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
    return _semaphore


async def _run_job_with_limit(job: Job):
    """Run job under concurrency semaphore."""
    async with _get_semaphore():
        await process_job(job)


def _job_dir(job_id: str) -> Path:
    settings = get_settings()
    return settings.artifacts_dir / "jobs" / job_id


def _job_to_response(job: Job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        input_mode=job.input_mode.value,
        progress=job.progress,
        created_at=job.created_at.isoformat() + "Z",
        updated_at=job.updated_at.isoformat() + "Z",
        completed_at=job.completed_at.isoformat() + "Z" if job.completed_at else None,
        error_message=job.error_message,
        warnings=job.warnings,
        artifacts=job.artifacts if job.status == JobStatus.COMPLETED else None,
        scenes=job.scenes if job.status == JobStatus.COMPLETED else None,
    )


# ── POST /jobs ──────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job_endpoint(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
):
    """Create a new B-roll video job."""
    input_mode = (
        InputMode.SCRIPT if request.script is not None
        else InputMode.AUDIO if request.audio_url is not None
        else InputMode.SCENES
    )

    job = Job(
        input_mode=input_mode,
        script=request.script,
        audio_url=request.audio_url,
        scenes_input=(
            [s.model_dump() for s in request.scenes] if request.scenes else None
        ),
        aspect_ratios=request.aspect_ratios,
        captions_enabled=request.captions.enabled,
        burn_in_captions=request.captions.burn_in,
        avoid_list=request.avoid_list,
        callback_url=request.callback_url,
    )

    create_job(job)
    background_tasks.add_task(_run_job_with_limit, job)

    logger.info("Created job %s (mode=%s)", job.job_id, input_mode.value)
    return {"job_id": job.job_id, "status": job.status.value}


# ── POST /jobs/upload ───────────────────────────────────────────────────────

@router.post("/jobs/upload", status_code=status.HTTP_202_ACCEPTED)
async def create_job_with_upload(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    aspect_ratios: str = Form("16:9"),
    captions_enabled: bool = Form(True),
    burn_in_captions: bool = Form(True),
    avoid_list: str = Form(""),
):
    """Create a job by uploading an audio file directly."""
    settings = get_settings()

    # Validate file type
    allowed_types = ("audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4", "audio/mp3")
    allowed_exts = (".mp3", ".wav", ".m4a", ".mp4")
    fname = audio_file.filename or ""
    if not any(fname.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(400, f"Unsupported audio format. Allowed: {allowed_exts}")

    # Parse aspect ratios
    ar_list = []
    for ar in aspect_ratios.split(","):
        ar = ar.strip()
        try:
            ar_list.append(AspectRatio(ar))
        except ValueError:
            raise HTTPException(400, f"Invalid aspect ratio: {ar}")

    # Save uploaded file
    job = Job(
        input_mode=InputMode.AUDIO,
        audio_filename=fname,
        aspect_ratios=ar_list or [AspectRatio.R16_9],
        captions_enabled=captions_enabled,
        burn_in_captions=burn_in_captions,
        avoid_list=[a.strip() for a in avoid_list.split(",") if a.strip()],
    )
    create_job(job)

    job_dir = _job_dir(job.job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / fname

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    written = 0
    with open(str(dest), "wb") as out:
        while chunk := await audio_file.read(65536):
            written += len(chunk)
            if written > max_bytes:
                out.close()
                os.remove(str(dest))
                raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")
            out.write(chunk)

    update_job(job)
    background_tasks.add_task(_run_job_with_limit, job)

    logger.info("Created upload job %s (%s)", job.job_id, fname)
    return {"job_id": job.job_id, "status": job.status.value}


# ── GET /jobs ───────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs_endpoint(limit: int = 20, offset: int = 0):
    jobs = list_jobs(limit=limit, offset=offset)
    return {"jobs": [_job_to_response(j).model_dump() for j in jobs], "total": len(jobs)}


# ── GET /jobs/{job_id} ──────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id!r} not found.")
    return _job_to_response(job).model_dump()


# ── GET /jobs/{job_id}/artifacts/{filename} ─────────────────────────────────

@router.get("/jobs/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id!r} not found.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "Job not completed yet.")

    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = _job_dir(job_id) / safe_name
    if not file_path.exists():
        raise HTTPException(404, f"Artifact {safe_name!r} not found.")

    media_type_map = {
        ".mp4": "video/mp4",
        ".srt": "text/plain",
        ".json": "application/json",
    }
    ext = file_path.suffix.lower()
    media_type = media_type_map.get(ext, "application/octet-stream")

    return FileResponse(str(file_path), media_type=media_type, filename=safe_name)


# ── POST /jobs/{job_id}/replace-clip ────────────────────────────────────────

@router.post("/jobs/{job_id}/replace-clip")
async def replace_clip(
    job_id: str,
    request: ClipReplaceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Replace a selected clip in a completed job and re-render.
    Implements the Explainable Scene Matching & Recovery feature.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id!r} not found.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "Can only replace clips in completed jobs.")

    # Find the scene
    scene = next((s for s in job.scenes if s.scene_id == request.scene_id), None)
    if not scene:
        raise HTTPException(404, f"Scene {request.scene_id!r} not found.")

    # Find the alternative clip
    alt_clip = next(
        (c for c in scene.alternative_clips if c.asset_id == request.asset_id), None
    )
    if not alt_clip:
        raise HTTPException(
            404,
            f"Alternative clip {request.asset_id!r} not found for scene {request.scene_id}."
        )

    # Swap clip
    original_clip = scene.clip
    scene.clip = alt_clip
    scene.selection_reason = f"User replaced: {request.reason or 'Manual selection'}"
    scene.recovery_attempts.append(
        f"User replaced {original_clip.asset_id if original_clip else 'none'} "
        f"with {alt_clip.asset_id}. Reason: {request.reason}"
    )

    # Reset to re-render
    job.status = JobStatus.PROCESSING
    job.set_stage("rendering", 70, "Re-rendering after clip replacement...")
    update_job(job)

    background_tasks.add_task(_run_job_with_limit, job)

    return {"job_id": job_id, "scene_id": request.scene_id, "status": "re-rendering"}
