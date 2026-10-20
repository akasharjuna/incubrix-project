"""
Mock footage provider for deterministic testing.
Returns fixture clips without any network calls.
Clip IDs are deterministic based on query so tests are reproducible.
"""
from __future__ import annotations

import hashlib
from typing import List, Tuple

from app.models.job import ClipInfo, ClipLicense
from app.providers.base import FootageProvider

# A set of realistic fixture clips covering common topics
_FIXTURE_CLIPS = [
    {
        "asset_id": "mock-001",
        "title": "city skyline timelapse urban buildings",
        "width": 1920, "height": 1080, "duration": 15.0,
        "source_url": "https://mock.provider/clips/001",
        "download_url": "https://mock.provider/download/001.mp4",
        "thumbnail_url": "https://mock.provider/thumb/001.jpg",
    },
    {
        "asset_id": "mock-002",
        "title": "solar panels renewable energy sunlight",
        "width": 1920, "height": 1080, "duration": 12.0,
        "source_url": "https://mock.provider/clips/002",
        "download_url": "https://mock.provider/download/002.mp4",
        "thumbnail_url": "https://mock.provider/thumb/002.jpg",
    },
    {
        "asset_id": "mock-003",
        "title": "technology computer code programming developer",
        "width": 1920, "height": 1080, "duration": 10.0,
        "source_url": "https://mock.provider/clips/003",
        "download_url": "https://mock.provider/download/003.mp4",
        "thumbnail_url": "https://mock.provider/thumb/003.jpg",
    },
    {
        "asset_id": "mock-004",
        "title": "nature forest trees green environment",
        "width": 1920, "height": 1080, "duration": 20.0,
        "source_url": "https://mock.provider/clips/004",
        "download_url": "https://mock.provider/download/004.mp4",
        "thumbnail_url": "https://mock.provider/thumb/004.jpg",
    },
    {
        "asset_id": "mock-005",
        "title": "business meeting office team collaboration",
        "width": 1920, "height": 1080, "duration": 18.0,
        "source_url": "https://mock.provider/clips/005",
        "download_url": "https://mock.provider/download/005.mp4",
        "thumbnail_url": "https://mock.provider/thumb/005.jpg",
    },
    {
        "asset_id": "mock-006",
        "title": "financial bank building money investment",
        "width": 1920, "height": 1080, "duration": 14.0,
        "source_url": "https://mock.provider/clips/006",
        "download_url": "https://mock.provider/download/006.mp4",
        "thumbnail_url": "https://mock.provider/thumb/006.jpg",
    },
    {
        "asset_id": "mock-007",
        "title": "clouds sky weather blue aerial",
        "width": 1920, "height": 1080, "duration": 25.0,
        "source_url": "https://mock.provider/clips/007",
        "download_url": "https://mock.provider/download/007.mp4",
        "thumbnail_url": "https://mock.provider/thumb/007.jpg",
    },
    {
        "asset_id": "mock-008",
        "title": "people walking street crowd urban",
        "width": 1920, "height": 1080, "duration": 16.0,
        "source_url": "https://mock.provider/clips/008",
        "download_url": "https://mock.provider/download/008.mp4",
        "thumbnail_url": "https://mock.provider/thumb/008.jpg",
    },
    {
        "asset_id": "mock-009",
        "title": "education learning students classroom school",
        "width": 1920, "height": 1080, "duration": 22.0,
        "source_url": "https://mock.provider/clips/009",
        "download_url": "https://mock.provider/download/009.mp4",
        "thumbnail_url": "https://mock.provider/thumb/009.jpg",
    },
    {
        "asset_id": "mock-010",
        "title": "health medical hospital doctor patient",
        "width": 1920, "height": 1080, "duration": 13.0,
        "source_url": "https://mock.provider/clips/010",
        "download_url": "https://mock.provider/download/010.mp4",
        "thumbnail_url": "https://mock.provider/thumb/010.jpg",
    },
    {
        "asset_id": "mock-011",
        "title": "food cooking kitchen chef restaurant",
        "width": 1920, "height": 1080, "duration": 11.0,
        "source_url": "https://mock.provider/clips/011",
        "download_url": "https://mock.provider/download/011.mp4",
        "thumbnail_url": "https://mock.provider/thumb/011.jpg",
    },
    {
        "asset_id": "mock-012",
        "title": "travel airplane airport tourism vacation",
        "width": 1920, "height": 1080, "duration": 17.0,
        "source_url": "https://mock.provider/clips/012",
        "download_url": "https://mock.provider/download/012.mp4",
        "thumbnail_url": "https://mock.provider/thumb/012.jpg",
    },
]

_MOCK_LICENSE = ClipLicense(
    name="CC0 / Mock License",
    url="https://creativecommons.org/publicdomain/zero/1.0/",
    commercial_use=True,
    attribution_required=False,
    ai_generated=False,
)


def _to_clip(data: dict) -> ClipInfo:
    return ClipInfo(
        asset_id=data["asset_id"],
        provider="mock",
        source_url=data["source_url"],
        download_url=data["download_url"],
        width=data["width"],
        height=data["height"],
        duration=data["duration"],
        license=_MOCK_LICENSE,
        thumbnail_url=data.get("thumbnail_url"),
    )


class MockFootageProvider(FootageProvider):
    """
    Deterministic mock provider — returns all fixture clips regardless of query.
    The semantic matcher then ranks them by relevance.
    No network calls are made.
    """

    @property
    def name(self) -> str:
        return "mock"

    async def search(
        self, query: str, max_results: int = 10, orientation: str = "landscape"
    ) -> List[Tuple[str, ClipInfo]]:
        results = [
            (clip["title"], _to_clip(clip))
            for clip in _FIXTURE_CLIPS[:max_results]
        ]
        return results

    async def health_check(self) -> dict:
        return {"provider": "mock", "status": "ok", "clips_available": len(_FIXTURE_CLIPS)}
