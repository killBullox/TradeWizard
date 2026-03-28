"""
MT5 data service — calls the mt5_bridge.py REST server running on Windows.

The bridge must be running on the Windows machine with MT5:
    python mt5_bridge.py   (default port 5001)

Configure in TradeWizard:
    mt5_bridge_url = http://<windows-ip>:5001   (e.g. http://192.168.1.10:5001)
    or http://localhost:5001 if running on the same machine / WSL
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

log = logging.getLogger("mt5_data")

_DEFAULT_BRIDGE = os.getenv("MT5_BRIDGE_URL", "http://localhost:5001")


async def _get(url: str, params: dict) -> dict:
    """Async HTTP GET via aiohttp."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params,
                               timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Bridge {resp.status}: {text[:200]}")
            return await resp.json(content_type=None)


async def fetch_ohlcv(symbol: str, timeframe: str = "H1", limit: int = 500,
                      bridge_url: str = "") -> dict:
    """
    Fetch OHLCV candles from the MT5 bridge.
    Falls back to OANDA → yfinance if bridge unreachable.
    """
    bridge_url = (bridge_url or _DEFAULT_BRIDGE).rstrip("/")
    try:
        data = await _get(f"{bridge_url}/candles",
                          {"symbol": symbol, "timeframe": timeframe, "count": limit})
        candles = data.get("candles", [])
        if not candles:
            raise RuntimeError("empty candles from bridge")
        log.info("MT5 bridge: %d %s %s candles", len(candles), symbol, timeframe)
        return {"symbol": symbol, "timeframe": timeframe,
                "candles": candles[-limit:], "indicators": {}}
    except Exception as exc:
        log.warning("MT5 bridge unreachable (%s), falling back to OANDA/yfinance: %s",
                    bridge_url, exc)
        # Fallback chain: OANDA → yfinance
        from services.oanda_data import fetch_ohlcv as _oanda
        return await _oanda(symbol, timeframe, limit)


async def fetch_m1_for_period(symbol: str, start_dt: datetime, end_dt: datetime,
                               bridge_url: str = "") -> list[dict]:
    """
    Fetch M1 candles for start_dt → end_dt from the MT5 bridge.
    Returns [] if bridge unreachable (backtester falls back to OHLC estimation).
    """
    bridge_url = (bridge_url or _DEFAULT_BRIDGE).rstrip("/")

    all_candles: list[dict] = []
    chunk_hours = 24          # fetch 1 day at a time to avoid huge responses
    current = start_dt

    while current < end_dt:
        chunk_end = min(current + timedelta(hours=chunk_hours), end_dt)
        try:
            data = await _get(f"{bridge_url}/candles/range", {
                "symbol":    symbol,
                "timeframe": "M1",
                "from_ts":   current.strftime("%Y-%m-%dT%H:%M:%S"),
                "to_ts":     chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            chunk = data.get("candles", [])
            all_candles.extend(chunk)
            current = chunk_end
        except Exception as exc:
            log.warning("M1 range fetch failed (%s → %s): %s", current, chunk_end, exc)
            break

    log.info("MT5 bridge M1: %d candles for %s [%s → %s]",
             len(all_candles), symbol,
             start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    return all_candles


async def check_bridge(bridge_url: str = "") -> dict:
    """Ping the bridge /health endpoint. Returns status dict."""
    bridge_url = (bridge_url or _DEFAULT_BRIDGE).rstrip("/")
    try:
        return await _get(f"{bridge_url}/health", {})
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}
