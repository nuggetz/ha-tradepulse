from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tradepulse.api.insider import InsiderClient
from custom_components.tradepulse.api.news import NewsClient
from custom_components.tradepulse.api.price import PriceClient
from custom_components.tradepulse.const import DOMAIN
from custom_components.tradepulse.models import (
    InsiderData,
    InsiderTransaction,
    NewsArticle,
    NewsData,
    PriceData,
)

_NOW = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

_TSLA_META = {
    "asset_type": "stock",
    "exchange": "NMS",
    "currency": "USD",
    "name": "Tesla, Inc.",
}

_BTC_META = {
    "asset_type": "crypto",
    "exchange": "CCC",
    "currency": "USD",
    "name": "Bitcoin",
}


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "symbols": {
                "TSLA": _TSLA_META,
                "BTC-USD": _BTC_META,
            }
        },
        options={},
        entry_id="test_entry_id",
        unique_id="tradepulse_main",
    )


@pytest.fixture
def mock_aiohttp_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_price_client() -> AsyncMock:
    client = AsyncMock(spec=PriceClient)
    client.get_price.return_value = PriceData(
        ticker="TSLA",
        price=250.0,
        currency="USD",
        exchange="NMS",
        asset_type="stock",
        name="Tesla, Inc.",
        last_updated=_NOW,
    )
    client.validate_symbol.return_value = _TSLA_META
    return client


@pytest.fixture
def mock_news_client() -> AsyncMock:
    client = AsyncMock(spec=NewsClient)
    client.get_news.return_value = NewsData(
        ticker="TSLA",
        articles=[
            NewsArticle(
                title="Tesla beats estimates",
                url="https://example.com/tsla-news",
                source="Yahoo Finance",
                published_at=_NOW,
                summary="Tesla reported strong Q1 results.",
            )
        ],
        last_updated=_NOW,
    )
    return client


@pytest.fixture
def mock_insider_client() -> AsyncMock:
    client = AsyncMock(spec=InsiderClient)
    client.get_insider.return_value = InsiderData(
        ticker="TSLA",
        transactions=[
            InsiderTransaction(
                name="Elon Musk",
                role="CEO",
                transaction_type="buy",
                shares=1000.0,
                price_per_share=200.0,
                total_value=200_000.0,
                date=_NOW,
            )
        ],
        buy_sell_ratio=1.0,
        cluster_signal=False,
        last_updated=_NOW,
    )
    return client
