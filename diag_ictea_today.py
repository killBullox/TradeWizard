"""ICTEA bias breakdown — last 4h, both modes."""
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
            .where(AgentLog.action == "ANALYSIS")
            .order_by(desc(AgentLog.timestamp))
        )
        items = rows.scalars().all()
    print(f'\n=== {mode.upper()} - ICTEA analyses last 4h ===')
    bias = Counter()
    strategies_count = Counter()
    for x in items:
        try:
            d = json.loads(x.data) if x.data else {}
        except Exception:
            d = {}
        bias[d.get('bias', '?')] += 1
        strategies_count[len(d.get('strategies', []))] += 1
    print(f'  total: {len(items)}')
    for b, n in bias.most_common():
        print(f'    bias={b:10s} {n}')
    print(f'  strategies count distribution:')
    for n_strats, freq in sorted(strategies_count.items()):
        print(f'    {n_strats} strategies: {freq} cycles')
    # Last 3 with full data
    print(f'  Last 3 analyses:')
    for x in items[:3]:
        try:
            d = json.loads(x.data) if x.data else {}
        except Exception:
            d = {}
        sym = (x.message or '').split()[1] if len(((x.message or '').split())) > 1 else '?'
        n_strats = len(d.get('strategies', []))
        print(f'    {str(x.timestamp)[:19]} {sym:10s} bias={d.get("bias","?")}  strategies={n_strats}')

async def main():
    await show('production')
    await show('lab')

asyncio.run(main())
