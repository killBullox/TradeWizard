"""
mt5_direct.py — MT5 HTTP bridge client.
Calls the MT5 bridge server via HTTP instead of importing MetaTrader5 directly.
This avoids IPC pipe corruption when read and write operations share a process.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger("mt5_direct")

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://localhost:5555")

# If httpx is not available, we're in a broken state but keep MT5_AVAILABLE
# logic for simulation mode fallback
try:
    _test_client = httpx.Client(timeout=15)
    MT5_AVAILABLE = True
except Exception:
    MT5_AVAILABLE = False
    logger.warning("httpx not available — simulation mode")


class MT5Direct:
    """MT5 interface via HTTP bridge."""

    def __init__(self):
        self.connected = False
        self._client = httpx.Client(base_url=BRIDGE_URL, timeout=15)

    def _url(self, path: str) -> str:
        return path

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

    def connect(self) -> bool:
        """Verify the bridge is responding."""
        result = self._get("/health")
        if result and result.get("status") == "ok":
            self.connected = True
            logger.info("MT5 bridge connected — %s", result)
            return True
        logger.warning("MT5 bridge not responding")
        return False

    def disconnect(self):
        self.connected = False

    def health(self) -> dict:
        result = self._get("/health")
        return result or {"status": "error", "mt5_available": False, "connected": False}

    def get_account_info(self) -> dict:
        result = self._get("/account")
        return result or {"error": "Bridge not responding"}

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict:
        result = self._post("/check_margin", {
            "symbol": symbol, "direction": direction, "lots": lots,
        })
        return result or {"ok": False, "margin_required": 0, "margin_free": 0,
                          "max_lots": 0, "error": "Bridge not responding"}

    def open_trade(self, signal: dict) -> dict:
        """Open a trade via the bridge."""
        result = self._post("/order_send", {
            "symbol": signal.get("symbol", ""),
            "direction": signal.get("direction", "BUY"),
            "order_type": signal.get("order_type", "MARKET"),
            "entry_price": float(signal.get("entry_price", 0)),
            "stop_loss": float(signal.get("stop_loss", 0)),
            "take_profit": float(signal.get("take_profit", signal.get("take_profit_1", 0))),
            "lot_size": float(signal.get("lot_size", 0.01)),
            "comment": signal.get("comment", "TW-ICT"),
        })
        return result or {"success": False, "error": "Bridge not responding"}

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

    def get_positions(self) -> list:
        result = self._get("/positions")
        return result if isinstance(result, list) else []

    def get_candles(self, symbol: str, timeframe: str, count: int = 500) -> list:
        result = self._get("/candles", {"symbol": symbol, "timeframe": timeframe, "count": count})
        return result if isinstance(result, list) else []


# Singleton
_instance: Optional[MT5Direct] = None

def get_mt5_direct() -> MT5Direct:
    global _instance
    if _instance is None:
        _instance = MT5Direct()
    return _instance
