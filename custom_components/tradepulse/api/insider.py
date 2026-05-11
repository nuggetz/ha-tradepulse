import logging
from datetime import datetime, timedelta, timezone

import aiohttp

from ..const import INSIDER_SUPPORTED_ASSET_TYPES
from ..models import InsiderData, InsiderTransaction

_LOGGER = logging.getLogger(__name__)

_OPENINSIDER_CSV_URL = (
    "https://openinsider.com/screener"
    "?s={ticker}&fd=-90&td=0&sortcol=0&cnt=100&action=1&csv=1"
)
_FINNHUB_INSIDER_URL  = "https://finnhub.io/api/v1/stock/insider-transactions"
_FINNHUB_PROFILE_URL  = "https://finnhub.io/api/v1/stock/profile2"
_EDGAR_SEARCH_URL     = (
    "https://efts.sec.gov/LATEST/search-index"
    "?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={from_date}&enddt={to_date}"
)

_EDGAR_HEADERS = {
    "User-Agent": "TradePulse HomeAssistant integration ha-tradepulse@example.com",
    "Accept-Encoding": "gzip, deflate",
}

_TIMEOUT = aiohttp.ClientTimeout(total=15)


class InsiderClient:
    def __init__(
        self, session: aiohttp.ClientSession, finnhub_key: str | None = None
    ) -> None:
        self._session = session
        self._finnhub_key = finnhub_key

    async def get_insider(self, ticker: str, asset_type: str) -> InsiderData:
        if asset_type not in INSIDER_SUPPORTED_ASSET_TYPES:
            return InsiderData(
                ticker=ticker,
                transactions=[],
                last_updated=datetime.now(timezone.utc),
            )

        sources: list[list[InsiderTransaction]] = []

        try:
            primary = await self._fetch_securitiesdb(ticker)
            sources.append(primary)
        except Exception as exc:
            _LOGGER.warning("OpenInsider fetch failed for %s: %s", ticker, exc)
            try:
                edgar = await self._fetch_sec_edgar(ticker)
                sources.append(edgar)
            except Exception as exc2:
                _LOGGER.warning("SEC EDGAR fallback failed for %s: %s", ticker, exc2)

        if self._finnhub_key:
            try:
                finnhub = await self._fetch_finnhub_insider(ticker)
                sources.append(finnhub)
            except Exception as exc:
                _LOGGER.warning("Finnhub insider failed for %s: %s", ticker, exc)
        else:
            _LOGGER.debug(
                "No Finnhub key — EU/UK PDMR insider data unavailable for %s", ticker
            )

        if not sources:
            _LOGGER.warning(
                "All insider sources failed for %s, returning stale", ticker
            )
            return InsiderData(
                ticker=ticker, stale=True, last_updated=datetime.now(timezone.utc)
            )

        transactions = _merge_transactions(sources)
        return InsiderData(
            ticker=ticker,
            transactions=transactions,
            buy_sell_ratio=self._compute_buy_sell_ratio(transactions),
            cluster_signal=self._compute_cluster_signal(transactions),
            stale=False,
            last_updated=datetime.now(timezone.utc),
        )

    async def _fetch_securitiesdb(self, ticker: str) -> list[InsiderTransaction]:
        url = _OPENINSIDER_CSV_URL.format(ticker=ticker)
        async with self._session.get(url, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            text = await resp.text()
        return _parse_openinsider_csv(text)

    async def _fetch_sec_edgar(self, ticker: str) -> list[InsiderTransaction]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = _EDGAR_SEARCH_URL.format(
            ticker=ticker, from_date=cutoff, to_date=today
        )
        async with self._session.get(url, headers=_EDGAR_HEADERS, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            data = await resp.json()

        transactions: list[InsiderTransaction] = []
        for hit in data.get("hits", {}).get("hits", []):
            try:
                src = hit.get("_source", {})
                date_str = src.get("file_date", "")[:10]
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                names = src.get("display_names", ["Unknown"])
                transactions.append(
                    InsiderTransaction(
                        name=names[0] if names else "Unknown",
                        role="",
                        transaction_type="buy",
                        shares=0.0,
                        price_per_share=0.0,
                        total_value=0.0,
                        date=date,
                    )
                )
            except (KeyError, IndexError, ValueError):
                continue
        return transactions

    async def _fetch_finnhub_insider(self, ticker: str) -> list[InsiderTransaction]:
        async with self._session.get(
            _FINNHUB_INSIDER_URL,
            params={"symbol": ticker, "token": self._finnhub_key},
            timeout=_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        transactions: list[InsiderTransaction] = []
        for item in data.get("data", []):
            try:
                change = float(item.get("change", 0))
                shares = abs(change)
                price = float(item.get("transactionPrice", 0))
                date = datetime.strptime(
                    item["filingDate"][:10], "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
                transactions.append(
                    InsiderTransaction(
                        name=item.get("name", ""),
                        role=item.get("officerTitle", ""),
                        transaction_type="buy" if change > 0 else "sell",
                        shares=shares,
                        price_per_share=price,
                        total_value=shares * price,
                        date=date,
                    )
                )
            except (KeyError, ValueError):
                continue
        return transactions

    async def validate_finnhub_key(self, key: str) -> bool:
        try:
            async with self._session.get(
                _FINNHUB_PROFILE_URL,
                params={"symbol": "AAPL", "token": key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _compute_cluster_signal(
        self, transactions: list[InsiderTransaction]
    ) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        buyers = {
            t.name
            for t in transactions
            if t.transaction_type == "buy" and t.date >= cutoff
        }
        return len(buyers) >= 2

    def _compute_buy_sell_ratio(
        self, transactions: list[InsiderTransaction], days: int = 90
    ) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [t for t in transactions if t.date >= cutoff]
        shares_buy = sum(t.shares for t in recent if t.transaction_type == "buy")
        shares_sell = sum(t.shares for t in recent if t.transaction_type == "sell")
        return shares_buy / max(shares_sell, 1)


def _parse_openinsider_csv(text: str) -> list[InsiderTransaction]:
    import csv
    import io

    transactions: list[InsiderTransaction] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        try:
            raw_type = row.get("Transaction", "").strip()
            transaction_type = "buy" if "Purchase" in raw_type else "sell"
            shares = abs(float(row.get("Qty", "0").replace(",", "") or 0))
            price = float(row.get("Price", "0").replace(",", "") or 0)
            date_str = (row.get("Filing Date") or row.get("Trade Date") or "")[:10]
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            transactions.append(
                InsiderTransaction(
                    name=(row.get("Insider Name") or "").strip(),
                    role=(row.get("Title") or "").strip(),
                    transaction_type=transaction_type,
                    shares=shares,
                    price_per_share=price,
                    total_value=shares * price,
                    date=date,
                )
            )
        except (ValueError, KeyError):
            continue
    return transactions


def _merge_transactions(
    sources: list[list[InsiderTransaction]],
) -> list[InsiderTransaction]:
    seen: set[tuple] = set()
    merged: list[InsiderTransaction] = []
    for source in sources:
        for t in source:
            key = (t.name, t.date.date(), t.transaction_type, t.shares)
            if key not in seen:
                seen.add(key)
                merged.append(t)
    return sorted(merged, key=lambda t: t.date, reverse=True)
