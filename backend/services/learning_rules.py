"""
learning_rules.py — Ingest, lifecycle, and lookup for learning rules.

Rules are JSON-structured trading constraints extracted from meetings:
  { rule_type, setup_type, symbol, session, condition, action, confidence, ... }

Lifecycle: CANDIDATE → ACTIVE → CONFIRMED → DEPRECATED
  - CANDIDATE: just ingested, not yet applied
  - ACTIVE: applied to trades; accuracy being measured
  - CONFIRMED: proven effective (>=5 applications, >=60% accuracy)
  - DEPRECATED: proven harmful or obsolete (>=10 applications, <40% accuracy)

Auto-activation: a CANDIDATE with confidence>=0.5 and sample_size>=5 is
activated automatically.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("learning_rules")


# Minimum thresholds for automatic lifecycle transitions.
# Raised after 2026-04-28 audit: sample=5 was too low — real-world (setup ×
# symbol × session) cells accumulate 1-2 trades per week, so rules became
# ACTIVE on n=1 and never had enough subsequent data to be CONFIRMED. The
# system ended up with 22 ACTIVE rules from single losing trades, all
# blocking trade flow. Threshold doubled to 10 so a rule has to survive
# more than one anecdotal observation before it gates real money.
AUTO_ACTIVATE_MIN_CONFIDENCE = 0.5
AUTO_ACTIVATE_MIN_SAMPLE = 10
CONFIRM_MIN_APPLICATIONS = 5
CONFIRM_MIN_ACCURACY = 0.60
DEPRECATE_MIN_APPLICATIONS = 10
DEPRECATE_MAX_ACCURACY = 0.40


async def ingest_proposed_rules(proposed: list[dict], source_type: str = "MEETING",
                                  source_id: Optional[int] = None) -> list[int]:
    """Save proposed rules as CANDIDATE. Returns list of created rule IDs.
    If a rule with identical scope+condition+action already exists, increment
    its sample_size and bump confidence instead of creating a duplicate."""
    if not proposed:
        return []
    from models.database import LearningRule, async_session_factory
    from sqlalchemy import select

    created_ids = []
    async with async_session_factory() as s:
        for p in proposed:
            rule_type = (p.get("rule_type") or "").upper()
            if rule_type not in ("FILTER", "BOOST", "BLOCK", "ADJUST_PARAM", "CONTEXT_NOTE"):
                log.warning("Rejecting rule with invalid type: %s", rule_type)
                continue

            condition = p.get("condition") or {}
            action = p.get("action") or {}
            if not action:
                log.warning("Rejecting rule with empty action: %s", p)
                continue

            setup_type = p.get("setup_type") or None
            symbol = p.get("symbol") or None
            session = p.get("session") or None
            cond_json = json.dumps(condition, sort_keys=True)
            act_json = json.dumps(action, sort_keys=True)

            # Dedup: same scope+condition+action
            q = select(LearningRule).where(
                LearningRule.rule_type == rule_type,
                LearningRule.setup_type == setup_type,
                LearningRule.symbol == symbol,
                LearningRule.session == session,
                LearningRule.condition == cond_json,
                LearningRule.action == act_json,
            )
            existing = (await s.execute(q)).scalar_one_or_none()
            if existing:
                existing.sample_size += int(p.get("sample_size", 1))
                existing.confidence = min(1.0, existing.confidence + 0.1)
                log.info("Reinforced existing rule #%d (samples→%d, conf→%.2f)",
                         existing.id, existing.sample_size, existing.confidence)
                # Re-check auto-activation
                if (existing.status == "CANDIDATE" and
                    existing.confidence >= AUTO_ACTIVATE_MIN_CONFIDENCE and
                    existing.sample_size >= AUTO_ACTIVATE_MIN_SAMPLE):
                    existing.status = "ACTIVE"
                    existing.activated_at = datetime.utcnow()
                    log.info("Rule #%d auto-activated", existing.id)
                continue

            # New candidate
            rule = LearningRule(
                rule_type=rule_type,
                setup_type=setup_type,
                symbol=symbol,
                session=session,
                condition=cond_json,
                action=act_json,
                confidence=float(p.get("confidence", 0.5)),
                sample_size=int(p.get("sample_size", 1)),
                source_type=source_type,
                source_id=source_id,
                description=p.get("description") or p.get("evidence"),
                status="CANDIDATE",
            )
            # Auto-activate if strong enough
            if (rule.confidence >= AUTO_ACTIVATE_MIN_CONFIDENCE and
                rule.sample_size >= AUTO_ACTIVATE_MIN_SAMPLE):
                rule.status = "ACTIVE"
                rule.activated_at = datetime.utcnow()
            s.add(rule)
            await s.flush()
            created_ids.append(rule.id)
            log.info("Ingested rule #%d (%s %s/%s/%s status=%s)",
                     rule.id, rule.rule_type, rule.setup_type, rule.symbol,
                     rule.session, rule.status)
        await s.commit()
    return created_ids


async def get_active_rules(setup_type: Optional[str] = None,
                           symbol: Optional[str] = None,
                           session: Optional[str] = None) -> list:
    """Return all ACTIVE and CONFIRMED rules that could apply to the given scope.
    A rule applies if its scope field is None OR matches the argument."""
    from models.database import LearningRule, async_session_factory
    from sqlalchemy import select, or_
    async with async_session_factory() as s:
        q = select(LearningRule).where(
            LearningRule.status.in_(["ACTIVE", "CONFIRMED"]),
        )
        rows = (await s.execute(q)).scalars().all()

    matching = []
    for r in rows:
        if r.setup_type and setup_type and r.setup_type != setup_type:
            continue
        if r.symbol and symbol and r.symbol != symbol:
            continue
        if r.session and session and r.session != session:
            continue
        matching.append(r)
    return matching


async def record_application(rule_id: int, was_correct: Optional[bool] = None):
    """Called after a trade where rule was applied, to track accuracy.
    was_correct=True  — rule's prediction matched outcome (good rule)
    was_correct=False — rule's prediction was wrong (bad rule)
    was_correct=None  — rule applied but we can't tell if it was correct
    """
    from models.database import LearningRule, async_session_factory
    async with async_session_factory() as s:
        rule = await s.get(LearningRule, rule_id)
        if not rule:
            return
        rule.times_applied += 1
        if was_correct is True:
            rule.times_correct += 1
        elif was_correct is False:
            rule.times_wrong += 1

        # Auto-lifecycle
        total_feedback = rule.times_correct + rule.times_wrong
        if total_feedback > 0:
            accuracy = rule.times_correct / total_feedback
            if (rule.status == "ACTIVE" and
                total_feedback >= CONFIRM_MIN_APPLICATIONS and
                accuracy >= CONFIRM_MIN_ACCURACY):
                rule.status = "CONFIRMED"
                rule.confirmed_at = datetime.utcnow()
                log.info("Rule #%d CONFIRMED (accuracy=%.2f over %d)",
                         rule.id, accuracy, total_feedback)
            elif (rule.status in ("ACTIVE", "CONFIRMED") and
                  total_feedback >= DEPRECATE_MIN_APPLICATIONS and
                  accuracy < DEPRECATE_MAX_ACCURACY):
                rule.status = "DEPRECATED"
                rule.deprecated_at = datetime.utcnow()
                log.warning("Rule #%d DEPRECATED (accuracy=%.2f over %d)",
                            rule.id, accuracy, total_feedback)
        await s.commit()


async def activate_rule(rule_id: int):
    from models.database import LearningRule, async_session_factory
    async with async_session_factory() as s:
        rule = await s.get(LearningRule, rule_id)
        if rule and rule.status == "CANDIDATE":
            rule.status = "ACTIVE"
            rule.activated_at = datetime.utcnow()
            await s.commit()


async def deprecate_rule(rule_id: int, reason: str = ""):
    from models.database import LearningRule, async_session_factory
    async with async_session_factory() as s:
        rule = await s.get(LearningRule, rule_id)
        if rule:
            rule.status = "DEPRECATED"
            rule.deprecated_at = datetime.utcnow()
            if reason:
                rule.description = (rule.description or "") + f"\nDeprecated: {reason}"
            await s.commit()
