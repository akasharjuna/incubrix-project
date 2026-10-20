"""
Application configuration using pydantic-settings.
All values can be overridden via environment variables or .env file.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = 2 levels up from this file (backend/app/core/config.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    workers: int = 1

    # Storage — absolute paths so they work from any working directory
    artifacts_dir: Path = _PROJECT_ROOT / "artifacts"
    temp_dir: Path = _PROJECT_ROOT / "temp"
    max_upload_size_mb: int = 100

    # Job processing
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 600

    # Footage provider
    footage_provider: Literal["pexels", "pixabay", "mock"] = "mock"
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    provider_timeout_seconds: int = 15
    provider_max_results: int = 10

    # TTS
    tts_provider: Literal["gtts", "mock"] = "gtts"
    elevenlabs_api_key: str = ""

    # STT
    stt_provider: Literal["whisper", "mock"] = "whisper"
    whisper_model: str = "base"

    # Semantic matching
    embedding_model: str = "all-MiniLM-L6-v2"
    min_relevance_threshold: float = 0.20
    semantic_weight: float = 0.60
    visual_hint_weight: float = 0.20
    duration_weight: float = 0.10
    aspect_ratio_weight: float = 0.10

    # Video rendering
    render_preset: Literal["production", "development"] = "development"
    video_fps: int = 30
    video_bitrate: str = "2000k"
    audio_bitrate: str = "128k"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Callback
    callback_hmac_secret: str = ""

    @property
    def render_resolution(self) -> dict:
        if self.render_preset == "production":
            return {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
        # Development — faster render
        return {"16:9": (854, 480), "9:16": (480, 854), "1:1": (480, 480)}

    def ensure_dirs(self):
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "jobs").mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear the settings cache and reload from environment / .env file."""
    get_settings.cache_clear()
    return get_settings()
