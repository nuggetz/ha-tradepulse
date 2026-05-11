DOMAIN = "tradepulse"

CONF_SYMBOLS          = "symbols"
CONF_FINNHUB_API_KEY  = "finnhub_api_key"
CONF_NEWS_COUNT       = "news_count"
CONF_SCAN_INTERVAL    = "scan_interval"
CONF_NEWS_INTERVAL    = "news_interval"
CONF_LANGUAGE         = "language"

DEFAULT_NEWS_COUNT       = 10
DEFAULT_SCAN_INTERVAL    = 5     # minutes
DEFAULT_NEWS_INTERVAL    = 30    # minutes
DEFAULT_INSIDER_INTERVAL = 6     # hours
DEFAULT_LANGUAGE         = "en"

ASSET_TYPE_STOCK  = "stock"
ASSET_TYPE_ETF    = "etf"
ASSET_TYPE_FOREX  = "forex"
ASSET_TYPE_CRYPTO = "crypto"

INSIDER_SUPPORTED_ASSET_TYPES = {ASSET_TYPE_STOCK}

FINNHUB_FREE_RATE_LIMIT   = 60   # req/min
COINGECKO_FREE_RATE_LIMIT = 30   # req/min
SEC_EDGAR_RATE_LIMIT      = 10   # req/sec

SENSOR_TYPE_PRICE   = "price"
SENSOR_TYPE_NEWS    = "news"
SENSOR_TYPE_INSIDER = "insider"
