"""Drill into RM evaluations today: how many approved vs rejected, and why."""
import os, sys, json, asyncio
from collections import Counter
from datetime import datetime, timedelta
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import AgentLog, async_session_factory
from sqlalchemy import select, desc


async def main():
    today = datetime.utcnow().date()
    cutoff = datetime.combine(today, datetime.min.time())
    async with async_session_factory() as s:
        rows = await s.execute(
            select(AgentLog).where(AgentLog.timestamp >= cutoff)
            .where(AgentLog.agent_name == "RM")
            .where(AgentLog.action == "EVALUATION")
            .order_by(desc(AgentLog.timestamp))
        )
        evals = rows.scalars().all()

    print(f"RM evaluations today: {len(evals)}")
    approved_n = 0
    rej_reasons = Counter()
    by_symbol = Counter()
    samples = []
    for e in evals:
        try:
            d = json.loads(e.data) if e.data else {}
        except Exception:
            d = {}
        approved = bool(d.get("approved"))
        if approved:
            approved_n += 1
        else:
            r = d.get("rejection_reason") or "(no reason)"
            rej_reasons[r[:80]] += 1
            by_symbol[(e.message or "").split()[1] if len(((e.message or "").split())) > 1 else "?"] += 1
        if len(samples) < 5:
            samples.append((e.timestamp, e.message, approved, d.get("rejection_reason", "")[:120]))

    print(f"  approved: {approved_n}")
    print(f"  rejected: {len(evals) - approved_n}")
    print()
    print("Top rejection reasons:")
    for r, n in rej_reasons.most_common(10):
        print(f"  [{n:3d}] {r}")
    print()
    print("Rejected by symbol:")
    for sym, n in by_symbol.most_common(10):
        print(f"  {sym:10s} {n}")
    print()
    print("Last 5 evaluations:")
    for ts, msg, ok, reason in samples:
        print(f"  {str(ts)[:19]} {msg}  approved={ok}  reason={reason}")


asyncio.run(main())
