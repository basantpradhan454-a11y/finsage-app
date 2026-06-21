"""
FinSage AI - Strategy Demo Bot
User describes a trading strategy (plain language or Pine Script) -> AI parses it ->
deterministic backtest engine runs it on real data -> AI narrates results in voice.
Connects to the embedded TradingView widget + lightweight charts for visual drawing.

IMPORTANT: This is DEMO / PAPER TRADING only. No real money.
"""

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import re
import time
from datetime import datetime, date

# --- Import shared helpers ---
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_URL

# --- Indicator helpers (same as backtester) ---
def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean()
    al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))

def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s, f) - _ema(s, sl)
    return m, _ema(m, sig)

def _bb(s, n=20, k=2):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m + k*sd, m, m - k*sd

def _atr(h, l, c, n=14):
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(com=n-1, min_periods=n).mean()


# =====================================================================
# 1. STRATEGY PARSER - Plain Language -> Structured Rules
# =====================================================================
STRATEGY_PARSE_SYSTEM = """You are a trading strategy parser. Convert the user's plain-language
strategy description into a structured JSON strategy object.

Return ONLY valid JSON with this structure:
{
  "strategy_name": "string",
  "timeframe": "1d|1h|15m|5m|1w",
  "entry_conditions": [
    {"indicator": "RSI", "operator": "<", "value": 30, "description": "RSI below 30"}
  ],
  "exit_conditions": [
    {"indicator": "RSI", "operator": ">", "value": 70, "description": "RSI above 70"}
  ],
  "filters": [
    {"indicator": "EMA", "period": 200, "operator": ">", "reference": "price", "description": "Price above EMA 200"}
  ],
  "risk_rules": {
    "stop_loss_pct": 5.0,
    "take_profit_pct": 10.0,
    "position_size_pct": 95.0
  },
  "indicators_needed": ["RSI", "EMA200"],
  "is_complete": true,
  "missing_fields": [],
  "clarification_questions": []
}

Rules:
- If stop loss or take profit is NOT mentioned, set is_complete=false and ask about it
- If timeframe is not mentioned, default to "1d" but note in missing_fields
- Parse operators: <, >, <=, >=, crosses_above, crosses_below
- indicators: RSI, EMA, SMA, MACD, Bollinger Bands, VWAP, ATR, Stochastic
- Always include risk_rules even if empty (set defaults)
- If strategy is ambiguous, set is_complete=false and list clarification_questions
- Return ONLY JSON, no other text"""


