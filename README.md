# TradePulse

Track stocks, ETFs, forex, and crypto directly in Home Assistant — price, news, and insider trading as native sensor entities, ready for dashboards and automations.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/github/license/nuggetz/ha-tradepulse)](LICENSE)
[![Release](https://img.shields.io/github/v/release/nuggetz/ha-tradepulse?display_name=tag)](https://github.com/nuggetz/ha-tradepulse/releases)
[![Validate](https://github.com/nuggetz/ha-tradepulse/actions/workflows/validate.yml/badge.svg)](https://github.com/nuggetz/ha-tradepulse/actions/workflows/validate.yml)
[![Issues](https://img.shields.io/github/issues/nuggetz/ha-tradepulse)](https://github.com/nuggetz/ha-tradepulse/issues)
[![Last commit](https://img.shields.io/github/last-commit/nuggetz/ha-tradepulse)](https://github.com/nuggetz/ha-tradepulse/commits/main)

---

## Features

| Module | Description | Free | Finnhub key |
| ------ | ----------- | :----: | :-----------: |
| **Price** | Real-time price, OHLC, volume, change %, market cap | ✅ | — |
| **News** | Aggregated articles from Yahoo Finance + Google News | ✅ | +1 extra source |
| **Insider** | US insider transactions, buy/sell ratio, cluster signal | ✅ | EU/UK (PDMR) data |

No API key is required for full US market coverage. A free [Finnhub](https://finnhub.io) key unlocks EU/UK insider data and additional news articles.

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant sidebar
2. Go to **Integrations** → click the **⋮** menu → **Custom repositories**
3. Paste `https://github.com/nuggetz/ha-tradepulse` and select category **Integration**
4. Click **Add** → find **TradePulse** in the list and install it
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration**
7. Search for **TradePulse** and follow the setup wizard

> **Tip:** After setup, click **Configure** on the integration card to add/remove tickers, adjust update intervals, or add a Finnhub key — no restart needed.

### Manual

1. Download the [latest release](https://github.com/nuggetz/ha-tradepulse/releases/latest)
2. Extract and copy `custom_components/tradepulse/` into your HA `config/custom_components/` directory
3. Restart Home Assistant and proceed from step 6 above

**Minimum requirement:** Home Assistant 2024.2.0

---

## Entities

Each tracked ticker creates a HA **device** (named after the asset) with up to three sensors. Entity IDs follow the pattern `sensor.{asset_name}_{type}` — check **Settings → Devices** to see the exact IDs in your instance. The `unique_id` used internally follows `tradepulse_{normalized_ticker}_{type}`.

### Price sensor

**State:** current price (`float`) in the asset's native currency.

| Attribute | Type | Description |
|-----------|------|-------------|
| `open` | `float \| null` | Opening price of the current session |
| `high` | `float \| null` | Intraday high |
| `low` | `float \| null` | Intraday low |
| `close` | `float \| null` | Previous close |
| `volume` | `int \| null` | Trading volume |
| `change` | `float \| null` | Absolute price change |
| `change_pct` | `float \| null` | Percentage change |
| `market_cap` | `float \| null` | Market capitalisation |
| `currency` | `string` | ISO 4217 currency code (e.g. `USD`, `EUR`) |
| `exchange` | `string` | Exchange code (e.g. `NMS`, `XETRA`) |
| `asset_type` | `string` | `stock` · `etf` · `forex` · `crypto` |
| `stale` | `bool` | `true` if the last fetch failed — previous value is retained |
| `last_updated` | `ISO 8601` | Timestamp of the last successful update |

### News sensor

**State:** number of articles currently loaded (`int`). Full content is in attributes.

| Attribute | Type | Description |
|-----------|------|-------------|
| `articles` | `list[object]` | List of articles — see structure below |
| `stale` | `bool` | `true` if all news sources failed |
| `last_updated` | `ISO 8601` | Timestamp of the last successful update |

Each article object:

```json
{
  "title": "Tesla beats Q1 estimates",
  "url": "https://finance.yahoo.com/news/...",
  "source": "Yahoo Finance",
  "published_at": "2026-05-11T10:00:00+00:00",
  "summary": "Tesla reported earnings above analyst expectations..."
}
```

### Insider sensor

**State:** number of insider transactions in the last 90 days (`int`). Only created for stocks — not for ETF, forex, or crypto.

| Attribute | Type | Description |
|-----------|------|-------------|
| `transactions` | `list[object]` | List of transactions — see structure below |
| `buy_sell_ratio` | `float` | `shares_bought / shares_sold` in the last 90 days |
| `cluster_signal` | `bool` | `true` if ≥ 2 distinct insiders bought within the last 30 days |
| `stale` | `bool` | `true` if all data sources failed |
| `last_updated` | `ISO 8601` | Timestamp of the last successful update |

Each transaction object:

```json
{
  "name": "Elon Musk",
  "role": "CEO",
  "transaction_type": "buy",
  "shares": 50000.0,
  "price_per_share": 185.50,
  "total_value": 9275000.0,
  "date": "2026-04-15T00:00:00+00:00"
}
```

> **EU/UK tickers:** insider data requires a Finnhub API key. Without it, the sensor is created but always shows `0` transactions (state=`0`), so automations that watch this sensor will not break.

### Entity reference table

| Ticker | Unique ID | Device Class | Update interval |
| ------ | --------- | :------------: | :---------------: |
| `TSLA` | `tradepulse_tsla_price` | Monetary | configurable (default 5 min) |
| `TSLA` | `tradepulse_tsla_news` | — | configurable (default 30 min) |
| `TSLA` | `tradepulse_tsla_insider` | — | 6 hours (fixed) |
| `BTC-USD` | `tradepulse_btc_usd_price` | Monetary | configurable |
| `BTC-USD` | `tradepulse_btc_usd_news` | — | configurable |
| `EURUSD=X` | `tradepulse_eurusd_x_price` | Monetary | configurable |
| `EURUSD=X` | `tradepulse_eurusd_x_news` | — | configurable |
| `VWCE.DE` | `tradepulse_vwce_de_price` | Monetary | configurable |
| `VWCE.DE` | `tradepulse_vwce_de_news` | — | configurable |

---

## Configuration

### Initial setup

Enter one or more ticker symbols separated by commas or newlines:

```
TSLA, AAPL, BTC-USD, EURUSD=X, VWCE.DE
```

Symbols are validated against Yahoo Finance in real time. Invalid symbols are listed inline — the form does not submit until all symbols are valid.

Supported formats:

| Asset type | Example symbols |
|------------|-----------------|
| Stock (US) | `TSLA`, `AAPL`, `MSFT` |
| Stock (EU) | `VWCE.DE`, `ENI.MI`, `AIR.PA` |
| ETF | `SPY`, `QQQ`, `VWCE.DE` |
| Forex | `EURUSD=X`, `GBPUSD=X` |
| Crypto | `BTC-USD`, `ETH-USD` |

### Options (post-setup)

Access via **Settings → Devices & Services → TradePulse → Configure**.

#### Manage symbols

| Field | Description |
|-------|-------------|
| Add symbols | Comma-separated list of new tickers to track |
| Remove symbols | Multi-select of currently tracked tickers to remove |

Changes take effect immediately after saving (integration reloads automatically).

#### Advanced options

| Field | Default | Range | Description |
|-------|---------|-------|-------------|
| Max articles per ticker | `10` | 5–50 | Number of news articles retained per ticker |
| Price update interval | `5` min | 1–60 min | How often price data is refreshed |
| News update interval | `30` min | 15–120 min | How often news is refreshed |
| News language | `en` | en/it/de/fr/es | Language used for Google News queries |

#### API keys

| Field | Required | Description |
|-------|----------|-------------|
| Finnhub API key | No | Enables EU/UK insider data (PDMR) and Finnhub news. Get a free key at [finnhub.io](https://finnhub.io) |

The key is validated before saving. If validation fails, the key is rejected and the field is shown empty — other options on the same page are not affected.

---

## Automation examples

### Alert when a stock hits a price target

```yaml
alias: "TSLA price alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.tesla_inc_price
    above: 300
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "📈 TSLA above $300"
      message: >
        Tesla is at {{ states('sensor.tesla_inc_price') }}
        {{ state_attr('sensor.tesla_inc_price', 'currency') }}
        ({{ state_attr('sensor.tesla_inc_price', 'change_pct') | round(2) }}% today)
```

### Alert when insider cluster signal triggers

```yaml
alias: "Insider cluster buy signal"
trigger:
  - platform: state
    entity_id: sensor.tesla_inc_insider
    attribute: cluster_signal
    to: true
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "🔔 TSLA insider cluster"
      message: >
        Multiple TSLA insiders bought in the last 30 days.
        Buy/sell ratio: {{ state_attr('sensor.tesla_inc_insider', 'buy_sell_ratio') | round(2) }}
```

### Daily news digest via notification

```yaml
alias: "Morning market digest"
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: template
    value_template: "{{ state_attr('sensor.tesla_inc_news', 'articles') | length > 0 }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "📰 TSLA news"
      message: >
        {% set articles = state_attr('sensor.tesla_inc_news', 'articles') %}
        {% for a in articles[:3] %}
        • {{ a.title }}
        {% endfor %}
```

### Mark data as stale in a dashboard

Use a template sensor or a conditional card in Lovelace:

```yaml
type: conditional
conditions:
  - entity: sensor.tesla_inc_price
    attribute: stale
    state: "true"
card:
  type: markdown
  content: "⚠️ Price data is stale — provider may be down."
```

---

## Graceful degradation

TradePulse is designed to never break your automations during outages:

| Scenario | Behaviour |
|----------|-----------|
| Price provider down at startup | `ConfigEntryNotReady` — HA retries automatically |
| Price provider down on update | Sensor retains last value, `stale: true` |
| One news source down | Remaining sources are used; warning in logs |
| All news sources down | Sensor retains last articles, `stale: true` |
| Insider source down | Sensor retains last transactions, `stale: true` |
| EU ticker without Finnhub key | Insider sensor created with `0` transactions |
| Invalid Finnhub key in options | Key rejected inline, other options still saved |

---

## Development

```bash
git clone https://github.com/nuggetz/ha-tradepulse.git
cd ha-tradepulse
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest tests/ -v
```

CI runs automatically on every push via GitHub Actions (hassfest + HACS validation + pytest).

---

## License

[MIT](LICENSE) © 2026 nuggetz
