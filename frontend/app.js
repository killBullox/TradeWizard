/* ====== TradeWizard Frontend ====== */
'use strict';

const WS_URL = `ws://${location.host}/ws`;
const API    = '';

// ── State ──────────────────────────────────────────────────────────
let ws = null;
let reconnectTimer = null;
let state = {
  trades: [],
  journal: [],
  meetings: [],
  performance: {},
  config: {},
  agents: {},
};

// ── Agent Metadata ──────────────────────────────────────────────────
const AGENTS = {
  ICTEA: { name: 'ICT Advisor',    emoji: '🎯', color: '#4F46E5' },
  RM:    { name: 'Risk Manager',   emoji: '⚖️', color: '#DC2626' },
  TR:    { name: 'Trader',         emoji: '💹', color: '#059669' },
  AT:    { name: 'Trade Analyst',  emoji: '🔬', color: '#7C3AED' },
  CC:    { name: 'Connector',      emoji: '🔌', color: '#0891B2' },
  JR:    { name: 'Journalist',     emoji: '📝', color: '#92400E' },
};

const FOREX_PAIRS = ['EURUSD','GBPUSD','USDJPY','XAUUSD','USDCHF','AUDUSD','GBPJPY'];

// ── WebSocket ───────────────────────────────────────────────────────
function connectWS() {
  setWsStatus('connecting');
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setWsStatus('connected');
    if (reconnectTimer) { clearInterval(reconnectTimer); reconnectTimer = null; }
    addActivity('Connected to TradeWizard server', 'success');
  };

  ws.onmessage = (e) => {
    try { handleMessage(JSON.parse(e.data)); }
    catch (err) { console.error('WS parse error', err); }
  };

  ws.onerror = () => setWsStatus('disconnected');
  ws.onclose = () => {
    setWsStatus('disconnected');
    if (!reconnectTimer) {
      reconnectTimer = setInterval(() => {
        if (ws?.readyState !== WebSocket.OPEN) connectWS();
      }, 3000);
    }
  };
}

function sendWS(obj) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

// ── Message Handler ─────────────────────────────────────────────────
function handleMessage(msg) {
  const { type } = msg;

  if (type === 'init') {
    applyStatus(msg.status);
    return;
  }

  if (type === 'agent_thinking' || type === 'agent_response') {
    updateAgentCard(msg.agent, msg.message, type === 'agent_thinking' ? 'thinking' : 'done');
    addComm(msg.agent, msg.message, type === 'agent_thinking');
    return;
  }

  if (type === 'agent_status') {
    updateAgentCard(msg.agent, msg.message, 'active');
    addComm(msg.agent, `[${msg.action}] ${msg.message}`);
    return;
  }

  switch (type) {
    case 'system_started':
      addActivity('⚡ TradeWizard system started', 'success');
      break;

    case 'analysis_cycle_started':
      addActivity(`🔍 Analysis cycle: ${msg.pairs?.join(', ')}`, 'info');
      break;

    case 'trade_opened':
      addActivity(
        `📈 Trade opened: ${msg.symbol} ${msg.direction} @ ${msg.entry_price ?? msg.entry} | SL: ${msg.sl} | TP1: ${msg.tp1}`,
        'trade'
      );
      refreshTrades();
      break;

    case 'trade_closed':
      const pnlClass = msg.pnl_usd > 0 ? 'success' : 'error';
      addActivity(
        `${msg.result === 'WIN' ? '🏆' : '💔'} Trade closed: ${msg.symbol} ${msg.result} | $${(msg.pnl_usd??0).toFixed(2)} | ${(msg.pnl_pips??0).toFixed(1)} pips`,
        pnlClass
      );
      refreshTrades();
      refreshPerformance();
      break;

    case 'trade_rejected':
      addActivity(`❌ ${msg.symbol} rejected by ${msg.agent}: ${msg.reason}`, 'warning');
      break;

    case 'sl_trailed':
      addActivity(`📍 SL trailed on trade #${msg.trade_id} ${msg.symbol} → ${msg.new_sl}`, 'info');
      refreshTrades();
      break;

    case 'partial_close':
      addActivity(`💰 Partial close ${msg.percent}% on trade #${msg.trade_id}`, 'info');
      break;

    case 'meeting_started':
      addActivity(`🗣️ ${msg.meeting_type} meeting started | Participants: ${msg.participants?.join(', ')}`, 'info');
      break;

    case 'meeting_completed':
    case 'meeting_summary':
      addActivity(`✅ Meeting completed: ${msg.improvements?.length || 0} improvements proposed`, 'success');
      refreshMeetings();
      break;

    case 'config_updated':
      addActivity(`⚙️ Config updated: ${msg.key} = ${msg.value} (${msg.reason})`, 'info');
      refreshConfig();
      break;

    case 'error':
      addActivity(`🚨 Error: ${msg.message}`, 'error');
      break;

    case 'skip':
      addActivity(`⏭ ${msg.symbol}: skipped (${msg.reason})`, 'info');
      break;

    case 'paper_update':
      handlePaperUpdate(msg);
      break;

    case 'paper_auto_close':
      addActivity(
        `📄 Paper auto-close #${msg.trade_id} ${msg.symbol} [${msg.reason}] — ${msg.pnl_usd >= 0 ? '+' : ''}$${(msg.pnl_usd||0).toFixed(2)}`,
        msg.pnl_usd >= 0 ? 'success' : 'warning'
      );
      refreshPaper();
      break;

    case 'news_block':
      addActivity(`📰 NEWS BLOCK: ${msg.symbol} — ${msg.message}`, 'warning');
      showNewsBanner(msg.event);
      break;

    case 'pong':
      break;
  }
}

// ── UI Helpers ───────────────────────────────────────────────────────
function setWsStatus(status) {
  const dot   = document.querySelector('.dot');
  const label = document.getElementById('ws-label');
  if (!dot) return;
  dot.className = `dot ${status}`;
  label.textContent = status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting…' : 'Disconnected';
}

function updateAgentCard(agentKey, message, state) {
  const card  = document.getElementById(`agent-${agentKey}`);
  const badge = card?.querySelector('.agent-badge');
  const msg   = document.getElementById(`msg-${agentKey}`);
  if (!card) return;
  card.className = `agent-card ${state}`;
  if (badge) { badge.className = `agent-badge ${state}`; badge.textContent = state.toUpperCase(); }
  if (msg)   { msg.textContent = message?.substring(0, 120) + (message?.length > 120 ? '…' : ''); }
  // Auto-reset to idle after 10s
  setTimeout(() => {
    if (card) card.className = 'agent-card';
    if (badge) { badge.className = 'agent-badge idle'; badge.textContent = 'IDLE'; }
  }, 10000);
}

function addActivity(text, type = 'info') {
  const feed = document.getElementById('activity-feed');
  if (!feed) return;
  const now  = new Date().toLocaleTimeString();
  const item = document.createElement('div');
  item.className = `activity-item ${type}`;
  item.innerHTML = `<span class="activity-time">${now}</span>${escHtml(text)}`;
  feed.appendChild(item);
  feed.scrollTop = feed.scrollHeight;
  // Keep last 100 items
  while (feed.children.length > 100) feed.removeChild(feed.firstChild);
}

