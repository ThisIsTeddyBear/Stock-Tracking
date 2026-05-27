import datetime
import yfinance as yf


def fetch_prices_batch(symbols: list) -> dict:
    fetched_at = datetime.datetime.utcnow().isoformat()
    results = {s: {"symbol": s, "price": None, "fetched_at": fetched_at, "error": None} for s in symbols}

    if not symbols:
        return results

    try:
        data = yf.download(" ".join(symbols), period="2d", progress=False, auto_adjust=True)

        if data.empty:
            for s in symbols:
                results[s]["error"] = "No data returned"
            return results

        close = data["Close"]

        # yfinance returns a Series for a single ticker on older versions and a
        # single-column DataFrame on newer versions.  Normalise to DataFrame so
        # the loop below works identically for 1 or N symbols.
        if not hasattr(close, "columns"):
            close = close.to_frame(name=symbols[0])

        for sym in symbols:
            if sym not in close.columns:
                results[sym]["error"] = "Symbol not found"
                continue
            col = close[sym].dropna()
            if col.empty:
                results[sym]["error"] = "No price data"
                continue
            price = float(col.iloc[-1])
            if price > 0:
                results[sym]["price"] = round(price, 4)
            else:
                results[sym]["error"] = "Price is zero or negative"

    except Exception as exc:
        for s in symbols:
            if results[s]["price"] is None and results[s]["error"] is None:
                results[s]["error"] = str(exc)

    return results


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
