from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.tradepulse.api.price import PriceClient
from custom_components.tradepulse.const import (
    ASSET_TYPE_CRYPTO,
    ASSET_TYPE_ETF,
    ASSET_TYPE_FOREX,
    ASSET_TYPE_STOCK,
)


@pytest.fixture
def client():
    return PriceClient()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "quote_type, expected",
    [
        ("EQUITY", ASSET_TYPE_STOCK),
        ("ETF", ASSET_TYPE_ETF),
        ("CURRENCY", ASSET_TYPE_FOREX),
        ("CRYPTOCURRENCY", ASSET_TYPE_CRYPTO),
    ],
)
async def test_validate_symbol_asset_type_detection(client, quote_type, expected):
    fake_info = {
        "quoteType": quote_type,
        "exchange": "NMS",
        "currency": "USD",
        "shortName": "Test Asset",
    }
    with patch.object(client, "_fetch_yfinance", AsyncMock(return_value=fake_info)):
        result = await client.validate_symbol("TEST")
    assert result["asset_type"] == expected


@pytest.mark.asyncio
async def test_validate_symbol_invalid(client):
    with patch.object(client, "_fetch_yfinance", AsyncMock(return_value={})):
        with pytest.raises(ValueError, match="Symbol not found"):
            await client.validate_symbol("FAKEXYZ")


@pytest.mark.asyncio
async def test_validate_symbol_timeout(client):
    async def _slow(*_):
        await asyncio.sleep(20)
        return {}

    with patch.object(client, "_fetch_yfinance", _slow):
        with pytest.raises(ValueError, match="Timeout"):
            await client.validate_symbol("SLOW")


@pytest.mark.asyncio
async def test_get_price_full_data(client):
    fake_info = {
        "quoteType": "EQUITY",
        "currentPrice": 250.5,
        "currency": "USD",
        "exchange": "NMS",
        "shortName": "Tesla, Inc.",
        "open": 248.0,
        "dayHigh": 252.0,
        "dayLow": 247.0,
        "previousClose": 249.0,
        "volume": 1_000_000,
        "regularMarketChange": 1.5,
        "regularMarketChangePercent": 0.6,
        "marketCap": 800_000_000_000,
    }
    with patch.object(client, "_fetch_yfinance", AsyncMock(return_value=fake_info)):
        data = await client.get_price("TSLA")

    assert data.price == 250.5
    assert data.currency == "USD"
    assert data.asset_type == ASSET_TYPE_STOCK
    assert data.high == 252.0
    assert data.stale is False


@pytest.mark.asyncio
async def test_get_price_optional_fields_none(client):
    fake_info = {
        "quoteType": "EQUITY",
        "currentPrice": 100.0,
        "currency": "USD",
        "exchange": "NMS",
        "shortName": "Minimal Corp",
    }
    with patch.object(client, "_fetch_yfinance", AsyncMock(return_value=fake_info)):
        data = await client.get_price("MIN")

    assert data.open is None
    assert data.high is None
    assert data.market_cap is None
