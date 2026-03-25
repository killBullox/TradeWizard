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
  item.innerHTML = `
    <span class="comm-agent ${agent}">${AGENTS[agent]?.emoji || ''} ${agent}</span>
    <span class="comm-msg">${isThinking ? '💭 ' : ''}${escHtml(message?.substring(0,200))}${message?.length>200?'…':''}</span>
    <span class="comm-time">${now}</span>
  `;
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
    const trades = await fetchJSON('/api/trades?limit=100');
    state.trades = trades;
    renderTradesTable(trades);
    renderOpenTrades(trades.filter(t => t.status === 'ACTIVE'));
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
      <td>${t.entry_price ?? '-'}</td>
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

function renderOpenTrades(trades) {
  const el = document.getElementById('open-trades-list');
  const cntEl = document.getElementById('open-trades-count');
  if (!el) return;
  if (cntEl) cntEl.textContent = trades.length;
  if (!trades.length) { el.innerHTML = '<div class="empty-state">No open trades</div>'; return; }
  el.innerHTML = trades.map(t => `
    <div class="open-trade-card">
      <div class="trade-header-row">
        <span class="trade-symbol">${t.symbol}</span>
        <span class="trade-dir ${t.direction}">${t.direction}</span>
        <span class="trade-setup">${t.ict_setup||'ICT'}</span>
        <button class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">✕</button>
      </div>
      <div class="trade-levels">
        <div><div class="trade-level-label">Entry</div><div class="trade-level-val">${t.entry_price}</div></div>
        <div><div class="trade-level-label">SL</div><div class="trade-level-val text-loss">${t.stop_loss}</div></div>
        <div><div class="trade-level-label">TP1</div><div class="trade-level-val text-win">${t.take_profit_1}</div></div>
      </div>
    </div>
  `).join('');
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
}

function renderConfig(cfg) {
  const form = document.getElementById('config-form');
  if (!form) return;
  const editable = ['risk_percent','rr_ratio','max_open_trades','account_balance','analysis_interval'];
  form.innerHTML = editable.map(key => `
    <div class="config-field">
      <label>${key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</label>
      <input type="text" id="cfg-${key}" value="${escHtml(cfg[key]||'')}" />
    </div>
  `).join('');
}

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
  addActivity('⚙️ Configuration saved', 'success');
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
  try { return new Date(iso).toLocaleString('it-IT', {dateStyle:'short',timeStyle:'short'}); }
  catch { return iso; }
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