def _call_groq(messages, max_tokens=2000, temperature=0.3):
    """Call Groq API."""
    import urllib.request
    if not GROQ_API_KEY:
        return None
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(GROQ_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Groq API error: {e}")
        return None


def parse_strategy_text(text):
    """Parse plain language strategy via Groq AI."""
    if not GROQ_API_KEY:
        return _rule_parse_strategy(text)

    messages = [
        {"role": "system", "content": STRATEGY_PARSE_SYSTEM},
        {"role": "user", "content": f"Parse this strategy: {text}"},
    ]
    raw = _call_groq(messages, max_tokens=1500, temperature=0.2)
    if not raw:
        return _rule_parse_strategy(text)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass
    return _rule_parse_strategy(text)


def _rule_parse_strategy(text):
    """Fallback parser when no API key - basic keyword matching."""
    t = text.lower()
    strategy = {
        "strategy_name": "Custom Strategy",
        "timeframe": "1d",
        "entry_conditions": [],
        "exit_conditions": [],
        "filters": [],
        "risk_rules": {"stop_loss_pct": 0, "take_profit_pct": 0, "position_size_pct": 95},
        "indicators_needed": [],
        "is_complete": True,
        "missing_fields": [],
        "clarification_questions": [],
    }

    # RSI detection
    if "rsi" in t:
        rsi_match = re.search(r'rsi\s*(?:below|<|less than|under)\s*(\d+)', t)
        if rsi_match:
            strategy["entry_conditions"].append({
                "indicator": "RSI", "operator": "<", "value": int(rsi_match.group(1)),
                "description": f"RSI below {rsi_match.group(1)}"
            })
        rsi_sell = re.search(r'rsi\s*(?:above|>|greater than|over)\s*(\d+)', t)
        if rsi_sell:
            strategy["exit_conditions"].append({
                "indicator": "RSI", "operator": ">", "value": int(rsi_sell.group(1)),
                "description": f"RSI above {rsi_sell.group(1)}"
            })
        strategy["indicators_needed"].append("RSI")

    # EMA detection
    if "ema" in t or "moving average" in t:
        ema_match = re.search(r'ema\s*(\d+)', t)
        period = int(ema_match.group(1)) if ema_match else 200
        strategy["filters"].append({
            "indicator": "EMA", "period": period, "operator": ">", "reference": "price",
            "description": f"Price above EMA {period}"
        })
        strategy["indicators_needed"].append(f"EMA{period}")

    # MACD detection
    if "macd" in t:
        strategy["entry_conditions"].append({
            "indicator": "MACD", "operator": "crosses_above", "value": "signal",
            "description": "MACD crosses above signal line"
        })
        strategy["exit_conditions"].append({
            "indicator": "MACD", "operator": "crosses_below", "value": "signal",
            "description": "MACD crosses below signal line"
        })
        strategy["indicators_needed"].append("MACD")

    # Stop loss detection
    sl_match = re.search(r'stop.?loss\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*%', t)
    if sl_match:
        strategy["risk_rules"]["stop_loss_pct"] = float(sl_match.group(1))
    else:
        strategy["is_complete"] = False
        strategy["missing_fields"].append("stop_loss")
        strategy["clarification_questions"].append("What stop-loss percentage would you like? (e.g., 5%)")

    # Take profit detection
    tp_match = re.search(r'(?:take.?profit|target)\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*%', t)
    if tp_match:
        strategy["risk_rules"]["take_profit_pct"] = float(tp_match.group(1))

    # Timeframe
    if "intraday" in t or "15m" in t or "15 min" in t:
        strategy["timeframe"] = "15m"
    elif "hourly" in t or "1h" in t or "1 hour" in t:
        strategy["timeframe"] = "1h"
    elif "weekly" in t or "1w" in t:
        strategy["timeframe"] = "1w"

    return strategy


def parse_pine_script(code):
    """Parse Pine Script v4/v5 into structured strategy."""
    strategy = {
        "strategy_name": "Pine Script Strategy",
        "timeframe": "1d",
        "entry_conditions": [],
        "exit_conditions": [],
        "filters": [],
        "risk_rules": {"stop_loss_pct": 0, "take_profit_pct": 0, "position_size_pct": 95},
        "indicators_needed": [],
        "is_complete": True,
        "missing_fields": [],
        "clarification_questions": [],
        "pine_script": code,
    }

    name_match = re.search(r'strategy\s*\(\s*"([^"]+)"', code)
    if name_match:
        strategy["strategy_name"] = name_match.group(1)

    if re.search(r'rsi\s*\(', code, re.IGNORECASE):
        rsi_val = re.search(r'rsi\s*\([^)]+\)\s*([<>=!]+)\s*(\d+)', code, re.IGNORECASE)
        if rsi_val:
            strategy["entry_conditions"].append({
                "indicator": "RSI", "operator": "<" if "<" in rsi_val.group(1) else ">",
                "value": int(rsi_val.group(2)),
                "description": f"RSI {rsi_val.group(1)} {rsi_val.group(2)}"
            })
        strategy["indicators_needed"].append("RSI")

    ema_match = re.search(r'ema\s*\(\s*(?:close\s*,\s*)?(\d+)\s*\)', code, re.IGNORECASE)
    sma_match = re.search(r'sma\s*\(\s*(?:close\s*,\s*)?(\d+)\s*\)', code, re.IGNORECASE)
    if ema_match:
        period = int(ema_match.group(1))
        strategy["indicators_needed"].append(f"EMA{period}")
        strategy["filters"].append({
            "indicator": "EMA", "period": period, "operator": ">", "reference": "price",
            "description": f"EMA {period} filter"
        })
    if sma_match:
        period = int(sma_match.group(1))
        strategy["indicators_needed"].append(f"SMA{period}")

    if re.search(r'macd\s*\(', code, re.IGNORECASE):
        strategy["indicators_needed"].append("MACD")
        strategy["entry_conditions"].append({
            "indicator": "MACD", "operator": "crosses_above", "value": "signal",
            "description": "MACD crossover"
        })

    sl_match = re.search(r'strategy\.exit.*stop\s*=\s*(\d+(?:\.\d+)?)', code, re.IGNORECASE)
    if sl_match:
        strategy["risk_rules"]["stop_loss_pct"] = float(sl_match.group(1))

    tf_match = re.search(r'resolution\s*=\s*"([^"]+)"', code)
    if tf_match:
        strategy["timeframe"] = tf_match.group(1)

    return strategy


# =====================================================================
# 2. DETERMINISTIC BACKTEST ENGINE
# =====================================================================
def run_strategy_backtest(df, strategy, initial_capital=100000):
    """Run deterministic backtest from parsed strategy. NO AI guessing."""
    if df.empty or len(df) < 50:
        return {"error": "Insufficient data (need 50+ candles)"}

    c = df["Close"].copy()
    h = df["High"].copy()
    l = df["Low"].copy()

    signals = pd.Series(0, index=df.index)
    indicators_data = {}
    needed = strategy.get("indicators_needed", [])

    # Compute indicators
    if any("RSI" in n for n in needed):
        indicators_data["RSI"] = _rsi(c)
    if any("MACD" in n for n in needed):
        macd, macd_sig = _macd(c)
        indicators_data["MACD"] = macd
        indicators_data["MACD_Signal"] = macd_sig
    for n in needed:
        ema_m = re.match(r'EMA(\d+)', n)
        sma_m = re.match(r'SMA(\d+)', n)
        if ema_m:
            indicators_data[f"EMA{ema_m.group(1)}"] = _ema(c, int(ema_m.group(1)))
        if sma_m:
            indicators_data[f"SMA{sma_m.group(1)}"] = c.rolling(int(sma_m.group(1))).mean()

    # Apply entry conditions
    for cond in strategy.get("entry_conditions", []):
        ind = cond.get("indicator", "")
        op = cond.get("operator", "")
        val = cond.get("value", 0)

        if ind == "RSI" and "RSI" in indicators_data:
            r = indicators_data["RSI"]
            if op == "<": signals[r < val] = 1
            elif op == ">": signals[r > val] = 1
        elif ind == "MACD" and "MACD" in indicators_data:
            m = indicators_data["MACD"]; s = indicators_data["MACD_Signal"]
            if op == "crosses_above":
                signals[(m > s) & (m.shift() <= s.shift())] = 1
            elif op == "crosses_below":
                signals[(m < s) & (m.shift() >= s.shift())] = 1

    # Apply exit conditions
    for cond in strategy.get("exit_conditions", []):
        ind = cond.get("indicator", "")
        op = cond.get("operator", "")
        val = cond.get("value", 0)

        if ind == "RSI" and "RSI" in indicators_data:
            r = indicators_data["RSI"]
            if op == ">": signals[r > val] = -1
            elif op == "<": signals[r < val] = -1
        elif ind == "MACD" and "MACD" in indicators_data:
            m = indicators_data["MACD"]; s = indicators_data["MACD_Signal"]
            if op == "crosses_below":
                signals[(m < s) & (m.shift() >= s.shift())] = -1
            elif op == "crosses_above":
                signals[(m > s) & (m.shift() <= s.shift())] = -1

    # Apply filters
    for filt in strategy.get("filters", []):
        ind = filt.get("indicator", "")
        period = filt.get("period", 200)
        if ind == "EMA" and f"EMA{period}" in indicators_data:
            ema = indicators_data[f"EMA{period}"]
            signals[(signals == 1) & (c < ema)] = 0

    # Simulate trades
    risk = strategy.get("risk_rules", {})
    sl_pct = risk.get("stop_loss_pct", 0)
    tp_pct = risk.get("take_profit_pct", 0)
    pos_pct = risk.get("position_size_pct", 95) / 100

    cash = initial_capital
    position = 0.0
    entry_px = 0.0
    entry_date = None
    trades = []
    equity = []
    in_trade = False
    markers = []

    for i, (ts, row) in enumerate(df.iterrows()):
        price = float(row["Close"])
        sig = int(signals.iloc[i])

        if in_trade and entry_px > 0:
            exit_reason = None
            if sl_pct > 0 and price <= entry_px * (1 - sl_pct / 100):
                exit_reason = "Stop Loss"
            elif tp_pct > 0 and price >= entry_px * (1 + tp_pct / 100):
                exit_reason = "Take Profit"

            if exit_reason:
                pnl = (price - entry_px) * position
                cash += position * price
                trades.append({
                    "entry_date": entry_date.strftime("%Y-%m-%d"),
                    "exit_date": ts.strftime("%Y-%m-%d"),
                    "entry_price": round(entry_px, 4),
                    "exit_price": round(price, 4),
                    "units": round(position, 4),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((price / entry_px - 1) * 100, 2),
                    "exit_reason": exit_reason,
                    "entry_index": df.index.get_loc(entry_date),
                    "exit_index": i,
                })
                markers.append({"type": "exit", "index": i, "price": price, "reason": exit_reason, "pnl": round(pnl, 2)})
                position = 0; in_trade = False; entry_px = 0

        if sig == 1 and not in_trade and cash > 0:
            invest = cash * pos_pct
            position = invest / price
            cash -= invest
            entry_px = price
            entry_date = ts
            in_trade = True
            markers.append({"type": "entry", "index": i, "price": price, "reason": "Signal"})

        elif sig == -1 and in_trade:
            pnl = (price - entry_px) * position
            cash += position * price
            trades.append({
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "exit_date": ts.strftime("%Y-%m-%d"),
                "entry_price": round(entry_px, 4),
                "exit_price": round(price, 4),
                "units": round(position, 4),
                "pnl": round(pnl, 2),
                "pnl_pct": round((price / entry_px - 1) * 100, 2),
                "exit_reason": "Signal Exit",
                "entry_index": df.index.get_loc(entry_date),
                "exit_index": i,
            })
            markers.append({"type": "exit", "index": i, "price": price, "reason": "Signal", "pnl": round(pnl, 2)})
            position = 0; in_trade = False; entry_px = 0

        eq = cash + (position * price if in_trade else 0)
        equity.append({"date": ts.strftime("%Y-%m-%d"), "equity": round(eq, 2)})

    if in_trade and entry_px > 0:
        final_price = float(df["Close"].iloc[-1])
        pnl = (final_price - entry_px) * position
        cash += position * final_price
        trades.append({
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "exit_date": df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(entry_px, 4),
            "exit_price": round(final_price, 4),
            "units": round(position, 4),
            "pnl": round(pnl, 2),
            "pnl_pct": round((final_price / entry_px - 1) * 100, 2),
            "exit_reason": "End of Data",
            "entry_index": df.index.get_loc(entry_date),
            "exit_index": len(df) - 1,
        })
        markers.append({"type": "exit", "index": len(df) - 1, "price": final_price, "reason": "End", "pnl": round(pnl, 2)})

    # Statistics
    total_trades = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades else 0
    avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
    avg_loss = np.mean([t["pnl"] for t in losses]) if losses else 0
    total_pnl = sum(t["pnl"] for t in trades)
    total_return = ((cash - initial_capital) / initial_capital * 100) if initial_capital else 0

    eq_values = [e["equity"] for e in equity]
    peak = eq_values[0] if eq_values else initial_capital
    max_dd = 0
    for ev in eq_values:
        if ev > peak: peak = ev
        dd = (peak - ev) / peak * 100
        if dd > max_dd: max_dd = dd

    best_trade = max(trades, key=lambda x: x["pnl"]) if trades else None
    worst_trade = min(trades, key=lambda x: x["pnl"]) if trades else None
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # Convert indicators for chart
    ind_data_clean = {}
    for k, v in indicators_data.items():
        if hasattr(v, 'dropna'):
            ind_data_clean[k] = {str(ts): round(float(val), 2) for ts, val in v.dropna().to_dict().items()}

    return {
        "trades": trades,
        "markers": markers,
        "equity_curve": equity,
        "stats": {
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "risk_reward": round(rr_ratio, 2),
            "initial_capital": initial_capital,
            "final_capital": round(cash, 2),
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        },
        "indicators_data": ind_data_clean,
    }


# =====================================================================
# 3. AI NARRATION
# =====================================================================
NARRATION_SYSTEM = """You are a trading educator narrating a strategy backtest.
Given the strategy and backtest results, generate a natural, conversational voice narration
in Hinglish (Hindi + English mix). Sound like an expert trader sitting next to the user.

Return JSON with:
{
  "segments": [
    {"text": "narration text", "type": "intro|trade|summary|warning"}
  ]
}

Rules:
- Hinglish tone - natural, conversational
- Explain WHAT happened, WHY the strategy triggered, and the OUTCOME
- For each trade, mention: entry price, why entry triggered, exit price, P&L
- At the end, give honest assessment: does the strategy have an edge?
- Mention weaknesses honestly (e.g., "choppy markets mein false signals aaye")
- Mention sample size limitations if few trades
- NO direct financial advice - educational only
- 60-120 seconds total narration
- Return ONLY JSON"""


def generate_narration(strategy, results, symbol):
    """Generate voice narration segments from backtest results."""
    stats = results.get("stats", {})
    trades = results.get("trades", [])

    if not GROQ_API_KEY:
        return _rule_narration(strategy, results, symbol)

    context = f"""
Strategy: {strategy.get('strategy_name', 'Custom')}
Symbol: {symbol}
Timeframe: {strategy.get('timeframe', '1d')}

Entry Conditions: {json.dumps(strategy.get('entry_conditions', []))}
Exit Conditions: {json.dumps(strategy.get('exit_conditions', []))}
Risk Rules: {json.dumps(strategy.get('risk_rules', {}))}

Backtest Results:
- Total Trades: {stats.get('total_trades', 0)}
- Win Rate: {stats.get('win_rate', 0)}%
- Total P&L: {stats.get('total_pnl', 0)}
- Total Return: {stats.get('total_return', 0)}%
- Max Drawdown: {stats.get('max_drawdown', 0)}%
- Risk/Reward: {stats.get('risk_reward', 0)}
- Avg Win: {stats.get('avg_win', 0)}
- Avg Loss: {stats.get('avg_loss', 0)}

Top 3 Trades: {json.dumps(trades[:3])}
"""

    messages = [
        {"role": "system", "content": NARRATION_SYSTEM},
        {"role": "user", "content": context},
    ]
    raw = _call_groq(messages, max_tokens=2000, temperature=0.5)
    if not raw:
        return _rule_narration(strategy, results, symbol)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return data.get("segments", [])
    except json.JSONDecodeError:
        pass
    return _rule_narration(strategy, results, symbol)


def _rule_narration(strategy, results, symbol):
    """Fallback narration without AI."""
    stats = results.get("stats", {})
    trades = results.get("trades", [])
    segments = []

    segments.append({
        "text": f"Namaste! Main aapke strategy ko {symbol} par test kar raha hoon. "
                f"Strategy ka naam hai {strategy.get('strategy_name', 'Custom Strategy')}. "
                f"Timeframe: {strategy.get('timeframe', '1d')}. "
                f"Chaliye dekhte hain kaise perform kiya.",
        "type": "intro"
    })

    for cond in strategy.get("entry_conditions", [])[:2]:
        segments.append({
            "text": f"Entry rule: {cond.get('description', '')}. "
                    f"Jab yeh condition meet hui, humne buy kiya.",
            "type": "trade"
        })

    for t in trades[:5]:
        segments.append({
            "text": f"Trade on {t['entry_date']}: Entry at {t['entry_price']}, "
                    f"exit on {t['exit_date']} at {t['exit_price']}. "
                    f"P&L: {t['pnl']} ({t['pnl_pct']}%). "
                    f"Exit reason: {t['exit_reason']}.",
            "type": "trade"
        })

    wr = stats.get("win_rate", 0)
    total_ret = stats.get("total_return", 0)
    max_dd = stats.get("max_drawdown", 0)

    if total_ret > 0:
        assessment = f"Strategy ne positive return diya: {total_ret}%. "
    else:
        assessment = f"Strategy ne negative return diya: {total_ret}%. "

    segments.append({
        "text": f"Summary: {stats.get('total_trades', 0)} trades, win rate {wr}%, "
                f"total return {total_ret}%, max drawdown {max_dd}%. "
                f"{assessment}"
                f"Yeh backtest educational purpose ke liye hai - "
                f"past performance future results ki guarantee nahi.",
        "type": "summary"
    })

    if stats.get("total_trades", 0) < 10:
        segments.append({
            "text": f"Dhyan dein: sirf {stats.get('total_trades', 0)} trades huye, "
                    f"jo statistical significance ke liye kam hai. "
                    f"Zyada data par test karna chahiye.",
            "type": "warning"
        })
    if max_dd > 20:
        segments.append({
            "text": f"Max drawdown {max_dd}% hai - kaafi high. "
                    f"Risk management improve karna padega.",
            "type": "warning"
        })

    return segments


# =====================================================================
# 4. CHART RENDERING - Lightweight Charts with trade markers
# =====================================================================
def build_strategy_chart(df, results, symbol, indicators_data=None):
    """Build lightweight chart HTML with trade markers + indicator overlays."""
    plot_df = df.tail(200).copy()
    candles = []
    for ts, row in plot_df.iterrows():
        candles.append({
            "time": int(ts.timestamp()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        })

    offset = len(df) - len(plot_df)
    markers = []
    for m in results.get("markers", []):
        adj_idx = m["index"] - offset
        if 0 <= adj_idx < len(plot_df):
            ts = plot_df.index[adj_idx]
            markers.append({
                "type": m["type"],
                "time": int(ts.timestamp()),
                "price": m["price"],
                "reason": m.get("reason", ""),
                "pnl": m.get("pnl", 0),
            })

    # Build indicator line series
    ind_series = {}
    if indicators_data:
        for ind_name, ind_dict in indicators_data.items():
            if "EMA" in ind_name or "SMA" in ind_name:
                line_data = []
                items = list(ind_dict.items())[-200:]
                for ts_str, val in items:
                    try:
                        ts_dt = pd.Timestamp(ts_str)
                        line_data.append({"time": int(ts_dt.timestamp()), "value": round(float(val), 2)})
                    except Exception:
                        continue
                if line_data:
                    ind_series[ind_name] = {"type": "line", "data": line_data}

    candles_json = json.dumps(candles)
    markers_json = json.dumps(markers)
    ind_json = json.dumps(ind_series)

    return f"""
<div id="strategy-chart" style="height:500px;width:100%;background:#020609;border-radius:10px;overflow:hidden;"></div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function() {{
    const chart = LightweightCharts.createChart(document.getElementById('strategy-chart'), {{
        layout: {{ background: {{ color: '#020609' }}, textColor: '#8b949e' }},
        grid: {{ vertLines: {{ color: 'rgba(0,212,255,0.04)' }}, horzLines: {{ color: 'rgba(0,212,255,0.04)' }} }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{ borderColor: 'rgba(0,212,255,0.1)' }},
        timeScale: {{ borderColor: 'rgba(0,212,255,0.1)', timeVisible: true, secondsVisible: false }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#10b981', downColor: '#ef4444',
        borderUpColor: '#10b981', borderDownColor: '#ef4444',
        wickUpColor: '#10b981', wickDownColor: '#ef4444',
    }});
    candleSeries.setData({candles_json});

    const indData = {ind_json};
    const indColors = {{ "EMA20": "#fbbf24", "EMA50": "#a371f7", "EMA200": "#00d4ff",
                        "SMA20": "#fbbf24", "SMA50": "#a371f7", "SMA200": "#00d4ff" }};
    for (const [name, info] of Object.entries(indData)) {{
        if (info.type === "line") {{
            const lineSeries = chart.addLineSeries({{
                color: indColors[name] || "#8b949e",
                lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
            }});
            lineSeries.setData(info.data);
        }}
    }}

    const markers = {markers_json};
    const markerData = markers.map(m => {{
        const isEntry = m.type === "entry";
        const isWin = m.pnl > 0;
        return {{
            time: m.time,
            position: isEntry ? "belowBar" : "aboveBar",
            color: isEntry ? "#10b981" : (isWin ? "#00d4ff" : "#ef4444"),
            shape: isEntry ? "arrowUp" : "arrowDown",
            text: isEntry ? "BUY" : "SELL " + m.pnl,
        }};
    }});
    candleSeries.setMarkers(markerData);

    chart.timeScale().fitContent();
}})();
</script>
"""


# =====================================================================
# 5. VOICE NARRATION HTML
# =====================================================================
def build_voice_narration_html(segments):
    """Build voice narration player with transcript + controls."""
    if not segments:
        return ""

    transcript = "\\n".join([f"[{s.get('type','').upper()}] {s['text']}" for s in segments])
    segments_json = json.dumps([{"text": s["text"], "type": s.get("type","")} for s in segments])

    return f"""
<div id="voice-narration" style="background:linear-gradient(135deg,#050d1f,#091628);
border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:16px;margin:10px 0;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
    <div style="font-size:0.8rem;font-weight:800;color:#00d4ff;">AI Strategy Narration</div>
    <div style="margin-left:auto;display:flex;gap:6px;">
      <button id="voice-play" onclick="playNarration()"
       style="background:rgba(0,212,255,0.15);border:1px solid rgba(0,212,255,0.3);
       border-radius:6px;padding:5px 12px;color:#00d4ff;cursor:pointer;font-size:11px;">
       Play Voice</button>
      <button id="voice-pause" onclick="pauseNarration()"
       style="background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);
       border-radius:6px;padding:5px 12px;color:#8b949e;cursor:pointer;font-size:11px;">
       Pause</button>
      <button id="voice-stop" onclick="stopNarration()"
       style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
       border-radius:6px;padding:5px 12px;color:#ef4444;cursor:pointer;font-size:11px;">
       Stop</button>
    </div>
  </div>
  <div id="voice-status" style="font-size:0.72rem;color:#4a7a99;margin-bottom:8px;">
  Click Play to hear the AI explain the strategy results</div>
  <div id="transcript" style="font-size:0.78rem;color:#b0cce0;line-height:1.7;
  max-height:200px;overflow-y:auto;padding:8px;background:rgba(0,0,0,0.2);
  border-radius:8px;white-space:pre-wrap;">{transcript}</div>
</div>
<script>
const narrationSegments = {segments_json};
let currentSegment = 0;
let isPlaying = false;

function playNarration() {{
    if (!('speechSynthesis' in window)) {{
        document.getElementById('voice-status').textContent = 'Voice not supported in this browser';
        return;
    }}
    if (isPlaying) return;
    isPlaying = true;
    currentSegment = 0;
    speakNext();
}}

function speakNext() {{
    if (!isPlaying || currentSegment >= narrationSegments.length) {{
        isPlaying = false;
        document.getElementById('voice-status').textContent = 'Narration complete';
        return;
    }}
    const seg = narrationSegments[currentSegment];
    const utter = new SpeechSynthesisUtterance(seg.text);
    utter.rate = 0.95;
    utter.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha'));
    if (naturalVoice) utter.voice = naturalVoice;

    utter.onstart = () => {{
        document.getElementById('voice-status').textContent =
            'Speaking segment ' + (currentSegment + 1) + ' of ' + narrationSegments.length + '...';
    }};
    utter.onend = () => {{
        currentSegment++;
        speakNext();
    }};
    window.speechSynthesis.speak(utter);
}}

function pauseNarration() {{
    if (window.speechSynthesis.speaking) window.speechSynthesis.pause();
    document.getElementById('voice-status').textContent = 'Paused';
}}

function stopNarration() {{
    isPlaying = false;
    window.speechSynthesis.cancel();
    currentSegment = 0;
    document.getElementById('voice-status').textContent = 'Stopped';
}}
</script>
"""


# =====================================================================
# 6. SYMBOL + TIMEFRAME HELPERS
# =====================================================================
SYMBOL_MAP = {
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS", "icici": "ICICIBANK.NS", "sbi": "SBIN.NS",
    "wipro": "WIPRO.NS", "tata": "TATAMOTORS.NS", "adani": "ADANIENT.NS",
    "btc": "BTC-USD", "ethereum": "ETH-USD", "eth": "ETH-USD",
    "nifty": "^NSEI", "banknifty": "^NSEBANK", "sensex": "^BSESN",
    "apple": "AAPL", "tesla": "TSLA", "google": "GOOGL", "amazon": "AMZN",
    "microsoft": "MSFT", "nvidia": "NVDA",
}

TF_MAP = {
    "1d": ("1y", "1d"), "1h": ("1mo", "1h"), "15m": ("5d", "15m"),
    "5m": ("1d", "5m"), "1w": ("5y", "1wk"),
}


def resolve_symbol(text):
    """Resolve user input to yfinance symbol."""
    t = text.lower().strip()
    if t in SYMBOL_MAP:
        return SYMBOL_MAP[t]
    for key, val in SYMBOL_MAP.items():
        if key in t:
            return val
    if not any(c in text for c in "^-.") and text.isalpha():
        return text.upper() + ".NS"
    return text.upper()


# =====================================================================
# 7. MAIN RENDER FUNCTION
# =====================================================================
def render_strategy_bot():
    """Main entry point for the AI Strategy Demo Bot page."""

    st.markdown("""
    <div style="background:linear-gradient(135deg,#050d1f,#091628);
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;box-shadow:0 0 30px rgba(0,212,255,0.06);">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <div style="font-size:1.3rem;">AI</div>
            <div>
                <div style="font-size:1.1rem;font-weight:800;
                background:linear-gradient(90deg,#00d4ff,#00b8d9);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                AI Strategy Demo Bot</div>
                <div style="color:#4a7a99;font-size:0.76rem;margin-top:2px;">
                Describe your strategy -> AI runs it on real charts -> Voice walkthrough</div>
            </div>
            <div style="margin-left:auto;background:rgba(255,185,0,0.1);
            border:1px solid rgba(255,185,0,0.3);border-radius:6px;
            padding:4px 10px;color:#ffd700;font-size:0.68rem;font-weight:700;">
            DEMO / PAPER TRADING - NO REAL MONEY</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "strat_bot_strategy" not in st.session_state:
        st.session_state.strat_bot_strategy = None
    if "strat_bot_results" not in st.session_state:
        st.session_state.strat_bot_results = None
    if "strat_bot_narration" not in st.session_state:
        st.session_state.strat_bot_narration = None
    if "strat_bot_symbol" not in st.session_state:
        st.session_state.strat_bot_symbol = "RELIANCE.NS"
    if "strat_bot_df" not in st.session_state:
        st.session_state.strat_bot_df = None
    if "strat_bot_saved" not in st.session_state:
        st.session_state.strat_bot_saved = []

    st.markdown("""<div style="background:rgba(255,185,0,0.05);
    border:1px solid rgba(255,185,0,0.15);border-radius:6px;
    padding:6px 12px;margin-bottom:12px;font-size:0.72rem;color:#ffd700;">
    DEMO / Paper Trading - No Real Money. Past backtest performance does not guarantee future results.
    Educational purpose only - not personalized financial advice.</div>""",
    unsafe_allow_html=True)

    # STEP 1: STRATEGY INPUT
    st.markdown("### Step 1: Define Your Strategy")
    input_tab1, input_tab2 = st.tabs(["Plain Language", "Pine Script Code"])

    with input_tab1:
        st.markdown("Describe your strategy in natural language:")
        strat_text = st.text_area(
            "Strategy Description",
            placeholder="e.g. Buy when RSI goes below 30 and price is above the 200 EMA. "
                       "Sell when RSI crosses above 70. Stop loss at 5%, take profit at 10%.",
            height=100, key="strat_text_input", label_visibility="collapsed"
        )
        col_sym, col_run = st.columns([3, 1])
        with col_sym:
            sym_input = st.text_input("Symbol (e.g. Reliance, BTC, AAPL)",
                                     value="RELIANCE.NS", key="strat_sym")
        with col_run:
            if st.button("Parse & Run Backtest", type="primary",
                        use_container_width=True, key="strat_run_text"):
                _run_strategy_flow(strat_text, sym_input, is_pine=False)

    with input_tab2:
        st.markdown("Paste your TradingView Pine Script (v4/v5):")
        pine_code = st.text_area(
            "Pine Script Code",
            placeholder="//@version=5\nstrategy('RSI Reversal', overlay=true)\nrsiVal = rsi(close, 14)\nif rsiVal < 30\n    strategy.entry('Buy', strategy.long)\nif rsiVal > 70\n    strategy.close('Buy')",
            height=150, key="strat_pine_input", label_visibility="collapsed"
        )
        col_sym2, col_run2 = st.columns([3, 1])
        with col_sym2:
            sym_input2 = st.text_input("Symbol", value="RELIANCE.NS", key="strat_sym2")
        with col_run2:
            if st.button("Parse & Run Backtest", type="primary",
                        use_container_width=True, key="strat_run_pine"):
                _run_strategy_flow(pine_code, sym_input2, is_pine=True)

    # DISPLAY RESULTS
    strategy = st.session_state.strat_bot_strategy
    results = st.session_state.strat_bot_results

    if strategy:
        st.markdown("---")
        st.markdown("### Step 2: AI Parsed Strategy")

        if not strategy.get("is_complete", True):
            st.warning("Strategy is incomplete. Please answer these questions:")
            for q in strategy.get("clarification_questions", []):
                st.markdown(f"- {q}")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**Entry Conditions:**")
            for c in strategy.get("entry_conditions", []):
                st.markdown(f"- {c.get('description', c)}")
            st.markdown("**Exit Conditions:**")
            for c in strategy.get("exit_conditions", []):
                st.markdown(f"- {c.get('description', c)}")
        with col_s2:
            st.markdown("**Filters:**")
            for f in strategy.get("filters", []):
                st.markdown(f"- {f.get('description', f)}")
            risk = strategy.get("risk_rules", {})
            st.markdown(f"**Risk Rules:**")
            st.markdown(f"- Stop Loss: {risk.get('stop_loss_pct', 0)}%")
            st.markdown(f"- Take Profit: {risk.get('take_profit_pct', 0)}%")
            st.markdown(f"- Position Size: {risk.get('position_size_pct', 95)}%")

        if st.button("Save This Strategy", key="save_strat"):
            st.session_state.strat_bot_saved.append({
                "name": strategy.get("strategy_name", "Custom"),
                "strategy": strategy,
                "symbol": st.session_state.strat_bot_symbol,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            st.success("Strategy saved! You can re-run it later.")

    if results:
        st.markdown("---")
        st.markdown("### Step 3: Backtest Results")

        if results.get("error"):
            st.error(results["error"])
        else:
            stats = results.get("stats", {})
            s_cols = st.columns(6)
            stat_items = [
                ("Total Trades", stats.get("total_trades", 0), "#00d4ff"),
                ("Win Rate", f"{stats.get('win_rate', 0)}%", "#10b981" if stats.get("win_rate", 0) > 50 else "#ef4444"),
                ("Total Return", f"{stats.get('total_return', 0)}%", "#10b981" if stats.get("total_return", 0) > 0 else "#ef4444"),
                ("Max Drawdown", f"{stats.get('max_drawdown', 0)}%", "#ef4444"),
                ("Risk/Reward", stats.get("risk_reward", 0), "#fbbf24"),
                ("Final Capital", f"{stats.get('final_capital', 0):,.0f}", "#00d4ff"),
            ]
            for i, (label, val, color) in enumerate(stat_items):
                with s_cols[i]:
                    st.markdown(f"""<div style="background:linear-gradient(145deg,#050d1f,#071a30);
                    border:1px solid rgba(0,212,255,0.1);border-radius:8px;
                    padding:10px 6px;text-align:center;">
                    <div style="font-size:0.6rem;color:#4a7a99;text-transform:uppercase;
                    letter-spacing:0.05em;">{label}</div>
                    <div style="font-size:1rem;font-weight:800;color:{color};
                    font-family:JetBrains Mono,monospace;margin:4px 0;">{val}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("")
            st.markdown("### Strategy Chart - Entry/Exit Markers")
            df = st.session_state.strat_bot_df
            if df is not None and not df.empty:
                chart_html = build_strategy_chart(
                    df, results, st.session_state.strat_bot_symbol,
                    indicators_data=results.get("indicators_data")
                )
                components.html(chart_html, height=540, scrolling=False)

            st.markdown("")
            st.markdown("### Trade Log")
            trades = results.get("trades", [])
            if trades:
                trade_df = pd.DataFrame(trades)
                display_cols = ["entry_date", "exit_date", "entry_price", "exit_price",
                               "pnl", "pnl_pct", "exit_reason"]
                available_cols = [c for c in display_cols if c in trade_df.columns]
                st.dataframe(trade_df[available_cols], use_container_width=True, hide_index=True)

                col_bt, col_wt = st.columns(2)
                with col_bt:
                    best = stats.get("best_trade")
                    if best:
                        st.markdown(f"""<div style="background:rgba(16,185,129,0.06);
                        border:1px solid rgba(16,185,129,0.2);border-radius:8px;padding:10px;">
                        <b style="color:#10b981;">Best Trade</b><br>
                        <span style="font-size:0.8rem;color:#b0cce0;">
                        Entry: {best['entry_price']} -> Exit: {best['exit_price']}<br>
                        P&L: +{best['pnl']} ({best['pnl_pct']}%)</span></div>""",
                        unsafe_allow_html=True)
                with col_wt:
                    worst = stats.get("worst_trade")
                    if worst:
                        st.markdown(f"""<div style="background:rgba(239,68,68,0.06);
                        border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:10px;">
                        <b style="color:#ef4444;">Worst Trade</b><br>
                        <span style="font-size:0.8rem;color:#b0cce0;">
                        Entry: {worst['entry_price']} -> Exit: {worst['exit_price']}<br>
                        P&L: {worst['pnl']} ({worst['pnl_pct']}%)</span></div>""",
                        unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### Step 6: AI Strategy Assessment")
            _render_ai_assessment(stats, strategy)

            st.markdown("---")
            st.markdown("### Step 5: Voice Walkthrough")
            narration = st.session_state.strat_bot_narration
            if narration:
                voice_html = build_voice_narration_html(narration)
                components.html(voice_html, height=350, scrolling=False)
            else:
                if st.button("Generate Voice Narration", key="gen_narration"):
                    with st.spinner("AI preparing voice walkthrough..."):
                        narration = generate_narration(
                            strategy, results, st.session_state.strat_bot_symbol
                        )
                    st.session_state.strat_bot_narration = narration
                    st.rerun()

    if st.session_state.strat_bot_saved:
        st.markdown("---")
        st.markdown("### Saved Strategies")
        for i, saved in enumerate(st.session_state.strat_bot_saved):
            with st.expander(f"{saved['name']} - {saved['symbol']} ({saved['date']})"):
                st.json(saved["strategy"])
                if st.button("Re-run", key=f"rerun_{i}"):
                    st.session_state.strat_bot_strategy = saved["strategy"]
                    st.session_state.strat_bot_symbol = saved["symbol"]
                    _fetch_and_backtest(saved["symbol"], saved["strategy"])
                    st.rerun()


def _run_strategy_flow(text, symbol, is_pine):
    """Parse strategy -> fetch data -> backtest -> generate narration."""
    if not text.strip():
        st.error("Please enter a strategy description or Pine Script code.")
        return

    yf_sym = resolve_symbol(symbol)
    st.session_state.strat_bot_symbol = yf_sym

    with st.spinner("AI parsing your strategy..."):
        if is_pine:
            strategy = parse_pine_script(text)
        else:
            strategy = parse_strategy_text(text)

    if not strategy:
        st.error("Could not parse strategy. Please try again with more detail.")
        return

    st.session_state.strat_bot_strategy = strategy
    _fetch_and_backtest(yf_sym, strategy)

    if st.session_state.strat_bot_results and not st.session_state.strat_bot_results.get("error"):
        with st.spinner("AI preparing voice narration..."):
            narration = generate_narration(
                strategy, st.session_state.strat_bot_results, yf_sym
            )
        st.session_state.strat_bot_narration = narration


def _fetch_and_backtest(yf_sym, strategy):
    """Fetch historical data and run backtest."""
    tf = strategy.get("timeframe", "1d")
    period, interval = TF_MAP.get(tf, ("1y", "1d"))

    with st.spinner(f"Fetching {yf_sym} data ({tf})..."):
        try:
            df = yf.download(yf_sym, period=period, interval=interval, progress=False)
            if df.empty:
                st.error(f"No data found for {yf_sym}")
                return
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            st.session_state.strat_bot_df = df
        except Exception as e:
            st.error(f"Data fetch error: {e}")
            return

    with st.spinner("Running deterministic backtest..."):
        results = run_strategy_backtest(df, strategy)

    st.session_state.strat_bot_results = results


def _render_ai_assessment(stats, strategy):
    """Render AI assessment of the strategy."""
    total_trades = stats.get("total_trades", 0)
    win_rate = stats.get("win_rate", 0)
    total_return = stats.get("total_return", 0)
    max_dd = stats.get("max_drawdown", 0)
    rr = stats.get("risk_reward", 0)

    assessments = []

    if total_trades < 10:
        assessments.append(("warn", "Sample Size", f"Sirf {total_trades} trades - statistical significance ke liye kam. Zyada data par test karo."))
    else:
        if win_rate > 55 and total_return > 10:
            assessments.append(("good", "Potential Edge", f"Win rate {win_rate}% aur return {total_return}% - strategy mein edge ho sakti hai. Lekin overfitting check karo."))
        elif win_rate < 40:
            assessments.append(("bad", "No Edge", f"Win rate {win_rate}% - strategy kaam nahi kar rahi. Rules revise karo."))
        else:
            assessments.append(("warn", "Marginal", f"Win rate {win_rate}% - marginal performance. Improvement needed."))

    if max_dd > 25:
        assessments.append(("bad", "High Risk", f"Max drawdown {max_dd}% - bahut high. Stop-loss tighten karo ya position size kam karo."))
    elif max_dd > 15:
        assessments.append(("warn", "Moderate Risk", f"Max drawdown {max_dd}% - acceptable but monitor needed."))

    if rr > 1.5:
        assessments.append(("good", "Good R:R", f"Risk-reward ratio {rr} - winners losers se bade hain."))
    elif rr < 1:
        assessments.append(("warn", "Poor R:R", f"Risk-reward ratio {rr} - losers winners se bade hain. Take profit increase ya stop loss tighten karo."))

    needed = strategy.get("indicators_needed", [])
    if any("RSI" in n for n in needed) and not any("EMA" in n for n in needed):
        assessments.append(("warn", "Suggestion", "RSI-only strategies sideways markets mein false signals dete hain. Trend filter (EMA 200) add karo."))
    if not strategy.get("risk_rules", {}).get("stop_loss_pct"):
        assessments.append(("bad", "Critical", "Stop loss defined nahi hai - risk management mandatory hai."))

    for level, title, text in assessments:
        if level == "good":
            color = "#10b981"; bg = "rgba(16,185,129,0.05)"
        elif level == "bad":
            color = "#ef4444"; bg = "rgba(239,68,68,0.05)"
        else:
            color = "#ffd700"; bg = "rgba(255,185,0,0.05)"
        st.markdown(f"""<div style="background:{bg};
        border:1px solid {color}33;border-left:3px solid {color};
        border-radius:8px;padding:10px 14px;margin:6px 0;font-size:0.82rem;">
        <b style="color:{color};">{title}</b> <span style="color:#b0cce0;">{text}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:rgba(255,185,0,0.05);
    border:1px solid rgba(255,185,0,0.15);border-radius:6px;
    padding:8px 12px;margin-top:10px;font-size:0.72rem;color:#ffd700;">
    Yeh assessment educational hai. Backtest results future performance ki guarantee nahi.
    Real trading mein slippage, fees, aur market conditions differ hote hain.</div>""",
    unsafe_allow_html=True)
