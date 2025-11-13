"""Utilities for retrieving article bodies when available."""

from __future__ import annotations

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .models import Article

LOGGER = logging.getLogger(__name__)


def enrich_article_content(article: Article, timeout: int = 10) -> Article:
    """Attempt to populate the article's content by scraping the linked page.

    If scraping fails the original article is returned unchanged.
    """

    if article.content:
        return article

    try:
        response = requests.get(article.url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.debug("Unable to fetch article body for %s: %s", article.url, exc)
        return article

    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = [p.get_text(strip=True) for p in soup.select("p") if p.get_text(strip=True)]
    if not paragraphs:
        return article

    max_chars = 2000
    text = "\n\n".join(paragraphs)
    if len(text) > max_chars:
        text = text[:max_chars]
    article.content = text
    return article


def best_text(article: Article) -> Optional[str]:
    """Return the most suitable text for summarization."""

    enriched = enrich_article_content(article)
    return enriched.primary_text()
