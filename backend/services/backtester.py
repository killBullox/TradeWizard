"""
backtester.py — Advanced ICT Strategy Backtesting Engine

Full ICT methodology:
- Market Structure: BOS / CHoCH
- HTF Bias: EMA50 + EMA200
- Premium / Discount zones (Fibonacci 50%)
- Valid FVGs with displacement, mitigation tracking
- Valid Order Blocks after BOS + displacement
- Equal Highs/Lows liquidity pools + sweep reversal
- Kill Zones: London Open (07-10 UTC), NY Open (12-15 UTC)
- Confluence scoring: minimum 2 tags required per signal
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Literal, Optional

import numpy as np

logger = logging.getLogger("backtester")

Strategy = Literal["FVG", "OrderBlock", "Liquidity", "Mixed"]


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Candle:
    time:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: int = 0


@dataclass
class PendingOrder:
    """Limit order waiting to be filled when price reaches entry_price."""
    id:          int
    setup:       str
    direction:   str
    signal_bar:  int       # bar where signal was detected
    entry_price: float
    stop_loss:   float
    take_profit: float
    lot_size:    float
    confluence:  list
    max_wait:    int = 20  # cancel after this many bars if not filled (20h for H1)


@dataclass
class SimTrade:
    id:          int
    setup:       str
    direction:   str
    entry_bar:   int
    entry_time:  str
    entry_price: float
    stop_loss:   float
    take_profit: float
    lot_size:    float = 0.01
    exit_bar:    Optional[int]   = None
    exit_time:   Optional[str]   = None
    exit_price:  Optional[float] = None
    result:      Optional[str]   = None
    pnl_pips:    Optional[float] = None
    pnl_pct:     Optional[float] = None
    pnl_usd:     Optional[float] = None
    rr_actual:   Optional[float] = None
    confluence:  Optional[list]  = None


@dataclass
class BacktestResult:
    symbol:        str
    timeframe:     str
    strategy:      str
    bars_used:     int
    risk_percent:  float
    rr_ratio:      float

    trades:        list[SimTrade] = field(default_factory=list)
    equity:        list[dict]     = field(default_factory=list)

    total_trades:    int   = 0
    wins:            int   = 0
    losses:          int   = 0
    win_rate:        float = 0.0
    total_pips:      float = 0.0
    total_return:    float = 0.0
    total_pnl_usd:   float = 0.0
    max_drawdown:    float = 0.0
    max_drawdown_usd:float = 0.0
    profit_factor:   float = 0.0
    avg_rr:          float = 0.0
    sharpe:          float = 0.0
    expectancy:      float = 0.0
    data_warning:    str   = ""

    def compute_stats(self, pip: float):
        closed = [t for t in self.trades if t.result and t.result != "OPEN"]
        self.total_trades = len(closed)
        self.wins   = sum(1 for t in closed if t.result == "WIN")
        self.losses = sum(1 for t in closed if t.result == "LOSS")
        self.win_rate = round(self.wins / self.total_trades * 100, 1) if self.total_trades else 0.0

        pips = [t.pnl_pips for t in closed if t.pnl_pips is not None]
        self.total_pips = round(sum(pips), 1)

        usd_vals = [t.pnl_usd for t in closed if t.pnl_usd is not None]
        self.total_pnl_usd = round(sum(usd_vals), 2)

        gross_profit = sum(p for p in pips if p > 0)
        gross_loss   = abs(sum(p for p in pips if p < 0))
        self.profit_factor = round(gross_profit / gross_loss, 2) if gross_loss else float('inf')
        self.expectancy    = round(sum(pips) / len(pips), 1) if pips else 0.0

        rets = [t.pnl_pct for t in closed if t.pnl_pct is not None]
        self.total_return = round(sum(rets), 2)

        if len(rets) > 1:
            sharpe_raw = np.mean(rets) / (np.std(rets) + 1e-9)
            self.sharpe = round(float(sharpe_raw) * math.sqrt(252), 2)

        if self.equity:
            eq   = [e["equity"] for e in self.equity]
            peak = eq[0]
            dd   = 0.0
            dd_usd = 0.0
            for v in eq:
                if v > peak:
                    peak = v
                dd     = max(dd,     (peak - v) / peak * 100)
                dd_usd = max(dd_usd, peak - v)
            self.max_drawdown     = round(dd, 2)
            self.max_drawdown_usd = round(dd_usd, 2)

        rrs = [t.rr_actual for t in closed if t.rr_actual is not None]
        self.avg_rr = round(sum(rrs) / len(rrs), 2) if rrs else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trades"] = [asdict(t) for t in self.trades]
        return d


# ── Advanced ICT Signal Analyzer ──────────────────────────────────────────────

class ICTAnalyzer:
    SWING_W         = 5
    DISP_MULT       = 0.5    # body ≥ 0.5×ATR
    MIN_FVG_ATR     = 0.15   # gap ≥ 0.15×ATR
    EQ_TOL          = 0.20
    MIN_CONFLUENCE  = 2
    BIAS_STABLE_N   = 1
    # ICT Kill Zones (UTC): Asian 00-03, London 07-10, NY 13-16
    KILL_ZONES      = [(0, 3), (7, 10), (13, 16)]
    MAX_HOLD_BARS   = 16     # force-close after 16 H1 bars

    def __init__(self, candles: list[Candle], symbol: str, timeframe: str, strategy: str = "Mixed"):
        self.candles  = candles
        self.symbol   = symbol
        self.tf       = timeframe
        self.strategy = strategy
        self.n        = len(candles)
        self.pip      = (0.01   if "JPY" in symbol else
                         1.0    if symbol in ("XAUUSD", "US30", "NAS100", "US500") else
                         0.0001)
        self._atr          = self._calc_atr()
        self._bias         = self._calc_bias()
        self._pdhl         = self._calc_pdhl()
        self._asian_ranges = self._calc_asian_ranges()
        self._day_bias_map = self._calc_day_bias_map()
        self._judas        = self._detect_judas()

    # ── ATR ─────────────────────────────────────────────────────────────────────
    def _calc_atr(self, p: int = 14) -> list[float]:
        out = []
        for i in range(self.n):
            hi, lo = self.candles[i].high, self.candles[i].low
            if i == 0:
                out.append(hi - lo)
                continue
            pc = self.candles[i - 1].close
            tr = max(hi - lo, abs(hi - pc), abs(lo - pc))
            out.append(out[-1] * (p - 1) / p + tr / p if i >= p else (out[-1] * i + tr) / (i + 1))
        return out

    def atr(self, i: int) -> float:
        v = self._atr[min(i, self.n - 1)] if self._atr else self.pip * 10
        return max(v, self.pip * 2)

    # ── HTF Bias: swing structure confirmed by EMA200 macro trend ────────────────
    def _calc_bias(self, lb: int = 40) -> list[str]:
        """
        Dual-layer bias:
        1. Local swing structure (HH/HL = bullish, LH/LL = bearish)
        2. EMA200 macro trend (price above = bullish, below = bearish)
        Both layers must agree → reduces false signals in counter-trend conditions.
        """
        # EMA200 for macro trend
        ema200: list[float] = []
        k = 2 / 201
        for c in self.candles:
            ema200.append(c.close * k + ema200[-1] * (1 - k) if ema200 else c.close)

        out = ["neutral"] * self.n
        for i in range(lb * 2, self.n):
            s = max(0, i - lb)
            sw_highs = [self.candles[j].high for j in self.sh(s, i + 1)]
            sw_lows  = [self.candles[j].low  for j in self.sl(s, i + 1)]
            if len(sw_highs) < 2 or len(sw_lows) < 2:
                continue

            hh = sw_highs[-1] > sw_highs[-2]
            hl = sw_lows[-1]  > sw_lows[-2]
            lh = sw_highs[-1] < sw_highs[-2]
            ll = sw_lows[-1]  < sw_lows[-2]

            if   hh and hl: local = "bullish"
            elif lh and ll: local = "bearish"
            elif hh or hl:  local = "bullish"
            elif lh or ll:  local = "bearish"
            else:           local = "neutral"

            # Macro filter: EMA200 must agree with local swing structure
            price  = self.candles[i].close
            macro  = "bullish" if price > ema200[i] else "bearish"
            out[i] = local if local == macro else "neutral"

        return out

    def bias(self, i: int) -> str:
        return self._bias[min(i, self.n - 1)]

    def bias_stable(self, i: int) -> bool:
        """Return True only if bias has been the same direction for BIAS_STABLE_N bars."""
        b = self.bias(i)
        if b == "neutral":
            return False
        start = max(0, i - self.BIAS_STABLE_N + 1)
        return all(self._bias[j] == b for j in range(start, i + 1))

    # ── Previous Day High/Low (IPDA reference levels) ───────────────────────────
    def _calc_pdhl(self) -> list:
        """Compute (prev_day_high, prev_day_low) for each bar. Returns list of tuples or None."""
        day_data: dict[str, tuple] = {}
        for c in self.candles:
            day = c.time[:10]
            if day not in day_data:
                day_data[day] = (c.high, c.low)
            else:
                ph, pl = day_data[day]
                day_data[day] = (max(ph, c.high), min(pl, c.low))
        sorted_days = sorted(day_data.keys())
        prev_map: dict[str, tuple] = {}
        for idx, d in enumerate(sorted_days):
            if idx > 0:
                prev_map[d] = day_data[sorted_days[idx - 1]]
        return [prev_map.get(c.time[:10]) for c in self.candles]

    def pdhl(self, i: int):
        return self._pdhl[i] if i < len(self._pdhl) else None

    def near_pdh(self, i: int) -> bool:
        """Price is within 0.5×ATR of previous day high."""
        v = self.pdhl(i)
        if not v:
            return False
        pdh, _ = v
        return abs(self.candles[i].close - pdh) <= self.atr(i) * 0.5

    def near_pdl(self, i: int) -> bool:
        """Price is within 0.5×ATR of previous day low."""
        v = self.pdhl(i)
        if not v:
            return False
        _, pdl = v
        return abs(self.candles[i].close - pdl) <= self.atr(i) * 0.5

    def pdl_swept(self, i: int) -> bool:
        """Turtle Soup / Judas: candle swept PDL wick but closed above it → long reversal."""
        v = self.pdhl(i)
        if not v:
            return False
        _, pdl = v
        c = self.candles[i]
        return c.low < pdl <= c.close

    def pdh_swept(self, i: int) -> bool:
        """Turtle Soup / Judas: candle swept PDH wick but closed below it → short reversal."""
        v = self.pdhl(i)
        if not v:
            return False
        pdh, _ = v
        c = self.candles[i]
        return c.high > pdh >= c.close

    def nearest_liq(self, i: int, direction: str, look: int = 80) -> Optional[float]:
        """
        Nearest liquidity pool (EQH, EQL, PDH, PDL) in the trade direction.
        Used for dynamic TP targeting — ICT: price is always drawn to the nearest pool.
        """
        price = self.candles[i].close
        candidates: list[float] = []

        v = self.pdhl(i)
        if v:
            pdh, pdl = v
            if direction == "BUY"  and pdh > price: candidates.append(pdh)
            if direction == "SELL" and pdl < price: candidates.append(pdl)

        s = max(0, i - look)
        if direction == "BUY":
            for j in self.sh(s, i):
                lv = self.candles[j].high
                if lv > price:
                    candidates.append(lv)
        else:
            for j in self.sl(s, i):
                lv = self.candles[j].low
                if lv < price:
                    candidates.append(lv)

        if not candidates:
            return None
        return min(candidates) if direction == "BUY" else max(candidates)

    def detect_breakers(self, obs: list[dict]) -> list[dict]:
        """
        ICT Breaker Blocks: a mitigated OB becomes a breaker in the opposite direction.
        OB_BULL that is fully violated → BREAK_BEAR (old support becomes resistance)
        OB_BEAR that is fully violated → BREAK_BULL (old resistance becomes support)
        """
        breakers = []
        for ob in obs:
            if ob.get("mitigated_at") is None:
                continue
            mit = ob["mitigated_at"]
            if ob["type"] == "OB_BULL":
                breakers.append({"formed_at": mit + 1, "type": "BREAK_BEAR",
                                  "top": ob["top"], "bottom": ob["bottom"],
                                  "mid": ob["mid"], "mitigated_at": None})
            else:
                breakers.append({"formed_at": mit + 1, "type": "BREAK_BULL",
                                  "top": ob["top"], "bottom": ob["bottom"],
                                  "mid": ob["mid"], "mitigated_at": None})
        return breakers

    # ── Power of 3: Asian Range ──────────────────────────────────────────────────
    def _calc_asian_ranges(self) -> dict:
        """Asian session high/low per calendar day (00:00–07:00 UTC)."""
        ranges: dict[str, dict] = {}
        for c in self.candles:
            try:
                dt  = datetime.fromisoformat(c.time.replace("Z", "+00:00"))
                day = dt.date().isoformat()
                if 0 <= dt.hour < 7:
                    if day not in ranges:
                        ranges[day] = {"high": c.high, "low": c.low}
                    else:
                        ranges[day]["high"] = max(ranges[day]["high"], c.high)
                        ranges[day]["low"]  = min(ranges[day]["low"],  c.low)
            except Exception:
                pass
        return ranges

    # ── Power of 3: Daily Bias (per-day, not per-bar) ────────────────────────────
    def _calc_day_bias_map(self) -> dict:
        """
        Per-day bias using EMA200 macro trend + previous day direction.
        Both must agree → bullish or bearish, else neutral.
        """
        ema200: list[float] = []
        k = 2.0 / 201.0
        for c in self.candles:
            ema200.append(c.close * k + ema200[-1] * (1 - k) if ema200 else c.close)

        day_ohlc: dict[str, dict] = {}
        for i, c in enumerate(self.candles):
            day = c.time[:10]
            if day not in day_ohlc:
                day_ohlc[day] = {"open": c.open, "close": c.close, "ema200": ema200[i]}
            else:
                day_ohlc[day]["close"] = c.close

        sorted_days = sorted(day_ohlc.keys())
        result: dict[str, str] = {}
        for idx, day in enumerate(sorted_days):
            d     = day_ohlc[day]
            macro = "bullish" if d["close"] > d["ema200"] else "bearish"
            if idx > 0:
                prev     = day_ohlc[sorted_days[idx - 1]]
                prev_dir = "bullish" if prev["close"] >= prev["open"] else "bearish"
            else:
                prev_dir = macro
            result[day] = macro if macro == prev_dir else "neutral"
        return result

    def day_bias(self, day: str) -> str:
        return self._day_bias_map.get(day, "neutral")

    # ── Power of 3: Judas Swing detection ────────────────────────────────────────
    def _detect_judas(self) -> dict:
        """
        Judas Swing (manipulation phase):
        - Bullish day → London (07-10 UTC) sweeps Asian LOW, closes back above → BUY
        - Bearish day → London (07-10 UTC) sweeps Asian HIGH, closes back below → SELL
        One Judas per day maximum. Returns {bar_index: direction}.
        """
        judas: dict[int, str] = {}
        done:  set[str]       = set()
        for i, c in enumerate(self.candles):
            try:
                dt  = datetime.fromisoformat(c.time.replace("Z", "+00:00"))
                day = dt.date().isoformat()
                if not (7 <= dt.hour < 11) or day in done:
                    continue
                ar   = self._asian_ranges.get(day)
                bias = self.day_bias(day)
                if not ar or bias == "neutral":
                    continue
                if bias == "bullish" and c.low < ar["low"] and c.close > ar["low"]:
                    judas[i] = "BUY";  done.add(day)
                elif bias == "bearish" and c.high > ar["high"] and c.close < ar["high"]:
                    judas[i] = "SELL"; done.add(day)
            except Exception:
                pass
        return judas

    # ── Kill zone ────────────────────────────────────────────────────────────────
    def in_kz(self, i: int) -> bool:
        if self.tf in ("D1", "W1"):
            return True
        try:
            dt = datetime.fromisoformat(self.candles[i].time.replace("Z", "+00:00"))
            h = dt.hour
            return any(s <= h < e for s, e in self.KILL_ZONES)
        except Exception:
            return True

    # ── Premium/Discount ─────────────────────────────────────────────────────────
    def zone(self, i: int, lb: int = 100) -> str:
        s = max(0, i - lb)
        hi = max(c.high for c in self.candles[s:i + 1])
        lo = min(c.low  for c in self.candles[s:i + 1])
        rng = hi - lo
        if rng < self.pip:
            return "neutral"
        pos = (self.candles[i].close - lo) / rng
        if pos < 0.40:  return "discount"
        if pos > 0.60:  return "premium"
        return "equilibrium"

    # ── Swings ───────────────────────────────────────────────────────────────────
    def sh(self, s: int, e: int, w: int = None) -> list[int]:
        w = w or self.SWING_W
        out = []
        for i in range(s + w, min(e, self.n) - w):
            h = self.candles[i].high
            if (all(self.candles[j].high <= h for j in range(i - w, i)) and
                    all(self.candles[j].high <= h for j in range(i + 1, i + w + 1))):
                out.append(i)
        return out

    def sl(self, s: int, e: int, w: int = None) -> list[int]:
        w = w or self.SWING_W
        out = []
        for i in range(s + w, min(e, self.n) - w):
            lo = self.candles[i].low
            if (all(self.candles[j].low >= lo for j in range(i - w, i)) and
                    all(self.candles[j].low >= lo for j in range(i + 1, i + w + 1))):
                out.append(i)
        return out

    # ── Displacement ──────────────────────────────────────────────────────────────
    def is_disp(self, i: int) -> bool:
        c = self.candles[i]
        body = abs(c.close - c.open)
        rng  = c.high - c.low
        return body >= self.atr(i) * self.DISP_MULT and body / max(rng, self.pip) > 0.55

    # ── Market Structure (BOS) ───────────────────────────────────────────────────
    def market_structure(self, lb: int = 80) -> list[dict]:
        events = []
        for i in range(lb, self.n):
            s = max(0, i - lb)
            highs = self.sh(s, i)
            lows  = self.sl(s, i)
            c = self.candles[i]

            if highs:
                idx = max(highs, key=lambda x: self.candles[x].high)
                lv  = self.candles[idx].high
                if c.close > lv:
                    events.append({"bar": i, "type": "BOS_BULL", "level": lv, "swing_bar": idx})

            if lows:
                idx = min(lows, key=lambda x: self.candles[x].low)
                lv  = self.candles[idx].low
                if c.close < lv:
                    events.append({"bar": i, "type": "BOS_BEAR", "level": lv, "swing_bar": idx})
        return events

    # ── FVGs ─────────────────────────────────────────────────────────────────────
    def detect_fvgs(self) -> list[dict]:
        fvgs = []
        for i in range(1, self.n - 1):
            c0, c1, c2 = self.candles[i - 1], self.candles[i], self.candles[i + 1]
            a = self.atr(i)
            if c0.high < c2.low and (c2.low - c0.high) >= a * self.MIN_FVG_ATR and self.is_disp(i):
                fvgs.append({"formed_at": i + 1, "type": "FVG_BULL",
                             "top": c2.low, "bottom": c0.high,
                             "mid": (c2.low + c0.high) / 2, "mitigated_at": None})
            elif c0.low > c2.high and (c0.low - c2.high) >= a * self.MIN_FVG_ATR and self.is_disp(i):
                fvgs.append({"formed_at": i + 1, "type": "FVG_BEAR",
                             "top": c0.low, "bottom": c2.high,
                             "mid": (c0.low + c2.high) / 2, "mitigated_at": None})
        for fvg in fvgs:
            for j in range(fvg["formed_at"] + 1, self.n):
                c = self.candles[j]
                if fvg["type"] == "FVG_BULL" and c.low <= fvg["mid"]:
                    fvg["mitigated_at"] = j; break
                if fvg["type"] == "FVG_BEAR" and c.high >= fvg["mid"]:
                    fvg["mitigated_at"] = j; break
        return fvgs

    # ── Order Blocks ─────────────────────────────────────────────────────────────
    def detect_obs(self, structure: list[dict]) -> list[dict]:
        obs = []
        for ev in structure:
            bos_bar   = ev["bar"]
            swing_bar = ev.get("swing_bar", bos_bar - 1)
            s = max(0, swing_bar - 30)
            if ev["type"] == "BOS_BULL":
                for j in range(swing_bar, s, -1):
                    c = self.candles[j]
                    if c.close < c.open:
                        if any(self.is_disp(k) for k in range(j + 1, min(j + 6, bos_bar + 1))):
                            obs.append({"formed_at": bos_bar, "type": "OB_BULL", "bar": j,
                                        "top": c.high, "bottom": c.low,
                                        "mid": (c.high + c.low) / 2, "mitigated_at": None})
                        break
            elif ev["type"] == "BOS_BEAR":
                for j in range(swing_bar, s, -1):
                    c = self.candles[j]
                    if c.close > c.open:
                        if any(self.is_disp(k) for k in range(j + 1, min(j + 6, bos_bar + 1))):
                            obs.append({"formed_at": bos_bar, "type": "OB_BEAR", "bar": j,
                                        "top": c.high, "bottom": c.low,
                                        "mid": (c.high + c.low) / 2, "mitigated_at": None})
                        break
        for ob in obs:
            for j in range(ob["formed_at"] + 1, self.n):
                c = self.candles[j]
                if ob["type"] == "OB_BULL" and c.low < ob["bottom"]:
                    ob["mitigated_at"] = j; break
                if ob["type"] == "OB_BEAR" and c.high > ob["top"]:
                    ob["mitigated_at"] = j; break
        return obs

    # ── Liquidity Sweeps ─────────────────────────────────────────────────────────
    def detect_sweeps(self) -> list[dict]:
        sh_idx = self.sh(0, self.n - 5)
        sl_idx = self.sl(0, self.n - 5)
        pools  = []
        for i in range(len(sh_idx)):
            for j in range(i + 1, len(sh_idx)):
                h1 = self.candles[sh_idx[i]].high
                h2 = self.candles[sh_idx[j]].high
                if abs(h1 - h2) <= self.atr(sh_idx[j]) * self.EQ_TOL:
                    pools.append({"type": "BSL", "level": max(h1, h2), "ref_bar": sh_idx[j]})
        for i in range(len(sl_idx)):
            for j in range(i + 1, len(sl_idx)):
                l1 = self.candles[sl_idx[i]].low
                l2 = self.candles[sl_idx[j]].low
                if abs(l1 - l2) <= self.atr(sl_idx[j]) * self.EQ_TOL:
                    pools.append({"type": "SSL", "level": min(l1, l2), "ref_bar": sl_idx[j]})
        sweeps = []
        for pool in pools:
            for i in range(pool["ref_bar"] + 1, self.n - 1):
                c = self.candles[i]
                if pool["type"] == "BSL" and c.high > pool["level"] and c.close < pool["level"]:
                    sweeps.append({"bar": i, "type": "LIQ_BEAR", "level": pool["level"],
                                   "top": c.high, "bottom": c.low, "mid": c.close}); break
                if pool["type"] == "SSL" and c.low < pool["level"] and c.close > pool["level"]:
                    sweeps.append({"bar": i, "type": "LIQ_BULL", "level": pool["level"],
                                   "top": c.high, "bottom": c.low, "mid": c.close}); break
        return sweeps

    # ── Build final entry signals ─────────────────────────────────────────────────
    def build_signals(self) -> list[dict]:
        """
        ICT Power of 3 — correct sequence:
        1. Daily bias: EMA200 + previous day direction must agree
        2. Asian range (00-07 UTC): defines accumulation zone
        3. Judas Swing (London 07-10 UTC): price sweeps Asian range AGAINST bias,
           then closes back inside → manipulation phase confirmed
        4. AFTER Judas: first FVG / OB / Breaker in bias direction = distribution entry
        5. Liquidity sweeps that ARE the Judas (sweep + close-back = same candle) → market entry

        One trade per calendar day maximum.
        """
        structure = self.market_structure()
        fvgs      = self.detect_fvgs()         if self.strategy in ("FVG",        "Mixed") else []
        obs       = self.detect_obs(structure) if self.strategy in ("OrderBlock", "Mixed") else []
        breakers  = self.detect_breakers(obs)  if self.strategy in ("OrderBlock", "Mixed") else []
        sweeps    = self.detect_sweeps()       if self.strategy in ("Liquidity",  "Mixed") else []

        # Index entry vehicles by bar for fast lookup
        fvg_at:  dict[int, list] = {}
        ob_at:   dict[int, list] = {}
        brk_at:  dict[int, list] = {}
        for f in fvgs:    fvg_at.setdefault(f["formed_at"], []).append(f)
        for o in obs:     ob_at.setdefault(o["formed_at"],  []).append(o)
        for b in breakers: brk_at.setdefault(b["formed_at"], []).append(b)

        signals:     list[dict] = []
        traded_days: set[str]   = set()   # max one trade per day
        ENTRY_WINDOW = 20                  # bars to search after Judas

        # ── Phase 1: Judas Swing → find first valid FVG/OB/Breaker after it ──────
        for judas_bar, direction in sorted(self._judas.items()):
            try:
                day = self.candles[judas_bar].time[:10]
            except Exception:
                continue
            if day in traded_days:
                continue

            for i in range(judas_bar + 1, min(judas_bar + ENTRY_WINDOW + 1, self.n)):
                c = self.candles[i]
                # Must still be in a kill zone
                if not self.in_kz(i):
                    continue
                z    = self.zone(i)
                tags = ["JUDAS", "KILLZONE"]

                # Priority 1: FVG in bias direction
                for fvg in fvg_at.get(i, []):
                    if direction == "BUY" and fvg["type"] == "FVG_BULL":
                        t = tags + ["FVG"]
                        if z == "discount":   t.append("DISCOUNT")
                        if self.near_pdl(i):  t.append("PDL")
                        signals.append({"bar": i, "type": "FVG_BULL",
                                        "top": fvg["top"], "bottom": fvg["bottom"],
                                        "mid": fvg["mid"], "confluence": t,
                                        "expires_at": fvg["mitigated_at"]})
                        traded_days.add(day); break
                    elif direction == "SELL" and fvg["type"] == "FVG_BEAR":
                        t = tags + ["FVG"]
                        if z == "premium":    t.append("PREMIUM")
                        if self.near_pdh(i):  t.append("PDH")
                        signals.append({"bar": i, "type": "FVG_BEAR",
                                        "top": fvg["top"], "bottom": fvg["bottom"],
                                        "mid": fvg["mid"], "confluence": t,
                                        "expires_at": fvg["mitigated_at"]})
                        traded_days.add(day); break
                if day in traded_days: break

                # Priority 2: Order Block
                for ob in ob_at.get(i, []):
                    if direction == "BUY" and ob["type"] == "OB_BULL":
                        t = tags + ["OB"]
                        if z == "discount":   t.append("DISCOUNT")
                        if self.near_pdl(i):  t.append("PDL")
                        signals.append({"bar": i, "type": "OB_BULL",
                                        "top": ob["top"], "bottom": ob["bottom"],
                                        "mid": ob["mid"], "confluence": t,
                                        "expires_at": ob["mitigated_at"]})
                        traded_days.add(day); break
                    elif direction == "SELL" and ob["type"] == "OB_BEAR":
                        t = tags + ["OB"]
                        if z == "premium":    t.append("PREMIUM")
                        if self.near_pdh(i):  t.append("PDH")
                        signals.append({"bar": i, "type": "OB_BEAR",
                                        "top": ob["top"], "bottom": ob["bottom"],
                                        "mid": ob["mid"], "confluence": t,
                                        "expires_at": ob["mitigated_at"]})
                        traded_days.add(day); break
                if day in traded_days: break

                # Priority 3: Breaker Block
                for brk in brk_at.get(i, []):
                    if direction == "BUY" and brk["type"] == "BREAK_BULL":
                        t = tags + ["BREAKER"]
                        if z == "discount":  t.append("DISCOUNT")
                        signals.append({"bar": i, "type": "BREAK_BULL",
                                        "top": brk["top"], "bottom": brk["bottom"],
                                        "mid": brk["mid"], "confluence": t})
                        traded_days.add(day); break
                    elif direction == "SELL" and brk["type"] == "BREAK_BEAR":
                        t = tags + ["BREAKER"]
                        if z == "premium":   t.append("PREMIUM")
                        signals.append({"bar": i, "type": "BREAK_BEAR",
                                        "top": brk["top"], "bottom": brk["bottom"],
                                        "mid": brk["mid"], "confluence": t})
                        traded_days.add(day); break
                if day in traded_days: break

        # ── Phase 2: Liquidity sweeps that ARE the Judas (market entry) ──────────
        for sw in sweeps:
            i = sw["bar"]
            if not self.in_kz(i):
                continue
            try:
                day = self.candles[i].time[:10]
            except Exception:
                continue
            if day in traded_days:
                continue
            bias = self.day_bias(day)
            if bias == "neutral":
                continue
            tags = ["SWEEP", "KILLZONE", "JUDAS"]
            if sw["type"] == "LIQ_BULL" and bias == "bullish":
                if self.pdl_swept(i): tags.append("PDL_SWEEP")
                signals.append({"bar": i, "type": "LIQ_BULL",
                                "top": sw["top"], "bottom": sw["bottom"],
                                "mid": sw["mid"], "confluence": tags})
                traded_days.add(day)
            elif sw["type"] == "LIQ_BEAR" and bias == "bearish":
                if self.pdh_swept(i): tags.append("PDH_SWEEP")
                signals.append({"bar": i, "type": "LIQ_BEAR",
                                "top": sw["top"], "bottom": sw["bottom"],
                                "mid": sw["mid"], "confluence": tags})
                traded_days.add(day)

        signals.sort(key=lambda s: s["bar"])
        return signals


# ── Backtesting engine ────────────────────────────────────────────────────────

class Backtester:
    def __init__(self, symbol, timeframe, strategy="Mixed", bars=500,
                 risk_percent=1.0, rr_ratio=2.0, initial_balance=10_000.0,
                 max_risk_usd=None, enabled_setups=None,
                 oanda_api_key: str = "", oanda_practice: bool = True,
                 mt5_bridge_url: str = ""):
        self.symbol          = symbol
        self.timeframe       = timeframe
        self.strategy        = strategy
        self.bars            = bars
        self.risk_percent    = risk_percent
        self.rr_ratio        = rr_ratio
        self.initial_balance = initial_balance
        self.max_risk_usd    = max_risk_usd
        self.enabled_setups  = set(enabled_setups) if enabled_setups else None
        self.mt5_bridge_url  = mt5_bridge_url or os.getenv("MT5_BRIDGE_URL", "")
        self.oanda_api_key   = oanda_api_key or os.getenv("OANDA_API_KEY", "")
        self.oanda_practice  = oanda_practice
        self.m1_index: dict[str, list[dict]] = {}   # hour_key → [m1 candles]

        self.pip             = (0.01 if "JPY" in symbol else
                                1.0  if symbol in ("XAUUSD","US30","NAS100","US500") else
                                0.0001)
        _pip_val_map = {
            "XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
            "USDJPY": 6.5,  "EURJPY": 6.5,  "GBPJPY": 6.5,  "AUDJPY": 6.5,
            "CHFJPY": 6.5,  "CADJPY": 6.5,  "NZDJPY": 6.5,
            "USDCHF": 11.0, "EURCHF": 11.0, "GBPCHF": 11.0,
            "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25,
        }
        self.pip_value = _pip_val_map.get(symbol, 10.0)

    async def run(self) -> BacktestResult:
        from services.oanda_data import build_m1_index

        # ── 1. Fetch H1 candles — MT5 bridge first, then OANDA, then yfinance ──
        if self.mt5_bridge_url:
            from services.mt5_data import fetch_ohlcv as _mt5_fetch
            raw = await _mt5_fetch(self.symbol, self.timeframe, self.bars,
                                   bridge_url=self.mt5_bridge_url)
        else:
            from services.oanda_data import fetch_ohlcv as _oanda_fetch
            raw = await _oanda_fetch(self.symbol, self.timeframe, self.bars,
                                     api_key=self.oanda_api_key,
                                     practice=self.oanda_practice)

        candles = [Candle(**c) for c in raw.get("candles", [])]
        if len(candles) < 50:
            return BacktestResult(symbol=self.symbol, timeframe=self.timeframe,
                                  strategy=self.strategy, bars_used=len(candles),
                                  risk_percent=self.risk_percent, rr_ratio=self.rr_ratio)

        # ── 2. Fetch M1 for precise intra-candle timing ────────────────────────
        m1_source = None
        try:
            first_dt = datetime.fromisoformat(candles[0].time)
            last_dt  = datetime.fromisoformat(candles[-1].time) + timedelta(hours=1)

            if self.mt5_bridge_url:
                from services.mt5_data import fetch_m1_for_period as _m1_fetch
                m1_raw = await _m1_fetch(self.symbol, first_dt, last_dt,
                                         bridge_url=self.mt5_bridge_url)
                m1_source = "MT5"
            elif self.oanda_api_key:
                from services.oanda_data import fetch_m1_for_period as _m1_fetch
                m1_raw = await _m1_fetch(self.symbol, first_dt, last_dt,
                                         api_key=self.oanda_api_key,
                                         practice=self.oanda_practice)
                m1_source = "OANDA"
            else:
                m1_raw = []

            if m1_raw:
                self.m1_index = build_m1_index(m1_raw)
                logger.info("M1 index: %d hour buckets from %s for %s",
                            len(self.m1_index), m1_source, self.symbol)
            else:
                logger.warning("M1 data empty from %s — timestamps will be H1 resolution", m1_source or "no source")
        except Exception as exc:
            logger.warning("M1 fetch failed (%s): %s", m1_source, exc)

        result = self._simulate(candles)

        # ── 3. Set data_warning if no precise timestamps ───────────────────────
        if not self.m1_index:
            if not self.mt5_bridge_url and not self.oanda_api_key:
                result.data_warning = (
                    "⚠️ Nessuna sorgente dati M1 configurata. "
                    "I timestamp di entry/exit mostrano solo l'inizio dell'ora H1, non il momento preciso. "
                    "Configura MT5 Bridge URL (o OANDA API Key) nei Settings per timestamps reali al minuto."
                )
            else:
                result.data_warning = (
                    f"⚠️ Dati M1 non disponibili da {m1_source or 'sorgente configurata'}. "
                    "I timestamp mostrano l'inizio dell'ora H1. "
                    "Verifica che MT5 Bridge sia attivo e raggiungibile."
                )

        return result

    def _simulate(self, candles: list[Candle]) -> BacktestResult:
        result   = BacktestResult(symbol=self.symbol, timeframe=self.timeframe,
                                  strategy=self.strategy, bars_used=len(candles),
                                  risk_percent=self.risk_percent, rr_ratio=self.rr_ratio)
        analyzer = ICTAnalyzer(candles, self.symbol, self.timeframe, self.strategy)
        signals  = analyzer.build_signals()
        if self.enabled_setups:
            signals = [s for s in signals if s["type"] in self.enabled_setups]
        sig_map: dict[int, list[dict]] = {}
        for sig in signals:
            sig_map.setdefault(sig["bar"], []).append(sig)

        balance      = self.initial_balance
        open_trades: list[SimTrade]    = []
        pending:     list[PendingOrder] = []
        trade_id     = 0
        used_bars: set = set()

        for i, candle in enumerate(candles):
            # ── 1. Check open trades for SL / TP ──────────────────────────
            still_open = []
            for t in open_trades:
                closed = False
                if t.direction == "BUY":
                    if candle.low <= t.stop_loss:
                        t = self._close(t, t.stop_loss, "LOSS", i, candle.time, balance, candle)
                        balance += balance * t.pnl_pct / 100; closed = True
                    elif candle.high >= t.take_profit:
                        t = self._close(t, t.take_profit, "WIN", i, candle.time, balance, candle)
                        balance += balance * t.pnl_pct / 100; closed = True
                else:
                    if candle.high >= t.stop_loss:
                        t = self._close(t, t.stop_loss, "LOSS", i, candle.time, balance, candle)
                        balance += balance * t.pnl_pct / 100; closed = True
                    elif candle.low <= t.take_profit:
                        t = self._close(t, t.take_profit, "WIN", i, candle.time, balance, candle)
                        balance += balance * t.pnl_pct / 100; closed = True
                if not closed and (i - t.entry_bar) >= analyzer.MAX_HOLD_BARS:
                    # Force-close at market after max hold time
                    t = self._close(t, candle.close, "LOSS", i, candle.time, balance, candle)
                    balance += balance * t.pnl_pct / 100; closed = True
                if closed:
                    result.trades.append(t)
                else:
                    still_open.append(t)
            open_trades = still_open

            # ── 2. Try to fill pending limit orders ────────────────────────
            if not open_trades:
                still_pending = []
                for order in pending:
                    bars_waiting = i - order.signal_bar
                    if bars_waiting > order.max_wait:
                        continue  # expired — discard
                    # Fill if current candle's range includes entry price
                    filled = (
                        (order.direction == "BUY"  and candle.low  <= order.entry_price <= candle.high) or
                        (order.direction == "SELL" and candle.low  <= order.entry_price <= candle.high)
                    )
                    if filled and not open_trades:
                        trade = SimTrade(
                            id=order.id, setup=order.setup, direction=order.direction,
                            entry_bar=i, entry_time=self._intrabar_time(candle.time, order.entry_price, candle),
                            entry_price=order.entry_price,
                            stop_loss=order.stop_loss, take_profit=order.take_profit,
                            lot_size=order.lot_size, confluence=order.confluence,
                        )
                        open_trades.append(trade)
                    else:
                        still_pending.append(order)
                pending = still_pending

            # ── 3. Detect new signals ─────────────────────────────────────
            # Liq sweeps = market entry (reversal happens at signal bar)
            # FVG / OB = limit order (wait for retracement to the level)
            if not open_trades and not pending:
                for sig in sig_map.get(i, []):
                    if i in used_bars:
                        continue
                    sig_type = sig.get("type", "")
                    is_liq = "LIQ" in sig_type
                    if is_liq:
                        # Market entry: open trade immediately at candle close
                        trade = self._make_market_trade(trade_id, sig, i, candle, balance, analyzer)
                        if trade:
                            trade_id += 1; used_bars.add(i)
                            open_trades.append(trade); break
                    else:
                        # Limit entry: wait for price to reach entry level
                        order = self._make_pending(trade_id, sig, i, candle, balance, analyzer)
                        if order:
                            trade_id += 1; used_bars.add(i)
                            pending.append(order); break

            result.equity.append({"bar": i, "time": candle.time, "equity": round(balance, 2)})

        if open_trades and candles:
            last = candles[-1]
            for t in open_trades:
                t = self._close(t, last.close, "OPEN", len(candles)-1, last.time, balance, last)
                result.trades.append(t)
        # Pending orders at end of simulation are simply discarded (never filled)

        result.compute_stats(self.pip)
        return result

    def _make_market_trade(self, trade_id, sig, bar, candle, balance, analyzer) -> Optional[SimTrade]:
        """Market entry at signal bar close (used for Liquidity sweep signals)."""
        order = self._make_pending(trade_id, sig, bar, candle, balance, analyzer)
        if not order:
            return None
        return SimTrade(
            id=order.id, setup=order.setup, direction=order.direction,
            entry_bar=bar, entry_time=self._intrabar_time(candle.time, order.entry_price, candle),
            entry_price=order.entry_price,
            stop_loss=order.stop_loss, take_profit=order.take_profit,
            lot_size=order.lot_size, confluence=order.confluence,
        )

    def _make_pending(self, trade_id, sig, bar, candle, balance, analyzer) -> Optional[PendingOrder]:
        """Create a pending limit order from a signal. Fills only when price reaches entry_price."""
        sig_type  = sig["type"]
        direction = "SELL" if "BEAR" in sig_type else "BUY"
        atr       = analyzer.atr(bar)

        # ICT OTE: entry at 70.5% retracement of the FVG/OB zone (optimal trade entry)
        top    = sig.get("top",    candle.close)
        bottom = sig.get("bottom", candle.close)
        rng    = top - bottom
        if rng < self.pip:
            return None
        if direction == "BUY":
            # 70.5% retracement from top down into the gap = discount entry
            entry = top - rng * 0.705
        else:
            # 70.5% retracement from bottom up into the gap = premium entry
            entry = bottom + rng * 0.705

        if direction == "BUY":
            # SL: just below the structural low (zone bottom) with small ATR buffer
            sl = bottom - atr * 0.2
            tp = entry + (entry - sl) * self.rr_ratio
        else:
            # SL: just above the structural high (zone top) with small ATR buffer
            sl = top + atr * 0.2
            tp = entry - (sl - entry) * self.rr_ratio

        sl_dist = abs(entry - sl)
        if sl_dist < self.pip:
            return None

        # Risk amount:
        # - max_risk_usd set → use it as the exact dollar amount to risk
        # - only risk_percent set → percentage of current balance
        # - both set → max_risk_usd wins (it IS the target, not just a cap)
        if self.max_risk_usd and self.max_risk_usd > 0:
            risk_amount = self.max_risk_usd
        else:
            risk_amount = balance * self.risk_percent / 100
        pips_risk   = sl_dist / self.pip
        lot_size    = round(risk_amount / (pips_risk * self.pip_value), 3)
        lot_size    = max(0.001, min(lot_size, 100.0))

        label = {"FVG_BULL":"FVG↑","FVG_BEAR":"FVG↓",
                 "OB_BULL":"OB↑","OB_BEAR":"OB↓",
                 "LIQ_BULL":"Liq↑","LIQ_BEAR":"Liq↓",
                 "BREAK_BULL":"BRK↑","BREAK_BEAR":"BRK↓"}.get(sig_type, sig_type)

        # max_wait: use expires_at from signal (FVG mitigated) or 48 bars
        expires_at = sig.get("expires_at")
        max_wait = max(1, (expires_at - bar)) if expires_at else 48

        return PendingOrder(id=trade_id, setup=label, direction=direction,
                            signal_bar=bar, entry_price=round(entry, 5),
                            stop_loss=round(sl, 5), take_profit=round(tp, 5),
                            lot_size=lot_size, confluence=sig.get("confluence", []),
                            max_wait=max_wait)

    def _intrabar_time(self, candle_time: str, price: float, candle,
                       candle_secs: int = 3600) -> str:
        """
        Return the precise M1 timestamp when `price` was touched inside a candle.
        If M1 data is not available, returns the H1 candle open time as-is (no estimation).
        """
        hour_key = candle_time[:13]   # "2024-01-15T14"
        m1_list  = self.m1_index.get(hour_key, [])
        if m1_list:
            for m1 in m1_list:
                if m1["low"] <= price <= m1["high"]:
                    return m1["time"]
            # Price not found in any M1 bar — use closest by price distance
            closest = min(m1_list, key=lambda m: min(abs(price - m["low"]), abs(price - m["high"])))
            return closest["time"]

        # No M1 data — return candle open time (H1 resolution, no estimates)
        return candle_time

    def _close(self, trade, exit_price, result, bar, time, balance, candle=None) -> SimTrade:
        trade.exit_bar   = bar
        trade.exit_time  = self._intrabar_time(time, exit_price, candle) if candle else time
        trade.exit_price = round(exit_price, 5)
        trade.result     = result
        entry = trade.entry_price
        pips  = ((exit_price - entry) if trade.direction == "BUY" else (entry - exit_price)) / self.pip
        trade.pnl_pips = round(pips, 1)
        pnl_usd        = pips * self.pip_value * trade.lot_size
        trade.pnl_usd  = round(pnl_usd, 2)
        trade.pnl_pct  = round(pnl_usd / max(balance, 1) * 100, 3)
        sl_dist = abs(entry - trade.stop_loss) / self.pip
        if sl_dist > 0:
            trade.rr_actual = round(abs(pips) / sl_dist * (1 if result == "WIN" else -1), 2)
        return trade


# ── Async runner ──────────────────────────────────────────────────────────────

async def run_backtest(symbol, timeframe="H1", strategy="Mixed",
                       bars=500, risk_percent=1.0, rr_ratio=2.0,
                       initial_balance=10_000.0, max_risk_usd=None,
                       enabled_setups=None,
                       oanda_api_key: str = "", oanda_practice: bool = True,
                       mt5_bridge_url: str = "") -> BacktestResult:
    return await Backtester(
        symbol=symbol, timeframe=timeframe, strategy=strategy,
        bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
        initial_balance=initial_balance, max_risk_usd=max_risk_usd,
        enabled_setups=enabled_setups,
        oanda_api_key=oanda_api_key, oanda_practice=oanda_practice,
        mt5_bridge_url=mt5_bridge_url,
    ).run()
