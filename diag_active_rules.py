"""List ACTIVE/CONFIRMED rules in lab — these are the ones actually
blocking trades (CANDIDATE rules don't apply yet)."""
import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import LearningRule, async_session_factory
from sqlalchemy import select, desc

async def main():
    async with async_session_factory() as s:
        rows = await s.execute(
            select(LearningRule)
            .where(LearningRule.status.in_(("ACTIVE", "CONFIRMED")))
            .order_by(desc(LearningRule.created_at))
        )
        rules = rows.scalars().all()
    print(f"Total ACTIVE/CONFIRMED rules: {len(rules)}\n")
    for r in rules:
        try:
            cond = json.loads(r.condition or '{}')
            act  = json.loads(r.action or '{}')
        except Exception:
            cond, act = {}, {}
        print(f"#{r.id} {r.status:9s} {r.rule_type:12s} setup={r.setup_type!r} sym={r.symbol!r} sess={r.session!r}")
        print(f"   cond: {cond}")
        print(f"   action: {act}")
        print(f"   conf={r.confidence} n={r.sample_size}  applications={r.applications_count}  accuracy={r.accuracy}")
        print(f"   created={str(r.created_at)[:16]}  desc={(r.description or '')[:80]}")
        print()

asyncio.run(main())
