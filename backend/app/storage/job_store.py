"""
In-memory + JSON-file job store.
Persists job state to disk so a restarted worker can detect orphaned jobs
and mark them failed instead of silently reporting them as successful.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import Job, JobStatus

logger = get_logger(__name__)
_lock = threading.Lock()

# In-memory store: job_id -> Job
_jobs: Dict[str, Job] = {}


def _job_path(job_id: str) -> Path:
    settings = get_settings()
    return settings.artifacts_dir / "jobs" / job_id / "job.json"


def _persist(job: Job) -> None:
    """Write job state to disk (best-effort)."""
    path = _job_path(job.job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not persist job %s: %s", job.job_id, exc)


def _load_from_disk() -> None:
    """On startup, load persisted jobs and fix orphaned processing ones."""
    settings = get_settings()
    jobs_dir = settings.artifacts_dir / "jobs"
    if not jobs_dir.exists():
        return
    for job_file in jobs_dir.glob("*/job.json"):
        try:
            data = json.loads(job_file.read_text(encoding="utf-8"))
            job = Job.model_validate(data)
            # Any job still in QUEUED or PROCESSING state was interrupted
            if job.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
                job.status = JobStatus.FAILED
                job.error_message = "Job interrupted by server restart."
                job.touch()
                _persist(job)
            _jobs[job.job_id] = job
            logger.info("Loaded persisted job %s (%s)", job.job_id, job.status)
        except Exception as exc:
            logger.warning("Could not load job from %s: %s", job_file, exc)


def initialize_store() -> None:
    _load_from_disk()


def create_job(job: Job) -> Job:
    with _lock:
        _jobs[job.job_id] = job
    _persist(job)
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def update_job(job: Job) -> None:
    job.touch()
    with _lock:
        _jobs[job.job_id] = job
    _persist(job)


def list_jobs(limit: int = 20, offset: int = 0) -> List[Job]:
    with _lock:
        jobs = sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)
    return jobs[offset : offset + limit]


def delete_job(job_id: str) -> bool:
    with _lock:
        if job_id not in _jobs:
            return False
        del _jobs[job_id]
    return True
