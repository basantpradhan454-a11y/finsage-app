"""
FinSage Data Fetcher
Fetches real market data from yfinance (stocks) and CoinGecko (crypto/meme coins).
No API key required — 100% free.
"""

import yfinance as yf
import requests
import pandas as pd
import time
from datetime import datetime, timedelta


# ── CoinGecko coin ID mapping ─────────────────────────────────────────────────
COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
    "AVAX": "avalanche-2", "DOT": "polkadot", "MATIC": "matic-network",
    "LINK": "chainlink", "UNI": "uniswap", "LTC": "litecoin",
    "ATOM": "cosmos", "TRX": "tron", "TON": "the-open-network",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
    "FLOKI": "floki", "BONK": "bonk", "WIF": "dogwifcoin",
    "MEME": "memecoin-2", "TURBO": "turbo", "BRETT": "brett",
    "NEIRO": "neiro-on-eth",
}

MEME_COINS = {"DOGE","SHIB","PEPE","FLOKI","BONK","WIF","MEME","TURBO","BRETT","NEIRO"}


def fetch_stock_data(ticker: str) -> dict:
    """Fetch stock data from yfinance with robust fallbacks."""
    ticker = ticker.strip().upper()
    try:
        stock = yf.Ticker(ticker)

        # ── Fetch history first (more reliable than info) ──────────────────
        hist = None
        for period in ["1mo", "3mo", "6mo"]:
            try:
                h = stock.history(period=period)
                if not h.empty:
                    hist = h
                    break
                time.sleep(0.5)
            except Exception:
                time.sleep(1)

        if hist is None or hist.empty:
            return {"error": f"No price history found for '{ticker}'. Please verify the symbol (e.g. RELIANCE.NS for NSE India, AAPL for US)."}

        # Keep only last 30 days for chart
        hist_30 = hist.tail(30)

        # ── Get info with retry ────────────────────────────────────────────
        info = {}
        for attempt in range(3):
            try:
                info = stock.info or {}
                if info and len(info) > 5:
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)

        # ── Derive price from history if info missing ──────────────────────
        last_close = float(hist["Close"].iloc[-1])
        prev_close_hist = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close

        current_price = (
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            info.get("ask") or
            last_close
        )
        prev_close = (
            info.get("previousClose") or
            info.get("regularMarketPreviousClose") or
            prev_close_hist
        )

        # Ensure numeric
        try: current_price = float(current_price)
        except: current_price = last_close

        try: prev_close = float(prev_close)
        except: prev_close = prev_close_hist

        change_pct = 0.0
        if prev_close and prev_close > 0:
            change_pct = ((current_price - prev_close) / prev_close) * 100

        # ── Volatility from history ────────────────────────────────────────
        volatility = 0.0
        if len(hist) > 5:
            returns = hist["Close"].pct_change().dropna()
            volatility = float(returns.std() * (252 ** 0.5) * 100)

        # ── Fallback values ────────────────────────────────────────────────
        name = (
            info.get("longName") or
            info.get("shortName") or
            ticker
        )
        market_cap = info.get("marketCap") or 0
        currency = info.get("currency") or ("INR" if ticker.endswith(".NS") or ticker.endswith(".BO") else "USD")

        week_high = info.get("fiftyTwoWeekHigh") or float(hist["High"].max())
        week_low  = info.get("fiftyTwoWeekLow")  or float(hist["Low"].min())

        risk_score = calculate_risk_score(
            change_pct=change_pct,
            volatility=volatility,
            market_cap=market_cap,
            asset_type="stock"
        )

        return {
            "ticker": ticker,
            "name": name,
            "asset_type": "Stock",
            "exchange": info.get("exchange", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": round(current_price, 4),
            "currency": currency,
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 4),
            "open_price": info.get("open") or info.get("regularMarketOpen") or float(hist["Open"].iloc[-1]),
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh") or float(hist["High"].iloc[-1]),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow") or float(hist["Low"].iloc[-1]),
            "week_52_high": week_high,
            "week_52_low": week_low,
            "market_cap": market_cap,
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "volume": info.get("volume") or info.get("regularMarketVolume") or int(hist["Volume"].iloc[-1]),
            "avg_volume": info.get("averageVolume", 0),
            "beta": info.get("beta"),
            "volatility_annualized": round(volatility, 2),
            "risk_score": risk_score,
            "history": hist_30,
            "analyst_target": info.get("targetMeanPrice"),
            "recommendation": (info.get("recommendationKey") or "N/A").upper(),
        }

    except Exception as e:
        return {"error": f"Failed to fetch data for '{ticker}': {str(e)}. Try again or check the symbol."}


