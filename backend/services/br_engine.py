"""
br_engine.py — Backtest-to-Reality engine.

Third TradeWizard environment, alongside Production and Lab. BR runs the
SAME deterministic strategy as the backtester (services.backtester.ICTAnalyzer)
in real time on live MT5 candles, in paper mode. No LLM calls, no meetings,
no learning rules — fixed strategy, fixed risk, just see if the backtest
edge survives the live tape.

Loop:
1. every BR_TICK_SECONDS (default 300 = every 5 min)
2. for each enabled symbol:
   - fetch latest H1 candles from the bridge (cached in DB by upsert)
   - run ICTAnalyzer.build_signals on the closed bars
   - check the LAST signal — if it's on a bar we haven't processed yet,
     and its setup is in br_enabled_setups, open a paper trade with the
     same SL/TP/lot logic the backtester uses
3. concurrently a monitor task watches open positions and closes on
   SL hit / TP hit / max-hold-time, mirroring the backtester's _simulate.

Persistence:
- BR-specific config keys live in SystemConfig (br_enabled_symbols,
  br_enabled_setups, br_risk_usd, br_rr_ratio, br_running, br_*_pips,
  br_commission, br_max_hold_hours).
- Trades go to the regular Trade table with is_paper=True and
  ict_setup="BR/<setup>" so they are easy to filter and don't mix with
  prod/lab streams (BR runs on its own DB anyway, but the prefix helps
  if the row is moved or copied).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("br_engine")

DEFAULT_TICK_SECONDS    = 300   # 5 minutes
DEFAULT_RISK_USD        = 250.0
DEFAULT_RR_RATIO        = 2.0
DEFAULT_SLIPPAGE_PIPS   = 0.2
DEFAULT_COMMISSION_USD  = 7.0
DEFAULT_MAX_HOLD_HOURS  = 6
DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF",
                   "AUDUSD", "USDCAD", "NZDUSD", "GBPJPY"]
DEFAULT_SETUPS = ["FVG_BULL", "FVG_BEAR",
                  "OB_BULL", "OB_BEAR",
                  "LIQ_BULL", "LIQ_BEAR",
                  "BREAK_BULL", "BREAK_BEAR"]


def _pip_for(symbol: str) -> float:
    if "JPY" in symbol: return 0.01
    if symbol in ("XAUUSD", "US30", "NAS100", "US500"): return 1.0
    return 0.0001


def _pip_value_for(symbol: str) -> float:
    table = {
        "XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
        "USDJPY": 6.5,  "EURJPY": 6.5,  "GBPJPY": 6.5,  "AUDJPY": 6.5,
        "CHFJPY": 6.5,  "CADJPY": 6.5,  "NZDJPY": 6.5,
        "USDCHF": 11.0, "EURCHF": 11.0, "GBPCHF": 11.0,
        "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25,
    }
    return table.get(symbol, 10.0)


_SPREAD_PIPS_DEFAULTS = {
    "EURUSD": 0.7, "GBPUSD": 0.9, "USDJPY": 0.8, "USDCHF": 1.4,
    "AUDUSD": 1.0, "NZDUSD": 1.6, "USDCAD": 1.5,
    "EURJPY": 1.2, "GBPJPY": 2.0, "EURGBP": 1.0,
    "XAUUSD": 30.0,
}


class BREngine:
    """The Backtest-to-Reality runtime. Single instance per backend."""

    def __init__(self, broadcast_fn=None):
        self._task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._broadcast = broadcast_fn  # async callable for websocket events
        # Config (loaded from DB on start)
        self.symbols: list[str] = list(DEFAULT_SYMBOLS)
        self.enabled_setups: set[str] = set(DEFAULT_SETUPS)
        self.risk_usd: float = DEFAULT_RISK_USD
        self.rr_ratio: float = DEFAULT_RR_RATIO
        self.slippage_pips: float = DEFAULT_SLIPPAGE_PIPS
        self.commission_per_lot_usd: float = DEFAULT_COMMISSION_USD
        self.max_hold_hours: int = DEFAULT_MAX_HOLD_HOURS
        self.tick_seconds: int = DEFAULT_TICK_SECONDS
        # Per-symbol last signal bar processed (avoid double-fire)
        self._last_signal_bar: dict[str, str] = {}

    # ---------------------------------------------------------------- #
    # Lifecycle
    # ---------------------------------------------------------------- #
    @property
    def running(self) -> bool:
        return self._running

    async def load_config(self):
        from models.database import async_session_factory, get_config

        async with async_session_factory() as s:
            async def _get(k, default):
                v = await get_config(k, s)
                return v if v not in (None, "") else default

            symbols_raw = await _get("br_enabled_symbols", json.dumps(DEFAULT_SYMBOLS))
            setups_raw  = await _get("br_enabled_setups", json.dumps(DEFAULT_SETUPS))
            try:
                self.symbols = json.loads(symbols_raw)
            except Exception:
                self.symbols = list(DEFAULT_SYMBOLS)
            try:
                self.enabled_setups = set(json.loads(setups_raw))
            except Exception:
                self.enabled_setups = set(DEFAULT_SETUPS)
            self.risk_usd = float(await _get("br_risk_usd", DEFAULT_RISK_USD))
            self.rr_ratio = float(await _get("br_rr_ratio", DEFAULT_RR_RATIO))
            self.slippage_pips = float(await _get("br_slippage_pips", DEFAULT_SLIPPAGE_PIPS))
            self.commission_per_lot_usd = float(await _get("br_commission_per_lot_usd", DEFAULT_COMMISSION_USD))
            self.max_hold_hours = int(float(await _get("br_max_hold_hours", DEFAULT_MAX_HOLD_HOURS)))
            self.tick_seconds = int(float(await _get("br_tick_seconds", DEFAULT_TICK_SECONDS)))

    async def start(self):
        if self._running:
            return
        await self.load_config()
        self._running = True
        self._task = asyncio.create_task(self._loop())
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        await self._set_running_flag(True)
        logger.info("BR engine started: symbols=%s setups=%s risk=$%s",
                    self.symbols, sorted(self.enabled_setups), self.risk_usd)
        await self._broadcast_event({"type": "br_started"})

    async def stop(self):
        self._running = False
        await self._set_running_flag(False)
        if self._task:
            self._task.cancel()
            try: await self._task
            except Exception: pass
        if self._monitor_task:
            self._monitor_task.cancel()
            try: await self._monitor_task
            except Exception: pass
        logger.info("BR engine stopped")
        await self._broadcast_event({"type": "br_stopped"})

    async def _set_running_flag(self, on: bool):
        from models.database import async_session_factory, set_config
        async with async_session_factory() as s:
            await set_config("br_running", "true" if on else "false", s)

    async def _broadcast_event(self, payload: dict):
        if not self._broadcast:
            return
        try:
            await self._broadcast(payload)
        except Exception:
            pass

    # ---------------------------------------------------------------- #
    # Main scan loop
    # ---------------------------------------------------------------- #
    async def _loop(self):
        # Brief startup delay so config + bridge are ready
        await asyncio.sleep(5)
        tick = 0
        while self._running:
            tick += 1
            logger.info("BR scan tick #%d starting (%d symbols, setups=%s)",
                        tick, len(self.symbols), sorted(self.enabled_setups))
            try:
                await self.load_config()  # pick up live changes
                for sym in self.symbols:
                    if not self._running:
                        break
                    try:
                        await self._scan_symbol(sym)
                    except Exception as exc_inner:
                        logger.warning("BR _scan_symbol %s raised: %s",
                                       sym, exc_inner, exc_info=True)
            except asyncio.CancelledError:
                logger.info("BR scan loop cancelled")
                break
            except Exception as exc:
                logger.error("BR scan loop error: %s", exc, exc_info=True)
            logger.info("BR scan tick #%d done — sleeping %ds", tick, self.tick_seconds)
            try:
                await asyncio.sleep(self.tick_seconds)
            except asyncio.CancelledError:
                logger.info("BR scan loop sleep cancelled — stopping")
                break
        logger.info("BR scan loop exited (tick=%d, running=%s)", tick, self._running)

    async def _scan_symbol(self, symbol: str):
        from services.backtester import ICTAnalyzer, Candle
        from services.mt5_data import fetch_ohlcv as _mt5_fetch
        from services.ohlcv_cache import upsert_candles

        bridge_url = os.environ.get("MT5_BRIDGE_URL") or "http://localhost:5555"
        try:
            raw = await _mt5_fetch(symbol, "H1", 300, bridge_url=bridge_url)
            candles_raw = raw.get("candles", [])
        except Exception as exc:
            logger.warning("BR fetch %s failed: %s", symbol, exc)
            return
        if len(candles_raw) < 60:
            logger.info("BR %s: only %d candles, need >=60 — skip", symbol, len(candles_raw))
            return
        logger.debug("BR %s: %d candles fetched", symbol, len(candles_raw))

        # Persist to cache so the backtester can replay BR runs
        try:
            await upsert_candles(symbol, "H1", candles_raw)
        except Exception:
            pass

        candles = [Candle(**c) for c in candles_raw]
        analyzer = ICTAnalyzer(candles, symbol, "H1", "Mixed")
        signals = analyzer.build_signals()
        if not signals:
            logger.info("BR %s: 0 signals from ICTAnalyzer", symbol)
            return
        logger.info("BR %s: %d signals (last on bar %d type=%s)",
                    symbol, len(signals), signals[-1].get("bar"), signals[-1].get("type"))

        # Only consider the latest signal bar — earlier ones are history.
        last_sig = signals[-1]
        sig_type = last_sig.get("type", "")
        if sig_type not in self.enabled_setups:
            logger.info("BR %s: last signal %s NOT in enabled setups", symbol, sig_type)
            return
        sig_bar = last_sig["bar"]
        sig_bar_time = candles[sig_bar].time if 0 <= sig_bar < len(candles) else None
        if not sig_bar_time:
            logger.warning("BR %s: bad sig_bar %d", symbol, sig_bar)
            return

        # Already processed?
        if self._last_signal_bar.get(symbol) == sig_bar_time:
            logger.debug("BR %s: signal at %s already processed", symbol, sig_bar_time)
            return

        # Skip stale signals (more than 2 hours old) — BR fires on the
        # bar that just closed, not on every history bar.
        try:
            sig_dt = datetime.fromisoformat(sig_bar_time.replace("Z", ""))
            age_h = (datetime.utcnow() - sig_dt).total_seconds() / 3600
            if age_h > 2.5:
                logger.info("BR %s: signal at %s is %.1fh old (>2.5h) — skip+memo",
                            symbol, sig_bar_time, age_h)
                self._last_signal_bar[symbol] = sig_bar_time
                return
        except Exception:
            pass

        # Already an open BR trade on this symbol? Skip — same as backtester
        # which runs one position at a time.
        if await self._has_open_trade(symbol):
            logger.info("BR %s: open trade exists — skip new signal", symbol)
            return

        # Build trade params from the signal (mirrors _make_pending /
        # _make_market_trade in backtester).
        trade_params = self._signal_to_trade_params(symbol, last_sig, candles[-1])
        if not trade_params:
            return
        trade_id = await self._open_paper_trade(symbol, last_sig, trade_params, sig_bar_time)
        self._last_signal_bar[symbol] = sig_bar_time
        await self._broadcast_event({
            "type": "br_trade_opened",
            "trade_id": trade_id, "symbol": symbol,
            "setup": sig_type, "direction": trade_params["direction"],
            "entry": trade_params["entry_price"],
            "sl": trade_params["stop_loss"], "tp": trade_params["take_profit_1"],
        })
        logger.info("BR opened paper #%d: %s %s @ %.5f sl=%.5f tp=%.5f",
                    trade_id, symbol, trade_params["direction"],
                    trade_params["entry_price"], trade_params["stop_loss"],
                    trade_params["take_profit_1"])

    def _signal_to_trade_params(self, symbol: str, sig: dict, last_candle) -> dict | None:
        sig_type = sig.get("type", "")
        is_bull = sig_type.endswith("_BULL")
        direction = "BUY" if is_bull else "SELL"
        # For market entries (LIQ / BREAK) we use last candle close; for
        # FVG/OB the signal level itself is the limit entry. To keep BR
        # simple we always use market-style entry on the latest close —
        # the backtester does the same for LIQ and our paper engine does
        # not support pending orders.
        entry = float(last_candle.close)
        sl_price = sig.get("sl") or sig.get("stop_loss")
        tp_price = sig.get("tp") or sig.get("take_profit")
        if sl_price is None or tp_price is None:
            return None
        sl = float(sl_price); tp = float(tp_price)
        # Minimum sanity: SL on the right side of entry
        pip = _pip_for(symbol)
        sl_dist = abs(entry - sl)
        if sl_dist < pip:
            return None

        # Lot size from fixed-risk dollars
        pip_value = _pip_value_for(symbol)
        sl_pips = sl_dist / pip
        lot = round(self.risk_usd / max(sl_pips * pip_value, 1e-6), 3)
        lot = max(0.01, min(lot, 100.0))

        return {
            "symbol": symbol, "direction": direction,
            "entry_price": round(entry, 5),
            "stop_loss": round(sl, 5),
            "take_profit_1": round(tp, 5),
            "take_profit_2": None, "take_profit_3": None,
            "lot_size": lot, "risk_percent": 0.0,
            "rr_ratio": round(abs(tp - entry) / sl_dist, 2) if sl_dist else 0,
        }

    async def _has_open_trade(self, symbol: str) -> bool:
        from models.database import Trade, async_session_factory
        from sqlalchemy import select, or_
        async with async_session_factory() as s:
            r = await s.execute(
                select(Trade).where(
                    Trade.symbol == symbol,
                    Trade.status == "ACTIVE",
                ).limit(1)
            )
            return r.scalars().first() is not None

    async def _open_paper_trade(self, symbol, sig, params, sig_bar_time) -> int:
        from models.database import Trade, async_session_factory
        sig_type = sig.get("type", "")
        trade = Trade(
            symbol=symbol,
            direction=params["direction"],
            status="ACTIVE",
            entry_price=params["entry_price"],
            stop_loss=params["stop_loss"],
            take_profit_1=params["take_profit_1"],
            lot_size=params["lot_size"],
            risk_percent=0.0,
            rr_ratio=params["rr_ratio"],
            ict_setup=f"BR/{sig_type}",
            ict_context=json.dumps({"signal": sig, "bar_time": sig_bar_time}, default=str),
            risk_analysis=json.dumps({"engine": "BR", "risk_usd": self.risk_usd}),
            analyst_verdict=json.dumps({}),
            mt5_ticket=f"BR-{int(datetime.utcnow().timestamp())}",
            open_time=datetime.utcnow(),
            is_paper=True,
            archived=False,
            market_context=json.dumps({"engine": "BR"}),
        )
        async with async_session_factory() as s:
            s.add(trade)
            await s.commit()
            await s.refresh(trade)
            return trade.id

    # ---------------------------------------------------------------- #
    # Position monitor — close on SL/TP/timeout
    # ---------------------------------------------------------------- #
    async def _monitor_loop(self):
        await asyncio.sleep(10)
        while self._running:
            try:
                await self._monitor_active_trades()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("BR monitor error: %s", exc, exc_info=True)
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break

    async def _monitor_active_trades(self):
        from models.database import Trade, async_session_factory
        from sqlalchemy import select
        bridge_url = os.environ.get("MT5_BRIDGE_URL") or "http://localhost:5555"

        async with async_session_factory() as s:
            r = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
            trades = r.scalars().all()
        if not trades:
            return

        # Cache last tick per symbol per cycle
        ticks: dict[str, float] = {}
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as cli:
            for sym in {t.symbol for t in trades}:
                try:
                    resp = await cli.get(f"{bridge_url}/tick", params={"symbol": sym})
                    if resp.status_code == 200:
                        d = resp.json()
                        ticks[sym] = float(d.get("bid") or d.get("ask") or 0)
                except Exception:
                    pass

        now = datetime.utcnow()
        for t in trades:
            price = ticks.get(t.symbol)
            if not price:
                continue
            sl = float(t.stop_loss or 0)
            tp = float(t.take_profit_1 or 0)
            close_reason = None
            close_price  = None
            if t.direction == "BUY":
                if price <= sl: close_reason, close_price = "SL_HIT", sl
                elif price >= tp: close_reason, close_price = "TP_HIT", tp
            else:
                if price >= sl: close_reason, close_price = "SL_HIT", sl
                elif price <= tp: close_reason, close_price = "TP_HIT", tp
            # Max hold timeout
            if not close_reason and t.open_time:
                age_h = (now - t.open_time).total_seconds() / 3600
                if age_h >= self.max_hold_hours:
                    close_reason, close_price = "TIMEOUT", price
            if close_reason:
                await self._close_paper(t, close_price, close_reason)

    async def _close_paper(self, trade, close_price, reason):
        from models.database import Trade, async_session_factory
        pip = _pip_for(trade.symbol)
        if trade.direction == "BUY":
            gross_pips = (close_price - trade.entry_price) / pip
        else:
            gross_pips = (trade.entry_price - close_price) / pip
        # Apply same friction model as backtester
        spread = _SPREAD_PIPS_DEFAULTS.get(trade.symbol, 1.5)
        net_pips = gross_pips - spread - self.slippage_pips
        pip_value = _pip_value_for(trade.symbol)
        pnl_usd = net_pips * pip_value * trade.lot_size
        pnl_usd -= self.commission_per_lot_usd * trade.lot_size
        result = "WIN" if pnl_usd > 0 else ("LOSS" if pnl_usd < 0 else "BREAKEVEN")
        async with async_session_factory() as s:
            t = await s.get(Trade, trade.id)
            if t and t.status == "ACTIVE":
                t.status = "CLOSED"
                t.close_time = datetime.utcnow()
                t.close_price = round(close_price, 5)
                t.pnl_pips = round(net_pips, 1)
                t.pnl_usd  = round(pnl_usd, 2)
                t.result   = result
                t.close_notes = (t.close_notes or "") + f"[BR] {reason} @ {close_price:.5f}"
                await s.commit()
        await self._broadcast_event({
            "type": "br_trade_closed",
            "trade_id": trade.id, "symbol": trade.symbol,
            "reason": reason, "close_price": close_price,
            "pnl_usd": round(pnl_usd, 2), "result": result,
        })
        logger.info("BR closed #%d %s: %s @ %.5f net=%.1fp pnl=$%.2f (%s)",
                    trade.id, trade.symbol, reason, close_price, net_pips, pnl_usd, result)
