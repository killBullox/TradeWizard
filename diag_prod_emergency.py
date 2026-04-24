"""Verify last EMERGENCY meeting improvements were actually applied to prod config."""
import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Meeting, SystemConfig, async_session_factory
from sqlalchemy import select, desc


async def main():
    async with async_session_factory() as s:
        # Most recent EMERGENCY meeting
        res = await s.execute(
            select(Meeting).where(Meeting.meeting_type == "EMERGENCY")
            .order_by(desc(Meeting.created_at)).limit(3)
        )
        meetings = res.scalars().all()
        if not meetings:
            print("NO EMERGENCY meetings in prod DB")
            return

        for m in meetings:
            print(f"=== Meeting #{m.id}  {str(m.created_at)[:19]}  trigger={m.trigger} ===")
            try:
                imps = json.loads(m.improvements or '[]')
            except Exception:
                imps = []
            print(f"improvements: {len(imps)}")
            for i, imp in enumerate(imps):
                cc = imp.get('config_change') or {}
                cat = imp.get('category', '?')
                has_cc = bool(cc and cc.get('key') and cc.get('new_value') is not None)
                desc_ = (imp.get('improvement') or '')[:140]
                if has_cc:
                    print(f"  [{i}] {cat:8s}  {cc.get('key')} = {cc.get('new_value')}")
                else:
                    print(f"  [{i}] {cat:8s}  (no config_change — discarded by applier)")
                print(f"       └─ {desc_}")

        print()
        print("=== CURRENT PROD CONFIG (keys of interest) ===")
        interesting = [
            "rm_min_sl_atr_mult", "rm_max_tp_atr_mult", "rm_min_rr_gate",
            "rm_sl_cap_atr_mult", "rm_min_sl_pips_floor",
            "min_sl_pips", "rr_ratio", "max_open_trades", "max_trade_duration_hours",
            "analysis_interval", "news_block_minutes_before", "news_block_minutes_after",
            "max_consecutive_losses",
        ]
        res = await s.execute(select(SystemConfig).where(SystemConfig.key.in_(interesting)))
        rows = {r.key: r.value for r in res.scalars().all()}
        for k in interesting:
            v = rows.get(k, "(not set)")
            print(f"  {k:35s} = {v}")


asyncio.run(main())
