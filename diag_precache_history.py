"""Pre-cache historical H1 + M1 for the walk-forward window.

Backtester uses fetch_ohlcv (count-based) which always returns the most
recent N bars from MT5. To run a backtest on October-January data we
need to pre-populate the OHLCV cache via the date-range endpoint."""
import os, sys, asyncio
from datetime import datetime
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from services.mt5_data import fetch_range
from services.ohlcv_cache import upsert_candles

SYMBOLS = ["AUDUSD", "EURUSD", "GBPJPY", "USDCAD", "USDCHF", "USDJPY"]
START = datetime(2025, 10, 28)
END   = datetime(2026, 1, 28)
BRIDGE = "http://localhost:5555"

async def main():
    for sym in SYMBOLS:
        for tf in ("H1", "M1"):
            print(f"Fetching {sym} {tf} {START.date()} -> {END.date()}...", flush=True)
            try:
                bars = await fetch_range(sym, tf, START, END, bridge_url=BRIDGE)
                if bars:
                    n = await upsert_candles(sym, tf, bars)
                    print(f"  -> {len(bars)} bars fetched, {n} new in cache")
                else:
                    print(f"  -> no bars returned")
            except Exception as exc:
                print(f"  -> ERROR: {exc}")

asyncio.run(main())
