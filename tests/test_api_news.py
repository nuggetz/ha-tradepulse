from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from custom_components.tradepulse.api.news import NewsClient, _normalize_url, _parse_rss
from custom_components.tradepulse.models import NewsArticle


_VALID_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Stock hits record high</title>
      <link>https://example.com/article1</link>
      <pubDate>Mon, 11 May 2026 10:00:00 +0000</pubDate>
      <description>The stock reached a new high today.</description>
    </item>
    <item>
      <title>Analyst upgrades rating</title>
      <link>https://example.com/article2</link>
      <pubDate>Mon, 11 May 2026 08:00:00 +0000</pubDate>
      <description>Analyst raised target price.</description>
    </item>
  </channel>
</rss>"""

_EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Empty</title></channel></rss>"""


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def client(session):
    return NewsClient(session)


def test_parse_rss_valid():
    articles = _parse_rss(_VALID_RSS, source="Test")
    assert len(articles) == 2
    assert articles[0].title == "Stock hits record high"
    assert articles[0].source == "Test"
    assert isinstance(articles[0].published_at, datetime)


def test_parse_rss_empty_feed():
    articles = _parse_rss(_EMPTY_RSS, source="Test")
    assert articles == []


def test_parse_rss_invalid_xml():
    from custom_components.tradepulse.api.news import _parse_rss
    with pytest.raises(ValueError, match="Invalid RSS XML"):
        _parse_rss("not xml at all", source="Test")


def test_merge_and_deduplicate_cross_source(client):
    now = datetime.now(timezone.utc)
    a1 = NewsArticle("Title A", "https://example.com/a", "Yahoo", now, "")
    a2 = NewsArticle("Title A dup", "https://example.com/a?utm_source=tw", "Google", now, "")
    a3 = NewsArticle("Title B", "https://example.com/b", "Yahoo", now, "")

    result = client._merge_and_deduplicate([[a1, a3], [a2]])
    urls = [r.url for r in result]
    assert len(result) == 2
    assert "https://example.com/b" in urls


def test_merge_and_deduplicate_sort_by_date(client):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    old = NewsArticle("Old", "https://example.com/old", "Yahoo", now - timedelta(hours=2), "")
    new = NewsArticle("New", "https://example.com/new", "Yahoo", now, "")
    result = client._merge_and_deduplicate([[old, new]])
    assert result[0].title == "New"


@pytest.mark.asyncio
async def test_get_news_one_source_fails(session):
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = AsyncMock(return_value=_VALID_RSS)

    fail_resp = AsyncMock()
    fail_resp.__aenter__ = AsyncMock(return_value=fail_resp)
    fail_resp.__aexit__ = AsyncMock(return_value=False)
    fail_resp.raise_for_status = MagicMock(side_effect=Exception("503"))

    call_count = 0

    def side_effect(url, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp if call_count == 1 else fail_resp

    session.get = side_effect
    client = NewsClient(session)
    result = await client.get_news("TSLA", "en", 10)
    assert not result.stale
    assert len(result.articles) > 0


@pytest.mark.asyncio
async def test_get_news_all_sources_fail(session):
    fail_resp = AsyncMock()
    fail_resp.__aenter__ = AsyncMock(return_value=fail_resp)
    fail_resp.__aexit__ = AsyncMock(return_value=False)
    fail_resp.raise_for_status = MagicMock(side_effect=Exception("error"))

    session.get = MagicMock(return_value=fail_resp)
    client = NewsClient(session)
    result = await client.get_news("TSLA", "en", 10)
    assert result.stale is True
    assert result.articles == []
