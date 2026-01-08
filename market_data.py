import yfinance as yf


class MarketDataError(Exception):
    pass


def get_price(symbol: str) -> float:
    try:
        t = yf.Ticker(symbol)

        fast = t.fast_info or {}
        if fast.get("last_price") is not None:
            return float(fast["last_price"])

        info = t.info or {}
        if info.get("regularMarketPrice") is not None:
            return float(info["regularMarketPrice"])

        raise MarketDataError(f"No live price available for {symbol}")

    except Exception as e:
        raise MarketDataError(f"Failed to fetch price for {symbol}: {e}")



def get_currency(symbol: str) -> str:
    """
    Get the trading currency for a ticker (e.g. USD).
    """
    try:
        ticker = yf.Ticker(symbol)
        currency = ticker.fast_info.get("currency")

        if currency is None:
            raise MarketDataError(f"No currency info for {symbol}")

        return currency

    except Exception as e:
        raise MarketDataError(f"Failed to fetch currency for {symbol}: {e}")


def get_fx_rate(from_currency: str, to_currency: str) -> float:
    """
    Get FX rate using Yahoo Finance.
    Returns: units of `to_currency` per 1 `from_currency`
    Example: USD -> EUR returns ~0.92
    """
    #move both to upper case
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return 1.0

    pair = f"{from_currency}{to_currency}=X"

    try:
        ticker = yf.Ticker(pair)

        # 1️⃣ Try fast_info
        fast = ticker.fast_info
        if fast and fast.get("last_price") is not None:
            return float(fast["last_price"])

        # 2️⃣ Fallback: info
        info = ticker.info
        rate = info.get("regularMarketPrice")
        if rate is not None:
            return float(rate)

        # 3️⃣ Last resort: daily close
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])

        raise MarketDataError(f"No FX data available for {pair}")

    except Exception as e:
        raise MarketDataError(
            f"Failed to fetch FX rate {from_currency}->{to_currency}: {e}"
        )



def is_etf(symbol: str) -> bool:
    t = yf.Ticker(symbol)
    info = t.get_info()
    return info.get("quoteType") == "ETF"

