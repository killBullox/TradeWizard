import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models.database import Trade, async_session_factory
from sqlalchemy import select, desc

async def main():
    async with async_session_factory() as s:
        r = await s.execute(
            select(Trade).where(Trade.status == 'CLOSED').order_by(desc(Trade.close_time)).limit(5)
        )
        for t in r.scalars().all():
            print(f"#{t.id} {t.symbol} setup={t.ict_setup!r} dir={t.direction} result={t.result}")
            print(f"   entry={t.entry_price} sl={t.stop_loss} tp1={t.take_profit_1} close={t.close_price}")
            print(f"   open={t.open_time}  close={t.close_time}")
            print(f"   pnl_usd={t.pnl_usd}  rr={t.rr_ratio}")
            mc = t.market_context or ''
            print(f"   market_context: {mc[:300] if mc else '(none)'}")
            cn = t.close_notes or ''
            print(f"   close_notes:    {cn[:200] if cn else '(none)'}")
            print()

asyncio.run(main())
