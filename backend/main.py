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
import os
import shutil
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
    BacktestRun, OhlcvBar, StrategyMemory, MT5Account,
)
from orchestrator import Orchestrator
from services.forex_data import fetch_ohlcv
from services.backtester import run_backtest
from services.analytics import compute_analytics

_log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(_log_dir, "tradewizard.log"), encoding="utf-8"),
    ],
)
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
_bridge_watchdog_thread = None
_bridge_watchdog_stop = False


def _spawn_bridge():
    """Spawn (or respawn) the MT5 bridge subprocess."""
    global _bridge_proc
    import subprocess
    bridge_script = os.path.join(os.path.dirname(__file__), "services", "mt5_bridge_server.py")
    _bridge_log = open(os.path.join(_log_dir, "mt5_bridge.log"), "a", encoding="utf-8")
    _bridge_proc = subprocess.Popen(
        [sys.executable, bridge_script],
        stdout=subprocess.DEVNULL,
        stderr=_bridge_log,
    )
    logger.info("MT5 bridge subprocess started (PID %d)", _bridge_proc.pid)


def _bridge_watchdog_loop():
    """Respawn the bridge if it exits. The bridge commits suicide (os._exit 1)
    when its IPC pipe is wedged beyond recovery (4 failed order_send retries)."""
    import time
    while not _bridge_watchdog_stop:
        time.sleep(3)
        if _bridge_proc is not None and _bridge_proc.poll() is not None:
            code = _bridge_proc.returncode
            logger.warning("MT5 bridge exited with code %s — respawning", code)
            try:
                _spawn_bridge()
                time.sleep(3)
                from services.mt5_direct import get_mt5_direct
                mt5 = get_mt5_direct()
                mt5.connected = False  # force reconnect on next call
                mt5.connect()
            except Exception as exc:
                logger.error("Bridge respawn failed: %s", exc)


def _start_mt5_direct():
    """Start the MT5 bridge subprocess, then connect the client, then arm watchdog.
    In lab mode the bridge is NOT started — lab uses the production bridge on
    port 5555 (shared, read-only) and operates in paper mode."""
    global _bridge_watchdog_thread
    import time, threading
    import os as _os
    if _os.getenv("SYSTEM_MODE", "production").lower() == "lab":
        logger.info("Lab mode: skipping bridge spawn, using production bridge read-only")
        try:
            from services.mt5_direct import get_mt5_direct
            mt5 = get_mt5_direct()
            mt5.connect()
        except Exception:
            logger.warning("Lab: could not connect to production bridge (non-fatal)")
        return
    try:
        _spawn_bridge()
        # Wait for bridge to be ready
        time.sleep(3)
        from services.mt5_direct import get_mt5_direct
        mt5 = get_mt5_direct()
        if mt5.connect():
            logger.info("MT5 bridge connection established")
        else:
            logger.warning("MT5 bridge not responding yet — will retry on first trade")
        # Arm watchdog to respawn on exit
        _bridge_watchdog_thread = threading.Thread(target=_bridge_watchdog_loop, daemon=True)
        _bridge_watchdog_thread.start()
    except Exception as exc:
        logger.warning("Could not start MT5 bridge: %s", exc)


_SETTINGS_BACKUP = os.path.join(os.path.dirname(__file__), "..", "settings_backup.json")


async def _restore_settings_from_backup():
    """If DB settings are missing/default, restore from backup file or .env."""
    backup_path = _SETTINGS_BACKUP
    backup_data = {}
    if os.path.exists(backup_path):
        try:
            with open(backup_path, "r") as f:
                backup_data = json.load(f)
            logger.info("Settings backup found with %d keys", len(backup_data))
        except Exception:
            pass

    async with async_session_factory() as s:
        # Restore MT5 credentials: .env takes priority, then backup
        env_fallbacks = {
            "mt5_login":      os.getenv("MT5_LOGIN", ""),
            "mt5_password":   os.getenv("MT5_PASSWORD", ""),
            "mt5_server":     os.getenv("MT5_SERVER", ""),
            "mt5_bridge_url": os.getenv("MT5_BRIDGE_URL", "http://localhost:5002"),
        }
        for key, env_val in env_fallbacks.items():
            current = await get_config(key, s)
            if not current or current.strip() == "":
                # Try backup first, then env
                restore_val = backup_data.get(key) or env_val
                if restore_val:
                    await set_config(key, restore_val, s)
                    logger.info("Restored setting '%s' from %s",
                                key, "backup" if backup_data.get(key) else ".env")

        # Restore paper_mode from backup if DB has default 'true' but backup says 'false'
        paper_val = await get_config("paper_mode", s)
        if paper_val == "true" and backup_data.get("paper_mode") == "false":
            await set_config("paper_mode", "false", s)
            logger.info("Restored paper_mode=false from backup")

        # Restore other important settings from backup
        restore_keys = [
            "risk_percent", "rr_ratio", "max_open_trades", "account_balance",
            "max_risk_usd", "enabled_pairs", "analysis_interval", "kill_zones",
            "ict_strategies", "min_sl_pips", "model_mode",
            "news_block_minutes_before", "news_block_minutes_after",
        ]
        for key in restore_keys:
            current = await get_config(key, s)
            backup_val = backup_data.get(key)
            if backup_val and current != backup_val:
                # Only restore if the DB has the default value (meaning it was reset)
                # We check by comparing with known defaults
                pass  # Don't auto-overwrite — backup is there for manual recovery

        await s.commit()


