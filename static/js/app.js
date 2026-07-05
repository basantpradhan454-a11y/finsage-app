/* ═══════════════════════════════════════════════════════════════════
   FinSage AI — Frontend JavaScript
   SPA Router + State + API calls
═══════════════════════════════════════════════════════════════════════ */

const API = '/api';
const LOGO_URL = 'https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg';

// ── State ──
const state = {
  currentPage: 'dashboard',
  currentTicker: 'RELIANCE.NS',
  currentName: 'Reliance',
  watchlist: [],
};

// ── Navigation config ──
const NAV = [
  { section: 'Trading', items: [
    { id:'dashboard', icon:'🏠', label:'Market Dashboard' },
    { id:'user-dashboard', icon:'👤', label:'User Dashboard' },
    { id:'tradingview', icon:'📈', label:'TradingView' },
    { id:'sage', icon:'🧠', label:'SAGE Analyst' },
  ]},
  { section: 'Analysis', items: [
    { id:'quant', icon:'🔢', label:'Quant Engine' },
    { id:'fundamental', icon:'📊', label:'Fundamentals' },
    { id:'technical', icon:'📐', label:'Technical' },
  ]},
  { section: 'More', items: [
    { id:'about', icon:'ℹ️', label:'About FinSage' },
  ]},
];

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  buildSidebar();
  buildTopbar();
  navigate('dashboard');
});

// ── Sidebar ──
function buildSidebar() {
  const sb = document.getElementById('sidebar');
  let html = `
    <div class="sb-logo">
      <img src="${LOGO_URL}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 36 36%22><rect width=%2236%22 height=%2236%22 rx=%228%22 fill=%22%2300d4ff%22/><text x=%2218%22 y=%2225%22 text-anchor=%22middle%22 fill=%22%23050d1f%22 font-weight=%22900%22 font-size=%2218%22>F</text></svg>'"/>
      <div><h1>FinSage AI</h1><small>Global Intelligence</small></div>
    </div>
    <div class="sb-search">
      <input type="text" id="sb-search-input" placeholder="🔍 Search stocks, crypto..." oninput="handleSearch(event)"/>
    </div>
    <div class="sb-nav">
  `;
  NAV.forEach(sec => {
    html += `<div class="nav-section">
      <div class="nav-section-title">${sec.section}</div>`;
    sec.items.forEach(item => {
      html += `<div class="nav-item" id="nav-${item.id}" onclick="navigate('${item.id}')">
        <span class="nav-ic">${item.icon}</span>
        <span>${item.label}</span>
      </div>`;
    });
    html += `</div>`;
  });
  html += `
    </div>
    <div class="sb-footer">FinSage AI v3.0 · FastAPI<br>For educational use only</div>
  `;
  sb.innerHTML = html;
}

// ── Topbar ──
function buildTopbar() {
  const tb = document.getElementById('topbar');
  tb.innerHTML = `
    <div class="tb-title" id="tb-title">Market Dashboard</div>
    <div class="tb-spacer"></div>
    <div class="tb-search">
      <span style="color:var(--text-muted)">🔍</span>
      <input type="text" id="tb-search" placeholder="Search ticker (e.g. RELIANCE, AAPL, BTC)" oninput="handleSearch(event)" onfocus="this.select()"/>
    </div>
    <div class="search-dropdown" id="search-dropdown"></div>
    <button class="btn btn-primary" onclick="refreshPage()">↻ Refresh</button>
  `;
}

// ── Search ──
let searchTimer;
function handleSearch(e) {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  const dd = document.getElementById('search-dropdown');
  if (q.length < 1) { dd.classList.remove('show'); return; }
  searchTimer = setTimeout(async () => {
    try {
      const r = await fetch(`${API}/search?q=${encodeURIComponent(q)}`);
      const data = await r.json();
      if (data.ok && data.data) {
        const items = Array.isArray(data.data) ? data.data : [data.data];
        dd.innerHTML = items.slice(0, 8).map(i => `
          <div class="search-result" onclick="selectTicker('${i.symbol||i.ticker||i}', '${i.name||i.symbol||i}')">
            <span class="sr-name">${i.name||i.symbol||i}</span>
            <span class="sr-ticker">${i.symbol||i.ticker||i}</span>
          </div>
        `).join('');
        dd.classList.add('show');
      }
    } catch (err) {
      // Fallback: direct ticker
      dd.innerHTML = `<div class="search-result" onclick="selectTicker('${q.toUpperCase()}', '${q.toUpperCase()}')">
        <span class="sr-name">${q.toUpperCase()}</span><span class="sr-ticker">Press to load</span>
      </div>`;
      dd.classList.add('show');
    }
  }, 350);
}