def fetch_crypto_data(symbol: str) -> dict:
    """Fetch crypto/meme coin data from CoinGecko (free, no key)."""
    try:
        symbol_upper = symbol.strip().upper()
        coin_id = COINGECKO_IDS.get(symbol_upper)

        if not coin_id:
            search_url = "https://api.coingecko.com/api/v3/search"
            search_resp = requests.get(search_url, params={"query": symbol}, timeout=12)
            if search_resp.status_code == 200:
                coins = search_resp.json().get("coins", [])
                if coins:
                    coin_id = coins[0]["id"]
                else:
                    return {"error": f"Coin '{symbol}' not found. Try BTC, ETH, DOGE, SHIB etc."}
            else:
                return {"error": f"CoinGecko search failed (HTTP {search_resp.status_code}). Try again."}

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            "localization": "false", "tickers": "false",
            "market_data": "true", "community_data": "false",
            "developer_data": "false",
        }
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 429:
            return {"error": "CoinGecko rate limit hit. Please wait 30 seconds and try again."}
        if resp.status_code != 200:
            return {"error": f"CoinGecko API error ({resp.status_code}). Please try again."}

        data = resp.json()
        mkt = data.get("market_data", {})

        current_price = mkt.get("current_price", {}).get("usd", 0) or 0
        change_24h    = mkt.get("price_change_percentage_24h", 0) or 0
        change_7d     = mkt.get("price_change_percentage_7d", 0) or 0
        change_30d    = mkt.get("price_change_percentage_30d", 0) or 0
        market_cap    = mkt.get("market_cap", {}).get("usd", 0) or 0
        volume_24h    = mkt.get("total_volume", {}).get("usd", 0) or 0
        volatility    = abs(change_30d) / 4 if change_30d else abs(change_24h) * 5

        risk_score = calculate_risk_score(
            change_pct=change_24h, volatility=volatility,
            market_cap=market_cap, asset_type="crypto"
        )

        # Historical chart
        history_df = pd.DataFrame()
        try:
            hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            hist_resp = requests.get(hist_url, params={"vs_currency": "usd", "days": "30"}, timeout=12)
            if hist_resp.status_code == 200:
                prices = hist_resp.json().get("prices", [])
                if prices:
                    history_df = pd.DataFrame(prices, columns=["timestamp", "Close"])
                    history_df["Date"] = pd.to_datetime(history_df["timestamp"], unit="ms")
                    history_df.set_index("Date", inplace=True)
                    history_df.drop("timestamp", axis=1, inplace=True)
        except Exception:
            pass

        asset_type = "Meme Coin" if symbol_upper in MEME_COINS else "Cryptocurrency"

        return {
            "ticker": symbol_upper,
            "coin_id": coin_id,
            "name": data.get("name", symbol_upper),
            "asset_type": asset_type,
            "symbol": data.get("symbol", "").upper(),
            "current_price": current_price,
            "currency": "USD",
            "change_pct": round(change_24h, 2),
            "change_7d": round(change_7d, 2),
            "change_30d": round(change_30d, 2),
            "market_cap": market_cap,
            "market_cap_rank": mkt.get("market_cap_rank"),
            "volume_24h": volume_24h,
            "high_24h": mkt.get("high_24h", {}).get("usd"),
            "low_24h": mkt.get("low_24h", {}).get("usd"),
            "ath": mkt.get("ath", {}).get("usd"),
            "ath_change_pct": mkt.get("ath_change_percentage", {}).get("usd"),
            "atl": mkt.get("atl", {}).get("usd"),
            "circulating_supply": mkt.get("circulating_supply"),
            "total_supply": mkt.get("total_supply"),
            "volatility_annualized": round(volatility, 2),
            "risk_score": risk_score,
            "history": history_df,
            "description": data.get("description", {}).get("en", "")[:500],
        }

    except Exception as e:
        return {"error": f"Error fetching crypto data: {str(e)}"}


def calculate_risk_score(change_pct: float, volatility: float, market_cap: float, asset_type: str) -> int:
    score = 5
    if volatility > 100:   score += 3
    elif volatility > 50:  score += 2
    elif volatility > 20:  score += 1
    elif volatility < 10:  score -= 1

    if abs(change_pct) > 20:   score += 2
    elif abs(change_pct) > 10: score += 1
    elif abs(change_pct) < 2:  score -= 1

    if market_cap > 100_000_000_000:   score -= 2
    elif market_cap > 10_000_000_000:  score -= 1
    elif market_cap < 1_000_000_000:   score += 1
    elif market_cap < 100_000_000:     score += 2

    if asset_type == "crypto": score += 1
    if asset_type == "meme":   score += 2

    return max(1, min(10, score))


