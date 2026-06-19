"""Last 15 rejections (any agent) in both prod and lab DBs, with timestamp.
Reveals what is currently blocking trades right now."""
import os, sys, json, asyncio
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy import select, desc

async def show(mode):
    os.environ['SYSTEM_MODE'] = mode
    if 'models.database' in sys.modules:
        del sys.modules['models.database']
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
    from models.database import AgentLog, async_session_factory
    cutoff = datetime.utcnow() - timedelta(hours=4)
    async with async_session_factory() as s:
        rows = await s.execute(
            select(AgentLog).where(AgentLog.timestamp >= cutoff)
            .where(AgentLog.action.in_(("REJECTED", "EVALUATION")))
            .order_by(desc(AgentLog.timestamp)).limit(40)
        )
        items = rows.scalars().all()
    print(f'\n=== {mode.upper()} - last 4h rejection / evaluation events ===')
    n_total = len(items)
    rm_eval_total = 0
    rm_approved = 0
    rm_rejected_reasons = Counter()
    sys_rejected_reasons = Counter()
    for x in items:
        if x.agent_name == 'RM' and x.action == 'EVALUATION':
            rm_eval_total += 1
            try:
                d = json.loads(x.data) if x.data else {}
            except Exception:
                d = {}
            if d.get('approved'):
                rm_approved += 1
            else:
                r = (d.get('rejection_reason') or '?')[:80]
                rm_rejected_reasons[r] += 1
        elif x.action == 'REJECTED':
            sys_rejected_reasons[(x.message or '?')[:90]] += 1
    print(f'  RM evals: {rm_eval_total} (approved={rm_approved}, rejected={rm_eval_total-rm_approved})')
    for r, n in rm_rejected_reasons.most_common(5):
        print(f'    [{n}] {r}')
    print(f'  SYS rejected: {sum(sys_rejected_reasons.values())}')
    for r, n in sys_rejected_reasons.most_common(5):
        print(f'    [{n}] {r}')
    print(f'  Last 5 events:')
    for x in items[:5]:
        try:
            d = json.loads(x.data) if x.data else {}
        except Exception:
            d = {}
        ok = d.get('approved')
        reason = d.get('rejection_reason', '') or x.message or ''
        print(f'    {str(x.timestamp)[:19]} {x.agent_name:6s} {x.action:12s}  approved={ok}  {reason[:120]}')

async def main():
    await show('production')
    await show('lab')

asyncio.run(main())