function selectTicker(ticker, name) {
  state.currentTicker = ticker;
  state.currentName = name;
  document.getElementById('search-dropdown').classList.remove('show');
  document.getElementById('tb-search').value = '';
  navigate(state.currentPage, true);
}

// ── Navigation ──
function navigate(page, forceReload=false) {
  if (state.currentPage === page && !forceReload) return;
  state.currentPage = page;

  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navEl = document.getElementById(`nav-${page}`);
  if (navEl) navEl.classList.add('active');

  // Update title
  const titles = {
    'dashboard':'Market Dashboard', 'user-dashboard':'User Dashboard',
    'tradingview':'TradingView Chart', 'sage':'SAGE Analyst',
    'quant':'Quant Engine', 'fundamental':'Fundamental Analysis',
    'technical':'Technical Analysis', 'about':'About FinSage',
  };
  document.getElementById('tb-title').textContent = titles[page] || page;

  // Render page
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading ${titles[page]||page}...</p></div>`;

  switch(page) {
    case 'dashboard': renderDashboard(); break;
    case 'user-dashboard': renderUserDashboard(); break;
    case 'tradingview': renderTradingView(); break;
    case 'sage': renderSage(); break;
    case 'quant': renderQuant(); break;
    case 'fundamental': renderFundamental(); break;
    case 'technical': renderTechnical(); break;
    case 'about': renderAbout(); break;
    default: content.innerHTML = '<p>Page not found</p>';
  }
}

function refreshPage() { navigate(state.currentPage, true); }

// ── Ticker pills ──
async function renderTickerPills() {
  const r = await fetch(`${API}/watchlist/popular`);
  const data = await r.json();
  if (!data.ok) return '';
  const pills = data.items.map(item => {
    const active = item.ticker === state.currentTicker ? 'active' : '';
    return `<div class="ticker-pill ${active}" onclick="selectTicker('${item.ticker}','${item.name}')">
      ${item.name} <span class="pill-price">${item.cat==='crypto'?'₿':item.cat==='index'?'📈':''}</span>
    </div>`;
  }).join('');
  return `<div class="ticker-pills">${pills}</div>`;
}

// ── Loading helper ──
function loading(msg='Loading...') {
  return `<div class="loading"><div class="spinner"></div><p>${msg}</p></div>`;
}

// ── Error helper ──
function errorBox(msg) {
  return `<div class="glass" style="border-color:var(--red);color:var(--red);"><p>⚠️ ${msg}</p></div>`;
}

// ═══ PAGE: Market Dashboard ═══
async function renderDashboard() {
  const content = document.getElementById('content');
  const pills = await renderTickerPills();

  content.innerHTML = pills + loading(`Loading ${state.currentName} (${state.currentTicker})...`);

  try {
    const r = await fetch(`${API}/dashboard/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = pills + errorBox(data.error); return; }

    const t = data.tech;
    const ai = data.ai;
    const f = data.fundamental;

    let html = pills;

    // ── AI Summary box ──
    const ratingColor = ai.rating === 'BUY' ? 'var(--green)' : ai.rating === 'SELL' ? 'var(--red)' : 'var(--amber)';
    html += `
    <div class="ai-box">
      <div class="ai-header">
        <span class="ai-rating" style="color:${ratingColor}">${ai.rating||'HOLD'}</span>
        <span class="badge badge-blue">${ai.confidence||60}% Confidence</span>
        <span class="badge ${ai.bias==='BULLISH'?'badge-green':ai.bias==='BEARISH'?'badge-red':'badge-amber'}">${ai.bias||'NEUTRAL'}</span>
        <span style="flex:1"></span>
        <span style="color:var(--text-muted);font-size:11px;">Source: ${ai._api||'AI'}</span>
      </div>
      <div class="ai-summary">${ai.summary||''}</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:12px 0;">
        <div class="stat-card"><div class="stat-label">Entry</div><div class="stat-value" style="color:var(--green);font-size:16px;">${ai.entry||'—'}</div></div>
        <div class="stat-card"><div class="stat-label">Stop Loss</div><div class="stat-value" style="color:var(--red);font-size:16px;">${ai.stop||'—'}</div></div>
        <div class="stat-card"><div class="stat-label">Target 1</div><div class="stat-value" style="color:var(--accent);font-size:16px;">${ai.t1||'—'}</div></div>
        <div class="stat-card"><div class="stat-label">Target 2</div><div class="stat-value" style="color:var(--purple);font-size:16px;">${ai.t2||'—'}</div></div>
        <div class="stat-card"><div class="stat-label">R:R</div><div class="stat-value" style="font-size:16px;">${ai.rr||'—'}</div></div>
      </div>
      ${ai.thesis ? `<ul class="ai-thesis">${ai.thesis.map(p=>`<li>${p}</li>`).join('')}</ul>` : ''}
      ${ai.risks ? `<div style="margin-top:10px;font-size:12px;color:var(--text-muted);">⚠️ Risks: ${ai.risks.join(' · ')}</div>` : ''}
    </div>`;

    // ── Stat grid ──
    html += `
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-label">Price</div><div class="stat-value">${t.price||'—'}</div><div class="stat-sub">RSI: ${t.rsi||'—'}</div></div>
      <div class="stat-card"><div class="stat-label">Trend</div><div class="stat-value" style="color:${t.trend==='Bullish'?'var(--green)':t.trend==='Bearish'?'var(--red)':'var(--amber)'};font-size:16px;">${t.trend||'—'}</div><div class="stat-sub">MACD: ${t.macd_h>0?'▲ Bull':'▼ Bear'}</div></div>
      <div class="stat-card"><div class="stat-label">Volume</div><div class="stat-value" style="font-size:16px;">${t.vol_ratio||1}x</div><div class="stat-sub">ATR: ${t.atr||'—'}</div></div>
      <div class="stat-card"><div class="stat-label">1M Perf</div><div class="stat-value" style="color:${t.perf1m>=0?'var(--green)':'var(--red)'};font-size:16px;">${t.perf1m>=0?'+':''}${t.perf1m||0}%</div><div class="stat-sub">3M: ${t.perf3m>=0?'+':''}${t.perf3m||0}%</div></div>
    </div>`;

    // ── Chart ──
    html += `
    <div class="glass" style="padding:0;overflow:hidden;">
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;">
        <span style="font-weight:800;font-size:14px;">📊 ${state.currentName} — Live Chart</span>
        <span style="color:var(--text-muted);font-size:11px;">300 candles · S/R · Patterns · AI Levels</span>
        <span style="flex:1"></span>
        <button class="btn" onclick="toggleFullscreen('chart-frame-main')">⛶ Fullscreen</button>
      </div>
      <div id="chart-frame-main" style="width:100%;"></div>
    </div>`;

    // Inject chart HTML
    html += `<script>(function(){
      var el = document.getElementById('chart-frame-main');
      if (el) el.innerHTML = ${JSON.stringify(data.chart_html)};
    })();<\/script>`;

    // ── White Paper ──
    if (data.whitepaper_html) {
      html += `
      <div class="glass" style="padding:0;overflow:hidden;">
        <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;">
          <span style="font-weight:800;font-size:14px;">📄 AI White Paper Report</span>
          <span style="flex:1"></span>
          <button class="btn" onclick="downloadReport()">⬇ Download</button>
        </div>
        <div id="whitepaper-content" style="padding:16px;"></div>
      </div>`;
      html += `<script>(function(){
        var el = document.getElementById('whitepaper-content');
        if (el) el.innerHTML = ${JSON.stringify(data.whitepaper_html)};
      })();<\/script>`;
    }

    content.innerHTML = html;

    // Execute embedded scripts
    executeScripts(content);
  } catch (err) {
    content.innerHTML = pills + errorBox(err.message);
  }
}

