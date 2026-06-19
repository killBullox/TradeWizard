"""Reproduce the backtester's M1 fetch path to see why the warning shows."""
import os, sys, asyncio
from datetime import datetime, timedelta
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    from services.mt5_data import fetch_m1_for_period
    from models.database import async_session_factory, get_config
    async with async_session_factory() as s:
        bridge_url = await get_config("mt5_bridge_url", s)
    print(f"DB mt5_bridge_url = {bridge_url!r}")
    print(f"env  MT5_BRIDGE_URL = {os.environ.get('MT5_BRIDGE_URL')!r}")

    # Try as backtester does
    start = datetime(2026, 4, 28, 6, 0)
    end   = datetime(2026, 4, 28, 9, 0)
    for url in (bridge_url, "http://localhost:5555"):
        if not url: continue
        print(f"\n=== fetch_m1 with bridge_url={url!r} ===")
        try:
            data = await fetch_m1_for_period("EURUSD", start, end, bridge_url=url)
            print(f"  got {len(data)} M1 candles")
            if data:
                print(f"  first: {data[0]}")
        except Exception as exc:
            print(f"  ERROR: {exc}")

asyncio.run(main())
