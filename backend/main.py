"""
TradeWizard — Multi-Agent ICT Forex Trading System
FastAPI backend with WebSocket for real-time agent communication.
"""

import sys
import os
# Ensure the backend directory is on sys.path regardless of where uvicorn is launched from
sys.path.insert(0, os.path.dirname(__file__))

import json
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Set

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, delete

load_dotenv()

from models.database import (
    async_session_factory, init_db, Trade, AgentLog,
    JournalEntry, Meeting, SystemConfig, set_config, get_config,
    BacktestRun, OhlcvBar,
)
from orchestrator import Orchestrator
from services.forex_data import fetch_ohlcv
from services.backtester import run_backtest
from services.analytics import compute_analytics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# In-memory build/update progress tracker  key = "SYMBOL_TF"
_build_tasks: dict[str, dict] = {}

# ------------------------------------------------------------------ #
#  WebSocket Connection Manager
# ------------------------------------------------------------------ #
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)
        logger.info(f"WS client connected (total: {len(self.active)})")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active.discard(ws)

    async def broadcast(self, message: dict):
        if not self.active:
            return
        data = json.dumps(message, default=str)
        disconnected = set()
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.add(ws)
        async with self._lock:
            self.active -= disconnected


manager = ConnectionManager()
orchestrator: Orchestrator | None = None


# ------------------------------------------------------------------ #
#  App Lifecycle
# ------------------------------------------------------------------ #
_bridge_proc = None


