"""
Pexels footage provider.
Uses the Pexels Videos API (free tier, requires API key).
All returned clips have Pexels License which permits commercial use with attribution.
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

PEXELS_API_BASE = "https://api.pexels.com/videos"

_PEXELS_LICENSE = ClipLicense(
    name="Pexels License",
    url="https://www.pexels.com/license/",
    commercial_use=True,
    attribution_required=False,  # Pexels license does not require attribution (recommended but not mandatory)
    ai_generated=False,
)


def _parse_clip(video: dict) -> Optional[Tuple[str, ClipInfo]]:
    """Parse a Pexels video object into (title, ClipInfo)."""
    try:
        video_files = video.get("video_files", [])
        if not video_files:
            return None

        # Prefer HD (1280x720 or better), non-watermarked
        hd_files = [
            f for f in video_files
            if f.get("quality") in ("hd", "uhd", "sd")
            and f.get("file_type") == "video/mp4"
        ]
        if not hd_files:
            return None

        # Pick best quality available
        hd_files.sort(key=lambda f: f.get("width", 0), reverse=True)
        chosen = hd_files[0]

        title_parts = []
        if video.get("user", {}).get("name"):
            pass  # Don't include user name in search title
        tags = [t.get("title", "") for t in video.get("tags", [])]
        title_parts.extend(tags)
        if not title_parts:
            title_parts = [str(video.get("id", "pexels clip"))]

        title = " ".join(title_parts) or f"pexels clip {video.get('id')}"

        clip = ClipInfo(
            asset_id=f"pexels-{video['id']}",
            provider="pexels",
            source_url=video.get("url", ""),
            download_url=chosen["link"],
            width=chosen.get("width", video.get("width", 1920)),
            height=chosen.get("height", video.get("height", 1080)),
            duration=float(video.get("duration", 10)),
            license=_PEXELS_LICENSE,
            thumbnail_url=video.get("image"),
        )
        return title, clip
    except Exception as exc:
        logger.warning("Could not parse Pexels clip: %s", exc)
        return None


class PexelsProvider(FootageProvider):
    """Real Pexels Videos API integration."""

    @property
    def name(self) -> str:
        return "pexels"

    def _headers(self) -> dict:
        settings = get_settings()
        return {"Authorization": settings.pexels_api_key}

    async def search(
        self, query: str, max_results: int = 10, orientation: str = "landscape"
    ) -> List[Tuple[str, ClipInfo]]:
        settings = get_settings()
        if not settings.pexels_api_key:
            logger.warning("Pexels API key not configured; returning empty results.")
            return []

        orient_map = {"landscape": "landscape", "portrait": "portrait", "square": "square"}
        params = {
            "query": query,
            "per_page": min(max_results, 20),
            "orientation": orient_map.get(orientation, "landscape"),
        }

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                resp = await client.get(
                    f"{PEXELS_API_BASE}/search",
                    headers=self._headers(),
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.error("Pexels API timed out for query: %s", query)
            return []
        except httpx.HTTPStatusError as exc:
            logger.error("Pexels API error %s for query: %s", exc.response.status_code, query)
            return []
        except Exception as exc:
            logger.error("Pexels provider unexpected error: %s", exc)
            return []

        results = []
        for video in data.get("videos", []):
            parsed = _parse_clip(video)
            if parsed:
                results.append(parsed)

        logger.info("Pexels returned %d clips for query: %s", len(results), query)
        return results

    async def health_check(self) -> dict:
        settings = get_settings()
        if not settings.pexels_api_key:
            return {"provider": "pexels", "status": "not_configured", "key": "missing"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{PEXELS_API_BASE}/search",
                    headers=self._headers(),
                    params={"query": "nature", "per_page": 1},
                )
                resp.raise_for_status()
            return {"provider": "pexels", "status": "ok"}
        except Exception as exc:
            return {"provider": "pexels", "status": "error", "detail": str(exc)}


def get_provider(name: str) -> FootageProvider:
    """Factory function returning a footage provider by name."""
    from app.providers.mock_provider import MockFootageProvider
    from app.providers.pixabay_provider import PixabayProvider
    providers = {
        "pexels": PexelsProvider,
        "pixabay": PixabayProvider,
        "mock": MockFootageProvider,
    }
    cls = providers.get(name)
    if cls is None:
        logger.warning("Unknown provider '%s', falling back to mock.", name)
        return MockFootageProvider()
    return cls()
