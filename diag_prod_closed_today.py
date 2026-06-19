"""Today's prod trades — what closed, when, why."""
import os, sys, json, asyncio
from datetime import datetime
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, async_session_factory
from sqlalchemy import select, desc

async def main():
    cutoff = datetime(2026, 4, 28, 0, 0)
    async with async_session_factory() as s:
        rows = await s.execute(
            select(Trade).where(Trade.created_at >= cutoff).order_by(Trade.id)
        )
        trades = rows.scalars().all()
    print(f"Prod trades created today (UTC): {len(trades)}\n")
    for t in trades:
        sl_pips = abs((t.entry_price or 0) - (t.stop_loss or 0))
        tp_pips = abs((t.entry_price or 0) - (t.take_profit_1 or 0))
        ot = str(t.open_time)[:19] if t.open_time else "?"
        ct = str(t.close_time)[:19] if t.close_time else "-"
        notes = (t.close_notes or "")[:120]
        print(f"#{t.id} {t.symbol} {t.direction} {t.status:8s} {t.result or '-':10s}  "
              f"entry={t.entry_price} sl={t.stop_loss} tp1={t.take_profit_1} close={t.close_price}")
        print(f"    open={ot}  close={ct}  pnl_usd={t.pnl_usd}  pnl_pips={t.pnl_pips}")
        print(f"    close_notes: {notes.encode('ascii','replace').decode('ascii')}")
        print()

asyncio.run(main())
