"""
OANDA v20 REST API data service.

Provides H1 (and other timeframes) OHLCV data for ICT signal detection,
plus M1 candles for precise intra-candle entry/exit timing in backtests.

Requires:
  - OANDA API key (practice or live)
  - pip install aiohttp
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger("oanda_data")

PRACTICE_URL = "https://api-fxpractice.oanda.com"
LIVE_URL     = "https://api-fxtrade.oanda.com"

# OANDA instrument names
INSTRUMENT_MAP: dict[str, str] = {
    "EURUSD": "EUR_USD",  "GBPUSD": "GBP_USD",  "USDJPY": "USD_JPY",
    "USDCHF": "USD_CHF",  "AUDUSD": "AUD_USD",  "USDCAD": "USD_CAD",
    "NZDUSD": "NZD_USD",  "GBPJPY": "GBP_JPY",  "EURJPY": "EUR_JPY",
    "EURGBP": "EUR_GBP",  "AUDJPY": "AUD_JPY",  "CADJPY": "CAD_JPY",
    "CHFJPY": "CHF_JPY",  "NZDJPY": "NZD_JPY",  "EURCAD": "EUR_CAD",
    "GBPCAD": "GBP_CAD",  "EURCHF": "EUR_CHF",  "GBPCHF": "GBP_CHF",
    "XAUUSD": "XAU_USD",  "XAGUSD": "XAG_USD",
    "US30":   "US30_USD", "US500":  "SPX500_USD", "NAS100": "NAS100_USD",
}

GRANULARITY_MAP: dict[str, str] = {
    "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
    "H1": "H1", "H4": "H4", "D1":  "D",   "W1":  "W",
}

# Minutes per granularity (for chunked fetching)
_GRAN_MINUTES: dict[str, int] = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440, "W1": 10080,
}

_MAX_PER_REQUEST = 5000


def _to_oanda_time(dt: datetime) -> str:
    """Convert datetime to OANDA RFC3339 string (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def _parse_candle(c: dict) -> dict | None:
    """Parse a single OANDA candle dict into our standard format."""
    try:
        mid = c.get("mid") or c.get("ask") or c.get("bid")
        if not mid:
            return None
        # Trim nanoseconds → plain ISO without offset
        raw_time = c["time"][:19].replace("Z", "")
        return {
            "time":   raw_time,
            "open":   round(float(mid["o"]), 6),
            "high":   round(float(mid["h"]), 6),
            "low":    round(float(mid["l"]), 6),
            "close":  round(float(mid["c"]), 6),
            "volume": int(c.get("volume", 0)),
        }
    except Exception:
        return None


class OandaClient:
    def __init__(self, api_key: str, practice: bool = True):
        self.api_key  = api_key
        self.base_url = PRACTICE_URL if practice else LIVE_URL
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept-Encoding": "gzip",
        }

    async def _get(self, path: str, params: dict) -> dict:
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp is required: pip install aiohttp")

        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers,
                                   params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                body = await resp.json(content_type=None)
                if resp.status != 200:
                    raise RuntimeError(f"OANDA {resp.status}: {body.get('errorMessage', body)}")
                return body

    async def get_candles(
        self,
        symbol:      str,
        granularity: str,
        count:       int             = 500,
        from_time:   Optional[datetime] = None,
        to_time:     Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch up to `count` OHLCV candles. Uses from/to when provided."""
        instr = INSTRUMENT_MAP.get(symbol.upper(), symbol.upper().replace("/", "_"))
        gran  = GRANULARITY_MAP.get(granularity, granularity)

        params: dict = {"granularity": gran, "price": "M"}
        if from_time and to_time:
            params["from"] = _to_oanda_time(from_time)
            params["to"]   = _to_oanda_time(to_time)
        else:
            params["count"] = min(count, _MAX_PER_REQUEST)

        data = await self._get(f"/v3/instruments/{instr}/candles", params)
        candles = []
        for c in data.get("candles", []):
            if not c.get("complete", True):
                continue
            parsed = _parse_candle(c)
            if parsed:
                candles.append(parsed)
        return candles

    async def get_candles_chunked(
        self,
        symbol:      str,
        granularity: str,
        count:       int,
    ) -> list[dict]:
        """Fetch `count` candles in multiple requests if count > 5000."""
        if count <= _MAX_PER_REQUEST:
            return await self.get_candles(symbol, granularity, count=count)

        gran_minutes = _GRAN_MINUTES.get(granularity, 60)
        now          = datetime.now(timezone.utc)
        start_dt     = now - timedelta(minutes=gran_minutes * count)

        all_candles: list[dict] = []
        current = start_dt
        while current < now and len(all_candles) < count:
            end_dt = min(current + timedelta(minutes=gran_minutes * _MAX_PER_REQUEST), now)
            try:
                chunk = await self.get_candles(symbol, granularity,
                                               from_time=current, to_time=end_dt)
            except Exception as exc:
                log.warning("chunked fetch error (%s %s): %s", symbol, granularity, exc)
                break
            if not chunk:
                break
            all_candles.extend(chunk)
            last_ts = datetime.fromisoformat(chunk[-1]["time"])
            current = last_ts + timedelta(minutes=gran_minutes)
            await asyncio.sleep(0.05)  # avoid hammering the API

        return all_candles[-count:]


# ── Public helpers ─────────────────────────────────────────────────────────────

async def fetch_ohlcv(symbol: str, timeframe: str = "H1", limit: int = 500,
                      api_key: str = "", practice: bool = True) -> dict:
    """
    Main entry point — fetches OHLCV from OANDA.
    Returns same schema as yfinance service: {symbol, timeframe, candles, indicators}.
    Falls back to yfinance/mock if api_key is empty.
    """
    if not api_key:
        api_key = os.getenv("OANDA_API_KEY", "")
    if not api_key:
        from services.forex_data import fetch_ohlcv as _yf
        return await _yf(symbol, timeframe, limit)

    client = OandaClient(api_key, practice)
    try:
        candles = await client.get_candles_chunked(symbol, timeframe, limit)
        if not candles:
            raise RuntimeError("empty response")
        return {"symbol": symbol, "timeframe": timeframe,
                "candles": candles, "indicators": {}}
    except Exception as exc:
        log.warning("OANDA fetch failed (%s %s), falling back: %s", symbol, timeframe, exc)
        from services.forex_data import fetch_ohlcv as _yf
        return await _yf(symbol, timeframe, limit)


async def fetch_m1_for_period(
    symbol:    str,
    start_dt:  datetime,
    end_dt:    datetime,
    api_key:   str = "",
    practice:  bool = True,
) -> list[dict]:
    """
    Fetch all M1 candles between start_dt and end_dt.
    Used by Backtester to pinpoint exact entry/exit times inside H1 bars.
    Returns [] if no API key or on error.
    """
    if not api_key:
        api_key = os.getenv("OANDA_API_KEY", "")
    if not api_key:
        return []

    client      = OandaClient(api_key, practice)
    all_candles: list[dict] = []
    current     = start_dt.replace(tzinfo=timezone.utc) if start_dt.tzinfo is None else start_dt
    end         = end_dt.replace(tzinfo=timezone.utc)   if end_dt.tzinfo   is None else end_dt

    while current < end:
        chunk_end = min(current + timedelta(minutes=_MAX_PER_REQUEST), end)
        try:
            chunk = await client.get_candles(symbol, "M1",
                                             from_time=current, to_time=chunk_end)
            if not chunk:
                break
            all_candles.extend(chunk)
            last_ts = datetime.fromisoformat(chunk[-1]["time"])
            current = last_ts.replace(tzinfo=timezone.utc) + timedelta(minutes=1)
            await asyncio.sleep(0.05)
        except Exception as exc:
            log.warning("M1 fetch error (%s): %s", symbol, exc)
            break

    log.info("Fetched %d M1 candles for %s [%s → %s]",
             len(all_candles), symbol,
             start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    return all_candles


def build_m1_index(m1_candles: list[dict]) -> dict[str, list[dict]]:
    """
    Index M1 candles by their H1 bucket key ("YYYY-MM-DDTHH").
    Used for O(1) lookup in _find_exact_time().
    """
    idx: dict[str, list[dict]] = {}
    for c in m1_candles:
        key = c["time"][:13]   # "2024-01-15T14"
        idx.setdefault(key, []).append(c)
    return idx
