"""Health and readiness endpoints."""
from fastapi import APIRouter
from app.core.config import get_settings
from app.providers.pexels_provider import get_provider

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@router.get("/ready")
async def ready():
    """Readiness check — verifies provider connectivity."""
    settings = get_settings()
    provider = get_provider(settings.footage_provider)
    provider_status = await provider.health_check()
    return {
        "status": "ready",
        "footage_provider": provider_status,
        "tts_provider": settings.tts_provider,
        "stt_provider": settings.stt_provider,
    }
