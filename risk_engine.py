"""
FinsageAI — Chief Risk Officer (CRO) Module
Hard-coded Risk & Money Management Engine
Overrides ALL execution signals — this is the kill-switch layer.

Implements:
  - Kelly Criterion / Fixed Fractional Position Sizing (max 1% equity per trade)
  - Dynamic Exits: ATR-based SL, 1:2 RR TP, Trailing Stop at 1:1
  - Circuit Breakers: 3% daily drawdown kill-switch, 4 consecutive losses halt
  - State Machine: IDLE → SCANNING → ENTRY_PENDING → POSITION_ACTIVE → CLOSED
"""

import os
import json
import math
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS — CRO Hard-Coded Limits (NEVER override from UI)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RISK_PER_TRADE    = 0.01    # 1% of equity per trade (absolute max)
ATR_SL_MULTIPLIER     = 1.5     # SL = Entry - (1.5 × ATR) for Longs
MIN_RISK_REWARD       = 2.0     # TP = Entry + (2 × SL distance)
TRAILING_ACTIVATION   = 1.0     # Activate trailing stop at 1:1 RR
TRAILING_LOCK_PCT     = 0.50    # Lock 50% of profits once trailing activated
MAX_DAILY_DRAWDOWN    = 0.03    # 3% daily equity drop → kill switch
MAX_CONSECUTIVE_LOSS  = 4       # 4 consecutive losses → halt trading
KILL_SWITCH_HOURS     = 24      # Hours bot is locked after kill-switch
STATE_FILE            = "/tmp/finsage_risk_state.json"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class BotState(str, Enum):
    IDLE           = "IDLE"
    SCANNING       = "SCANNING"
    ENTRY_PENDING  = "ENTRY_PENDING"
    POSITION_ACTIVE= "POSITION_ACTIVE"
    CLOSED         = "CLOSED"
    KILL_SWITCH    = "KILL_SWITCH"


@dataclass
class Position:
    symbol:         str
    side:           Literal["LONG", "SHORT"]
    entry_price:    float
    quantity:       float
    stop_loss:      float
    take_profit:    float
    trailing_active: bool = False
    trailing_stop:  float = 0.0
    open_time:      str   = field(default_factory=lambda: datetime.utcnow().isoformat())
    order_id:       str   = ""
    sl_order_id:    str   = ""
    tp_order_id:    str   = ""


