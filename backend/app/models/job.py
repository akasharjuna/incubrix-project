"""Job state models and enumerations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(str, Enum):
    VALIDATING = "validating"
    TRANSCRIBING = "transcribing"
    SEGMENTING = "segmenting"
    GENERATING_AUDIO = "generating_audio"
    MATCHING_FOOTAGE = "matching_footage"
    DOWNLOADING_CLIPS = "downloading_clips"
    RENDERING = "rendering"
    GENERATING_CAPTIONS = "generating_captions"
    FINALIZING = "finalizing"
    DONE = "done"


class AspectRatio(str, Enum):
    R16_9 = "16:9"
    R9_16 = "9:16"
    R1_1 = "1:1"


class InputMode(str, Enum):
    SCRIPT = "script"
    AUDIO = "audio"
    SCENES = "scenes"


class ClipLicense(BaseModel):
    name: str
    url: Optional[str] = None
    commercial_use: bool
    attribution_required: bool
    ai_generated: bool = False


class ClipInfo(BaseModel):
    asset_id: str
    provider: str
    source_url: str
    download_url: str
    width: int
    height: int
    duration: float
    license: ClipLicense
    thumbnail_url: Optional[str] = None


class SceneMatch(BaseModel):
    scene_id: str
    text: str
    visual_hint: Optional[str] = None
    start: float
    end: float
    clip: Optional[ClipInfo] = None
    relevance_score: float = 0.0
    selection_reason: str = ""
    alternative_clips: List[ClipInfo] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    recovery_attempts: List[str] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list)


class JobProgress(BaseModel):
    stage: JobStage = JobStage.VALIDATING
    percent: int = 0
    message: str = ""
    scenes_total: int = 0
    scenes_done: int = 0


class JobArtifacts(BaseModel):
    video_16_9: Optional[str] = None
    video_9_16: Optional[str] = None
    video_1_1: Optional[str] = None
    captions_srt: Optional[str] = None
    timeline_json: Optional[str] = None
    manifest_json: Optional[str] = None


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    input_mode: InputMode
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Input details
    script: Optional[str] = None
    audio_url: Optional[str] = None
    audio_filename: Optional[str] = None
    scenes_input: Optional[List[Dict[str, Any]]] = None

    # Configuration
    aspect_ratios: List[AspectRatio] = Field(default_factory=lambda: [AspectRatio.R16_9])
    captions_enabled: bool = True
    burn_in_captions: bool = True
    avoid_list: List[str] = Field(default_factory=list)
    callback_url: Optional[str] = None

    # Progress
    progress: JobProgress = Field(default_factory=JobProgress)

    # Results
    scenes: List[SceneMatch] = Field(default_factory=list)
    artifacts: JobArtifacts = Field(default_factory=JobArtifacts)
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    def touch(self):
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def set_stage(self, stage: JobStage, percent: int, message: str):
        self.progress.stage = stage
        self.progress.percent = percent
        self.progress.message = message
        self.touch()
