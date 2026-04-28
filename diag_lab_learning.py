"""Is the Lab actually learning? Audit 7d trades, win rate trend, rules
lifecycle, meeting cadence."""
import os, sys, json, asyncio
from datetime import datetime, timedelta
from collections import Counter, defaultdict
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, Meeting, LearningRule, async_session_factory
from sqlalchemy import select, desc, func


async def main():
    cutoff = datetime.utcnow() - timedelta(days=10)

    async with async_session_factory() as s:
        # All closed trades last 10 days
        rows = await s.execute(
            select(Trade).where(Trade.created_at >= cutoff)
            .where(Trade.status == "CLOSED")
            .order_by(Trade.close_time)
        )
        trades = rows.scalars().all()

    if not trades:
        print("No closed trades in last 10 days"); return

    # Daily P&L + win rate
    by_day = defaultdict(list)
    for t in trades:
        if t.close_time:
            by_day[t.close_time.date()].append(t)

    print("=== LAB daily P&L + win rate (last 10d, paper+real) ===")
    cum_pnl = 0.0
    print(f"{'date':12s} {'n':>3} {'wins':>4} {'WR%':>5} {'pnl_usd':>9} {'cum':>9}")
    for d in sorted(by_day.keys()):
        ts = by_day[d]
        wins = sum(1 for t in ts if (t.result or '').upper() == 'WIN')
        wr = (wins / len(ts) * 100) if ts else 0
        pnl = sum(float(t.pnl_usd or 0) for t in ts)
        cum_pnl += pnl
        print(f"{d}  {len(ts):>3} {wins:>4} {wr:>5.0f} {pnl:>+9.2f} {cum_pnl:>+9.2f}")
    print(f"\nTotal: {len(trades)} trades, cum_pnl = {cum_pnl:+.2f} USD")

    # Failure mode breakdown
    print("\n=== Failure modes (close_notes patterns) ===")
    notes = Counter()
    for t in trades:
        n = (t.close_notes or '').lower()
        if 'sl colpito' in n or 'sl hit' in n: notes['SL_HIT'] += 1
        elif 'tp' in n and 'colpito' in n: notes['TP_HIT'] += 1
        elif 'max duration' in n or 'force close' in n: notes['TIMEOUT'] += 1
        elif 'manual' in n: notes['MANUAL'] += 1
        else: notes['OTHER'] += 1
    for k, n in notes.most_common():
        print(f"  {k:12s} {n}  ({n/len(trades)*100:.0f}%)")

    # Learning rules lifecycle
    async with async_session_factory() as s:
        rules = (await s.execute(select(LearningRule))).scalars().all()
    by_status = Counter(r.status for r in rules)
    print(f"\n=== Learning rules lifecycle (total {len(rules)}) ===")
    for st, n in by_status.most_common():
        print(f"  {st:12s} {n}")
    print()
    # Confirmed rules — these should be the system's wisdom
    confirmed = [r for r in rules if r.status == 'CONFIRMED']
    print(f"CONFIRMED rules ({len(confirmed)}):")
    for r in confirmed[:5]:
        print(f"  #{r.id} {r.rule_type} {r.setup_type}/{r.symbol}/{r.session}: conf={r.confidence}")

    # Meetings
    cutoff_meetings = datetime.utcnow() - timedelta(days=5)
    async with async_session_factory() as s:
        ms = (await s.execute(
            select(Meeting).where(Meeting.created_at >= cutoff_meetings).order_by(Meeting.created_at)
        )).scalars().all()
    print(f"\n=== Meetings last 5d ({len(ms)}) ===")
    by_type = Counter(m.meeting_type for m in ms)
    for t, n in by_type.most_common():
        print(f"  {t:18s} {n}")
    # Are improvements with config_change reaching the system or stuck as narrative?
    applied_total = 0
    narrative_total = 0
    for m in ms:
        try:
            imps = json.loads(m.improvements or '[]')
        except Exception:
            imps = []
        for i in imps:
            cc = i.get('config_change') or {}
            if cc.get('key') and cc.get('new_value') is not None:
                applied_total += 1
            else:
                narrative_total += 1
    print(f"  config_changes proposed: {applied_total}  narrative-only: {narrative_total}")


asyncio.run(main())
