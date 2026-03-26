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

    total_trades:  int   = 0
    wins:          int   = 0
    losses:        int   = 0
    win_rate:      float = 0.0
    total_pips:    float = 0.0
    total_return:  float = 0.0
    max_drawdown:  float = 0.0
    profit_factor: float = 0.0
    avg_rr:        float = 0.0
    sharpe:        float = 0.0
    expectancy:    float = 0.0

    def compute_stats(self, pip: float):
        closed = [t for t in self.trades if t.result and t.result != "OPEN"]
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

        if self.equity:
            eq   = [e["equity"] for e in self.equity]
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


# ── Advanced ICT Signal Analyzer ──────────────────────────────────────────────

class ICTAnalyzer:
    SWING_W         = 5
    DISP_MULT       = 1.3
    MIN_FVG_ATR     = 0.25
    EQ_TOL          = 0.20
    MIN_CONFLUENCE  = 2
    KILL_ZONES      = [(7, 10), (12, 15), (15, 17)]

    def __init__(self, candles: list[Candle], symbol: str, timeframe: str, strategy: str = "Mixed"):
        self.candles  = candles
        self.symbol   = symbol
        self.tf       = timeframe
        self.strategy = strategy
        self.n        = len(candles)
        self.pip      = (0.01   if "JPY" in symbol else
                         1.0    if symbol in ("XAUUSD", "US30", "NAS100", "US500") else
                         0.0001)
        self._atr   = self._calc_atr()
        self._bias  = self._calc_bias()

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

    # ── HTF Bias ────────────────────────────────────────────────────────────────
    def _calc_bias(self) -> list[str]:
        e50  = [self.candles[0].close] * self.n
        e200 = [self.candles[0].close] * self.n
        k50, k200 = 2 / 51, 2 / 201
        for i in range(1, self.n):
            c = self.candles[i].close
            e50[i]  = c * k50  + e50[i - 1]  * (1 - k50)
            e200[i] = c * k200 + e200[i - 1] * (1 - k200)
        out = []
        for i in range(self.n):
            c = self.candles[i].close
            if c > e50[i] and e50[i] > e200[i]:
                out.append("bullish")
            elif c < e50[i] and e50[i] < e200[i]:
                out.append("bearish")
            else:
                out.append("neutral")
        return out

    def bias(self, i: int) -> str:
        return self._bias[min(i, self.n - 1)]

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
        if pos < 0.45:  return "discount"
        if pos > 0.55:  return "premium"
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
        structure = self.market_structure()
        fvgs   = self.detect_fvgs()   if self.strategy in ("FVG",        "Mixed") else []
        obs    = self.detect_obs(structure) if self.strategy in ("OrderBlock", "Mixed") else []
        sweeps = self.detect_sweeps() if self.strategy in ("Liquidity",  "Mixed") else []

        signals: list[dict] = []

        for fvg in fvgs:
            formed  = fvg["formed_at"]
            max_bar = fvg["mitigated_at"] or self.n
            for i in range(formed + 1, min(max_bar, self.n)):
                c = self.candles[i]; b = self.bias(i); z = self.zone(i)
                tags = ["FVG"]
                if fvg["type"] == "FVG_BULL":
                    if not (c.low <= fvg["top"] and c.low >= fvg["bottom"]): continue
                    if b == "bullish":  tags.append("BIAS")
                    if z == "discount": tags.append("DISCOUNT")
                    if self.in_kz(i):  tags.append("KILLZONE")
                    if len(tags) >= self.MIN_CONFLUENCE:
                        signals.append({"bar": i, "type": "FVG_BULL",
                                        "top": fvg["top"], "bottom": fvg["bottom"],
                                        "mid": fvg["mid"], "confluence": tags}); break
                elif fvg["type"] == "FVG_BEAR":
                    if not (c.high >= fvg["bottom"] and c.high <= fvg["top"]): continue
                    if b == "bearish": tags.append("BIAS")
                    if z == "premium": tags.append("PREMIUM")
                    if self.in_kz(i): tags.append("KILLZONE")
                    if len(tags) >= self.MIN_CONFLUENCE:
                        signals.append({"bar": i, "type": "FVG_BEAR",
                                        "top": fvg["top"], "bottom": fvg["bottom"],
                                        "mid": fvg["mid"], "confluence": tags}); break

        for ob in obs:
            formed  = ob["formed_at"]
            max_bar = ob["mitigated_at"] or self.n
            for i in range(formed + 1, min(max_bar, self.n)):
                c = self.candles[i]; b = self.bias(i); z = self.zone(i)
                tags = ["OB"]
                if ob["type"] == "OB_BULL":
                    if not (c.low <= ob["top"] and c.high >= ob["bottom"]): continue
                    if b == "bullish":  tags.append("BIAS")
                    if z == "discount": tags.append("DISCOUNT")
                    if self.in_kz(i):  tags.append("KILLZONE")
                    if len(tags) >= self.MIN_CONFLUENCE:
                        signals.append({"bar": i, "type": "OB_BULL",
                                        "top": ob["top"], "bottom": ob["bottom"],
                                        "mid": ob["mid"], "confluence": tags}); break
                elif ob["type"] == "OB_BEAR":
                    if not (c.high >= ob["bottom"] and c.low <= ob["top"]): continue
                    if b == "bearish": tags.append("BIAS")
                    if z == "premium": tags.append("PREMIUM")
                    if self.in_kz(i): tags.append("KILLZONE")
                    if len(tags) >= self.MIN_CONFLUENCE:
                        signals.append({"bar": i, "type": "OB_BEAR",
                                        "top": ob["top"], "bottom": ob["bottom"],
                                        "mid": ob["mid"], "confluence": tags}); break

        for sw in sweeps:
            i = sw["bar"]; b = self.bias(i); z = self.zone(i)
            tags = ["SWEEP"]
            if sw["type"] == "LIQ_BULL":
                if b == "bullish":               tags.append("BIAS")
                if z in ("discount","equilibrium"): tags.append("DISCOUNT")
                if self.in_kz(i):               tags.append("KILLZONE")
                if len(tags) >= self.MIN_CONFLUENCE:
                    signals.append({"bar": i, "type": "LIQ_BULL",
                                    "top": sw["top"], "bottom": sw["bottom"],
                                    "mid": sw["mid"], "confluence": tags})
            elif sw["type"] == "LIQ_BEAR":
                if b == "bearish":               tags.append("BIAS")
                if z in ("premium","equilibrium"): tags.append("PREMIUM")
                if self.in_kz(i):               tags.append("KILLZONE")
                if len(tags) >= self.MIN_CONFLUENCE:
                    signals.append({"bar": i, "type": "LIQ_BEAR",
                                    "top": sw["top"], "bottom": sw["bottom"],
                                    "mid": sw["mid"], "confluence": tags})

        signals.sort(key=lambda s: s["bar"])
        return signals


