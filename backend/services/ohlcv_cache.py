"""
ohlcv_cache.py — Local OHLCV bar cache backed by SQLite.

Eliminates repeated API calls for the same historical data:
- upsert_candles()       → bulk-insert candles, skip duplicates
- get_cached_candles()   → read from DB with optional date/bar filter
- get_latest_time()      → find newest stored bar timestamp
- get_cache_info()       → summary per (symbol, timeframe)
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

log = logging.getLogger("ohlcv_cache")


async def upsert_candles(symbol: str, timeframe: str, candles: list[dict]) -> int:
    """Bulk-insert candles; silently skip duplicates. Returns # rows inserted."""
    if not candles:
        return 0
    from models.database import OhlcvBar, async_session_factory
    from sqlalchemy.dialects.sqlite import insert as _ins

    sym = symbol.upper()
    inserted = 0
    BATCH = 500

    async with async_session_factory() as s:
        for i in range(0, len(candles), BATCH):
            batch = candles[i : i + BATCH]
            vals = [
                {
                    "symbol": sym, "timeframe": timeframe,
                    "time":   c["time"],
                    "open":   float(c["open"]),  "high": float(c["high"]),
                    "low":    float(c["low"]),   "close": float(c["close"]),
                    "volume": int(c.get("volume", 0)),
                }
                for c in batch
            ]
            stmt   = _ins(OhlcvBar).values(vals).on_conflict_do_nothing()
            result = await s.execute(stmt)
            inserted += result.rowcount or 0
            await s.commit()

    return inserted


async def get_cached_candles(
    symbol: str,
    timeframe: str,
    n_bars: int = None,
    date_from: str = None,
    date_to: str = None,
) -> list[dict]:
    """
    Return cached bars as list[dict] matching the OANDA/MT5 candle schema.
    If date_from is None and n_bars is given, returns the *last* n_bars rows.
    """
    from models.database import OhlcvBar, async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as s:
        q = (
            select(OhlcvBar)
            .where(OhlcvBar.symbol == symbol.upper(), OhlcvBar.timeframe == timeframe)
            .order_by(OhlcvBar.time.asc())
        )
        if date_from:
            q = q.where(OhlcvBar.time >= date_from)
        if date_to:
            dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)
            q = q.where(OhlcvBar.time < dt_to.isoformat())

        rows = (await s.execute(q)).scalars().all()

    if not rows:
        return []

    candles = [
        {"time": r.time, "open": r.open, "high": r.high,
         "low": r.low, "close": r.close, "volume": r.volume}
        for r in rows
    ]

    # Without a date_from, honour n_bars by taking the tail
    if n_bars and not date_from and len(candles) > n_bars:
        candles = candles[-n_bars:]

    return candles


async def get_latest_time(symbol: str, timeframe: str) -> Optional[str]:
    """Return ISO timestamp of the most recent cached bar, or None."""
    from models.database import OhlcvBar, async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as s:
        q = (
            select(OhlcvBar.time)
            .where(OhlcvBar.symbol == symbol.upper(), OhlcvBar.timeframe == timeframe)
            .order_by(OhlcvBar.time.desc())
            .limit(1)
        )
        return (await s.execute(q)).scalar_one_or_none()


async def get_earliest_time(symbol: str, timeframe: str) -> Optional[str]:
    """Return ISO timestamp of the oldest cached bar, or None."""
    from models.database import OhlcvBar, async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as s:
        q = (
            select(OhlcvBar.time)
            .where(OhlcvBar.symbol == symbol.upper(), OhlcvBar.timeframe == timeframe)
            .order_by(OhlcvBar.time.asc())
            .limit(1)
        )
        return (await s.execute(q)).scalar_one_or_none()


async def get_cache_info() -> list[dict]:
    """Summary of cached data: one row per (symbol, timeframe) with bar counts."""
    from models.database import OhlcvBar, async_session_factory
    from sqlalchemy import select, func

    async with async_session_factory() as s:
        q = select(
            OhlcvBar.symbol, OhlcvBar.timeframe,
            func.count(OhlcvBar.id).label("bars"),
            func.min(OhlcvBar.time).label("from_time"),
            func.max(OhlcvBar.time).label("to_time"),
        ).group_by(OhlcvBar.symbol, OhlcvBar.timeframe).order_by(
            OhlcvBar.symbol, OhlcvBar.timeframe
        )
        rows = (await s.execute(q)).all()

    return [
        {"symbol": r.symbol, "timeframe": r.timeframe,
         "bars": r.bars, "from": r.from_time, "to": r.to_time}
        for r in rows
    ]
