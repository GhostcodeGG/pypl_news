"""Configuration utilities for the PayPal news digest project."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DATA_DIR = Path(os.getenv("PAYPAL_DIGEST_DATA_DIR", "data"))
DEFAULT_DIGEST_DIR = DEFAULT_DATA_DIR / "digests"
DEFAULT_STATE_FILE = DEFAULT_DATA_DIR / "state.json"


@dataclass(frozen=True)
class Config:
    """Runtime configuration values for the digest run."""

    newsapi_key: Optional[str]
    data_dir: Path = DEFAULT_DATA_DIR
    digest_dir: Path = DEFAULT_DIGEST_DIR
    state_file: Path = DEFAULT_STATE_FILE
    query: str = "PayPal OR PYPL"
    language: str = "en"
    max_articles: int = 30
    digest_date: datetime = field(default_factory=datetime.utcnow)

    @property
    def digest_path(self) -> Path:
        """Return the output path for today's digest."""
        filename = self.digest_date.strftime("paypal-digest-%Y-%m-%d.md")
        return self.digest_dir / filename


def load_config() -> Config:
    """Load configuration from environment variables and defaults."""

    newsapi_key = os.getenv("NEWSAPI_KEY")
    config = Config(newsapi_key=newsapi_key)

    # Ensure directories exist when configuration is loaded.
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.digest_dir.mkdir(parents=True, exist_ok=True)

    return config
