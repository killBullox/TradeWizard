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
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc

load_dotenv()

from models.database import (
    async_session_factory, init_db, Trade, AgentLog,
    JournalEntry, Meeting, SystemConfig, set_config, get_config,
    BacktestRun,
)
from orchestrator import Orchestrator
from services.forex_data import fetch_ohlcv
from services.backtester import run_backtest
from services.analytics import compute_analytics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

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
@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    await init_db()
    orchestrator = Orchestrator(broadcast_fn=manager.broadcast)
    await orchestrator.start()
    logger.info("TradeWizard system started ✅")
    yield
    if orchestrator:
        await orchestrator.stop()
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

# Serve static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


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
@app.get("/")
async def root():
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "TradeWizard API", "docs": "/docs"}


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
    symbol       = data.get("symbol", "EURUSD").upper()
    timeframe    = data.get("timeframe", "H1")
    strategy     = data.get("strategy", "Mixed")
    bars         = int(data.get("bars", 500))
    risk_percent = float(data.get("risk_percent", 1.0))
    rr_ratio     = float(data.get("rr_ratio", 2.0))
    balance      = float(data.get("initial_balance", 10000.0))
    max_risk_usd    = float(data["max_risk_usd"]) if data.get("max_risk_usd") else None
    enabled_setups  = data.get("enabled_setups") or None  # list or None

    valid_tf = {"M5","M15","M30","H1","H4","D1"}
    valid_st = {"FVG","OrderBlock","Liquidity","Mixed"}
    if timeframe not in valid_tf:
        raise HTTPException(400, f"timeframe must be one of {valid_tf}")
    if strategy not in valid_st:
        raise HTTPException(400, f"strategy must be one of {valid_st}")

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
        risk_percent, rr_ratio, balance, max_risk_usd, enabled_setups
    ))
    return {"run_id": run_id, "status": "RUNNING"}


async def _exec_backtest(
    run_id, symbol, timeframe, strategy, bars,
    risk_percent, rr_ratio, balance, max_risk_usd=None, enabled_setups=None
):
    try:
        result = await run_backtest(
            symbol=symbol, timeframe=timeframe, strategy=strategy,
            bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
            initial_balance=balance, max_risk_usd=max_risk_usd,
            enabled_setups=enabled_setups,
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
        "created_at":   r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


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