// ═══ PAGE: User Dashboard (6-chart grid) ═══
async function renderUserDashboard() {
  const content = document.getElementById('content');
  const pills = await renderTickerPills();

  content.innerHTML = pills + loading(`Building 6-chart grid for ${state.currentName}...`);

  try {
    const r = await fetch(`${API}/user-dashboard/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = pills + errorBox(data.error); return; }

    let html = pills;

    // AI summary
    const ai = data.ai;
    const ratingColor = ai.rating === 'BUY' ? 'var(--green)' : ai.rating === 'SELL' ? 'var(--red)' : 'var(--amber)';
    html += `
    <div class="ai-box">
      <div class="ai-header">
        <span class="ai-rating" style="color:${ratingColor};font-size:22px;">${ai.rating||'HOLD'}</span>
        <span class="badge badge-blue">${ai.confidence||60}%</span>
        <span style="color:var(--text-secondary);font-size:13px;">${ai.summary||''}</span>
      </div>
    </div>`;

    // 6-chart grid
    html += `
    <div class="glass" style="padding:0;overflow:hidden;margin-bottom:16px;">
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);">
        <span style="font-weight:800;font-size:14px;">🎯 6 Trader Perspectives — ${state.currentName}</span>
        <span style="color:var(--text-muted);font-size:11px;margin-left:8px;">Price Action · SMC · Quant · Indicators · Order Flow · Wave</span>
      </div>
      <div id="six-chart-container" style="width:100%;"></div>
    </div>`;

    // Order flow
    html += `
    <div class="glass" style="padding:0;overflow:hidden;">
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);">
        <span style="font-weight:800;font-size:14px;">📦 Order Flow & Volume Profile</span>
        <span style="color:var(--text-muted);font-size:11px;margin-left:8px;">POC: ${data.vp_poc||'—'} · VAH: ${data.vp_vah||'—'} · VAL: ${data.vp_val||'—'}</span>
      </div>
      <div id="order-flow-container" style="width:100%;"></div>
    </div>`;

    content.innerHTML = html;

    // Inject chart HTML via iframe approach
    const sixEl = document.getElementById('six-chart-container');
    if (sixEl) {
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'width:100%;height:900px;border:none;';
      iframe.srcdoc = data.six_chart_html;
      sixEl.appendChild(iframe);
    }

    const ofEl = document.getElementById('order-flow-container');
    if (ofEl) {
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'width:100%;height:500px;border:none;';
      iframe.srcdoc = data.order_flow_html;
      ofEl.appendChild(iframe);
    }

  } catch (err) {
    content.innerHTML = pills + errorBox(err.message);
  }
}

// ═══ PAGE: TradingView ═══
async function renderTradingView() {
  const content = document.getElementById('content');
  const pills = await renderTickerPills();

  content.innerHTML = pills + loading('Loading TradingView widget...');

  try {
    const r = await fetch(`${API}/tradingview/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = pills + errorBox(data.error); return; }

    let html = pills;
    html += `
    <div class="glass" style="padding:0;overflow:hidden;">
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;">
        <span style="font-weight:800;font-size:14px;">📈 TradingView — ${state.currentName}</span>
        <span style="color:var(--text-muted);font-size:11px;">Real-time · RSI · MACD · BB · Volume</span>
        <span style="flex:1"></span>
        <button class="btn" onclick="toggleFullscreen('tv-frame')">⛶ Fullscreen</button>
      </div>
      <div id="tv-frame" style="width:100%;height:80vh;"></div>
    </div>`;

    content.innerHTML = html;

    const el = document.getElementById('tv-frame');
    if (el) {
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'width:100%;height:100%;border:none;';
      iframe.srcdoc = data.html;
      el.appendChild(iframe);
    }
  } catch (err) {
    content.innerHTML = pills + errorBox(err.message);
  }
}

