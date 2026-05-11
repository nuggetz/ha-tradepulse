import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from ..const import (
    ASSET_TYPE_CRYPTO,
    ASSET_TYPE_ETF,
    ASSET_TYPE_FOREX,
    ASSET_TYPE_STOCK,
)
from ..models import PriceData

_LOGGER = logging.getLogger(__name__)

_QUOTE_TYPE_MAP: dict[str, str] = {
    "EQUITY": ASSET_TYPE_STOCK,
    "ETF": ASSET_TYPE_ETF,
    "CURRENCY": ASSET_TYPE_FOREX,
    "CRYPTOCURRENCY": ASSET_TYPE_CRYPTO,
}


class PriceClient:
    async def get_price(self, ticker: str) -> PriceData:
        info = await self._fetch_yfinance(ticker)
        asset_type = _QUOTE_TYPE_MAP.get(info.get("quoteType", ""), ASSET_TYPE_STOCK)
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("navPrice")
            or 0.0
        )
        return PriceData(
            ticker=ticker,
            price=float(price),
            currency=info.get("currency", ""),
            exchange=info.get("exchange", ""),
            asset_type=asset_type,
            open=_optional_float(info.get("open") or info.get("regularMarketOpen")),
            high=_optional_float(info.get("dayHigh") or info.get("regularMarketDayHigh")),
            low=_optional_float(info.get("dayLow") or info.get("regularMarketDayLow")),
            close=_optional_float(
                info.get("previousClose") or info.get("regularMarketPreviousClose")
            ),
            volume=_optional_int(info.get("volume") or info.get("regularMarketVolume")),
            change=_optional_float(info.get("regularMarketChange")),
            change_pct=_optional_float(info.get("regularMarketChangePercent")),
            market_cap=_optional_float(info.get("marketCap")),
            name=info.get("shortName") or info.get("longName") or ticker,
            stale=False,
            last_updated=datetime.now(timezone.utc),
        )

    async def validate_symbol(self, ticker: str) -> dict:
        try:
            info = await asyncio.wait_for(self._fetch_yfinance(ticker), timeout=10.0)
        except asyncio.TimeoutError as exc:
            raise ValueError(f"Timeout validating {ticker}") from exc

        if not info or not info.get("quoteType"):
            raise ValueError(f"Symbol not found: {ticker}")

        asset_type = _QUOTE_TYPE_MAP.get(info.get("quoteType", ""), ASSET_TYPE_STOCK)
        return {
            "asset_type": asset_type,
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", ""),
            "name": info.get("shortName") or info.get("longName") or ticker,
        }

    async def _fetch_yfinance(self, ticker: str) -> dict:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: yf.Ticker(ticker).info)


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