def fetch_ticker_bar_data() -> list:
    """Fetch live prices for the top ticker bar."""
    results = []
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,dogecoin,solana,shiba-inu,binancecoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            id_map = {
                "bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE",
                "solana": "SOL", "shiba-inu": "SHIB", "binancecoin": "BNB"
            }
            for coin_id, sym in id_map.items():
                d = data.get(coin_id, {})
                price = d.get("usd", 0)
                chg = d.get("usd_24h_change", 0) or 0
                results.append({"symbol": sym, "price": price, "change": round(chg, 2)})
    except Exception:
        pass

    # Add stock tickers via yfinance if crypto succeeded
    try:
        stock_syms = ["AAPL", "TSLA", "NVDA"]
        tickers = yf.Tickers(" ".join(stock_syms))
        for sym in stock_syms:
            try:
                t = tickers.tickers[sym]
                hist = t.history(period="2d")
                if not hist.empty and len(hist) >= 2:
                    price = float(hist["Close"].iloc[-1])
                    prev  = float(hist["Close"].iloc[-2])
                    chg   = ((price - prev) / prev) * 100 if prev else 0
                    results.append({"symbol": sym, "price": price, "change": round(chg, 2)})
            except Exception:
                pass
    except Exception:
        pass

    return results


# ── Timeframe config ──────────────────────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "1m":  {"period": "1d",   "interval": "1m",  "label": "1 Minute",   "bars": 390,  "mode": "Intraday"},
    "5m":  {"period": "5d",   "interval": "5m",  "label": "5 Minutes",  "bars": 288,  "mode": "Intraday"},
    "15m": {"period": "5d",   "interval": "15m", "label": "15 Minutes", "bars": 200,  "mode": "Intraday"},
    "30m": {"period": "10d",  "interval": "30m", "label": "30 Minutes", "bars": 200,  "mode": "Intraday"},
    "1h":  {"period": "1mo",  "interval": "1h",  "label": "1 Hour",     "bars": 168,  "mode": "Swing"},
    "4h":  {"period": "3mo",  "interval": "4h",  "label": "4 Hours",    "bars": 180,  "mode": "Swing"},
    "1D":  {"period": "6mo",  "interval": "1d",  "label": "Daily",      "bars": 180,  "mode": "Swing"},
    "1W":  {"period": "2y",   "interval": "1wk", "label": "Weekly",     "bars": 104,  "mode": "Position"},
    "1M":  {"period": "5y",   "interval": "1mo", "label": "Monthly",    "bars": 60,   "mode": "Position"},
}


def fetch_history_by_timeframe(ticker: str, timeframe: str = "1D") -> dict:
    """
    Fetch OHLCV history for a given timeframe.
    Returns: {"history": DataFrame, "timeframe": str, "trading_mode": str, "error": str}
    """
    cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1D"])
    try:
        stock = yf.Ticker(ticker.strip().upper())
        hist  = stock.history(period=cfg["period"], interval=cfg["interval"])
        if hist is None or hist.empty:
            # Fallback to daily
            hist = stock.history(period="3mo", interval="1d")
            if hist is None or hist.empty:
                return {"error": f"No data for {ticker} on {timeframe} timeframe"}
            return {
                "history":      hist.tail(cfg["bars"]),
                "timeframe":    "1D",
                "trading_mode": "Swing",
                "fallback":     True,
            }
        return {
            "history":      hist.tail(cfg["bars"]),
            "timeframe":    timeframe,
            "trading_mode": cfg["mode"],
            "fallback":     False,
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_crypto_history_by_timeframe(coin_id: str, timeframe: str = "1D") -> dict:
    """
    Fetch OHLCV history for crypto from CoinGecko for a given timeframe.
    Returns DataFrame-compatible dict.
    """
    import pandas as pd_inner

    # CoinGecko supports: 1 day -> minutely (up to 1d), up to 90 days -> hourly, >90 days -> daily
    tf_to_days = {
        "1m": 1, "5m": 1, "15m": 2, "30m": 3,
        "1h": 7, "4h": 30, "1D": 90, "1W": 365, "1M": 730,
    }
    cfg   = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1D"])
    days  = tf_to_days.get(timeframe, 90)
    url   = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        raw = r.json()
        if not raw or isinstance(raw, dict):
            return {"error": "No OHLC data from CoinGecko"}
        df = pd_inner.DataFrame(raw, columns=["timestamp","Open","High","Low","Close"])
        df["timestamp"] = pd_inner.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df["Volume"] = 0  # CoinGecko OHLC doesn't include volume
        return {
            "history":      df.tail(cfg["bars"]),
            "timeframe":    timeframe,
            "trading_mode": cfg["mode"],
            "fallback":     False,
        }
    except Exception as e:
        return {"error": str(e)}