// ═══ PAGE: SAGE Analyst ═══
async function renderSage() {
  const content = document.getElementById('content');
  content.innerHTML = loading('Loading SAGE Analyst...');

  try {
    const r = await fetch(`${API}/dashboard/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = errorBox(data.error); return; }

    const t = data.tech;
    const ai = data.ai;
    const f = data.fundamental;

    let html = `
    <div class="ai-box">
      <div class="ai-header">
        <span style="font-family:Orbitron;font-size:20px;font-weight:900;color:var(--accent);">🧠 SAGE ANALYST</span>
        <span style="color:var(--text-muted);font-size:12px;">${state.currentName} (${state.currentTicker})</span>
      </div>
      <div class="ai-summary">${ai.summary||''}</div>
    </div>`;

    // Indicators detail
    if (ai.indicators) {
      html += `<div class="glass"><h3 style="margin-bottom:12px;font-size:15px;">📊 Indicator Breakdown</h3>`;
      for (const [key, val] of Object.entries(ai.indicators)) {
        html += `<div style="padding:8px 0;border-bottom:1px solid var(--border);">
          <span style="font-weight:700;color:var(--accent);font-size:12px;">${key.replace(/_/g,' ')}</span>
          <span style="color:var(--text-secondary);font-size:13px;margin-left:8px;">${val}</span>
        </div>`;
      }
      html += `</div>`;
    }

    // Multi-timeframe
    if (ai.multi_tf) {
      html += `<div class="glass"><h3 style="margin-bottom:12px;font-size:15px;">⏰ Multi-Timeframe Analysis</h3>`;
      for (const [tf, view] of Object.entries(ai.multi_tf)) {
        html += `<div style="padding:8px 0;border-bottom:1px solid var(--border);">
          <span class="badge badge-blue" style="text-transform:uppercase;">${tf}</span>
          <span style="color:var(--text-secondary);font-size:13px;margin-left:8px;">${view}</span>
        </div>`;
      }
      html += `</div>`;
    }

    // Fundamental
    if (f.health_score) {
      html += `<div class="glass">
        <h3 style="margin-bottom:12px;font-size:15px;">💰 Fundamental Health</h3>
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">
          <div style="font-size:36px;font-weight:900;color:${f.health_score>=75?'var(--green)':f.health_score>=50?'var(--amber)':'var(--red)'};">${f.health_score}</div>
          <div><div style="font-weight:700;">${f.health_verdict}</div><div style="color:var(--text-muted);font-size:12px;">Health Score (0-100)</div></div>
        </div>`;
      if (f.health_breakdown) {
        html += `<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;">`;
        for (const [k,v] of Object.entries(f.health_breakdown)) {
          html += `<div class="stat-card"><div class="stat-label">${k}</div><div class="stat-value" style="font-size:16px;">${v}/100</div></div>`;
        }
        html += `</div>`;
      }
      html += `</div>`;
    }

    // Chart
    html += `<div class="glass" style="padding:0;overflow:hidden;">
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);">
        <span style="font-weight:800;font-size:14px;">📊 Chart with AI Levels</span>
      </div>
      <div id="sage-chart" style="width:100%;"></div>
    </div>`;

    content.innerHTML = html;

    // Inject chart
    const el = document.getElementById('sage-chart');
    if (el) el.innerHTML = data.chart_html;
    executeScripts(content);

  } catch (err) {
    content.innerHTML = errorBox(err.message);
  }
}

