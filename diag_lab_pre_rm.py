"""Why does lab never reach RM? Inspect last 4h of cycles, ICTEA bias,
strategies, broadcasts to find where the flow exits."""
import os, sys, json, asyncio
from datetime import datetime, timedelta
from collections import Counter
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import AgentLog, async_session_factory
from sqlalchemy import select, desc

async def main():
    cutoff = datetime.utcnow() - timedelta(hours=4)
    async with async_session_factory() as s:
        rows = await s.execute(
            select(AgentLog).where(AgentLog.timestamp >= cutoff)
            .order_by(desc(AgentLog.timestamp))
        )
        items = rows.scalars().all()

    by_action = Counter()
    by_agent_action = Counter()
    for x in items:
        by_action[x.action] += 1
        by_agent_action[(x.agent_name, x.action)] += 1
    print(f"Total log events last 4h: {len(items)}")
    print("\nBy (agent, action):")
    for (a, ac), n in by_agent_action.most_common(15):
        print(f"  {a:8s} {ac:20s} {n}")

    # Look at ICTEA outputs
    print("\nLast 5 ICTEA analyses:")
    ictea = [x for x in items if x.agent_name == "ICTEA"][:5]
    for x in ictea:
        try:
            d = json.loads(x.data) if x.data else {}
        except Exception:
            d = {}
        sym = (x.message or "").split()[1] if len(((x.message or "").split())) > 1 else "?"
        print(f"  {str(x.timestamp)[:19]} {sym}: bias={d.get('bias')} strategies={len(d.get('strategies', []))}")
        for s in d.get('strategies', [])[:2]:
            print(f"      - setup={s.get('setup')} prob={s.get('probability')}")

    # Were there REJECTED events from SYS or RULE_ENGINE?
    rejects = [x for x in items if x.action in ("REJECTED", "RULE_BLOCK")]
    print(f"\nReject events: {len(rejects)}")
    for r in rejects[:10]:
        print(f"  {str(r.timestamp)[:19]} {r.agent_name} {r.action} {(r.message or '')[:120]}")

    # Open trades right now
    from models.database import Trade
    async with async_session_factory() as s:
        active = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
        active = active.scalars().all()
    print(f"\nLAB ACTIVE trades right now: {len(active)}")
    for t in active:
        print(f"  #{t.id} {t.symbol} {t.direction} open={str(t.open_time)[:19]}")

asyncio.run(main())
