"""News source fetchers for PayPal coverage."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser

from .config import Config
from .models import Article

LOGGER = logging.getLogger(__name__)


class NewsFetcher:
    """Abstract base class for source-specific fetchers."""

    name: str = "base"

    def fetch(self, config: Config) -> List[Article]:
        raise NotImplementedError

    @staticmethod
    def _canonical_id(*parts: str) -> str:
        digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
        return digest


class NewsAPIFetcher(NewsFetcher):
    name = "newsapi"

    API_URL = "https://newsapi.org/v2/everything"

    def fetch(self, config: Config) -> List[Article]:
        if not config.newsapi_key:
            LOGGER.warning("Skipping NewsAPI fetcher – NEWSAPI_KEY not configured.")
            return []

        params = {
            "q": config.query,
            "language": config.language,
            "pageSize": config.max_articles,
            "sortBy": "publishedAt",
        }
        headers = {"Authorization": config.newsapi_key}
        try:
            response = requests.get(self.API_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.error("NewsAPI request failed: %s", exc)
            return []

        payload = response.json()
        articles = []
        for item in payload.get("articles", []):
            title = item.get("title")
            url = item.get("url")
            if not title or not url:
                continue
            content = item.get("content")
            summary = item.get("description")
            published_at = self._parse_datetime(item.get("publishedAt"))
            article = Article(
                title=title,
                url=url,
                source=item.get("source", {}).get("name", "NewsAPI"),
                published_at=published_at,
                summary=summary,
                content=content,
                author=item.get("author"),
                id=self._canonical_id(self.name, url),
            )
            articles.append(article)
        LOGGER.info("Fetched %d articles from NewsAPI", len(articles))
        return articles

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return date_parser.parse(value)
        except (ValueError, TypeError, OverflowError):
            return None


class GoogleNewsFetcher(NewsFetcher):
    name = "google_news"

    RSS_URL = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=PayPal"

    def fetch(self, config: Config) -> List[Article]:
        try:
            response = requests.get(self.RSS_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.error("Google News RSS request failed: %s", exc)
            return []

        feed = feedparser.parse(response.content)
        articles: List[Article] = []
        for entry in feed.entries:
            title = entry.get("title")
            link = entry.get("link")
            if not title or not link:
                continue
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
            published_at = None
            if "published" in entry:
                published_at = NewsAPIFetcher._parse_datetime(entry.get("published"))
            article = Article(
                title=title,
                url=link,
                source=entry.get("source", {}).get("title", "Google News"),
                published_at=published_at,
                summary=summary,
                content=None,
                id=self._canonical_id(self.name, link),
            )
            articles.append(article)
        LOGGER.info("Fetched %d articles from Google News RSS", len(articles))
        return articles


class PYMNTSFetcher(NewsFetcher):
    """Scrape recent PayPal-related posts from PYMNTS.com."""

    name = "pymnts"
    SOURCE_URL = "https://www.pymnts.com/company/paypal/"

    def fetch(self, config: Config) -> List[Article]:
        try:
            response = requests.get(self.SOURCE_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.error("PYMNTS request failed: %s", exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        articles: List[Article] = []
        for card in soup.select("article.post"):
            header = card.select_one("h2.entry-title a")
            if not header:
                continue
            title = header.get_text(strip=True)
            link = header.get("href")
            if not title or not link:
                continue
            summary_elem = card.select_one("div.entry-excerpt p")
            summary = summary_elem.get_text(strip=True) if summary_elem else None
            date_elem = card.select_one("time")
            published_at = None
            if date_elem and date_elem.has_attr("datetime"):
                published_at = NewsAPIFetcher._parse_datetime(date_elem["datetime"])
            article = Article(
                title=title,
                url=link,
                source="PYMNTS",
                published_at=published_at,
                summary=summary,
                content=None,
                id=self._canonical_id(self.name, link),
            )
            articles.append(article)
        LOGGER.info("Fetched %d articles from PYMNTS", len(articles))
        return articles


def collect_articles(config: Config, fetchers: Optional[Iterable[NewsFetcher]] = None) -> List[Article]:
    """Collect articles from all configured fetchers."""

    fetchers = list(fetchers or [NewsAPIFetcher(), GoogleNewsFetcher(), PYMNTSFetcher()])
    aggregated: List[Article] = []
    seen_ids = set()

    for fetcher in fetchers:
        try:
            items = fetcher.fetch(config)
        except Exception as exc:  # pragma: no cover - guard clause
            LOGGER.exception("Fetcher %s failed unexpectedly: %s", fetcher.name, exc)
            continue
        for article in items:
            if article.id in seen_ids:
                LOGGER.debug("Skipping duplicate article: %s", article.url)
                continue
            if not _is_relevant(article):
                LOGGER.debug("Filtered out non-relevant article: %s", article.title)
                continue
            seen_ids.add(article.id)
            aggregated.append(article)

    LOGGER.info("Collected %d unique articles", len(aggregated))
    return aggregated


def _is_relevant(article: Article) -> bool:
    text = f"{article.title} {article.summary or ''}".lower()
    keywords = ["paypal", "pypl"]
    return any(keyword in text for keyword in keywords)
