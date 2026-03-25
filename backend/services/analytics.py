"""
analytics.py — TradeWizard Analytics Engine

Computes comprehensive performance analytics from closed trade history:
  - Equity curve & drawdown series
  - Monthly returns heatmap
  - Win/loss streaks
  - Performance by symbol, ICT setup, day-of-week, session hour
  - Key metrics: Sharpe, Sortino, profit factor, expectancy, avg R:R
  - Live system stats (open P&L, margins, recent activity)
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


# ── Main entry point ─────────────────────────────────────────────────────────

async def compute_analytics() -> dict:
    """Fetch all closed trades from DB and return a full analytics report."""
    trades = await _fetch_closed_trades()
    return _build_report(trades)


# ── Report builder ────────────────────────────────────────────────────────────

def _build_report(trades: list[dict]) -> dict:
    if not trades:
        return _empty_report()

    # Sort by close time
    trades = sorted(
        trades,
        key=lambda t: t.get("close_time") or t.get("open_time") or "",
    )

    # ── Core series ──────────────────────────────────────────────────────────
    equity_curve, drawdown_series = _equity_and_drawdown(trades)

    # ── Aggregate stats ──────────────────────────────────────────────────────
    closed  = [t for t in trades if t.get("pnl_usd") is not None]
    total   = len(closed)
    wins    = [t for t in closed if (t.get("pnl_usd") or 0) > 0]
    losses  = [t for t in closed if (t.get("pnl_usd") or 0) < 0]
    be      = [t for t in closed if (t.get("pnl_usd") or 0) == 0]

    win_rate   = round(len(wins) / total * 100, 1) if total else 0.0
    total_pnl  = sum(t.get("pnl_usd") or 0 for t in closed)
    total_pips = sum(t.get("pnl_pips") or 0 for t in closed)

    gross_win  = sum(t.get("pnl_usd") or 0 for t in wins)
    gross_loss = abs(sum(t.get("pnl_usd") or 0 for t in losses))
    pf         = round(gross_win / gross_loss, 2) if gross_loss else (float("inf") if gross_win else 0.0)

    avg_win    = round(gross_win  / len(wins),   2) if wins   else 0.0
    avg_loss   = round(gross_loss / len(losses), 2) if losses else 0.0
    avg_rr     = round(gross_win / len(wins) / (gross_loss / len(losses)), 2) \
                 if wins and losses else 0.0
    expectancy = round(total_pnl / total, 2) if total else 0.0

    pnl_series = [t.get("pnl_usd") or 0 for t in closed]
    sharpe     = _sharpe(pnl_series)
    sortino    = _sortino(pnl_series)

    max_dd     = min((d["drawdown_pct"] for d in drawdown_series), default=0.0)
    streak_win, streak_loss, cur_streak = _streaks(closed)

    # ── Breakdown tables ─────────────────────────────────────────────────────
    by_symbol  = _group_by(closed, "symbol")
    by_setup   = _group_by(closed, "ict_setup")
    by_dow     = _group_by_dow(closed)
    by_hour    = _group_by_hour(closed)
    by_month   = _monthly_returns(closed)

    return {
        # ── Summary ──────────────────────────────────────────────────────────
        "summary": {
            "total_trades":  total,
            "wins":          len(wins),
            "losses":        len(losses),
            "breakeven":     len(be),
            "win_rate":      win_rate,
            "total_pnl_usd": round(total_pnl, 2),
            "total_pips":    round(total_pips, 1),
            "gross_profit":  round(gross_win, 2),
            "gross_loss":    round(gross_loss, 2),
            "profit_factor": pf if pf != float("inf") else 999.0,
            "avg_win_usd":   avg_win,
            "avg_loss_usd":  avg_loss,
            "avg_rr":        avg_rr,
            "expectancy":    expectancy,
            "sharpe":        sharpe,
            "sortino":       sortino,
            "max_drawdown_pct": round(max_dd, 2),
            "max_win_streak":  streak_win,
            "max_loss_streak": streak_loss,
            "current_streak":  cur_streak,
        },
        # ── Time series ──────────────────────────────────────────────────────
        "equity_curve":    equity_curve,
        "drawdown_series": drawdown_series,
        # ── Breakdowns ───────────────────────────────────────────────────────
        "by_symbol":  by_symbol,
        "by_setup":   by_setup,
        "by_dow":     by_dow,
        "by_hour":    by_hour,
        "by_month":   by_month,
    }


# ── Series builders ───────────────────────────────────────────────────────────

def _equity_and_drawdown(trades: list[dict], start: float = 10_000.0):
    equity_curve    = []
    drawdown_series = []
    balance  = start
    peak     = start

    for t in trades:
        pnl  = t.get("pnl_usd") or 0
        balance = round(balance + pnl, 2)
        ts   = t.get("close_time") or t.get("open_time") or datetime.utcnow().isoformat()

        if balance > peak:
            peak = balance
        dd_pct = round((balance - peak) / peak * 100, 2) if peak else 0.0

        equity_curve.append({"time": ts, "equity": balance})
        drawdown_series.append({"time": ts, "drawdown_pct": dd_pct})

    return equity_curve, drawdown_series


# ── Grouping helpers ──────────────────────────────────────────────────────────

def _group_by(trades: list[dict], key: str) -> list[dict]:
    buckets: dict[str, list] = defaultdict(list)
    for t in trades:
        k = str(t.get(key) or "Unknown")
        buckets[k].append(t)

    result = []
    for name, ts in sorted(buckets.items()):
        total  = len(ts)
        wins   = sum(1 for t in ts if (t.get("pnl_usd") or 0) > 0)
        pips   = sum(t.get("pnl_pips") or 0 for t in ts)
        pnl    = sum(t.get("pnl_usd")  or 0 for t in ts)
        result.append({
            "name":     name,
            "total":    total,
            "wins":     wins,
            "losses":   total - wins,
            "win_rate": round(wins / total * 100, 1),
            "total_pips": round(pips, 1),
            "total_pnl":  round(pnl, 2),
        })
    return sorted(result, key=lambda r: r["total_pnl"], reverse=True)


_DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def _group_by_dow(trades: list[dict]) -> list[dict]:
    buckets: dict[int, list] = defaultdict(list)
    for t in trades:
        ts = t.get("close_time") or t.get("open_time")
        if not ts:
            continue
        try:
            dt  = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            dow = dt.weekday()
            buckets[dow].append(t)
        except Exception:
            pass

    result = []
    for dow in range(7):
        ts     = buckets[dow]
        total  = len(ts)
        wins   = sum(1 for t in ts if (t.get("pnl_usd") or 0) > 0)
        pips   = sum(t.get("pnl_pips") or 0 for t in ts)
        result.append({
            "day":      _DOW_NAMES[dow],
            "total":    total,
            "wins":     wins,
            "win_rate": round(wins / total * 100, 1) if total else 0.0,
            "total_pips": round(pips, 1),
        })
    return result


def _group_by_hour(trades: list[dict]) -> list[dict]:
    buckets: dict[int, list] = defaultdict(list)
    for t in trades:
        ts = t.get("open_time")
        if not ts:
            continue
        try:
            dt   = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            hour = dt.hour
            buckets[hour].append(t)
        except Exception:
            pass

    result = []
    for h in range(24):
        ts    = buckets[h]
        total = len(ts)
        wins  = sum(1 for t in ts if (t.get("pnl_usd") or 0) > 0)
        pips  = sum(t.get("pnl_pips") or 0 for t in ts)
        result.append({
            "hour":     h,
            "label":    f"{h:02d}:00",
            "total":    total,
            "wins":     wins,
            "win_rate": round(wins / total * 100, 1) if total else 0.0,
            "total_pips": round(pips, 1),
        })
    return result


def _monthly_returns(trades: list[dict]) -> list[dict]:
    """Returns a list of {year, month, return_pct, total_pnl, trades} dicts."""
    buckets: dict[tuple, list] = defaultdict(list)
    for t in trades:
        ts = t.get("close_time") or t.get("open_time")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            buckets[(dt.year, dt.month)].append(t)
        except Exception:
            pass

    result = []
    for (year, month), ts in sorted(buckets.items()):
        pnl = sum(t.get("pnl_usd") or 0 for t in ts)
        result.append({
            "year":       year,
            "month":      month,
            "month_name": _MONTH_NAMES[month - 1],
            "total_pnl":  round(pnl, 2),
            "trades":     len(ts),
            "wins":       sum(1 for t in ts if (t.get("pnl_usd") or 0) > 0),
        })
    return result


_MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


# ── Stats helpers ─────────────────────────────────────────────────────────────

def _sharpe(returns: list[float], risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean  = sum(returns) / len(returns)
    var   = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std   = math.sqrt(var) if var > 0 else 1e-9
    return round((mean - risk_free) / std * math.sqrt(252), 2)


def _sortino(returns: list[float], risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean     = sum(returns) / len(returns)
    neg      = [r for r in returns if r < risk_free]
    if not neg:
        return 999.0
    down_var = sum((r - risk_free) ** 2 for r in neg) / len(neg)
    down_std = math.sqrt(down_var) if down_var > 0 else 1e-9
    return round((mean - risk_free) / down_std * math.sqrt(252), 2)


def _streaks(trades: list[dict]) -> tuple[int, int, dict]:
    max_win = max_loss = cur_win = cur_loss = 0
    for t in trades:
        win = (t.get("pnl_usd") or 0) > 0
        if win:
            cur_win  += 1
            cur_loss  = 0
        else:
            cur_loss += 1
            cur_win   = 0
        max_win  = max(max_win,  cur_win)
        max_loss = max(max_loss, cur_loss)

    current: dict[str, Any] = {}
    if cur_win > 0:
        current = {"type": "WIN",  "count": cur_win}
    elif cur_loss > 0:
        current = {"type": "LOSS", "count": cur_loss}

    return max_win, max_loss, current


# ── DB fetch ──────────────────────────────────────────────────────────────────

async def _fetch_closed_trades() -> list[dict]:
    from models.database import async_session_factory, Trade
    from sqlalchemy import select
    async with async_session_factory() as s:
        result = await s.execute(
            select(Trade)
            .where(Trade.status == "CLOSED", Trade.is_paper == False)  # noqa: E712
            .order_by(Trade.close_time)
        )
        trades = result.scalars().all()
    return [
        {
            "id":         t.id,
            "symbol":     t.symbol,
            "direction":  t.direction,
            "ict_setup":  t.ict_setup,
            "open_time":  t.open_time.isoformat() if t.open_time  else None,
            "close_time": t.close_time.isoformat() if t.close_time else None,
            "pnl_usd":    t.pnl_usd,
            "pnl_pips":   t.pnl_pips,
            "result":     t.result,
            "rr_ratio":   t.rr_ratio,
            "lot_size":   t.lot_size,
        }
        for t in trades
    ]


def _empty_report() -> dict:
    return {
        "summary": {
            "total_trades": 0, "wins": 0, "losses": 0, "breakeven": 0,
            "win_rate": 0.0, "total_pnl_usd": 0.0, "total_pips": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0,
            "avg_win_usd": 0.0, "avg_loss_usd": 0.0, "avg_rr": 0.0,
            "expectancy": 0.0, "sharpe": 0.0, "sortino": 0.0,
            "max_drawdown_pct": 0.0, "max_win_streak": 0,
            "max_loss_streak": 0, "current_streak": {},
        },
        "equity_curve": [], "drawdown_series": [],
        "by_symbol": [], "by_setup": [], "by_dow": [], "by_hour": [], "by_month": [],
    }
