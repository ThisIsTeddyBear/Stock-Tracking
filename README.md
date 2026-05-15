# Stock Tracking

General stock tracking repository. Local tool - no cloud, no auth.

## Setup

```bash
# Activate the venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies (already done if you ran setup)
pip install -r requirements.txt

# Run
python app.py
```

Open: http://127.0.0.1:5000

## Files

| File | Purpose |
|------|---------|
| `app.py` | Flask backend, all API routes |
| `database.py` | SQLite setup, CRUD helpers |
| `price_fetcher.py` | yfinance price fetching |
| `requirements.txt` | Python dependencies |
| `stocks.db` | SQLite database (auto-created) |
| `templates/index.html` | Single-page frontend |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recommendations` | List all |
| POST | `/api/recommendations` | Create new |
| PUT | `/api/recommendations/<id>` | Update |
| DELETE | `/api/recommendations/<id>` | Delete |
| GET | `/api/prices?symbols=TCS.NS,INFY.NS` | Fetch prices |

## Notes

- Prices labeled "Latest Available Price" — not real-time
- yfinance uses NSE suffix `.NS`, BSE suffix `.BO` (auto-derived from ticker + exchange)
- Sample data (TCS, HDFC Bank, Infosys) seeded on first run if DB is empty

