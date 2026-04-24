import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import LearningRule, async_session_factory
from sqlalchemy import select, desc

async def main():
    async with async_session_factory() as s:
        res = await s.execute(select(LearningRule).order_by(desc(LearningRule.created_at)).limit(15))
        rules = res.scalars().all()
        print(f"Total (last 15): {len(rules)}")
        for r in rules:
            print(f"#{r.id} {str(r.created_at)[:19]} {r.status:10s} {r.rule_type:10s} "
                  f"setup={r.setup_type!r} symbol={r.symbol!r} session={getattr(r,'session',None)!r}")
            try:
                act = json.loads(r.action or '{}')
                cond = json.loads(r.condition or '{}')
                print(f"     cond: {cond}")
                print(f"     action: {act}")
            except Exception:
                pass
            print(f"     desc: {(r.description or '')[:150]}")
            print(f"     source: {r.source_type} #{r.source_id}  conf={r.confidence}  n={r.sample_size}")

asyncio.run(main())
