"""Per-(setup × symbol × session) diagnostics for self-adaptation meetings.

Produces a structured breakdown of which ICT setups work where and when,
classifies failures (SL-hit / TP-hit / timeout / manual), and yields a
verdict per cell. Output feeds the Journalist prompt so auto-tuning
proposals target quality, not just trade frequency.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from models.database import Trade, async_session_factory

log = logging.getLogger("setup_diagnostics")


def _classify_failure(trade: Trade) -> str:
    notes = (trade.close_notes or "").lower()
    if "sl colpito" in notes or "sl hit" in notes:
        return "sl_hit"
    if ("tp1" in notes or "tp2" in notes or "tp3" in notes) and "colpito" in notes:
        return "tp_hit"
    if "max duration" in notes or "force close" in notes or "duration reached" in notes:
        return "timeout"
    if "manuale" in notes or "manually" in notes:
        return "manual"

    if trade.stop_loss and trade.close_price:
        denom = max(abs(trade.stop_loss), 1e-8)
        if abs(trade.close_price - trade.stop_loss) / denom < 0.0005:
            return "sl_hit"
    for tp in (trade.take_profit_1, trade.take_profit_2, trade.take_profit_3):
        if tp and trade.close_price:
            denom = max(abs(tp), 1e-8)
            if abs(trade.close_price - tp) / denom < 0.0005:
                return "tp_hit"
    return "unknown"


def _session_of(ctx: dict | None, hour_utc: int | None) -> str:
    if ctx and ctx.get("session"):
        return ctx["session"]
    if hour_utc is None:
        return "Unknown"
    if 0 <= hour_utc < 7:
        return "Asian"
    if 7 <= hour_utc < 12:
        return "London"
    if 12 <= hour_utc < 17:
        return "NewYork"
    return "Off"


def _htf_aligned(trade: Trade, ctx: dict | None) -> bool | None:
    if not ctx:
        return None
    htf = (ctx.get("htf_trend") or "").lower()
    dirn = (trade.direction or "").upper()
    if htf in ("bullish", "up", "long"):
        return dirn == "BUY"
    if htf in ("bearish", "down", "short"):
        return dirn == "SELL"
    return None


def _near_news(ctx: dict | None, threshold_min: int = 60) -> bool:
    if not ctx:
        return False
    mins = ctx.get("minutes_to_next_news")
    if mins is None or mins >= 9999:
        return False
    try:
        return int(mins) < threshold_min
    except (TypeError, ValueError):
        return False


def _verdict(n: int, wr: float, expectancy_r: float) -> str:
    if n < 3:
        return "INSUFFICIENT"
    if wr >= 55 and expectancy_r >= 0.15:
        return "WORKING"
    if wr < 40 or expectancy_r <= -0.10:
        return "FAILING"
    return "MARGINAL"


def _normalize_setup(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    # "FVG+OB" -> "FVG"; "Liquidity Sweep" -> "LiquiditySweep"
    head = raw.split("+")[0].strip()
    return head.replace(" ", "")


async def diagnose_setups(days_back: int = 7, include_paper: bool = True) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    async with async_session_factory() as s:
        q = select(Trade).where(Trade.status == "CLOSED").where(Trade.close_time >= cutoff)
        q = q.where((Trade.archived == False) | (Trade.archived == None))  # noqa: E712
        if not include_paper:
            q = q.where((Trade.is_paper == False) | (Trade.is_paper == None))  # noqa: E712
        rows = (await s.execute(q)).scalars().all()

    cells: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {
        "n": 0, "wins": 0, "losses": 0, "pnl_sum": 0.0, "rr_sum": 0.0,
        "failures": {"sl_hit": 0, "tp_hit": 0, "timeout": 0, "manual": 0, "unknown": 0},
        "counter_trend": 0, "htf_eval": 0, "near_news": 0,
        "durations_min": [],
    })

    for t in rows:
        ctx = None
        if t.market_context:
            try:
                ctx = json.loads(t.market_context)
            except Exception:
                ctx = None
        hour_utc = ctx.get("hour_utc") if ctx else None
        sess = _session_of(ctx, hour_utc)
        setup = _normalize_setup(t.ict_setup)
        key = (setup, t.symbol or "?", sess)
        c = cells[key]
        c["n"] += 1
        res = (t.result or "").upper()
        if res == "WIN":
            c["wins"] += 1
        elif res == "LOSS":
            c["losses"] += 1
        c["pnl_sum"] += float(t.pnl_usd or 0.0)
        c["rr_sum"] += float(t.rr_ratio or 0.0)
        c["failures"][_classify_failure(t)] += 1
        aligned = _htf_aligned(t, ctx)
        if aligned is not None:
            c["htf_eval"] += 1
            if not aligned:
                c["counter_trend"] += 1
        if _near_news(ctx):
            c["near_news"] += 1
        if t.open_time and t.close_time:
            c["durations_min"].append(int((t.close_time - t.open_time).total_seconds() / 60))

    cells_out = []
    for (setup, sym, sess), c in cells.items():
        n = c["n"]
        wr = (c["wins"] / n) * 100 if n else 0
        avg_rr = c["rr_sum"] / n if n else 0
        avg_pnl = c["pnl_sum"] / n if n else 0
        # Expectancy in R: each win earns avg_rr R, each loss costs 1R
        exp_r = ((c["wins"] * avg_rr) - c["losses"]) / n if n else 0
        cells_out.append({
            "setup": setup, "symbol": sym, "session": sess,
            "n": n, "wins": c["wins"], "losses": c["losses"],
            "wr": round(wr, 1), "avg_rr": round(avg_rr, 2),
            "avg_pnl_usd": round(avg_pnl, 2),
            "expectancy_r": round(exp_r, 2),
            "failures": dict(c["failures"]),
            "counter_trend_pct": (round((c["counter_trend"] / c["htf_eval"]) * 100) if c["htf_eval"] else None),
            "near_news_pct": round((c["near_news"] / n) * 100) if n else 0,
            "avg_duration_min": (int(sum(c["durations_min"]) / len(c["durations_min"])) if c["durations_min"] else None),
            "verdict": _verdict(n, wr, exp_r),
        })
    cells_out.sort(key=lambda x: (x["verdict"] != "FAILING", -x["n"], -x["expectancy_r"]))

    total_n = sum(x["n"] for x in cells_out)
    total_losses = sum(x["losses"] for x in cells_out)
    sl_hits = sum(x["failures"]["sl_hit"] for x in cells_out)
    timeouts = sum(x["failures"]["timeout"] for x in cells_out)
    counter_trend_total = sum(c["counter_trend"] for c in cells.values())
    htf_eval_total = sum(c["htf_eval"] for c in cells.values())

    return {
        "window_days": days_back,
        "total_closed": total_n,
        "wins": sum(x["wins"] for x in cells_out),
        "losses": total_losses,
        "cells": cells_out,
        "worst_cells": [c for c in cells_out if c["verdict"] == "FAILING"][:10],
        "best_cells":  [c for c in cells_out if c["verdict"] == "WORKING"][:10],
        "failure_patterns": {
            "sl_hit_pct_of_losses":    round((sl_hits / total_losses) * 100) if total_losses else 0,
            "timeout_pct_of_losses":   round((timeouts / total_losses) * 100) if total_losses else 0,
            "counter_trend_pct_total": round((counter_trend_total / htf_eval_total) * 100) if htf_eval_total else 0,
        },
    }


def format_diagnostics_for_prompt(d: dict) -> str:
    if not d or not d.get("cells"):
        return "(no closed trades in window — nothing to diagnose)"
    lines: list[str] = []
    lines.append(f"=== SETUP DIAGNOSTICS (last {d['window_days']}d) ===")
    lines.append(f"Closed: {d['total_closed']}  Wins: {d['wins']}  Losses: {d['losses']}")
    fp = d["failure_patterns"]
    lines.append(
        "Failure patterns — "
        f"SL-hit: {fp['sl_hit_pct_of_losses']}% of losses, "
        f"Timeout: {fp['timeout_pct_of_losses']}%, "
        f"Counter-trend entries: {fp['counter_trend_pct_total']}% (HTF-evaluated)"
    )
    lines.append("")
    lines.append("## Per-cell table (setup × symbol × session):")
    lines.append(
        f"{'setup':<14}{'symbol':<10}{'session':<10}"
        f"{'n':>3} {'WR%':>5} {'RR':>5} {'E(R)':>6} "
        f"{'SL':>3} {'TP':>3} {'TO':>3} {'CT%':>5}  verdict"
    )
    for c in d["cells"]:
        ct = f"{c['counter_trend_pct']}%" if c["counter_trend_pct"] is not None else "-"
        lines.append(
            f"{c['setup']:<14}{c['symbol']:<10}{c['session']:<10}"
            f"{c['n']:>3} {c['wr']:>5.0f} {c['avg_rr']:>5.2f} {c['expectancy_r']:>6.2f} "
            f"{c['failures']['sl_hit']:>3} {c['failures']['tp_hit']:>3} {c['failures']['timeout']:>3} "
            f"{ct:>5}  {c['verdict']}"
        )
    lines.append("")
    if d["worst_cells"]:
        lines.append("## FAILING cells (candidates for BLOCK / FILTER rules):")
        for c in d["worst_cells"]:
            lines.append(
                f"  - {c['setup']}:{c['symbol']}:{c['session']}"
                f"  n={c['n']} WR={c['wr']}% E={c['expectancy_r']}R"
                f"  SL-hit={c['failures']['sl_hit']} TO={c['failures']['timeout']}"
                f"  CT={c['counter_trend_pct']}%"
            )
    if d["best_cells"]:
        lines.append("## WORKING cells (candidates for BOOST / INCREASE_SIZE rules):")
        for c in d["best_cells"]:
            lines.append(
                f"  - {c['setup']}:{c['symbol']}:{c['session']}"
                f"  n={c['n']} WR={c['wr']}% E={c['expectancy_r']}R RR={c['avg_rr']}"
            )
    return "\n".join(lines)
