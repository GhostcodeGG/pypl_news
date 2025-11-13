"""Persisted state helpers to prevent duplicate processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Set

LOGGER = logging.getLogger(__name__)


class StateStore:
    """JSON-backed store tracking processed article IDs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._data = json.loads(self.path.read_text())
        except json.JSONDecodeError as exc:
            LOGGER.warning("Could not parse state file %s: %s", self.path, exc)
            self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

    @property
    def seen_ids(self) -> Set[str]:
        return set(self._data.keys())

    def mark_seen(self, article_id: str, title: str) -> None:
        self._data[article_id] = title


__all__ = ["StateStore"]
