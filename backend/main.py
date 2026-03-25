"""
TradeWizard — Multi-Agent ICT Forex Trading System
FastAPI backend with WebSocket for real-time agent communication.
"""

import json
import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Set

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc

load_dotenv()

from models.database import (
    async_session_factory, init_db, Trade, AgentLog,
    JournalEntry, Meeting, SystemConfig, set_config, get_config
)
from orchestrator import Orchestrator

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


@app.post("/api/news/refresh")
async def refresh_news():
    if not orchestrator or not orchestrator.news_filter:
        raise HTTPException(503, "System not ready")
    count = await orchestrator.news_filter.force_refresh()
    return {"status": "refreshed", "event_count": count}


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