function addComm(agent, message, isThinking = false) {
  const feed = document.getElementById('comms-feed');
  if (!feed) return;
  const now  = new Date().toLocaleTimeString('it-IT', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  const item = document.createElement('div');
  item.className = 'comm-item';
  item.style.borderLeftColor = AGENTS[agent]?.color || '#666';
  const fullText = (isThinking ? '💭 ' : '') + (message || '');
  const needsTruncation = fullText.length > 120;
  item.innerHTML = `
    <span class="comm-agent ${agent}">${AGENTS[agent]?.emoji || ''} ${agent}</span>
    <span class="comm-msg${needsTruncation ? ' truncated' : ''}">${escHtml(fullText)}</span>
    ${needsTruncation ? '<span class="comm-expand">▼ espandi</span>' : ''}
    <span class="comm-time">${now}</span>
  `;
  if (needsTruncation) {
    item.addEventListener('click', () => {
      const msg = item.querySelector('.comm-msg');
      const btn = item.querySelector('.comm-expand');
      const expanded = !msg.classList.contains('truncated');
      msg.classList.toggle('truncated', expanded);
      if (btn) btn.textContent = expanded ? '▼ espandi' : '▲ riduci';
    });
  }
  feed.appendChild(item);
  feed.scrollTop = feed.scrollHeight;
  while (feed.children.length > 200) feed.removeChild(feed.firstChild);
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Data Refresh ─────────────────────────────────────────────────────
async function refreshAll() {
  await Promise.all([
    refreshTrades(), refreshJournal(), refreshMeetings(),
    refreshPerformance(), refreshConfig(), refreshNews(),
  ]);
}

async function refreshTrades() {
  try {
    const [trades, livePnl] = await Promise.all([
      fetchJSON('/api/trades?limit=100'),
      fetchJSON('/api/trades/live_pnl').catch(() => []),
    ]);
    state.trades = trades;
    renderTradesTable(trades);
    const livePnlMap = Object.fromEntries((livePnl||[]).map(p => [p.trade_id, p]));
    renderOpenTrades(trades.filter(t => t.status === 'ACTIVE'), livePnlMap);
    // PNL Calendar — trades tab (real trades use status=CLOSED, not result=WIN/LOSS)
    const calTrades = trades.filter(t => t.status === 'CLOSED' || t.result === 'WIN' || t.result === 'LOSS');
    if (calTrades.length) _tradesCal.setTrades(calTrades);
    // Update stats
    const closed = trades.filter(t => t.status === 'CLOSED');
    const wins   = closed.filter(t => t.result === 'WIN').length;
    setEl('stat-open',    trades.filter(t=>t.status==='ACTIVE').length);
    setEl('stat-total',   closed.length);
    setEl('stat-winrate', closed.length ? (wins/closed.length*100).toFixed(1)+'%' : '0%');
    const totalPnl = closed.reduce((s,t) => s + (t.pnl_usd||0), 0);
    const pnlEl = document.getElementById('stat-pnl');
    if (pnlEl) {
      pnlEl.textContent = `$${totalPnl.toFixed(2)}`;
      pnlEl.className = `stat-value ${totalPnl >= 0 ? 'text-win' : 'text-loss'}`;
    }
  } catch (e) { console.error('refreshTrades', e); }
}

async function refreshJournal() {
  try {
    const entries = await fetchJSON('/api/journal?limit=30');
    state.journal = entries;
    renderJournal(entries);
  } catch (e) { console.error('refreshJournal', e); }
}

async function refreshMeetings() {
  try {
    const meetings = await fetchJSON('/api/meetings?limit=10');
    state.meetings = meetings;
    renderMeetings(meetings);
  } catch (e) { console.error('refreshMeetings', e); }
}

async function refreshPerformance() {
  try {
    const perf = await fetchJSON('/api/performance');
    state.performance = perf;
    renderPerformance(perf);
  } catch (e) { console.error('refreshPerformance', e); }
}

async function refreshConfig() {
  try {
    const cfg = await fetchJSON('/api/config');
    state.config = cfg;
    renderConfig(cfg);
  } catch (e) { console.error('refreshConfig', e); }
}

// ── Renderers ────────────────────────────────────────────────────────
function renderTradesTable(trades) {
  const tbody = document.getElementById('trades-tbody');
  if (!tbody) return;
  const filter = document.getElementById('trades-filter')?.value || '';
  const filtered = filter ? trades.filter(t => t.status === filter) : trades;
  tbody.innerHTML = filtered.map(t => `
    <tr>
      <td>#${t.id}</td>
      <td><strong>${t.symbol}</strong></td>
      <td class="${t.direction==='BUY'?'text-win':'text-loss'}">${t.direction}</td>
      <td><span class="badge">${t.ict_setup||'-'}</span></td>
      <td style="font-size:0.78rem;color:var(--text-secondary)">${fmtDate(t.open_time)}</td>
      <td>${t.entry_price ?? '-'}</td>
      <td style="font-size:0.78rem;color:var(--text-secondary)">${t.close_time ? fmtDate(t.close_time) : '-'}</td>
      <td>${t.close_price ?? '-'}</td>
      <td>${t.stop_loss ?? '-'}</td>
      <td>${t.take_profit_1 ?? '-'}</td>
      <td>${t.lot_size ?? '-'}</td>
      <td><span class="badge ${t.status==='ACTIVE'?'badge-active':t.result==='WIN'?'badge-win':t.result==='LOSS'?'badge-loss':''}">${t.status}</span></td>
      <td class="${(t.pnl_usd||0)>0?'text-win':(t.pnl_usd||0)<0?'text-loss':''}">${t.pnl_usd!=null ? '$'+t.pnl_usd.toFixed(2) : '-'}</td>
      <td>
        ${t.status==='ACTIVE' ? `<button class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">Close</button>` : ''}
        <button class="btn btn-ghost btn-sm" onclick="viewTrade(${t.id})">View</button>
      </td>
    </tr>
  `).join('');
}

function renderOpenTrades(trades, livePnlMap = {}) {
  const el = document.getElementById('open-trades-list');
  const cntEl = document.getElementById('open-trades-count');
  if (!el) return;
  if (cntEl) cntEl.textContent = trades.length;
  if (!trades.length) { el.innerHTML = '<div class="empty-state">No open trades</div>'; return; }
  el.innerHTML = trades.map(t => {
    const live = livePnlMap[t.id] || {};
    const cp   = live.current_price;
    const pnl  = live.pnl_usd;
    const pips = live.pnl_pips;
    const pnlClass = pnl == null ? '' : pnl >= 0 ? 'text-win' : 'text-loss';
    const pnlStr = pnl != null ? `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pips >= 0 ? '+' : ''}${pips?.toFixed(1)} pip)` : '—';
    return `
    <div class="open-trade-card">
      <div class="trade-header-row">
        <span class="trade-symbol">${t.symbol}</span>
        <span class="trade-dir ${t.direction}">${t.direction}</span>
        <span class="trade-setup">${t.ict_setup||'ICT'}</span>
        <button class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">✕</button>
      </div>
      <div style="font-size:0.7rem;color:var(--text-muted);margin:2px 0 6px">
        Aperto: ${fmtDate(t.open_time)}
      </div>
      <div class="trade-levels">
        <div><div class="trade-level-label">Entry</div><div class="trade-level-val">${t.entry_price}</div></div>
        <div><div class="trade-level-label">Now</div><div class="trade-level-val">${cp ?? '—'}</div></div>
        <div><div class="trade-level-label">SL</div><div class="trade-level-val text-loss">${t.stop_loss}</div></div>
        <div><div class="trade-level-label">TP1</div><div class="trade-level-val text-win">${t.take_profit_1 ?? '—'}</div></div>
      </div>
      <div style="font-size:0.82rem;font-weight:700;margin-top:6px;text-align:right" class="${pnlClass}">
        P&L: ${pnlStr}
      </div>
    </div>`;
  }).join('');
}

function renderJournal(entries) {
  const el = document.getElementById('journal-entries');
  if (!el) return;
  if (!entries.length) { el.innerHTML = '<div class="empty-state">No journal entries yet</div>'; return; }
  el.innerHTML = entries.map(e => {
    let content = e.content;
    try { const j = JSON.parse(content); content = j.content || JSON.stringify(j, null, 2); } catch {}
    return `
      <div class="journal-entry">
        <div class="journal-entry-header">
          <span class="journal-type">${e.entry_type}</span>
          ${e.trade_id ? `<span class="badge">Trade #${e.trade_id}</span>` : ''}
          <span class="journal-time">${fmtDate(e.created_at)}</span>
        </div>
        <div class="journal-content">${escHtml(content)}</div>
      </div>
    `;
  }).join('');
}

function renderMeetings(meetings) {
  const el = document.getElementById('meetings-list');
  if (!el) return;
  if (!meetings.length) { el.innerHTML = '<div class="empty-state">No meetings yet</div>'; return; }
  el.innerHTML = meetings.map(m => {
    let conclusions = [];
    let improvements = [];
    try { conclusions  = JSON.parse(m.conclusions || '[]');  } catch {}
    try { improvements = JSON.parse(m.improvements || '[]'); } catch {}
    return `
      <div class="meeting-card">
        <div class="meeting-header">
          <div>
            <div class="meeting-type">${m.meeting_type}</div>
            <div class="meeting-participants">👥 ${m.participants}</div>
          </div>
          <span class="badge">${fmtDate(m.created_at)}</span>
        </div>
        ${conclusions.length ? `
          <div style="margin-bottom:8px">
            <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px">📌 Conclusions</div>
            <ul class="meeting-conclusions">${conclusions.map(c => `<li>${escHtml(String(c))}</li>`).join('')}</ul>
          </div>
        ` : ''}
        ${improvements.length ? `
          <div>
            <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px">⚡ Improvements</div>
            ${improvements.map(i => `<div class="improvement-item">${escHtml(i.improvement||JSON.stringify(i))}</div>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function renderPerformance(perf) {
  const statsEl = document.getElementById('perf-stats');
  if (statsEl) {
    statsEl.innerHTML = `
      <div class="stat-card"><div class="stat-value">${perf.total_trades||0}</div><div class="stat-label">Total Trades</div></div>
      <div class="stat-card win"><div class="stat-value">${perf.win_rate||0}%</div><div class="stat-label">Win Rate</div></div>
      <div class="stat-card"><div class="stat-value">${perf.wins||0}</div><div class="stat-label">Wins</div></div>
      <div class="stat-card"><div class="stat-value">${perf.losses||0}</div><div class="stat-label">Losses</div></div>
    `;
  }
  const tbody = document.getElementById('perf-tbody');
  if (tbody && perf.by_setup) {
    tbody.innerHTML = Object.entries(perf.by_setup).map(([setup, d]) => `
      <tr>
        <td><strong>${setup}</strong></td>
        <td>${d.total}</td>
        <td class="text-win">${d.wins}</td>
        <td class="text-loss">${d.losses}</td>
        <td><span class="${d.win_rate>=55?'text-win':d.win_rate>=45?'':' text-loss'}">${d.win_rate}%</span></td>
        <td class="${(d.total_pips||0)>=0?'text-win':'text-loss'}">${(d.total_pips||0).toFixed(1)}</td>
      </tr>
    `).join('');
  }
  // PNL Calendar — feed from all closed trades in state
  const closed = (state.trades || []).filter(t => t.result === 'WIN' || t.result === 'LOSS');
  if (closed.length) _perfCal.setTrades(closed);
}

function renderConfig(cfg) {
  const form = document.getElementById('config-form');
  if (!form) return;

  const editable = ['risk_percent','rr_ratio','max_open_trades','account_balance','analysis_interval'];
  const paperOn      = cfg['paper_mode'] === 'true' || cfg['paper_mode'] === true;
  const weekendOn    = cfg['trade_on_weekend'] === 'true';
  const mt5BridgeUrl = cfg['mt5_bridge_url'] || '';
  const oandaKey     = cfg['oanda_api_key'] || '';
  const oandaPractice = (cfg['oanda_practice'] || 'true') !== 'false';

  const ALL_PAIRS = ['EURUSD','GBPUSD','USDJPY','USDCHF','AUDUSD','USDCAD','NZDUSD','XAUUSD','US30','NAS100','US500'];
  let enabledPairs = [];
  try { enabledPairs = JSON.parse(cfg['enabled_pairs'] || '[]'); } catch(e) {}

  let killZones = [{"start":"07:00","end":"11:00"},{"start":"13:00","end":"18:00"}];
  try { if (cfg['kill_zones']) killZones = JSON.parse(cfg['kill_zones']); } catch(e) {}

  form.innerHTML = editable.map(key => `
    <div class="config-field">
      <label>${key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</label>
      <input type="text" id="cfg-${key}" value="${escHtml(cfg[key]||'')}" />
    </div>
  `).join('') + `
    <div class="config-field" style="grid-column:1/-1">
      <label>Paper Mode</label>
      <label class="toggle-switch">
        <input type="checkbox" id="cfg-paper_mode" ${paperOn ? 'checked' : ''}>
        <span class="toggle-slider"></span>
      </label>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>Trading nel Weekend</label>
      <label class="toggle-switch">
        <input type="checkbox" id="cfg-trade_on_weekend" ${weekendOn ? 'checked' : ''}>
        <span class="toggle-slider"></span>
      </label>
      <span style="font-size:0.75rem;color:var(--text-muted);margin-left:10px">OFF = sistema in pausa sab/dom (consigliato)</span>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>Kill Zones <span style="font-size:0.75rem;color:var(--text-muted);font-weight:400">(ora di Roma)</span></label>
      <div id="cfg-kill-zones">
        ${killZones.map((w,i) => `
          <div class="kz-row" data-idx="${i}">
            <input type="time" class="kz-start" value="${w.start}" />
            <span class="kz-sep">→</span>
            <input type="time" class="kz-end" value="${w.end}" />
            <button class="btn btn-ghost btn-xs kz-remove" onclick="removeKillZone(${i})">✕</button>
          </div>`).join('')}
      </div>
      <button class="btn btn-secondary btn-sm" style="margin-top:8px" onclick="addKillZone()">+ Aggiungi fascia</button>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>MT5 Bridge URL <span style="font-size:0.75rem;color:var(--text-muted);font-weight:400">(bridge Python su Windows con MT5 aperto — priorità su tutto)</span></label>
      <input type="text" id="cfg-mt5_bridge_url" value="${escHtml(mt5BridgeUrl)}"
             placeholder="es. http://192.168.1.10:5001 oppure http://localhost:5001"
             style="width:100%;max-width:480px" />
      <span style="font-size:0.75rem;color:var(--text-muted);margin-left:8px">Lascia vuoto se non usi MT5</span>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>OANDA API Key <span style="font-size:0.75rem;color:var(--text-muted);font-weight:400">(usato solo se MT5 bridge non disponibile)</span></label>
      <input type="password" id="cfg-oanda_api_key" value="${escHtml(oandaKey)}"
             placeholder="Bearer token OANDA practice/live"
             style="font-family:monospace;width:100%;max-width:480px" />
      <label class="toggle-switch" style="margin-top:8px">
        <input type="checkbox" id="cfg-oanda_practice" ${oandaPractice ? 'checked' : ''}>
        <span class="toggle-slider"></span>
      </label>
      <span style="font-size:0.75rem;color:var(--text-muted);margin-left:10px">Account Practice (deseleziona per Live)</span>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>Enabled Pairs</label>
      <div class="setup-checks" id="cfg-pairs-grid">
        ${ALL_PAIRS.map(p => `
          <label class="check-pill">
            <input type="checkbox" class="cfg-pair-chk" value="${p}" ${enabledPairs.includes(p)?'checked':''}>
            ${p}
          </label>`).join('')}
      </div>
    </div>
    <div class="config-field" style="grid-column:1/-1">
      <label>AI Model Mode <span style="font-size:0.75rem;color:var(--text-muted);font-weight:400">(impatta consumo token e qualità analisi ICT)</span></label>
      <div style="display:flex;gap:12px;margin-top:4px">
        ${['economy','quality'].map(m => `
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="radio" name="cfg-model_mode" value="${m}" ${(cfg['model_mode']||'economy')===m?'checked':''}>
            <span>${m === 'economy'
              ? '<strong>Economy</strong> — Haiku (veloce, ~20x più economico, consigliato)'
              : '<strong>Quality</strong> — Sonnet (analisi più profonda, costo maggiore)'}</span>
          </label>`).join('')}
      </div>
    </div>
  `;
}

window.addKillZone = function() {
  const container = document.getElementById('cfg-kill-zones');
  if (!container) return;
  const idx = container.querySelectorAll('.kz-row').length;
  const row = document.createElement('div');
  row.className = 'kz-row';
  row.dataset.idx = idx;
  row.innerHTML = `
    <input type="time" class="kz-start" value="09:00" />
    <span class="kz-sep">→</span>
    <input type="time" class="kz-end" value="12:00" />
    <button class="btn btn-ghost btn-xs kz-remove" onclick="removeKillZone(${idx})">✕</button>`;
  container.appendChild(row);
};

window.removeKillZone = function(idx) {
  const container = document.getElementById('cfg-kill-zones');
  if (!container) return;
  const rows = container.querySelectorAll('.kz-row');
  if (rows.length <= 1) return; // keep at least one
  rows[idx]?.remove();
  // re-index remaining rows
  container.querySelectorAll('.kz-row').forEach((r, i) => {
    r.dataset.idx = i;
    const btn = r.querySelector('.kz-remove');
    if (btn) btn.setAttribute('onclick', `removeKillZone(${i})`);
  });
};

function renderPairsGrid() {
  const grid = document.getElementById('pairs-grid');
  if (!grid) return;
  grid.innerHTML = FOREX_PAIRS.map(p => `
    <div class="pair-btn" onclick="analyzePair('${p}')">
      <div class="pair-name">${p}</div>
      <div class="pair-analyze">🔍 Analyze</div>
    </div>
  `).join('');
}

function applyStatus(status) {
  if (!status) return;
  const cfg = status.config || {};
  state.config = cfg;
  renderConfig(cfg);
  renderPairsGrid();
  document.getElementById('stat-open')?.setAttribute('data-val', status.open_trades || 0);
  setEl('stat-open', status.open_trades || 0);
}

// ── Actions ──────────────────────────────────────────────────────────
function analyzePair(symbol) {
  sendWS({ command: 'analyze', symbol });
  addActivity(`🔍 Analysis triggered for ${symbol}`, 'info');
}

async function closeTrade(id) {
  if (!confirm(`Close trade #${id}?`)) return;
  try {
    await fetchJSON(`/api/trades/${id}/close`, { method: 'POST' });
    addActivity(`Trade #${id} close requested`, 'warning');
    setTimeout(refreshTrades, 1000);
  } catch (e) { alert('Failed: ' + e); }
}

async function viewTrade(id) {
  const trade = state.trades.find(t => t.id === id) || await fetchJSON(`/api/trades/${id}`);
  const modal = document.getElementById('trade-modal');
  const body  = document.getElementById('modal-body');
  const title = document.getElementById('modal-title');
  title.textContent = `Trade #${id}: ${trade.symbol} ${trade.direction}`;
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:0.82rem">
      ${[
        ['Setup', trade.ict_setup], ['Status', trade.status], ['Lot Size', trade.lot_size],
        ['Entry', trade.entry_price], ['Stop Loss', trade.stop_loss], ['TP1', trade.take_profit_1],
        ['TP2', trade.take_profit_2||'-'], ['TP3', trade.take_profit_3||'-'],
        ['Risk %', trade.risk_percent+'%'], ['RR Ratio', trade.rr_ratio],
        ['P&L Pips', trade.pnl_pips??'-'], ['P&L USD', trade.pnl_usd!=null?'$'+trade.pnl_usd:'-'],
        ['Opened', fmtDate(trade.open_time)], ['Closed', fmtDate(trade.close_time)],
        ['MT5 Ticket', trade.mt5_ticket||'N/A'], ['SL Updates', trade.trailing_sl_updates||0],
      ].map(([l,v]) => `<div><div style="color:var(--text-muted);font-size:0.7rem">${l}</div><div>${escHtml(String(v??'-'))}</div></div>`).join('')}
    </div>
    ${trade.status === 'ACTIVE' ? `
      <div style="margin-top:16px">
        <button class="btn btn-danger" onclick="closeTrade(${id});closeModal()">Close Trade</button>
      </div>
    ` : ''}
  `;
  modal.style.display = 'flex';
}

function closeModal() { document.getElementById('trade-modal').style.display = 'none'; }

async function triggerMeeting(type) {
  try {
    await fetchJSON('/api/meetings/trigger', { method: 'POST', body: JSON.stringify({ type }) });
    addActivity(`🗣️ ${type} meeting triggered`, 'info');
  } catch (e) { alert('Failed: ' + e); }
}

window.triggerMeeting = triggerMeeting;

async function saveConfig() {
  const editable = ['risk_percent','rr_ratio','max_open_trades','account_balance','analysis_interval'];
  for (const key of editable) {
    const el = document.getElementById(`cfg-${key}`);
    if (!el) continue;
    await fetchJSON(`/api/config/${key}`, { method: 'PUT', body: JSON.stringify({ value: el.value }) });
  }
  // Paper mode toggle
  const paperEl = document.getElementById('cfg-paper_mode');
  if (paperEl) {
    await fetchJSON('/api/config/paper_mode', { method: 'PUT', body: JSON.stringify({ value: paperEl.checked ? 'true' : 'false' }) });
  }
  // Weekend trading toggle
  const weekendEl = document.getElementById('cfg-trade_on_weekend');
  if (weekendEl) {
    await fetchJSON('/api/config/trade_on_weekend', { method: 'PUT', body: JSON.stringify({ value: weekendEl.checked ? 'true' : 'false' }) });
  }
  // Kill zones
  const kzRows = document.querySelectorAll('#cfg-kill-zones .kz-row');
  if (kzRows.length) {
    const zones = [...kzRows].map(row => ({
      start: row.querySelector('.kz-start')?.value || '07:00',
      end:   row.querySelector('.kz-end')?.value   || '11:00',
    })).filter(z => z.start && z.end);
    await fetchJSON('/api/config/kill_zones', { method: 'PUT', body: JSON.stringify({ value: JSON.stringify(zones) }) });
  }
  // MT5 bridge URL
  const mt5El = document.getElementById('cfg-mt5_bridge_url');
  if (mt5El) {
    await fetchJSON('/api/config/mt5_bridge_url', { method: 'PUT', body: JSON.stringify({ value: mt5El.value.trim() }) });
  }
  // OANDA credentials
  const oandaKeyEl  = document.getElementById('cfg-oanda_api_key');
  const oandaPracEl = document.getElementById('cfg-oanda_practice');
  if (oandaKeyEl) {
    await fetchJSON('/api/config/oanda_api_key', { method: 'PUT', body: JSON.stringify({ value: oandaKeyEl.value.trim() }) });
  }
  if (oandaPracEl) {
    await fetchJSON('/api/config/oanda_practice', { method: 'PUT', body: JSON.stringify({ value: oandaPracEl.checked ? 'true' : 'false' }) });
  }
  // Enabled pairs
  const checked = [...document.querySelectorAll('.cfg-pair-chk:checked')].map(el => el.value);
  if (checked.length) {
    await fetchJSON('/api/config/enabled_pairs', { method: 'PUT', body: JSON.stringify({ value: JSON.stringify(checked) }) });
  }
  // AI Model mode
  const modelModeEl = document.querySelector('input[name="cfg-model_mode"]:checked');
  if (modelModeEl) {
    await fetchJSON('/api/config/model_mode', { method: 'PUT', body: JSON.stringify({ value: modelModeEl.value }) });
  }
  addActivity('⚙️ Configuration saved', 'success');
  await refreshConfig();
}

// ── Utility ───────────────────────────────────────────────────────────
async function fetchJSON(url, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const res = await fetch(API + url, { ...opts, headers });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function fmtDate(iso) {
  if (!iso) return '-';
  try {
    // Backend stores UTC datetimes without timezone suffix — append Z so the
    // browser correctly converts to local time instead of treating as local
    const s = (iso.endsWith('Z') || iso.includes('+') || iso.includes('-', 10)) ? iso : iso + 'Z';
    return new Date(s).toLocaleString('it-IT', {dateStyle:'short', timeStyle:'medium'});
  } catch { return iso; }
}

// ── Tab Switching ─────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    const id = `tab-${tab.dataset.tab}`;
    document.getElementById(id)?.classList.add('active');
    // Refresh data for the relevant tab
    if (tab.dataset.tab === 'trades')      refreshTrades();
    if (tab.dataset.tab === 'journal')     refreshJournal();
    if (tab.dataset.tab === 'meetings')    refreshMeetings();
    if (tab.dataset.tab === 'performance') refreshPerformance();
    if (tab.dataset.tab === 'settings')    refreshConfig();
    if (tab.dataset.tab === 'news')        refreshNews();
    if (tab.dataset.tab === 'charts')      window.activateChartsTab?.();
    if (tab.dataset.tab === 'backtest')    { refreshBtHistory(); refreshCacheStatus(); }
    if (tab.dataset.tab === 'paper')       refreshPaper();
    if (tab.dataset.tab === 'analytics')  refreshAnalytics();
  });
});

// ── Event Listeners ───────────────────────────────────────────────────
document.getElementById('btn-analyze-all')?.addEventListener('click', () => {
  sendWS({ command: 'analyze' });
  addActivity('🔍 Full analysis triggered for all pairs', 'info');
});

document.getElementById('btn-meeting')?.addEventListener('click', () => triggerMeeting('POST_TRADE'));

document.getElementById('btn-settings')?.addEventListener('click', async () => {
  const cfg = await fetchJSON('/api/config');
  const modal = document.getElementById('settings-modal');
  const body  = document.getElementById('settings-body');
  state.config = cfg;
  renderConfig(cfg);
  // Copy to settings modal
  body.innerHTML = document.getElementById('config-form')?.innerHTML || '';
  modal.style.display = 'flex';
});

document.getElementById('btn-save-config')?.addEventListener('click', saveConfig);
document.getElementById('btn-clear-feed')?.addEventListener('click', () => {
  const feed = document.getElementById('activity-feed');
  if (feed) feed.innerHTML = '';
});
document.getElementById('trades-filter')?.addEventListener('change', () => renderTradesTable(state.trades));

window.closeSettingsModal = () => { document.getElementById('settings-modal').style.display = 'none'; };

// ── News ─────────────────────────────────────────────────────────────
let newsData = [];

async function refreshNews() {
  try {
    const hours = document.getElementById('news-hours-filter')?.value || 24;
    const data  = await fetchJSON(`/api/news?hours=${hours}`);
    newsData = data.events || [];

    // Sync settings inputs
    const bBefore = document.getElementById('news-block-before');
    const bAfter  = document.getElementById('news-block-after');
    if (bBefore && data.block_minutes_before !== undefined) bBefore.value = data.block_minutes_before;
    if (bAfter  && data.block_minutes_after  !== undefined) bAfter.value  = data.block_minutes_after;

    renderNewsTable(newsData);
    renderNewsPreview(newsData);
  } catch (e) { console.error('refreshNews', e); }
}

function renderNewsTable(events) {
  const tbody = document.getElementById('news-tbody');
  if (!tbody) return;
  if (!events.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No high-impact events in this window</td></tr>';
    return;
  }
  tbody.innerHTML = events.map(e => {
    const t    = new Date(e.time);
    const soon = (t - Date.now()) < 30 * 60 * 1000 && (t - Date.now()) > -30 * 60 * 1000;
    return `
      <tr class="${soon ? 'news-row-soon' : ''}">
        <td>${t.toUTCString().slice(5,22)}</td>
        <td><span class="currency-badge">${e.currency}</span></td>
        <td>${escHtml(e.title)}</td>
        <td><span class="impact-badge impact-${e.impact.toLowerCase()}">${e.impact}</span></td>
        <td>${e.forecast || '—'}</td>
        <td>${e.previous || '—'}</td>
        <td>${e.actual   || '—'}</td>
        <td>${e.is_released
          ? '<span class="badge badge-win">Released</span>'
          : soon
            ? '<span class="badge badge-warn">🔴 Soon</span>'
            : '<span class="badge">Pending</span>'}</td>
      </tr>
    `;
  }).join('');
}

function renderNewsPreview(events) {
  const el = document.getElementById('news-preview-list');
  if (!el) return;
  const now = Date.now();
  const upcoming = events
    .filter(e => !e.is_released && new Date(e.time) > now - 15 * 60 * 1000)
    .slice(0, 5);

  if (!upcoming.length) {
    el.innerHTML = '<div class="empty-state">No high-impact events in the next 24h</div>';
    return;
  }
  el.innerHTML = upcoming.map(e => {
    const t    = new Date(e.time);
    const mins = Math.round((t - now) / 60000);
    const soon = mins >= 0 && mins <= 30;
    return `
      <div class="news-preview-item ${soon ? 'news-soon' : ''}">
        <span class="currency-badge">${e.currency}</span>
        <span class="news-title">${escHtml(e.title)}</span>
        <span class="impact-badge impact-${e.impact.toLowerCase()}">${e.impact}</span>
        <span class="news-time">${mins >= 0 ? `in ${mins}m` : `${-mins}m ago`}</span>
      </div>
    `;
  }).join('');
}

function showNewsBanner(event) {
  const banner = document.getElementById('news-block-banner');
  if (!banner) return;
  banner.style.display = 'block';
  banner.innerHTML = `
    📰 <strong>NEWS BLOCK ACTIVE</strong> —
    ${escHtml(event.title)} [${event.currency}]
    @ ${new Date(event.time).toUTCString().slice(17,22)} UTC
    <button onclick="this.parentElement.style.display='none'" style="float:right;background:none;border:none;color:inherit;cursor:pointer">✕</button>
  `;
  setTimeout(() => { banner.style.display = 'none'; }, 5 * 60 * 1000);
}

async function saveNewsConfig() {
  const before  = document.getElementById('news-block-before')?.value;
  const after   = document.getElementById('news-block-after')?.value;
  const medium  = document.getElementById('news-block-medium')?.value;
  await Promise.all([
    before !== undefined ? fetchJSON('/api/config/news_block_minutes_before', { method: 'PUT', body: JSON.stringify({ value: before }) }) : null,
    after  !== undefined ? fetchJSON('/api/config/news_block_minutes_after',  { method: 'PUT', body: JSON.stringify({ value: after  }) }) : null,
    medium !== undefined ? fetchJSON('/api/config/news_block_medium',          { method: 'PUT', body: JSON.stringify({ value: medium }) }) : null,
  ].filter(Boolean));
  addActivity('📰 News filter settings saved', 'success');
}

document.getElementById('btn-refresh-news')?.addEventListener('click', refreshNews);
document.getElementById('btn-refresh-news-tab')?.addEventListener('click', refreshNews);
document.getElementById('btn-save-news-config')?.addEventListener('click', saveNewsConfig);
document.getElementById('news-hours-filter')?.addEventListener('change', refreshNews);

// ── Analytics ─────────────────────────────────────────────────────────
let anEquityChart = null;
let anDdChart     = null;

async function refreshAnalytics() {
  try {
    const data = await fetchJSON('/api/analytics');
    renderAnalyticsSummary(data.summary);
    renderAnEquity(data.equity_curve);
    renderAnDrawdown(data.drawdown_series);
    renderAnHeatmap(data.by_month);
    renderAnBarChart('an-by-symbol', data.by_symbol,  'name',  'win_rate', 'total_pnl');
    renderAnBarChart('an-by-setup',  data.by_setup,   'name',  'win_rate', 'total_pnl');
    renderAnBarChart('an-by-dow',    data.by_dow,     'day',   'win_rate', 'total_pips');
    renderAnHourChart('an-by-hour',  data.by_hour);
  } catch (e) { console.error('refreshAnalytics', e); }
}

function renderAnalyticsSummary(s) {
  if (!s) return;
  const fmt  = (v, d=2) => v != null ? Number(v).toFixed(d) : '—';
  const pct  = v => v != null ? fmt(v,1) + '%' : '—';
  const pnl  = v => v != null ? (v >= 0 ? '+' : '') + '$' + fmt(v) : '—';

  setEl('an-total',   s.total_trades ?? '—');
  const wrEl = document.getElementById('an-winrate');
  if (wrEl) {
    wrEl.textContent = pct(s.win_rate);
    wrEl.className   = `stat-value ${(s.win_rate||0) >= 55 ? 'text-win' : (s.win_rate||0) >= 45 ? '' : 'text-loss'}`;
  }
  setEl('an-pf',      s.profit_factor === 999 ? '∞' : fmt(s.profit_factor));
  setEl('an-sharpe',  fmt(s.sharpe));
  setEl('an-sortino', fmt(s.sortino));
  const ddEl = document.getElementById('an-maxdd');
  if (ddEl) { ddEl.textContent = fmt(s.max_drawdown_pct, 1) + '%'; ddEl.className = 'stat-value text-loss'; }
  const expEl = document.getElementById('an-exp');
  if (expEl) { expEl.textContent = pnl(s.expectancy); expEl.className = `stat-value ${(s.expectancy||0) >= 0 ? 'text-win' : 'text-loss'}`; }

  const streak = s.current_streak || {};
  const strEl  = document.getElementById('an-streak');
  if (strEl) {
    if (streak.type) {
      strEl.textContent = `${streak.count} ${streak.type}`;
      strEl.className   = `stat-value ${streak.type === 'WIN' ? 'text-win' : 'text-loss'}`;
    } else {
      strEl.textContent = '—';
      strEl.className   = 'stat-value';
    }
  }
}

function renderAnEquity(equityCurve) {
  const container = document.getElementById('an-equity-canvas');
  if (!container || !equityCurve?.length || typeof LightweightCharts === 'undefined') return;
  if (anEquityChart) { anEquityChart.remove(); anEquityChart = null; }

  anEquityChart = LightweightCharts.createChart(container, _chartOpts(container.clientWidth, 220));
  const series = anEquityChart.addAreaSeries({
    lineColor: '#3b82f6', topColor: 'rgba(59,130,246,0.2)',
    bottomColor: 'rgba(59,130,246,0.02)', lineWidth: 2, priceLineVisible: false,
  });
  series.setData(equityCurve.map(e => ({ time: _tsToUnix(e.time), value: e.equity })).filter(d => d.time > 0));
  anEquityChart.timeScale().fitContent();
}

function renderAnDrawdown(ddSeries) {
  const container = document.getElementById('an-dd-canvas');
  if (!container || !ddSeries?.length || typeof LightweightCharts === 'undefined') return;
  if (anDdChart) { anDdChart.remove(); anDdChart = null; }

  anDdChart = LightweightCharts.createChart(container, _chartOpts(container.clientWidth, 220));
  const series = anDdChart.addAreaSeries({
    lineColor: '#ef4444', topColor: 'rgba(239,68,68,0.15)',
    bottomColor: 'rgba(239,68,68,0.02)', lineWidth: 2,
    priceLineVisible: false, invertFilledArea: false,
  });
  series.setData(ddSeries.map(e => ({ time: _tsToUnix(e.time), value: e.drawdown_pct })).filter(d => d.time > 0));
  anDdChart.timeScale().fitContent();
}

function renderAnHeatmap(byMonth) {
  const container = document.getElementById('an-heatmap');
  if (!container) return;
  if (!byMonth?.length) {
    container.innerHTML = '<div class="empty-state">No trade history yet</div>';
    return;
  }

  // Group by year
  const years = {};
  for (const m of byMonth) {
    if (!years[m.year]) years[m.year] = {};
    years[m.year][m.month] = m;
  }

  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const maxAbs  = Math.max(...byMonth.map(m => Math.abs(m.total_pnl)), 1);

  let html = `<div class="heatmap-table">
    <div class="heatmap-row heatmap-header">
      <div class="heatmap-year-label"></div>
      ${MONTHS.map(m => `<div class="heatmap-month-label">${m}</div>`).join('')}
    </div>`;

  for (const year of Object.keys(years).sort()) {
    html += `<div class="heatmap-row">
      <div class="heatmap-year-label">${year}</div>`;
    for (let mo = 1; mo <= 12; mo++) {
      const m = years[year][mo];
      if (!m) {
        html += `<div class="heatmap-cell heatmap-empty"></div>`;
        continue;
      }
      const intensity = Math.min(Math.abs(m.total_pnl) / maxAbs, 1);
      const alpha     = 0.15 + intensity * 0.7;
      const bg        = m.total_pnl >= 0
        ? `rgba(16,185,129,${alpha.toFixed(2)})`
        : `rgba(239,68,68,${alpha.toFixed(2)})`;
      const sign = m.total_pnl >= 0 ? '+' : '';
      html += `<div class="heatmap-cell" style="background:${bg}" title="${m.month_name} ${year}: ${sign}$${m.total_pnl.toFixed(0)} (${m.trades} trades)">
        <span class="heatmap-value">${sign}$${Math.abs(m.total_pnl) >= 1000 ? (m.total_pnl/1000).toFixed(1)+'k' : m.total_pnl.toFixed(0)}</span>
      </div>`;
    }
    html += '</div>';
  }
  html += '</div>';
  container.innerHTML = html;
}

function renderAnBarChart(containerId, data, nameKey, rateKey, valueKey) {
  const container = document.getElementById(containerId);
  if (!container || !data?.length) {
    if (container) container.innerHTML = '<div class="empty-state">No data</div>';
    return;
  }
  const maxVal = Math.max(...data.map(d => Math.abs(d[valueKey] || 0)), 1);
  container.innerHTML = data.slice(0, 8).map(d => {
    const val     = d[valueKey] ?? 0;
    const wr      = d[rateKey]  ?? 0;
    const width   = Math.round(Math.abs(val) / maxVal * 100);
    const isPos   = val >= 0;
    const barCls  = isPos ? 'an-bar-pos' : 'an-bar-neg';
    const sign    = isPos ? '+' : '';
    const valStr  = valueKey === 'win_rate' ? wr.toFixed(1)+'%'
                  : valueKey === 'total_pips' ? val.toFixed(1)+'p'
                  : '$'+val.toFixed(0);
    return `
      <div class="an-bar-row">
        <div class="an-bar-label">${escHtml(String(d[nameKey] || '?'))}</div>
        <div class="an-bar-track">
          <div class="an-bar ${barCls}" style="width:${width}%"></div>
        </div>
        <div class="an-bar-stat">
          <span class="${isPos ? 'text-win' : 'text-loss'}">${sign}${valStr}</span>
          <span class="an-bar-wr">${wr.toFixed(1)}%WR</span>
          <span class="an-bar-cnt">${d.total ?? 0}T</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderAnHourChart(containerId, hours) {
  const container = document.getElementById(containerId);
  if (!container || !hours?.length) return;
  const active  = hours.filter(h => h.total > 0);
  if (!active.length) { container.innerHTML = '<div class="empty-state">No data</div>'; return; }
  const maxPips = Math.max(...active.map(h => Math.abs(h.total_pips)), 1);
  container.innerHTML = hours.map(h => {
    if (!h.total) return `<div class="an-hour-col an-hour-empty" title="${h.label}"></div>`;
    const height = Math.round(Math.abs(h.total_pips) / maxPips * 60);
    const isPos  = h.total_pips >= 0;
    return `
      <div class="an-hour-col" title="${h.label}: ${h.total_pips.toFixed(1)}p (${h.win_rate}%WR, ${h.total}T)">
        <div class="an-hour-bar ${isPos ? 'an-hour-pos' : 'an-hour-neg'}" style="height:${height}px"></div>
        <div class="an-hour-label">${h.hour}</div>
      </div>
    `;
  }).join('');
}

function _chartOpts(w, h) {
  return {
    layout: { background: { color: '#0f1117' }, textColor: '#94a3b8' },
    grid:   { vertLines: { color: '#1e2130' }, horzLines: { color: '#1e2130' } },
    rightPriceScale: { borderColor: '#2d3450' },
    timeScale: { borderColor: '#2d3450', timeVisible: true },
    width: w || 600, height: h || 220,
  };
}

function _tsToUnix(ts) {
  if (!ts) return 0;
  try { return Math.floor(new Date(ts).getTime() / 1000); } catch { return 0; }
}

// ── Paper Trading ─────────────────────────────────────────────────────
let paperEquityChart  = null;
let paperEquityData   = [];

async function refreshPaper() {
  try {
    const status = await fetchJSON('/api/paper/status');
    renderPaperSummary(status);
    const positions = await fetchJSON('/api/paper/positions');
    renderPaperPositions(positions);
    const trades = await fetchJSON('/api/paper/trades?limit=50');
    renderPaperTrades(trades);
    // Sync toggle
    const toggle = document.getElementById('paper-toggle');
    if (toggle) toggle.checked = !!status.paper_mode;
    // Equity curve from summary
    if (status.equity_curve && status.equity_curve.length > 1) {
      paperEquityData = status.equity_curve;
      renderPaperEquity(paperEquityData);
    }
  } catch (e) { console.error('refreshPaper', e); }
}

function renderPaperSummary(s) {
  const fmt = v => v != null ? '$' + Number(v).toFixed(2) : '$—';
  const pct = v => v != null ? (v >= 0 ? '+' : '') + Number(v).toFixed(2) + '%' : '—';
  setEl('paper-balance',    fmt(s.balance));
  setEl('paper-equity',     fmt(s.equity));
  setEl('paper-open-pos',   s.open_positions ?? 0);
  const unrEl = document.getElementById('paper-unrealised');
  if (unrEl) {
    const u = s.unrealised_pnl ?? 0;
    unrEl.textContent  = fmt(u);
    unrEl.className    = `stat-value ${u >= 0 ? 'text-win' : 'text-loss'}`;
  }
  const retEl = document.getElementById('paper-return');
  if (retEl) {
    const r = s.return_pct ?? 0;
    retEl.textContent = pct(r);
    retEl.className   = `stat-value ${r >= 0 ? 'text-win' : 'text-loss'}`;
  }
}

function renderPaperPositions(positions) {
  const el  = document.getElementById('paper-positions-list');
  const cnt = document.getElementById('paper-pos-count');
  if (!el) return;
  if (cnt) cnt.textContent = positions.length;
  if (!positions.length) {
    el.innerHTML = '<div class="empty-state">No open paper positions</div>';
    return;
  }
  el.innerHTML = positions.map(p => {
    const pnl  = p.unrealised_pnl_usd ?? 0;
    const pips = p.unrealised_pnl_pips ?? 0;
    const isB  = p.direction === 'BUY';
    return `
      <div class="open-trade-card ${pnl >= 0 ? 'paper-pos-win' : 'paper-pos-loss'}">
        <div class="trade-header-row">
          <span class="trade-symbol">${p.symbol}</span>
          <span class="trade-dir ${p.direction}">${p.direction}</span>
          <span class="trade-setup">${p.ict_setup || 'PAPER'}</span>
          <span class="paper-live-pnl ${pnl >= 0 ? 'text-win' : 'text-loss'}">
            ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pips >= 0 ? '+' : ''}${pips.toFixed(1)}p)
          </span>
          <button class="btn btn-danger btn-sm" onclick="closePaperTrade(${p.trade_id})">✕</button>
        </div>
        <div class="trade-levels">
          <div><div class="trade-level-label">Entry</div><div class="trade-level-val">${p.entry_price}</div></div>
          <div><div class="trade-level-label">Current</div><div class="trade-level-val ${pnl>=0?'text-win':'text-loss'}">${p.current_price ?? '—'}</div></div>
          <div><div class="trade-level-label">SL</div><div class="trade-level-val text-loss">${p.stop_loss}</div></div>
          <div><div class="trade-level-label">TP</div><div class="trade-level-val text-win">${p.take_profit}</div></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderPaperTrades(trades) {
  const tbody = document.getElementById('paper-trades-tbody');
  if (!tbody) return;
  if (!trades.length) {
    tbody.innerHTML = '<tr><td colspan="14" class="empty-state">No paper trades yet</td></tr>';
    return;
  }
  tbody.innerHTML = trades.map(t => `
    <tr>
      <td>#${t.id}</td>
      <td><b>${t.symbol}</b></td>
      <td class="${t.direction==='BUY'?'text-win':'text-loss'}">${t.direction}</td>
      <td><span class="badge">${t.ict_setup||'—'}</span></td>
      <td style="font-size:0.72rem;white-space:nowrap">${t.open_time ? fmtDate(t.open_time) : '—'}</td>
      <td style="font-size:0.72rem;white-space:nowrap">${t.close_time ? fmtDate(t.close_time) : '—'}</td>
      <td>${t.entry_price??'—'}</td>
      <td>${t.stop_loss??'—'}</td>
      <td>${t.take_profit_1??'—'}</td>
      <td>${t.close_price??'—'}</td>
      <td><span class="badge ${t.result==='WIN'?'badge-win':t.result==='LOSS'?'badge-loss':''}">${t.result||t.status}</span></td>
      <td class="${(t.pnl_pips??0)>=0?'text-win':'text-loss'}">${t.pnl_pips!=null?t.pnl_pips.toFixed(1):'—'}</td>
      <td class="${(t.pnl_usd??0)>=0?'text-win':'text-loss'}">${t.pnl_usd!=null?'$'+t.pnl_usd.toFixed(2):'—'}</td>
      <td>${t.status==='ACTIVE'?`<button class="btn btn-danger btn-sm" onclick="closePaperTrade(${t.id})">Close</button>`:''}</td>
    </tr>
  `).join('');
}

function renderPaperEquity(equityData) {
  const container = document.getElementById('paper-equity-canvas');
  const card      = document.getElementById('paper-equity-card');
  if (!container || typeof LightweightCharts === 'undefined') return;
  card && (card.style.display = 'block');

  if (paperEquityChart) { paperEquityChart.remove(); paperEquityChart = null; }

  paperEquityChart = LightweightCharts.createChart(container, {
    layout: { background: { color: '#0f1117' }, textColor: '#94a3b8' },
    grid:   { vertLines: { color: '#1e2130' }, horzLines: { color: '#1e2130' } },
    rightPriceScale: { borderColor: '#2d3450' },
    timeScale: { borderColor: '#2d3450', timeVisible: true },
    width: container.clientWidth, height: 240,
  });

  const series = paperEquityChart.addAreaSeries({
    lineColor: '#10b981', topColor: 'rgba(16,185,129,0.2)',
    bottomColor: 'rgba(16,185,129,0.02)', lineWidth: 2,
    priceLineVisible: false,
  });
  const data = equityData
    .map(e => ({ time: Math.floor(new Date(e.time).getTime() / 1000), value: e.equity }))
    .filter(d => d.time > 0);
  series.setData(data);
  paperEquityChart.timeScale().fitContent();
}

async function closePaperTrade(id) {
  if (!confirm(`Close paper trade #${id}?`)) return;
  try {
    const r = await fetchJSON(`/api/paper/close/${id}`, { method: 'POST' });
    addActivity(`📄 Paper trade #${id} closed — ${r.pnl_usd >= 0 ? '+' : ''}$${(r.pnl_usd||0).toFixed(2)}`,
      r.pnl_usd >= 0 ? 'success' : 'warning');
    await refreshPaper();
  } catch (e) { alert('Failed: ' + e); }
}
window.closePaperTrade = closePaperTrade;

document.getElementById('paper-toggle')?.addEventListener('change', async (e) => {
  if (e.target.checked) {
    await fetchJSON('/api/paper/enable', { method: 'POST', body: JSON.stringify({}) });
    addActivity('📄 Paper trading ENABLED', 'info');
  } else {
    await fetchJSON('/api/paper/disable', { method: 'POST' });
    addActivity('📄 Paper trading DISABLED', 'info');
  }
  await refreshPaper();
});

document.getElementById('btn-paper-reset')?.addEventListener('click', async () => {
  const bal = parseFloat(document.getElementById('paper-reset-balance')?.value || 10000);
  if (!confirm(`Reset paper account to $${bal}? All open positions will be cancelled.`)) return;
  await fetchJSON('/api/paper/reset', { method: 'POST', body: JSON.stringify({ balance: bal }) });
  addActivity(`📄 Paper account reset to $${bal}`, 'info');
  await refreshPaper();
});

document.getElementById('btn-reset-all')?.addEventListener('click', async () => {
  const bal = parseFloat(document.getElementById('paper-reset-balance')?.value || 5000);
  if (!confirm(`RESET TOTALE: verranno eliminati tutti i trade, log, journal e statistiche.\nIl saldo paper verrà reimpostato a $${bal}.\n\nConfermi?`)) return;
  await fetchJSON('/api/reset-all', { method: 'POST', body: JSON.stringify({ balance: bal }) });
  addActivity(`🗑 Reset totale eseguito — saldo $${bal}`, 'warning');
  await Promise.all([refreshPaper(), refreshTrades(), refreshConfig()]);
});

document.getElementById('btn-paper-refresh')?.addEventListener('click', refreshPaper);

// Handle live paper_update events from WebSocket
function handlePaperUpdate(msg) {
  if (msg.summary) renderPaperSummary(msg.summary);
  if (msg.positions) renderPaperPositions(msg.positions);
  if (msg.summary?.equity_curve) {
    paperEquityData = msg.summary.equity_curve;
    if (paperEquityData.length > 1) renderPaperEquity(paperEquityData);
  }
}

// ── Backtest ──────────────────────────────────────────────────────────
let btEquityChart = null;
let currentBtRunId = null;
let btPollTimer = null;
let _currentBtRun = null;   // full run object for client-side filtering

// Calculate bars + date_from/date_to from the date-range preset
function _btDateRange() {
  const preset = document.getElementById('bt-date-preset')?.value || '90d';
  const tf     = document.getElementById('bt-tf')?.value || 'H1';
  const bptd   = {M5: 288, M15: 96, M30: 48, H1: 24, H4: 6, D1: 1}[tf] || 24;
  const now    = new Date();

  if (preset === 'custom') {
    const from = document.getElementById('bt-date-from')?.value;
    const to   = document.getElementById('bt-date-to')?.value;
    if (!from) return { bars: 500, date_from: null, date_to: null };
    const days = Math.ceil((new Date(to || now) - new Date(from)) / 86400000);
    return { bars: Math.min(Math.ceil(days * bptd * 5/7 * 1.2), 25000), date_from: from, date_to: to || null };
  }

  const days = {'30d': 30, '60d': 60, '90d': 90, '180d': 180, '1y': 365}[preset] || 90;
  const fromDate = new Date(now - days * 86400000);
  return {
    bars:      Math.min(Math.ceil(days * bptd * 5/7 * 1.2), 25000),
    date_from: fromDate.toISOString().slice(0, 10),
    date_to:   null,
  };
}

async function runBacktest() {
  const { bars, date_from, date_to } = _btDateRange();
  const maxRiskVal    = document.getElementById('bt-max-risk-usd')?.value;
  const checkedSetups = [...document.querySelectorAll('.bt-setup-chk:checked')].map(el => el.value);
  const payload = {
    symbol:          document.getElementById('bt-symbol')?.value  || 'EURUSD',
    timeframe:       document.getElementById('bt-tf')?.value      || 'H1',
    strategy:        document.getElementById('bt-strategy')?.value || 'Mixed',
    bars,
    date_from,
    date_to,
    risk_percent:    parseFloat(document.getElementById('bt-risk')?.value  || 1.0),
    rr_ratio:        parseFloat(document.getElementById('bt-rr')?.value    || 2.0),
    initial_balance: parseFloat(document.getElementById('bt-balance')?.value || 10000),
    max_risk_usd:    maxRiskVal ? parseFloat(maxRiskVal) : null,
    enabled_setups:  checkedSetups.length === document.querySelectorAll('.bt-setup-chk').length ? null : checkedSetups,
  };

  setBtStatus('running', '⏳ Running…');
  document.getElementById('bt-results').style.display = 'none';

  try {
    const resp = await fetchJSON('/api/backtest/run', {
      method: 'POST',
      body:   JSON.stringify(payload),
    });
    currentBtRunId = resp.run_id;
    // Poll until DONE
    clearInterval(btPollTimer);
    btPollTimer = setInterval(() => pollBtResult(currentBtRunId), 1500);
  } catch (e) {
    setBtStatus('error', '❌ ' + e.message);
  }
}

async function pollBtResult(runId) {
  try {
    const run = await fetchJSON(`/api/backtest/${runId}`);
    if (run.status === 'DONE') {
      clearInterval(btPollTimer);
      setBtStatus('ok', `✅ Done — ${run.total_trades} trades`);
      renderBtResults(run);
      refreshBtHistory();
    } else if (run.status === 'FAILED') {
      clearInterval(btPollTimer);
      setBtStatus('error', '❌ ' + (run.error || 'Unknown error'));
    } else if (run.status === 'UPDATING_CACHE') {
      setBtStatus('warn', '⏳ Cache dati non aggiornata — aggiornamento in corso...');
    }
  } catch (e) {
    clearInterval(btPollTimer);
    setBtStatus('error', '❌ Polling error');
  }
}

function setBtStatus(type, msg) {
  const el = document.getElementById('bt-run-status');
  if (!el) return;
  el.style.color = type === 'ok' ? '#10b981' : type === 'error' ? '#ef4444' : '#f59e0b';
  el.textContent = msg;
}

// ── Client-side stat recalculation from a filtered trade list ───────────────
function calcBtStatsFromTrades(trades, initialBalance) {
  const closed = trades.filter(t => t.result === 'WIN' || t.result === 'LOSS');
  if (!closed.length) return {
    total_trades: 0, wins: 0, losses: 0, win_rate: 0,
    total_pips: 0, total_pnl_usd: 0, total_return: 0,
    profit_factor: 0, avg_rr: 0, max_drawdown: 0, max_drawdown_usd: 0, sharpe: 0,
    equity: [{ bar: 0, time: new Date().toISOString(), equity: initialBalance }],
  };
  const wins    = closed.filter(t => t.result === 'WIN');
  const totalPips = closed.reduce((s,t) => s + (t.pnl_pips||0), 0);
  const totalUsd  = closed.reduce((s,t) => s + (t.pnl_usd ||0), 0);
  const grossWin  = wins.reduce((s,t) => s + (t.pnl_usd||0), 0);
  const grossLoss = closed.filter(t=>t.result==='LOSS').reduce((s,t)=>s+Math.abs(t.pnl_usd||0),0);
  const pf  = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? 999 : 0);
  const rrs = closed.filter(t=>t.rr_actual!=null).map(t=>t.rr_actual);
  const avgRR = rrs.length ? rrs.reduce((a,b)=>a+b,0)/rrs.length : 0;

  // Rebuild equity from trades sorted by entry_time
  const sorted = [...closed].sort((a,b)=>a.entry_time.localeCompare(b.entry_time));
  let bal = initialBalance, peak = bal, maxDD = 0, maxDDusd = 0;
  const equity = [{ bar: 0, time: sorted[0].entry_time, equity: bal }];
  sorted.forEach((t, i) => {
    bal += (t.pnl_usd || 0);
    if (bal > peak) peak = bal;
    const dd = peak > 0 ? (peak - bal) / peak * 100 : 0;
    if (dd > maxDD) { maxDD = dd; maxDDusd = peak - bal; }
    equity.push({ bar: i+1, time: t.exit_time || t.entry_time, equity: Math.round(bal*100)/100 });
  });

  // Simplified per-trade Sharpe
  const rets = sorted.map(t => (t.pnl_usd||0) / (initialBalance||1));
  const mean = rets.reduce((a,b)=>a+b,0)/rets.length;
  const vari = rets.reduce((a,b)=>a+(b-mean)**2,0)/rets.length;
  const sharpe = vari > 0 ? parseFloat(((mean/Math.sqrt(vari))*Math.sqrt(252)).toFixed(2)) : 0;

  return {
    total_trades: closed.length, wins: wins.length, losses: closed.length-wins.length,
    win_rate: closed.length ? wins.length/closed.length*100 : 0,
    total_pips: totalPips, total_pnl_usd: totalUsd,
    total_return: initialBalance > 0 ? (bal-initialBalance)/initialBalance*100 : 0,
    profit_factor: pf, avg_rr: parseFloat(avgRR.toFixed(2)),
    max_drawdown: maxDD, max_drawdown_usd: maxDDusd, sharpe, equity,
  };
}

function renderBtStatsRow(s) {
  const statsEl = document.getElementById('bt-stats-row');
  if (!statsEl) return;
  const wr = s.win_rate ?? 0, ret = s.total_return ?? 0, pnl = s.total_pnl_usd ?? 0;
  const dd = s.max_drawdown ?? 0, ddUsd = s.max_drawdown_usd ?? 0, pf = s.profit_factor ?? 0;
  statsEl.innerHTML = `
    <div class="stat-card"><div class="stat-value">${s.total_trades ?? 0}</div><div class="stat-label">Trades</div></div>
    <div class="stat-card ${wr>=55?'win':''}"><div class="stat-value">${wr.toFixed(1)}%</div><div class="stat-label">Win Rate</div></div>
    <div class="stat-card"><div class="stat-value ${(s.total_pips??0)>=0?'text-win':'text-loss'}">${(s.total_pips??0).toFixed(1)}</div><div class="stat-label">Total Pips</div></div>
    <div class="stat-card">
      <div class="stat-value ${pnl>=0?'text-win':'text-loss'}">${pnl>=0?'+':''}$${pnl.toFixed(2)}</div>
      <div class="stat-sub ${ret>=0?'text-win':'text-loss'}">${ret.toFixed(2)}%</div>
      <div class="stat-label">Return</div>
    </div>
    <div class="stat-card">
      <div class="stat-value text-loss">-$${ddUsd.toFixed(2)}</div>
      <div class="stat-sub text-loss">${dd.toFixed(2)}%</div>
      <div class="stat-label">Max DD</div>
    </div>
    <div class="stat-card"><div class="stat-value">${pf === 999 ? '∞' : pf.toFixed(2)}</div><div class="stat-label">Profit Factor</div></div>
    <div class="stat-card"><div class="stat-value">${(s.sharpe??0).toFixed(2)}</div><div class="stat-label">Sharpe</div></div>
    <div class="stat-card"><div class="stat-value">${s.avg_rr??0}</div><div class="stat-label">Avg R:R</div></div>
  `;
}

function renderBtTradesTable(trades) {
  const tbody = document.getElementById('bt-trades-tbody');
  const cnt   = document.getElementById('bt-trade-count');
  if (!tbody) return;
  cnt && (cnt.textContent = trades.length);
  tbody.innerHTML = trades.map((t, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><span class="badge">${t.setup}</span></td>
      <td class="${t.direction==='BUY'?'text-win':'text-loss'}">${t.direction}</td>
      <td style="font-size:0.72rem;white-space:nowrap">${fmtDate(t.entry_time)}</td>
      <td style="font-size:0.72rem;white-space:nowrap">${t.exit_time ? fmtDate(t.exit_time) : '—'}</td>
      <td>${t.entry_price}</td>
      <td>${t.stop_loss}</td>
      <td>${t.take_profit}</td>
      <td>${t.exit_price ?? '—'}</td>
      <td style="font-size:0.75rem">${t.lot_size != null ? t.lot_size.toFixed(3) : '—'}</td>
      <td>
        <span class="badge ${t.result==='WIN'?'badge-win':t.result==='LOSS'?'badge-loss':''}">
          ${t.result ?? 'OPEN'}
        </span>
      </td>
      <td class="${(t.pnl_pips??0)>=0?'text-win':'text-loss'}">${t.pnl_pips!=null?t.pnl_pips.toFixed(1):'—'}</td>
      <td class="${(t.pnl_usd??0)>=0?'text-win':'text-loss'}">${t.pnl_usd!=null?'$'+t.pnl_usd.toFixed(2):'—'}</td>
      <td>${t.rr_actual!=null?t.rr_actual.toFixed(2):'—'}</td>
    </tr>
  `).join('');
}

const _SETUP_LABELS = {
  FVG_BULL: 'FVG ↑', FVG_BEAR: 'FVG ↓', OB_BULL: 'OB ↑', OB_BEAR: 'OB ↓',
  LIQ_BULL: 'Liq ↑', LIQ_BEAR: 'Liq ↓', BREAK_BULL: 'BRK ↑', BREAK_BEAR: 'BRK ↓',
};

function _applyBtResultFilter() {
  if (!_currentBtRun) return;
  const checks = [...document.querySelectorAll('.bt-res-chk')];
  const checked = checks.filter(c=>c.checked).map(c=>c.value);
  const trades = checked.length === checks.length
    ? _currentBtRun.trades
    : _currentBtRun.trades.filter(t => checked.includes(t.setup));

  const initBal = _currentBtRun.equity?.[0]?.equity || 10000;
  const stats   = calcBtStatsFromTrades(trades, initBal);
  renderBtStatsRow(stats);
  if (stats.equity.length > 1) renderBtEquity(stats.equity);
  renderBtBySetup(trades);
  _btCal.setTrades(trades);
  renderBtTradesTable(trades);
}

function setupBtResultFilter(run) {
  _currentBtRun = run;
  const filterEl = document.getElementById('bt-result-filter');
  const container = document.getElementById('bt-result-filter-checks');
  if (!filterEl || !container) return;

  const setups = [...new Set((run.trades||[]).map(t=>t.setup).filter(Boolean))].sort();
  if (setups.length < 2) { filterEl.style.display = 'none'; return; }

  filterEl.style.display = 'block';
  container.innerHTML = setups.map(s =>
    `<label class="check-pill"><input type="checkbox" class="bt-res-chk" value="${s}" checked> ${_SETUP_LABELS[s]||s}</label>`
  ).join('');
  container.querySelectorAll('.bt-res-chk').forEach(cb =>
    cb.addEventListener('change', _applyBtResultFilter)
  );
  document.getElementById('btn-bt-res-all')?.addEventListener('click', () => {
    container.querySelectorAll('.bt-res-chk').forEach(c => c.checked = true);
    _applyBtResultFilter();
  });
  document.getElementById('btn-bt-res-none')?.addEventListener('click', () => {
    container.querySelectorAll('.bt-res-chk').forEach(c => c.checked = false);
    _applyBtResultFilter();
  });
}

function renderBtResults(run) {
  const resultsEl = document.getElementById('bt-results');
  if (!resultsEl) return;
  resultsEl.style.display = 'block';

  // ── Data warning banner ───────────────────────────────────────────────
  let warnEl = document.getElementById('bt-data-warning');
  if (!warnEl) {
    warnEl = document.createElement('div');
    warnEl.id = 'bt-data-warning';
    warnEl.style.cssText = 'display:none;margin-bottom:12px;padding:12px 16px;border-radius:8px;background:#422006;border:1px solid #f97316;color:#fed7aa;font-size:0.875rem;line-height:1.5';
    resultsEl.prepend(warnEl);
  }
  warnEl.style.display = run.data_warning ? 'block' : 'none';
  if (run.data_warning) warnEl.textContent = run.data_warning;

  // Stats row (from full run data)
  renderBtStatsRow(run);

  // Equity curve
  if (run.equity && run.equity.length > 1) renderBtEquity(run.equity);

  // Result-side setup filter (must come after trades are known)
  if (run.trades) setupBtResultFilter(run);

  // By setup breakdown
  if (run.trades) renderBtBySetup(run.trades);

  // PNL Calendar
  if (run.trades?.length) _btCal.setTrades(run.trades);

  // Trades table
  if (run.trades) renderBtTradesTable(run.trades);
}

function renderBtBySetup(trades) {
  const tbody = document.getElementById('bt-setup-tbody');
  if (!tbody) return;
  const closed = trades.filter(t => t.result === 'WIN' || t.result === 'LOSS');
  if (!closed.length) { tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No closed trades</td></tr>'; return; }

  const groups = {};
  for (const t of closed) {
    const s = t.setup || '—';
    if (!groups[s]) groups[s] = { trades: 0, wins: 0, losses: 0, pips: 0, usd: 0, rrs: [], grossWin: 0, grossLoss: 0 };
    groups[s].trades++;
    if (t.result === 'WIN') { groups[s].wins++; groups[s].grossWin += t.pnl_pips ?? 0; }
    else                    { groups[s].losses++; groups[s].grossLoss += Math.abs(t.pnl_pips ?? 0); }
    groups[s].pips += t.pnl_pips ?? 0;
    groups[s].usd  += t.pnl_usd  ?? 0;
    if (t.rr_actual != null) groups[s].rrs.push(t.rr_actual);
  }

  tbody.innerHTML = Object.entries(groups)
    .sort((a, b) => b[1].usd - a[1].usd)
    .map(([setup, g]) => {
      const wr      = g.trades ? g.wins / g.trades * 100 : 0;
      const wrStr   = wr.toFixed(1);
      const avgRR   = g.rrs.length ? (g.rrs.reduce((a,b) => a+b, 0) / g.rrs.length).toFixed(2) : '—';
      const pf      = g.grossLoss > 0 ? (g.grossWin / g.grossLoss).toFixed(2) : g.grossWin > 0 ? '∞' : '—';
      const exp     = g.trades ? (g.pips / g.trades).toFixed(1) : '—';
      const pClass  = g.pips >= 0 ? 'text-win' : 'text-loss';
      const uClass  = g.usd  >= 0 ? 'text-win' : 'text-loss';
      const wrClass = wr >= 50 ? 'text-win' : 'text-loss';
      const pfNum   = parseFloat(pf);
      const pfClass = pfNum >= 1.5 ? 'text-win' : pfNum >= 1.0 ? '' : 'text-loss';
      const expClass = parseFloat(exp) >= 0 ? 'text-win' : 'text-loss';
      // mini bar for win rate
      const bar = `<div style="display:flex;align-items:center;gap:6px">
        <span class="${wrClass}">${wrStr}%</span>
        <div style="flex:1;min-width:60px;height:6px;background:#1e2130;border-radius:3px;overflow:hidden">
          <div style="width:${Math.round(wr)}%;height:100%;background:${wr>=50?'#22c55e':'#ef4444'};border-radius:3px"></div>
        </div>
      </div>`;
      return `<tr>
        <td><span class="badge">${setup}</span></td>
        <td>${g.trades}</td>
        <td class="text-win">${g.wins}</td>
        <td class="text-loss">${g.losses}</td>
        <td style="min-width:110px">${bar}</td>
        <td class="${pClass}">${g.pips.toFixed(1)}</td>
        <td class="${uClass}">${g.usd >= 0 ? '+' : ''}$${g.usd.toFixed(2)}</td>
        <td>${avgRR}</td>
        <td class="${pfClass}">${pf}</td>
        <td class="${expClass}">${exp}</td>
      </tr>`;
    }).join('');
}

function renderBtEquity(equityData) {
  const container = document.getElementById('bt-equity-canvas');
  if (!container || typeof LightweightCharts === 'undefined') return;

  if (btEquityChart) {
    btEquityChart.remove();
    btEquityChart = null;
  }

  btEquityChart = LightweightCharts.createChart(container, {
    layout: { background: { color: '#0f1117' }, textColor: '#94a3b8' },
    grid:   { vertLines: { color: '#1e2130' }, horzLines: { color: '#1e2130' } },
    rightPriceScale: { borderColor: '#2d3450' },
    timeScale: { borderColor: '#2d3450', timeVisible: true },
    width:  container.clientWidth,
    height: 260,
  });

  const lineSeries = btEquityChart.addAreaSeries({
    lineColor:    '#3b82f6',
    topColor:     'rgba(59,130,246,0.25)',
    bottomColor:  'rgba(59,130,246,0.02)',
    lineWidth:    2,
    priceLineVisible: false,
  });

  const data = equityData.map(e => ({
    time:  Math.floor(new Date(e.time).getTime() / 1000),
    value: e.equity,
  })).filter(d => d.time > 0);

  lineSeries.setData(data);
  btEquityChart.timeScale().fitContent();
}

async function refreshBtHistory() {
  try {
    const runs  = await fetchJSON('/api/backtest?limit=15');
    const tbody = document.getElementById('bt-history-tbody');
    if (!tbody) return;
    if (!runs.length) {
      tbody.innerHTML = '<tr><td colspan="13" class="empty-state">No runs yet</td></tr>';
      return;
    }
    tbody.innerHTML = runs.map(r => {
      const statusClass = r.status === 'DONE' ? 'badge-win' : r.status === 'FAILED' ? 'badge-loss' : 'badge-warn';
      return `
        <tr>
          <td>${r.id}</td>
          <td><b>${r.symbol}</b></td>
          <td>${r.timeframe}</td>
          <td>${r.strategy}</td>
          <td>${r.total_trades ?? '—'}</td>
          <td class="${(r.win_rate??0)>=55?'text-win':''}">${r.win_rate!=null?r.win_rate.toFixed(1)+'%':'—'}</td>
          <td class="${(r.total_pips??0)>=0?'text-win':'text-loss'}">${r.total_pips!=null?r.total_pips.toFixed(1):'—'}</td>
          <td class="${(r.total_return??0)>=0?'text-win':'text-loss'}">${r.total_return!=null?r.total_return.toFixed(2)+'%':'—'}</td>
          <td class="text-loss">${r.max_drawdown!=null?r.max_drawdown.toFixed(2)+'%':'—'}</td>
          <td>${r.profit_factor!=null?(r.profit_factor===999?'∞':r.profit_factor.toFixed(2)):'—'}</td>
          <td>${r.sharpe!=null?r.sharpe.toFixed(2):'—'}</td>
          <td><span class="badge ${statusClass}">${r.status}</span></td>
          <td>${r.status==='DONE'?`<button class="btn btn-ghost btn-sm" onclick="loadBtRun(${r.id})">Load</button>`:''}</td>
        </tr>
      `;
    }).join('');
  } catch (e) { console.error('refreshBtHistory', e); }
}

async function loadBtRun(runId) {
  try {
    const run = await fetchJSON(`/api/backtest/${runId}`);
    renderBtResults(run);
    document.getElementById('bt-results').scrollIntoView({ behavior: 'smooth' });
  } catch (e) { alert('Failed to load run: ' + e.message); }
}
window.loadBtRun = loadBtRun;

document.getElementById('btn-bt-run')?.addEventListener('click', runBacktest);
document.getElementById('btn-bt-refresh-history')?.addEventListener('click', refreshBtHistory);

// Toggle custom date inputs visibility
document.getElementById('bt-date-preset')?.addEventListener('change', function() {
  const row = document.getElementById('bt-date-custom-row');
  if (row) row.style.display = this.value === 'custom' ? 'flex' : 'none';
});

// Default bt-date-to to today
const _todayIso = new Date().toISOString().slice(0, 10);
const _btDateTo = document.getElementById('bt-date-to');
if (_btDateTo && !_btDateTo.value) _btDateTo.value = _todayIso;

// ── OHLCV Data Cache ──────────────────────────────────────────────────────────
let _cachePollTimer = null;

const _DURATION_BARS = {
  '90d':  { M15: 8640, M30: 4320, H1: 2160, H4: 540,  D1: 90  },
  '180d': { M15:17280, M30: 8640, H1: 4320, H4:1080,  D1: 180 },
  '1y':   { M15:35040, M30:17520, H1: 8760, H4:2190,  D1: 365 },
  '2y':   { M15:70080, M30:35040, H1:17520, H4:4380,  D1: 730 },
  '5y':   { M15:175200,M30:87600, H1:43800, H4:10950, D1:1825 },
};

async function refreshCacheStatus() {
  try {
    const data  = await fetchJSON('/api/ohlcv/status');
    const tbody = document.getElementById('cache-tbody');
    if (!tbody) return;

    if (!data.cached?.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No cached data — click Build to download</td></tr>';
    } else {
      tbody.innerHTML = data.cached.map(row => {
        const build = row.build || {};
        const progressHtml = build.status === 'running' || build.status === 'updating'
          ? `<span style="color:#f97316;font-size:0.78rem">${build.done}/${build.total} bars…</span>`
          : build.status === 'error'
            ? `<span style="color:#ef4444;font-size:0.78rem">Error</span>`
            : '';
        return `<tr>
          <td><b>${row.symbol}</b></td>
          <td>${row.timeframe}</td>
          <td>${row.bars.toLocaleString()}</td>
          <td style="font-size:0.78rem">${row.from ? row.from.slice(0,10) : '—'}</td>
          <td style="font-size:0.78rem">${row.to   ? row.to.slice(0,10)   : '—'}</td>
          <td style="white-space:nowrap">
            ${progressHtml}
            <button class="btn btn-ghost btn-sm" onclick="cacheUpdate('${row.symbol}','${row.timeframe}')">↑ Update</button>
            <button class="btn btn-ghost btn-sm" style="color:#ef4444" onclick="cacheClear('${row.symbol}','${row.timeframe}')">✕</button>
          </td>
        </tr>`;
      }).join('');
    }

    // If any build is running, keep polling
    const anyRunning = Object.values(data.building || {}).length > 0;
    if (anyRunning && !_cachePollTimer) {
      _cachePollTimer = setInterval(refreshCacheStatus, 1500);
    } else if (!anyRunning && _cachePollTimer) {
      clearInterval(_cachePollTimer); _cachePollTimer = null;
      _hideCacheProgress();
    }
  } catch(e) { console.error('refreshCacheStatus', e); }
}

function _showCacheProgress(label) {
  const wrap = document.getElementById('cache-progress-wrap');
  if (wrap) wrap.style.display = 'block';
  const lbl = document.getElementById('cache-progress-label');
  if (lbl) lbl.textContent = label;
}
function _hideCacheProgress() {
  const wrap = document.getElementById('cache-progress-wrap');
  if (wrap) wrap.style.display = 'none';
}
function _updateCacheProgress(done, total) {
  const bar   = document.getElementById('cache-progress-bar');
  const pctEl = document.getElementById('cache-progress-pct');
  if (total > 0) {
    const pct = Math.round(done / total * 100);
    if (bar)   { bar.style.width = pct + '%'; bar.style.opacity = '1'; }
    if (pctEl) pctEl.textContent = `${pct}%  (${done.toLocaleString()} / ${total.toLocaleString()})`;
  } else {
    // Total unknown (still fetching from MT5) — pulse animation
    if (bar)   { bar.style.width = '100%'; bar.style.opacity = null; bar.classList.add('cache-bar-pulse'); }
    if (pctEl) pctEl.textContent = done > 0 ? `${done.toLocaleString()} bars…` : 'Fetching data…';
  }
}

async function cacheBuild() {
  const sym  = document.getElementById('cache-symbol')?.value || 'EURUSD';
  const tf   = document.getElementById('cache-tf')?.value || 'H1';
  const dur  = document.getElementById('cache-duration')?.value || '1y';
  const bars = (_DURATION_BARS[dur] || {})[tf] || 8760;

  _showCacheProgress(`Building ${sym} ${tf} (${bars.toLocaleString()} bars)…`);
  _updateCacheProgress(0, bars);
  if (!_cachePollTimer) _cachePollTimer = setInterval(refreshCacheStatus, 1500);

  const key   = `${sym}_${tf}`;
  const keyM1 = `${sym}_M1`;

  // Generic poller: tracks any key and calls onDone when complete.
  // idleRetries: how many times to retry before giving up on "idle" status
  // (needed because asyncio.create_task may not start before the first poll)
  const pollKey = (trackKey, label, onDone, idleRetries = 5) => {
    const run = async (retries) => {
      const p = await fetchJSON(`/api/ohlcv/progress/${trackKey}`).catch(() => null);
      if (!p || p.status === 'idle') {
        if (retries > 0) { setTimeout(() => run(retries - 1), 1200); }
        else             { onDone(); }
        return;
      }
      _showCacheProgress(label);
      _updateCacheProgress(p.done || 0, p.total || 0);
      const bar = document.getElementById('cache-progress-bar');
      if (bar) bar.classList.remove('cache-bar-pulse');
      if      (p.status === 'done')  { refreshCacheStatus(); onDone(); }
      else if (p.status === 'error') { _hideCacheProgress(); alert(`Error (${trackKey}): ${p.error}`); }
      else    setTimeout(() => run(0), 1000);
    };
    setTimeout(() => run(idleRetries), 800);
  };

  try {
    await fetchJSON('/api/ohlcv/build', { method: 'POST', body: JSON.stringify({ symbol: sym, timeframe: tf, bars }) });
    // Phase 1: H1  →  Phase 2: M1 (launched automatically by backend)
    pollKey(key, `Building ${sym} ${tf} (${bars.toLocaleString()} bars)…`, () => {
      pollKey(keyM1, `Building ${sym} M1 precision data… (questo richiede qualche minuto)`, () => {
        _hideCacheProgress();
        refreshCacheStatus();
      });
    });
  } catch(e) { _hideCacheProgress(); alert('Build failed: ' + e.message); }
}

async function cacheUpdate(symbol, tf) {
  const key = `${symbol}_${tf}`;
  _showCacheProgress(`Updating ${symbol} ${tf}…`);
  if (!_cachePollTimer) _cachePollTimer = setInterval(refreshCacheStatus, 1500);
  try {
    await fetchJSON('/api/ohlcv/update', { method: 'POST', body: JSON.stringify({ symbol, timeframe: tf }) });
  } catch(e) { _hideCacheProgress(); alert('Update failed: ' + e.message); }
}

async function cacheClear(symbol, tf) {
  if (!confirm(`Delete cached data for ${symbol} ${tf}?`)) return;
  try {
    const r = await fetchJSON('/api/ohlcv/clear', { method: 'DELETE', body: JSON.stringify({ symbol, timeframe: tf }) });
    alert(`Deleted ${r.deleted} bars`);
    refreshCacheStatus();
  } catch(e) { alert('Clear failed: ' + e.message); }
}

window.cacheUpdate = cacheUpdate;
window.cacheClear  = cacheClear;

document.getElementById('btn-cache-build')?.addEventListener('click', cacheBuild);
document.getElementById('btn-cache-refresh')?.addEventListener('click', refreshCacheStatus);
document.getElementById('btn-cache-update-all')?.addEventListener('click', async () => {
  const rows = document.querySelectorAll('#cache-tbody tr[data-sym]');
  // fallback: read from table cells
  const tbody = document.getElementById('cache-tbody');
  const trs = tbody?.querySelectorAll('tr') || [];
  for (const tr of trs) {
    const cells = tr.querySelectorAll('td');
    if (cells.length >= 2) await cacheUpdate(cells[0].textContent.trim(), cells[1].textContent.trim());
  }
});

// Keep WS alive
setInterval(() => { if (ws?.readyState === WebSocket.OPEN) sendWS({ command: 'ping' }); }, 30000);

// ── Boot ─────────────────────────────────────────────────────────────
async function boot() {
  renderPairsGrid();
  connectWS();
  await refreshAll();
  // Periodic auto-refresh (every 30s)
  setInterval(refreshTrades, 30000);
}

boot();

// ── PNL Calendar ──────────────────────────────────────────────────────────────
class PnlCalendar {
  constructor(containerId) {
    this.containerId  = containerId;
    this.trades       = [];
    this.year         = new Date().getFullYear();
    this.month        = new Date().getMonth();
    this.activeSetups = null; // null = all
  }

  _isClosed(t) {
    return t.result === 'WIN' || t.result === 'LOSS' || t.status === 'CLOSED';
  }
  _isWin(t) {
    if (t.result === 'WIN')  return true;
    if (t.result === 'LOSS') return false;
    return (t.pnl_usd || 0) > 0;
  }

  setTrades(trades) {
    this.trades = trades;
    // Jump to most recent month with trades
    const dates = trades
      .filter(t => (t.exit_time || t.close_time) && this._isClosed(t))
      .map(t => this._parseDate(t.exit_time || t.close_time)).filter(Boolean);
    if (dates.length) {
      const latest = new Date(Math.max(...dates.map(d => d.getTime())));
      this.year  = latest.getFullYear();
      this.month = latest.getMonth();
    }
    this._buildFilter();
    this.render();
  }

  _parseDate(s) {
    if (!s) return null;
    // "16/06/25, 18:00:00" → dd/mm/yy
    const m = s.match(/^(\d{2})\/(\d{2})\/(\d{2})[, ]/);
    if (m) return new Date(2000 + +m[3], +m[2] - 1, +m[1]);
    // ISO / other
    const d = new Date(s);
    return isNaN(d) ? null : d;
  }

  _buildFilter() {
    const container = document.getElementById(this.containerId);
    if (!container) return;
    const setups = [...new Set(this.trades.map(t => t.setup).filter(Boolean))].sort();
    if (setups.length < 2) { this.activeSetups = null; return; }

    const wrap = document.createElement('div');
    wrap.className = 'pnl-cal-filter';
    wrap.innerHTML = setups.map(s =>
      `<label class="check-pill"><input type="checkbox" class="cal-setup-chk" value="${s}" checked> ${s}</label>`
    ).join('');
    container.innerHTML = '';
    container.appendChild(wrap);

    wrap.querySelectorAll('.cal-setup-chk').forEach(cb => {
      cb.addEventListener('change', () => {
        const checked = [...wrap.querySelectorAll('.cal-setup-chk:checked')].map(c => c.value);
        this.activeSetups = checked.length === setups.length ? null : new Set(checked);
        this.render(true); // re-render grid only
      });
    });
  }

  _buildDayMap() {
    const map = {};
    for (const t of this.trades) {
      if (!this._isClosed(t)) continue;
      if (this.activeSetups && !this.activeSetups.has(t.setup)) continue;
      const d = this._parseDate(t.exit_time || t.close_time);
      if (!d || d.getFullYear() !== this.year || d.getMonth() !== this.month) continue;
      const day = d.getDate();
      if (!map[day]) map[day] = { pnl: 0, wins: 0, losses: 0 };
      map[day].pnl    += t.pnl_usd || 0;
      if (this._isWin(t)) map[day].wins++; else map[day].losses++;
    }
    return map;
  }

  render(gridOnly = false) {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Remove old grid if exists
    const oldGrid = container.querySelector('.cal-grid-wrap');
    if (oldGrid) oldGrid.remove();

    const dayMap  = this._buildDayMap();
    const first   = new Date(this.year, this.month, 1).getDay();
    const total   = new Date(this.year, this.month + 1, 0).getDate();
    const today   = new Date();
    const todayD  = today.getFullYear() === this.year && today.getMonth() === this.month ? today.getDate() : -1;
    const maxAbs  = Math.max(1, ...Object.values(dayMap).map(d => Math.abs(d.pnl)));
    const mName   = new Date(this.year, this.month).toLocaleString('default', { month: 'long', year: 'numeric' });
    const DAYS    = ['SUN','MON','TUE','WED','THU','FRI','SAT'];

    const wrap = document.createElement('div');
    wrap.className = 'cal-grid-wrap';

    // Nav row
    const nav = document.createElement('div');
    nav.className = 'pnl-cal-nav';
    nav.innerHTML = `
      <button class="btn btn-ghost btn-sm cal-prev">←</button>
      <span class="pnl-cal-title">${mName}</span>
      <button class="btn btn-ghost btn-sm cal-next">→</button>`;
    wrap.appendChild(nav);

    // Grid
    const grid = document.createElement('div');
    grid.className = 'cal-grid';
    grid.innerHTML = DAYS.map(d => `<div class="cal-head">${d}</div>`).join('');

    // Empty prefix cells
    for (let i = 0; i < first; i++) grid.innerHTML += `<div class="cal-cell cal-empty"></div>`;

    for (let day = 1; day <= total; day++) {
      const data = dayMap[day];
      const cell = document.createElement('div');
      cell.className = 'cal-cell' + (day === todayD ? ' cal-today' : '');
      if (data) {
        const isPos = data.pnl >= 0;
        const intens = Math.min(0.85, 0.18 + 0.67 * Math.abs(data.pnl) / maxAbs);
        cell.style.background = isPos
          ? `rgba(34,197,94,${intens})` : `rgba(239,68,68,${intens})`;
        const tot = data.wins + data.losses;
        const wr  = tot ? Math.round(data.wins / tot * 100) : 0;
        const pnlFmt = (isPos ? '+' : '-') + '$' + Math.abs(data.pnl).toFixed(2);
        cell.innerHTML = `
          <div class="cal-day" style="color:#ffffffcc">${day}</div>
          <div class="cal-pnl" style="color:#fff;font-weight:700">${pnlFmt}</div>
          <div class="cal-wr" style="color:#ffffffbb">${wr}%</div>`;
      } else {
        cell.innerHTML = `<div class="cal-day">${day}</div>`;
      }
      grid.appendChild(cell);
    }
    wrap.appendChild(grid);
    container.appendChild(wrap);

    nav.querySelector('.cal-prev').onclick = () => {
      this.month--;
      if (this.month < 0) { this.month = 11; this.year--; }
      this.render();
    };
    nav.querySelector('.cal-next').onclick = () => {
      this.month++;
      if (this.month > 11) { this.month = 0; this.year++; }
      this.render();
    };
  }
}

// Calendar instances
const _perfCal   = new PnlCalendar('perf-cal');
const _tradesCal = new PnlCalendar('trades-cal');
const _btCal     = new PnlCalendar('bt-cal');
