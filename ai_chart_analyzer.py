"""
FinSage AI — Chart Image Analyzer
Upload any chart screenshot → AI detects levels, patterns, indicators
→ Annotated photo + White Paper report (white bg, black text)
"""
import streamlit as st
import streamlit.components.v1 as components
import base64, os, json, requests
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

def _key(n):
    try: return st.secrets.get(n) or os.environ.get(n, "")
    except: return os.environ.get(n, "")

GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL   = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ─────────────────────────────────────────────────────────────────────────────

def _img_to_b64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode()

def _call_vision_api(img_b64: str, prompt: str) -> str:
    """Try OpenAI GPT-4o Vision → fallback to Groq llama-3.2-90b-vision."""
    openai_key = _key("OPENAI_API_KEY")
    groq_key   = _key("GROQ_API_KEY")

    # Try OpenAI GPT-4o first
    if openai_key:
        try:
            resp = requests.post(OPENAI_URL, headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }, json={
                "model": "gpt-4o",
                "max_tokens": 4000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"], "GPT-4o"
        except Exception as e:
            pass

    # Groq llama-3.2-90b-vision
    if groq_key:
        try:
            resp = requests.post(GROQ_URL, headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }, json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "max_tokens": 4000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"], "Groq Vision"
        except:
            pass

    return None, None

VISION_PROMPT = """You are a professional financial chart analyst. Analyze this trading chart image in EXTREME detail.

Return a JSON object with EXACTLY this structure (no markdown, pure JSON):
{
  "ticker": "detected symbol or UNKNOWN",
  "timeframe": "detected timeframe e.g. 1D, 4H, 1H, 15m",
  "chart_type": "Candlestick/Line/Bar",
  "current_price": 0.0,
  "trend": "BULLISH/BEARISH/SIDEWAYS",
  "trend_strength": "STRONG/MODERATE/WEAK",
  "support_levels": [{"price": 0.0, "strength": "STRONG/MODERATE/WEAK", "note": "description"}],
  "resistance_levels": [{"price": 0.0, "strength": "STRONG/MODERATE/WEAK", "note": "description"}],
  "patterns_detected": [{"name": "pattern name", "type": "BULLISH/BEARISH/NEUTRAL", "location": "where on chart", "significance": "what it means"}],
  "candlestick_patterns": [{"name": "candle pattern", "type": "BULLISH/BEARISH/NEUTRAL", "action": "what to do"}],
  "indicators_visible": [{"name": "indicator name", "reading": "current value/state", "signal": "BULLISH/BEARISH/NEUTRAL", "explanation": "what it means"}],
  "volume_analysis": {"trend": "INCREASING/DECREASING/FLAT", "observation": "volume behavior description", "signal": "BULLISH/BEARISH/NEUTRAL"},
  "fibonacci_levels": [{"level": "0.382/0.5/0.618", "price": 0.0}],
  "entry_zone": {"price_from": 0.0, "price_to": 0.0, "reason": "why enter here"},
  "stop_loss": {"price": 0.0, "reason": "why this stop"},
  "targets": [{"price": 0.0, "label": "T1/T2/T3", "rr_ratio": "1:2"}],
  "order_flow": {"buying_pressure": "HIGH/MODERATE/LOW", "selling_pressure": "HIGH/MODERATE/LOW", "imbalance_zones": ["description"]},
  "liquidity": {"buy_side_liq": "description", "sell_side_liq": "description", "hvn": 0.0, "lvn": 0.0},
  "key_observations": ["observation 1", "observation 2", "observation 3"],
  "trading_bias": "LONG/SHORT/WAIT",
  "confidence_score": 75,
  "executive_summary": "2-3 sentence professional summary of what this chart is showing",
  "indicator_summary": "What all visible indicators collectively suggest",
  "volume_narrative": "Detailed explanation of volume behavior and what it reveals about buying/selling pressure",
  "risk_assessment": "LOW/MEDIUM/HIGH — with explanation"
}

Be specific with price levels if visible. If a value is not visible in the chart, use 0 for numbers or descriptive text."""


def _draw_annotations_on_image(img_bytes: bytes, analysis: dict) -> bytes:
    """Draw S/R levels, patterns, and measurements on the chart image."""
    if not PIL_OK:
        return img_bytes
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")
        W, H = img.size

        # Try to load a font
        try:
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
            font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except:
            font_sm = ImageFont.load_default()
            font_xs = font_sm

        cur  = analysis.get("current_price", 0)
        supps = analysis.get("support_levels", [])
        resis = analysis.get("resistance_levels", [])
        pats  = analysis.get("patterns_detected", [])

        # If prices are available, draw horizontal lines
        # Estimate price-to-pixel mapping from support/resistance
        all_prices = [s["price"] for s in supps if s.get("price",0)>0] + \
                     [r["price"] for r in resis if r.get("price",0)>0]
        if cur > 0:
            all_prices.append(cur)

        if len(all_prices) >= 2:
            p_min = min(all_prices) * 0.995
            p_max = max(all_prices) * 1.005
            p_range = p_max - p_min

            def price_to_y(price):
                if p_range == 0: return H // 2
                # Charts typically have price axis inverted (higher = top)
                ratio = (p_max - price) / p_range
                return int(ratio * H * 0.85 + H * 0.05)

            # Draw support lines (green)
            for i, s in enumerate(supps[:4]):
                if s.get("price", 0) > 0:
                    y = price_to_y(s["price"])
                    if 10 < y < H-10:
                        # Dashed line effect
                        for x in range(0, W, 16):
                            draw.line([(x, y), (min(x+10, W), y)], fill=(34,197,94,200), width=2)
                        # Label
                        lbl = f"S{i+1}: {s['price']:.2f} ({s.get('strength','')[:3]})"
                        draw.rectangle([W-145, y-14, W-5, y+4], fill=(0,0,0,170))
                        draw.text((W-140, y-13), lbl, fill=(34,197,94), font=font_xs)

            # Draw resistance lines (red)
            for i, r in enumerate(resis[:4]):
                if r.get("price", 0) > 0:
                    y = price_to_y(r["price"])
                    if 10 < y < H-10:
                        for x in range(0, W, 16):
                            draw.line([(x, y), (min(x+10, W), y)], fill=(239,68,68,200), width=2)
                        lbl = f"R{i+1}: {r['price']:.2f} ({r.get('strength','')[:3]})"
                        draw.rectangle([W-145, y-14, W-5, y+4], fill=(0,0,0,170))
                        draw.text((W-140, y-13), lbl, fill=(239,68,68), font=font_xs)

            # Draw current price line (yellow)
            if cur > 0:
                y = price_to_y(cur)
                if 10 < y < H-10:
                    draw.line([(0,y),(W,y)], fill=(250,204,21,180), width=1)
                    draw.rectangle([5, y-13, 90, y+3], fill=(0,0,0,180))
                    draw.text((8, y-12), f"CUR: {cur:.2f}", fill=(250,204,21), font=font_xs)

        # Draw pattern annotations (top-left overlay)
        overlay_y = 10
        for p in pats[:3]:
            col = (34,197,94) if p.get("type","")=="BULLISH" else (239,68,68) if p.get("type","")=="BEARISH" else (250,204,21)
            lbl = f"▲ {p['name']}" if p.get("type","")=="BULLISH" else f"▼ {p['name']}" if p.get("type","")=="BEARISH" else f"→ {p['name']}"
            tw  = len(lbl) * 8
            draw.rectangle([5, overlay_y, tw+15, overlay_y+18], fill=(0,0,0,180))
            draw.text((8, overlay_y+2), lbl, fill=col, font=font_xs)
            overlay_y += 22

        # Trend badge top-right
        trend = analysis.get("trend","")
        tc = (34,197,94) if trend=="BULLISH" else (239,68,68) if trend=="BEARISH" else (250,204,21)
        badge = f"⬆ {trend}" if trend=="BULLISH" else f"⬇ {trend}" if trend=="BEARISH" else f"→ {trend}"
        draw.rectangle([W-120, 8, W-5, 30], fill=(0,0,0,200))
        draw.text((W-116, 11), badge, fill=tc, font=font_sm)

        # Confidence badge
        conf = analysis.get("confidence_score", 0)
        draw.rectangle([W-120, 35, W-5, 55], fill=(0,0,0,180))
        draw.text((W-116, 38), f"AI Conf: {conf}%", fill=(255,255,255), font=font_xs)

        # FinSage watermark
        draw.rectangle([3, H-22, 110, H-2], fill=(0,0,0,160))
        draw.text((6, H-20), "FinSage AI Analysis", fill=(100,200,255), font=font_xs)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception as e:
        return img_bytes


def _white_paper_html_chart(analysis: dict, ticker_name: str) -> str:
    """Generate white-paper HTML report from vision analysis."""
    trend = analysis.get("trend","—")
    bias  = analysis.get("trading_bias","—")
    conf  = analysis.get("confidence_score",0)
    tc    = "#1b5e20" if trend=="BULLISH" else "#b71c1c" if trend=="BEARISH" else "#e65100"
    bc    = "#1b5e20" if bias=="LONG"    else "#b71c1c" if bias=="SHORT"    else "#555"
    now   = datetime.now().strftime("%B %d, %Y · %H:%M IST")

    # Support rows
    sup_rows = ""
    for i, s in enumerate(analysis.get("support_levels",[])[:5]):
        p = s.get("price",0); st_str = s.get("strength","")
        sc = "#1b5e20" if "STRONG" in st_str.upper() else "#388e3c" if "MOD" in st_str.upper() else "#666"
        sup_rows += f"<tr><td><b>S{i+1}</b></td><td style='font-family:monospace;font-weight:700;'>{p:.4f if 0<p<10 else f'{p:.2f}' if p>0 else '—'}</td><td style='color:{sc};font-weight:700;'>{st_str}</td><td>{s.get('note','')[:60]}</td></tr>"

    res_rows = ""
    for i, r in enumerate(analysis.get("resistance_levels",[])[:5]):
        p = r.get("price",0); st_str = r.get("strength","")
        sc = "#b71c1c" if "STRONG" in st_str.upper() else "#d32f2f" if "MOD" in st_str.upper() else "#666"
        res_rows += f"<tr><td><b>R{i+1}</b></td><td style='font-family:monospace;font-weight:700;'>{p:.4f if 0<p<10 else f'{p:.2f}' if p>0 else '—'}</td><td style='color:{sc};font-weight:700;'>{st_str}</td><td>{r.get('note','')[:60]}</td></tr>"

    pat_rows = ""
    for p in analysis.get("patterns_detected",[])[:5]:
        pt = p.get("type","NEUTRAL")
        pc = "#1b5e20" if "BULL" in pt.upper() else "#b71c1c" if "BEAR" in pt.upper() else "#555"
        sig = "▲ BULLISH" if "BULL" in pt.upper() else "▼ BEARISH" if "BEAR" in pt.upper() else "→ NEUTRAL"
        pat_rows += f"<tr><td style='font-weight:700;'>{p.get('name','')}</td><td style='color:{pc};font-weight:700;'>{sig}</td><td>{p.get('location','')[:40]}</td><td>{p.get('significance','')[:80]}</td></tr>"

    ind_rows = ""
    for ind in analysis.get("indicators_visible",[])[:8]:
        si = ind.get("signal","NEUTRAL")
        ic = "#1b5e20" if "BULL" in si.upper() else "#b71c1c" if "BEAR" in si.upper() else "#555"
        sig = "▲ BULLISH" if "BULL" in si.upper() else "▼ BEARISH" if "BEAR" in si.upper() else "→ NEUTRAL"
        ind_rows += f"<tr><td style='font-weight:700;'>{ind.get('name','')}</td><td style='font-family:monospace;'>{ind.get('reading','')[:25]}</td><td style='color:{ic};font-weight:700;'>{sig}</td><td>{ind.get('explanation','')[:80]}</td></tr>"

    obs_rows = "".join([f"<div style='padding:5px 0 5px 18px;border-bottom:1px solid #eee;font-size:14px;position:relative;'><span style='position:absolute;left:2px;color:#1a237e;font-weight:900;'>→</span>{o}</div>" for o in analysis.get("key_observations",[])])
    targets_rows = ""
    for t in analysis.get("targets",[]):
        tp = t.get("price",0)
        targets_rows += f"<tr><td style='font-weight:700;color:#1b5e20;'>{t.get('label','')}</td><td style='font-family:monospace;font-weight:700;'>{tp:.4f if 0<tp<10 else f'{tp:.2f}' if tp>0 else '—'}</td><td>{t.get('rr_ratio','')}</td></tr>"
    
    vol = analysis.get("volume_analysis",{})
    liq = analysis.get("liquidity",{})
    of  = analysis.get("order_flow",{})
    ez  = analysis.get("entry_zone",{})
    sl  = analysis.get("stop_loss",{})
    ep_f = lambda p: f"{p:.4f}" if 0<p<10 else f"{p:.2f}" if p>0 else "—"
    ez_p = f"{ep_f(ez.get('price_from',0))} – {ep_f(ez.get('price_to',0))}" if ez.get("price_from",0) else "—"

    fib_rows = ""
    for fi in analysis.get("fibonacci_levels",[])[:6]:
        fp = fi.get("price",0)
        fib_rows += f"<tr><td style='font-weight:700;font-family:monospace;'>Fib {fi.get('level','')}</td><td style='font-family:monospace;'>{ep_f(fp)}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap');
body{{margin:0;padding:0;background:#fff;}}
.wp{{background:#ffffff;color:#1a1a1a;font-family:Georgia,'Times New Roman',serif;
  padding:44px 48px;line-height:1.8;max-width:960px;margin:0 auto;}}
.wp *{{color:#1a1a1a!important;}}
.stripe{{height:6px;background:linear-gradient(90deg,#1a237e,#0d47a1,#006064,#1b5e20,#e65100,#b71c1c);
  margin-bottom:28px;border-radius:3px;}}
h1{{font-size:28px;font-weight:900;margin-bottom:6px;letter-spacing:.01em;line-height:1.3;}}
h2{{font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.12em;
  border-bottom:2.5px solid #1a1a1a;padding-bottom:6px;margin:24px 0 14px;font-family:Arial,sans-serif;}}
p,.txt{{font-size:14.5px;line-height:1.85;margin-bottom:10px;text-align:justify;}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:10px 0;}}
table th{{background:#1a1a1a!important;color:#ffffff!important;padding:9px 11px;text-align:left;
  font-family:Arial,sans-serif;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;}}
table td{{padding:8px 11px;border-bottom:1px solid #e0e0e0;vertical-align:top;}}
table tr:nth-child(even) td{{background:#f9f9f9!important;}}
.badge{{display:inline-block;border:2.5px solid #1a1a1a;border-radius:4px;
  padding:5px 18px;font-size:15px;font-weight:900;margin-right:12px;font-family:Arial,sans-serif;}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0;}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0;}}
.cell{{border:1px solid #cccccc;border-radius:4px;padding:12px;text-align:center;}}
.cl{{font-size:11px;text-transform:uppercase;letter-spacing:.07em;font-family:Arial,sans-serif;margin-bottom:5px;}}
.cv{{font-size:20px;font-weight:900;font-family:'Courier New',monospace;}}
.disc{{font-size:11px;border-top:1px solid #ccc;margin-top:24px;padding-top:12px;
  font-family:Arial,sans-serif;line-height:1.6;text-align:center;}}
</style>
</head><body><div class="wp">
<div class="stripe"></div>

<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:22px;">
  <div>
    <div style="font-size:11px;font-family:Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">FinSage AI — Chart Vision Analysis</div>
    <h1>Chart Analysis Report<br><span style="font-size:18px;font-weight:700;">{ticker_name}</span></h1>
    <div style="margin-top:10px;">
      <span class="badge">{trend}</span>
      <span class="badge" style="font-size:13px;">{bias}</span>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:13px;">Timeframe: <b>{analysis.get('timeframe','—')}</b></div>
    <div style="font-size:13px;">Chart Type: <b>{analysis.get('chart_type','—')}</b></div>
    <div style="font-size:13px;">AI Confidence: <b>{conf}%</b></div>
    <div style="font-size:13px;">Risk: <b>{analysis.get('risk_assessment','—')[:20]}</b></div>
    <div style="font-size:12px;margin-top:6px;">{now}</div>
  </div>
</div>

<h2>Executive Summary</h2>
<p class="txt">{analysis.get('executive_summary','')}</p>

<h2>Key Metrics</h2>
<div class="grid4">
  <div class="cell"><div class="cl">Current Price</div><div class="cv">{ep_f(analysis.get('current_price',0))}</div></div>
  <div class="cell"><div class="cl">Trend</div><div class="cv" style="color:{tc}!important;font-size:14px;">{trend}</div></div>
  <div class="cell"><div class="cl">Strength</div><div class="cv" style="font-size:14px;">{analysis.get('trend_strength','—')}</div></div>
  <div class="cell"><div class="cl">Trade Bias</div><div class="cv" style="color:{bc}!important;font-size:14px;">{bias}</div></div>
</div>

<h2>Support & Resistance Levels</h2>
<div class="grid3" style="margin-bottom:14px;">
  <div>
    <div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;color:#1b5e20!important;">▲ Support Levels</div>
    <table><thead><tr><th>#</th><th>Price</th><th>Strength</th><th>Note</th></tr></thead>
    <tbody>{sup_rows or '<tr><td colspan=4 style=color:#888!important;>Not detected</td></tr>'}</tbody></table>
  </div>
  <div>
    <div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;color:#b71c1c!important;">▼ Resistance Levels</div>
    <table><thead><tr><th>#</th><th>Price</th><th>Strength</th><th>Note</th></tr></thead>
    <tbody>{res_rows or '<tr><td colspan=4 style=color:#888!important;>Not detected</td></tr>'}</tbody></table>
  </div>
  <div>
    <div style="font-weight:800;font-family:Arial;font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">📐 Trade Setup</div>
    <table><tbody>
      <tr><td style="font-weight:700;">Entry Zone</td><td style="font-family:monospace;">{ez_p}</td></tr>
      <tr><td style="font-weight:700;">Stop Loss</td><td style="font-family:monospace;color:#b71c1c!important;">{ep_f(sl.get('price',0))}</td></tr>
      {targets_rows}
      <tr><td style="font-weight:700;">Entry Reason</td><td>{ez.get('reason','')[:60]}</td></tr>
      <tr><td style="font-weight:700;">Stop Reason</td><td>{sl.get('reason','')[:60]}</td></tr>
    </tbody></table>
  </div>
</div>

<h2>Chart & Candlestick Patterns</h2>
<table><thead><tr><th>Pattern</th><th>Signal</th><th>Location</th><th>Significance</th></tr></thead>
<tbody>{pat_rows or '<tr><td colspan=4 style=color:#888!important;>No significant patterns detected</td></tr>'}</tbody></table>

<h2>Technical Indicators</h2>
<p class="txt" style="font-size:13.5px;">{analysis.get('indicator_summary','')}</p>
<table><thead><tr><th>Indicator</th><th>Reading</th><th>Signal</th><th>Explanation</th></tr></thead>
<tbody>{ind_rows or '<tr><td colspan=4 style=color:#888!important;>No indicators visible</td></tr>'}</tbody></table>

<h2>Volume & Order Flow Analysis</h2>
<p class="txt">{analysis.get('volume_narrative','')}</p>
<div class="grid3">
  <div class="cell">
    <div class="cl">Volume Trend</div>
    <div class="cv" style="font-size:14px;">{vol.get('trend','—')}</div>
    <div style="font-size:12px;margin-top:5px;">{vol.get('observation','')[:60]}</div>
  </div>
  <div class="cell">
    <div class="cl">Buying Pressure</div>
    <div class="cv" style="font-size:14px;color:#1b5e20!important;">{of.get('buying_pressure','—')}</div>
    <div style="font-size:12px;margin-top:5px;">vs Selling: {of.get('selling_pressure','—')}</div>
  </div>
  <div class="cell">
    <div class="cl">Liquidity</div>
    <div style="font-size:12px;margin-top:5px;text-align:left;">
      <b>Buy-side:</b> {liq.get('buy_side_liq','—')[:50]}<br>
      <b>Sell-side:</b> {liq.get('sell_side_liq','—')[:50]}
    </div>
  </div>
</div>
{"<div style='margin-top:8px;font-size:13px;'><b>Imbalance Zones:</b> " + " · ".join(of.get("imbalance_zones",[])[:3]) + "</div>" if of.get("imbalance_zones") else ""}

<h2>Fibonacci Levels</h2>
<div style="display:flex;gap:20px;flex-wrap:wrap;">
<table style="width:auto;min-width:220px;">{fib_rows or '<tr><td colspan=2 style=color:#888!important;>Not calculated (no swing points detected)</td></tr>'}</table>
</div>

<h2>Key Observations</h2>
{obs_rows or '<p>—</p>'}

<div class="disc">
  ⚠️ DISCLAIMER: This is an AI-generated analysis of a chart image. It is for educational purposes only and does not constitute financial advice. Past patterns do not guarantee future results. Always do your own research. FinSage AI · {now}
</div>
</div></body></html>"""
    return html


def render_chart_analyzer():
    """Main render function for Chart Analyzer page."""
    st.markdown("""<div style="background:linear-gradient(135deg,#0d1219,#111820);
    border:1px solid rgba(41,98,255,0.2);border-radius:12px;padding:14px 20px;margin-bottom:16px;">
      <div style="font-size:18px;font-weight:800;color:#e2e8f2;">📸 AI Chart Analyzer</div>
      <div style="font-size:12px;color:#6a7585;margin-top:3px;">Upload any trading chart screenshot → AI detects S/R, patterns, indicators, volume → Annotated photo + White Paper</div>
    </div>""", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload Chart Screenshot (PNG, JPG, JPEG)",
        type=["png","jpg","jpeg","webp"],
        key="chart_img_upload",
        help="Upload a screenshot of any trading chart — TradingView, MT4, Zerodha, etc."
    )

    col1, col2 = st.columns([2,1])
    with col1:
        ticker_hint = st.text_input("Ticker/Symbol (optional hint for AI)", placeholder="e.g. NIFTY, AAPL, BTC-USD", key="chart_ticker_hint")
    with col2:
        analyze_btn = st.button("🤖 Analyze Chart", type="primary", use_container_width=True, key="chart_analyze_btn")

    if uploaded:
        img_bytes = uploaded.read()
        st.image(img_bytes, caption="Uploaded Chart", use_container_width=True)

        if analyze_btn or st.session_state.get("chart_analysis_done") == uploaded.name:
            if st.session_state.get("chart_analysis_done") != uploaded.name:
                st.session_state.chart_analysis_done  = uploaded.name
                st.session_state.chart_analysis_result = None

            if st.session_state.get("chart_analysis_result") is None:
                with st.spinner("🤖 AI analyzing your chart — detecting levels, patterns, indicators, volume..."):
                    img_b64    = _img_to_b64(img_bytes)
                    prompt     = VISION_PROMPT
                    if ticker_hint:
                        prompt += f"\n\nHint: The ticker is likely {ticker_hint}."

                    raw, api_used = _call_vision_api(img_b64, prompt)

                    if raw:
                        # Parse JSON
                        try:
                            clean = raw.strip()
                            if "```" in clean:
                                clean = clean.split("```")[1]
                                if clean.startswith("json"): clean = clean[4:]
                            analysis = json.loads(clean)
                        except:
                            # Try to extract JSON from response
                            try:
                                start = raw.find("{"); end = raw.rfind("}") + 1
                                analysis = json.loads(raw[start:end])
                            except:
                                analysis = {"executive_summary": raw, "trend":"—","trading_bias":"—",
                                            "confidence_score":50, "key_observations":[raw[:200]]}
                        analysis["_api"] = api_used or "AI"
                        st.session_state.chart_analysis_result = analysis

                        # Draw annotations
                        annotated_bytes = _draw_annotations_on_image(img_bytes, analysis)
                        st.session_state.chart_annotated_img = annotated_bytes
                    else:
                        st.error("❌ Vision API unavailable. Set OPENAI_API_KEY or GROQ_API_KEY in secrets.")
                        return

            analysis = st.session_state.get("chart_analysis_result")
            if not analysis:
                return

            # Show annotated image
            st.markdown("---")
            st.markdown(f"### 📊 AI-Annotated Chart Analysis — {analysis.get('ticker','Chart')} | {analysis.get('timeframe','—')} | via {analysis.get('_api','AI')}")

            ann_bytes = st.session_state.get("chart_annotated_img", img_bytes)
            st.image(ann_bytes, caption="AI-Annotated: S/R Levels, Trend, Patterns detected", use_container_width=True)

            # Quick stats
            col_a, col_b, col_c, col_d = st.columns(4)
            trend = analysis.get("trend","—")
            tc    = "inverse" if trend=="BEARISH" else "normal"
            with col_a: st.metric("Trend", trend)
            with col_b: st.metric("Trade Bias", analysis.get("trading_bias","—"))
            with col_c: st.metric("AI Confidence", f"{analysis.get('confidence_score',0)}%")
            with col_d: st.metric("Risk", analysis.get("risk_assessment","—")[:12])

            # White paper report
            st.markdown("---")
            ticker_name = ticker_hint or analysis.get("ticker","Chart")
            wp_html = _white_paper_html_chart(analysis, ticker_name)
            components.html(wp_html, height=3200, scrolling=True)

            # Download annotated image
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "📥 Download Annotated Chart",
                    ann_bytes,
                    f"finsage_chart_{ticker_name.replace(' ','_')}.jpg",
                    "image/jpeg",
                    key="dl_ann_chart"
                )
            with col_dl2:
                if st.button("🔄 Re-analyze", key="reanalyze_btn"):
                    st.session_state.chart_analysis_done   = None
                    st.session_state.chart_analysis_result = None
                    st.rerun()
    else:
        st.info("👆 Upload a trading chart screenshot above to begin AI analysis")
        st.markdown("""
        **What AI will detect:**
        - 📏 Support & Resistance levels with strength ratings
        - 📊 Chart patterns (Head & Shoulders, Double Top/Bottom, Flags, etc.)
        - 🕯️ Candlestick patterns (Engulfing, Hammer, Doji, etc.)
        - 📈 Technical indicators (RSI, MACD, Bollinger Bands, EMA, etc.)
        - 📦 Volume & Order Flow analysis
        - 🌊 Fibonacci levels
        - 🎯 Entry zone, Stop loss, Target levels
        - 💧 Liquidity zones & Imbalance areas
        
        **Output:**
        - 🖼️ Annotated chart with all levels drawn
        - 📄 White Paper report (white background, black text, full details)
        """)
