import datetime
import yfinance as yf


def fetch_price(yf_symbol: str) -> dict:
    fetched_at = datetime.datetime.utcnow().isoformat()
    result = {"symbol": yf_symbol, "price": None, "fetched_at": fetched_at, "error": None}

    try:
        ticker = yf.Ticker(yf_symbol)

        # Primary: fast_info
        try:
            info = ticker.fast_info
            price = getattr(info, "last_price", None)
            if price is None:
                price = getattr(info, "regularMarketPrice", None)
            if price is not None and float(price) > 0:
                result["price"] = float(price)
                return result
        except Exception:
            pass

        # Fallback: recent history
        hist = ticker.history(period="2d")
        if hist.empty or "Close" not in hist.columns:
            result["error"] = "No price data returned by yfinance"
            return result

        price = float(hist["Close"].iloc[-1])
        if price <= 0:
            result["error"] = "Price data is zero or negative"
            return result

        result["price"] = price

    except Exception as exc:
        result["error"] = str(exc)

    return result
