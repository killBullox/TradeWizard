"""Lab morning report — same shape as the prod report, reads tradewizard_lab.db."""
import os, sys, json, asyncio
from collections import Counter
from datetime import datetime
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, AgentLog, async_session_factory
from sqlalchemy import select, desc


async def main():
    today = datetime.utcnow().date()
    cutoff = datetime.combine(today, datetime.min.time())

    async with async_session_factory() as s:
        rows = await s.execute(select(Trade).where(Trade.created_at >= cutoff).order_by(desc(Trade.created_at)))
        trades = rows.scalars().all()
        rows = await s.execute(select(AgentLog).where(AgentLog.timestamp >= cutoff).order_by(desc(AgentLog.timestamp)))
        logs = rows.scalars().all()

    print(f"=== LAB Morning report for {today} UTC ===\n")
    print(f"Trades created today: {len(trades)}")
    by_status = Counter(t.status for t in trades)
    for st, n in by_status.items():
        print(f"  {st:12s} {n}")
    if trades:
        print()
        for t in trades[:10]:
            print(f"  #{t.id} {t.symbol} {t.direction} {t.status} setup={t.ict_setup}  paper={t.is_paper}  "
                  f"open={str(t.open_time)[:19]} close={str(t.close_time)[:19] if t.close_time else '-'}  pnl_usd={t.pnl_usd}")

    print()
    print(f"Agent log events today: {len(logs)}")
    by_action = Counter(l.action for l in logs)
    for a, n in by_action.most_common(20):
        print(f"  {a:25s} {n}")

    # RM evaluations breakdown
    print()
    rm_evals = [l for l in logs if l.agent_name == "RM" and l.action == "EVALUATION"]
    approved_n = 0
    rej_reasons = Counter()
    for e in rm_evals:
        try:
            d = json.loads(e.data) if e.data else {}
        except Exception:
            d = {}
        if d.get("approved"):
            approved_n += 1
        else:
            r = (d.get("rejection_reason") or "(no reason)")[:80]
            rej_reasons[r] += 1
    print(f"RM evaluations: {len(rm_evals)} (approved={approved_n}, rejected={len(rm_evals)-approved_n})")
    for r, n in rej_reasons.most_common(10):
        print(f"  [{n:3d}] {r}")

    # ICTEA bias
    print()
    analyses = [l for l in logs if l.action == "ANALYSIS"]
    print(f"ICTEA analyses: {len(analyses)}")
    bias_counts = Counter()
    for a in analyses:
        try:
            d = json.loads(a.data) if a.data else {}
            bias_counts[d.get("bias", "?")] += 1
        except Exception:
            pass
    for b, n in bias_counts.most_common():
        print(f"  bias={b:10s} {n}")
    if analyses:
        print(f"  first: {str(analyses[-1].timestamp)[:19]}   last: {str(analyses[0].timestamp)[:19]}")

    # Sanity check rejections (the SYS,REJECTED ones)
    print()
    sys_rej = [l for l in logs if l.action == "REJECTED"]
    print(f"SYS rejections: {len(sys_rej)}")
    by_msg = Counter()
    for r in sys_rej:
        msg = (r.message or "")[:80]
        by_msg[msg] += 1
    for m, n in by_msg.most_common(8):
        print(f"  [{n:3d}] {m}")


asyncio.run(main())
