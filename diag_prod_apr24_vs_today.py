"""Compare prod config + trade flow between 2026-04-24 and 2026-04-27."""
import os, sys, json, asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_

os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, AgentLog, Meeting, async_session_factory


async def main():
    async with async_session_factory() as s:
        # --- TRADES on Apr 24 ---
        t24 = await s.execute(
            select(Trade).where(Trade.created_at >= datetime(2026, 4, 24))
            .where(Trade.created_at < datetime(2026, 4, 25))
            .order_by(Trade.created_at)
        )
        trades24 = t24.scalars().all()
        print(f"=== Trades created 2026-04-24 in prod: {len(trades24)} ===")
        for t in trades24:
            sl_pips = abs((t.entry_price or 0) - (t.stop_loss or 0))
            tp_pips = abs((t.entry_price or 0) - (t.take_profit_1 or 0))
            ratio = (tp_pips / sl_pips) if sl_pips else 0
            mc_str = "?"
            try:
                mc = json.loads(t.market_context or "{}")
                mc_str = f"ATR={mc.get('atr_pips_h1', '?')}p sess={mc.get('session', '?')}"
            except Exception:
                pass
            print(f"  #{t.id:3d} {str(t.created_at)[:16]} {t.symbol:8s} {t.direction:4s} {t.status:9s} "
                  f"setup={t.ict_setup or '?':12s}  SL/TP/RR={sl_pips:.5f}/{tp_pips:.5f}/{ratio:.2f}  "
                  f"{mc_str}")

        # --- TRADES on Apr 27 ---
        t27 = await s.execute(
            select(Trade).where(Trade.created_at >= datetime(2026, 4, 27))
            .where(Trade.created_at < datetime(2026, 4, 28))
            .order_by(Trade.created_at)
        )
        trades27 = t27.scalars().all()
        print(f"\n=== Trades created 2026-04-27 in prod: {len(trades27)} ===")
        for t in trades27[:20]:
            print(f"  #{t.id} {str(t.created_at)[:16]} {t.symbol} {t.status}")

        # --- CONFIG CHANGES from meetings between Apr 24 and Apr 27 ---
        print("\n=== Config changes via meetings since 2026-04-24 (prod) ===")
        m = await s.execute(
            select(Meeting).where(Meeting.created_at >= datetime(2026, 4, 24))
            .order_by(Meeting.created_at)
        )
        meetings = m.scalars().all()
        for me in meetings:
            try:
                imps = json.loads(me.improvements or "[]")
            except Exception:
                imps = []
            applied = []
            for imp in imps:
                cc = imp.get("config_change") or {}
                if cc.get("key") and cc.get("new_value") is not None:
                    applied.append(f"{cc['key']}={cc['new_value']}")
            if applied:
                print(f"  Meeting #{me.id} {str(me.created_at)[:16]} {me.meeting_type:18s} -> {', '.join(applied)}")


asyncio.run(main())