// ═══ PAGE: Quant Engine ═══
async function renderQuant() {
  const content = document.getElementById('content');
  content.innerHTML = loading('Running Quant Engine (ML trend probability)...');

  try {
    const r = await fetch(`${API}/quant/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = errorBox(data.error); return; }

    let html = `<div class="glass">
      <h3 style="margin-bottom:16px;font-size:16px;">🔢 Quantitative Analysis — ${state.currentName}</h3>`;

    if (data.volatility) {
      const v = data.volatility;
      html += `<h4 style="margin:12px 0 8px;color:var(--accent);">Volatility</h4>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-label">Daily Vol</div><div class="stat-value" style="font-size:18px;">${v.daily_volatility_pct}%</div></div>
        <div class="stat-card"><div class="stat-label">Annualized</div><div class="stat-value" style="font-size:18px;">${v.annualized_volatility_pct}%</div></div>
        <div class="stat-card"><div class="stat-label">20D Recent</div><div class="stat-value" style="font-size:18px;">${v.recent_20d_volatility_pct}%</div></div>
      </div>`;
    }

    if (data.beta !== null && data.beta !== undefined) {
      html += `<div class="stat-card" style="margin:12px 0;"><div class="stat-label">Beta (vs S&P 500)</div><div class="stat-value" style="font-size:20px;color:${data.beta>1?'var(--amber)':'var(--green)'};">${data.beta}</div>
      <div class="stat-sub">${data.beta>1?'More volatile than market':'Less volatile than market'}</div></div>`;
    }

    if (data.trend) {
      const t = data.trend;
      if (t.ok) {
        html += `<h4 style="margin:16px 0 8px;color:var(--accent);">ML Trend Probability (Logistic Regression)</h4>
        <div class="stat-grid">
          <div class="stat-card"><div class="stat-label">P(Up 5D)</div><div class="stat-value" style="font-size:20px;color:var(--green);">${t.prob_up_5d}%</div></div>
          <div class="stat-card"><div class="stat-label">P(Down 5D)</div><div class="stat-value" style="font-size:20px;color:var(--red);">${t.prob_down_5d}%</div></div>
          <div class="stat-card"><div class="stat-label">Train Accuracy</div><div class="stat-value" style="font-size:18px;">${t.train_accuracy_pct}%</div></div>
          <div class="stat-card"><div class="stat-label">Rows Used</div><div class="stat-value" style="font-size:18px;">${t.rows_used}</div></div>
        </div>
        <p style="color:var(--text-muted);font-size:11px;margin-top:8px;">⚠️ Statistical tendency based on historical patterns, NOT financial advice. Stock prediction is an unsolved problem.</p>`;
      } else {
        html += `<p style="color:var(--text-muted);">${t.error||'Trend analysis unavailable'}</p>`;
      }
    }

    html += `</div>`;
    content.innerHTML = html;
  } catch (err) {
    content.innerHTML = errorBox(err.message);
  }
}

// ═══ PAGE: Fundamental ═══
async function renderFundamental() {
  const content = document.getElementById('content');
  content.innerHTML = loading('Fetching fundamentals...');

  try {
    const r = await fetch(`${API}/fundamental/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = errorBox(data.error); return; }

    const d = data.data;
    const s = data.score;

    let html = `<div class="glass">
      <h3 style="margin-bottom:16px;font-size:16px;">💰 ${d.name} — Fundamental Analysis</h3>
      <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;">
        <div style="font-size:42px;font-weight:900;color:${s.health_score>=75?'var(--green)':s.health_score>=50?'var(--amber)':'var(--red)'};">${s.health_score}</div>
        <div><div style="font-size:18px;font-weight:700;">${s.verdict}</div><div style="color:var(--text-muted);">Health Score (0-100)</div></div>
      </div>`;

    // Breakdown
    html += `<div class="stat-grid">`;
    for (const [k,v] of Object.entries(s.breakdown)) {
      html += `<div class="stat-card"><div class="stat-label">${k}</div><div class="stat-value" style="font-size:16px;">${v}/100</div></div>`;
    }
    html += `</div>`;

    // Key metrics
    html += `<h4 style="margin:16px 0 8px;color:var(--accent);">Key Metrics</h4>
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-label">P/E Ratio</div><div class="stat-value" style="font-size:16px;">${d.pe_ratio||'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">Forward P/E</div><div class="stat-value" style="font-size:16px;">${d.forward_pe||'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">P/B Ratio</div><div class="stat-value" style="font-size:16px;">${d.pb_ratio||'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">ROE</div><div class="stat-value" style="font-size:16px;">${d.roe?(d.roe*100).toFixed(1)+'%':'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">Profit Margin</div><div class="stat-value" style="font-size:16px;">${d.profit_margin?(d.profit_margin*100).toFixed(1)+'%':'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">Dividend Yield</div><div class="stat-value" style="font-size:16px;">${d.dividend_yield?(d.dividend_yield*100).toFixed(2)+'%':'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">52W High</div><div class="stat-value" style="font-size:16px;">${d['52w_high']||'N/A'}</div></div>
      <div class="stat-card"><div class="stat-label">52W Low</div><div class="stat-value" style="font-size:16px;">${d['52w_low']||'N/A'}</div></div>
    </div>`;

    html += `</div>`;
    content.innerHTML = html;
  } catch (err) {
    content.innerHTML = errorBox(err.message);
  }
}

