"""Shared dataclasses and type definitions for the digest."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """Normalized article representation used across fetchers."""

    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    summary: Optional[str]
    content: Optional[str]
    author: Optional[str] = None
    id: str = field(default_factory=str)

    def primary_text(self) -> Optional[str]:
        """Return the best available text for summarization."""

        if self.content:
            return self.content
        return self.summary
