from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""


@dataclass
class InsiderTransaction:
    name: str
    role: str
    transaction_type: str   # "buy" | "sell"
    shares: float           # float: RSU/awards can be fractional
    price_per_share: float
    total_value: float
    date: datetime


@dataclass
class PriceData:
    ticker: str
    price: float
    currency: str
    exchange: str
    asset_type: str         # "stock" | "etf" | "forex" | "crypto"
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    market_cap: Optional[float] = None
    name: str = ""
    stale: bool = False
    last_updated: Optional[datetime] = None


@dataclass
class NewsData:
    ticker: str
    articles: list[NewsArticle] = field(default_factory=list)
    stale: bool = False
    last_updated: Optional[datetime] = None


@dataclass
class InsiderData:
    ticker: str
    transactions: list[InsiderTransaction] = field(default_factory=list)
    buy_sell_ratio: float = 0.0
    cluster_signal: bool = False    # True if >= 2 distinct insiders buy within 30 days
    stale: bool = False
    last_updated: Optional[datetime] = None
