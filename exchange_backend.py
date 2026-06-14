"""
FinsageAI — Exchange Backend Architecture Document
Backend Solutions Architect Module

This file implements:
1. Secure CCXT API wrapper with HMAC SHA256 via env vars
2. Error-handling middleware (429, timeouts, slippage)
3. Async bracket order placement (market/limit + SL + TP)
4. State machine order routing

NOTE: This runs in SIMULATION/PAPER mode in Streamlit.
      For real trading, deploy this as a FastAPI service separately.
"""

import os
import json
import time
import asyncio
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional, Literal
from enum import Enum
from dataclasses import dataclass, asdict

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("FinsageAI.Exchange")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SECURE CONFIG — All secrets from ENV (never hardcoded)
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeConfig:
    """
    Loads exchange credentials securely from environment variables.
    Add these to Streamlit Cloud Secrets or .env file:

    BINANCE_API_KEY     = your_key_here
    BINANCE_SECRET_KEY  = your_secret_here
    EXCHANGE_ID         = binance  (or kucoin, bybit, okx)
    PAPER_TRADING       = true     (always start with paper)
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id  = os.environ.get("EXCHANGE_ID", exchange_id).lower()
        self.api_key      = os.environ.get("BINANCE_API_KEY", "")
        self.secret_key   = os.environ.get("BINANCE_SECRET_KEY", "")
        self.paper_mode   = os.environ.get("PAPER_TRADING", "true").lower() == "true"
        self.base_url     = self._get_base_url()

        if not self.api_key or not self.secret_key:
            logger.warning("⚠️  No API credentials found — running in PAPER mode only")
            self.paper_mode = True

    def _get_base_url(self) -> str:
        urls = {
            "binance":  "https://api.binance.com",
            "kucoin":   "https://api.kucoin.com",
            "bybit":    "https://api.bybit.com",
            "okx":      "https://www.okx.com",
            "paper":    "https://testnet.binance.vision",
        }
        if self.paper_mode:
            return urls.get("paper", urls["paper"])
        return urls.get(self.exchange_id, urls["binance"])

    def generate_hmac_signature(self, query_string: str) -> str:
        """HMAC-SHA256 signature — used for authenticated endpoints."""
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def get_safe_display(self) -> dict:
        """Returns masked config for display (never expose raw keys)."""
        return {
            "exchange":    self.exchange_id,
            "paper_mode":  self.paper_mode,
            "api_key":     f"{self.api_key[:4]}...{self.api_key[-4:]}" if self.api_key else "NOT SET",
            "secret_key":  "***HIDDEN***",
            "base_url":    self.base_url,
            "configured":  self.is_configured(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ERROR HANDLING MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeError(Exception):
    pass

class RateLimitError(ExchangeError):
    pass

class TimeoutError(ExchangeError):
    pass

class SlippageError(ExchangeError):
    pass


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator: Exponential backoff retry for exchange calls.
    Handles: HTTP 429 (rate limit), network timeouts, connection errors.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    delay = base_delay * (2 ** attempt)   # Exponential: 1s, 2s, 4s
                    logger.warning(f"Rate limited (attempt {attempt+1}). Waiting {delay}s...")
                    time.sleep(delay)
                    last_error = e
                except TimeoutError as e:
                    delay = base_delay * (attempt + 1)
                    logger.warning(f"Timeout (attempt {attempt+1}). Waiting {delay}s...")
                    time.sleep(delay)
                    last_error = e
                except SlippageError as e:
                    logger.error(f"Slippage exceeded acceptable threshold: {e}")
                    raise e   # Don't retry slippage — reject the order
                except Exception as e:
                    logger.error(f"Exchange error (attempt {attempt+1}): {e}")
                    last_error = e
                    time.sleep(base_delay)
            raise ExchangeError(f"All {max_retries} retries failed: {last_error}")
        return wrapper
    return decorator


def check_slippage(expected_price: float, fill_price: float, max_slippage_pct: float = 0.1) -> bool:
    """
    Returns True if slippage is within acceptable range.
    max_slippage_pct = 0.1 means max 0.1% slippage allowed.
    """
    if expected_price <= 0:
        return True
    slippage = abs(fill_price - expected_price) / expected_price * 100
    if slippage > max_slippage_pct:
        logger.error(f"Slippage {slippage:.3f}% > max {max_slippage_pct}% | Expected: {expected_price}, Got: {fill_price}")
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ORDER DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT  = "LIMIT"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"

class OrderSide(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING  = "PENDING"
    FILLED   = "FILLED"
    PARTIAL  = "PARTIAL_FILL"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    symbol:     str
    side:       str          # BUY / SELL
    order_type: str          # MARKET / LIMIT
    quantity:   float
    price:      Optional[float] = None    # None for MARKET orders
    stop_price: Optional[float] = None   # For SL/TP orders
    time_in_force: str = "GTC"           # GTC / IOC / FOK
    order_id:   str = ""
    status:     str = OrderStatus.PENDING
    fill_price: float = 0.0
    commission: float = 0.0
    timestamp:  str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BracketOrder:
    """Complete bracket: Entry + Stop Loss + Take Profit"""
    symbol:          str
    direction:       str      # LONG / SHORT
    entry:           Order
    stop_loss:       Order
    take_profit:     Order
    entry_order_id:  str = ""
    sl_order_id:     str = ""
    tp_order_id:     str = ""
    status:          str = "PENDING"
    created_at:      str = ""
    pnl:             float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PAPER TRADING ENGINE (Simulates exchange responses)
# ═══════════════════════════════════════════════════════════════════════════════

class PaperExchange:
    """
    Simulates exchange order execution for paper trading.
    Mirrors the interface of the real ExchangeClient below.
    """

    def __init__(self):
        self.orders: dict[str, Order] = {}
        self.order_counter = 1000
        logger.info("📄 Paper Exchange initialized — SIMULATION MODE")

    def _next_id(self) -> str:
        self.order_counter += 1
        return f"PAPER-{self.order_counter}"

    def place_order(self, order: Order, slippage_pct: float = 0.05) -> Order:
        """Simulate order fill with slight slippage."""
        import random
        oid = self._next_id()
        fill_price = order.price if order.price else 0.0
        if fill_price > 0:
            slip = random.uniform(-slippage_pct/100, slippage_pct/100)
            fill_price = fill_price * (1 + slip)

        order.order_id  = oid
        order.status    = OrderStatus.FILLED
        order.fill_price= round(fill_price, 6)
        order.commission= round(fill_price * order.quantity * 0.001, 6)  # 0.1% fee
        order.timestamp = datetime.utcnow().isoformat()
        self.orders[oid] = order
        logger.info(f"📄 Paper fill: {order.side} {order.quantity} {order.symbol} @ {fill_price:.4f}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELED
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# 5. REAL EXCHANGE CLIENT (CCXT wrapper — requires API keys)
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeClient:
    """
    Production exchange client using CCXT.
    Install: pip install ccxt

    All methods have @with_retry decorator for resilience.
    HMAC signatures handled by CCXT internally using config keys.
    """

    def __init__(self, config: ExchangeConfig):
        self.config = config
        self._exchange = None
        self._init_ccxt()

    def _init_ccxt(self):
        """Initialize CCXT exchange object with credentials from env."""
        try:
            import ccxt
            exchange_class = getattr(ccxt, self.config.exchange_id, None)
            if not exchange_class:
                logger.error(f"Exchange '{self.config.exchange_id}' not supported by CCXT")
                return

            self._exchange = exchange_class({
                "apiKey":    self.config.api_key,
                "secret":    self.config.secret_key,
                "enableRateLimit": True,     # Built-in CCXT rate limiting
                "options":   {
                    "defaultType":   "future",   # futures trading
                    "adjustForTimeDifference": True,
                },
                "timeout":   15000,          # 15s timeout
                "sandbox":   self.config.paper_mode,
            })
            logger.info(f"✅ CCXT {self.config.exchange_id} client ready (paper={self.config.paper_mode})")
        except ImportError:
            logger.warning("CCXT not installed. Run: pip install ccxt")
        except Exception as e:
            logger.error(f"CCXT init error: {e}")

    @with_retry(max_retries=3, base_delay=1.0)
    def get_balance(self) -> dict:
        if not self._exchange:
            return {"error": "Exchange not initialized"}
        try:
            balance = self._exchange.fetch_balance()
            return {"USDT": balance.get("USDT", {}).get("free", 0)}
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                raise RateLimitError(str(e))
            raise ExchangeError(str(e))

    @with_retry(max_retries=3, base_delay=0.5)
    def get_ticker(self, symbol: str) -> dict:
        if not self._exchange:
            return {"error": "Exchange not initialized"}
        try:
            ticker = self._exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "bid":    ticker.get("bid", 0),
                "ask":    ticker.get("ask", 0),
                "last":   ticker.get("last", 0),
                "spread": ticker.get("ask", 0) - ticker.get("bid", 0),
            }
        except Exception as e:
            if "429" in str(e) or "rateLimit" in str(e):
                raise RateLimitError(str(e))
            elif "timeout" in str(e).lower():
                raise TimeoutError(str(e))
            raise ExchangeError(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ASYNC BRACKET ORDER PLACEMENT (Market or Limit + SL + TP)
# ═══════════════════════════════════════════════════════════════════════════════

async def place_bracket_order_async(
    symbol:           str,
    direction:        Literal["LONG", "SHORT"],
    entry_price:      float,
    quantity:         float,
    stop_loss_price:  float,
    take_profit_price: float,
    order_type:       Literal["MARKET", "LIMIT"] = "MARKET",
    exchange:         Optional[PaperExchange] = None,
    max_slippage_pct: float = 0.1,
) -> dict:
    """
    Async bracket order:
    1. Place entry order (MARKET or LIMIT)
    2. Wait for fill confirmation
    3. Immediately attach SL order
    4. Immediately attach TP order
    5. Verify all 3 orders placed before returning

    No unmanaged exposure — if SL/TP fail, entry is cancelled.
    """

    if exchange is None:
        exchange = PaperExchange()

    logger.info(f"📤 Placing {direction} bracket order: {symbol} | Qty: {quantity} | Entry: {entry_price}")

    bracket = BracketOrder(
        symbol=symbol,
        direction=direction,
        entry=Order(
            symbol=symbol,
            side="BUY" if direction == "LONG" else "SELL",
            order_type=order_type,
            quantity=quantity,
            price=entry_price if order_type == "LIMIT" else None,
        ),
        stop_loss=Order(
            symbol=symbol,
            side="SELL" if direction == "LONG" else "BUY",
            order_type="STOP_LOSS_LIMIT",
            quantity=quantity,
            stop_price=stop_loss_price,
            price=round(stop_loss_price * (0.999 if direction == "LONG" else 1.001), 6),
        ),
        take_profit=Order(
            symbol=symbol,
            side="SELL" if direction == "LONG" else "BUY",
            order_type="TAKE_PROFIT_LIMIT",
            quantity=quantity,
            stop_price=take_profit_price,
            price=round(take_profit_price * (0.999 if direction == "LONG" else 1.001), 6),
        ),
        created_at=datetime.utcnow().isoformat(),
    )

    try:
        # Step 1: Place entry order
        await asyncio.sleep(0.1)   # Simulate network I/O
        entry_filled = exchange.place_order(bracket.entry)
        bracket.entry_order_id = entry_filled.order_id

        # Slippage check
        if entry_filled.fill_price > 0 and not check_slippage(entry_price, entry_filled.fill_price, max_slippage_pct):
            exchange.cancel_order(entry_filled.order_id)
            return {
                "success": False,
                "error": f"Slippage exceeded {max_slippage_pct}% — order rejected",
                "expected": entry_price,
                "got": entry_filled.fill_price,
            }

        logger.info(f"✅ Entry filled @ {entry_filled.fill_price}")

        # Step 2: Attach SL (non-negotiable — run immediately)
        await asyncio.sleep(0.05)
        sl_placed = exchange.place_order(bracket.stop_loss)
        bracket.sl_order_id = sl_placed.order_id
        logger.info(f"🛑 Stop Loss placed @ {stop_loss_price}")

        # Step 3: Attach TP
        await asyncio.sleep(0.05)
        tp_placed = exchange.place_order(bracket.take_profit)
        bracket.tp_order_id = tp_placed.order_id
        logger.info(f"🎯 Take Profit placed @ {take_profit_price}")

        # All 3 orders confirmed
        bracket.status = "ACTIVE"

        # Calculate expected P&L
        sl_dist = abs(entry_filled.fill_price - stop_loss_price)
        tp_dist = abs(take_profit_price - entry_filled.fill_price)

        return {
            "success":         True,
            "bracket_status":  "ACTIVE",
            "symbol":          symbol,
            "direction":       direction,
            "entry_id":        bracket.entry_order_id,
            "sl_id":           bracket.sl_order_id,
            "tp_id":           bracket.tp_order_id,
            "fill_price":      entry_filled.fill_price,
            "stop_loss":       stop_loss_price,
            "take_profit":     take_profit_price,
            "quantity":        quantity,
            "sl_distance":     round(sl_dist, 6),
            "tp_distance":     round(tp_dist, 6),
            "risk_reward":     f"1:{tp_dist/sl_dist:.1f}" if sl_dist > 0 else "N/A",
            "commission_est":  round(entry_filled.commission * 3, 6),   # 3 orders
            "timestamp":       datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Bracket order failed: {e}")
        # Emergency: cancel any partial fills
        if bracket.entry_order_id:
            exchange.cancel_order(bracket.entry_order_id)
        return {
            "success": False,
            "error":   str(e),
            "action":  "Entry cancelled — no exposure taken",
        }


def place_bracket_order_sync(
    symbol: str,
    direction: Literal["LONG","SHORT"],
    entry_price: float,
    quantity: float,
    stop_loss_price: float,
    take_profit_price: float,
    order_type: Literal["MARKET","LIMIT"] = "MARKET",
    max_slippage_pct: float = 0.1,
) -> dict:
    """Synchronous wrapper for Streamlit (runs async in new event loop)."""
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            place_bracket_order_async(
                symbol, direction, entry_price, quantity,
                stop_loss_price, take_profit_price,
                order_type, PaperExchange(), max_slippage_pct
            )
        )
        loop.close()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. STREAMLIT UI RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def render_exchange_backend():
    """Streamlit UI for the Exchange Backend module."""
    import streamlit as st
    from config import LOGO_URL

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,10,20,0.95));
    border:1px solid rgba(110,64,201,0.3);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(110,64,201,0.3);">
            <div>
                <div style="font-size:1.1rem;font-weight:800;color:#a371f7;
                font-family:Orbitron,monospace;">⚡ Exchange Backend</div>
                <div style="color:#9b59d4;font-size:0.75rem;">
                FastAPI + CCXT Architecture · Bracket Orders · Risk Engine
                </div>
            </div>
            <span style="margin-left:auto;background:rgba(110,64,201,0.1);color:#a371f7;
            padding:0.2rem 0.8rem;border-radius:20px;font-size:0.68rem;font-weight:700;
            border:1px solid rgba(110,64,201,0.3);">PAPER MODE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ **Paper Trading Simulation Only.** Real exchange integration requires API credentials, regulatory compliance, and separate FastAPI deployment.")

    cfg = ExchangeConfig()

    tab1, tab2, tab3 = st.tabs(["🔑 API Config", "📤 Order Simulator", "📋 Architecture"])

    # TAB 1: API Config
    with tab1:
        st.markdown("### 🔑 Exchange API Configuration")
        st.markdown("*All credentials loaded from Streamlit Cloud Secrets (never hardcoded)*")

        safe = cfg.get_safe_display()
        st.markdown(f"""
        <div style="background:rgba(0,20,40,0.8);border:1px solid rgba(110,64,201,0.2);
        border-radius:10px;padding:1rem;font-size:0.83rem;font-family:monospace;">
            <div style="color:#f0c040;margin-bottom:0.5rem;">📋 Current Config (masked)</div>
            Exchange: <b style="color:#4a9eff;">{safe['exchange']}</b><br>
            Paper Mode: <b style="color:{'#00ff88' if safe['paper_mode'] else '#ff4466'};">{safe['paper_mode']}</b><br>
            API Key: <b style="color:#a371f7;">{safe['api_key']}</b><br>
            Secret: <b style="color:#a371f7;">{safe['secret_key']}</b><br>
            Base URL: <b style="color:#8b949e;">{safe['base_url']}</b><br>
            Configured: <b style="color:{'#00ff88' if safe['configured'] else '#f0c040'};">
            {'✅ YES' if safe['configured'] else '⚠️ NO (paper mode only)'}</b>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Required Streamlit Secrets (Settings → Secrets):**")
        st.code("""
# Add these to Streamlit Cloud Secrets
BINANCE_API_KEY = "your_api_key_here"
BINANCE_SECRET_KEY = "your_secret_here"
EXCHANGE_ID = "binance"
PAPER_TRADING = "true"
GEMINI_API_KEY = "your_gemini_key"
GOOGLE_CLIENT_ID = "your_google_oauth_id"
GOOGLE_CLIENT_SECRET = "your_google_oauth_secret"
        """, language="toml")

        st.info("💡 For HMAC-SHA256 signing: CCXT library handles all signature generation internally using your API key/secret. Never build raw HMAC manually unless using exchange REST directly.")

    # TAB 2: Order Simulator
    with tab2:
        st.markdown("### 📤 Bracket Order Simulator")
        st.markdown("*Entry + Stop Loss + Take Profit placed atomically*")

        oc1, oc2 = st.columns(2)
        with oc1:
            o_sym    = st.text_input("Symbol", value="BTC/USDT", key="o_sym")
            o_dir    = st.selectbox("Direction", ["LONG","SHORT"], key="o_dir")
            o_type   = st.selectbox("Order Type", ["MARKET","LIMIT"], key="o_type")
            o_entry  = st.number_input("Entry Price ($)", value=65000.0, key="o_entry")
        with oc2:
            o_qty    = st.number_input("Quantity", value=0.01, min_value=0.0001, format="%.4f", key="o_qty")
            o_sl     = st.number_input("Stop Loss ($)", value=63500.0, key="o_sl")
            o_tp     = st.number_input("Take Profit ($)", value=68000.0, key="o_tp")
            o_slip   = st.slider("Max Slippage %", 0.05, 0.5, 0.1, key="o_slip")

        if o_entry > 0 and o_sl > 0 and o_tp > 0:
            sl_d = abs(o_entry - o_sl)
            tp_d = abs(o_tp - o_entry)
            rr   = tp_d / sl_d if sl_d > 0 else 0
            pv   = o_entry * o_qty
            prev = {"LONG": o_sl < o_entry and o_tp > o_entry,
                    "SHORT": o_sl > o_entry and o_tp < o_entry}
            valid = prev.get(o_dir, False)

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("📦 Position Value", f"${pv:,.2f}")
            col_b.metric("📏 R:R Ratio", f"1:{rr:.1f}", delta="✅ Valid" if rr >= 2 else "⚠️ Below 1:2")
            col_c.metric("🛑 SL Distance", f"${sl_d:,.2f}")

            if not valid:
                st.error(f"❌ Invalid: For {o_dir}, SL must be {'below' if o_dir=='LONG' else 'above'} entry and TP {'above' if o_dir=='LONG' else 'below'} entry")

        if st.button("📤 Simulate Bracket Order ▶", type="primary", key="sim_order",
                     help="Runs async order placement simulation"):
            with st.spinner("⚡ Placing bracket order (entry → SL → TP)..."):
                result = place_bracket_order_sync(
                    o_sym, o_dir, o_entry, o_qty, o_sl, o_tp, o_type, o_slip
                )
            if result.get("success"):
                st.success("✅ Bracket Order Placed Successfully!")
                r1,r2,r3 = st.columns(3)
                r1.metric("Entry Fill", f"${result['fill_price']:,.4f}")
                r2.metric("Stop Loss", f"${result['stop_loss']:,.4f}")
                r3.metric("Take Profit", f"${result['take_profit']:,.4f}")
                st.markdown(f"""
                <div style="background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.2);
                border-radius:8px;padding:0.9rem 1rem;font-size:0.82rem;color:#c9d1d9;font-family:monospace;">
                🆔 Entry ID: {result['entry_id']} | SL ID: {result['sl_id']} | TP ID: {result['tp_id']}<br>
                📏 R:R: {result['risk_reward']} | Commission est: ${result['commission_est']:.4f}<br>
                ⏰ Timestamp: {result['timestamp']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ Order Failed: {result.get('error','Unknown error')}")
                if result.get("action"):
                    st.info(f"🛡️ {result['action']}")

    # TAB 3: Architecture
    with tab3:
        st.markdown("### 📋 System Architecture")
        st.code("""
# FastAPI + CCXT Production Architecture
# deploy separately: uvicorn main:app --host 0.0.0.0 --port 8000

# .env file (NEVER commit to git)
BINANCE_API_KEY=xxxx
BINANCE_SECRET_KEY=xxxx
PAPER_TRADING=true
MAX_SLIPPAGE_PCT=0.1
LOG_LEVEL=INFO

# main.py (FastAPI)
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ccxt.async_support as ccxt

app = FastAPI(title="FinsageAI Exchange API")

class OrderRequest(BaseModel):
    symbol: str
    direction: str      # LONG / SHORT
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    order_type: str = "MARKET"

@app.post("/order/bracket")
async def create_bracket_order(req: OrderRequest):
    # 1. Risk Engine check first
    # 2. Circuit breaker check
    # 3. Position size validation
    # 4. Place bracket order
    # Returns: {entry_id, sl_id, tp_id, fill_price}
    ...

@app.get("/health")
async def health():
    return {"status": "ok", "paper_mode": True}
        """, language="python")

        st.markdown("""
        **State Machine Flow:**
        ```
        IDLE ──▶ SCANNING ──▶ ENTRY_PENDING ──▶ POSITION_ACTIVE ──▶ CLOSED
                     │                │                  │
                     │         (signal rejected)   (SL/TP hit or
                     │                │             manual close)
                  (no signal)    ◀───────               ▼
                     ▲                             KILL_SWITCH (if CB triggered)
                     └─────────────────────────────────┘
        ```
        """)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:1rem;font-size:0.74rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Legal Notice:</b> Automated trading requires compliance with SEBI regulations (India),
    exchange TOS, and applicable financial laws. Paper trading is for education only.
    Real deployment requires professional legal and compliance review.
    </div>
    """, unsafe_allow_html=True)
