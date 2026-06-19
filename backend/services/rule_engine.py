"""
rule_engine.py — Evaluates learning_rules against a proposed trade.

Called by the orchestrator BEFORE sending the trade to the RiskManager.
Returns a verdict: ALLOW | BLOCK + reasons + size_factor + context_notes.

In production mode (SYSTEM_MODE != 'lab') the engine is a no-op: evaluate_trade
always returns ALLOW with no adjustments. This lets the lab/prod instances
share the same codebase without affecting the real-money system.
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("rule_engine")

SYSTEM_MODE = os.getenv("SYSTEM_MODE", "production").lower()
RULE_ENGINE_ACTIVE = (SYSTEM_MODE == "lab")


_OPS = {
    "<":  lambda a, b: a < b,
    ">":  lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class RuleVerdict:
    action: str = "ALLOW"                 # ALLOW | BLOCK
    reasons: list[str] = field(default_factory=list)
    size_factor: float = 1.0
    context_notes: list[str] = field(default_factory=list)
    rules_applied: list[int] = field(default_factory=list)
    adjustments: list[dict] = field(default_factory=list)  # {type:"ADJUST_SL", min_pips: 40, rule_id}

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reasons": self.reasons,
            "size_factor": self.size_factor,
            "context_notes": self.context_notes,
            "rules_applied": self.rules_applied,
            "adjustments": self.adjustments,
        }


def _resolve_value(v: Any, strategy: dict) -> Any:
    """Resolve dynamic references like 'strategy.direction'."""
    if isinstance(v, str) and v.startswith("strategy."):
        key = v.split(".", 1)[1]
        return strategy.get(key)
    return v


def condition_matches(condition: dict, context: dict, strategy: dict) -> bool:
    """Evaluate a JSON condition against market context + strategy.
    Returns False on any malformed condition (conservative: don't trigger)."""
    if not condition:
        return False
    try:
        if "and" in condition:
            return all(condition_matches(c, context, strategy) for c in condition["and"])
        if "or" in condition:
            return any(condition_matches(c, context, strategy) for c in condition["or"])

        field_name = condition.get("field")
        op = condition.get("op")
        expected = _resolve_value(condition.get("value"), strategy)
        actual = context.get(field_name)

        if actual is None or op not in _OPS:
            return False
        return _OPS[op](actual, expected)
    except Exception as exc:
        log.warning("condition_matches failed for %s: %s", condition, exc)
        return False


async def evaluate_trade(setup_type: Optional[str],
                          symbol: Optional[str],
                          session: Optional[str],
                          market_context: dict,
                          strategy: Optional[dict] = None) -> RuleVerdict:
    """Evaluate all active rules against the trade. Returns a verdict.

    If any BLOCK rule matches → action="BLOCK".
    REDUCE_SIZE and INCREASE_SIZE rules multiply size_factor.
    ADJUST_SL and ADD_CONTEXT accumulate in adjustments/context_notes.

    Circuit breaker: if consecutive losses >= 5, all BOOST rules are skipped.

    In production mode this function returns ALLOW immediately — no rules run.
    """
    if not RULE_ENGINE_ACTIVE:
        return RuleVerdict()

    from services.learning_rules import get_active_rules
    strategy = strategy or {}

    # Circuit breaker: detect losing streak — disables BOOST rules
    disable_boost = await _is_losing_streak(5)

    rules = await get_active_rules(setup_type, symbol, session)
    verdict = RuleVerdict()

    for rule in rules:
        try:
            condition = json.loads(rule.condition or "{}")
            action = json.loads(rule.action or "{}")
        except Exception:
            continue

        # Empty condition means rule always applies (unconditional)
        matches = (not condition) or condition_matches(condition, market_context, strategy)
        if not matches:
            continue

        verdict.rules_applied.append(rule.id)
        atype = (action.get("type") or "").upper()

        if atype == "BLOCK":
            verdict.action = "BLOCK"
            verdict.reasons.append(f"#{rule.id} {action.get('reason', 'blocked')}")
        elif atype == "REDUCE_SIZE":
            factor = float(action.get("factor", 0.5))
            verdict.size_factor *= factor
        elif atype == "INCREASE_SIZE":
            if disable_boost:
                verdict.context_notes.append(
                    f"[circuit-breaker] BOOST rule #{rule.id} skipped (losing streak)"
                )
                continue
            factor = float(action.get("factor", 1.5))
            verdict.size_factor *= factor
        elif atype == "ADJUST_SL":
            verdict.adjustments.append({
                "type": "ADJUST_SL",
                "min_pips": float(action.get("min_pips", 0)),
                "rule_id": rule.id,
            })
        elif atype == "ADD_CONTEXT":
            text = action.get("text", "")
            if text:
                verdict.context_notes.append(f"[rule #{rule.id}] {text}")

    # Clamp size_factor to sane range
    verdict.size_factor = max(0.1, min(3.0, verdict.size_factor))

    return verdict


async def validate_after_trade(trade_id: int, rules_applied: list[int],
                                trade_result: str):
    """Called after trade closes to update rule accuracy.
    For BLOCK rules: can't directly validate (trade never opened).
    For BOOST rules: WIN → correct, LOSS → wrong.
    For REDUCE_SIZE: LOSS → correct (smaller loss), WIN → wrong (missed profit).
    For CONTEXT_NOTE / ADJUST_SL: skipped (no binary outcome).
    """
    from services.learning_rules import record_application, get_active_rules
    from models.database import LearningRule, async_session_factory

    if not rules_applied:
        return

    async with async_session_factory() as s:
        for rule_id in rules_applied:
            rule = await s.get(LearningRule, rule_id)
            if not rule:
                continue
            try:
                action = json.loads(rule.action or "{}")
            except Exception:
                continue
            atype = (action.get("type") or "").upper()

            was_correct: Optional[bool] = None
            if atype == "INCREASE_SIZE":
                was_correct = (trade_result == "WIN")
            elif atype == "REDUCE_SIZE":
                was_correct = (trade_result == "LOSS")
            # BLOCK: the trade never ran; can't validate directly.
            # CONTEXT_NOTE / ADJUST_SL: non-binary, skip.

            await record_application(rule_id, was_correct)


async def _is_losing_streak(n: int) -> bool:
    """Check if the last N closed trades are all losses (circuit breaker)."""
    try:
        from models.database import Trade, async_session_factory
        from sqlalchemy import select
        async with async_session_factory() as s:
            q = (select(Trade)
                 .where(Trade.status == "CLOSED")
                 .order_by(Trade.close_time.desc())
                 .limit(n))
            rows = (await s.execute(q)).scalars().all()
            if len(rows) < n:
                return False
            return all(r.result == "LOSS" for r in rows)
    except Exception:
        return False


def build_market_context(market_data: dict, symbol: str,
                          config: dict, open_trades_count: int = 0) -> dict:
    """Gather all context fields that rules can reference.
    Called by orchestrator before rule_engine.evaluate_trade."""
    from datetime import datetime
    ind = market_data.get("H1", {}).get("indicators", {}) if market_data else {}

    # Minutes to next news — computed elsewhere (news filter); default 9999 if unknown
    news_info = market_data.get("news", {}) if market_data else {}

    now = datetime.utcnow()
    hour_utc = now.hour
    weekday_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_of_week = weekday_map[now.weekday()]

    # Session from kill zones — simplified by hour_utc
    if 7 <= hour_utc < 12:
        session = "London"
    elif 12 <= hour_utc < 17:
        session = "NewYork"
    elif 0 <= hour_utc < 7:
        session = "Asian"
    else:
        session = "Off"

    return {
        "symbol": symbol,
        "session": session,
        "hour_utc": hour_utc,
        "day_of_week": day_of_week,
        "minutes_to_next_news": news_info.get("minutes_to_next", 9999),
        "news_impact": news_info.get("impact", "none"),
        "htf_trend": ind.get("trend", "unknown"),
        "atr_pips_h1": ind.get("atr_pips", 0),
        "spread_pips": ind.get("spread_pips", 0),
        "daily_range_used_pct": ind.get("daily_range_used_pct", 0),
        "open_trades_count": open_trades_count,
    }
