"""
Pixabay footage provider.
Uses the Pixabay Videos API (requires API key).
All returned clips are licensed for commercial use without attribution.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import ClipInfo, ClipLicense
from app.providers.base import FootageProvider

logger = get_logger(__name__)

PIXABAY_API_BASE = "https://pixabay.com/api/videos/"

_PIXABAY_LICENSE = ClipLicense(
    name="Pixabay License",
    url="https://pixabay.com/service/license/",
    commercial_use=True,
    attribution_required=False,
    ai_generated=False,
)


def _parse_clip(hit: dict) -> Optional[Tuple[str, ClipInfo]]:
    """Parse a Pixabay video hit into (title, ClipInfo)."""
    try:
        videos = hit.get("videos", {})
        # Prefer large resolution, fallback to medium, small, tiny
        for quality in ("large", "medium", "small", "tiny"):
            vid = videos.get(quality)
            if vid and vid.get("url"):
                chosen = vid
                break
        else:
            return None

        title = hit.get("tags", "pixabay video")
        clip = ClipInfo(
            asset_id=f"pixabay-{hit.get('id')}",
            provider="pixabay",
            source_url=hit.get("pageURL", ""),
            download_url=chosen["url"],
            width=chosen.get("width", 1280),
            height=chosen.get("height", 720),
            duration=float(hit.get("duration", 10)),
            license=_PIXABAY_LICENSE,
            thumbnail_url=hit.get("previewURL", ""),
        )
        return title, clip
    except Exception as exc:
        logger.warning("Could not parse Pixabay clip: %s", exc)
        return None


class PixabayProvider(FootageProvider):
    """Real Pixabay Videos API integration."""

    @property
    def name(self) -> str:
        return "pixabay"

    def _headers(self) -> dict:
        # Pixabay uses API key as query param, no special headers needed
        return {}

    async def search(
        self, query: str, max_results: int = 10, orientation: str = "landscape"
    ) -> List[Tuple[str, ClipInfo]]:
        settings = get_settings()
        if not settings.pixabay_api_key:
            logger.warning("Pixabay API key not configured; returning empty results.")
            return []
        params = {
            "key": settings.pixabay_api_key,
            "q": query,
            "per_page": min(max_results, 200),
            "safesearch": "true",
        }
        # Pixabay does not support orientation filter for videos; ignore orientation argument
        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                resp = await client.get(PIXABAY_API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.error("Pixabay API timed out for query: %s", query)
            return []
        except httpx.HTTPStatusError as exc:
            logger.error("Pixabay API error %s for query: %s", exc.response.status_code, query)
            return []
        except Exception as exc:
            logger.error("Pixabay provider unexpected error: %s", exc)
            return []

        results: List[Tuple[str, ClipInfo]] = []
        for hit in data.get("hits", []):
            parsed = _parse_clip(hit)
            if parsed:
                results.append(parsed)
        logger.info("Pixabay returned %d clips for query: %s", len(results), query)
        return results

    async def health_check(self) -> dict:
        settings = get_settings()
        if not settings.pixabay_api_key:
            return {"provider": "pixabay", "status": "not_configured", "key": "missing"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    PIXABAY_API_BASE,
                    params={"key": settings.pixabay_api_key, "q": "nature", "per_page": 1},
                )
                resp.raise_for_status()
            return {"provider": "pixabay", "status": "ok"}
        except Exception as exc:
            return {"provider": "pixabay", "status": "error", "detail": str(exc)}
