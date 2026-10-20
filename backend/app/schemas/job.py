"""API request/response schemas."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.job import AspectRatio, JobStatus, JobStage, SceneMatch, JobArtifacts, JobProgress


class SceneInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    visual_hint: Optional[str] = Field(None, max_length=500)


class CaptionConfig(BaseModel):
    enabled: bool = True
    burn_in: bool = True
    style: str = "default"  # default | minimal | bold


class CreateJobRequest(BaseModel):
    # Input (one of the three is required)
    script: Optional[str] = Field(None, max_length=50000)
    audio_url: Optional[str] = Field(None, max_length=2048)
    scenes: Optional[List[SceneInput]] = Field(None, max_length=100)

    # Options
    aspect_ratios: List[AspectRatio] = Field(
        default_factory=lambda: [AspectRatio.R16_9]
    )
    captions: CaptionConfig = Field(default_factory=CaptionConfig)
    avoid_list: List[str] = Field(default_factory=list, max_length=50)
    callback_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_input_mode(self) -> "CreateJobRequest":
        modes = [
            self.script is not None,
            self.audio_url is not None,
            self.scenes is not None,
        ]
        if sum(modes) == 0:
            raise ValueError("Provide one of: script, audio_url, or scenes.")
        if sum(modes) > 1:
            raise ValueError("Provide only one of: script, audio_url, or scenes.")
        return self

    @field_validator("script")
    @classmethod
    def validate_script(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Script cannot be blank.")
        return v

    @field_validator("audio_url")
    @classmethod
    def validate_audio_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from urllib.parse import urlparse
            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("audio_url must use http or https.")
            # SSRF protection: block private IPs
            import ipaddress, socket
            try:
                host = parsed.hostname
                addr = socket.getaddrinfo(host, None)[0][4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("audio_url resolves to a private/internal address.")
            except (socket.gaierror, ValueError):
                pass  # DNS not resolvable at validation time — checked at download
        return v


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    input_mode: str
    progress: JobProgress
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = []
    artifacts: Optional[JobArtifacts] = None
    scenes: Optional[List[SceneMatch]] = None


class ClipReplaceRequest(BaseModel):
    scene_id: str
    asset_id: str  # The alternative clip asset_id to use
    reason: Optional[str] = "User selected alternative"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    providers: Dict[str, Any] = {}
