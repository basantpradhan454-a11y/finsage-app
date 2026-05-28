"""
FinSage Data Fetcher
Fetches real market data from yfinance (stocks) and CoinGecko (crypto/meme coins).
Also fetches latest news for context-aware AI analysis.
No API key required — 100% free.
"""

import yfinance as yf
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


# ── CoinGecko coin ID mapping ─────────────────────────────────────────────────
COINGECKO_IDS = {
    # Crypto
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
    "AVAX": "avalanche-2", "DOT": "polkadot", "MATIC": "matic-network",
    "LINK": "chainlink", "UNI": "uniswap", "LTC": "litecoin",
    "ATOM": "cosmos", "TRX": "tron", "TON": "the-open-network",
    # Meme Coins
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
    "FLOKI": "floki", "BONK": "bonk", "WIF": "dogwifcoin",
    "MEME": "memecoin-2", "TURBO": "turbo", "BRETT": "brett",
    "NEIRO": "neiro-on-eth",
}

MEME_COINS = {"DOGE","SHIB","PEPE","FLOKI","BONK","WIF","MEME","TURBO","BRETT","NEIRO"}


# ── News Fetchers ─────────────────────────────────────────────────────────────

def fetch_stock_news(ticker: str, company_name: str = "") -> list:
    """Fetch latest news for a stock via yfinance. Returns list of dicts."""
    news_items = []
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news or []
        for n in raw_news[:8]:
            c = n.get("content", {})
            title = c.get("title", "")
            if not title:
                continue
            summary = c.get("summary", "")
            pub_date = c.get("pubDate", "")
            # Get URL
            cp = c.get("canonicalUrl") or c.get("clickThroughUrl") or {}
            url = cp.get("url", "") if isinstance(cp, dict) else ""
            # Thumbnail
            thumb = c.get("thumbnail", {})
            img = thumb.get("originalUrl", "") if isinstance(thumb, dict) else ""
            news_items.append({
                "title": title,
                "summary": summary[:200] if summary else "",
                "url": url,
                "published": pub_date,
                "image": img,
                "source": "Yahoo Finance",
            })
    except Exception:
        pass
    return news_items


def fetch_crypto_news(coin_name: str, ticker: str) -> list:
    """Fetch latest crypto news via Google News RSS. Returns list of dicts."""
    news_items = []
    try:
        query = f"{coin_name} {ticker} cryptocurrency".replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        for item in items[:8]:
            title_el = item.find("title")
            link_el  = item.find("link")
            date_el  = item.find("pubDate")
            src_el   = item.find("source")
            title = title_el.text if title_el is not None else ""
            if not title:
                continue
            news_items.append({
                "title": title,
                "summary": "",
                "url": link_el.text if link_el is not None else "",
                "published": date_el.text if date_el is not None else "",
                "image": "",
                "source": src_el.text if src_el is not None else "Google News",
            })
    except Exception:
        pass
    return news_items


# ── Stock Fetcher ─────────────────────────────────────────────────────────────

def fetch_stock_data(ticker: str) -> dict:
    """Fetch stock data + OHLCV history + news from yfinance."""
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="3mo")   # 3 months for better candlestick

        if hist.empty or not info:
            return {"error": f"No data found for ticker '{ticker}'. Please check the symbol."}

        current_price = (info.get("currentPrice") or info.get("regularMarketPrice")
                         or (hist["Close"].iloc[-1] if not hist.empty else None))
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change_pct = 0.0
        if current_price and prev_close and prev_close > 0:
            change_pct = ((current_price - prev_close) / prev_close) * 100

        week_high  = info.get("fiftyTwoWeekHigh")
        week_low   = info.get("fiftyTwoWeekLow")
        volume     = info.get("volume") or info.get("regularMarketVolume", 0)
        avg_volume = info.get("averageVolume", 0)

        volatility = 0.0
        if len(hist) > 5:
            returns = hist["Close"].pct_change().dropna()
            volatility = float(returns.std() * (252 ** 0.5) * 100)

        risk_score = calculate_risk_score(
            change_pct=change_pct,
            volatility=volatility,
            market_cap=info.get("marketCap", 0),
            asset_type="stock"
        )

        company_name = info.get("longName") or info.get("shortName", ticker.upper())

        return {
            "ticker": ticker.upper(),
            "name": company_name,
            "asset_type": "Stock",
            "exchange": info.get("exchange", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": round(current_price, 4) if current_price else None,
            "currency": info.get("currency", "USD"),
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 4) if prev_close else None,
            "open_price": info.get("open") or info.get("regularMarketOpen"),
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "week_52_high": week_high,
            "week_52_low": week_low,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "volume": volume,
            "avg_volume": avg_volume,
            "beta": info.get("beta"),
            "volatility_annualized": round(volatility, 2),
            "risk_score": risk_score,
            "history": hist,           # Full OHLCV DataFrame
            "analyst_target": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey", "N/A").upper(),
            "news": fetch_stock_news(ticker.upper(), company_name),
        }

    except Exception as e:
        return {"error": f"Error fetching stock data: {str(e)}"}


# ── Crypto Fetcher ────────────────────────────────────────────────────────────

