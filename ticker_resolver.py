"""
FinSage Ticker Resolver — fuzzy/symbol name matching
Handles common misspellings and company name -> ticker conversions.
e.g. 'apple' -> AAPL, 'google' -> GOOGL, 'AAPLE' -> AAPL, 'microsoft' -> MSFT
"""
import re

# ── Company name → ticker mapping ─────────────────────────────────────────────
NAME_TO_TICKER = {
    # US stocks
    "apple": "AAPL", "aapl": "AAPL", "aaple": "AAPL", "appel": "AAPL", "aple": "AAPL",
    "microsoft": "MSFT", "msft": "MSFT", "micorsoft": "MSFT", "microsft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL", "goog": "GOOGL",
    "gogle": "GOOGL", "goggle": "GOOGL",
    "amazon": "AMZN", "amzn": "AMZN", "amazn": "AMZN", "amzon": "AMZN", "amazoon": "AMZN",
    "tesla": "TSLA", "tsla": "TSLA", "tesala": "TSLA", "tesl": "TSLA", "tesle": "TSLA",
    "nvidia": "NVDA", "nvda": "NVDA", "nvida": "NVDA", "nvidea": "NVDA", "nvdia": "NVDA", "nividia": "NVDA",
    "meta": "META", "facebook": "META", "fb": "META",
    "netflix": "NFLX", "nflx": "NFLX", "netflx": "NFLX",
    "amd": "AMD", "advanced micro": "AMD",
    "intel": "INTC", "intc": "INTC",
    "qualcomm": "QCOM", "qcom": "QCOM",
    "broadcom": "AVGO", "avgo": "AVGO",
    "jpmorgan": "JPM", "jpm": "JPM", "jpmorgan chase": "JPM",
    "goldman sachs": "GS", "gs": "GS",
    "walmart": "WMT", "wmt": "WMT",
    "disney": "DIS", "dis": "DIS",
    "coca cola": "KO", "coca-cola": "KO", "ko": "KO", "coke": "KO",
    "pepsi": "PEP", "pepsiCo": "PEP", "pep": "PEP",
    "exxon": "XOM", "xom": "XOM",
    "pfizer": "PFE", "pfe": "PFE",
    "johnson johnson": "JNJ", "jnj": "JNJ", "johnson & johnson": "JNJ",
    "visa": "V", "mastercard": "MA",
    "paypal": "PYPL", "pypl": "PYPL",
    "salesforce": "CRM", "crm": "CRM",
    "oracle": "ORCL", "orcl": "ORCL",
    "cisco": "CSCO", "csco": "CSCO",
    "boeing": "BA", "ba": "BA",
    "ford": "F", "general motors": "GM", "gm": "GM",
    "spotify": "SPOT", "spot": "SPOT",
    "uber": "UBER", "lyft": "LYFT",
    "airbnb": "ABNB", "abnb": "ABNB",
    "shopify": "SHOP", "shop": "SHOP",
    "snowflake": "SNOW", "snow": "SNOW",
    "palantir": "PLTR", "pltr": "PLTR",
    "coinbase": "COIN", "coin": "COIN",

    # Indian stocks (NSE)
    "reliance": "RELIANCE.NS", "ril": "RELIANCE.NS",
    "tcs": "TCS.NS", "tata consultancy": "TCS.NS",
    "infosys": "INFY.NS", "infy": "INFY.NS", "infoys": "INFY.NS",
    "wipro": "WIPRO.NS",
    "hcl": "HCLTECH.NS", "hcltech": "HCLTECH.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfcbank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS", "icici": "ICICIBANK.NS", "icicibank": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "state bank": "SBIN.NS", "sbin": "SBIN.NS",
    "axis bank": "AXISBANK.NS", "axis": "AXISBANK.NS", "axisbank": "AXISBANK.NS",
    "kotak": "KOTAKBANK.NS", "kotak bank": "KOTAKBANK.NS",
    "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS", "bharti": "BHARTIARTL.NS",
    "adani": "ADANIENT.NS", "adani enterprises": "ADANIENT.NS",
    "tata motors": "TATAMOTORS.NS", "tata motor": "TATAMOTORS.NS",
    "maruti": "MARUTI.NS", "maruti suzuki": "MARUTI.NS",
    "bajaj finance": "BAJFINANCE.NS", "bajfinance": "BAJFINANCE.NS",
    "lt": "LT.NS", "larsen toubro": "LT.NS", "larsen": "LT.NS",
    "itc": "ITC.NS",
    "sun pharma": "SUNPHARMA.NS", "sunpharma": "SUNPHARMA.NS",
    "dr reddy": "DRREDDY.NS", "drreddy": "DRREDDY.NS",
    "cipla": "CIPLA.NS",
    "nifty": "^NSEI", "nifty 50": "^NSEI", "nifty50": "^NSEI",
    "bank nifty": "^NSEBANK", "nifty bank": "^NSEBANK",
    "sensex": "^BSESN",

    # Crypto
    "bitcoin": "BTC", "btc": "BTC", "bitcon": "BTC",
    "ethereum": "ETH", "eth": "ETH", "ether": "ETH", "etherium": "ETH",
    "solana": "SOL", "sol": "SOL",
    "ripple": "XRP", "xrp": "XRP",
    "cardano": "ADA", "ada": "ADA",
    "dogecoin": "DOGE", "doge": "DOGE", "doge coin": "DOGE",
    "shiba inu": "SHIB", "shib": "SHIB", "shibainu": "SHIB",
    "polygon": "MATIC", "matic": "MATIC",
    "avalanche": "AVAX", "avax": "AVAX",
    "polkadot": "DOT", "dot": "DOT",
    "chainlink": "LINK", "link": "LINK",
    "binance coin": "BNB", "bnb": "BNB",
    "litecoin": "LTC", "ltc": "LTC",
    "uniswap": "UNI", "uni": "UNI",
    "aptos": "APT", "apt": "APT",
    "near": "NEAR", "near protocol": "NEAR",
    "pepe": "PEPE", "flok": "FLOKI", "floki": "FLOKI",
    "bonk": "BONK", "wif": "WIF",
}

