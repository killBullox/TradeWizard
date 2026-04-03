"""
mt5_bridge.py — Optional Python ↔ MetaTrader 5 bridge

Alternative to the MQL5 EA webhook server. Use this if:
  - You prefer Python-side MT5 control
  - Your broker provides the MetaTrader5 Python package
  - You want deeper integration (account info, history, etc.)

Requirements:
    pip install MetaTrader5
    (Windows only — MT5 terminal must be installed and running)

Usage:
    python mt5_bridge.py               # starts REST bridge on :5001
    or import MT5Bridge into your code
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Optional

logger = logging.getLogger("mt5_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MT5Bridge] %(message)s")

# ── Try to import MetaTrader5 ──────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5  # type: ignore
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not installed. Running in simulation mode.")


class MT5Bridge:
    """Python-side MT5 bridge that mirrors the MQL5 EA webhook actions."""

    def __init__(
        self,
        login: int = 0,
        password: str = "",
        server: str = "",
        path: str = "",
    ):
        self.login    = login
        self.password = password
        self.server   = server
        self.path     = path
        self.connected = False

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            logger.info("Simulation mode: MT5 not available")
            self.connected = True
            return True

        kwargs = {}
        if self.path:     kwargs["path"]     = self.path
        if self.login:    kwargs["login"]    = self.login
        if self.password: kwargs["password"] = self.password
        if self.server:   kwargs["server"]   = self.server

        if not mt5.initialize(**kwargs):
            logger.error("MT5 initialize failed: %s", mt5.last_error())
            return False

        info = mt5.account_info()
        if info:
            logger.info("Connected — Account %s | Balance %.2f %s",
                        info.login, info.balance, info.currency)
        self.connected = True
        return True

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5")

    # ── Core trade actions (mirrors MQL5 EA) ───────────────────────────────────

    def open_trade(self, signal: dict) -> dict:
        """OPEN — place market, limit, or stop order."""
        symbol     = signal.get("symbol", "")
        direction  = signal.get("direction", "BUY")
        order_type = signal.get("order_type", "MARKET")
        entry      = float(signal.get("entry_price", 0))
        sl         = float(signal.get("stop_loss", 0))
        tp         = float(signal.get("take_profit", 0))
        lots       = float(signal.get("lot_size", 0.01))
        comment    = signal.get("comment", "TW-ICT")

        if not MT5_AVAILABLE:
            ticket = int(datetime.now().timestamp())
            logger.info("SIM OPEN  %s %s %s @ %.5f  SL=%.5f  TP=%.5f  lots=%.2f  ticket=%s",
                        order_type, direction, symbol, entry, sl, tp, lots, ticket)
            return {"success": True, "ticket": str(ticket), "message": "Simulated open"}

        # Normalise symbol
        symbol = self._normalise_symbol(symbol)
        if not symbol:
            return {"success": False, "error": f"Symbol not found: {signal.get('symbol')}"}

        # Normalise lots
        lots = self._normalise_lots(symbol, lots)

        is_buy = direction.upper() == "BUY"

        if order_type.upper() == "MARKET":
            price = mt5.symbol_info_tick(symbol).ask if is_buy else mt5.symbol_info_tick(symbol).bid
            action = mt5.TRADE_ACTION_DEAL
            otype  = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        elif order_type.upper() == "LIMIT":
            price  = entry
            action = mt5.TRADE_ACTION_PENDING
            otype  = mt5.ORDER_TYPE_BUY_LIMIT if is_buy else mt5.ORDER_TYPE_SELL_LIMIT
        else:  # STOP
            price  = entry
            action = mt5.TRADE_ACTION_PENDING
            otype  = mt5.ORDER_TYPE_BUY_STOP if is_buy else mt5.ORDER_TYPE_SELL_STOP

        request = {
            "action":       action,
            "symbol":       symbol,
            "volume":       lots,
            "type":         otype,
            "price":        price,
            "sl":           sl,
            "tp":           tp,
            "deviation":    10,
            "magic":        20250101,
            "comment":      comment,
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling(symbol),
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else -1
            return {"success": False, "error": f"order_send failed: {code}"}

        logger.info("OPEN OK  ticket=%s  %s %s %s @ %.5f",
                    result.order, order_type, direction, symbol, price)
        return {"success": True, "ticket": str(result.order), "message": "Order placed"}

    def modify_sl(self, signal: dict) -> dict:
        """MODIFY_SL — move the stop loss of an open position."""
        ticket = int(signal.get("ticket", 0))
        new_sl = float(signal.get("new_sl", 0))

        if not MT5_AVAILABLE:
            logger.info("SIM MODIFY_SL  ticket=%s  new_sl=%.5f", ticket, new_sl)
            return {"success": True, "ticket": str(ticket), "message": f"SL → {new_sl:.5f}"}

        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"success": False, "error": f"Position not found: {ticket}"}

        p = pos[0]
        request = {
            "action":   mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl":       new_sl,
            "tp":       p.tp,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else -1
            return {"success": False, "error": f"SLTP failed: {code}"}

        logger.info("MODIFY_SL OK  ticket=%s  new_sl=%.5f", ticket, new_sl)
        return {"success": True, "ticket": str(ticket),
                "message": f"Stop loss modified to {new_sl:.5f}"}

    def close_partial(self, signal: dict) -> dict:
        """CLOSE_PARTIAL — close a percentage of the position volume."""
        ticket  = int(signal.get("ticket", 0))
        percent = float(signal.get("percent", 50.0))

        if not MT5_AVAILABLE:
            logger.info("SIM CLOSE_PARTIAL  ticket=%s  %.0f%%", ticket, percent)
            return {"success": True, "ticket": str(ticket),
                    "message": f"Closed {percent:.0f}% (simulated)"}

        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"success": False, "error": f"Position not found: {ticket}"}

        p       = pos[0]
        symbol  = p.symbol
        volume  = self._normalise_lots(symbol, p.volume * percent / 100.0)
        if volume <= 0:
            return {"success": False, "error": "Close volume too small"}

        is_buy  = p.type == mt5.ORDER_TYPE_BUY
        price   = mt5.symbol_info_tick(symbol).bid if is_buy else mt5.symbol_info_tick(symbol).ask
        otype   = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "position":     ticket,
            "symbol":       symbol,
            "volume":       volume,
            "type":         otype,
            "price":        price,
            "deviation":    10,
            "magic":        20250101,
            "comment":      "TW-PARTIAL",
            "type_filling": self._get_filling(symbol),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else -1
            return {"success": False, "error": f"Partial close failed: {code}"}

        logger.info("CLOSE_PARTIAL OK  ticket=%s  %.0f%%  vol=%.2f", ticket, percent, volume)
        return {"success": True, "ticket": str(ticket),
                "message": f"Closed {percent:.0f}%"}

    def close_trade(self, signal: dict) -> dict:
        """CLOSE — fully close a position."""
        ticket_str = signal.get("ticket", "")
        symbol     = signal.get("symbol", "")

        if not ticket_str and not symbol:
            return {"success": False, "error": "Missing ticket or symbol"}

        if not MT5_AVAILABLE:
            logger.info("SIM CLOSE  ticket=%s  symbol=%s", ticket_str, symbol)
            return {"success": True, "ticket": ticket_str or "ALL",
                    "message": "Position closed (simulated)"}

        if ticket_str:
            ticket = int(ticket_str)
            return self._close_position_by_ticket(ticket)

        # Close all positions for symbol
        norm   = self._normalise_symbol(symbol)
        closed = 0
        for p in (mt5.positions_get(symbol=norm) or []):
            r = self._close_position_by_ticket(p.ticket)
            if r.get("success"):
                closed += 1
        return {"success": True, "ticket": "ALL",
                "message": f"Closed {closed} positions for {symbol}"}

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _close_position_by_ticket(self, ticket: int) -> dict:
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"success": False, "error": f"Position not found: {ticket}"}

        p      = pos[0]
        symbol = p.symbol
        is_buy = p.type == mt5.ORDER_TYPE_BUY
        price  = mt5.symbol_info_tick(symbol).bid if is_buy else mt5.symbol_info_tick(symbol).ask
        otype  = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "position":     ticket,
            "symbol":       symbol,
            "volume":       p.volume,
            "type":         otype,
            "price":        price,
            "deviation":    10,
            "magic":        20250101,
            "comment":      "TW-CLOSE",
            "type_filling": self._get_filling(symbol),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else -1
            return {"success": False, "error": f"Close failed: {code}"}

        logger.info("CLOSE OK  ticket=%s  price=%.5f", ticket, price)
        return {"success": True, "ticket": str(ticket),
                "close_price": price, "message": "Position closed"}

    # Common broker aliases for standard symbol names
    _SYMBOL_ALIASES = {
        "XAUUSD": ["GOLD", "#GOLD", "XAUUSD", "XAUUSDm", "GOLD.z", "XAUUSD.z"],
        "XAGUSD": ["SILVER", "#SILVER", "XAGUSD", "XAGUSDm"],
        "US30":   ["US30", "DJ30", "#DJ30", "US30.z", "US30m"],
        "NAS100": ["NAS100", "USTEC", "#NAS100", "NAS100.z", "NAS100m"],
        "US500":  ["US500", "SP500", "#SP500", "US500.z", "US500m"],
    }

    def _normalise_symbol(self, raw: str) -> str:
        if not MT5_AVAILABLE:
            return raw
        # Direct match
        info = mt5.symbol_info(raw)
        if info:
            return raw
        # Try aliases for known symbols
        aliases = self._SYMBOL_ALIASES.get(raw.upper(), [])
        for alias in aliases:
            info = mt5.symbol_info(alias)
            if info:
                mt5.symbol_select(alias, True)
                logger.info("Symbol %s resolved to broker name: %s", raw, alias)
                return alias
        # Try common suffixes
        for suffix in [".z", "m", "+", "pro", ".r", ".stp", ".a", "-C"]:
            test = raw + suffix
            info = mt5.symbol_info(test)
            if info:
                mt5.symbol_select(test, True)
                logger.info("Symbol %s resolved with suffix: %s", raw, test)
                return test
        mt5.symbol_select(raw, True)
        return raw if mt5.symbol_info(raw) else ""

    def _normalise_lots(self, symbol: str, lots: float) -> float:
        if not MT5_AVAILABLE:
            return round(lots, 2)
        info = mt5.symbol_info(symbol)
        if not info:
            return round(lots, 2)
        step = info.volume_step or 0.01
        lots = round(round(lots / step) * step, 2)
        lots = max(lots, info.volume_min)
        lots = min(lots, info.volume_max)
        return lots

    def _get_filling(self, symbol: str) -> int:
        if not MT5_AVAILABLE:
            return 0  # ORDER_FILLING_FOK
        info = mt5.symbol_info(symbol)
        if not info:
            return mt5.ORDER_FILLING_RETURN
        mode = info.filling_mode
        if mode & mt5.SYMBOL_FILLING_FOK:
            return mt5.ORDER_FILLING_FOK
        if mode & mt5.SYMBOL_FILLING_IOC:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    # ── Historical data ────────────────────────────────────────────────────────

    _TF_MAP = {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 16385, "H4": 16388, "D1": 16408,
    }

    def get_candles(self, symbol: str, timeframe: str, count: int = 500) -> list[dict]:
        """
        Return the last `count` closed OHLCV bars for symbol/timeframe.
        Falls back to empty list in simulation mode.
        """
        if not MT5_AVAILABLE:
            return []

        norm = self._normalise_symbol(symbol)
        if not norm:
            logger.warning("get_candles: symbol not found: %s", symbol)
            return []

        tf_id = self._TF_MAP.get(timeframe.upper(), 16385)  # default H1
        rates = mt5.copy_rates_from_pos(norm, tf_id, 0, min(count, 50000))
        if rates is None or len(rates) == 0:
            logger.warning("get_candles: no data for %s %s", symbol, timeframe)
            return []

        return self._rates_to_list(rates)

    def get_candles_range(self, symbol: str, timeframe: str,
                          from_dt: datetime, to_dt: datetime) -> list[dict]:
        """Return bars between from_dt and to_dt (UTC)."""
        if not MT5_AVAILABLE:
            return []

        norm = self._normalise_symbol(symbol)
        if not norm:
            return []

        tf_id = self._TF_MAP.get(timeframe.upper(), 1)
        rates = mt5.copy_rates_range(norm, tf_id, from_dt, to_dt)
        if rates is None or len(rates) == 0:
            return []

        return self._rates_to_list(rates)

    @staticmethod
    def _rates_to_list(rates) -> list[dict]:
        result = []
        for r in rates:
            # r.time is a Unix timestamp (seconds, UTC)
            ts = datetime.utcfromtimestamp(int(r[0])).strftime("%Y-%m-%dT%H:%M:%S")
            result.append({
                "time":   ts,
                "open":   round(float(r[1]), 6),
                "high":   round(float(r[2]), 6),
                "low":    round(float(r[3]), 6),
                "close":  round(float(r[4]), 6),
                "volume": int(r[5]),
            })
        return result

    # ── Account info ───────────────────────────────────────────────────────────

    def get_account_info(self) -> dict:
        if not MT5_AVAILABLE:
            return {"balance": 10000.0, "equity": 10000.0,
                    "margin_free": 9500.0, "currency": "USD",
                    "simulated": True}
        info = mt5.account_info()
        if not info:
            return {"error": "Could not fetch account info"}
        return {
            "login":       info.login,
            "balance":     info.balance,
            "equity":      info.equity,
            "margin":      info.margin,
            "margin_free": info.margin_free,
            "currency":    info.currency,
            "leverage":    info.leverage,
        }

    def get_open_positions(self) -> list:
        if not MT5_AVAILABLE:
            return []
        return [
            {
                "ticket":  p.ticket,
                "symbol":  p.symbol,
                "type":    "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume":  p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl":      p.sl,
                "tp":      p.tp,
                "profit":  p.profit,
                "comment": p.comment,
            }
            for p in (mt5.positions_get() or [])
        ]

    # ── Dispatch from signal dict ──────────────────────────────────────────────

    def execute_signal(self, signal: dict) -> dict:
        action = signal.get("action", "").upper()
        if   action == "OPEN":          return self.open_trade(signal)
        elif action == "MODIFY_SL":     return self.modify_sl(signal)
        elif action == "CLOSE_PARTIAL": return self.close_partial(signal)
        elif action == "CLOSE":         return self.close_trade(signal)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


# ── Standalone REST bridge server ─────────────────────────────────────────────

def _make_app(bridge: MT5Bridge):
    """Wrap the bridge in a tiny FastAPI app (optional standalone mode)."""
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.error("FastAPI not installed. Cannot start standalone server.")
        sys.exit(1)

    app = FastAPI(title="MT5 Python Bridge", version="1.0")

    @app.post("/webhook")
    async def webhook(request: Request):
        body = await request.json()
        result = bridge.execute_signal(body)
        return JSONResponse(result)

    @app.get("/account")
    async def account():
        return bridge.get_account_info()

    @app.get("/positions")
    async def positions():
        return bridge.get_open_positions()

    @app.get("/health")
    async def health():
        return {"status": "ok", "mt5_available": MT5_AVAILABLE,
                "connected": bridge.connected}

    @app.post("/test-credentials")
    async def test_credentials(request: Request):
        """Temporarily connect with given credentials to verify them, then reconnect to original."""
        if not MT5_AVAILABLE:
            return {"ok": True, "note": "Simulation mode — credentials not verified"}
        body = await request.json()
        test_login    = int(body.get("login", 0))
        test_password = body.get("password", "")
        test_server   = body.get("server", "")
        if not test_login:
            return {"ok": False, "error": "Login required"}

        # Capture current live account info BEFORE disconnecting (more reliable than bridge.login)
        orig_info     = mt5.account_info()
        orig_login    = orig_info.login    if orig_info else bridge.login
        orig_server   = orig_info.server   if orig_info else bridge.server
        orig_password = bridge.password  # no way to read it back from MT5

        result = {"ok": False, "error": "Unknown error"}
        try:
            mt5.shutdown()
            kwargs = {"login": test_login}
            if test_password: kwargs["password"] = test_password
            if test_server:   kwargs["server"]   = test_server
            if bridge.path:   kwargs["path"]     = bridge.path
            if not mt5.initialize(**kwargs):
                err = mt5.last_error()
                result = {"ok": False, "error": f"MT5 error {err[0]}: {err[1]}"}
            else:
                info = mt5.account_info()
                result = {
                    "ok":      True,
                    "login":   info.login   if info else test_login,
                    "balance": info.balance if info else None,
                    "server":  info.server  if info else test_server,
                    "name":    info.name    if info else "",
                }
        except Exception as e:
            result = {"ok": False, "error": str(e)}
        finally:
            # Always reconnect to original account
            try:
                mt5.shutdown()
                rkw = {}
                if orig_login:    rkw["login"]    = orig_login
                if orig_password: rkw["password"] = orig_password
                if orig_server:   rkw["server"]   = orig_server
                if bridge.path:   rkw["path"]     = bridge.path
                mt5.initialize(**rkw)
                bridge.connected = True
            except Exception:
                pass
        return result

    @app.get("/candles")
    async def candles(symbol: str = "EURUSD", timeframe: str = "H1", count: int = 500):
        """Return the last `count` OHLCV bars for symbol/timeframe."""
        bars = bridge.get_candles(symbol, timeframe, count)
        return {"symbol": symbol, "timeframe": timeframe,
                "candles": bars, "count": len(bars)}

    @app.get("/candles/range")
    async def candles_range(symbol: str = "EURUSD", timeframe: str = "M1",
                             from_ts: str = "", to_ts: str = ""):
        """
        Return bars between from_ts and to_ts (ISO format UTC).
        Example: ?symbol=EURUSD&timeframe=M1&from_ts=2024-01-15T14:00:00&to_ts=2024-01-15T15:00:00
        """
        try:
            from_dt = datetime.fromisoformat(from_ts)
            to_dt   = datetime.fromisoformat(to_ts)
        except Exception:
            return JSONResponse({"error": "Invalid from_ts/to_ts format (use ISO: YYYY-MM-DDTHH:MM:SS)"}, 400)
        bars = bridge.get_candles_range(symbol, timeframe, from_dt, to_dt)
        return {"symbol": symbol, "timeframe": timeframe,
                "candles": bars, "count": len(bars)}

    return app


if __name__ == "__main__":
    import uvicorn

    login    = int(os.getenv("MT5_LOGIN",    "0"))
    password =     os.getenv("MT5_PASSWORD", "")
    server   =     os.getenv("MT5_SERVER",   "")
    path     =     os.getenv("MT5_PATH",     "")
    port     = int(os.getenv("MT5_BRIDGE_PORT", "5001"))

    bridge = MT5Bridge(login=login, password=password, server=server, path=path)
    if not bridge.connect():
        logger.error("Could not connect to MT5")
        sys.exit(1)

    app = _make_app(bridge)

    def _shutdown(*_):
        bridge.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("MT5 Python Bridge starting on port %s", port)
    uvicorn.run(app, host="0.0.0.0", port=port,
                forwarded_allow_ips="*", proxy_headers=False)
