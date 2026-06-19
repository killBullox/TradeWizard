"""
paper_account.py — Virtual paper trading account

Manages a fully simulated trading account that runs the complete
multi-agent pipeline (ICTEA → RM → TR → AT) but executes trades
virtually instead of sending to MT5.

Features
--------
- Virtual balance with real-time P&L
- Price update loop: fetches current prices every 30 s
- Full position lifecycle: open, modify SL, partial close, close
- Equity curve tracking (sampled every price update)
- Separate from live trades — stored with is_paper=True flag
- Persists across restarts via DB
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable, Optional

logger = logging.getLogger("paper_account")


class PaperAccount:
    """In-memory paper trading account with DB persistence."""

    PRICE_INTERVAL = 30   # seconds between price refreshes

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        broadcast_fn: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.initial_balance = initial_balance
        self.balance         = initial_balance   # cash (closed P&L applied)
        self.broadcast       = broadcast_fn or self._noop

        # open paper positions: trade_id → position dict
        self._positions: dict[int, dict] = {}
        self._equity_curve: list[dict]   = []
        self._price_task: Optional[asyncio.Task] = None
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        """Start price-update loop and restore open positions from DB."""
        await self._restore_from_db()
        self._running    = True
        self._price_task = asyncio.create_task(self._price_loop())
        logger.info("PaperAccount started  balance=%.2f  open=%d",
                    self.balance, len(self._positions))

    async def stop(self):
        self._running = False
        if self._price_task:
            self._price_task.cancel()
            try:
                await self._price_task
            except asyncio.CancelledError:
                pass

    # ── Trade actions ─────────────────────────────────────────────────────────

    def open_position(self, trade_id: int, trade_params: dict) -> dict:
        """Register a new paper position. Returns a mock MT5 response."""
        entry = float(trade_params.get("entry_price", 0))
        if entry == 0:
            return {"success": False, "error": "No entry price"}

        pos = {
            "trade_id":    trade_id,
            "symbol":      trade_params.get("symbol", ""),
            "direction":   trade_params.get("direction", "BUY"),
            "entry_price": entry,
            "stop_loss":   float(trade_params.get("stop_loss", 0)),
            "take_profit": float(trade_params.get("take_profit_1", 0)),
            "lot_size":    float(trade_params.get("lot_size", 0.01)),
            "open_time":   datetime.now(timezone.utc).isoformat(),
            "opened_at":   datetime.now(timezone.utc),  # for min-hold check
            "current_price": entry,
            "unrealised_pnl_usd":  0.0,
            "unrealised_pnl_pips": 0.0,
        }
        self._positions[trade_id] = pos
        logger.info("Paper OPEN  #%d  %s %s @ %.5f", trade_id, pos["symbol"], pos["direction"], entry)
        return {"success": True, "ticket": f"PAPER-{trade_id}", "mode": "paper"}

    def modify_sl(self, trade_id: int, new_sl: float) -> dict:
        pos = self._positions.get(trade_id)
        if not pos:
            return {"success": False, "error": f"Paper position {trade_id} not found"}
        pos["stop_loss"] = new_sl
        return {"success": True, "ticket": f"PAPER-{trade_id}", "new_sl": new_sl}

    def close_position(self, trade_id: int, close_price: Optional[float] = None) -> dict:
        pos = self._positions.pop(trade_id, None)
        if not pos:
            return {"success": False, "error": f"Paper position {trade_id} not found"}

        price = close_price or pos.get("current_price", pos["entry_price"])
        pnl   = self._calc_pnl(pos, price)
        self.balance = round(self.balance + pnl["usd"], 2)
        logger.info("Paper CLOSE #%d  %s  pnl=%.2f USD", trade_id, pos["symbol"], pnl["usd"])
        return {
            "success":     True,
            "ticket":      f"PAPER-{trade_id}",
            "close_price": price,
            "pnl_usd":     pnl["usd"],
            "pnl_pips":    pnl["pips"],
        }

    def partial_close(self, trade_id: int, percent: float) -> dict:
        pos = self._positions.get(trade_id)
        if not pos:
            return {"success": False, "error": f"Paper position {trade_id} not found"}
        price = pos.get("current_price", pos["entry_price"])
        pnl   = self._calc_pnl(pos, price)
        partial_usd = pnl["usd"] * percent / 100
        self.balance = round(self.balance + partial_usd, 2)
        pos["lot_size"] = round(pos["lot_size"] * (1 - percent / 100), 4)
        return {"success": True, "partial_pnl_usd": partial_usd}

    # ── Account summary ───────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        unrealised = sum(
            self._calc_pnl(p, p.get("current_price", p["entry_price"]))["usd"]
            for p in self._positions.values()
        )
        equity = round(self.balance + unrealised, 2)
        return {
            "balance":        round(self.balance, 2),
            "equity":         equity,
            "unrealised_pnl": round(unrealised, 2),
            "initial_balance": self.initial_balance,
            "return_pct":     round((equity - self.initial_balance) / self.initial_balance * 100, 2),
            "open_positions": len(self._positions),
            "equity_curve":   self._equity_curve[-200:],
        }

    def get_positions(self) -> list[dict]:
        return list(self._positions.values())

    async def reset(self, new_balance: Optional[float] = None):
        """Close all paper positions and reset the account."""
        self._positions.clear()
        self._equity_curve.clear()
        self.balance         = new_balance or self.initial_balance
        self.initial_balance = self.balance
        # Mark all open paper trades as CANCELLED in DB
        await self._cancel_open_db_trades()
        logger.info("PaperAccount reset  balance=%.2f", self.balance)

    # ── Price update loop ─────────────────────────────────────────────────────

    async def _price_loop(self):
        while self._running:
            try:
                await self._refresh_prices()
            except Exception as exc:
                logger.warning("Price update error: %s", exc)
            await asyncio.sleep(self.PRICE_INTERVAL)

    async def _refresh_prices(self):
        if not self._positions:
            return

        symbols = {p["symbol"] for p in self._positions.values()}
        updates = []

        for sym in symbols:
            try:
                # 1. Try local OHLCV cache (H1) — populated by MT5/yfinance, most reliable
                price = 0
                try:
                    from services.ohlcv_cache import get_cached_candles
                    cached = await get_cached_candles(sym, "H1", n_bars=1)
                    if cached:
                        price = float(cached[-1]["close"])
                except Exception:
                    pass

                # 2. Fall back to live yfinance H1 fetch
                if not price:
                    from services.forex_data import fetch_ohlcv
                    data = await fetch_ohlcv(sym, "H1", 5)
                    price = data.get("indicators", {}).get("current_price", 0)

                if not price:
                    continue
                for tid, pos in list(self._positions.items()):
                    if pos["symbol"] != sym:
                        continue
                    pos["current_price"] = price
                    pnl = self._calc_pnl(pos, price)
                    pos["unrealised_pnl_usd"]  = pnl["usd"]
                    pos["unrealised_pnl_pips"] = pnl["pips"]

                    # Check SL / TP auto-close
                    hit = self._check_sl_tp(pos, price)
                    if hit:
                        if hit == "SL_HIT":
                            close_at = pos["stop_loss"] or price
                            note = f"SL colpito @ {close_at:.5f}"
                        else:  # TP_HIT
                            close_at = pos["take_profit"] or price
                            note = f"TP colpito @ {close_at:.5f} — trade chiuso su target"
                        result = self.close_position(tid, close_at)
                        updates.append({
                            "type":      "paper_auto_close",
                            "trade_id":  tid,
                            "symbol":    sym,
                            "reason":    hit,
                            "price":     close_at,
                            "pnl_usd":   result.get("pnl_usd", 0),
                            "pnl_pips":  result.get("pnl_pips", 0),
                        })
                        await self._close_in_db(tid, close_at, note)
            except Exception as exc:
                logger.debug("Price fetch error for %s: %s", sym, exc)

        # Record equity snapshot
        summary = self.get_summary()
        self._equity_curve.append({
            "time":   datetime.now(timezone.utc).isoformat(),
            "equity": summary["equity"],
        })

        # Broadcast updates
        if self._positions or updates:
            await self.broadcast({
                "type":      "paper_update",
                "summary":   summary,
                "positions": self.get_positions(),
            })
        for ev in updates:
            await self.broadcast(ev)

    # ── Helpers ───────────────────────────────────────────────────────────────

    _PIP_USD = {
        "XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
        "USDJPY": 6.5,  "EURJPY": 6.5,  "GBPJPY": 6.5,  "AUDJPY": 6.5,
        "CHFJPY": 6.5,  "CADJPY": 6.5,  "NZDJPY": 6.5,
        "USDCHF": 11.0, "EURCHF": 11.0, "GBPCHF": 11.0,
        "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25,
    }

    @staticmethod
    def _calc_pnl(pos: dict, current_price: float) -> dict:
        sym   = pos["symbol"]
        pip   = 0.01 if "JPY" in sym else (1.0 if sym in ("XAUUSD","US30","NAS100","US500") else 0.0001)
        entry = pos["entry_price"]
        lots  = pos.get("lot_size", 0.01)
        if pos["direction"] == "BUY":
            pips = (current_price - entry) / pip
        else:
            pips = (entry - current_price) / pip
        pip_value_usd = PaperAccount._PIP_USD.get(sym, 10.0)
        usd = pips * pip_value_usd * lots
        return {"pips": round(pips, 1), "usd": round(usd, 2)}

    @staticmethod
    def _check_sl_tp(pos: dict, price: float) -> Optional[str]:
        sl = pos.get("stop_loss", 0)
        tp = pos.get("take_profit", 0)
        if pos["direction"] == "BUY":
            if sl and price <= sl: return "SL_HIT"
            if tp and price >= tp: return "TP_HIT"
        else:
            if sl and price >= sl: return "SL_HIT"
            if tp and price <= tp: return "TP_HIT"
        return None

    async def _restore_from_db(self):
        """Re-load open paper trades from DB after a restart."""
        try:
            from models.database import async_session_factory, Trade
            from sqlalchemy import select
            async with async_session_factory() as s:
                result = await s.execute(
                    select(Trade).where(Trade.status == "ACTIVE", Trade.is_paper == True)  # noqa: E712
                )
                trades = result.scalars().all()

            # Restore balance from config
            async with async_session_factory() as s:
                from models.database import get_config
                bal_raw = await get_config("paper_balance", s)
                if bal_raw:
                    self.balance = float(bal_raw)

            for t in trades:
                self._positions[t.id] = {
                    "trade_id":    t.id,
                    "symbol":      t.symbol,
                    "direction":   t.direction,
                    "entry_price": t.entry_price or 0,
                    "stop_loss":   t.stop_loss or 0,
                    "take_profit": t.take_profit_1 or 0,
                    "lot_size":    t.lot_size or 0.01,
                    "open_time":   t.open_time.isoformat() if t.open_time else "",
                    "current_price": t.entry_price or 0,
                    "unrealised_pnl_usd":  0.0,
                    "unrealised_pnl_pips": 0.0,
                }
            logger.info("Restored %d open paper positions from DB", len(self._positions))
        except Exception as exc:
            logger.warning("Could not restore paper positions: %s", exc)

    async def _close_in_db(self, trade_id: int, close_price: float, note: str = ""):
        try:
            from models.database import async_session_factory, Trade
            pos = self._positions.get(trade_id)  # already popped; use local copy
            async with async_session_factory() as s:
                t = await s.get(Trade, trade_id)
                if t:
                    entry = t.entry_price or 0
                    sym2  = t.symbol or ""
                    pip2  = 0.01 if "JPY" in sym2 else (1.0 if sym2 in ("XAUUSD","US30","NAS100","US500") else 0.0001)
                    if t.direction == "BUY":
                        pips = (close_price - entry) / pip2
                    else:
                        pips = (entry - close_price) / pip2
                    pv   = PaperAccount._PIP_USD.get(sym2, 10.0)
                    usd  = pips * pv * (t.lot_size or 0.01)
                    t.status      = "CLOSED"
                    t.close_price = close_price
                    t.close_time  = datetime.utcnow()
                    t.pnl_pips    = round(pips, 1)
                    t.pnl_usd     = round(usd, 2)
                    t.result      = "WIN" if usd > 0 else ("LOSS" if usd < 0 else "BREAKEVEN")
                    if note:
                        from datetime import datetime as _dt
                        ts = _dt.utcnow().strftime("%H:%M")
                        existing = t.close_notes or ""
                        t.close_notes = (existing + "\n" if existing else "") + f"[{ts}] {note}"
                    await s.commit()
            # Persist updated balance
            async with async_session_factory() as s:
                from models.database import set_config
                await set_config("paper_balance", str(round(self.balance, 2)), s)
        except Exception as exc:
            logger.warning("Could not close paper trade in DB: %s", exc)

    async def _cancel_open_db_trades(self):
        try:
            from models.database import async_session_factory, Trade, set_config
            from sqlalchemy import select
            async with async_session_factory() as s:
                result = await s.execute(
                    select(Trade).where(Trade.status == "ACTIVE", Trade.is_paper == True)  # noqa: E712
                )
                for t in result.scalars().all():
                    t.status = "CANCELLED"
                await set_config("paper_balance", str(round(self.balance, 2)), s)
                await s.commit()
        except Exception as exc:
            logger.warning("Cancel DB trades error: %s", exc)

    @staticmethod
    async def _noop(_): pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_instance: Optional[PaperAccount] = None


def get_paper_account(broadcast_fn=None, initial_balance: float = 10_000.0) -> PaperAccount:
    global _instance
    if _instance is None:
        _instance = PaperAccount(initial_balance=initial_balance, broadcast_fn=broadcast_fn)
    elif broadcast_fn is not None:
        _instance.broadcast = broadcast_fn
    return _instance
