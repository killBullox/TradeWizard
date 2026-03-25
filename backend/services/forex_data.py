"""
Forex data service.
Fetches OHLCV data using yfinance and computes basic market structure
indicators used by ICT analysis (swing highs/lows, ATR, spreads).
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# Map common forex pair names to yfinance tickers
SYMBOL_MAP = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDCHF": "CHF=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "NZDUSD": "NZDUSD=X",
    "GBPJPY": "GBPJPY=X",
    "EURJPY": "EURJPY=X",
    "EURGBP": "EURGBP=X",
    "XAUUSD": "GC=F",    # Gold
    "XAGUSD": "SI=F",    # Silver
    "US30":   "^DJI",
    "US500":  "^GSPC",
    "NAS100": "^NDX",
}

TIMEFRAME_MAP = {
    "M1":  ("1m",  "1d"),
    "M5":  ("5m",  "5d"),
    "M15": ("15m", "5d"),
    "M30": ("30m", "10d"),
    "H1":  ("1h",  "30d"),
    "H4":  ("1h",  "60d"),   # yfinance doesn't have 4h; use 1h and resample
    "D1":  ("1d",  "365d"),
    "W1":  ("1wk", "730d"),
}


def _resample_to_h4(df: pd.DataFrame) -> pd.DataFrame:
    df = df.resample("4h").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna()
    return df


async def fetch_ohlcv(symbol: str, timeframe: str = "H1", limit: int = 200) -> dict:
    """
    Fetch OHLCV data for a symbol/timeframe.
    Returns a dict with 'candles' list and 'indicators'.
    """
    if not YFINANCE_AVAILABLE:
        return _generate_mock_data(symbol, timeframe, limit)

    ticker_symbol = SYMBOL_MAP.get(symbol, symbol)
    interval, period = TIMEFRAME_MAP.get(timeframe, ("1h", "30d"))

    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: _download(ticker_symbol, interval, period))

        if df is None or df.empty:
            return _generate_mock_data(symbol, timeframe, limit)

        if timeframe == "H4":
            df = _resample_to_h4(df)

        # Normalize column names (yfinance 1.x uses lowercase)
        df.columns = [c.capitalize() for c in df.columns]

        df = df.tail(limit)
        candles = []
        for ts, row in df.iterrows():
            candles.append({
                "time":   ts.isoformat(),
                "open":   round(float(row["Open"]), 5),
                "high":   round(float(row["High"]), 5),
                "low":    round(float(row["Low"]), 5),
                "close":  round(float(row["Close"]), 5),
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            })

        indicators = _compute_indicators(df, symbol)
        return {"symbol": symbol, "timeframe": timeframe, "candles": candles, "indicators": indicators}

    except Exception as e:
        import logging
        logging.getLogger("forex_data").warning("yfinance fetch failed (%s), using mock data: %s", symbol, e)
        return _generate_mock_data(symbol, timeframe, limit)


def _download(ticker: str, interval: str, period: str) -> Optional[pd.DataFrame]:
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty:
            return None
        # Normalize to capitalized column names for both old and new yfinance
        df.columns = [c.capitalize() for c in df.columns]
        return df
    except Exception as e:
        import logging
        logging.getLogger("forex_data").warning("_download error: %s", e)
        return None


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

    # Pip value (approximate)
    pip_value = 0.0001 if "JPY" not in symbol else 0.01

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


def _generate_mock_data(symbol: str, timeframe: str, limit: int) -> dict:
    """Generate realistic mock OHLCV data when live data is unavailable."""
    base_prices = {
        "EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 149.50,
        "XAUUSD": 2050.0, "USDCHF": 0.8950, "AUDUSD": 0.6550,
    }
    base = base_prices.get(symbol, 1.1000)
    pip = 0.0001 if "JPY" not in symbol else 0.01

    candles = []
    now = datetime.utcnow()
    intervals = {"M1":1,"M5":5,"M15":15,"M30":30,"H1":60,"H4":240,"D1":1440}
    minutes = intervals.get(timeframe, 60)

    price = base
    rng = np.random.default_rng(42)
    for i in range(limit):
        ts = now - timedelta(minutes=minutes * (limit - i))
        o = price
        h = o + rng.uniform(0, 20) * pip
        l = o - rng.uniform(0, 20) * pip
        c = rng.uniform(l, h)
        price = c
        candles.append({
            "time": ts.isoformat(), "open": round(o, 5), "high": round(h, 5),
            "low": round(l, 5), "close": round(c, 5), "volume": int(rng.integers(100, 5000)),
        })

    current = candles[-1]["close"]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "indicators": {
            "current_price": current,
            "atr": round(15 * pip, 5),
            "atr_pips": 15.0,
            "trend": "bullish",
            "ema20": round(current * 0.9999, 5),
            "ema50": round(current * 0.9997, 5),
            "swing_highs": [{"price": round(current + 30 * pip, 5)}],
            "swing_lows":  [{"price": round(current - 30 * pip, 5)}],
            "pdh": round(current + 20 * pip, 5),
            "pdl": round(current - 20 * pip, 5),
            "pdc": round(current - 5 * pip, 5),
            "fvgs": [],
            "order_blocks": [],
            "pip_value": pip,
        },
    }


async def get_multi_timeframe_data(symbol: str) -> dict:
    """Fetch H4 and H1 data together for ICT multi-timeframe analysis."""
    h4, h1 = await asyncio.gather(
        fetch_ohlcv(symbol, "H4", 100),
        fetch_ohlcv(symbol, "H1", 200),
    )
    return {"H4": h4, "H1": h1}