// ═══ PAGE: Technical ═══
async function renderTechnical() {
  const content = document.getElementById('content');
  content.innerHTML = loading('Running technical analysis...');

  try {
    const r = await fetch(`${API}/technical/${state.currentTicker}`);
    const data = await r.json();
    if (!data.ok) { content.innerHTML = errorBox(data.error); return; }

    let html = `<div class="glass">
      <h3 style="margin-bottom:16px;font-size:16px;">📐 Technical Analysis — ${state.currentTicker}</h3>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-label">RSI</div><div class="stat-value" style="font-size:20px;color:${data.rsi>70?'var(--red)':data.rsi<30?'var(--green)':'var(--text-primary)'};">${data.rsi}</div><div class="stat-sub">${data.rsi_signal}</div></div>
        <div class="stat-card"><div class="stat-label">MACD Hist</div><div class="stat-value" style="font-size:20px;color:${data.macd_hist>0?'var(--green)':'var(--red)'};">${data.macd_hist>0?'▲':'▼'} ${data.macd_hist}</div><div class="stat-sub">${data.macd_signal}</div></div>
      </div>`;

    // Support/Resistance
    html += `<h4 style="margin:16px 0 8px;color:var(--accent);">Support / Resistance</h4>
    <div style="display:flex;gap:16px;margin-bottom:12px;">
      <div><span style="color:var(--green);font-weight:700;">Support:</span> ${data.support.map(s=>s.toFixed(2)).join(', ')}</div>
      <div><span style="color:var(--red);font-weight:700;">Resistance:</span> ${data.resistance.map(r=>r.toFixed(2)).join(', ')}</div>
    </div>`;

    // Patterns
    if (data.candlestick_patterns && data.candlestick_patterns.length > 0) {
      html += `<h4 style="margin:12px 0 8px;color:var(--accent);">Candlestick Patterns Detected</h4>`;
      data.candlestick_patterns.forEach(p => {
        const color = p[1] === 'Bullish' ? 'badge-green' : p[1] === 'Bearish' ? 'badge-red' : 'badge-amber';
        html += `<span class="badge ${color}" style="margin-right:6px;">${p[0]} (${p[1]})</span>`;
      });
    }

    if (data.chart_pattern) {
      html += `<div style="margin-top:12px;"><span class="badge badge-amber">📈 ${data.chart_pattern}</span></div>`;
    }

    html += `</div>`;
    content.innerHTML = html;
  } catch (err) {
    content.innerHTML = errorBox(err.message);
  }
}

