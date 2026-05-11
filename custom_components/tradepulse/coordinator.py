import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api.insider import InsiderClient
from .api.news import NewsClient
from .api.price import PriceClient
from .const import (
    CONF_LANGUAGE,
    CONF_NEWS_COUNT,
    CONF_NEWS_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_SYMBOLS,
    DEFAULT_INSIDER_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_NEWS_COUNT,
    DEFAULT_NEWS_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    INSIDER_SUPPORTED_ASSET_TYPES,
)
from .models import InsiderData, NewsData, PriceData

_LOGGER = logging.getLogger(__name__)


def _symbols(entry: ConfigEntry) -> dict[str, dict]:
    return entry.options.get(CONF_SYMBOLS) or entry.data.get(CONF_SYMBOLS, {})


class PriceCoordinator(DataUpdateCoordinator[dict[str, PriceData]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: PriceClient,
        tickers: list[str],
    ) -> None:
        interval = int(
            entry.options.get(CONF_SCAN_INTERVAL)
            or entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name="TradePulse Price",
            update_interval=timedelta(minutes=interval),
        )
        self._client = client
        self._tickers = tickers
        self._cache: dict[str, PriceData] = {}

    async def _async_update_data(self) -> dict[str, PriceData]:
        results: dict[str, PriceData] = {}
        for ticker in self._tickers:
            try:
                data = await self._client.get_price(ticker)
                self._cache[ticker] = data
                results[ticker] = data
            except Exception as exc:
                _LOGGER.warning("Price fetch failed for %s: %s", ticker, exc)
                if ticker in self._cache:
                    results[ticker] = replace(self._cache[ticker], stale=True)
        return results


class NewsCoordinator(DataUpdateCoordinator[dict[str, NewsData]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: NewsClient,
        tickers: list[str],
    ) -> None:
        interval = int(
            entry.options.get(CONF_NEWS_INTERVAL)
            or entry.data.get(CONF_NEWS_INTERVAL, DEFAULT_NEWS_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name="TradePulse News",
            update_interval=timedelta(minutes=interval),
        )
        self._client = client
        self._tickers = tickers
        self._language: str = entry.options.get(CONF_LANGUAGE) or entry.data.get(
            CONF_LANGUAGE, DEFAULT_LANGUAGE
        )
        self._news_count: int = int(
            entry.options.get(CONF_NEWS_COUNT)
            or entry.data.get(CONF_NEWS_COUNT, DEFAULT_NEWS_COUNT)
        )
        self._cache: dict[str, NewsData] = {}

    async def _async_update_data(self) -> dict[str, NewsData]:
        results: dict[str, NewsData] = {}
        for ticker in self._tickers:
            try:
                data = await self._client.get_news(
                    ticker, self._language, self._news_count
                )
                self._cache[ticker] = data
                results[ticker] = data
            except Exception as exc:
                _LOGGER.warning("News fetch failed for %s: %s", ticker, exc)
                if ticker in self._cache:
                    results[ticker] = replace(self._cache[ticker], stale=True)
        return results


class InsiderCoordinator(DataUpdateCoordinator[dict[str, InsiderData]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: InsiderClient,
        tickers: list[str],
        ticker_meta: dict[str, dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="TradePulse Insider",
            update_interval=timedelta(hours=DEFAULT_INSIDER_INTERVAL),
        )
        self._client = client
        self._tickers = tickers
        self._ticker_meta = ticker_meta
        self._cache: dict[str, InsiderData] = {}

    async def _async_update_data(self) -> dict[str, InsiderData]:
        results: dict[str, InsiderData] = {}
        for ticker in self._tickers:
            asset_type = self._ticker_meta.get(ticker, {}).get("asset_type", "")
            if asset_type not in INSIDER_SUPPORTED_ASSET_TYPES:
                _LOGGER.debug(
                    "Skipping insider for %s (asset_type=%s)", ticker, asset_type
                )
                continue
            try:
                data = await self._client.get_insider(ticker, asset_type)
                self._cache[ticker] = data
                results[ticker] = data
            except Exception as exc:
                _LOGGER.warning("Insider fetch failed for %s: %s", ticker, exc)
                if ticker in self._cache:
                    results[ticker] = replace(self._cache[ticker], stale=True)
        return results
