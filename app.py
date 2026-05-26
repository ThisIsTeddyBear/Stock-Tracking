import requests as req_lib
from flask import Flask, render_template, request, jsonify
import database as db
from price_fetcher import fetch_prices_batch

app = Flask(__name__)


def derive_yf_symbol(ticker: str, exchange: str) -> str:
    t = ticker.strip().upper()
    if exchange.upper() == "BSE":
        return f"{t}.BO"
    return f"{t}.NS"


def normalize_tab_name(raw_name) -> str:
    name = (raw_name or "").strip()
    if not name:
        raise ValueError("Tab name is required")
    if len(name) > 60:
        raise ValueError("Tab name must be 60 characters or less")
    return name


def resolve_watchlist_id(raw_watchlist_id=None) -> int:
    tabs = db.get_tabs()
    if not tabs:
        raise ValueError("No tabs available")

    if raw_watchlist_id is None or raw_watchlist_id == "":
        return tabs[0]["id"]

    try:
        watchlist_id = int(raw_watchlist_id)
    except (TypeError, ValueError):
        raise ValueError("watchlist_id must be a valid integer")

    if not db.get_tab(watchlist_id):
        raise ValueError("Tab not found")
    return watchlist_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    try:
        raw_watchlist_id = request.args.get("watchlist_id")
        if raw_watchlist_id is None:
            return jsonify(db.get_all())

        watchlist_id = resolve_watchlist_id(raw_watchlist_id)
        return jsonify(db.get_all(watchlist_id=watchlist_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/recommendations", methods=["POST"])
def create_recommendation():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        required = ["stock_name", "ticker", "exchange", "entry_price"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        watchlist_id = resolve_watchlist_id(data.get("watchlist_id"))
        ticker = data["ticker"].strip().upper()
        exchange = data["exchange"].strip().upper()

        if db.stock_exists_in_tab(watchlist_id, ticker, exchange):
            return jsonify({"error": "This stock already exists in the selected tab"}), 409

        record = {
            "stock_name": data["stock_name"].strip(),
            "ticker": ticker,
            "exchange": exchange,
            "yf_symbol": derive_yf_symbol(ticker, exchange),
            "watchlist_id": watchlist_id,
            "rec_date": data.get("rec_date") or None,
            "entry_price": float(data["entry_price"]),
            "target1": float(data["target1"]) if data.get("target1") else None,
            "target2": float(data["target2"]) if data.get("target2") else None,
            "target3": float(data["target3"]) if data.get("target3") else None,
            "stop_loss": float(data["stop_loss"]) if data.get("stop_loss") else None,
            "notes": data.get("notes") or None,
            "status": data.get("status", "Active"),
        }

        new_rec = db.insert(record)
        return jsonify(new_rec), 201

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except TypeError as exc:
        return jsonify({"error": f"Invalid data: {exc}"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/recommendations/<int:rec_id>", methods=["PUT"])
def update_recommendation(rec_id):
    try:
        existing = db.get_by_id(rec_id)
        if not existing:
            return jsonify({"error": "Recommendation not found"}), 404

        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Re-derive yf_symbol if ticker or exchange changed
        ticker = data.get("ticker", existing["ticker"])
        exchange = data.get("exchange", existing["exchange"])
        data["ticker"] = ticker.strip().upper()
        data["exchange"] = exchange.strip().upper()
        data["yf_symbol"] = derive_yf_symbol(ticker, exchange)

        if "stock_name" in data and data["stock_name"] is not None:
            data["stock_name"] = data["stock_name"].strip()

        if "watchlist_id" in data:
            data["watchlist_id"] = resolve_watchlist_id(data.get("watchlist_id"))
        else:
            data["watchlist_id"] = existing["watchlist_id"]

        if db.stock_exists_in_tab(
            data["watchlist_id"],
            data["ticker"],
            data["exchange"],
            exclude_rec_id=rec_id,
        ):
            return jsonify({"error": "This stock already exists in the selected tab"}), 409

        for field in ["entry_price", "target1", "target2", "target3", "stop_loss"]:
            if field in data and data[field] is not None and data[field] != "":
                data[field] = float(data[field])
            elif field in data and data[field] == "":
                data[field] = None

        updated = db.update(rec_id, data)
        return jsonify(updated)

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except TypeError as exc:
        return jsonify({"error": f"Invalid data: {exc}"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/recommendations/<int:rec_id>", methods=["DELETE"])
def delete_recommendation(rec_id):
    try:
        existing = db.get_by_id(rec_id)
        if not existing:
            return jsonify({"error": "Recommendation not found"}), 404

        raw_watchlist_id = request.args.get("watchlist_id")
        if raw_watchlist_id is not None:
            watchlist_id = resolve_watchlist_id(raw_watchlist_id)
            if existing["watchlist_id"] != watchlist_id:
                return jsonify({"error": "Recommendation not found in selected tab"}), 404

        db.delete(rec_id)
        return jsonify({"success": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/watchlists", methods=["GET"])
def list_watchlists():
    try:
        tabs = db.get_tabs()
        include_stocks = request.args.get("include_stocks") in {"1", "true", "True"}
        if not include_stocks:
            return jsonify(tabs)

        by_tab = {}
        for rec in db.get_all():
            by_tab.setdefault(rec["watchlist_id"], []).append(rec)

        enriched = []
        for tab in tabs:
            row = dict(tab)
            row["stocks"] = by_tab.get(tab["id"], [])
            enriched.append(row)
        return jsonify(enriched)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/watchlists", methods=["POST"])
def create_watchlist():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        name = normalize_tab_name(data.get("name"))
        if db.find_tab_by_name(name):
            return jsonify({"error": "A tab with this name already exists"}), 409

        tab = db.create_tab(name)
        return jsonify(tab), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/watchlists/<int:tab_id>", methods=["PUT"])
def rename_watchlist(tab_id):
    try:
        existing = db.get_tab(tab_id)
        if not existing:
            return jsonify({"error": "Tab not found"}), 404

        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        name = normalize_tab_name(data.get("name"))
        dup = db.find_tab_by_name(name)
        if dup and dup["id"] != tab_id:
            return jsonify({"error": "A tab with this name already exists"}), 409

        tab = db.rename_tab(tab_id, name)
        return jsonify(tab)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/watchlists/<int:tab_id>", methods=["DELETE"])
def delete_watchlist(tab_id):
    try:
        existing = db.get_tab(tab_id)
        if not existing:
            return jsonify({"error": "Tab not found"}), 404

        next_tab_id = db.delete_tab(tab_id)
        return jsonify({"success": True, "deleted_tab_id": tab_id, "next_tab_id": next_tab_id})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/prices", methods=["GET"])
def get_prices():
    try:
        symbols_param = request.args.get("symbols", "")
        if not symbols_param:
            return jsonify({"error": "symbols query parameter required"}), 400

        symbols = [s.strip() for s in symbols_param.split(",") if s.strip()]
        return jsonify(fetch_prices_batch(symbols))

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/historical_price", methods=["GET"])
def historical_price():
    try:
        symbol   = request.args.get("symbol", "").strip()
        date_str = request.args.get("date", "").strip()
        if not symbol or not date_str:
            return jsonify({"price": None, "actual_date": None, "error": "symbol and date are required"}), 400

        from datetime import datetime, timedelta
        import yfinance as yf

        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if target_date >= today:
            return jsonify({"price": None, "actual_date": None, "error": "Date is not in the past"})

        start = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
        end   = (target_date + timedelta(days=3)).strftime("%Y-%m-%d")

        ticker = yf.Ticker(symbol)
        hist   = ticker.history(start=start, end=end)

        if hist.empty:
            return jsonify({"price": None, "actual_date": None, "error": "No data found for this date range"})

        # strip timezone if present
        try:
            hist.index = hist.index.tz_localize(None)
        except TypeError:
            pass

        available = hist[hist.index.date <= target_date.date()]
        if available.empty:
            available = hist

        closest_row = available.iloc[-1]
        actual_date = available.index[-1].strftime("%Y-%m-%d")
        closing_price = round(float(closest_row["Close"]), 2)

        return jsonify({"price": closing_price, "actual_date": actual_date, "error": None})

    except Exception as exc:
        return jsonify({"price": None, "actual_date": None, "error": str(exc)})


@app.route("/api/search_stocks", methods=["GET"])
def search_stocks():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify([])

        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": query,
            "newsCount": 0,
            "enableFuzzyQuery": False,
            "enableEnhancedTrivialQuery": True,
            "quotesCount": 8,
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = req_lib.get(url, params=params, headers=headers, timeout=5)
        data = resp.json()

        results = []
        for item in data.get("quotes", []):
            if item.get("quoteType") != "EQUITY":
                continue
            sym = item.get("symbol", "")
            exch = item.get("exchange", "")
            is_nse = sym.endswith(".NS") or exch in ["NSI", "NSE"]
            is_bse = sym.endswith(".BO") or exch in ["BOM", "BSE"]
            if not (is_nse or is_bse):
                continue

            if sym.endswith(".NS"):
                ticker = sym[:-3]
                exchange = "NSE"
            elif sym.endswith(".BO"):
                ticker = sym[:-3]
                exchange = "BSE"
            else:
                ticker = sym
                exchange = "NSE" if is_nse else "BSE"

            results.append({
                "symbol": sym,
                "ticker": ticker,
                "name": item.get("longname") or item.get("shortname") or ticker,
                "exchange": exchange,
                "exchange_display": exchange,
            })
            if len(results) >= 8:
                break

        return jsonify(results)
    except Exception:
        return jsonify([])


if __name__ == "__main__":
    db.init_db()
    print("Stock Tracking running at: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)