// ═══ PAGE: About ═══
function renderAbout() {
  const content = document.getElementById('content');
  content.innerHTML = `
    <div class="glass" style="text-align:center;padding:40px;">
      <img src="${LOGO_URL}" style="width:64px;height:64px;border-radius:16px;margin-bottom:16px;" onerror="this.style.display='none'"/>
      <h2 style="font-family:Orbitron;color:var(--accent);margin-bottom:8px;">FinSage AI</h2>
      <p style="color:var(--text-secondary);margin-bottom:20px;">Global Financial Intelligence Platform</p>
      <p style="color:var(--text-muted);font-size:13px;max-width:500px;margin:0 auto 20px;">
        FinSage AI provides institutional-grade stock and crypto analysis using free APIs (yfinance, CoinGecko).
        Features include: 6-perspective chart analysis, SAGE AI analyst, quantitative ML models,
        fundamental health scoring, candlestick pattern detection, and TradingView integration.
      </p>
      <div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;">
        <span class="badge badge-blue">FastAPI Backend</span>
        <span class="badge badge-green">Vanilla JS Frontend</span>
        <span class="badge badge-amber">100% Free APIs</span>
      </div>
      <p style="color:var(--text-muted);font-size:11px;margin-top:20px;">⚠️ For educational purposes only. Not financial advice.</p>
    </div>
  `;
}

// ═══ Utilities ═══
function executeScripts(container) {
  // Re-execute scripts injected via innerHTML
  const scripts = container.querySelectorAll('script');
  scripts.forEach(oldScript => {
    const newScript = document.createElement('script');
    if (oldScript.src) { newScript.src = oldScript.src; } else { newScript.textContent = oldScript.textContent; }
    oldScript.parentNode.replaceChild(newScript, oldScript);
  });
}

function toggleFullscreen(id) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!document.fullscreenElement) {
    el.requestFullscreen?.() || el.webkitRequestFullscreen?.();
  } else {
    document.exitFullscreen?.() || document.webkitExitFullscreen?.();
  }
}

function downloadReport() {
  const el = document.getElementById('whitepaper-content');
  if (!el) return;
  const html = el.innerHTML;
  const blob = new Blob([`<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:Inter,sans-serif;background:#050d1f;color:#e2e8f2;padding:20px;}</style></head><body>${html}</body></html>`], {type:'text/html'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `FinSage_Report_${state.currentTicker}_${Date.now()}.html`;
  a.click();
}

// Close search dropdown on outside click
document.addEventListener('click', (e) => {
  const dd = document.getElementById('search-dropdown');
  const search = e.target.closest('.tb-search, .sb-search');
  if (dd && !search) dd.classList.remove('show');
});
