# TradePulse

[![Validate](https://github.com/nuggetz/ha-tradepulse/actions/workflows/validate.yml/badge.svg)](https://github.com/nuggetz/ha-tradepulse/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant custom component that transforms financial assets — stocks, ETFs, forex, crypto — into native HA sensor entities ready for dashboards and automations.

**Data provided per ticker:**
- **Price sensor** — current price, open/high/low/close, volume, change %, market cap
- **News sensor** — aggregated articles from Yahoo Finance, Google News (+ Finnhub if key provided)
- **Insider sensor** — insider transactions, buy/sell ratio, cluster signal (stocks only)

No API key required for basic operation. A free [Finnhub](https://finnhub.io) key unlocks EU/UK insider (PDMR) data and additional news sources.

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add `https://github.com/nuggetz/ha-tradepulse` with category **Integration**
4. Search for **TradePulse** and install it
5. Restart Home Assistant

### Manual

1. Download the latest release from the [Releases page](https://github.com/nuggetz/ha-tradepulse/releases)
2. Copy `custom_components/tradepulse/` into your HA `config/custom_components/` directory
3. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **TradePulse**
3. Enter one or more ticker symbols (e.g. `TSLA, AAPL, BTC-USD, EURUSD=X, VWCE.DE`)
4. Click **Submit** — symbols are validated in real time

### Options (post-setup)

Go to the integration card → **Configure** to:

- **Manage symbols** — add or remove tracked tickers
- **Advanced options** — adjust update intervals and news language
- **API keys** — add a Finnhub key for EU insider data and extra news

---

## Entities

| Ticker | Entity | Description |
|--------|--------|-------------|
| `TSLA` | `sensor.tradepulse_tsla_price` | Current price in USD |
| `TSLA` | `sensor.tradepulse_tsla_news` | Article count (articles in attributes) |
| `TSLA` | `sensor.tradepulse_tsla_insider` | Transactions in last 90 days |
| `BTC-USD` | `sensor.tradepulse_btc_usd_price` | Bitcoin price |
| `EURUSD=X` | `sensor.tradepulse_eurusd_x_price` | EUR/USD rate |

---

## Requirements

- Home Assistant **2024.2.0** or newer
- Python **3.11+**

---

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest tests/ -v
```

---

## License

[MIT](LICENSE)
