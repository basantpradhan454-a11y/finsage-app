"""
FinSage Data Fetcher
Fetches real market data from yfinance (stocks) and CoinGecko (crypto/meme coins).
No API key required — 100% free.
"""

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta


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


def fetch_stock_data(ticker: str) -> dict:
    """Fetch stock data from yfinance."""
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="1mo")

        if hist.empty or not info:
            return {"error": f"No data found for ticker '{ticker}'. Please check the symbol."}

        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or (hist["Close"].iloc[-1] if not hist.empty else None)
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change_pct = 0.0
        if current_price and prev_close and prev_close > 0:
            change_pct = ((current_price - prev_close) / prev_close) * 100

        # 52-week high/low
        week_high = info.get("fiftyTwoWeekHigh")
        week_low = info.get("fiftyTwoWeekLow")

        # Volume
        volume = info.get("volume") or info.get("regularMarketVolume", 0)
        avg_volume = info.get("averageVolume", 0)

        # Volatility (30-day)
        volatility = 0.0
        if len(hist) > 5:
            returns = hist["Close"].pct_change().dropna()
            volatility = float(returns.std() * (252 ** 0.5) * 100)

        # Risk Score (1-10)
        risk_score = calculate_risk_score(
            change_pct=change_pct,
            volatility=volatility,
            market_cap=info.get("marketCap", 0),
            asset_type="stock"
        )

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName", ticker.upper()),
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
            "history": hist,
            "analyst_target": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey", "N/A").upper(),
        }

    except Exception as e:
        return {"error": f"Error fetching stock data: {str(e)}"}


def fetch_crypto_data(symbol: str) -> dict:
    """Fetch crypto/meme coin data from CoinGecko (free, no key)."""
    try:
        symbol_upper = symbol.upper()
        coin_id = COINGECKO_IDS.get(symbol_upper)

        if not coin_id:
            # Try searching by symbol
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
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 429:
            return {"error": "CoinGecko rate limit hit. Please wait 30 seconds and try again."}
        if resp.status_code != 200:
            return {"error": f"CoinGecko API error: {resp.status_code}"}

        data = resp.json()
        mkt = data.get("market_data", {})

        current_price = mkt.get("current_price", {}).get("usd", 0)
        change_24h = mkt.get("price_change_percentage_24h", 0) or 0
        change_7d = mkt.get("price_change_percentage_7d", 0) or 0
        change_30d = mkt.get("price_change_percentage_30d", 0) or 0

        market_cap = mkt.get("market_cap", {}).get("usd", 0) or 0
        volume_24h = mkt.get("total_volume", {}).get("usd", 0) or 0

        volatility = abs(change_30d) / 4 if change_30d else abs(change_24h) * 5

        risk_score = calculate_risk_score(
            change_pct=change_24h,
            volatility=volatility,
            market_cap=market_cap,
            asset_type="crypto"
        )

        # Historical data via market_chart
        hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        hist_resp = requests.get(hist_url, params={"vs_currency": "usd", "days": "30"}, timeout=10)
        history_df = pd.DataFrame()
        if hist_resp.status_code == 200:
            prices = hist_resp.json().get("prices", [])
            if prices:
                history_df = pd.DataFrame(prices, columns=["timestamp", "Close"])
                history_df["Date"] = pd.to_datetime(history_df["timestamp"], unit="ms")
                history_df.set_index("Date", inplace=True)
                history_df.drop("timestamp", axis=1, inplace=True)

        return {
            "ticker": symbol_upper,
            "coin_id": coin_id,
            "name": data.get("name", symbol_upper),
            "asset_type": "Meme Coin" if symbol_upper in ["DOGE","SHIB","PEPE","FLOKI","BONK","WIF","MEME","TURBO","BRETT","NEIRO"] else "Cryptocurrency",
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
    """Calculate a Risk Score from 1 (very low) to 10 (very high)."""
    score = 5  # baseline

    # Volatility impact
    if volatility > 100: score += 3
    elif volatility > 50: score += 2
    elif volatility > 20: score += 1
    elif volatility < 10: score -= 1

    # Price change impact
    if abs(change_pct) > 20: score += 2
    elif abs(change_pct) > 10: score += 1
    elif abs(change_pct) < 2: score -= 1

    # Market cap impact (larger = safer)
    if market_cap > 100_000_000_000: score -= 2  # > $100B
    elif market_cap > 10_000_000_000: score -= 1  # > $10B
    elif market_cap < 1_000_000_000: score += 1   # < $1B
    elif market_cap < 100_000_000: score += 2     # < $100M

    # Asset type baseline
    if asset_type == "crypto": score += 1
    if asset_type == "meme": score += 2

    return max(1, min(10, score))


def fetch_ticker_bar_data() -> list:
    """Fetch live prices for the top ticker bar."""
    results = []
    symbols = ["BTC", "ETH", "DOGE", "SOL", "SHIB", "BNB"]
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
    except:
        pass
    return results
