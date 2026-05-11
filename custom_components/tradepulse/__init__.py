from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.insider import InsiderClient
from .api.news import NewsClient
from .api.price import PriceClient
from .const import CONF_FINNHUB_API_KEY, CONF_SYMBOLS
from .coordinator import InsiderCoordinator, NewsCoordinator, PriceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


@dataclass
class TradePulseRuntimeData:
    price_coordinator: PriceCoordinator
    news_coordinator: NewsCoordinator
    insider_coordinator: InsiderCoordinator
    price_client: PriceClient
    news_client: NewsClient
    insider_client: InsiderClient


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    # Bug fix: API key set via OptionsFlow lives in entry.options, not entry.data
    finnhub_key: str | None = entry.options.get(CONF_FINNHUB_API_KEY)

    symbols: dict[str, dict] = (
        entry.options.get(CONF_SYMBOLS) or entry.data.get(CONF_SYMBOLS, {})
    )
    tickers = list(symbols.keys())

    price_client = PriceClient()
    news_client = NewsClient(session, finnhub_key)
    insider_client = InsiderClient(session, finnhub_key)

    price_coordinator = PriceCoordinator(hass, entry, price_client, tickers)
    news_coordinator = NewsCoordinator(hass, entry, news_client, tickers)
    insider_coordinator = InsiderCoordinator(
        hass, entry, insider_client, tickers, symbols
    )

    # Price blocks setup — HA retries automatically via ConfigEntryNotReady
    await price_coordinator.async_config_entry_first_refresh()

    # News and insider are non-blocking; entities are stale until first update completes
    await news_coordinator.async_refresh()
    await insider_coordinator.async_refresh()

    entry.runtime_data = TradePulseRuntimeData(
        price_coordinator=price_coordinator,
        news_coordinator=news_coordinator,
        insider_coordinator=insider_coordinator,
        price_client=price_client,
        news_client=news_client,
        insider_client=insider_client,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