async def _save_settings_backup():
    """Save all current settings to a JSON backup file."""
    try:
        async with async_session_factory() as s:
            result = await s.execute(select(SystemConfig))
            rows = result.scalars().all()
            data = {r.key: r.value for r in rows}
        with open(_SETTINGS_BACKUP, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Settings backup saved (%d keys)", len(data))
    except Exception as exc:
        logger.warning("Failed to save settings backup: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    await init_db()

    # Restore settings from backup/.env if DB was reset
    await _restore_settings_from_backup()

    # Set default MT5 bridge URL if not already configured
    async with async_session_factory() as s:
        existing = await get_config("mt5_bridge_url", s)
        if not existing:
            await set_config("mt5_bridge_url", "http://localhost:5002", s)
            await s.commit()
        mt5_login    = await get_config("mt5_login",    s) or ""
        mt5_password = await get_config("mt5_password", s) or ""
        mt5_server   = await get_config("mt5_server",   s) or ""
    # Pass credentials to bridge via env vars
    if mt5_login:
        os.environ.setdefault("MT5_LOGIN",    mt5_login)
        os.environ.setdefault("MT5_PASSWORD", mt5_password)
        os.environ.setdefault("MT5_SERVER",   mt5_server)
    # MT5 terminal path (for multi-terminal setup)
    async with async_session_factory() as s:
        mt5_path = await get_config("mt5_path", s) or os.getenv("MT5_PATH", "")
        if mt5_path:
            os.environ["MT5_PATH"] = mt5_path
    _start_mt5_direct()
    orchestrator = Orchestrator(broadcast_fn=manager.broadcast)
    await orchestrator.start()
    app.state.start_time = datetime.utcnow()

    # Save settings backup after successful startup
    await _save_settings_backup()

    logger.info("TradeWizard system started ✅")
    yield

    # Save settings backup before shutdown
    await _save_settings_backup()

    if orchestrator:
        await orchestrator.stop()
    # Stop MT5 bridge subprocess
    try:
        from services.mt5_direct import get_mt5_direct
        get_mt5_direct().disconnect()
    except Exception:
        pass
    # Disarm watchdog before terminating the bridge so it doesn't try to respawn
    global _bridge_watchdog_stop
    _bridge_watchdog_stop = True
    if _bridge_proc and _bridge_proc.poll() is None:
        try:
            _bridge_proc.terminate()
            _bridge_proc.wait(timeout=5)
            logger.info("MT5 bridge subprocess stopped")
        except Exception:
            _bridge_proc.kill()
    logger.info("MT5 disconnected")
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

    @app.get("/compare")
    async def compare_page(response: Response):
        """Side-by-side dashboard comparing Production (8000) vs Lab (8001)."""
        full = os.path.join(frontend_dir, "compare.html")
        if not os.path.exists(full):
            raise HTTPException(404, "compare.html missing")
        response.headers["Cache-Control"] = "no-store"
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
    elif cmd == "meeting_message":
        text = msg.get("message", "").strip()
        if text and orchestrator and orchestrator._active_meeting:
            orchestrator.send_meeting_message(text)
    elif cmd == "meeting_approve":
        if orchestrator and orchestrator._active_meeting:
            orchestrator.approve_meeting_close()
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


@app.get("/api/health")
async def health_check():
    """Comprehensive health check for watchdog and monitoring."""
    import psutil
    now = datetime.utcnow()
    start = getattr(app.state, "start_time", now)
    uptime = (now - start).total_seconds()

    # MT5 bridge status
    mt5_ok = False
    worker_ok = False
    try:
        from services.mt5_direct import get_mt5_direct
        _mt5 = get_mt5_direct()
        h = _mt5.health()
        mt5_ok = h.get("connected", False)
        # In lab mode there's no local bridge subprocess — worker healthiness
        # is proven by a reachable shared bridge instead.
        if os.environ.get("SYSTEM_MODE", "production").lower() == "lab":
            worker_ok = mt5_ok
        else:
            worker_ok = _bridge_proc is not None and _bridge_proc.poll() is None
    except Exception:
        pass

    # Last analysis time
    last_analysis = None
    try:
        async with async_session_factory() as s:
            from sqlalchemy import desc as _desc
            result = await s.execute(
                select(AgentLog).where(AgentLog.action == "ANALYSIS")
                .order_by(_desc(AgentLog.timestamp)).limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                last_analysis = row.timestamp.isoformat()
    except Exception:
        pass

    # Open trades count
    open_trades = 0
    try:
        async with async_session_factory() as s:
            result = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
            open_trades = len(result.scalars().all())
    except Exception:
        pass

    # System resources
    mem = psutil.Process().memory_info()
    disk = shutil.disk_usage(os.path.dirname(__file__))

    # Determine overall status
    status = "healthy"
    if not orchestrator or not orchestrator._running:
        status = "critical"
    elif not mt5_ok:
        status = "degraded"

    return {
        "status": status,
        "uptime_seconds": int(uptime),
        "backend_running": bool(orchestrator and orchestrator._running),
        "mt5_connected": mt5_ok,
        "mt5_worker": worker_ok,
        "last_analysis": last_analysis,
        "open_trades": open_trades,
        "memory_mb": round(mem.rss / 1024 / 1024, 1),
        "disk_free_gb": round(disk.free / 1024**3, 1),
        "active_meeting": bool(orchestrator and orchestrator._active_meeting),
        "timestamp": now.isoformat(),
    }


@app.get("/api/status")
async def get_status():
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    return await orchestrator.get_status()


@app.get("/api/trades")
async def list_trades(status: str | None = None, limit: int = 50, include_archived: bool = False):
    async with async_session_factory() as s:
        q = select(Trade).order_by(desc(Trade.created_at)).limit(limit)
        if status:
            q = q.where(Trade.status == status.upper())
        if not include_archived:
            q = q.where((Trade.archived == False) | (Trade.archived == None))
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

    # Fetch prices concurrently, one per unique symbol
    symbols = list({t.symbol for t in active})
    async def _price(sym):
        try:
            data = await fetch_ohlcv(sym, "H1", 2)
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


@app.post("/api/trades/{trade_id}/lock-profit")
async def lock_profit(trade_id: int):
    """Move SL to entry + 3 pips to lock in profit."""
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    return await orchestrator.lock_profit(trade_id)


@app.post("/api/trades/{trade_id}/modify-tp")
async def modify_tp(trade_id: int, data: dict):
    """Update TP1/TP2/TP3 for an active trade."""
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    return await orchestrator.modify_tps(
        trade_id,
        tp1=data.get("tp1"),
        tp2=data.get("tp2"),
        tp3=data.get("tp3"),
    )


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


@app.post("/api/meetings/emergency")
async def trigger_emergency_meeting(data: dict):
    """User-convened interactive emergency meeting."""
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    topic = data.get("topic", "").strip()
    if not topic:
        raise HTTPException(400, "Topic is required")
    if orchestrator._active_meeting:
        raise HTTPException(409, "A meeting is already in progress")
    asyncio.create_task(orchestrator.start_interactive_meeting(topic))
    return {"status": "Interactive emergency meeting started", "topic": topic}


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


@app.get("/api/debug")
async def debug_info(limit: int = 20):
    """Full diagnostic info for remote debugging — recent logs, rejections, config, trades."""
    result = {}
    async with async_session_factory() as s:
        # Recent agent logs
        logs = await s.execute(
            select(AgentLog).order_by(desc(AgentLog.timestamp)).limit(limit)
        )
        result["recent_logs"] = [
            {"time": str(l.timestamp)[:19], "agent": l.agent_name, "action": l.action,
             "message": (l.message or "")[:300], "data_preview": (l.data or "")[:500]}
            for l in logs.scalars().all()
        ]

        # Recent rejections
        rejections = await s.execute(
            select(AgentLog).where(AgentLog.action.in_(["REJECTED", "ERROR"]))
            .order_by(desc(AgentLog.timestamp)).limit(10)
        )
        result["rejections"] = [
            {"time": str(r.timestamp)[:19], "agent": r.agent_name, "action": r.action,
             "message": (r.message or "")[:500]}
            for r in rejections.scalars().all()
        ]

        # Active trades
        trades = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
        result["active_trades"] = [
            {"id": t.id, "symbol": t.symbol, "direction": t.direction,
             "entry": t.entry_price, "sl": t.stop_loss, "tp1": t.take_profit_1,
             "lot": t.lot_size, "ticket": t.mt5_ticket, "is_paper": t.is_paper,
             "open_time": str(t.open_time)[:19]}
            for t in trades.scalars().all()
        ]

        # Key config values
        config_keys = ["paper_mode", "enabled_pairs", "min_sl_pips", "rr_ratio",
                       "max_open_trades", "kill_zones", "mt5_bridge_url", "model_mode",
                       "account_balance", "max_risk_usd"]
        config = {}
        for key in config_keys:
            config[key] = await get_config(key, s)
        result["config"] = config

        # Last RM evaluation detail
        rm_log = await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "RM")
            .order_by(desc(AgentLog.timestamp)).limit(1)
        )
        rm_row = rm_log.scalar_one_or_none()
        if rm_row and rm_row.data:
            try:
                rm_data = json.loads(rm_row.data)
                result["last_rm"] = {
                    "symbol": (rm_row.message or "")[:50],
                    "approved": rm_data.get("approved"),
                    "rejection_reason": rm_data.get("rejection_reason", "")[:300],
                    "recommendation": rm_data.get("recommendation"),
                    "sl_pips": rm_data.get("position_size", {}).get("sl_pips"),
                    "tp1_pips": rm_data.get("position_size", {}).get("tp1_pips"),
                    "rr_ratio": rm_data.get("position_size", {}).get("rr_ratio"),
                }
            except Exception:
                result["last_rm"] = {"raw": (rm_row.data or "")[:300]}

    return result


@app.put("/api/config/{key}")
async def update_config(key: str, data: dict):
    value = str(data.get("value", ""))
    async with async_session_factory() as s:
        await set_config(key, value, s)
        # Keep paper_balance in sync with account_balance
        if key == "account_balance":
            await set_config("paper_balance", value, s)
    # Auto-save settings backup on every config change
    asyncio.create_task(_save_settings_backup())
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


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Receive incoming WhatsApp messages from Twilio webhook."""
    if not orchestrator or not orchestrator._wa:
        return {"ok": False}
    form = await request.form()
    form_data = dict(form)
    asyncio.create_task(orchestrator._wa.handle_webhook(form_data))
    # Twilio expects a TwiML response (empty is fine if we reply via API)
    from fastapi.responses import Response
    return Response(content="<Response></Response>", media_type="application/xml")


@app.post("/api/whatsapp/test")
async def whatsapp_test():
    if not orchestrator or not orchestrator._wa:
        raise HTTPException(503, "WhatsApp bot not configured")
    result = await orchestrator._wa.send_test()
    return result


@app.get("/api/news")
async def get_news(hours: int = 24, symbol: str | None = None):
    if not orchestrator or not orchestrator.news_filter:
        raise HTTPException(503, "System not ready")
    events = await orchestrator.news_filter.upcoming_events(hours_ahead=hours, symbol=symbol)
    async with async_session_factory() as s:
        block_enabled = await get_config("news_block_enabled", s)
    return {
        "events": [e.to_dict() for e in events],
        "block_enabled": (block_enabled or "true").lower() != "false",
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
    # Only pass balance if explicitly provided — avoids resetting current paper balance
    balance_param = (data or {}).get("balance")
    balance = float(balance_param) if balance_param else None
    await orchestrator.enable_paper_mode(balance)
    return {"status": "paper_mode enabled"}


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


# ── Backup / Restore Points ───────────────────────────────────────────────────

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")


def _backup_dir() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


async def _create_backup(label: str) -> dict:
    """Snapshot all key tables to a JSON file in backups/. Returns metadata."""
    import json as _json
    ts = datetime.utcnow()
    fname = f"{ts.strftime('%Y%m%d_%H%M%S')}_{label}.json"
    path = os.path.join(_backup_dir(), fname)

    async with async_session_factory() as s:
        trades   = (await s.execute(select(Trade).order_by(Trade.id))).scalars().all()
        journals = (await s.execute(select(JournalEntry).order_by(JournalEntry.id))).scalars().all()
        meetings = (await s.execute(select(Meeting).order_by(Meeting.id))).scalars().all()
        mem_rows = (await s.execute(select(StrategyMemory).order_by(StrategyMemory.id))).scalars().all()
        configs  = (await s.execute(select(SystemConfig))).scalars().all()

    def _t(obj):
        return obj.isoformat() if isinstance(obj, datetime) else obj

    def row_to_dict(r):
        return {c.name: _t(getattr(r, c.name)) for c in r.__table__.columns}

    snapshot = {
        "meta":    {"timestamp": ts.isoformat(), "label": label, "file": fname},
        "trades":           [row_to_dict(r) for r in trades],
        "journal_entries":  [row_to_dict(r) for r in journals],
        "meetings":         [row_to_dict(r) for r in meetings],
        "strategy_memory":  [row_to_dict(r) for r in mem_rows],
        "config":           [row_to_dict(r) for r in configs],
    }
    with open(path, "w", encoding="utf-8") as fh:
        _json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    return {
        "file": fname,
        "timestamp": ts.isoformat(),
        "label": label,
        "trades": len(trades),
        "meetings": len(meetings),
        "size_kb": round(os.path.getsize(path) / 1024, 1),
    }


@app.post("/api/backup/create")
async def backup_create(data: dict | None = None):
    label = (data or {}).get("label", "manual")
    meta = await _create_backup(label)
    return meta


@app.get("/api/backup/list")
async def backup_list():
    d = _backup_dir()
    files = sorted([f for f in os.listdir(d) if f.endswith(".json")], reverse=True)
    result = []
    for f in files:
        path = os.path.join(d, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                meta = json.load(fh).get("meta", {})
            result.append({
                "file":      f,
                "timestamp": meta.get("timestamp"),
                "label":     meta.get("label", ""),
                "size_kb":   round(os.path.getsize(path) / 1024, 1),
            })
        except Exception:
            result.append({"file": f, "timestamp": None, "label": "?", "size_kb": 0})
    return result


@app.post("/api/backup/restore/{filename}")
async def backup_restore(filename: str):
    """Restore DB tables from a backup snapshot file."""
    import logging as _log
    _rlog = _log.getLogger("backup_restore")

    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = os.path.join(_backup_dir(), filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Backup not found")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
    except Exception as e:
        raise HTTPException(400, f"Cannot read backup file: {e}")

    def _parse_dt(v):
        if not v:
            return None
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return None

    def _safe_row(model_class, row_dict):
        """Build model kwargs using only columns that exist in the current model."""
        valid_cols = {c.name for c in model_class.__table__.columns}
        dt_suffixes = ("_at", "_time", "started_at", "ended_at", "last_updated")
        return {
            k: (_parse_dt(v) if any(k.endswith(s) for s in dt_suffixes) else v)
            for k, v in row_dict.items()
            if k in valid_cols
        }

    try:
        async with async_session_factory() as s:
            # Clear current data
            await s.execute(delete(AgentLog))
            await s.execute(delete(JournalEntry))
            await s.execute(delete(Meeting))
            await s.execute(delete(Trade))
            await s.execute(delete(StrategyMemory))
            await s.commit()

            for r in snap.get("trades", []):
                s.add(Trade(**_safe_row(Trade, r)))
            await s.flush()

            for r in snap.get("meetings", []):
                s.add(Meeting(**_safe_row(Meeting, r)))
            await s.flush()

            for r in snap.get("journal_entries", []):
                s.add(JournalEntry(**_safe_row(JournalEntry, r)))

            for r in snap.get("strategy_memory", []):
                s.add(StrategyMemory(**_safe_row(StrategyMemory, r)))

            for r in snap.get("config", []):
                result = await s.execute(select(SystemConfig).where(SystemConfig.key == r["key"]))
                cfg = result.scalar_one_or_none()
                if cfg:
                    cfg.value = r["value"]
                else:
                    s.add(SystemConfig(**_safe_row(SystemConfig, r)))

            await s.commit()
    except Exception as e:
        _rlog.exception("Restore failed")
        raise HTTPException(500, f"Restore failed: {e}")

    if orchestrator:
        await orchestrator.broadcast({"type": "full_reset"})

    return {
        "status": "restored",
        "file": filename,
        "trades_restored": len(snap.get("trades", [])),
        "meetings_restored": len(snap.get("meetings", [])),
    }


@app.delete("/api/backup/{filename}")
async def backup_delete(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = os.path.join(_backup_dir(), filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Backup not found")
    os.remove(path)
    return {"deleted": filename}


@app.post("/api/reset-stats")
async def reset_stats():
    """Archive all closed trades so stats start from zero. Trades are preserved and restorable."""
    await _create_backup("reset_stats")
    from sqlalchemy import update as _upd
    async with async_session_factory() as s:
        # Archive all non-active trades (CLOSED, CANCELLED, PROPOSED)
        res = await s.execute(
            _upd(Trade)
            .where(Trade.status != "ACTIVE")
            .where((Trade.archived == False) | (Trade.archived == None))
            .values(archived=True)
        )
        archived_count = res.rowcount
        empty = '{"total_trades":0,"wins":0,"losses":0,"breakeven":0,"win_rate":0,"avg_rr":0}'
        await set_config("system_performance", empty, s)
        await s.execute(delete(AgentLog))
        await s.commit()
    if orchestrator:
        await orchestrator.broadcast({"type": "stats_reset"})
    return {"status": "stats_reset", "archived": archived_count}


@app.post("/api/trades/unarchive")
async def unarchive_trades():
    """Restore all archived trades back to visible state."""
    from sqlalchemy import update as _upd
    async with async_session_factory() as s:
        res = await s.execute(
            _upd(Trade).where(Trade.archived == True).values(archived=False)
        )
        count = res.rowcount
        await s.commit()
    if orchestrator:
        await orchestrator.broadcast({"type": "stats_reset"})
    return {"status": "unarchived", "restored": count}


@app.get("/api/trades/archived-count")
async def archived_count():
    from sqlalchemy import func
    async with async_session_factory() as s:
        cnt = (await s.execute(
            select(func.count()).select_from(Trade).where(Trade.archived == True)
        )).scalar_one()
    return {"count": cnt}


@app.post("/api/reset-all")
async def reset_all(data: dict | None = None):
    """Full reset: delete closed trades, agent logs, journal entries, meetings. Preserves ACTIVE trades."""
    balance = float((data or {}).get("balance", 5000.0))
    await _create_backup("reset_all")
    async with async_session_factory() as s:
        await s.execute(delete(AgentLog))
        await s.execute(delete(JournalEntry))
        await s.execute(delete(Meeting))
        # Only delete non-active trades — preserve open positions
        await s.execute(delete(Trade).where(Trade.status != "ACTIVE"))
        await set_config("system_performance", "{}", s)
        await s.commit()
    # Reset paper account in memory only if no active trades remain
    if orchestrator and orchestrator.paper_account:
        from sqlalchemy import func as _func
        async with async_session_factory() as s:
            active_count = (await s.execute(
                select(_func.count()).select_from(Trade).where(Trade.status == "ACTIVE")
            )).scalar()
        if active_count == 0:
            await orchestrator.paper_account.reset(balance)
    await orchestrator.broadcast({"type": "full_reset", "balance": balance})
    return {"status": "reset", "balance": balance}


@app.get("/api/strategy-memory")
async def get_strategy_memory():
    """Return all StrategyMemory rows for frontend visualization."""
    import json as _json
    async with async_session_factory() as s:
        rows = (await s.execute(
            select(StrategyMemory).order_by(StrategyMemory.setup_type, StrategyMemory.symbol)
        )).scalars().all()
    result = []
    for r in rows:
        total = (r.win_count or 0) + (r.loss_count or 0)
        win_rate = round(r.win_count / total * 100, 1) if total > 0 else None
        result.append({
            "id":               r.id,
            "setup_type":       r.setup_type,
            "symbol":           r.symbol,
            "win_count":        r.win_count or 0,
            "loss_count":       r.loss_count or 0,
            "total_trades":     total,
            "win_rate":         win_rate,
            "total_pnl_usd":    round(r.total_pnl_usd or 0, 2),
            "failure_patterns": _json.loads(r.failure_patterns or "[]"),
            "success_patterns": _json.loads(r.success_patterns or "[]"),
            "lessons":          _json.loads(r.lessons or "[]"),
            "strategy_notes":   r.strategy_notes or "",
            "last_updated":     r.last_updated.isoformat() if r.last_updated else None,
        })
    return result


@app.delete("/api/strategy-memory")
async def clear_strategy_memory():
    """Clear all strategy memory (use after intentional strategy reset)."""
    async with async_session_factory() as s:
        result = await s.execute(delete(StrategyMemory))
        await s.commit()
    return {"deleted": result.rowcount}


@app.get("/api/system-mode")
async def get_system_mode():
    """Tells the frontend which instance it is talking to (production vs lab)."""
    import os as _os
    return {
        "mode": _os.getenv("SYSTEM_MODE", "production").lower(),
        "db_file": "tradewizard_lab.db" if _os.getenv("SYSTEM_MODE", "production").lower() == "lab" else "tradewizard.db",
    }


# ─── Learning Rules API ────────────────────────────────────────────────
from models.database import LearningRule


@app.get("/api/learning-rules")
async def list_learning_rules(status: str | None = None):
    """List learning rules, optionally filtered by status."""
    import json as _json
    async with async_session_factory() as s:
        q = select(LearningRule)
        if status:
            q = q.where(LearningRule.status == status.upper())
        rows = (await s.execute(q.order_by(LearningRule.created_at.desc()))).scalars().all()
    result = []
    for r in rows:
        total_feedback = r.times_correct + r.times_wrong
        accuracy = round(r.times_correct / total_feedback * 100, 1) if total_feedback > 0 else None
        result.append({
            "id":            r.id,
            "rule_type":     r.rule_type,
            "setup_type":    r.setup_type,
            "symbol":        r.symbol,
            "session":       r.session,
            "condition":     _json.loads(r.condition or "{}"),
            "action":        _json.loads(r.action or "{}"),
            "confidence":    r.confidence,
            "sample_size":   r.sample_size,
            "source_type":   r.source_type,
            "source_id":     r.source_id,
            "description":   r.description,
            "status":        r.status,
            "times_applied": r.times_applied,
            "times_correct": r.times_correct,
            "times_wrong":   r.times_wrong,
            "accuracy":      accuracy,
            "created_at":    r.created_at.isoformat() if r.created_at else None,
            "activated_at":  r.activated_at.isoformat() if r.activated_at else None,
            "confirmed_at":  r.confirmed_at.isoformat() if r.confirmed_at else None,
            "deprecated_at": r.deprecated_at.isoformat() if r.deprecated_at else None,
        })
    return result


@app.get("/api/learning-rules/stats")
async def learning_rules_stats():
    """Summary metrics for the learning dashboard."""
    async with async_session_factory() as s:
        rows = (await s.execute(select(LearningRule))).scalars().all()

    from collections import Counter
    status_counts = Counter(r.status for r in rows)
    type_counts = Counter(r.rule_type for r in rows)

    active = [r for r in rows if r.status in ("ACTIVE", "CONFIRMED")]
    total_applications = sum(r.times_applied for r in active)
    total_correct = sum(r.times_correct for r in active)
    total_wrong = sum(r.times_wrong for r in active)
    total_feedback = total_correct + total_wrong
    avg_accuracy = round(total_correct / total_feedback * 100, 1) if total_feedback > 0 else None

    # Top 5 by impact
    top_rules = sorted(active, key=lambda r: r.times_applied, reverse=True)[:5]
    top = [{"id": r.id, "description": r.description, "times_applied": r.times_applied,
            "accuracy": (round(r.times_correct / (r.times_correct + r.times_wrong) * 100, 1)
                         if (r.times_correct + r.times_wrong) > 0 else None)}
           for r in top_rules]

    return {
        "by_status": dict(status_counts),
        "by_type":   dict(type_counts),
        "total_applications": total_applications,
        "avg_accuracy": avg_accuracy,
        "top_rules":  top,
    }


@app.post("/api/learning-rules/{rule_id}/activate")
async def activate_learning_rule(rule_id: int):
    from services.learning_rules import activate_rule
    await activate_rule(rule_id)
    return {"id": rule_id, "status": "ACTIVE"}


@app.post("/api/learning-rules/{rule_id}/deprecate")
async def deprecate_learning_rule(rule_id: int, data: dict | None = None):
    from services.learning_rules import deprecate_rule
    reason = (data or {}).get("reason", "Manual deprecation")
    await deprecate_rule(rule_id, reason)
    return {"id": rule_id, "status": "DEPRECATED"}


@app.post("/api/learning-rules")
async def create_learning_rule(data: dict):
    """Create a manual learning rule. Expected JSON: {rule_type, setup_type, symbol,
    session, condition, action, confidence, description}."""
    from services.learning_rules import ingest_proposed_rules
    ids = await ingest_proposed_rules([data], source_type="MANUAL")
    return {"created_ids": ids}


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
    """Check if MT5 is connected (direct, no bridge)."""
    try:
        from services.mt5_direct import get_mt5_direct
        h = get_mt5_direct().health()
        return {"connected": h.get("connected", False), "status": h.get("status", "unknown")}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


@app.get("/api/mt5/account")
async def mt5_account():
    """Fetch live MT5 account info (direct)."""
    try:
        from services.mt5_direct import get_mt5_direct
        return get_mt5_direct().get_account_info()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/mt5/test-order")
async def mt5_test_order():
    """Test MT5 order_send with 0.01 lot EURUSD (opens and immediately closes)."""
    try:
        import MetaTrader5 as _mt5
        from services.mt5_direct import get_mt5_direct
        m = get_mt5_direct()
        # Fresh init
        _mt5.shutdown()
        kwargs = {}
        if m.path: kwargs["path"] = m.path
        if m.login: kwargs["login"] = m.login
        if m.password: kwargs["password"] = m.password
        if m.server: kwargs["server"] = m.server
        init_ok = _mt5.initialize(**kwargs)
        info = _mt5.account_info()
        tick = _mt5.symbol_info_tick("EURUSD")
        if not tick:
            return {"error": "No tick", "init": init_ok, "account": info.login if info else None}
        # order_check first
        check = _mt5.order_check({
            "action": _mt5.TRADE_ACTION_DEAL, "symbol": "EURUSD",
            "volume": 0.01, "type": _mt5.ORDER_TYPE_BUY, "price": tick.ask,
        })
        check_result = {"retcode": check.retcode, "comment": check.comment} if check else {"error": "None", "last_error": str(_mt5.last_error())}
        # order_send
        r = _mt5.order_send({
            "action": _mt5.TRADE_ACTION_DEAL, "symbol": "EURUSD",
            "volume": 0.01, "type": _mt5.ORDER_TYPE_BUY, "price": tick.ask,
            "deviation": 10, "magic": 99999, "comment": "TW-DIAG",
            "type_time": _mt5.ORDER_TIME_GTC, "type_filling": _mt5.ORDER_FILLING_FOK,
        })
        send_result = {"retcode": r.retcode, "comment": r.comment, "ticket": r.order} if r else {"error": "None", "last_error": str(_mt5.last_error())}
        # Close immediately if opened
        if r and r.retcode == 10009:
            _mt5.order_send({
                "action": _mt5.TRADE_ACTION_DEAL, "symbol": "EURUSD",
                "volume": 0.01, "type": _mt5.ORDER_TYPE_SELL, "price": tick.bid,
                "position": r.order, "deviation": 10, "magic": 99999,
                "comment": "TW-DIAG-CLOSE", "type_filling": _mt5.ORDER_FILLING_FOK,
            })
        return {"init": init_ok, "account": info.login if info else None,
                "order_check": check_result, "order_send": send_result}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/broker/accounts")
async def list_broker_accounts():
    """List all MT5 accounts."""
    async with async_session_factory() as s:
        result = await s.execute(select(MT5Account).order_by(MT5Account.created_at))
        accounts = result.scalars().all()
    return [_mt5acc_to_dict(a) for a in accounts]


@app.post("/api/broker/accounts")
async def add_broker_account(payload: dict):
    """Add a new MT5 account."""
    async with async_session_factory() as s:
        acc = MT5Account(
            label=payload.get("label", ""),
            login=str(payload.get("login", "")),
            password=payload.get("password", ""),
            server=payload.get("server", ""),
            account_type=payload.get("account_type", "demo"),
            is_active=False,
        )
        s.add(acc)
        await s.commit()
        await s.refresh(acc)
        return _mt5acc_to_dict(acc)


@app.post("/api/broker/accounts/{account_id}/activate")
async def activate_broker_account(account_id: int):
    """Set a specific account as active; deactivate all others."""
    async with async_session_factory() as s:
        result = await s.execute(select(MT5Account))
        all_accs = result.scalars().all()
        target = None
        for a in all_accs:
            if a.id == account_id:
                a.is_active = True
                target = a
            else:
                a.is_active = False
        if not target:
            raise HTTPException(404, "Account not found")
        # Update system config with new credentials
        await set_config("mt5_login",    target.login,        s)
        await set_config("mt5_password", target.password,     s)
        await set_config("mt5_server",   target.server,       s)
        await s.commit()
    # Restart bridge with new credentials
    os.environ["MT5_LOGIN"]    = target.login
    os.environ["MT5_PASSWORD"] = target.password
    os.environ["MT5_SERVER"]   = target.server
    global _bridge_proc
    if _bridge_proc and _bridge_proc.poll() is None:
        try:
            _bridge_proc.terminate()
            _bridge_proc.wait(timeout=3)
        except Exception:
            pass
    _bridge_proc = None
    _start_mt5_direct()
    return {"status": "activated", "account_id": account_id}


@app.get("/api/broker/accounts/{account_id}/test")
async def test_broker_account(account_id: int):
    """Test credentials for a specific account via the bridge."""
    async with async_session_factory() as s:
        acc = await s.get(MT5Account, account_id)
        bridge_url = await get_config("mt5_bridge_url", s) or ""
    if not acc:
        raise HTTPException(404, "Account not found")
    if not bridge_url:
        return {"ok": False, "error": "MT5 bridge non configurato"}
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{bridge_url.rstrip('/')}/test-credentials",
                json={"login": acc.login, "password": acc.password, "server": acc.server},
            )
            return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/broker/accounts/{account_id}")
async def remove_broker_account(account_id: int):
    """Delete an MT5 account (cannot delete active account)."""
    async with async_session_factory() as s:
        acc = await s.get(MT5Account, account_id)
        if not acc:
            raise HTTPException(404, "Account not found")
        if acc.is_active:
            raise HTTPException(400, "Cannot remove the active account")
        await s.delete(acc)
        await s.commit()
    return {"status": "removed", "account_id": account_id}


def _mt5acc_to_dict(a: MT5Account) -> dict:
    return {
        "id":           a.id,
        "label":        a.label,
        "login":        a.login,
        "server":       a.server,
        "account_type": a.account_type,
        "is_active":    a.is_active,
        "balance":      a.balance,
        "created_at":   a.created_at.isoformat() if a.created_at else None,
    }


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
        # Include ALL closed trades (including archived) for accurate performance stats
        result = await s.execute(
            select(Trade).where(Trade.status == "CLOSED")
        )
        closed = result.scalars().all()

    total  = len(closed)
    wins   = sum(1 for t in closed if t.result == "WIN")
    losses = sum(1 for t in closed if t.result == "LOSS")
    be     = sum(1 for t in closed if t.result == "BREAKEVEN")

    gross_win  = sum((t.pnl_usd or 0) for t in closed if (t.pnl_usd or 0) > 0)
    gross_loss = abs(sum((t.pnl_usd or 0) for t in closed if (t.pnl_usd or 0) < 0))
    pf = round(gross_win / gross_loss, 2) if gross_loss else (999.0 if gross_win else 0.0)

    pnl_list = [t.pnl_usd or 0 for t in closed]
    avg_rr   = round(gross_win / wins / (gross_loss / losses), 2) if wins and losses else 0.0

    setups: dict = {}
    for t in closed:
        setup = t.ict_setup or "Unknown"
        if setup not in setups:
            setups[setup] = {"total": 0, "wins": 0, "losses": 0, "total_pips": 0.0, "total_pnl": 0.0}
        setups[setup]["total"]      += 1
        setups[setup]["total_pips"] += t.pnl_pips or 0
        setups[setup]["total_pnl"]  += t.pnl_usd  or 0
        if t.result == "WIN":   setups[setup]["wins"]   += 1
        elif t.result == "LOSS": setups[setup]["losses"] += 1
    for v in setups.values():
        v["win_rate"]   = round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        v["total_pips"] = round(v["total_pips"], 1)
        v["total_pnl"]  = round(v["total_pnl"], 2)

    # Max drawdown calculation — track equity curve from trade sequence
    account_balance = 5000.0
    try:
        async with async_session_factory() as s:
            bal_raw = await get_config("account_balance", s)
            if bal_raw:
                account_balance = float(bal_raw)
    except Exception:
        pass

    sorted_trades = sorted(closed, key=lambda t: t.close_time or t.open_time or datetime.min)
    equity = account_balance
    peak = equity
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    for t in sorted_trades:
        equity += (t.pnl_usd or 0)
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak * 100) if peak > 0 else 0
        if dd > max_dd_usd:
            max_dd_usd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    return {
        "total_trades":  total,
        "wins":          wins,
        "losses":        losses,
        "breakeven":     be,
        "win_rate":      round(wins / total * 100, 1) if total else 0,
        "avg_rr":        avg_rr,
        "profit_factor": pf,
        "total_pnl":     round(sum(pnl_list), 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "by_setup":      setups,
        "total_closed":  total,
    }


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
        "tp_hits": t.tp_hits or 0,
        "close_notes": t.close_notes or "",
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
    try:
        uvicorn.run(
            "main:app",
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", 8000)),
            reload=False,
        )
    except Exception as exc:
        logger.critical("FATAL: Backend crashed: %s", exc, exc_info=True)
        raise