def fetch_crypto_data(symbol: str) -> dict:
    """Fetch crypto data + OHLC history + news from CoinGecko & Google News."""
    try:
        symbol_upper = symbol.upper()
        coin_id = COINGECKO_IDS.get(symbol_upper)

        if not coin_id:
            search_url = f"https://api.coingecko.com/api/v3/search?query={symbol}"
            search_resp = requests.get(search_url, timeout=10)
            search_data = search_resp.json()
            coins = search_data.get("coins", [])
            if coins:
                coin_id = coins[0]["id"]
            else:
                return {"error": f"Coin '{symbol}' not found. Try BTC, ETH, DOGE, SHIB etc."}

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            "localization": "false", "tickers": "false",
            "market_data": "true", "community_data": "false", "developer_data": "false",
        }
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 429:
            return {"error": "CoinGecko rate limit hit. Please wait 30 seconds and try again."}
        if resp.status_code != 200:
            return {"error": f"CoinGecko API error: {resp.status_code}"}

        data = resp.json()
        mkt  = data.get("market_data", {})

        current_price = mkt.get("current_price", {}).get("usd", 0)
        change_24h    = mkt.get("price_change_percentage_24h", 0) or 0
        change_7d     = mkt.get("price_change_percentage_7d",  0) or 0
        change_30d    = mkt.get("price_change_percentage_30d", 0) or 0
        market_cap    = mkt.get("market_cap", {}).get("usd", 0) or 0
        volume_24h    = mkt.get("total_volume", {}).get("usd", 0) or 0
        volatility    = abs(change_30d) / 4 if change_30d else abs(change_24h) * 5

        risk_score = calculate_risk_score(
            change_pct=change_24h, volatility=volatility,
            market_cap=market_cap, asset_type="crypto"
        )

        # ── OHLC history for candlestick ──
        ohlc_df = pd.DataFrame()
        try:
            ohlc_url  = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
            ohlc_resp = requests.get(ohlc_url, params={"vs_currency": "usd", "days": "30"}, timeout=10)
            if ohlc_resp.status_code == 200:
                raw = ohlc_resp.json()  # [[ts, open, high, low, close], ...]
                if raw:
                    ohlc_df = pd.DataFrame(raw, columns=["timestamp", "Open", "High", "Low", "Close"])
                    ohlc_df["Date"] = pd.to_datetime(ohlc_df["timestamp"], unit="ms")
                    ohlc_df.set_index("Date", inplace=True)
                    ohlc_df.drop("timestamp", axis=1, inplace=True)
        except Exception:
            pass

        # Fallback line-only history
        history_df = ohlc_df if not ohlc_df.empty else pd.DataFrame()
        if ohlc_df.empty:
            try:
                hist_resp = requests.get(
                    f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                    params={"vs_currency": "usd", "days": "30"}, timeout=10
                )
                if hist_resp.status_code == 200:
                    prices = hist_resp.json().get("prices", [])
                    if prices:
                        history_df = pd.DataFrame(prices, columns=["timestamp", "Close"])
                        history_df["Date"] = pd.to_datetime(history_df["timestamp"], unit="ms")
                        history_df.set_index("Date", inplace=True)
                        history_df.drop("timestamp", axis=1, inplace=True)
            except Exception:
                pass

        coin_name = data.get("name", symbol_upper)
        is_meme   = symbol_upper in MEME_COINS

        return {
            "ticker": symbol_upper,
            "coin_id": coin_id,
            "name": coin_name,
            "asset_type": "Meme Coin" if is_meme else "Cryptocurrency",
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
            "news": fetch_crypto_news(coin_name, symbol_upper),
        }

    except Exception as e:
        return {"error": f"Error fetching crypto data: {str(e)}"}


# ── Risk Score Calculator ─────────────────────────────────────────────────────

def calculate_risk_score(change_pct: float, volatility: float, market_cap: float, asset_type: str) -> int:
    score = 5  # base

    if abs(change_pct) > 10: score += 2
    elif abs(change_pct) > 5: score += 1

    if volatility > 80: score += 3
    elif volatility > 50: score += 2
    elif volatility > 30: score += 1

    if market_cap > 100e9: score -= 2
    elif market_cap > 10e9: score -= 1
    elif market_cap < 1e9: score += 1

    if asset_type == "crypto": score += 1

    return max(1, min(10, score))


# ── Ticker Bar Data ───────────────────────────────────────────────────────────

def fetch_ticker_bar_data() -> list:
    """Fetch quick price data for top assets for the ticker bar."""
    tickers = {
        "AAPL": "stock", "TSLA": "stock", "NVDA": "stock", "MSFT": "stock",
        "BTC-USD": "crypto", "ETH-USD": "crypto", "SOL-USD": "crypto",
    }
    results = []
    try:
        for sym, atype in tickers.items():
            t = yf.Ticker(sym)
            info = t.info
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
            prev  = info.get("previousClose") or info.get("regularMarketPreviousClose", 0) or 0
            chg   = ((price - prev) / prev * 100) if prev > 0 else 0
            display = sym.replace("-USD", "")
            results.append({"symbol": display, "price": price, "change": round(chg, 2)})
    except Exception:
        pass
    return results
