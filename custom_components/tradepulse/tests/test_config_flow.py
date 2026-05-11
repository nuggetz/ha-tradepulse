from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.tradepulse.config_flow import TradePulseConfigFlow
from custom_components.tradepulse.const import CONF_SYMBOLS, DOMAIN


_VALID_META = {
    "asset_type": "stock",
    "exchange": "NMS",
    "currency": "USD",
    "name": "Tesla, Inc.",
}


@pytest.fixture
def flow(hass):
    f = TradePulseConfigFlow()
    f.hass = hass
    return f


@pytest.mark.asyncio
async def test_step_user_single_valid_symbol():
    flow = TradePulseConfigFlow()
    flow.hass = AsyncMock()
    flow._async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = AsyncMock()
    flow.async_set_unique_id = AsyncMock()

    with patch(
        "custom_components.tradepulse.config_flow._validate_symbols",
        AsyncMock(return_value=({"TSLA": _VALID_META}, [])),
    ):
        result = await flow.async_step_user({"symbols": "TSLA"})

    assert result["type"] == "create_entry"
    assert result["data"][CONF_SYMBOLS]["TSLA"] == _VALID_META


@pytest.mark.asyncio
async def test_step_user_invalid_symbol():
    flow = TradePulseConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.tradepulse.config_flow._validate_symbols",
        AsyncMock(return_value=({}, ["FAKEXYZ"])),
    ):
        result = await flow.async_step_user({"symbols": "FAKEXYZ"})

    assert result["type"] == "form"
    assert result["errors"].get(CONF_SYMBOLS) == "invalid_symbols"


@pytest.mark.asyncio
async def test_step_user_mixed_symbols():
    flow = TradePulseConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.tradepulse.config_flow._validate_symbols",
        AsyncMock(return_value=({"TSLA": _VALID_META, "AAPL": _VALID_META}, ["FAKEXYZ"])),
    ):
        result = await flow.async_step_user({"symbols": "TSLA, AAPL, FAKEXYZ"})

    assert result["type"] == "form"
    assert "FAKEXYZ" in result["errors"].get("invalid_list", "")


@pytest.mark.asyncio
async def test_options_flow_news_count():
    from custom_components.tradepulse.config_flow import TradePulseOptionsFlow
    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.data = {CONF_SYMBOLS: {"TSLA": _VALID_META}}
    entry.options = {}

    flow = TradePulseOptionsFlow(entry)
    flow.hass = AsyncMock()

    result = await flow.async_step_options(
        {
            "news_count": 20,
            "scan_interval": 10,
            "news_interval": 60,
            "language": "en",
        }
    )
    assert result["type"] == "create_entry"
    assert result["data"]["news_count"] == 20


@pytest.mark.asyncio
async def test_options_flow_api_key_valid():
    from custom_components.tradepulse.config_flow import TradePulseOptionsFlow
    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.options = {}

    flow = TradePulseOptionsFlow(entry)
    flow.hass = AsyncMock()

    with patch(
        "custom_components.tradepulse.config_flow.InsiderClient"
    ) as MockClient:
        instance = MockClient.return_value
        instance.validate_finnhub_key = AsyncMock(return_value=True)
        result = await flow.async_step_api_keys({"finnhub_api_key": "valid_key_123"})

    assert result["type"] == "create_entry"
    assert result["data"].get("finnhub_api_key") == "valid_key_123"


@pytest.mark.asyncio
async def test_options_flow_api_key_invalid():
    from custom_components.tradepulse.config_flow import TradePulseOptionsFlow
    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.options = {}

    flow = TradePulseOptionsFlow(entry)
    flow.hass = AsyncMock()

    with patch(
        "custom_components.tradepulse.config_flow.InsiderClient"
    ) as MockClient:
        instance = MockClient.return_value
        instance.validate_finnhub_key = AsyncMock(return_value=False)
        result = await flow.async_step_api_keys({"finnhub_api_key": "bad_key"})

    assert result["type"] == "form"
    assert result["errors"].get("finnhub_api_key") == "invalid_finnhub_key"
    assert "finnhub_api_key" not in result.get("data", {})
