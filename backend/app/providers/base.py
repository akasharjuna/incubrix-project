"""Base footage provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from app.models.job import ClipInfo


class FootageProvider(ABC):
    """Abstract base for footage providers. Swap implementations without touching the engine."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def search(
        self, query: str, max_results: int = 10, orientation: str = "landscape"
    ) -> List[Tuple[str, ClipInfo]]:
        """
        Search for video clips matching the query.
        Returns list of (title, ClipInfo) tuples.
        orientation: "landscape" | "portrait" | "square"
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Return provider status dict."""
        ...
