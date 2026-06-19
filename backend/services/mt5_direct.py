"""
mt5_direct.py — Full HTTP bridge client.
ALL MT5 operations go through the bridge server (separate process).
The backend does NOT import MetaTrader5 — this prevents IPC pipe conflicts
between two processes trying to use the same MT5 terminal.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger("mt5_direct")

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://localhost:5555")


class MT5Direct:
    """MT5 interface — all calls go through HTTP bridge."""

    def __init__(self):
        self.connected = False
        # 60s timeout: bridge retries order_send 3x with 5s delays + subprocess fallback
        self._client = httpx.Client(base_url=BRIDGE_URL, timeout=60)

    def _get(self, path: str, params: dict = None):
        try:
            r = self._client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Bridge GET %s failed: %s", path, e)
            return None

    def _post(self, path: str, data: dict = None):
        try:
            r = self._client.post(path, json=data or {})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Bridge POST %s failed: %s", path, e)
            return None

    # ── Connection ───────────────────────────────────────────────────────

    def connect(self) -> bool:
        result = self._get("/health")
        if result and result.get("status") == "ok":
            self.connected = True
            logger.info("MT5 bridge connected — %s", result)
            return True
        logger.warning("MT5 bridge not responding")
        return False

    def disconnect(self):
        self.connected = False

    # ── READ operations ──────────────────────────────────────────────────

    def health(self) -> dict:
        result = self._get("/health")
        return result or {"status": "error", "mt5_available": False, "connected": False}

    def get_account_info(self) -> dict:
        result = self._get("/account")
        return result or {"error": "Bridge not responding"}

    def get_positions(self) -> list:
        result = self._get("/positions")
        return result if isinstance(result, list) else []

    def get_candles(self, symbol: str, timeframe: str, count: int = 500) -> list:
        result = self._get("/candles", {"symbol": symbol, "timeframe": timeframe, "count": count})
        return result if isinstance(result, list) else []

    # ── WRITE operations ─────────────────────────────────────────────────

    def open_trade(self, signal: dict) -> dict:
        payload = {
            "symbol": signal.get("symbol", ""),
            "direction": signal.get("direction", "BUY"),
            "order_type": signal.get("order_type", "MARKET"),
            "entry_price": float(signal.get("entry_price", 0)),
            "stop_loss": float(signal.get("stop_loss", 0)),
            "take_profit": float(signal.get("take_profit", signal.get("take_profit_1", 0))),
            "lot_size": float(signal.get("lot_size", 0.01)),
            "comment": signal.get("comment", "TW-ICT"),
        }
        result = self._post("/order_send", payload)

        # If the bridge is restarting after a wedge, wait for the watchdog to
        # respawn it (main.py monitors every 3s) and retry once. This is the
        # only known recovery path for the IPC-pipe wedge state.
        if result and not result.get("success") and "will restart" in str(result.get("error", "")):
            import time as _time
            logger.warning("MT5 OPEN: bridge respawning, waiting 7s before retry...")
            _time.sleep(7)
            # Reconnect the client to the new bridge process
            self.connected = False
            self.connect()
            result = self._post("/order_send", payload)

        if result and result.get("success"):
            logger.info("MT5 OPEN OK (bridge): ticket=%s %s %s",
                        result.get("ticket"), signal.get("direction"), signal.get("symbol"))
        elif result:
            logger.error("MT5 OPEN FAILED (bridge): %s", result.get("error"))
        return result or {"success": False, "error": "Bridge not responding"}

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict:
        result = self._post("/check_margin", {
            "symbol": symbol, "direction": direction, "lots": lots,
        })
        return result or {"ok": False, "margin_required": 0, "margin_free": 0,
                          "max_lots": 0, "error": "Bridge not responding"}

    def modify_sl(self, ticket: str, new_sl: float, symbol: str = "") -> dict:
        result = self._post("/modify_sl", {
            "ticket": ticket, "new_sl": new_sl, "symbol": symbol,
        })
        return result or {"success": False, "error": "Bridge not responding"}

    def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        result = self._post("/close_partial", {
            "ticket": ticket, "symbol": symbol, "percent": percent,
        })
        return result or {"success": False, "error": "Bridge not responding"}

    def close_trade(self, ticket: str, symbol: str = "") -> dict:
        result = self._post("/close", {
            "ticket": ticket, "symbol": symbol,
        })
        return result or {"success": False, "error": "Bridge not responding"}


# Singleton
_instance: Optional[MT5Direct] = None

def get_mt5_direct() -> MT5Direct:
    global _instance
    if _instance is None:
        _instance = MT5Direct()
    return _instance