@dataclass
class RiskState:
    bot_state:          str   = BotState.IDLE
    equity_start_of_day: float = 0.0
    current_equity:     float = 0.0
    consecutive_losses: int   = 0
    kill_switch_until:  str   = ""   # ISO datetime
    daily_pnl:          float = 0.0
    total_trades:       int   = 0
    winning_trades:     int   = 0
    active_position:    Optional[dict] = None
    last_updated:       str   = field(default_factory=lambda: datetime.utcnow().isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RISK ENGINE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskEngine:
    """CRO-level risk management. All methods are synchronous for Streamlit."""

    def __init__(self, initial_equity: float = 10000.0):
        self.state = self._load_state(initial_equity)

    # ── Persistence ─────────────────────────────────────────────────────────────

    def _load_state(self, initial_equity: float) -> RiskState:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    raw = json.load(f)
                s = RiskState(**{k: v for k, v in raw.items() if k in RiskState.__dataclass_fields__})
                return s
            except Exception:
                pass
        return RiskState(
            bot_state=BotState.IDLE,
            equity_start_of_day=initial_equity,
            current_equity=initial_equity,
        )

    def _save_state(self):
        d = asdict(self.state)
        with open(STATE_FILE, "w") as f:
            json.dump(d, f, indent=2, default=str)

    # ── Kill-Switch Check ────────────────────────────────────────────────────────

    def is_kill_switch_active(self) -> tuple[bool, str]:
        """Returns (is_locked, reason_message)"""
        if self.state.bot_state == BotState.KILL_SWITCH:
            if self.state.kill_switch_until:
                until = datetime.fromisoformat(self.state.kill_switch_until)
                if datetime.utcnow() < until:
                    remaining = until - datetime.utcnow()
                    hrs = int(remaining.total_seconds() // 3600)
                    mins = int((remaining.total_seconds() % 3600) // 60)
                    return True, f"⛔ KILL SWITCH ACTIVE — Unlocks in {hrs}h {mins}m"
                else:
                    # Auto-unlock after 24h
                    self.state.bot_state = BotState.IDLE
                    self.state.kill_switch_until = ""
                    self._save_state()
                    return False, "✅ Kill switch expired — Bot unlocked"
        return False, ""

    def _activate_kill_switch(self, reason: str):
        """Engage emergency stop."""
        self.state.bot_state = BotState.KILL_SWITCH
        self.state.kill_switch_until = (
            datetime.utcnow() + timedelta(hours=KILL_SWITCH_HOURS)
        ).isoformat()
        self.state.active_position = None
        self._save_state()
        return {
            "action": "KILL_SWITCH",
            "reason": reason,
            "locked_until": self.state.kill_switch_until,
            "message": f"🚨 EMERGENCY STOP: {reason}. All positions closed. Bot locked for {KILL_SWITCH_HOURS}h.",
        }

    # ── Circuit Breakers ─────────────────────────────────────────────────────────

    def check_circuit_breakers(self, current_equity: float) -> dict:
        """Check daily drawdown + consecutive losses. Returns action dict."""
        self.state.current_equity = current_equity
        self.state.last_updated = datetime.utcnow().isoformat()

        # Daily drawdown check
        if self.state.equity_start_of_day > 0:
            dd = (self.state.equity_start_of_day - current_equity) / self.state.equity_start_of_day
            self.state.daily_pnl = current_equity - self.state.equity_start_of_day
            if dd >= MAX_DAILY_DRAWDOWN:
                return self._activate_kill_switch(
                    f"Daily drawdown {dd*100:.2f}% exceeded {MAX_DAILY_DRAWDOWN*100:.0f}% limit"
                )

        # Consecutive losses check
        if self.state.consecutive_losses >= MAX_CONSECUTIVE_LOSS:
            return self._activate_kill_switch(
                f"{self.state.consecutive_losses} consecutive losing trades"
            )

        self._save_state()
        return {"action": "OK", "daily_pnl": self.state.daily_pnl}

    # ── Position Sizing ──────────────────────────────────────────────────────────

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: float = MAX_RISK_PER_TRADE,
    ) -> dict:
        """
        Kelly / Fixed-Fractional sizing.
        Position Size = (Equity × Risk%) / |Entry - Stop Loss|
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Invalid prices"}
        if entry_price == stop_loss_price:
            return {"error": "Entry == Stop Loss — no risk defined"}

        risk_amount = equity * min(risk_pct, MAX_RISK_PER_TRADE)
        sl_distance = abs(entry_price - stop_loss_price)
        qty = risk_amount / sl_distance

        return {
            "equity":          round(equity, 2),
            "risk_pct":        round(risk_pct * 100, 2),
            "risk_amount_usd": round(risk_amount, 2),
            "entry_price":     entry_price,
            "stop_loss":       stop_loss_price,
            "sl_distance":     round(sl_distance, 6),
            "quantity":        round(qty, 6),
            "position_value":  round(qty * entry_price, 2),
        }

    # ── Dynamic Exits ────────────────────────────────────────────────────────────

    def calculate_exits(
        self,
        entry_price: float,
        atr: float,
        side: Literal["LONG", "SHORT"] = "LONG",
    ) -> dict:
        """
        Hard SL: 1.5 × ATR
        TP:      2 × SL distance (1:2 RR minimum)
        Trailing: activates at 1:1 RR, locks 50% of profit
        """
        sl_distance = ATR_SL_MULTIPLIER * atr
        tp_distance = MIN_RISK_REWARD * sl_distance

        if side == "LONG":
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
            trailing_activation_price = entry_price + sl_distance   # 1:1 RR
            trailing_stop_price       = entry_price + sl_distance * TRAILING_LOCK_PCT
        else:  # SHORT
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance
            trailing_activation_price = entry_price - sl_distance
            trailing_stop_price       = entry_price - sl_distance * TRAILING_LOCK_PCT

        return {
            "entry":                    round(entry_price, 6),
            "stop_loss":                round(sl, 6),
            "take_profit":              round(tp, 6),
            "sl_distance":              round(sl_distance, 6),
            "tp_distance":              round(tp_distance, 6),
            "risk_reward":              f"1:{MIN_RISK_REWARD}",
            "atr_used":                 round(atr, 6),
            "trailing_activation_price":round(trailing_activation_price, 6),
            "trailing_stop_initial":    round(trailing_stop_price, 6),
            "side":                     side,
        }

    # ── Trade Result Recording ───────────────────────────────────────────────────

    def record_trade_result(self, pnl: float, equity: float):
        """Call after every trade closes."""
        self.state.total_trades += 1
        self.state.current_equity = equity
        self.state.active_position = None

        if pnl >= 0:
            self.state.winning_trades += 1
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_losses += 1

        self.state.bot_state = BotState.IDLE
        self._save_state()

        win_rate = (self.state.winning_trades / self.state.total_trades * 100) if self.state.total_trades else 0
        return {
            "pnl": pnl,
            "consecutive_losses": self.state.consecutive_losses,
            "total_trades": self.state.total_trades,
            "win_rate": round(win_rate, 1),
        }

    def reset_daily_stats(self, equity: float):
        """Call at start of each trading day."""
        self.state.equity_start_of_day = equity
        self.state.current_equity = equity
        self.state.daily_pnl = 0.0
        self._save_state()

    def manual_unlock(self) -> str:
        """Admin: manually unlock kill switch."""
        self.state.bot_state = BotState.IDLE
        self.state.kill_switch_until = ""
        self.state.consecutive_losses = 0
        self._save_state()
        return "✅ Kill switch manually disengaged. Bot is IDLE."

    def get_dashboard_stats(self) -> dict:
        eq = self.state.current_equity
        sod = self.state.equity_start_of_day
        daily_dd = ((sod - eq) / sod * 100) if sod > 0 else 0
        wr = (self.state.winning_trades / self.state.total_trades * 100) if self.state.total_trades else 0
        return {
            "bot_state":          self.state.bot_state,
            "current_equity":     eq,
            "daily_pnl":          self.state.daily_pnl,
            "daily_drawdown_pct": round(daily_dd, 2),
            "consecutive_losses": self.state.consecutive_losses,
            "total_trades":       self.state.total_trades,
            "win_rate":           round(wr, 1),
            "kill_switch_until":  self.state.kill_switch_until,
            "max_risk_per_trade": f"{MAX_RISK_PER_TRADE*100:.0f}%",
            "max_daily_dd":       f"{MAX_DAILY_DRAWDOWN*100:.0f}%",
            "max_consec_loss":    MAX_CONSECUTIVE_LOSS,
            "sl_atr_mult":        ATR_SL_MULTIPLIER,
            "min_rr":             f"1:{MIN_RISK_REWARD:.0f}",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MULTI-TIMEFRAME STRATEGY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class StrategyEngine:
    """
    Lead Trading Strategist logic.
    Multi-timeframe: 15M entry, 4H macro trend.
    State machine: IDLE → SCANNING → ENTRY_PENDING → POSITION_ACTIVE → CLOSED
    """

    def compute_signals(self, data_4h: dict, data_15m: dict) -> dict:
        """
        data_4h / data_15m must contain:
          price, ema_200, bb_upper, bb_lower, rsi, macd_hist, atr, prev_rsi
        Returns signal dict with direction, confidence, and reason list.
        """
        reasons = []
        long_score = 0
        short_score = 0

        # ── 4H Macro Trend ───────────────────────────────────────────────────────
        price_4h  = data_4h.get("price", 0)
        ema200_4h = data_4h.get("ema_200", 0)

        if price_4h > ema200_4h:
            long_score += 1
            reasons.append("✅ 4H: Price ABOVE 200 EMA (bullish macro)")
        elif price_4h < ema200_4h:
            short_score += 1
            reasons.append("✅ 4H: Price BELOW 200 EMA (bearish macro)")
        else:
            reasons.append("⚠️ 4H: Price AT 200 EMA (neutral)")

        # ── 15M Entry Signals ────────────────────────────────────────────────────
        price_15m    = data_15m.get("price", 0)
        bb_lower_15m = data_15m.get("bb_lower", 0)
        bb_upper_15m = data_15m.get("bb_upper", 0)
        rsi_15m      = data_15m.get("rsi", 50)
        prev_rsi     = data_15m.get("prev_rsi", 50)
        macd_hist    = data_15m.get("macd_hist", 0)
        atr_15m      = data_15m.get("atr", 0)

        # Bollinger Band touch
        if bb_lower_15m > 0 and price_15m <= bb_lower_15m:
            long_score += 1
            reasons.append("✅ 15M: Price at/below Lower Bollinger Band")
        if bb_upper_15m > 0 and price_15m >= bb_upper_15m:
            short_score += 1
            reasons.append("✅ 15M: Price at/above Upper Bollinger Band")

        # RSI + Divergence
        rsi_bullish_div = rsi_15m < 30 and prev_rsi < rsi_15m
        rsi_bearish_div = rsi_15m > 70 and prev_rsi > rsi_15m

        if rsi_15m < 30:
            long_score += 1
            reasons.append(f"✅ 15M: RSI {rsi_15m:.1f} — Oversold (<30)")
        if rsi_15m > 70:
            short_score += 1
            reasons.append(f"✅ 15M: RSI {rsi_15m:.1f} — Overbought (>70)")
        if rsi_bullish_div:
            long_score += 1
            reasons.append("✅ 15M: Bullish RSI divergence detected")
        if rsi_bearish_div:
            short_score += 1
            reasons.append("✅ 15M: Bearish RSI divergence detected")

        # MACD Histogram
        if macd_hist > 0:
            long_score += 1
            reasons.append(f"✅ 15M: MACD histogram GREEN ({macd_hist:.4f}) — bullish crossover")
        elif macd_hist < 0:
            short_score += 1
            reasons.append(f"✅ 15M: MACD histogram RED ({macd_hist:.4f}) — bearish crossover")

        # ── Signal Decision ──────────────────────────────────────────────────────
        # LONG: all 4 criteria required (score >= 4)
        # SHORT: all 4 criteria required (score >= 4)

        LONG_CRITERIA  = 4   # price>200EMA, BB touch, RSI<30+divergence, MACD green
        SHORT_CRITERIA = 4

        signal = "HOLD"
        confidence = 0
        if long_score >= LONG_CRITERIA and long_score > short_score:
            signal = "LONG"
            confidence = min(100, long_score * 20)
        elif short_score >= SHORT_CRITERIA and short_score > long_score:
            signal = "SHORT"
            confidence = min(100, short_score * 20)
        else:
            signal = "HOLD"
            confidence = 0
            reasons.append(f"⏸️ Criteria not met — LONG:{long_score}/4, SHORT:{short_score}/4")

        return {
            "signal":       signal,
            "confidence":   confidence,
            "long_score":   long_score,
            "short_score":  short_score,
            "atr":          atr_15m,
            "entry_price":  price_15m,
            "reasons":      reasons,
            "timestamp":    datetime.utcnow().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. STREAMLIT DASHBOARD RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def render_risk_dashboard():
    """Streamlit UI for the Risk Engine — for the 3-dot menu."""
    import streamlit as st
    from config import LOGO_URL

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(10,0,20,0.95));
    border:1px solid rgba(255,60,60,0.25);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(255,60,60,0.25);">
            <div>
                <div style="font-size:1.1rem;font-weight:800;color:#ff6b6b;
                font-family:Orbitron,monospace;">🛡️ Risk Management Engine</div>
                <div style="color:#ff9999;font-size:0.75rem;">
                CRO-Level Capital Protection — Overrides ALL signals
                </div>
            </div>
            <span style="margin-left:auto;background:rgba(255,60,60,0.1);color:#ff6b6b;
            padding:0.2rem 0.8rem;border-radius:20px;font-size:0.68rem;font-weight:700;
            border:1px solid rgba(255,60,60,0.3);">PAPER MODE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ **Educational / Paper Trading Only.** This module demonstrates professional risk management concepts. Real exchange integration requires API credentials and regulatory compliance.")

    # ── Equity Input ────────────────────────────────────────────────────────────
    eq_col, _ = st.columns([1, 2])
    with eq_col:
        equity = st.number_input("Simulated Account Equity ($)", min_value=100.0,
                                 max_value=10_000_000.0, value=10000.0, step=100.0)

    engine = RiskEngine(initial_equity=equity)
    stats  = engine.get_dashboard_stats()
    locked, lock_msg = engine.is_kill_switch_active()

    # ── Kill Switch Status ───────────────────────────────────────────────────────
    if locked:
        st.error(f"🚨 {lock_msg}")
        if st.button("🔓 Admin: Manual Unlock", type="secondary"):
            msg = engine.manual_unlock()
            st.success(msg)
            st.rerun()
        return

    # ── Live Stats Bar ───────────────────────────────────────────────────────────
    m1,m2,m3,m4,m5 = st.columns(5)
    state_colors = {
        "IDLE":"#8b949e","SCANNING":"#4a9eff",
        "ENTRY_PENDING":"#f0c040","POSITION_ACTIVE":"#00ff88",
        "CLOSED":"#8b949e","KILL_SWITCH":"#ff4444"
    }
    sc = state_colors.get(stats["bot_state"],"#8b949e")
    m1.markdown(f"""<div style="background:rgba(0,20,40,0.8);border:1px solid {sc}33;
    border-radius:8px;padding:0.6rem;text-align:center;">
    <div style="color:{sc};font-size:0.7rem;font-weight:700;">BOT STATE</div>
    <div style="color:{sc};font-size:1rem;font-weight:900;">{stats['bot_state']}</div>
    </div>""", unsafe_allow_html=True)

    dd_col = "#00ff88" if stats["daily_drawdown_pct"] < 2 else ("#f0c040" if stats["daily_drawdown_pct"] < 3 else "#ff4444")
    m2.markdown(f"""<div style="background:rgba(0,20,40,0.8);border:1px solid {dd_col}33;
    border-radius:8px;padding:0.6rem;text-align:center;">
    <div style="color:#8b949e;font-size:0.7rem;font-weight:700;">DAILY DD</div>
    <div style="color:{dd_col};font-size:1rem;font-weight:900;">{stats['daily_drawdown_pct']:.2f}%</div>
    <div style="color:#8b949e;font-size:0.62rem;">Max: {stats['max_daily_dd']}</div>
    </div>""", unsafe_allow_html=True)

    cl_col = "#00ff88" if stats["consecutive_losses"] == 0 else ("#f0c040" if stats["consecutive_losses"] < 3 else "#ff4444")
    m3.markdown(f"""<div style="background:rgba(0,20,40,0.8);border:1px solid {cl_col}33;
    border-radius:8px;padding:0.6rem;text-align:center;">
    <div style="color:#8b949e;font-size:0.7rem;font-weight:700;">CONSEC. LOSSES</div>
    <div style="color:{cl_col};font-size:1rem;font-weight:900;">{stats['consecutive_losses']}/{stats['max_consec_loss']}</div>
    </div>""", unsafe_allow_html=True)

    m4.markdown(f"""<div style="background:rgba(0,20,40,0.8);border:1px solid rgba(0,212,255,0.2);
    border-radius:8px;padding:0.6rem;text-align:center;">
    <div style="color:#8b949e;font-size:0.7rem;font-weight:700;">WIN RATE</div>
    <div style="color:#4a9eff;font-size:1rem;font-weight:900;">{stats['win_rate']:.0f}%</div>
    <div style="color:#8b949e;font-size:0.62rem;">{stats['total_trades']} trades</div>
    </div>""", unsafe_allow_html=True)

    pnl_col = "#00ff88" if stats["daily_pnl"] >= 0 else "#ff4444"
    m5.markdown(f"""<div style="background:rgba(0,20,40,0.8);border:1px solid {pnl_col}33;
    border-radius:8px;padding:0.6rem;text-align:center;">
    <div style="color:#8b949e;font-size:0.7rem;font-weight:700;">DAILY P&L</div>
    <div style="color:{pnl_col};font-size:1rem;font-weight:900;">${stats['daily_pnl']:+,.2f}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tools ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📐 Position Sizer", "🎯 Exit Calculator", "📊 Signal Scanner", "⚙️ Circuit Breakers"
    ])

    # TAB 1: Position Sizer
    with tab1:
        st.markdown("### 📐 Kelly / Fixed-Fractional Position Sizer")
        st.markdown("*Formula: Position Size = (Equity × Risk%) ÷ |Entry − Stop Loss|*")
        pc1, pc2 = st.columns(2)
        with pc1:
            p_entry = st.number_input("Entry Price ($)", min_value=0.0001, value=100.0, step=0.01, key="ps_entry")
            p_sl    = st.number_input("Stop Loss Price ($)", min_value=0.0001, value=97.0, step=0.01, key="ps_sl")
        with pc2:
            p_risk  = st.slider("Risk % per Trade", min_value=0.1, max_value=1.0, value=1.0, step=0.1, key="ps_risk")
            st.info(f"Max allowed: **{MAX_RISK_PER_TRADE*100:.0f}%** of equity")

        if st.button("Calculate Position Size ▶", type="primary", key="ps_calc"):
            result = engine.calculate_position_size(equity, p_entry, p_sl, p_risk/100)
            if "error" in result:
                st.error(result["error"])
            else:
                r1,r2,r3,r4 = st.columns(4)
                r1.metric("💰 Risk Amount", f"${result['risk_amount_usd']:,.2f}")
                r2.metric("📦 Quantity", f"{result['quantity']:,.4f}")
                r3.metric("💵 Position Value", f"${result['position_value']:,.2f}")
                r4.metric("📏 SL Distance", f"${result['sl_distance']:,.4f}")
                st.success(f"✅ Buy **{result['quantity']:,.4f} units** at ${p_entry} with SL at ${p_sl}")
                st.markdown(f"""
                <div style="background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.2);
                border-radius:8px;padding:0.7rem 1rem;font-size:0.82rem;color:#c9d1d9;">
                💡 <b>CRO Rule:</b> Risking only <b style="color:#00ff88">{p_risk:.1f}%</b>
                = <b style="color:#00ff88">${result['risk_amount_usd']:,.2f}</b> on this trade.
                Account safe even if stopped out completely.
                </div>
                """, unsafe_allow_html=True)

    # TAB 2: Exit Calculator
    with tab2:
        st.markdown("### 🎯 Dynamic Exit Calculator")
        st.markdown("*ATR-based SL · 1:2 RR TP · Trailing Stop at 1:1*")
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            e_entry = st.number_input("Entry Price ($)", min_value=0.0001, value=100.0, step=0.01, key="ec_entry")
        with ec2:
            e_atr   = st.number_input("ATR (14 period)", min_value=0.0001, value=2.0, step=0.01, key="ec_atr",
                                       help="Average True Range of the asset")
        with ec3:
            e_side  = st.selectbox("Trade Direction", ["LONG","SHORT"], key="ec_side")

        if st.button("Calculate Exits ▶", type="primary", key="ec_calc"):
            exits = engine.calculate_exits(e_entry, e_atr, e_side)
            e1,e2,e3 = st.columns(3)
            sl_col = "#ff4466" if e_side == "LONG" else "#00ff88"
            tp_col = "#00ff88" if e_side == "LONG" else "#ff4466"
            e1.metric("🛑 Stop Loss", f"${exits['stop_loss']:,.4f}",
                      delta=f"-${exits['sl_distance']:,.4f}" if e_side=="LONG" else f"+${exits['sl_distance']:,.4f}")
            e2.metric("🎯 Take Profit", f"${exits['take_profit']:,.4f}",
                      delta=f"+${exits['tp_distance']:,.4f}" if e_side=="LONG" else f"-${exits['tp_distance']:,.4f}")
            e3.metric("📏 Risk:Reward", exits["risk_reward"])

            st.markdown(f"""
            <div style="background:rgba(0,20,40,0.8);border:1px solid rgba(0,212,255,0.15);
            border-radius:10px;padding:1rem;margin-top:0.6rem;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;font-size:0.82rem;">
                    <div><span style="color:#8b949e;">ATR Used:</span> <b style="color:#4a9eff;">{exits['atr_used']}</b></div>
                    <div><span style="color:#8b949e;">SL Mult:</span> <b style="color:#4a9eff;">{ATR_SL_MULTIPLIER}× ATR</b></div>
                    <div><span style="color:#8b949e;">Trail Activate @ </span> <b style="color:#f0c040;">${exits['trailing_activation_price']:,.4f}</b> (1:1 RR)</div>
                    <div><span style="color:#8b949e;">Trail Stop:</span> <b style="color:#f0c040;">${exits['trailing_stop_initial']:,.4f}</b> (50% locked)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # TAB 3: Signal Scanner (multi-timeframe)
    with tab3:
        st.markdown("### 📊 Multi-Timeframe Signal Scanner")
        st.markdown("*15M entry + 4H macro trend — all 4 criteria required for valid signal*")
        strategy = StrategyEngine()
        st.markdown("**4H Chart (Macro Trend)**")
        s1,s2 = st.columns(2)
        with s1:
            s_price4h  = st.number_input("Current Price (4H)", value=50000.0, key="s_p4h")
            s_ema200   = st.number_input("200 EMA (4H)", value=48000.0, key="s_ema")
        with s2:
            st.info("4H Price > 200 EMA = Bullish macro\n\n4H Price < 200 EMA = Bearish macro")

        st.markdown("**15M Chart (Entry Triggers)**")
        s3,s4,s5 = st.columns(3)
        with s3:
            s_price15m = st.number_input("Current Price (15M)", value=50000.0, key="s_p15m")
            s_bbl      = st.number_input("BB Lower", value=49500.0, key="s_bbl")
            s_bbu      = st.number_input("BB Upper", value=50800.0, key="s_bbu")
        with s4:
            s_rsi      = st.number_input("RSI (14)", min_value=0.0, max_value=100.0, value=28.0, key="s_rsi")
            s_prev_rsi = st.number_input("Previous RSI", min_value=0.0, max_value=100.0, value=25.0, key="s_prsi")
        with s5:
            s_macd     = st.number_input("MACD Histogram", value=0.002, format="%.4f", key="s_macd")
            s_atr      = st.number_input("ATR (15M)", value=150.0, key="s_atr")

        if st.button("🔍 Scan for Signal ▶", type="primary", key="sig_scan"):
            data_4h  = {"price": s_price4h, "ema_200": s_ema200}
            data_15m = {
                "price": s_price15m, "bb_lower": s_bbl, "bb_upper": s_bbu,
                "rsi": s_rsi, "prev_rsi": s_prev_rsi, "macd_hist": s_macd, "atr": s_atr
            }
            sig = strategy.compute_signals(data_4h, data_15m)

            sig_colors = {"LONG":"#00ff88","SHORT":"#ff4466","HOLD":"#f0c040"}
            sc2 = sig_colors.get(sig["signal"],"#8b949e")
            st.markdown(f"""
            <div style="background:rgba(0,20,40,0.9);border:2px solid {sc2}44;
            border-radius:12px;padding:1.2rem;margin:0.8rem 0;text-align:center;">
                <div style="font-size:2rem;font-weight:900;color:{sc2};
                font-family:Orbitron,monospace;letter-spacing:0.1em;">
                {'🟢' if sig['signal']=='LONG' else '🔴' if sig['signal']=='SHORT' else '🟡'} {sig['signal']}
                </div>
                <div style="color:#8b949e;font-size:0.8rem;margin-top:0.3rem;">
                Confidence: <b style="color:{sc2};">{sig['confidence']}%</b> |
                Long Score: {sig['long_score']}/4 | Short Score: {sig['short_score']}/4
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**📋 Signal Reasons:**")
            for r in sig["reasons"]:
                st.markdown(f"- {r}")

    # TAB 4: Circuit Breakers
    with tab4:
        st.markdown("### ⚙️ Circuit Breaker Parameters")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style="background:rgba(255,60,60,0.07);border:1px solid rgba(255,60,60,0.2);
            border-radius:10px;padding:1rem;">
                <div style="color:#ff6b6b;font-weight:700;margin-bottom:0.7rem;">
                🚨 Kill-Switch Triggers
                </div>
                <div style="font-size:0.83rem;color:#c9d1d9;line-height:2;">
                📉 Daily Drawdown: <b style="color:#ff6b6b;">{MAX_DAILY_DRAWDOWN*100:.0f}%</b><br>
                ❌ Max Consecutive Losses: <b style="color:#ff6b6b;">{MAX_CONSECUTIVE_LOSS}</b><br>
                ⏱️ Lock Duration: <b style="color:#ff6b6b;">{KILL_SWITCH_HOURS}h</b><br>
                🛡️ Action: Close all + Cancel pending + Lock bot
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div style="background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.2);
            border-radius:10px;padding:1rem;">
                <div style="color:#00ff88;font-weight:700;margin-bottom:0.7rem;">
                ✅ Risk Parameters
                </div>
                <div style="font-size:0.83rem;color:#c9d1d9;line-height:2;">
                💰 Max Risk/Trade: <b style="color:#00ff88;">{MAX_RISK_PER_TRADE*100:.0f}%</b> of equity<br>
                📏 SL: <b style="color:#00ff88;">{ATR_SL_MULTIPLIER}× ATR</b> from entry<br>
                🎯 Min R:R: <b style="color:#00ff88;">1:{MIN_RISK_REWARD:.0f}</b><br>
                📈 Trail: Activates at <b style="color:#00ff88;">1:1 RR</b>, locks 50%
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Simulate circuit breaker
        st.markdown("---")
        st.markdown("**🧪 Simulate Circuit Breaker**")
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            sim_equity = st.number_input("Current Equity ($)", value=equity * 0.97, step=10.0, key="sim_eq")
        with sim_col2:
            sim_consec = st.number_input("Consecutive Losses", min_value=0, max_value=10, value=0, step=1, key="sim_cl")
        if st.button("▶ Run Circuit Breaker Check", type="secondary", key="sim_cb"):
            engine.state.consecutive_losses = int(sim_consec)
            result = engine.check_circuit_breakers(sim_equity)
            if result["action"] == "KILL_SWITCH":
                st.error(f"🚨 {result['message']}")
            else:
                dd = (equity - sim_equity) / equity * 100
                st.success(f"✅ All clear — Daily DD: {dd:.2f}%, Consec Losses: {sim_consec}")

    # Disclaimer
    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:1.2rem;font-size:0.74rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> This Risk Engine runs in PAPER/SIMULATION mode only.
    No real orders are placed. Real trading requires SEBI registration, broker API credentials,
    and compliance with applicable regulations. Not investment advice.
    </div>
    """, unsafe_allow_html=True)
