"""
strategy_memory.py — Persistent per-setup learning memory.

After every trade close and every meeting, this module updates
StrategyMemory rows so that each agent call is informed by the
actual historical performance of each ICT setup.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("strategy_memory")


async def get_win_rate(setup_type: str, symbol: Optional[str] = None) -> Optional[dict]:
    """Return real win-rate data for a setup, or None if no data.
    Tries symbol-specific first, falls back to global (symbol=None).
    Used by the RiskManager to replace hard-coded SETUP_WIN_RATES with
    actual performance when enough trades exist."""
    if not setup_type:
        return None
    try:
        from models.database import StrategyMemory, async_session_factory
        from sqlalchemy import select
        async with async_session_factory() as s:
            # Try symbol-specific first
            for sym in (symbol, None):
                q = select(StrategyMemory).where(
                    StrategyMemory.setup_type == setup_type,
                    StrategyMemory.symbol == sym,
                )
                row = (await s.execute(q)).scalar_one_or_none()
                if row:
                    total = (row.win_count or 0) + (row.loss_count or 0)
                    if total > 0:
                        return {
                            "win_rate": round(row.win_count / total * 100, 2),
                            "sample_size": total,
                            "wins": row.win_count,
                            "losses": row.loss_count,
                            "avg_pnl_usd": round((row.total_pnl_usd or 0) / total, 2),
                            "scope": "symbol" if sym else "global",
                        }
        return None
    except Exception as exc:
        log.warning("get_win_rate failed: %s", exc)
        return None


async def update_from_trade(setup_type: str, symbol: str, pnl_usd: float, result: str):
    """Called after every trade close — increments win/loss counters and P&L."""
    if not setup_type:
        return
    try:
        from models.database import StrategyMemory, async_session_factory
        from sqlalchemy.dialects.sqlite import insert as _ins
        async with async_session_factory() as s:
            # Upsert global row (symbol=None)
            for sym in (None, symbol):
                row = await _get_or_create(s, setup_type, sym)
                if result == "WIN":
                    row.win_count += 1
                elif result == "LOSS":
                    row.loss_count += 1
                row.total_pnl_usd = round((row.total_pnl_usd or 0) + (pnl_usd or 0), 2)
                row.last_updated = datetime.utcnow()
            await s.commit()
    except Exception as exc:
        log.warning("update_from_trade failed: %s", exc)


async def update_from_meeting(memory_updates: list[dict]):
    """
    Called after every meeting — applies JR's qualitative insights.
    Each item in memory_updates:
      { "setup_type": "FVG", "symbol": null|"EURUSD",
        "failure_patterns": [...], "success_patterns": [...],
        "lessons": [...], "strategy_notes": "..." }
    """
    if not memory_updates:
        return
    try:
        from models.database import async_session_factory
        async with async_session_factory() as s:
            for upd in memory_updates:
                setup = upd.get("setup_type")
                sym   = upd.get("symbol") or None
                if not setup:
                    continue
                row = await _get_or_create(s, setup, sym)
                # Merge new patterns / lessons (keep unique, cap at 10 each)
                row.failure_patterns = _merge_list(row.failure_patterns, upd.get("failure_patterns", []))
                row.success_patterns = _merge_list(row.success_patterns, upd.get("success_patterns", []))
                row.lessons          = _merge_list(row.lessons,          upd.get("lessons", []))
                if upd.get("strategy_notes"):
                    row.strategy_notes = upd["strategy_notes"]
                row.last_updated = datetime.utcnow()
            await s.commit()
        log.info("Strategy memory updated from meeting: %d entries", len(memory_updates))
    except Exception as exc:
        log.warning("update_from_meeting failed: %s", exc)


async def build_context_string(setup_types: list[str] | None = None) -> str:
    """
    Returns a formatted string injected into agent prompts.
    If setup_types is given, only include those setups (plus global rows).
    """
    try:
        from models.database import StrategyMemory, async_session_factory
        from sqlalchemy import select
        async with async_session_factory() as s:
            q = select(StrategyMemory).order_by(StrategyMemory.setup_type, StrategyMemory.symbol)
            rows = (await s.execute(q)).scalars().all()

        if not rows:
            return ""

        lines = ["## 📚 Strategy Performance Memory (Continuous Learning)",
                 "The following is derived from ACTUAL trade history. Use it to weight your decisions.\n"]

        # Group by setup_type
        by_setup: dict[str, list] = {}
        for r in rows:
            by_setup.setdefault(r.setup_type, []).append(r)

        for setup, entries in by_setup.items():
            if setup_types and setup not in setup_types:
                continue
            # Global row first, then per-symbol
            global_row = next((e for e in entries if e.symbol is None), None)
            sym_rows   = [e for e in entries if e.symbol is not None]

            total = (global_row.win_count + global_row.loss_count) if global_row else 0
            if total == 0 and not any(e.strategy_notes or e.lessons for e in entries):
                continue  # skip setup with no data yet

            wr = round(global_row.win_count / total * 100, 1) if (global_row and total > 0) else None
            avg_pnl = round(global_row.total_pnl_usd / total, 2) if (global_row and total > 0) else None
            performance_tag = _perf_tag(wr)

            lines.append(f"### {setup} {performance_tag}")
            if total > 0:
                lines.append(f"  Overall: {total} trades | {wr}% win rate | avg P&L ${avg_pnl:+.2f}")
            for sr in sym_rows[:5]:
                st = sr.win_count + sr.loss_count
                if st > 0:
                    swr = round(sr.win_count / st * 100, 1)
                    lines.append(f"  {sr.symbol}: {st} trades | {swr}% win rate")

            if global_row:
                fp = json.loads(global_row.failure_patterns or "[]")
                sp = json.loads(global_row.success_patterns or "[]")
                ls = json.loads(global_row.lessons or "[]")
                if fp:
                    lines.append("  ❌ Failure patterns: " + " | ".join(fp[:3]))
                if sp:
                    lines.append("  ✅ Success patterns: " + " | ".join(sp[:3]))
                if ls:
                    lines.append("  💡 Lessons: " + " | ".join(ls[:3]))
                if global_row.strategy_notes:
                    lines.append(f"  📌 Guidance: {global_row.strategy_notes}")
            lines.append("")

        if len(lines) <= 3:
            return ""
        lines.append("Apply this data: de-prioritize setups marked ⚠️ CAUTION or 🚫 AVOID, "
                      "prioritize ✅ STRONG setups. Adjust position sizing accordingly.\n")
        return "\n".join(lines)
    except Exception as exc:
        log.warning("build_context_string failed: %s", exc)
        return ""


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create(session, setup_type: str, symbol: Optional[str]):
    from models.database import StrategyMemory
    from sqlalchemy import select
    q = select(StrategyMemory).where(
        StrategyMemory.setup_type == setup_type,
        StrategyMemory.symbol == symbol,
    )
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        row = StrategyMemory(setup_type=setup_type, symbol=symbol)
        session.add(row)
        await session.flush()
    return row


def _merge_list(existing_json: str, new_items: list) -> str:
    try:
        existing = json.loads(existing_json or "[]")
    except Exception:
        existing = []
    merged = existing + [i for i in new_items if i and i not in existing]
    return json.dumps(merged[-10:])  # keep most recent 10


def _perf_tag(win_rate: Optional[float]) -> str:
    if win_rate is None:
        return "🔄 NEW"
    if win_rate >= 65:
        return "✅ STRONG"
    if win_rate >= 50:
        return "🟡 NEUTRAL"
    if win_rate >= 35:
        return "⚠️ CAUTION"
    return "🚫 AVOID"
