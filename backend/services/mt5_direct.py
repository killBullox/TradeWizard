"""
mt5_direct.py — Hybrid MT5 interface.
READ operations (candles, positions, account) use MetaTrader5 directly in-process.
WRITE operations (order_send, modify_sl, close) go to the HTTP bridge (separate process).
This prevents IPC pipe corruption from mixing reads and writes.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger("mt5_direct")

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://localhost:5555")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not installed — simulation mode")


class MT5Direct:
    """Hybrid MT5 interface: reads in-process, writes via bridge."""

    def __init__(self):
        self.connected = False
        self.path = os.getenv("MT5_PATH", "")
        self.login = int(os.getenv("MT5_LOGIN", "0"))
        self.password = os.getenv("MT5_PASSWORD", "")
        self.server = os.getenv("MT5_SERVER", "")
        self._http = httpx.Client(base_url=BRIDGE_URL, timeout=15)

    # ── Bridge HTTP helpers (for WRITE operations) ───────────────────────

    def _post(self, path: str, data: dict = None):
        try:
            r = self._http.post(path, json=data or {})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Bridge POST %s failed: %s", path, e)
            return None

    # ── Direct MT5 connection (for READ operations) ──────────────────────

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            self.connected = True
            return True
        kwargs = {}
        if self.path:     kwargs["path"] = self.path
        if self.login:    kwargs["login"] = self.login
        if self.password: kwargs["password"] = self.password
        if self.server:   kwargs["server"] = self.server
        kwargs["timeout"] = 10000
        for attempt in range(3):
            if mt5.initialize(**kwargs):
                info = mt5.account_info()
                if info:
                    logger.info("MT5 connected — Account %s | Balance %.2f %s",
                                info.login, info.balance, info.currency)
                self.connected = True
                return True
            logger.warning("MT5 connect attempt %d/3 failed", attempt + 1)
            import time; time.sleep(2)
        logger.error("MT5 connection failed after 3 attempts")
        return False

    def _ensure_connected(self):
        if not MT5_AVAILABLE:
            return
        if not self.connected:
            self.connect()

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False

    # ── READ operations (direct, in-process) ─────────────────────────────

    def health(self) -> dict:
        if not MT5_AVAILABLE:
            return {"status": "ok", "mt5_available": False, "connected": True}
        self._ensure_connected()
        info = mt5.account_info()
        return {"status": "ok", "mt5_available": True, "connected": info is not None}

    def get_account_info(self) -> dict:
        if not MT5_AVAILABLE:
            return {"balance": 10000.0, "equity": 10000.0, "currency": "USD", "simulated": True}
        self._ensure_connected()
        info = mt5.account_info()
        if not info:
            return {"error": "Not connected"}
        return {
            "login": info.login, "balance": info.balance, "equity": info.equity,
            "margin": info.margin, "margin_free": info.margin_free,
            "currency": info.currency, "leverage": info.leverage,
        }

    def get_positions(self) -> list:
        if not MT5_AVAILABLE:
            return []
        self._ensure_connected()
        positions = mt5.positions_get()
        if not positions:
            return []
        return [
            {
                "ticket": p.ticket, "symbol": p.symbol,
                "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p.volume, "price_open": p.price_open,
                "price_current": p.price_current, "sl": p.sl, "tp": p.tp,
                "profit": p.profit, "comment": p.comment,
            }
            for p in positions
        ]

    def get_candles(self, symbol: str, timeframe: str, count: int = 500) -> list:
        if not MT5_AVAILABLE:
            return []
        self._ensure_connected()
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            return []
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        }
        tf_id = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, tf_id, 0, min(count, 50000))
        if rates is None or len(rates) == 0:
            return []
        result = []
        for r in rates:
            ts = datetime.utcfromtimestamp(int(r[0])).strftime("%Y-%m-%dT%H:%M:%S")
            result.append({
                "time": ts, "open": round(float(r[1]), 6),
                "high": round(float(r[2]), 6), "low": round(float(r[3]), 6),
                "close": round(float(r[4]), 6), "volume": int(r[5]),
            })
        return result

    # ── WRITE operations (via bridge HTTP) ───────────────────────────────

    def open_trade(self, signal: dict) -> dict:
        if not MT5_AVAILABLE:
            ticket = int(datetime.now().timestamp())
            return {"success": True, "ticket": str(ticket), "simulated": True}
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
        if result and result.get("success"):
            logger.info("MT5 OPEN OK (bridge): ticket=%s %s %s",
                        result.get("ticket"), signal.get("direction"), signal.get("symbol"))
        elif result:
            logger.error("MT5 OPEN FAILED (bridge): %s", result.get("error"))
        return result or {"success": False, "error": "Bridge not responding"}

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict:
        if not MT5_AVAILABLE:
            return {"ok": True, "margin_required": 0, "margin_free": 99999, "max_lots": lots, "simulated": True}
        result = self._post("/check_margin", {
            "symbol": symbol, "direction": direction, "lots": lots,
        })
        return result or {"ok": False, "margin_required": 0, "margin_free": 0,
                          "max_lots": 0, "error": "Bridge not responding"}

    def modify_sl(self, ticket: str, new_sl: float, symbol: str = "") -> dict:
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"SL -> {new_sl}"}
        result = self._post("/modify_sl", {
            "ticket": ticket, "new_sl": new_sl, "symbol": symbol,
        })
        return result or {"success": False, "error": "Bridge not responding"}

    def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"Closed {percent*100}%"}
        result = self._post("/close_partial", {
            "ticket": ticket, "symbol": symbol, "percent": percent,
        })
        return result or {"success": False, "error": "Bridge not responding"}

    def close_trade(self, ticket: str, symbol: str = "") -> dict:
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": "Closed"}
        result = self._post("/close", {
            "ticket": ticket, "symbol": symbol,
        })
        return result or {"success": False, "error": "Bridge not responding"}

    # ── Helpers ───────────────────────────────────────────────────────────

    _SYMBOL_ALIASES = {
        "XAUUSD": ["GOLD", "#GOLD", "XAUUSD", "XAUUSDm"],
        "XAGUSD": ["SILVER", "#SILVER", "XAGUSD"],
        "US30": ["US30", "DJ30", "#DJ30"],
        "NAS100": ["NAS100", "USTEC", "#NAS100"],
        "US500": ["US500", "SP500", "#SP500"],
    }

    def _normalize_symbol(self, raw: str) -> str:
        if not MT5_AVAILABLE:
            return raw
        info = mt5.symbol_info(raw)
        if info:
            mt5.symbol_select(raw, True)
            return raw
        for alias in self._SYMBOL_ALIASES.get(raw.upper(), []):
            info = mt5.symbol_info(alias)
            if info:
                mt5.symbol_select(alias, True)
                return alias
        for suffix in [".z", "m", "+", ".a", "-C", ".stp"]:
            test = raw + suffix
            info = mt5.symbol_info(test)
            if info:
                mt5.symbol_select(test, True)
                return test
        return ""

    def _normalize_lots(self, symbol: str, lots: float) -> float:
        if not MT5_AVAILABLE:
            return round(lots, 2)
        info = mt5.symbol_info(symbol)
        if not info:
            return round(lots, 2)
        step = info.volume_step or 0.01
        lots = max(info.volume_min, min(lots, info.volume_max))
        return round(round(lots / step) * step, 2)


# Singleton
_instance: Optional[MT5Direct] = None

def get_mt5_direct() -> MT5Direct:
    global _instance
    if _instance is None:
        _instance = MT5Direct()
    return _instance
