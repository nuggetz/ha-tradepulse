from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.tradepulse.coordinator import (
    InsiderCoordinator,
    NewsCoordinator,
    PriceCoordinator,
)
from custom_components.tradepulse.models import InsiderData, NewsData, PriceData


_NOW = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)


def _make_price(ticker: str = "TSLA", stale: bool = False) -> PriceData:
    return PriceData(
        ticker=ticker,
        price=250.0,
        currency="USD",
        exchange="NMS",
        asset_type="stock",
        stale=stale,
        last_updated=_NOW,
    )


@pytest.fixture
def hass():
    h = MagicMock()
    h.loop = MagicMock()
    return h


@pytest.fixture
def entry():
    e = MagicMock()
    e.data = {"symbols": {"TSLA": {"asset_type": "stock"}, "AAPL": {"asset_type": "stock"}}}
    e.options = {}
    return e


@pytest.mark.asyncio
async def test_price_coordinator_fetch_ok(hass, entry, mock_price_client):
    async def _get_price(ticker):
        return _make_price(ticker)

    mock_price_client.get_price.side_effect = _get_price
    coord = PriceCoordinator(hass, entry, mock_price_client, ["TSLA", "AAPL"])
    coord.data = {}

    result = await coord._async_update_data()

    assert "TSLA" in result
    assert "AAPL" in result
    assert result["TSLA"].stale is False


@pytest.mark.asyncio
async def test_price_coordinator_stale_on_provider_down(hass, entry, mock_price_client):
    cached = _make_price("TSLA")
    mock_price_client.get_price.side_effect = Exception("Provider down")
    coord = PriceCoordinator(hass, entry, mock_price_client, ["TSLA"])
    coord._cache = {"TSLA": cached}

    result = await coord._async_update_data()

    assert result["TSLA"].stale is True


@pytest.mark.asyncio
async def test_price_coordinator_one_of_three_fails(hass, entry, mock_price_client):
    async def side_effect(ticker):
        if ticker == "FAIL":
            raise Exception("Down")
        return _make_price(ticker)

    mock_price_client.get_price.side_effect = side_effect
    coord = PriceCoordinator(hass, entry, mock_price_client, ["TSLA", "FAIL", "AAPL"])
    coord._cache = {"FAIL": _make_price("FAIL")}

    result = await coord._async_update_data()

    assert result["TSLA"].stale is False
    assert result["FAIL"].stale is True
    assert result["AAPL"].stale is False


@pytest.mark.asyncio
async def test_news_coordinator_merge(hass, entry, mock_news_client):
    coord = NewsCoordinator(hass, entry, mock_news_client, ["TSLA"])
    result = await coord._async_update_data()
    assert "TSLA" in result
    assert not result["TSLA"].stale


@pytest.mark.asyncio
async def test_insider_coordinator_skip_crypto(hass, entry, mock_insider_client):
    ticker_meta = {
        "TSLA": {"asset_type": "stock"},
        "BTC-USD": {"asset_type": "crypto"},
    }
    coord = InsiderCoordinator(
        hass, entry, mock_insider_client, ["TSLA", "BTC-USD"], ticker_meta
    )
    result = await coord._async_update_data()
    assert "TSLA" in result
    assert "BTC-USD" not in result


@pytest.mark.asyncio
async def test_insider_coordinator_skip_forex(hass, entry, mock_insider_client):
    ticker_meta = {"EURUSD=X": {"asset_type": "forex"}}
    coord = InsiderCoordinator(
        hass, entry, mock_insider_client, ["EURUSD=X"], ticker_meta
    )
    result = await coord._async_update_data()
    assert "EURUSD=X" not in result
