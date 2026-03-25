"""
backtester.py — ICT Strategy Backtesting Engine

Simulates trades on historical OHLCV data using ICT setups:
  - FVG       Fair Value Gap retest
  - OrderBlock  Order Block retest
  - Liquidity  Liquidity sweep reversal
  - Mixed      All of the above

Each bar is evaluated for a setup. When a setup fires, a simulated
trade is opened and tracked bar-by-bar until SL or TP is hit.

Returns a BacktestResult with per-trade list and equity curve.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Literal, Optional

import numpy as np

logger = logging.getLogger("backtester")

Strategy = Literal["FVG", "OrderBlock", "Liquidity", "Mixed"]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Candle:
    time:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: int = 0


@dataclass
class SimTrade:
    id:          int
    setup:       str
    direction:   str          # BUY / SELL
    entry_bar:   int
    entry_time:  str
    entry_price: float
    stop_loss:   float
    take_profit: float
    lot_size:    float = 0.01
    exit_bar:    Optional[int]   = None
    exit_time:   Optional[str]   = None
    exit_price:  Optional[float] = None
    result:      Optional[str]   = None   # WIN / LOSS
    pnl_pips:    Optional[float] = None
    pnl_pct:     Optional[float] = None   # % of account
    rr_actual:   Optional[float] = None


@dataclass
class BacktestResult:
    symbol:        str
    timeframe:     str
    strategy:      str
    bars_used:     int
    risk_percent:  float
    rr_ratio:      float

    trades:        list[SimTrade] = field(default_factory=list)
    equity:        list[dict]     = field(default_factory=list)  # [{bar, equity}]

    # Computed stats
    total_trades:  int   = 0
    wins:          int   = 0
    losses:        int   = 0
    win_rate:      float = 0.0
    total_pips:    float = 0.0
    total_return:  float = 0.0     # %
    max_drawdown:  float = 0.0     # %
    profit_factor: float = 0.0
    avg_rr:        float = 0.0
    sharpe:        float = 0.0
    expectancy:    float = 0.0     # pips per trade

    def compute_stats(self, pip: float):
        closed = [t for t in self.trades if t.result]
        self.total_trades = len(closed)
        self.wins   = sum(1 for t in closed if t.result == "WIN")
        self.losses = sum(1 for t in closed if t.result == "LOSS")
        self.win_rate = round(self.wins / self.total_trades * 100, 1) if self.total_trades else 0.0

        pips = [t.pnl_pips for t in closed if t.pnl_pips is not None]
        self.total_pips = round(sum(pips), 1)

        gross_profit = sum(p for p in pips if p > 0)
        gross_loss   = abs(sum(p for p in pips if p < 0))
        self.profit_factor = round(gross_profit / gross_loss, 2) if gross_loss else float('inf')
        self.expectancy    = round(sum(pips) / len(pips), 1) if pips else 0.0

        rets = [t.pnl_pct for t in closed if t.pnl_pct is not None]
        self.total_return = round(sum(rets), 2)

        if len(rets) > 1:
            sharpe_raw = np.mean(rets) / (np.std(rets) + 1e-9)
            self.sharpe = round(float(sharpe_raw) * math.sqrt(252), 2)

        # Max drawdown from equity curve
        if self.equity:
            eq = [e["equity"] for e in self.equity]
            peak = eq[0]
            dd   = 0.0
            for v in eq:
                if v > peak:
                    peak = v
                dd = max(dd, (peak - v) / peak * 100)
            self.max_drawdown = round(dd, 2)

        rrs = [t.rr_actual for t in closed if t.rr_actual is not None]
        self.avg_rr = round(sum(rrs) / len(rrs), 2) if rrs else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trades"] = [asdict(t) for t in self.trades]
        return d


# ── Signal detectors ──────────────────────────────────────────────────────────

def _detect_fvg_signals(candles: list[Candle]) -> list[dict]:
    """
    FVG = 3-candle pattern where candle[0].high < candle[2].low (bullish)
          or candle[0].low > candle[2].high (bearish).
    Signal fires when price later re-enters the gap zone.
    """
    signals = []
    for i in range(2, len(candles) - 1):
        c0, c1, c2 = candles[i-2], candles[i-1], candles[i]
        # Bullish FVG
        if c0.high < c2.low and c1.close > c1.open:
            gap_top    = c2.low
            gap_bottom = c0.high
            gap_mid    = (gap_top + gap_bottom) / 2
            signals.append({
                "bar": i, "type": "FVG_BULL",
                "top": gap_top, "bottom": gap_bottom, "mid": gap_mid,
            })
        # Bearish FVG
        elif c0.low > c2.high and c1.close < c1.open:
            gap_top    = c0.low
            gap_bottom = c2.high
            gap_mid    = (gap_top + gap_bottom) / 2
            signals.append({
                "bar": i, "type": "FVG_BEAR",
                "top": gap_top, "bottom": gap_bottom, "mid": gap_mid,
            })
    return signals


def _detect_ob_signals(candles: list[Candle]) -> list[dict]:
    """
    Order Block: last opposite-body candle before an impulsive move.
    Bullish OB = bearish candle just before a strong bullish impulse.
    Bearish OB = bullish candle just before a strong bearish impulse.
    """
    signals = []
    bodies  = [abs(c.close - c.open) for c in candles]
    avg_body = sum(bodies) / max(len(bodies), 1)

    for i in range(1, len(candles) - 2):
        impulse = bodies[i + 1]
        if avg_body == 0 or impulse < avg_body * 1.5:
            continue
        c_ob  = candles[i]
        c_imp = candles[i + 1]
        # Bullish OB
        if c_ob.close < c_ob.open and c_imp.close > c_imp.open:
            signals.append({
                "bar": i, "type": "OB_BULL",
                "top": c_ob.high, "bottom": c_ob.low,
                "mid": (c_ob.high + c_ob.low) / 2,
            })
        # Bearish OB
        elif c_ob.close > c_ob.open and c_imp.close < c_imp.open:
            signals.append({
                "bar": i, "type": "OB_BEAR",
                "top": c_ob.high, "bottom": c_ob.low,
                "mid": (c_ob.high + c_ob.low) / 2,
            })
    return signals


def _detect_liquidity_signals(candles: list[Candle], swing_window: int = 5) -> list[dict]:
    """
    Liquidity sweep: price spikes above a recent swing high then closes below it
    (false breakout → reversal = bearish signal), or below swing low then closes
    above it (= bullish signal).
    """
    signals = []
    highs   = [c.high  for c in candles]
    lows    = [c.low   for c in candles]

    for i in range(swing_window + 1, len(candles)):
        window_highs = highs[i - swing_window - 1: i - 1]
        window_lows  = lows[ i - swing_window - 1: i - 1]
        swing_high   = max(window_highs) if window_highs else candles[i].high
        swing_low    = min(window_lows)  if window_lows  else candles[i].low

        c = candles[i]
        # Bearish sweep: wick above swing high, close below it
        if c.high > swing_high and c.close < swing_high:
            signals.append({
                "bar": i, "type": "LIQ_BEAR",
                "sweep_level": swing_high,
                "top": c.high, "bottom": c.low,
                "mid": c.close,
            })
        # Bullish sweep: wick below swing low, close above it
        elif c.low < swing_low and c.close > swing_low:
            signals.append({
                "bar": i, "type": "LIQ_BULL",
                "sweep_level": swing_low,
                "top": c.high, "bottom": c.low,
                "mid": c.close,
            })
    return signals


# ── Backtesting engine ────────────────────────────────────────────────────────

class Backtester:

    def __init__(
        self,
        symbol:       str,
        timeframe:    str,
        strategy:     Strategy = "Mixed",
        bars:         int      = 500,
        risk_percent: float    = 1.0,
        rr_ratio:     float    = 2.0,
        initial_balance: float = 10_000.0,
    ):
        self.symbol          = symbol
        self.timeframe       = timeframe
        self.strategy        = strategy
        self.bars            = bars
        self.risk_percent    = risk_percent
        self.rr_ratio        = rr_ratio
        self.initial_balance = initial_balance
        self.pip             = 0.0001 if "JPY" not in symbol else 0.01

    async def run(self) -> BacktestResult:
        from services.forex_data import fetch_ohlcv  # avoid circular import at module level
        raw    = await fetch_ohlcv(self.symbol, self.timeframe, self.bars)
        candles = [Candle(**c) for c in raw.get("candles", [])]

        if len(candles) < 50:
            result = BacktestResult(
                symbol=self.symbol, timeframe=self.timeframe,
                strategy=self.strategy, bars_used=len(candles),
                risk_percent=self.risk_percent, rr_ratio=self.rr_ratio,
            )
            return result

        return self._simulate(candles)

    def _simulate(self, candles: list[Candle]) -> BacktestResult:
        result = BacktestResult(
            symbol=self.symbol, timeframe=self.timeframe,
            strategy=self.strategy, bars_used=len(candles),
            risk_percent=self.risk_percent, rr_ratio=self.rr_ratio,
        )

        # Collect all potential entry zones upfront
        signals: list[dict] = []
        if self.strategy in ("FVG", "Mixed"):
            signals += _detect_fvg_signals(candles)
        if self.strategy in ("OrderBlock", "Mixed"):
            signals += _detect_ob_signals(candles)
        if self.strategy in ("Liquidity", "Mixed"):
            signals += _detect_liquidity_signals(candles)

        # Sort by bar index
        signals.sort(key=lambda s: s["bar"])

        # Build quick lookup: bar → signals that formed at this bar
        sig_map: dict[int, list[dict]] = {}
        for sig in signals:
            sig_map.setdefault(sig["bar"], []).append(sig)

        # Walk bars forward, simulating entries
        balance     = self.initial_balance
        open_trades: list[SimTrade] = []
        trade_id    = 0
        used_bars   = set()   # prevent re-entering same signal bar

        for i, candle in enumerate(candles):
            # 1. Check if any open trade hits SL or TP
            still_open = []
            for t in open_trades:
                closed = False
                if t.direction == "BUY":
                    if candle.low <= t.stop_loss:
                        t = self._close_trade(t, t.stop_loss, "LOSS", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100
                        closed = True
                    elif candle.high >= t.take_profit:
                        t = self._close_trade(t, t.take_profit, "WIN", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100
                        closed = True
                else:  # SELL
                    if candle.high >= t.stop_loss:
                        t = self._close_trade(t, t.stop_loss, "LOSS", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100
                        closed = True
                    elif candle.low <= t.take_profit:
                        t = self._close_trade(t, t.take_profit, "WIN", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100
                        closed = True
                if closed:
                    result.trades.append(t)
                else:
                    still_open.append(t)
            open_trades = still_open

            # 2. Only allow 1 open trade at a time (simple sizing)
            if open_trades:
                result.equity.append({"bar": i, "time": candle.time, "equity": round(balance, 2)})
                continue

            # 3. Check for entry signals on this bar
            for sig in sig_map.get(i, []):
                if i in used_bars:
                    continue
                trade = self._make_trade(trade_id, sig, i, candle, balance)
                if trade:
                    trade_id  += 1
                    used_bars.add(i)
                    open_trades.append(trade)
                    break   # one trade per bar

            result.equity.append({"bar": i, "time": candle.time, "equity": round(balance, 2)})

        # Force-close remaining open trades at last bar's close
        if open_trades and candles:
            last = candles[-1]
            for t in open_trades:
                t = self._close_trade(t, last.close, "OPEN", len(candles) - 1, last.time, balance)
                result.trades.append(t)

        result.compute_stats(self.pip)
        return result

    def _make_trade(
        self, trade_id: int, sig: dict, bar: int, candle: Candle, balance: float
    ) -> Optional[SimTrade]:
        sig_type = sig["type"]
        direction = "BUY"  if "_BULL" in sig_type or "_BULL" in sig_type else "SELL"
        if "BEAR" in sig_type:
            direction = "SELL"

        entry = sig.get("mid") or candle.close
        atr   = self._estimate_atr(bar)

        if direction == "BUY":
            sl = sig.get("bottom", entry - atr)
            tp = entry + (entry - sl) * self.rr_ratio
        else:
            sl = sig.get("top", entry + atr)
            tp = entry - (sl - entry) * self.rr_ratio

        sl_dist = abs(entry - sl)
        if sl_dist < 1e-7:
            return None

        # Risk sizing
        risk_amount = balance * self.risk_percent / 100
        pips_risk   = sl_dist / self.pip
        lot_size    = round(risk_amount / (pips_risk * self.pip * 100_000), 3)
        lot_size    = max(0.01, min(lot_size, 1.0))

        setup_label = {
            "FVG_BULL": "FVG↑", "FVG_BEAR": "FVG↓",
            "OB_BULL":  "OB↑",  "OB_BEAR":  "OB↓",
            "LIQ_BULL": "Liq↑", "LIQ_BEAR": "Liq↓",
        }.get(sig_type, sig_type)

        return SimTrade(
            id=trade_id, setup=setup_label, direction=direction,
            entry_bar=bar, entry_time=candle.time,
            entry_price=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            lot_size=lot_size,
        )

    def _close_trade(
        self, trade: SimTrade, exit_price: float, result: str,
        bar: int, time: str, balance: float
    ) -> SimTrade:
        trade.exit_bar   = bar
        trade.exit_time  = time
        trade.exit_price = round(exit_price, 5)
        trade.result     = result

        entry = trade.entry_price
        if trade.direction == "BUY":
            pips = (exit_price - entry) / self.pip
        else:
            pips = (entry - exit_price) / self.pip

        trade.pnl_pips  = round(pips, 1)
        pnl_usd         = pips * self.pip * trade.lot_size * 100_000
        trade.pnl_pct   = round(pnl_usd / max(balance, 1) * 100, 3)

        sl_dist = abs(entry - trade.stop_loss) / self.pip
        if sl_dist > 0:
            trade.rr_actual = round(abs(pips) / sl_dist * (1 if result == "WIN" else -1), 2)

        return trade

    def _estimate_atr(self, bar_idx: int) -> float:
        """Simple ATR estimate — returns a reasonable default by symbol."""
        defaults = {
            "EURUSD": 0.0012, "GBPUSD": 0.0015, "USDJPY": 0.15,
            "XAUUSD": 8.0,    "USDCHF": 0.0010, "AUDUSD": 0.0010,
        }
        return defaults.get(self.symbol, 0.0012)


# ── Async runner (called from FastAPI) ───────────────────────────────────────

async def run_backtest(
    symbol:          str,
    timeframe:       str   = "H1",
    strategy:        str   = "Mixed",
    bars:            int   = 500,
    risk_percent:    float = 1.0,
    rr_ratio:        float = 2.0,
    initial_balance: float = 10_000.0,
) -> BacktestResult:
    bt = Backtester(
        symbol=symbol, timeframe=timeframe, strategy=strategy,
        bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
        initial_balance=initial_balance,
    )
    return await bt.run()
