"""Why didn't anything trade this morning? Pulls AgentLog + Trade rows from
the prod DB, summarises by hour for today UTC, prints rejections by reason."""
import os, sys, json, asyncio
from collections import Counter
from datetime import datetime, timedelta
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, AgentLog, async_session_factory
from sqlalchemy import select, desc


async def main():
    today = datetime.utcnow().date()
    cutoff = datetime.combine(today, datetime.min.time())  # 00:00 UTC today

    async with async_session_factory() as s:
        # All trades created today
        rows = await s.execute(
            select(Trade).where(Trade.created_at >= cutoff)
            .order_by(desc(Trade.created_at))
        )
        trades = rows.scalars().all()

        # All agent log events today
        rows = await s.execute(
            select(AgentLog).where(AgentLog.timestamp >= cutoff)
            .order_by(desc(AgentLog.timestamp))
        )
        logs = rows.scalars().all()

    print(f"=== Morning report for {today} UTC ===\n")
    print(f"Trades created today: {len(trades)}")
    by_status = Counter(t.status for t in trades)
    for st, n in by_status.items():
        print(f"  {st:12s} {n}")
    if trades:
        print()
        for t in trades[:8]:
            print(f"  #{t.id} {t.symbol} {t.direction} {t.status} {t.ict_setup}  "
                  f"created={str(t.created_at)[:19]}")

    print()
    print(f"Agent log events today: {len(logs)}")
    by_action = Counter(l.action for l in logs)
    for a, n in by_action.most_common(15):
        print(f"  {a:20s} {n}")

    print()
    rejections = [l for l in logs if l.action in ("REJECTED", "RULE_BLOCK")]
    print(f"Rejections today: {len(rejections)}")
    by_reason = Counter()
    for r in rejections:
        msg = (r.message or "")[:90].split(":", 1)[-1].strip()
        # bucket by first 50 chars
        by_reason[msg[:50]] += 1
    for reason, n in by_reason.most_common(20):
        print(f"  [{n:3d}]  {reason}")

    print()
    analyses = [l for l in logs if l.action == "ANALYSIS"]
    print(f"ICTEA analyses today: {len(analyses)}")
    if analyses:
        # Try to extract bias counts
        bias_counts = Counter()
        for a in analyses:
            try:
                d = json.loads(a.data) if a.data else {}
                bias_counts[d.get("bias", "?")] += 1
            except Exception:
                pass
        for b, n in bias_counts.most_common():
            print(f"  bias={b:10s} {n}")
        print(f"  first analysis: {str(analyses[-1].timestamp)[:19]}")
        print(f"  last  analysis: {str(analyses[0].timestamp)[:19]}")


asyncio.run(main())
