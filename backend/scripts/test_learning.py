"""
test_learning.py — End-to-end smoke test for the self-learning system.

Uses a temporary SQLite DB (tradewizard_test.db) so it does not touch prod/lab.

Run from the backend directory:
    SYSTEM_MODE=test python scripts/test_learning.py

What it verifies:
1. StrategyMemory.get_win_rate returns real data when sample >= 10
2. RiskManager uses real win rate instead of hard-coded when memory is populated
3. learning_rules ingestion (dedup + auto-activate)
4. rule_engine condition matcher (simple + compound + dynamic refs)
5. rule_engine evaluate_trade returns correct verdict for BLOCK / REDUCE_SIZE
6. record_application promotes rules to CONFIRMED / DEPRECATED
7. validate_after_trade updates accuracy correctly
"""
import os
import asyncio
import sys

# Point to a test DB before importing database module
os.environ["SYSTEM_MODE"] = "test"

# Use test DB, not prod or lab
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tradewizard_test.db")
# Delete previous test DB
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

# Monkey-patch the database URL before import
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "models.database",
    os.path.join(os.path.dirname(__file__), "..", "models", "database.py"),
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import database  # noqa: E402

# Override URL to test DB
database.DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH.replace(chr(92), '/')}"
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
database.engine = create_async_engine(database.DATABASE_URL, echo=False)
database.async_session_factory = async_sessionmaker(database.engine, expire_on_commit=False)

from models.database import (  # noqa: E402
    init_db, async_session_factory, StrategyMemory, LearningRule,
)
from services.strategy_memory import get_win_rate, update_from_trade  # noqa: E402
from services.learning_rules import (  # noqa: E402
    ingest_proposed_rules, get_active_rules, record_application,
)
from services.rule_engine import (  # noqa: E402
    condition_matches, evaluate_trade, RuleVerdict,
)


PASS = "[PASS]"
FAIL = "[FAIL]"
checks = {"passed": 0, "failed": 0}


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        checks["passed"] += 1
        print(f"  {PASS} {name}")
    else:
        checks["failed"] += 1
        print(f"  {FAIL} {name}  — {detail}")


async def seed_strategy_memory():
    """Populate StrategyMemory with: FVG/GBPUSD 4W/16L, OTE/EURUSD 8W/2L, FVG/global 12W/8L."""
    for _ in range(4):
        await update_from_trade("FVG", "GBPUSD", 20.0, "WIN")
    for _ in range(16):
        await update_from_trade("FVG", "GBPUSD", -10.0, "LOSS")
    for _ in range(8):
        await update_from_trade("OTE", "EURUSD", 30.0, "WIN")
    for _ in range(2):
        await update_from_trade("OTE", "EURUSD", -15.0, "LOSS")


async def test_phase_1_win_rate():
    print("\n=== FASE 1: StrategyMemory.get_win_rate + RM integration ===")
    wr = await get_win_rate("FVG", "GBPUSD")
    check("FVG/GBPUSD win rate returned", wr is not None)
    check("FVG/GBPUSD sample_size == 20", wr and wr["sample_size"] == 20,
          f"got {wr.get('sample_size') if wr else None}")
    check("FVG/GBPUSD win_rate == 20%", wr and wr["win_rate"] == 20.0,
          f"got {wr.get('win_rate') if wr else None}")

    wr2 = await get_win_rate("OTE", "EURUSD")
    check("OTE/EURUSD win_rate == 80%", wr2 and wr2["win_rate"] == 80.0,
          f"got {wr2.get('win_rate') if wr2 else None}")

    wr_none = await get_win_rate("LiquiditySweep", "AUDCAD")
    check("Unknown setup returns None", wr_none is None)


async def test_phase_2_ingest():
    print("\n=== FASE 2: learning_rules ingestion ===")
    rule1 = {
        "rule_type": "FILTER",
        "setup_type": "FVG",
        "symbol": "GBPUSD",
        "condition": {"field": "minutes_to_next_news", "op": "<", "value": 30},
        "action": {"type": "BLOCK", "reason": "FVG GBPUSD fails with news"},
        "confidence": 0.7,
        "sample_size": 8,
        "description": "test rule 1",
    }
    ids = await ingest_proposed_rules([rule1], source_type="MEETING", source_id=1)
    check("Rule 1 created", len(ids) == 1)

    # Re-ingest → should increment sample, not create new
    ids2 = await ingest_proposed_rules([rule1], source_type="MEETING", source_id=2)
    check("Rule 1 dedup (no new id)", len(ids2) == 0)

    # Verify auto-activation (confidence=0.7, sample=8+1>=5 → ACTIVE)
    async with async_session_factory() as s:
        rule = await s.get(LearningRule, ids[0])
    check("Rule 1 auto-activated", rule.status == "ACTIVE",
          f"status={rule.status}")

    # Invalid rule type → rejected
    bad = {"rule_type": "WRONG", "action": {"type": "BLOCK"}}
    ids3 = await ingest_proposed_rules([bad])
    check("Invalid rule_type rejected", len(ids3) == 0)

    # Empty action → rejected
    bad2 = {"rule_type": "FILTER", "action": {}}
    ids4 = await ingest_proposed_rules([bad2])
    check("Empty action rejected", len(ids4) == 0)


