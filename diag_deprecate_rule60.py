"""Deprecate the broken rule #60 in lab — it BLOCKs every trade because
its condition (htf_trend != 'strategy.direction') is always True given
the lexical mismatch (bullish/bearish vs BUY/SELL)."""
import os, sys, asyncio
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import LearningRule, async_session_factory
from sqlalchemy import select

async def main():
    async with async_session_factory() as s:
        r = await s.get(LearningRule, 60)
        if not r:
            print("rule #60 not found"); return
        print(f"Before: rule #{r.id} status={r.status} action={r.action[:80]}")
        r.status = "DEPRECATED"
        # also mark a few others that might be problematic with same condition
        for rid in (96,):
            r2 = await s.get(LearningRule, rid)
            if r2 and r2.status in ("ACTIVE", "CANDIDATE"):
                print(f"Also deprecating rule #{r2.id}: {(r2.description or '')[:80]}")
                r2.status = "DEPRECATED"
        await s.commit()
        print(f"After:  rule #60 status=DEPRECATED")

asyncio.run(main())