def _start_mt5_bridge():
    """Launch mt5_bridge.py as a subprocess if not already running."""
    import subprocess
    global _bridge_proc
    bridge_script = os.path.join(os.path.dirname(__file__), "mt5_bridge.py")
    if not os.path.exists(bridge_script):
        return
    port = os.getenv("MT5_BRIDGE_PORT", "5002")
    env = {**os.environ, "MT5_BRIDGE_PORT": port}
    try:
        _bridge_proc = subprocess.Popen(
            [sys.executable, bridge_script],
            env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        logger.info("MT5 bridge started (PID %s) on port %s", _bridge_proc.pid, port)
    except Exception as exc:
        logger.warning("Could not start MT5 bridge: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    await init_db()
    _start_mt5_bridge()
    # Set default MT5 bridge URL if not already configured
    async with async_session_factory() as s:
        existing = await get_config("mt5_bridge_url", s)
        if not existing:
            await set_config("mt5_bridge_url", "http://localhost:5002", s)
            await s.commit()
    orchestrator = Orchestrator(broadcast_fn=manager.broadcast)
    await orchestrator.start()
    logger.info("TradeWizard system started ✅")
    yield
    if orchestrator:
        await orchestrator.stop()
    if _bridge_proc and _bridge_proc.poll() is None:
        _bridge_proc.terminate()
        logger.info("MT5 bridge stopped")
    logger.info("TradeWizard system stopped")


app = FastAPI(
    title="TradeWizard",
    description="Multi-Agent ICT Forex Trading System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files — no-cache headers so browser always gets latest
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    from fastapi.responses import FileResponse
    from fastapi import Response

    @app.get("/static/{file_path:path}")
    async def static_files(file_path: str, response: Response):
        full = os.path.join(frontend_dir, file_path)
        if not os.path.exists(full):
            raise HTTPException(404, "Not found")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return FileResponse(full)


# ------------------------------------------------------------------ #
#  WebSocket Endpoint
# ------------------------------------------------------------------ #
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send current status immediately
    if orchestrator:
        status = await orchestrator.get_status()
        await ws.send_text(json.dumps({"type": "init", "status": status}, default=str))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                await handle_ws_command(ws, msg)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(ws)


async def handle_ws_command(ws: WebSocket, msg: dict):
    cmd = msg.get("command")
    if cmd == "analyze":
        symbol = msg.get("symbol")
        asyncio.create_task(orchestrator.trigger_analysis(symbol))
    elif cmd == "close_trade":
        tid = msg.get("trade_id")
        if tid:
            asyncio.create_task(orchestrator.close_trade_manually(int(tid)))
    elif cmd == "run_meeting":
        meeting_type = msg.get("meeting_type", "POST_TRADE")
        asyncio.create_task(orchestrator.run_meeting(meeting_type))
    elif cmd == "ping":
        await ws.send_text(json.dumps({"type": "pong", "ts": datetime.utcnow().isoformat()}))


# ------------------------------------------------------------------ #
#  REST API Endpoints
# ------------------------------------------------------------------ #
@app.get("/mt5-setup", response_class=HTMLResponse)
async def mt5_setup_page():
    async with async_session_factory() as s:
        current_url = await get_config("mt5_bridge_url", s) or ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>MT5 Bridge Setup</title>
<style>
  body {{ font-family: sans-serif; max-width: 600px; margin: 60px auto; padding: 20px; background:#1a1a2e; color:#eee; }}
  h2 {{ color:#a78bfa; }}
  input {{ width:100%; padding:10px; font-size:16px; background:#2d2d44; border:1px solid #555; color:#eee; border-radius:6px; box-sizing:border-box; margin:10px 0; }}
  button {{ padding:12px 28px; background:#7c3aed; color:#fff; border:none; border-radius:6px; font-size:16px; cursor:pointer; }}
  button:hover {{ background:#6d28d9; }}
  .ok {{ color:#4ade80; margin-top:12px; display:none; }}
  .info {{ color:#94a3b8; font-size:0.85rem; margin-bottom:20px; }}
</style>
</head><body>
<h2>⚙️ MT5 Bridge URL</h2>
<p class="info">Inserisci l'URL del bridge MT5 Python che gira sul PC Windows con MetaTrader 5 aperto.<br>
Esempio: <code>http://192.168.1.10:5001</code> oppure <code>http://localhost:5001</code></p>
<input type="text" id="url" value="{current_url}" placeholder="http://192.168.1.10:5001" />
<br>
<button onclick="save()">💾 Salva</button>
<p class="ok" id="ok">✅ Salvato!</p>
<br><br>
<a href="/" style="color:#a78bfa">← Torna all'app</a>
<script>
async function save() {{
  const val = document.getElementById('url').value.trim();
  await fetch('/api/config/mt5_bridge_url', {{method:'PUT', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{value:val}})}});
  document.getElementById('ok').style.display='block';
  setTimeout(()=>document.getElementById('ok').style.display='none', 3000);
}}
</script>
</body></html>"""


_MT5_STATUS_DIV = (
    '<div class="status-indicator" id="mt5-status" style="margin-left:16px">'
    '<span class="dot disconnected" id="mt5-dot"></span>'
    '<span id="mt5-label">MT5 &#8212;</span>'
    '</div>'
)
_MT5_STATUS_JS = (
    '<script>'
    'async function checkMt5Status(){'
    'var dot=document.getElementById("mt5-dot");'
    'var lbl=document.getElementById("mt5-label");'
    'if(!dot||!lbl)return;'
    'try{'
    'var r=await fetch("/api/mt5/health");'
    'var d=await r.json();'
    'if(d.connected){dot.className="dot connected";lbl.textContent="MT5 \u2713";}'
    'else{dot.className="dot connecting";lbl.textContent="MT5 \u2014 no MT5";}'
    '}catch(e){dot.className="dot disconnected";lbl.textContent="MT5 \u2014";}'
    '}'
    'checkMt5Status();setInterval(checkMt5Status,15000);'
    '</script>'
)


@app.get("/", response_class=HTMLResponse)
async def root():
    import re, time
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        with open(index, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        v = str(int(time.time()))
        html = re.sub(r'src="/static/app\.js[^"]*"',    f'src="/static/app.js?v={v}"',    html)
        html = re.sub(r'href="/static/styles\.css[^"]*"', f'href="/static/styles.css?v={v}"', html)
        html = re.sub(r'src="/static/charts\.js[^"]*"', f'src="/static/charts.js?v={v}"', html)
        # Inject MT5 status dot next to WS dot (server-side — never edit HTML on disk)
        html = re.sub(
            r'(<div class="status-indicator" id="ws-status">.*?</div>)',
            r'\1' + _MT5_STATUS_DIV,
            html, flags=re.DOTALL
        )
        # Inject MT5 polling JS (idempotent)
        if 'checkMt5Status' not in html:
            html = html.replace('</body>', _MT5_STATUS_JS + '</body>')
        return HTMLResponse(content=html, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        })
    return HTMLResponse(content='{"message":"TradeWizard API"}')


@app.get("/api/status")
async def get_status():
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    return await orchestrator.get_status()


@app.get("/api/trades")
async def list_trades(status: str | None = None, limit: int = 50):
    async with async_session_factory() as s:
        q = select(Trade).order_by(desc(Trade.created_at)).limit(limit)
        if status:
            q = q.where(Trade.status == status.upper())
        result = await s.execute(q)
        trades = result.scalars().all()
        return [_trade_to_dict(t) for t in trades]


# NOTE: must be defined BEFORE /api/trades/{trade_id} to avoid 422 on "live_pnl"
@app.get("/api/trades/live_pnl")
async def trades_live_pnl():
    """Return current price + unrealized PNL for all active trades."""
    async with async_session_factory() as s:
        result = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
        active = result.scalars().all()
    if not active:
        return []

    from services.forex_data import fetch_ohlcv
    async with async_session_factory() as s:
        mt5_url  = await get_config("mt5_bridge_url", s) or ""

    # Fetch prices concurrently, one per unique symbol
    symbols = list({t.symbol for t in active})
    async def _price(sym):
        try:
            data = await fetch_ohlcv(sym, "H1", 2, mt5_bridge_url=mt5_url)
            return sym, float(data.get("indicators", {}).get("current_price") or 0)
        except Exception:
            return sym, 0.0

    prices = dict(await asyncio.gather(*[_price(s) for s in symbols]))

    out = []
    for t in active:
        cp = prices.get(t.symbol, 0.0)
        pip = 0.01 if "JPY" in t.symbol else (1.0 if t.symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)
        _pip_usd = {"XAUUSD":100.0,"US30":5.0,"NAS100":20.0,"US500":50.0,
                    "USDJPY":6.5,"EURJPY":6.5,"GBPJPY":6.5,"AUDJPY":6.5,
                    "USDCHF":11.0,"USDCAD":7.25}
        pip_usd = _pip_usd.get(t.symbol, 10.0)
        if cp and t.entry_price:
            pnl_pips = ((cp - t.entry_price) if t.direction == "BUY" else (t.entry_price - cp)) / pip
            pnl_usd  = round(pnl_pips * pip_usd * (t.lot_size or 0.01), 2)
        else:
            pnl_pips = pnl_usd = None
        out.append({"trade_id": t.id, "symbol": t.symbol, "current_price": cp,
                    "pnl_pips": round(pnl_pips, 1) if pnl_pips is not None else None,
                    "pnl_usd": pnl_usd})
    return out


@app.get("/api/trades/{trade_id}")
async def get_trade(trade_id: int):
    async with async_session_factory() as s:
        trade = await s.get(Trade, trade_id)
        if not trade:
            raise HTTPException(404, "Trade not found")
        return _trade_to_dict(trade)


@app.post("/api/trades/{trade_id}/close")
async def close_trade(trade_id: int):
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    return await orchestrator.close_trade_manually(trade_id)


@app.get("/api/journal")
async def get_journal(trade_id: int | None = None, limit: int = 50):
    async with async_session_factory() as s:
        q = select(JournalEntry).order_by(desc(JournalEntry.created_at)).limit(limit)
        if trade_id:
            q = q.where(JournalEntry.trade_id == trade_id)
        result = await s.execute(q)
        entries = result.scalars().all()
        return [_journal_to_dict(e) for e in entries]


@app.get("/api/meetings")
async def get_meetings(limit: int = 20):
    async with async_session_factory() as s:
        result = await s.execute(
            select(Meeting).order_by(desc(Meeting.created_at)).limit(limit)
        )
        meetings = result.scalars().all()
        return [_meeting_to_dict(m) for m in meetings]


@app.post("/api/meetings/trigger")
async def trigger_meeting(data: dict):
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    meeting_type = data.get("type", "POST_TRADE")
    asyncio.create_task(orchestrator.run_meeting(meeting_type))
    return {"status": "Meeting scheduled", "type": meeting_type}


@app.get("/api/logs")
async def get_logs(agent: str | None = None, limit: int = 100):
    async with async_session_factory() as s:
        q = select(AgentLog).order_by(desc(AgentLog.timestamp)).limit(limit)
        if agent:
            q = q.where(AgentLog.agent_name == agent.upper())
        result = await s.execute(q)
        logs = result.scalars().all()
        return [_log_to_dict(l) for l in logs]


@app.get("/api/config")
async def get_config_all():
    async with async_session_factory() as s:
        result = await s.execute(select(SystemConfig))
        rows = result.scalars().all()
        return {r.key: r.value for r in rows}


@app.put("/api/config/{key}")
async def update_config(key: str, data: dict):
    value = str(data.get("value", ""))
    async with async_session_factory() as s:
        await set_config(key, value, s)
    return {"key": key, "value": value}


@app.post("/api/config/save_as_default")
async def save_config_as_default():
    """Snapshot all current config values as user defaults for fresh-DB restores."""
    skip = {"system_performance", "_user_defaults"}
    async with async_session_factory() as s:
        result = await s.execute(select(SystemConfig))
        rows = result.scalars().all()
        snapshot = {r.key: r.value for r in rows if r.key not in skip}
        await set_config("_user_defaults", json.dumps(snapshot), s)
    return {"saved": len(snapshot)}


@app.post("/api/analyze")
async def trigger_analysis(data: dict | None = None):
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    symbol = data.get("symbol") if data else None
    asyncio.create_task(orchestrator.trigger_analysis(symbol))
    return {"status": "Analysis triggered", "symbol": symbol or "all pairs"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram webhook updates (alternative to polling)."""
    if not orchestrator or not orchestrator.telegram:
        return {"ok": False}
    update = await request.json()
    asyncio.create_task(orchestrator.telegram.handle_webhook_update(update))
    return {"ok": True}


@app.post("/api/telegram/test")
async def telegram_test():
    if not orchestrator or not orchestrator.telegram:
        raise HTTPException(503, "Telegram bot not configured")
    result = await orchestrator.telegram.send_test()
    return result


@app.post("/api/telegram/webhook/set")
async def telegram_set_webhook(data: dict):
    if not orchestrator or not orchestrator.telegram:
        raise HTTPException(503, "Telegram bot not configured")
    url = data.get("url", "")
    if not url:
        raise HTTPException(400, "url is required")
    result = await orchestrator.telegram.set_webhook(url)
    return result


@app.get("/api/news")
async def get_news(hours: int = 24, symbol: str | None = None):
    if not orchestrator or not orchestrator.news_filter:
        raise HTTPException(503, "System not ready")
    events = await orchestrator.news_filter.upcoming_events(hours_ahead=hours, symbol=symbol)
    return {
        "events": [e.to_dict() for e in events],
        "block_minutes_before": orchestrator.news_filter.block_minutes_before,
        "block_minutes_after":  orchestrator.news_filter.block_minutes_after,
        "count": len(events),
    }


@app.get("/api/chart-data/{symbol}")
async def get_chart_data(symbol: str, timeframe: str = "H1", bars: int = 200):
    """OHLCV + ICT overlays for the chart tab."""
    symbol = symbol.upper()
    bars   = max(50, min(bars, 500))
    valid_tf = {"M1","M5","M15","M30","H1","H4","D1","W1"}
    if timeframe not in valid_tf:
        raise HTTPException(400, f"timeframe must be one of {valid_tf}")

    data = await fetch_ohlcv(symbol, timeframe, bars)

    # Attach active trades for this symbol as overlay levels
    async with async_session_factory() as s:
        result = await s.execute(
            select(Trade).where(Trade.symbol == symbol, Trade.status == "ACTIVE")
        )
        active = result.scalars().all()

    trade_levels = [
        {
            "id":          t.id,
            "direction":   t.direction,
            "entry_price": t.entry_price,
            "stop_loss":   t.stop_loss,
            "take_profit_1": t.take_profit_1,
            "take_profit_2": t.take_profit_2,
            "take_profit_3": t.take_profit_3,
            "ict_setup":   t.ict_setup,
        }
        for t in active
    ]

    return {**data, "active_trades": trade_levels}


@app.post("/api/news/refresh")
async def refresh_news():
    if not orchestrator or not orchestrator.news_filter:
        raise HTTPException(503, "System not ready")
    count = await orchestrator.news_filter.force_refresh()
    return {"status": "refreshed", "event_count": count}


@app.post("/api/backtest/run")
async def backtest_run(data: dict):
    try:
        symbol       = data.get("symbol", "EURUSD").upper()
        timeframe    = data.get("timeframe", "H1")
        strategy     = data.get("strategy", "Mixed")
        bars         = int(data.get("bars", 500))
        risk_percent = float(data.get("risk_percent", 1.0))
        rr_ratio     = float(data.get("rr_ratio", 2.0))
        balance      = float(data.get("initial_balance", 10000.0))
        max_risk_usd    = float(data["max_risk_usd"]) if data.get("max_risk_usd") else None
        enabled_setups  = data.get("enabled_setups") or None  # list or None
        date_from       = data.get("date_from") or None       # ISO date string e.g. "2025-01-01"
        date_to         = data.get("date_to")   or None

        valid_tf = {"M5","M15","M30","H1","H4","D1"}
        valid_st = {"FVG","OrderBlock","Liquidity","Mixed"}
        if timeframe not in valid_tf:
            raise HTTPException(400, f"timeframe must be one of {valid_tf}")
        if strategy not in valid_st:
            raise HTTPException(400, f"strategy must be one of {valid_st}")

        # Read data source config from DB
        async with async_session_factory() as s:
            oanda_key      = await get_config("oanda_api_key", s) or ""
            oanda_practice = (await get_config("oanda_practice", s) or "true") != "false"
            mt5_bridge_url = await get_config("mt5_bridge_url", s) or ""

        # Create DB record
        async with async_session_factory() as s:
            run = BacktestRun(
                symbol=symbol, timeframe=timeframe, strategy=strategy,
                bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
            )
            s.add(run)
            await s.commit()
            await s.refresh(run)
            run_id = run.id

        # Execute in background so the HTTP call returns quickly
        asyncio.create_task(_exec_backtest(
            run_id, symbol, timeframe, strategy, bars,
            risk_percent, rr_ratio, balance, max_risk_usd, enabled_setups,
            oanda_key, oanda_practice, mt5_bridge_url,
            date_from=date_from, date_to=date_to,
        ))
        return {"run_id": run_id, "status": "RUNNING"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("backtest_run failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


async def _maybe_auto_update_cache(run_id, symbol, timeframe, oanda_key, oanda_practice, mt5_bridge_url):
    """If the H1 cache exists but is stale (last bar > 4h old), update it before running the backtest."""
    try:
        from services.ohlcv_cache import get_latest_time
        from datetime import datetime, timezone
        latest = await get_latest_time(symbol, timeframe)
        if not latest:
            return  # No cache → backtester will fall back to API
        dt_latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - dt_latest).total_seconds() / 3600
        if age_hours <= 4:
            return  # Fresh enough
        logger.info("Cache stale (%.1fh old) for %s %s — auto-updating before backtest", age_hours, symbol, timeframe)
        # Signal frontend that we're updating
        async with async_session_factory() as s:
            run = await s.get(BacktestRun, run_id)
            if run:
                run.status = "UPDATING_CACHE"
                await s.commit()
        await _do_update_cache(symbol, timeframe, oanda_key, oanda_practice, mt5_bridge_url)
    except Exception as exc:
        logger.warning("Auto-update cache skipped (%s) — continuing with existing data", exc)


async def _exec_backtest(
    run_id, symbol, timeframe, strategy, bars,
    risk_percent, rr_ratio, balance, max_risk_usd=None, enabled_setups=None,
    oanda_api_key="", oanda_practice=True, mt5_bridge_url="",
    date_from=None, date_to=None,
):
    try:
        # Auto-refresh cache if stale before running
        await _maybe_auto_update_cache(run_id, symbol, timeframe, oanda_api_key, oanda_practice, mt5_bridge_url)
        result = await run_backtest(
            symbol=symbol, timeframe=timeframe, strategy=strategy,
            bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
            initial_balance=balance, max_risk_usd=max_risk_usd,
            enabled_setups=enabled_setups, date_from=date_from, date_to=date_to,
            oanda_api_key=oanda_api_key, oanda_practice=oanda_practice,
            mt5_bridge_url=mt5_bridge_url,
        )
        async with async_session_factory() as s:
            run = await s.get(BacktestRun, run_id)
            if run:
                run.status        = "DONE"
                run.total_trades  = result.total_trades
                run.wins          = result.wins
                run.losses        = result.losses
                run.win_rate      = result.win_rate
                run.total_pips    = result.total_pips
                run.total_return     = result.total_return
                run.total_pnl_usd    = result.total_pnl_usd
                run.max_drawdown     = result.max_drawdown
                run.max_drawdown_usd = result.max_drawdown_usd
                run.profit_factor = result.profit_factor if result.profit_factor != float("inf") else 999.0
                run.avg_rr        = result.avg_rr
                run.sharpe        = result.sharpe
                run.trades_json   = json.dumps([t.__dict__ for t in result.trades], default=str)
                run.equity_json   = json.dumps(result.equity)
                run.data_warning  = result.data_warning or None
                run.completed_at  = datetime.utcnow()
                await s.commit()
    except Exception as exc:
        logger.error("Backtest %s failed: %s", run_id, exc, exc_info=True)
        async with async_session_factory() as s:
            run = await s.get(BacktestRun, run_id)
            if run:
                run.status = "FAILED"
                run.error  = str(exc)
                await s.commit()


@app.get("/api/paper/status")
async def paper_status():
    if not orchestrator or not orchestrator.paper_account:
        raise HTTPException(503, "System not ready")
    paper_on = (await orchestrator._get_config_value("paper_mode")) == "true"
    return {
        **orchestrator.paper_account.get_summary(),
        "paper_mode": paper_on,
    }


@app.get("/api/paper/positions")
async def paper_positions():
    if not orchestrator or not orchestrator.paper_account:
        raise HTTPException(503, "System not ready")
    return orchestrator.paper_account.get_positions()


@app.get("/api/paper/trades")
async def paper_trades(limit: int = 50):
    async with async_session_factory() as s:
        result = await s.execute(
            select(Trade)
            .where(Trade.is_paper == True)  # noqa: E712
            .order_by(desc(Trade.created_at))
            .limit(limit)
        )
        trades = result.scalars().all()
    return [_trade_to_dict(t) for t in trades]


@app.post("/api/paper/enable")
async def paper_enable(data: dict | None = None):
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    balance = float((data or {}).get("balance", 10000.0))
    await orchestrator.enable_paper_mode(balance)
    return {"status": "paper_mode enabled", "balance": balance}


@app.post("/api/paper/disable")
async def paper_disable():
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    await orchestrator.disable_paper_mode()
    return {"status": "paper_mode disabled"}


@app.post("/api/paper/reset")
async def paper_reset(data: dict | None = None):
    if not orchestrator or not orchestrator.paper_account:
        raise HTTPException(503, "System not ready")
    balance = float((data or {}).get("balance", 10000.0))
    await orchestrator.paper_account.reset(balance)
    await orchestrator.enable_paper_mode(balance)
    return {"status": "reset", "balance": balance}


@app.post("/api/reset-all")
async def reset_all(data: dict | None = None):
    """Full reset: delete all trades, agent logs, journal entries, meetings and reset performance stats."""
    balance = float((data or {}).get("balance", 5000.0))
    async with async_session_factory() as s:
        await s.execute(delete(AgentLog))
        await s.execute(delete(JournalEntry))
        await s.execute(delete(Meeting))
        await s.execute(delete(Trade))
        await set_config("system_performance", "{}", s)
        await s.commit()
    # Reset paper account in memory
    if orchestrator and orchestrator.paper_account:
        await orchestrator.paper_account.reset(balance)
    await orchestrator.broadcast({"type": "full_reset", "balance": balance})
    return {"status": "reset", "balance": balance}


@app.post("/api/paper/close/{trade_id}")
async def paper_close(trade_id: int):
    if not orchestrator or not orchestrator.paper_account:
        raise HTTPException(503, "System not ready")
    result = orchestrator.paper_account.close_position(trade_id)
    if result.get("success"):
        # Update DB
        async with async_session_factory() as s:
            t = await s.get(Trade, trade_id)
            if t:
                close_price = result.get("close_price", t.entry_price)
                t.status      = "CLOSED"
                t.close_price = close_price
                t.close_time  = datetime.utcnow()
                t.pnl_pips    = result.get("pnl_pips", 0)
                t.pnl_usd     = result.get("pnl_usd", 0)
                t.result      = "WIN" if (t.pnl_usd or 0) > 0 else "LOSS"
                await s.commit()
    return result


@app.get("/api/mt5/health")
async def mt5_health():
    """Check if the MT5 bridge is reachable."""
    async with async_session_factory() as s:
        bridge_url = await get_config("mt5_bridge_url", s) or ""
    if not bridge_url:
        return {"status": "not_configured"}
    from services.mt5_data import check_bridge
    return await check_bridge(bridge_url)


@app.get("/api/backtest")
async def list_backtests(limit: int = 20):
    async with async_session_factory() as s:
        result = await s.execute(
            select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(limit)
        )
        runs = result.scalars().all()
    return [_bt_to_dict(r) for r in runs]


@app.get("/api/backtest/{run_id}")
async def get_backtest(run_id: int):
    async with async_session_factory() as s:
        run = await s.get(BacktestRun, run_id)
    if not run:
        raise HTTPException(404, "Backtest run not found")
    d = _bt_to_dict(run)
    if run.trades_json:
        try:
            d["trades"] = json.loads(run.trades_json)
        except Exception:
            d["trades"] = []
    if run.equity_json:
        try:
            d["equity"] = json.loads(run.equity_json)
        except Exception:
            d["equity"] = []
    return d


def _bt_to_dict(r: BacktestRun) -> dict:
    return {
        "id":           r.id,
        "symbol":       r.symbol,
        "timeframe":    r.timeframe,
        "strategy":     r.strategy,
        "bars":         r.bars,
        "risk_percent": r.risk_percent,
        "rr_ratio":     r.rr_ratio,
        "status":       r.status,
        "total_trades": r.total_trades,
        "wins":         r.wins,
        "losses":       r.losses,
        "win_rate":     r.win_rate,
        "total_pips":   r.total_pips,
        "total_return":     r.total_return,
        "total_pnl_usd":    r.total_pnl_usd,
        "max_drawdown":     r.max_drawdown,
        "max_drawdown_usd": r.max_drawdown_usd,
        "profit_factor":r.profit_factor,
        "avg_rr":       r.avg_rr,
        "sharpe":       r.sharpe,
        "error":        r.error,
        "data_warning": r.data_warning,
        "created_at":   r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


# ── OHLCV Cache endpoints ──────────────────────────────────────────────────────

@app.get("/api/ohlcv/status")
async def ohlcv_status():
    """Summary of what's in the local OHLCV cache."""
    from services.ohlcv_cache import get_cache_info
    info = await get_cache_info()
    for row in info:
        key = f"{row['symbol']}_{row['timeframe']}"
        if key in _build_tasks:
            row["build"] = _build_tasks[key]
    building = {k: v for k, v in _build_tasks.items() if v["status"] in ("running", "updating")}
    return {"cached": info, "building": building}


@app.get("/api/ohlcv/progress/{key}")
async def ohlcv_progress(key: str):
    """Poll build/update progress for a symbol_timeframe key."""
    return _build_tasks.get(key, {"status": "idle"})


@app.post("/api/ohlcv/build")
async def ohlcv_build(data: dict):
    """Start building the cache for a symbol/timeframe/bar-count."""
    symbol    = data.get("symbol", "EURUSD").upper()
    timeframe = data.get("timeframe", "H1")
    n_bars    = int(data.get("bars", 5000))
    key       = f"{symbol}_{timeframe}"

    if _build_tasks.get(key, {}).get("status") in ("running", "updating"):
        return {"status": "already_running", "key": key}

    async with async_session_factory() as s:
        oanda_key      = await get_config("oanda_api_key", s) or ""
        oanda_practice = (await get_config("oanda_practice", s) or "true") != "false"
        mt5_bridge_url = await get_config("mt5_bridge_url", s) or ""

    asyncio.create_task(_do_build_cache(symbol, timeframe, n_bars, oanda_key, oanda_practice, mt5_bridge_url))
    return {"status": "started", "key": key}


@app.post("/api/ohlcv/update")
async def ohlcv_update(data: dict):
    """Fetch bars newer than the latest cached timestamp."""
    symbol    = data.get("symbol", "EURUSD").upper()
    timeframe = data.get("timeframe", "H1")
    key       = f"{symbol}_{timeframe}"

    if _build_tasks.get(key, {}).get("status") in ("running", "updating"):
        return {"status": "already_running", "key": key}

    async with async_session_factory() as s:
        oanda_key      = await get_config("oanda_api_key", s) or ""
        oanda_practice = (await get_config("oanda_practice", s) or "true") != "false"
        mt5_bridge_url = await get_config("mt5_bridge_url", s) or ""

    asyncio.create_task(_do_update_cache(symbol, timeframe, oanda_key, oanda_practice, mt5_bridge_url))
    return {"status": "started", "key": key}


@app.delete("/api/ohlcv/clear")
async def ohlcv_clear(data: dict):
    """Delete cached bars for a symbol/timeframe (or all if empty)."""
    symbol    = (data.get("symbol") or "").upper()
    timeframe = data.get("timeframe") or ""
    from sqlalchemy import delete as _del
    async with async_session_factory() as s:
        q = _del(OhlcvBar)
        if symbol:    q = q.where(OhlcvBar.symbol    == symbol)
        if timeframe: q = q.where(OhlcvBar.timeframe == timeframe)
        result = await s.execute(q)
        await s.commit()
    key = f"{symbol}_{timeframe}" if symbol and timeframe else None
    if key and key in _build_tasks:
        del _build_tasks[key]
    return {"deleted": result.rowcount}


# ── Cache background workers ───────────────────────────────────────────────────

async def _do_build_cache(symbol, timeframe, n_bars, oanda_key, oanda_practice, mt5_bridge_url):
    key = f"{symbol}_{timeframe}"
    _build_tasks[key] = {"done": 0, "total": n_bars, "status": "running", "error": None, "inserted": 0}
    try:
        if mt5_bridge_url:
            from services.mt5_data import fetch_ohlcv as _fetch
            raw     = await _fetch(symbol, timeframe, n_bars, bridge_url=mt5_bridge_url)
            candles = raw.get("candles", [])
        else:
            from services.oanda_data import OandaClient
            client  = OandaClient(oanda_key, oanda_practice)
            candles = await client.get_candles_chunked(symbol, timeframe, n_bars)

        if not candles:
            raise RuntimeError("No candles returned from data source")

        _build_tasks[key]["total"] = len(candles)
        from services.ohlcv_cache import upsert_candles
        BATCH = 500
        inserted = 0
        for i in range(0, len(candles), BATCH):
            n = await upsert_candles(symbol, timeframe, candles[i : i + BATCH])
            inserted += n
            _build_tasks[key]["done"] = min(i + BATCH, len(candles))
            _build_tasks[key]["inserted"] = inserted

        _build_tasks[key].update({"status": "done", "done": len(candles), "inserted": inserted})
        logger.info("Cache built: %s %s — %d bars fetched, %d new", symbol, timeframe, len(candles), inserted)

        # Also cache M1 data so backtests never need to call the API for timing data
        if timeframe != "M1" and candles:
            # Pre-register M1 task NOW so the frontend finds "running" immediately
            # (asyncio.create_task is non-deterministic and might not start before the next frontend poll)
            key_m1 = f"{symbol}_M1"
            _build_tasks[key_m1] = {"done": 0, "total": 0, "status": "running", "error": None, "inserted": 0}
            asyncio.create_task(_build_m1_cache(symbol, candles, oanda_key, oanda_practice, mt5_bridge_url))
    except Exception as exc:
        logger.error("Cache build failed %s %s: %s", symbol, timeframe, exc, exc_info=True)
        _build_tasks[key].update({"status": "error", "error": str(exc)})


async def _do_update_cache(symbol, timeframe, oanda_key, oanda_practice, mt5_bridge_url):
    key = f"{symbol}_{timeframe}"
    _build_tasks[key] = {"done": 0, "total": 0, "status": "updating", "error": None, "inserted": 0}
    try:
        from services.ohlcv_cache import get_latest_time, upsert_candles
        latest = await get_latest_time(symbol, timeframe)

        if not latest:
            # Nothing cached yet → full build with 2000-bar default
            await _do_build_cache(symbol, timeframe, 2000, oanda_key, oanda_practice, mt5_bridge_url)
            return

        from datetime import datetime, timezone, timedelta
        dt_from = datetime.fromisoformat(latest.replace("Z", "+00:00")) + timedelta(minutes=1)
        dt_to   = datetime.now(timezone.utc)

        if mt5_bridge_url:
            from services.mt5_data import fetch_ohlcv as _fetch
            raw     = await _fetch(symbol, timeframe, 500, bridge_url=mt5_bridge_url)
            candles = [c for c in raw.get("candles", []) if c["time"] > latest]
        else:
            from services.oanda_data import OandaClient
            client  = OandaClient(oanda_key, oanda_practice)
            candles = await client.get_candles(symbol, timeframe, from_time=dt_from, to_time=dt_to)

        _build_tasks[key]["total"] = len(candles)
        inserted = await upsert_candles(symbol, timeframe, candles) if candles else 0
        _build_tasks[key].update({"status": "done", "done": len(candles), "inserted": inserted})
        logger.info("Cache updated: %s %s — %d new bars", symbol, timeframe, inserted)

        # Update M1 cache too (only new bars since latest M1)
        if timeframe != "M1" and candles:
            asyncio.create_task(_build_m1_cache(symbol, candles, oanda_key, oanda_practice, mt5_bridge_url))
    except Exception as exc:
        logger.error("Cache update failed %s %s: %s", symbol, timeframe, exc, exc_info=True)
        _build_tasks[key].update({"status": "error", "error": str(exc)})


async def _build_m1_cache(symbol, h1_candles, oanda_key, oanda_practice, mt5_bridge_url):
    """Fetch and cache M1 data for the date range covered by the given H1 candles."""
    key_m1 = f"{symbol}_M1"
    _build_tasks[key_m1] = {"done": 0, "total": 0, "status": "running", "error": None, "inserted": 0}
    try:
        from datetime import datetime, timedelta
        from services.ohlcv_cache import upsert_candles, get_latest_time

        first_t = h1_candles[0]["time"]
        last_t  = h1_candles[-1]["time"]

        # Skip M1 bars we already have
        latest_m1 = await get_latest_time(symbol, "M1")

        def _dt(s):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))

        first_dt = _dt(first_t)
        if latest_m1 and _dt(latest_m1) >= first_dt:
            first_dt = _dt(latest_m1) + timedelta(minutes=1)

        last_dt = _dt(last_t) + timedelta(hours=1)

        if first_dt >= last_dt:
            _build_tasks[key_m1].update({"status": "done", "done": 0, "total": 0})
            return

        if mt5_bridge_url:
            from services.mt5_data import fetch_m1_for_period as _m1_fetch
            m1_list = await _m1_fetch(symbol, first_dt, last_dt, bridge_url=mt5_bridge_url)
        else:
            from services.oanda_data import fetch_m1_for_period as _m1_fetch
            m1_list = await _m1_fetch(symbol, first_dt, last_dt,
                                      api_key=oanda_key, practice=oanda_practice)

        _build_tasks[key_m1]["total"] = len(m1_list) if m1_list else 0
        if m1_list:
            n = await upsert_candles(symbol, "M1", m1_list)
            _build_tasks[key_m1].update({"status": "done", "done": len(m1_list), "inserted": n})
            logger.info("M1 cache built: %s — %d bars, %d new", symbol, len(m1_list), n)
        else:
            _build_tasks[key_m1].update({"status": "done", "done": 0})
    except Exception as exc:
        logger.warning("M1 cache build failed for %s: %s", symbol, exc)
        _build_tasks[key_m1].update({"status": "error", "error": str(exc)})


@app.get("/api/analytics")
async def get_analytics():
    """Full analytics report — equity curve, drawdown, breakdowns, stats."""
    return await compute_analytics()


@app.get("/api/performance")
async def get_performance():
    async with async_session_factory() as s:
        perf_raw = await get_config("system_performance", s)
        perf = json.loads(perf_raw or "{}")

        # Compute per-setup stats
        result = await s.execute(select(Trade).where(Trade.status == "CLOSED"))
        closed = result.scalars().all()

        setups: dict = {}
        for t in closed:
            setup = t.ict_setup or "Unknown"
            if setup not in setups:
                setups[setup] = {"total": 0, "wins": 0, "losses": 0, "total_pips": 0}
            setups[setup]["total"] += 1
            if t.result == "WIN":
                setups[setup]["wins"] += 1
            elif t.result == "LOSS":
                setups[setup]["losses"] += 1
            setups[setup]["total_pips"] += t.pnl_pips or 0

        for k, v in setups.items():
            v["win_rate"] = round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0

        return {**perf, "by_setup": setups, "total_closed": len(closed)}


# ------------------------------------------------------------------ #
#  Serializers
# ------------------------------------------------------------------ #
def _trade_to_dict(t: Trade) -> dict:
    return {
        "id": t.id, "symbol": t.symbol, "direction": t.direction,
        "status": t.status, "entry_price": t.entry_price, "stop_loss": t.stop_loss,
        "take_profit_1": t.take_profit_1, "take_profit_2": t.take_profit_2,
        "take_profit_3": t.take_profit_3, "lot_size": t.lot_size,
        "risk_percent": t.risk_percent, "rr_ratio": t.rr_ratio,
        "ict_setup": t.ict_setup, "mt5_ticket": t.mt5_ticket,
        "open_time": t.open_time.isoformat() if t.open_time else None,
        "close_time": t.close_time.isoformat() if t.close_time else None,
        "close_price": t.close_price, "pnl_pips": t.pnl_pips, "pnl_usd": t.pnl_usd,
        "result": t.result, "trailing_sl_updates": t.trailing_sl_updates,
    }


def _journal_to_dict(e: JournalEntry) -> dict:
    return {
        "id": e.id, "trade_id": e.trade_id, "meeting_id": e.meeting_id,
        "entry_type": e.entry_type, "content": e.content,
        "metrics": e.metrics,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _meeting_to_dict(m: Meeting) -> dict:
    return {
        "id": m.id, "meeting_type": m.meeting_type, "trigger": m.trigger,
        "participants": m.participants, "summary": m.summary,
        "conclusions": m.conclusions, "improvements": m.improvements,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
    }


def _log_to_dict(l: AgentLog) -> dict:
    return {
        "id": l.id, "trade_id": l.trade_id, "agent_name": l.agent_name,
        "action": l.action, "message": l.message,
        "timestamp": l.timestamp.isoformat() if l.timestamp else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
    )
