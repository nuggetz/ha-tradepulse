import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from xml.etree import ElementTree

import aiohttp

from ..models import NewsArticle, NewsData

_LOGGER = logging.getLogger(__name__)

_YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
_GOOGLE_RSS_URL = (
    "https://news.google.com/rss/search"
    "?q={ticker}+stock&hl={lang}-{region}&gl={region}&ceid={region}:{lang}"
)
_FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"

_LANG_TO_REGION: dict[str, str] = {
    "en": "US",
    "it": "IT",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
}

_TRACKING_PARAMS = frozenset(
    {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
)

_TIMEOUT = aiohttp.ClientTimeout(total=15)


class NewsClient:
    def __init__(
        self, session: aiohttp.ClientSession, finnhub_key: str | None = None
    ) -> None:
        self._session = session
        self._finnhub_key = finnhub_key

    async def get_news(self, ticker: str, language: str, count: int) -> NewsData:
        tasks: list = [
            self._fetch_yahoo_rss(ticker),
            self._fetch_google_rss(ticker, language),
        ]
        if self._finnhub_key:
            tasks.append(self._fetch_finnhub(ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        sources: list[list[NewsArticle]] = []
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("News source failed for %s: %s", ticker, result)
            else:
                sources.append(result)

        if not sources:
            _LOGGER.error("All news sources failed for %s", ticker)
            return NewsData(ticker=ticker, stale=True, last_updated=datetime.now(timezone.utc))

        articles = self._merge_and_deduplicate(sources)[:count]
        return NewsData(
            ticker=ticker,
            articles=articles,
            stale=False,
            last_updated=datetime.now(timezone.utc),
        )

    async def _fetch_yahoo_rss(self, ticker: str) -> list[NewsArticle]:
        url = _YAHOO_RSS_URL.format(ticker=ticker)
        async with self._session.get(url, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            text = await resp.text()
        return _parse_rss(text, source="Yahoo Finance")

    async def _fetch_google_rss(self, ticker: str, language: str) -> list[NewsArticle]:
        region = _LANG_TO_REGION.get(language, "US")
        url = _GOOGLE_RSS_URL.format(ticker=ticker, lang=language, region=region)
        async with self._session.get(url, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            text = await resp.text()
        return _parse_rss(text, source="Google News")

    async def _fetch_finnhub(self, ticker: str) -> list[NewsArticle]:
        from datetime import date, timedelta

        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        async with self._session.get(
            _FINNHUB_NEWS_URL,
            params={
                "symbol": ticker,
                "from": from_date,
                "to": to_date,
                "token": self._finnhub_key,
            },
            timeout=_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        articles: list[NewsArticle] = []
        for item in data:
            try:
                articles.append(
                    NewsArticle(
                        title=item["headline"],
                        url=item["url"],
                        source=item.get("source", "Finnhub"),
                        published_at=datetime.fromtimestamp(
                            item["datetime"], tz=timezone.utc
                        ),
                        summary=item.get("summary", ""),
                    )
                )
            except (KeyError, ValueError, OSError):
                continue
        return articles

    def _merge_and_deduplicate(
        self, sources: list[list[NewsArticle]]
    ) -> list[NewsArticle]:
        seen: set[str] = set()
        merged: list[NewsArticle] = []
        for source in sources:
            for article in source:
                key = _normalize_url(article.url)
                if key not in seen:
                    seen.add(key)
                    merged.append(article)
        return sorted(merged, key=lambda a: a.published_at, reverse=True)


def _parse_rss(text: str, source: str) -> list[NewsArticle]:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid RSS XML from {source}") from exc

    articles: list[NewsArticle] = []
    for item in root.iter("item"):
        try:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            if not title or not link:
                continue

            try:
                published_at = parsedate_to_datetime(pub_date)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                published_at = datetime.now(timezone.utc)

            articles.append(
                NewsArticle(
                    title=title,
                    url=link,
                    source=source,
                    published_at=published_at,
                    summary=description,
                )
            )
        except Exception:
            continue
    return articles


def _normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url.lower())
        clean_params = {
            k: v
            for k, v in parse_qs(parsed.query).items()
            if k not in _TRACKING_PARAMS
        }
        cleaned = parsed._replace(query=urlencode(clean_params, doseq=True))
        return urlunparse(cleaned)
    except Exception:
        return url.lower()