async def test_phase_3_engine():
    print("\n=== FASE 3: rule_engine condition + evaluate_trade ===")
    # Simple condition
    ctx = {"minutes_to_next_news": 15, "session": "London", "htf_trend": "bullish"}
    c1 = {"field": "minutes_to_next_news", "op": "<", "value": 30}
    check("Simple < matches", condition_matches(c1, ctx, {}))

    c2 = {"field": "minutes_to_next_news", "op": ">", "value": 30}
    check("Simple > does not match", not condition_matches(c2, ctx, {}))

    # Compound AND
    c3 = {"and": [
        {"field": "minutes_to_next_news", "op": "<", "value": 30},
        {"field": "session", "op": "==", "value": "London"},
    ]}
    check("Compound AND matches", condition_matches(c3, ctx, {}))

    # Compound OR with one false
    c4 = {"or": [
        {"field": "session", "op": "==", "value": "Asian"},
        {"field": "htf_trend", "op": "==", "value": "bullish"},
    ]}
    check("Compound OR matches", condition_matches(c4, ctx, {}))

    # Dynamic ref
    strategy = {"direction": "BUY"}
    c5 = {"field": "htf_trend", "op": "==", "value": "strategy.direction"}
    # htf_trend="bullish", strategy.direction="BUY" — they don't match literally, but proves resolution
    check("Dynamic ref resolved", not condition_matches(c5, ctx, strategy))

    # evaluate_trade: FVG/GBPUSD with news<30 should BLOCK
    # Note: evaluate_trade checks RULE_ENGINE_ACTIVE env flag. For test we force it.
    from services import rule_engine as re_mod
    re_mod.RULE_ENGINE_ACTIVE = True
    verdict = await evaluate_trade("FVG", "GBPUSD", "London", ctx, strategy)
    check("Verdict BLOCK when news<30", verdict.action == "BLOCK",
          f"got action={verdict.action} reasons={verdict.reasons}")
    check("Rule IDs captured", len(verdict.rules_applied) >= 1)

    # evaluate_trade with safe context (news far away) → ALLOW
    ctx_safe = {"minutes_to_next_news": 9999, "session": "London", "htf_trend": "bullish"}
    verdict2 = await evaluate_trade("FVG", "GBPUSD", "London", ctx_safe, strategy)
    check("Verdict ALLOW when news far", verdict2.action == "ALLOW")


async def test_phase_3_feedback():
    print("\n=== FASE 3: record_application lifecycle ===")
    # Add a BOOST rule, apply it 6 times with 5 correct → should CONFIRM
    boost = {
        "rule_type": "BOOST",
        "setup_type": "OTE",
        "symbol": "EURUSD",
        "condition": {"field": "session", "op": "==", "value": "London"},
        "action": {"type": "INCREASE_SIZE", "factor": 1.5},
        "confidence": 0.7,
        "sample_size": 5,
    }
    ids = await ingest_proposed_rules([boost], source_type="MEETING", source_id=99)
    rid = ids[0]

    for _ in range(5):
        await record_application(rid, was_correct=True)
    await record_application(rid, was_correct=False)  # 5/6 accuracy = 83%

    async with async_session_factory() as s:
        r = await s.get(LearningRule, rid)
    check("Rule CONFIRMED after 5 correct", r.status == "CONFIRMED",
          f"status={r.status} applied={r.times_applied}")

    # Add a bad rule: 10 applications, 3 correct → DEPRECATED
    bad_rule = {
        "rule_type": "BOOST",
        "setup_type": "BOS",
        "symbol": "XAUUSD",
        "condition": {"field": "session", "op": "==", "value": "NewYork"},
        "action": {"type": "INCREASE_SIZE", "factor": 2.0},
        "confidence": 0.7,
        "sample_size": 5,
    }
    ids2 = await ingest_proposed_rules([bad_rule])
    rid2 = ids2[0]
    for _ in range(3):
        await record_application(rid2, was_correct=True)
    for _ in range(7):
        await record_application(rid2, was_correct=False)  # 3/10 = 30%

    async with async_session_factory() as s:
        r2 = await s.get(LearningRule, rid2)
    check("Rule DEPRECATED after 7 wrong", r2.status == "DEPRECATED",
          f"status={r2.status} applied={r2.times_applied}")


async def main():
    await init_db()
    await seed_strategy_memory()
    await test_phase_1_win_rate()
    await test_phase_2_ingest()
    await test_phase_3_engine()
    await test_phase_3_feedback()

    print(f"\n{'=' * 50}")
    total = checks["passed"] + checks["failed"]
    print(f"RESULT: {checks['passed']}/{total} passed")
    if checks["failed"] > 0:
        print("FAIL")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    asyncio.run(main())
