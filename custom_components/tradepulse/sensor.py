from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TradePulseRuntimeData
from .const import CONF_SYMBOLS, DOMAIN, INSIDER_SUPPORTED_ASSET_TYPES
from .coordinator import InsiderCoordinator, NewsCoordinator, PriceCoordinator
from .models import InsiderTransaction, NewsArticle

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: TradePulseRuntimeData = entry.runtime_data
    symbols: dict[str, dict] = (
        entry.options.get(CONF_SYMBOLS) or entry.data.get(CONF_SYMBOLS, {})
    )

    entities: list[SensorEntity] = []
    for ticker, meta in symbols.items():
        entities.append(
            TradePulsePriceSensor(ticker, meta, runtime.price_coordinator)
        )
        entities.append(
            TradePulseNewsSensor(ticker, meta, runtime.news_coordinator)
        )
        if meta.get("asset_type") in INSIDER_SUPPORTED_ASSET_TYPES:
            entities.append(
                TradePulseInsiderSensor(ticker, meta, runtime.insider_coordinator)
            )

    async_add_entities(entities)


def _device_info(ticker: str, meta: dict) -> DeviceInfo:
    name = meta.get("name") or ticker
    return DeviceInfo(
        identifiers={(DOMAIN, ticker)},
        name=name,
        manufacturer="TradePulse",
        model=meta.get("asset_type", "").upper(),
        configuration_url=f"https://finance.yahoo.com/quote/{ticker}",
    )


def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class TradePulsePriceSensor(CoordinatorEntity[PriceCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(
        self, ticker: str, meta: dict, coordinator: PriceCoordinator
    ) -> None:
        super().__init__(coordinator)
        self._ticker = ticker
        self._meta = meta
        self._attr_unique_id = f"tradepulse_{normalize_ticker(ticker)}_price"
        self._attr_name = "Price"
        self._attr_device_info = _device_info(ticker, meta)

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        return data.price if data else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        return data.currency if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        if not data:
            return {}
        return {
            "open": data.open,
            "high": data.high,
            "low": data.low,
            "close": data.close,
            "volume": data.volume,
            "change": data.change,
            "change_pct": data.change_pct,
            "market_cap": data.market_cap,
            "currency": data.currency,
            "exchange": data.exchange,
            "asset_type": data.asset_type,
            "stale": data.stale,
            "last_updated": _fmt_dt(data.last_updated),
        }


class TradePulseNewsSensor(CoordinatorEntity[NewsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, ticker: str, meta: dict, coordinator: NewsCoordinator
    ) -> None:
        super().__init__(coordinator)
        self._ticker = ticker
        self._meta = meta
        self._attr_unique_id = f"tradepulse_{normalize_ticker(ticker)}_news"
        self._attr_name = "News"
        self._attr_icon = "mdi:newspaper"
        self._attr_device_info = _device_info(ticker, meta)

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        return len(data.articles) if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        if not data:
            return {}
        return {
            "articles": [_serialize_article(a) for a in data.articles],
            "stale": data.stale,
            "last_updated": _fmt_dt(data.last_updated),
        }


class TradePulseInsiderSensor(CoordinatorEntity[InsiderCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, ticker: str, meta: dict, coordinator: InsiderCoordinator
    ) -> None:
        super().__init__(coordinator)
        self._ticker = ticker
        self._meta = meta
        self._attr_unique_id = f"tradepulse_{normalize_ticker(ticker)}_insider"
        self._attr_name = "Insider"
        self._attr_icon = "mdi:account-tie"
        self._attr_device_info = _device_info(ticker, meta)

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        if data is None:
            return None
        from datetime import timedelta, timezone
        from datetime import datetime as _dt
        cutoff = _dt.now(timezone.utc) - timedelta(days=90)
        return sum(1 for t in data.transactions if t.date >= cutoff)

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data.get(self._ticker) if self.coordinator.data else None
        if not data:
            return {}
        return {
            "transactions": [_serialize_transaction(t) for t in data.transactions],
            "buy_sell_ratio": data.buy_sell_ratio,
            "cluster_signal": data.cluster_signal,
            "stale": data.stale,
            "last_updated": _fmt_dt(data.last_updated),
        }


def normalize_ticker(ticker: str) -> str:
    """TSLA→tsla  BTC-USD→btc_usd  VWCE.DE→vwce_de  EURUSD=X→eurusd_x"""
    return ticker.lower().replace("-", "_").replace(".", "_").replace("=", "_")


def _serialize_article(article: NewsArticle) -> dict:
    return {
        "title": article.title,
        "url": article.url,
        "source": article.source,
        "published_at": article.published_at.isoformat(),
        "summary": article.summary,
    }


def _serialize_transaction(t: InsiderTransaction) -> dict:
    return {
        "name": t.name,
        "role": t.role,
        "transaction_type": t.transaction_type,
        "shares": t.shares,
        "price_per_share": t.price_per_share,
        "total_value": t.total_value,
        "date": t.date.isoformat(),
    }
