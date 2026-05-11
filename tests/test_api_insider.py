from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.tradepulse.api.insider import InsiderClient
from custom_components.tradepulse.models import InsiderData, InsiderTransaction


_NOW = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def client(session):
    return InsiderClient(session)


def _make_transaction(
    name: str = "John Doe",
    days_ago: int = 5,
    transaction_type: str = "buy",
    shares: float = 1000.0,
) -> InsiderTransaction:
    return InsiderTransaction(
        name=name,
        role="Director",
        transaction_type=transaction_type,
        shares=shares,
        price_per_share=100.0,
        total_value=shares * 100.0,
        date=_NOW - timedelta(days=days_ago),
    )


def test_compute_cluster_signal_true(client):
    transactions = [
        _make_transaction("Alice", days_ago=10),
        _make_transaction("Bob", days_ago=15),
    ]
    with patch("custom_components.tradepulse.api.insider.datetime") as mock_dt:
        mock_dt.now.return_value = _NOW
        result = client._compute_cluster_signal(transactions)
    assert result is True


def test_compute_cluster_signal_same_person(client):
    transactions = [
        _make_transaction("Alice", days_ago=5),
        _make_transaction("Alice", days_ago=10),
    ]
    with patch("custom_components.tradepulse.api.insider.datetime") as mock_dt:
        mock_dt.now.return_value = _NOW
        result = client._compute_cluster_signal(transactions)
    assert result is False


def test_compute_cluster_signal_outside_window(client):
    transactions = [
        _make_transaction("Alice", days_ago=35),
        _make_transaction("Bob", days_ago=40),
    ]
    with patch("custom_components.tradepulse.api.insider.datetime") as mock_dt:
        mock_dt.now.return_value = _NOW
        result = client._compute_cluster_signal(transactions)
    assert result is False


def test_compute_buy_sell_ratio_correct(client):
    transactions = [
        _make_transaction("Alice", shares=200.0, transaction_type="buy", days_ago=10),
        _make_transaction("Bob", shares=100.0, transaction_type="sell", days_ago=20),
    ]
    with patch("custom_components.tradepulse.api.insider.datetime") as mock_dt:
        mock_dt.now.return_value = _NOW
        ratio = client._compute_buy_sell_ratio(transactions)
    assert ratio == pytest.approx(2.0)


def test_compute_buy_sell_ratio_empty(client):
    with patch("custom_components.tradepulse.api.insider.datetime") as mock_dt:
        mock_dt.now.return_value = _NOW
        ratio = client._compute_buy_sell_ratio([])
    assert ratio == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_get_insider_unsupported_asset_type(client):
    result = await client.get_insider("BTC-USD", "crypto")
    assert isinstance(result, InsiderData)
    assert result.transactions == []
    assert result.stale is False


@pytest.mark.asyncio
async def test_get_insider_forex_returns_empty(client):
    result = await client.get_insider("EURUSD=X", "forex")
    assert isinstance(result, InsiderData)
    assert result.transactions == []


@pytest.mark.asyncio
async def test_get_insider_eu_no_key_logs_debug(client):
    with patch.object(client, "_fetch_securitiesdb", AsyncMock(return_value=[])):
        with patch.object(client, "_fetch_sec_edgar", AsyncMock(return_value=[])):
            result = await client.get_insider("VWCE.DE", "stock")
    assert isinstance(result, InsiderData)
