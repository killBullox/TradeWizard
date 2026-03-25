"""
news_filter.py — Economic calendar news filter

Fetches high-impact economic events and blocks trade analysis when a
scheduled event is within the configured time window (default ±30 min).

Data source (primary): ForexFactory public JSON feed
  https://nfs.faireconomy.media/ff_calendar_thisweek.json

Fallback: built-in schedule of recurring high-impact events so the system
never has an empty calendar even when the network is unavailable.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

logger = logging.getLogger("news_filter")

# ── Currency → forex pair mapping ────────────────────────────────────────────
CURRENCY_PAIRS: dict[str, list[str]] = {
    "USD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD"],
    "EUR": ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURNZD", "EURCAD"],
    "GBP": ["GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPAUD", "GBPNZD", "GBPCAD"],
    "JPY": ["USDJPY", "EURJPY", "GBPJPY", "CADJPY", "AUDJPY", "NZDJPY", "CHFJPY"],
    "AUD": ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF"],
    "NZD": ["NZDUSD", "EURNZD", "GBPNZD", "NZDJPY", "AUDNZD", "NZDCAD", "NZDCHF"],
    "CAD": ["USDCAD", "EURCAD", "GBPCAD", "CADJPY", "AUDCAD", "NZDCAD", "CADCHF"],
    "CHF": ["USDCHF", "EURCHF", "GBPCHF", "CHFJPY", "AUDCHF", "NZDCHF", "CADCHF"],
    "XAU": ["XAUUSD"],
    "XAG": ["XAGUSD"],
}

# High-impact keywords that should always block trading
HIGH_IMPACT_KEYWORDS = {
    "interest rate", "rate decision", "fomc", "boe", "ecb", "rba", "rbnz",
    "boc", "snb", "boj", "nfp", "non-farm", "cpi", "inflation",
    "gdp", "unemployment", "payroll", "retail sales", "pmi",
    "consumer price", "producer price", "trade balance", "monetary policy",
    "press conference", "chair", "governor", "statement",
}


@dataclass
class NewsEvent:
    title:    str
    currency: str
    impact:   str           # "High", "Medium", "Low"
    time:     datetime      # UTC
    actual:   Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None

    @property
    def is_released(self) -> bool:
        return self.actual is not None

    @property
    def affected_pairs(self) -> list[str]:
        return CURRENCY_PAIRS.get(self.currency.upper(), [])

    def to_dict(self) -> dict:
        return {
            "title":          self.title,
            "currency":       self.currency,
            "impact":         self.impact,
            "time":           self.time.isoformat(),
            "actual":         self.actual,
            "forecast":       self.forecast,
            "previous":       self.previous,
            "is_released":    self.is_released,
            "affected_pairs": self.affected_pairs,
        }


class NewsFilter:
    """
    Maintains an in-memory cache of upcoming economic events.
    Provides `is_blocked(symbol)` for the orchestrator.
    """

    FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    REFRESH_INTERVAL = 15 * 60     # seconds — refresh calendar every 15 min

    def __init__(
        self,
        block_minutes_before: int = 30,
        block_minutes_after:  int = 30,
        block_medium_impact:  bool = False,
    ):
        self.block_minutes_before = block_minutes_before
        self.block_minutes_after  = block_minutes_after
        self.block_medium_impact  = block_medium_impact

        self._events:      list[NewsEvent] = []
        self._last_fetch:  Optional[datetime] = None
        self._fetch_lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    async def is_blocked(self, symbol: str) -> tuple[bool, Optional[NewsEvent]]:
        """
        Returns (True, event) if trading `symbol` should be blocked right now,
        or (False, None) if clear.
        """
        await self._maybe_refresh()
        now = datetime.now(timezone.utc)

        for event in self._events:
            if not self._event_affects_symbol(event, symbol):
                continue
            if not self._should_block_impact(event.impact):
                continue

            window_start = event.time - timedelta(minutes=self.block_minutes_before)
            window_end   = event.time + timedelta(minutes=self.block_minutes_after)

            if window_start <= now <= window_end:
                logger.info("BLOCKED %s — %s [%s] @ %s UTC (window %s–%s)",
                            symbol, event.title, event.impact,
                            event.time.strftime("%H:%M"),
                            window_start.strftime("%H:%M"),
                            window_end.strftime("%H:%M"))
                return True, event

        return False, None

    async def upcoming_events(
        self,
        hours_ahead: int = 24,
        symbol: Optional[str] = None,
    ) -> list[NewsEvent]:
        """Return events in the next `hours_ahead` hours, optionally filtered by symbol."""
        await self._maybe_refresh()
        now   = datetime.now(timezone.utc)
        limit = now + timedelta(hours=hours_ahead)

        events = [
            e for e in self._events
            if now <= e.time <= limit
            and (symbol is None or self._event_affects_symbol(e, symbol))
            and (e.impact == "High" or self.block_medium_impact)
        ]
        return sorted(events, key=lambda e: e.time)

    async def all_events(self) -> list[NewsEvent]:
        await self._maybe_refresh()
        return sorted(self._events, key=lambda e: e.time)

    async def force_refresh(self) -> int:
        """Force a calendar refresh and return the number of events loaded."""
        self._last_fetch = None
        await self._maybe_refresh()
        return len(self._events)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _should_block_impact(self, impact: str) -> bool:
        if impact == "High":
            return True
        if impact == "Medium" and self.block_medium_impact:
            return True
        return False

    def _event_affects_symbol(self, event: NewsEvent, symbol: str) -> bool:
        sym = symbol.upper().replace("/", "").replace("_", "")
        currency = event.currency.upper()
        # Direct match: symbol contains the currency code
        if currency in sym:
            return True
        # Mapped pairs
        for pair in CURRENCY_PAIRS.get(currency, []):
            if pair.upper() == sym:
                return True
        return False

    async def _maybe_refresh(self):
        now = datetime.now(timezone.utc)
        if (
            self._last_fetch is None
            or (now - self._last_fetch).total_seconds() > self.REFRESH_INTERVAL
        ):
            async with self._fetch_lock:
                # Double-check inside lock
                if (
                    self._last_fetch is None
                    or (now - self._last_fetch).total_seconds() > self.REFRESH_INTERVAL
                ):
                    await self._fetch_calendar()
                    self._last_fetch = now

    async def _fetch_calendar(self):
        """Fetch from ForexFactory JSON feed; fall back to mock data on error."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(self.FF_URL) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        events = self._parse_ff_json(data)
                        if events:
                            self._events = events
                            logger.info("Calendar refreshed: %d events from ForexFactory",
                                        len(events))
                            return
        except Exception as exc:
            logger.warning("ForexFactory fetch failed (%s) — using fallback data", exc)

        # Fallback
        self._events = self._generate_fallback_events()
        logger.info("Calendar refreshed: %d fallback events", len(self._events))

    # ── ForexFactory JSON parser ───────────────────────────────────────────────

    def _parse_ff_json(self, data: list) -> list[NewsEvent]:
        """
        ForexFactory JSON schema:
        {
          "title":    "Non-Farm Employment Change",
          "country":  "USD",
          "date":     "2025-01-03",
          "time":     "1:30pm",
          "impact":   "High",
          "forecast": "165K",
          "previous": "227K",
          "actual":   ""
        }
        """
        events: list[NewsEvent] = []
        now  = datetime.now(timezone.utc)
        past = now - timedelta(hours=6)

        for item in data:
            try:
                impact = item.get("impact", "Low")
                if impact not in ("High", "Medium"):
                    continue

                title    = item.get("title", "")
                currency = item.get("country", "")
                date_str = item.get("date", "")
                time_str = item.get("time", "")

                if not date_str or not currency:
                    continue

                event_time = self._parse_ff_datetime(date_str, time_str)
                if event_time is None or event_time < past:
                    continue

                actual   = item.get("actual") or None
                forecast = item.get("forecast") or None
                previous = item.get("previous") or None

                events.append(NewsEvent(
                    title=title, currency=currency, impact=impact,
                    time=event_time, actual=actual,
                    forecast=forecast, previous=previous,
                ))
            except Exception:
                continue

        return events

    @staticmethod
    def _parse_ff_datetime(date_str: str, time_str: str) -> Optional[datetime]:
        """Parse FF date like '2025-01-03' and time like '1:30pm' → UTC datetime."""
        try:
            base = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

        if not time_str or time_str.lower() in ("all day", "tentative", ""):
            # Default to midnight UTC for all-day events
            return base.replace(tzinfo=timezone.utc)

        try:
            # e.g. "1:30pm" or "12:00am"
            time_str = time_str.strip().lower()
            match = re.match(r"(\d{1,2}):(\d{2})(am|pm)", time_str)
            if not match:
                return base.replace(tzinfo=timezone.utc)
            hour, minute, period = int(match[1]), int(match[2]), match[3]
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            # ForexFactory times are US/Eastern — convert to UTC (+5 winter, +4 summer)
            # Approximate: use UTC-5 (EST) year-round for simplicity
            naive_et = base.replace(hour=hour, minute=minute)
            return naive_et.replace(tzinfo=timezone.utc) + timedelta(hours=5)
        except Exception:
            return base.replace(tzinfo=timezone.utc)

    # ── Fallback calendar ─────────────────────────────────────────────────────

    def _generate_fallback_events(self) -> list[NewsEvent]:
        """
        Generate a realistic set of upcoming high-impact events based on
        typical weekly schedule. Used when network is unavailable.
        """
        now    = datetime.now(timezone.utc)
        today  = now.replace(hour=0, minute=0, second=0, microsecond=0)
        events: list[NewsEvent] = []

        # Recurring weekly events (day_offset, hour_utc, minute, currency, title, impact)
        schedule = [
            # Monday
            (0, 23, 50, "JPY", "Bank of Japan Meeting Minutes",       "High"),
            # Tuesday
            (1,  9, 30, "GBP", "Claimant Count Change",               "Medium"),
            (1, 13, 30, "USD", "Core CPI m/m",                        "High"),
            # Wednesday
            (2,  1, 30, "AUD", "Westpac Consumer Sentiment",          "Medium"),
            (2, 13, 30, "USD", "Core Retail Sales m/m",               "High"),
            (2, 18,  0, "USD", "FOMC Meeting Minutes",                 "High"),
            # Thursday
            (3,  8,  0, "EUR", "ECB Monetary Policy Statement",        "High"),
            (3, 13, 30, "USD", "Unemployment Claims",                  "Medium"),
            (3, 13, 30, "USD", "Producer Price Index m/m",             "High"),
            # Friday
            (4, 13, 30, "USD", "Non-Farm Employment Change",           "High"),
            (4, 13, 30, "USD", "Unemployment Rate",                    "High"),
            (4, 15,  0, "USD", "ISM Manufacturing PMI",               "Medium"),
        ]

        weekday = today.weekday()  # 0=Mon … 6=Sun

        for day_offset, hour, minute, currency, title, impact in schedule:
            # Find the next occurrence of that weekday
            days_until = (day_offset - weekday) % 7
            event_day  = today + timedelta(days=days_until)
            event_time = event_day.replace(hour=hour, minute=minute, tzinfo=timezone.utc)

            # Keep events within the next 7 days or past 6 hours
            if event_time < now - timedelta(hours=6):
                event_time += timedelta(weeks=1)

            events.append(NewsEvent(
                title=title, currency=currency,
                impact=impact, time=event_time,
            ))

        return sorted(events, key=lambda e: e.time)


# ── Singleton ─────────────────────────────────────────────────────────────────
_instance: Optional[NewsFilter] = None


def get_news_filter(
    block_minutes_before: int = 30,
    block_minutes_after:  int = 30,
    block_medium_impact:  bool = False,
) -> NewsFilter:
    global _instance
    if _instance is None:
        _instance = NewsFilter(
            block_minutes_before=block_minutes_before,
            block_minutes_after=block_minutes_after,
            block_medium_impact=block_medium_impact,
        )
    return _instance
