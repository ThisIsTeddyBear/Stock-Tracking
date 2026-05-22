# Stock Tracking

A local stock recommendation tracking dashboard for Indian equities (NSE/BSE). Track your picks, monitor real-time prices, and measure P&L — all without accounts, cloud sync, or subscriptions.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-2.3+-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)

---

## Features

- **Multi-watchlist support** — organize stocks into tabs (e.g. "Short Term", "Long Term", "Options")
- **Real-time prices** — fetches live prices from Yahoo Finance via yfinance
- **P&L tracking** — calculates absolute and percentage gain/loss against your entry price
- **3 price targets + stop loss** — track which levels have been hit
- **Historical price lookup** — fetch the closing price on your recommendation date
- **Search & filter** — by ticker, name, or status (Active / Watching / Exited / Stopped Out)
- **Multi-column sort** — sort by name, ticker, date, price, gain, or status
- **Statistics panel** — see how many picks hit Target 1 vs Stop Loss per tab
- **15-minute price cache** — avoids hammering Yahoo Finance on every refresh
- **100% local** — data lives in a local SQLite file; no account required beyond price fetches

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite 3 |
| Price data | yfinance (Yahoo Finance) |
| Frontend | Vanilla JS, HTML5, CSS (dark theme) |

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/Stock-Tracking.git
cd Stock-Tracking

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open your browser and go to **http://127.0.0.1:5000**

The SQLite database (`stocks.db`) is created automatically on first run with a few sample stocks (TCS, HDFC Bank, Infosys) so you can explore the UI right away.

---

## Usage

### Adding a Stock

Click **+ Add Stock** to open the form. Fill in:

- **Stock Name** — e.g. "Reliance Industries"
- **Ticker** — NSE or BSE symbol (e.g. `RELIANCE`, `HDFCBANK`)
- **Exchange** — NSE or BSE
- **Recommendation Date** — optionally fetches the historical closing price for that date
- **Entry Price** — your buy price
- **Targets** — up to 3 price targets
- **Stop Loss** — your risk level
- **Status** — Active / Watching / Exited / Stopped Out
- **Notes** — optional free-text

### Watchlists (Tabs)

- Click **+ New Tab** to create a watchlist
- Double-click a tab name to rename it
- The **×** on a tab deletes it and all its stocks (at least one tab must remain)

### Refreshing Prices

Click **Refresh Prices** to fetch current prices for all visible stocks. Prices are cached for 15 minutes. Displayed values are the latest available price from Yahoo Finance, not a real-time stream.

### Search & Filter

Use the search bar to filter by name or ticker. Use the status dropdown to show only Active, Watching, Exited, or Stopped Out picks.

---

## Project Structure

```
Stock-Tracking/
├── app.py              # Flask app — all API routes
├── database.py         # SQLite schema and CRUD helpers
├── price_fetcher.py    # Yahoo Finance integration + 15-min cache
├── templates/
│   └── index.html      # Single-page frontend (HTML + CSS + JS)
├── tests/
│   └── test_watchlists.py
├── requirements.txt
└── stocks.db           # Auto-created on first run (gitignored)
```

---

## API Reference

### Watchlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watchlists` | List all watchlists |
| `GET` | `/api/watchlists?include_stocks=1` | List watchlists with their stocks |
| `POST` | `/api/watchlists` | Create a watchlist |
| `PUT` | `/api/watchlists/<id>` | Rename a watchlist |
| `DELETE` | `/api/watchlists/<id>` | Delete a watchlist (cascades to stocks) |

### Recommendations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/recommendations` | List all recommendations |
| `GET` | `/api/recommendations?watchlist_id=<id>` | Filter by watchlist |
| `POST` | `/api/recommendations` | Add a recommendation |
| `PUT` | `/api/recommendations/<id>` | Update a recommendation |
| `DELETE` | `/api/recommendations/<id>` | Delete a recommendation |

### Prices

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/prices?symbols=TCS.NS,INFY.NS` | Fetch current prices |
| `GET` | `/api/historical_price?symbol=TCS.NS&date=2024-01-15` | Fetch closing price on a past date |
| `GET` | `/api/search_stocks?q=reliance` | Search stocks on Yahoo Finance |

---

## Ticker Symbols

Yahoo Finance appends a suffix to Indian stock tickers:

| Exchange | Suffix | Example |
|----------|--------|---------|
| NSE | `.NS` | `RELIANCE.NS` |
| BSE | `.BO` | `RELIANCE.BO` |

The app derives the correct suffix automatically based on the exchange you select.

---

## Running Tests

```bash
python -m pytest tests/
```

Tests cover watchlist CRUD, recommendation filtering, duplicate handling, cascade deletion, and legacy database migration.

---

## Known Limitations

- **Indian equities only** — optimized for NSE/BSE symbols; other exchanges are untested
- **yfinance availability** — price data depends on Yahoo Finance's unofficial API; occasional failures can occur during market hours or under rate limiting
- **Single user** — no authentication or multi-user support; intended as a personal local tool
- **No price history** — only the latest fetched price is stored per session; no charting

---

## Contributing

Pull requests are welcome. For larger changes, open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a PR