# ── Levenshtein distance for fuzzy matching ───────────────────────────────────
def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            ins = prev[j + 1] + 1
            dele = curr[j] + 1
            sub = prev[j] + (ca != cb)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


def resolve_ticker(query: str) -> str:
    """
    Resolve user input to a proper ticker symbol.
    Handles:
      - Company names: 'apple' -> AAPL
      - Misspellings: 'aaple' -> AAPL, 'microsft' -> MSFT
      - Direct tickers: 'AAPL' -> AAPL (returns as-is)
      - Indian suffixes: 'reliance' -> RELIANCE.NS
      - Crypto names: 'bitcoin' -> BTC
    """
    if not query or not query.strip():
        return query
    q = query.strip().lower().replace(" ", "")

    # 1. Exact match in mapping
    if q in NAME_TO_TICKER:
        return NAME_TO_TICKER[q]

    # Also try with spaces preserved
    q_sp = query.strip().lower()
    if q_sp in NAME_TO_TICKER:
        return NAME_TO_TICKER[q_sp]

    # 2. Already a valid ticker (uppercase, short)
    upper = query.strip().upper()
    if re.match(r'^[A-Z]{1,5}(\.NS|\.BO)?$', upper):
        return upper

    # 3. Fuzzy match — find closest key within edit distance 2
    best_key = None
    best_dist = 99
    for key in NAME_TO_TICKER:
        d = _levenshtein(q, key.replace(" ", ""))
        if d < best_dist:
            best_dist = d
            best_key = key
    if best_key and best_dist <= 2:
        return NAME_TO_TICKER[best_key]

    # 4. Return original (let yfinance handle it)
    return query.strip().upper()


if __name__ == "__main__":
    tests = ["apple", "AAPLE", "google", "microsft", "tesla", "bitcoin", "reliance",
             "AAPL", "TSLA", "nvdia", "amzon", "hdfc", "sbi", "nifty"]
    for t in tests:
        print(f"  {t:>15} -> {resolve_ticker(t)}")
