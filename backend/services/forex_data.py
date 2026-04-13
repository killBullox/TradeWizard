"""
Forex data service.
Fetches OHLCV data EXCLUSIVELY from MT5 bridge.
If MT5 is not available, sends WhatsApp alarm and returns empty data.
yfinance is NOT used — all price data must come from the broker via MT5.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np

import httpx

logger = logging.getLogger("forex_data")

# ── MT5 bridge connection ─────────────────────────────────────────────────────
_mt5_bridge_url: str = ""
_last_alarm_time: float = 0  # track alarm frequency


async def _get_bridge_url() -> str:
    """Get MT5 bridge URL from DB config or env."""
    global _mt5_bridge_url
    if _mt5_bridge_url:
        return _mt5_bridge_url
    # Try from DB
    try:
        from models.database import async_session_factory, get_config
        async with async_session_factory() as s:
            url = await get_config("mt5_bridge_url", s)
            if url:
                _mt5_bridge_url = url.rstrip("/")
                return _mt5_bridge_url
    except Exception:
        pass
    # Fallback to env or default
    _mt5_bridge_url = os.getenv("MT5_BRIDGE_URL", "http://localhost:5002")
    return _mt5_bridge_url


async def _send_mt5_alarm(reason: str):
    """Send WhatsApp alarm when MT5 data is unavailable. Max once per minute."""
    import time
    global _last_alarm_time
    now = time.time()
    if now - _last_alarm_time < 60:
        return  # Already sent alarm recently
    _last_alarm_time = now

    try:
        from services.whatsapp_bot import get_whatsapp_bot
        wa = get_whatsapp_bot()
        await wa.send_message(
            f"🚨 *MT5 DATA UNAVAILABLE*\n\n"
            f"Cannot fetch live price data from MT5.\n"
            f"Reason: {reason}\n\n"
            f"⚠️ All trading decisions are SUSPENDED until MT5 reconnects.\n"
            f"This alarm repeats every 60 seconds."
        )
    except Exception as exc:
        logger.error("Failed to send MT5 alarm via WhatsApp: %s", exc)


async def fetch_ohlcv(symbol: str, timeframe: str = "H1", limit: int = 200) -> dict:
    """
    Fetch OHLCV data EXCLUSIVELY from MT5 (direct, no HTTP bridge).
    If MT5 is unavailable, sends WhatsApp alarm and returns empty data.
    """
    try:
        from services.mt5_direct import get_mt5_direct
        mt5 = get_mt5_direct()
        if not mt5.connected:
            mt5.connect()
        candles = mt5.get_candles(symbol, timeframe, limit)
        if not candles:
            raise ValueError(f"MT5 returned 0 candles for {symbol} {timeframe}")

    except Exception as exc:
        logger.error("MT5 data fetch failed for %s %s: %s", symbol, timeframe, exc)
        await _send_mt5_alarm(f"{symbol} {timeframe}: {exc}")
        # Return empty data — caller must handle gracefully
        return {
            "symbol": symbol, "timeframe": timeframe,
            "candles": [],
            "indicators": _empty_indicators(symbol),
            "mt5_error": str(exc),
        }

    # Build DataFrame from MT5 candles
    df = pd.DataFrame(candles)
    df.columns = [c.capitalize() for c in df.columns]
    if "Time" in df.columns:
        df.index = pd.to_datetime(df["Time"])
        df.drop(columns=["Time"], inplace=True, errors="ignore")

    # Ensure numeric types
    for col in ("Open", "High", "Low", "Close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)

    df = df.tail(limit)

    indicators = _compute_indicators(df, symbol)
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles, "indicators": indicators}


def _empty_indicators(symbol: str) -> dict:
    """Return empty indicator dict when MT5 data is unavailable."""
    pip_value = 0.01 if "JPY" in symbol else (1.0 if symbol in ("XAUUSD","XAGUSD","US30","NAS100","US500") else 0.0001)
    return {
        "current_price": 0,
        "atr": 0, "atr_pips": 0,
        "ema20": 0, "ema50": 0,
        "trend": "unknown",
        "pdh": 0, "pdl": 0, "pdc": 0,
        "pip_value": pip_value,
        "swing_highs": [], "swing_lows": [],
        "fvgs": [], "order_blocks": [],
    }


def _compute_indicators(df: pd.DataFrame, symbol: str) -> dict:
    """Compute ICT-relevant indicators from OHLCV data."""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # ATR (14)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]

    # Swing highs / lows (last 50 candles, pivot window 5)
    window = 5
    recent = df.tail(50)
    swing_highs = _find_swings(recent["High"], window, "high")
    swing_lows  = _find_swings(recent["Low"],  window, "low")

    # Previous Day High / Low / Close (PDH/PDL)
    if len(df) >= 2:
        yesterday = df.iloc[-2]
        pdh = float(yesterday["High"])
        pdl = float(yesterday["Low"])
        pdc = float(yesterday["Close"])
    else:
        pdh = pdl = pdc = float(close.iloc[-1])

    # Simple trend direction (EMA 20 vs 50)
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    trend = "bullish" if ema20 > ema50 else "bearish"

    # Current price
    current_price = float(close.iloc[-1])

    # Fair Value Gaps detection (simplified)
    fvgs = _detect_fvg(df.tail(30))

    # Order Blocks detection (simplified)
    order_blocks = _detect_order_blocks(df.tail(50))

    # Pip value — must match backtester.py pip definitions
    if "JPY" in symbol:
        pip_value = 0.01
    elif symbol in ("XAUUSD", "XAGUSD"):
        pip_value = 1.0    # Gold/Silver: 1 pip = $1 (price moves in whole dollars)
    elif symbol in ("US30", "NAS100", "US500"):
        pip_value = 1.0    # Indices: 1 pip = 1 point
    else:
        pip_value = 0.0001  # Standard forex

    return {
        "current_price": current_price,
        "atr": round(float(atr), 5),
        "atr_pips": round(float(atr) / pip_value, 1),
        "trend": trend,
        "ema20": round(float(ema20), 5),
        "ema50": round(float(ema50), 5),
        "swing_highs": swing_highs[-3:],
        "swing_lows":  swing_lows[-3:],
        "pdh": pdh,
        "pdl": pdl,
        "pdc": pdc,
        "fvgs": fvgs,
        "order_blocks": order_blocks,
        "pip_value": pip_value,
    }


def _find_swings(series: pd.Series, window: int, kind: str) -> list:
    swings = []
    for i in range(window, len(series) - window):
        val = series.iloc[i]
        neighbors = list(series.iloc[i - window:i]) + list(series.iloc[i + 1:i + window + 1])
        if kind == "high" and all(val >= n for n in neighbors):
            swings.append({"index": i, "price": round(float(val), 5),
                           "time": series.index[i].isoformat()})
        elif kind == "low" and all(val <= n for n in neighbors):
            swings.append({"index": i, "price": round(float(val), 5),
                           "time": series.index[i].isoformat()})
    return swings


def _detect_fvg(df: pd.DataFrame) -> list:
    """Detect Fair Value Gaps (3-candle imbalances)."""
    fvgs = []
    for i in range(1, len(df) - 1):
        c0 = df.iloc[i - 1]
        c2 = df.iloc[i + 1]
        # Bullish FVG: c0 high < c2 low
        if c0["High"] < c2["Low"]:
            fvgs.append({
                "type": "bullish",
                "top":    round(float(c2["Low"]), 5),
                "bottom": round(float(c0["High"]), 5),
                "time":   df.index[i].isoformat(),
            })
        # Bearish FVG: c0 low > c2 high
        elif c0["Low"] > c2["High"]:
            fvgs.append({
                "type": "bearish",
                "top":    round(float(c0["Low"]), 5),
                "bottom": round(float(c2["High"]), 5),
                "time":   df.index[i].isoformat(),
            })
    return fvgs[-5:]  # return last 5


def _detect_order_blocks(df: pd.DataFrame) -> list:
    """
    Simplified Order Block detection:
    A bullish OB is the last down-close candle before a strong up move.
    A bearish OB is the last up-close candle before a strong down move.
    """
    obs = []
    close = df["Close"].values
    high  = df["High"].values
    low   = df["Low"].values
    open_ = df["Open"].values

    for i in range(1, len(df) - 2):
        body = abs(close[i + 1] - open_[i + 1])
        avg_body = np.mean([abs(close[j] - open_[j]) for j in range(max(0, i - 10), i)])
        if avg_body == 0:
            continue
        momentum = body / avg_body

        if momentum > 1.5:
            # Bullish move — check for bearish candle before it
            if close[i] < open_[i]:
                obs.append({
                    "type":   "bullish",
                    "top":    round(float(high[i]), 5),
                    "bottom": round(float(low[i]), 5),
                    "time":   df.index[i].isoformat(),
                })
            # Bearish move — check for bullish candle before it
            elif close[i] > open_[i]:
                obs.append({
                    "type":   "bearish",
                    "top":    round(float(high[i]), 5),
                    "bottom": round(float(low[i]), 5),
                    "time":   df.index[i].isoformat(),
                })

    return obs[-5:]


async def get_multi_timeframe_data(symbol: str) -> dict:
    """Fetch H4 and H1 data together for ICT multi-timeframe analysis."""
    h4, h1 = await asyncio.gather(
        fetch_ohlcv(symbol, "H4", 100),
        fetch_ohlcv(symbol, "H1", 200),
    )
    return {"H4": h4, "H1": h1}
