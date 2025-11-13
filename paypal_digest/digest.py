"""High-level orchestration for building the PayPal daily digest."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .config import Config, load_config
from .content import best_text
from .fetchers import collect_articles
from .state import StateStore
from .summarizer import summarize_text

LOGGER = logging.getLogger(__name__)


@dataclass
class DigestItem:
    title: str
    source: str
    url: str
    published_at: datetime | None
    summary: str


@dataclass
class Digest:
    created_at: datetime
    items: List[DigestItem]

    def to_markdown(self) -> str:
        lines = [f"# PayPal Daily Digest — {self.created_at.strftime('%Y-%m-%d')}", ""]
        for item in self.items:
            published = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "Unknown"
            lines.append(f"## {item.title}")
            lines.append(f"*Source:* {item.source} — *Published:* {published}")
            lines.append("")
            lines.append(item.summary.strip())
            lines.append("")
            lines.append(f"[Read more]({item.url})")
            lines.append("")
        return "\n".join(lines).strip() + "\n"


@dataclass
class DigestResult:
    digest: Digest
    new_article_ids: List[str]


def build_digest(config: Config) -> DigestResult:
    LOGGER.info("Starting digest build")
    state = StateStore(config.state_file)
    articles = collect_articles(config)

    fresh_articles = [article for article in articles if article.id not in state.seen_ids]
    fresh_articles.sort(key=lambda art: art.published_at or datetime.min, reverse=True)
    LOGGER.info("Processing %d new articles (skipped %d duplicates)", len(fresh_articles), len(articles) - len(fresh_articles))

    digest_items: List[DigestItem] = []
    processed_ids: List[str] = []

    for article in fresh_articles:
        text = best_text(article)
        if not text:
            LOGGER.debug("Skipping article with no text: %s", article.url)
            continue
        summary = summarize_text(text)
        digest_items.append(
            DigestItem(
                title=article.title,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                summary=summary,
            )
        )
        processed_ids.append(article.id)

    digest = Digest(created_at=config.digest_date, items=digest_items)

    for article_id in processed_ids:
        matching = next((a for a in fresh_articles if a.id == article_id), None)
        state.mark_seen(article_id, matching.title if matching else "")
    state.save()

    LOGGER.info("Digest built with %d items", len(digest_items))
    return DigestResult(digest=digest, new_article_ids=processed_ids)


def write_digest(digest: Digest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(digest.to_markdown(), encoding="utf-8")
    LOGGER.info("Digest written to %s", path)


def run(config: Config | None = None) -> DigestResult:
    config = config or load_config()
    result = build_digest(config)
    if result.digest.items:
        write_digest(result.digest, config.digest_path)
        print(result.digest.to_markdown())
    else:
        LOGGER.warning("No digest items produced for %s", config.digest_date.strftime("%Y-%m-%d"))
    return result


__all__ = [
    "Digest",
    "DigestItem",
    "DigestResult",
    "build_digest",
    "run",
    "write_digest",
]