# ── Backtesting engine ────────────────────────────────────────────────────────

class Backtester:
    def __init__(self, symbol, timeframe, strategy="Mixed", bars=500,
                 risk_percent=1.0, rr_ratio=2.0, initial_balance=10_000.0,
                 max_risk_usd=None, enabled_setups=None):
        self.symbol          = symbol
        self.timeframe       = timeframe
        self.strategy        = strategy
        self.bars            = bars
        self.risk_percent    = risk_percent
        self.rr_ratio        = rr_ratio
        self.initial_balance = initial_balance
        self.max_risk_usd    = max_risk_usd  # None = no cap
        # None = all setups enabled; otherwise a set of sig type strings
        self.enabled_setups  = set(enabled_setups) if enabled_setups else None
        self.pip             = (0.01 if "JPY" in symbol else
                                1.0  if symbol in ("XAUUSD","US30","NAS100","US500") else
                                0.0001)

    async def run(self) -> BacktestResult:
        from services.forex_data import fetch_ohlcv
        raw     = await fetch_ohlcv(self.symbol, self.timeframe, self.bars)
        candles = [Candle(**c) for c in raw.get("candles", [])]
        if len(candles) < 50:
            return BacktestResult(symbol=self.symbol, timeframe=self.timeframe,
                                  strategy=self.strategy, bars_used=len(candles),
                                  risk_percent=self.risk_percent, rr_ratio=self.rr_ratio)
        return self._simulate(candles)

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

        balance     = self.initial_balance
        open_trades: list[SimTrade] = []
        trade_id    = 0
        used_bars: set  = set()

        for i, candle in enumerate(candles):
            still_open = []
            for t in open_trades:
                closed = False
                if t.direction == "BUY":
                    if candle.low <= t.stop_loss:
                        t = self._close(t, t.stop_loss, "LOSS", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100; closed = True
                    elif candle.high >= t.take_profit:
                        t = self._close(t, t.take_profit, "WIN", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100; closed = True
                else:
                    if candle.high >= t.stop_loss:
                        t = self._close(t, t.stop_loss, "LOSS", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100; closed = True
                    elif candle.low <= t.take_profit:
                        t = self._close(t, t.take_profit, "WIN", i, candle.time, balance)
                        balance += balance * t.pnl_pct / 100; closed = True
                if closed:
                    result.trades.append(t)
                else:
                    still_open.append(t)
            open_trades = still_open

            if not open_trades:
                for sig in sig_map.get(i, []):
                    if i in used_bars:
                        continue
                    trade = self._make_trade(trade_id, sig, i, candle, balance, analyzer)
                    if trade:
                        trade_id += 1; used_bars.add(i)
                        open_trades.append(trade); break

            result.equity.append({"bar": i, "time": candle.time, "equity": round(balance, 2)})

        if open_trades and candles:
            last = candles[-1]
            for t in open_trades:
                t = self._close(t, last.close, "OPEN", len(candles)-1, last.time, balance)
                result.trades.append(t)

        result.compute_stats(self.pip)
        return result

    def _make_trade(self, trade_id, sig, bar, candle, balance, analyzer) -> Optional[SimTrade]:
        sig_type  = sig["type"]
        direction = "SELL" if "BEAR" in sig_type else "BUY"
        atr       = analyzer.atr(bar)
        entry     = sig.get("mid", candle.close)

        if direction == "BUY":
            sl = sig.get("bottom", entry - atr) - atr * 0.3
            tp = entry + (entry - sl) * self.rr_ratio
        else:
            sl = sig.get("top", entry + atr) + atr * 0.3
            tp = entry - (sl - entry) * self.rr_ratio

        sl_dist = abs(entry - sl)
        if sl_dist < self.pip:
            return None

        risk_amount = balance * self.risk_percent / 100
        if self.max_risk_usd is not None:
            risk_amount = min(risk_amount, self.max_risk_usd)
        pips_risk   = sl_dist / self.pip
        lot_size    = round(risk_amount / (pips_risk * self.pip * 100_000), 3)
        lot_size    = max(0.01, min(lot_size, 10.0))

        label = {"FVG_BULL":"FVG↑","FVG_BEAR":"FVG↓",
                 "OB_BULL":"OB↑","OB_BEAR":"OB↓",
                 "LIQ_BULL":"Liq↑","LIQ_BEAR":"Liq↓"}.get(sig_type, sig_type)

        return SimTrade(id=trade_id, setup=label, direction=direction,
                        entry_bar=bar, entry_time=candle.time,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5), take_profit=round(tp, 5),
                        lot_size=lot_size, confluence=sig.get("confluence", []))

    def _close(self, trade, exit_price, result, bar, time, balance) -> SimTrade:
        trade.exit_bar   = bar
        trade.exit_time  = time
        trade.exit_price = round(exit_price, 5)
        trade.result     = result
        entry = trade.entry_price
        pips  = ((exit_price - entry) if trade.direction == "BUY" else (entry - exit_price)) / self.pip
        trade.pnl_pips = round(pips, 1)
        pnl_usd        = pips * self.pip * trade.lot_size * 100_000
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
                       enabled_setups=None) -> BacktestResult:
    return await Backtester(symbol=symbol, timeframe=timeframe, strategy=strategy,
                            bars=bars, risk_percent=risk_percent, rr_ratio=rr_ratio,
                            initial_balance=initial_balance, max_risk_usd=max_risk_usd,
                            enabled_setups=enabled_setups).run()
