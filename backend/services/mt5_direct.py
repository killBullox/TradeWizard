"""
mt5_direct.py — Direct MT5 execution without HTTP bridge.
Calls MetaTrader5 Python library directly from the backend process.
No subprocess, no HTTP, no connection loss.
"""

import logging
import os
import threading
from datetime import datetime
from typing import Optional

logger = logging.getLogger("mt5_direct")

# Global lock: the MetaTrader5 Python library is NOT thread-safe.
# Concurrent calls (e.g. monitor_loop checking positions while analysis_loop
# sends orders) corrupt the IPC pipe to the terminal, causing order_send
# to return None with error -2. This lock serializes write operations
# (order_send, connect, shutdown) to prevent IPC corruption.
# Read operations (get_candles, get_positions, account_info) use a separate
# lighter lock to avoid blocking the async event loop.
_mt5_lock = threading.RLock()  # RLock allows reentrant calls (e.g. connect inside open_trade)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not installed — simulation mode")


class MT5Direct:
    """Direct MT5 interface — no HTTP bridge needed."""

    def __init__(self):
        self.connected = False
        self.path = os.getenv("MT5_PATH", "")
        self.login = int(os.getenv("MT5_LOGIN", "0"))
        self.password = os.getenv("MT5_PASSWORD", "")
        self.server = os.getenv("MT5_SERVER", "")

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            logger.info("MT5 not available — simulation mode")
            self.connected = True
            return True

        kwargs = {}
        if self.path:     kwargs["path"] = self.path
        if self.login:    kwargs["login"] = self.login
        if self.password: kwargs["password"] = self.password
        if self.server:   kwargs["server"] = self.server

        with _mt5_lock:
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

            logger.error("MT5 connection failed after 3 attempts: %s", mt5.last_error() if MT5_AVAILABLE else "N/A")
            return False

    def _ensure_connected(self):
        """Verify we are connected to the CORRECT MT5 account (not another terminal)."""
        if not MT5_AVAILABLE:
            return
        info = mt5.account_info()
        # Check not just connected, but connected to the RIGHT account
        wrong_account = (info is not None and self.login and info.login != self.login)
        if info is None or wrong_account:
            if wrong_account:
                logger.warning("MT5 connected to WRONG account %d (expected %d) — reconnecting to correct terminal...",
                               info.login, self.login)
            else:
                logger.warning("MT5 disconnected — reconnecting...")
            mt5.shutdown()
            for attempt in range(3):
                kwargs = {}
                if self.path:     kwargs["path"] = self.path
                if self.login:    kwargs["login"] = self.login
                if self.password: kwargs["password"] = self.password
                if self.server:   kwargs["server"] = self.server
                if mt5.initialize(**kwargs):
                    check = mt5.account_info()
                    if check and (not self.login or check.login == self.login):
                        self.connected = True
                        logger.info("MT5 reconnected to account %d (attempt %d)", check.login, attempt + 1)
                        return
                    logger.warning("MT5 init OK but wrong account %d, retrying...", check.login if check else 0)
                    mt5.shutdown()
                import time; time.sleep(2)
            logger.error("MT5 reconnect to correct account failed after 3 attempts")

    def disconnect(self):
        with _mt5_lock:
            if MT5_AVAILABLE and self.connected:
                mt5.shutdown()
            self.connected = False

    def health(self) -> dict:
        if not MT5_AVAILABLE:
            return {"status": "ok", "mt5_available": False, "connected": True}
        info = mt5.account_info()
        return {
            "status": "ok",
            "mt5_available": True,
            "connected": info is not None,
        }

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

    # ── Margin check ─────────────────────────────────────────────────────

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict:
        """Check if there's enough free margin for the trade.
        Returns {"ok": True/False, "margin_required": float, "margin_free": float,
                 "max_lots": float} — max_lots is the largest lot size that fits."""
        if not MT5_AVAILABLE:
            return {"ok": True, "margin_required": 0, "margin_free": 99999, "max_lots": lots, "simulated": True}

        with _mt5_lock:
            return self._check_margin_locked(symbol, direction, lots)

    def _check_margin_locked(self, symbol, direction, lots):
        """Must be called inside _mt5_lock."""
        self._ensure_connected()
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            return {"ok": False, "margin_required": 0, "margin_free": 0, "max_lots": 0,
                    "error": f"Symbol not found: {symbol}"}

        account = mt5.account_info()
        if not account:
            return {"ok": False, "margin_required": 0, "margin_free": 0, "max_lots": 0,
                    "error": "Cannot get account info"}

        margin_free = account.margin_free
        leverage = account.leverage or 100
        is_buy = direction.upper() == "BUY"
        otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"ok": False, "margin_required": 0, "margin_free": margin_free, "max_lots": 0,
                    "error": f"No tick data for {symbol}"}
        price = tick.ask if is_buy else tick.bid

        # Use order_check to get exact margin required
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lots,
            "type": otype,
            "price": price,
        }
        check = mt5.order_check(request)
        if check is None:
            # Fallback: estimate margin from symbol info
            sym_info = mt5.symbol_info(symbol)
            if sym_info and sym_info.trade_contract_size > 0:
                margin_est = (lots * sym_info.trade_contract_size * price) / leverage
                ok = margin_free > margin_est * 1.1  # 10% safety buffer
                max_lots = lots if ok else self._find_max_lots(symbol, margin_free, sym_info, price, leverage)
                return {"ok": ok, "margin_required": round(margin_est, 2),
                        "margin_free": round(margin_free, 2), "max_lots": max_lots,
                        "leverage": leverage}
            return {"ok": False, "margin_required": 0, "margin_free": round(margin_free, 2),
                    "max_lots": 0, "leverage": leverage, "error": "order_check failed and no symbol info"}

        margin_required = check.margin or 0
        ok = check.retcode == mt5.TRADE_RETCODE_DONE or margin_free > margin_required * 1.1

        # If not enough margin, find max affordable lot size
        max_lots = lots
        if not ok and margin_required > 0:
            ratio = (margin_free * 0.9) / margin_required
            max_lots = self._normalize_lots(symbol, lots * ratio)

        return {
            "ok": ok,
            "margin_required": round(margin_required, 2),
            "margin_free": round(margin_free, 2),
            "max_lots": max_lots,
            "leverage": leverage,
            "retcode": check.retcode,
            "comment": check.comment,
        }

    def _find_max_lots(self, symbol: str, margin_free: float, sym_info, price: float, leverage: int) -> float:
        """Estimate max affordable lots from margin_free."""
        if sym_info.trade_contract_size <= 0 or price <= 0:
            return 0.01
        max_lots = (margin_free * 0.9 * leverage) / (sym_info.trade_contract_size * price)
        return self._normalize_lots(symbol, max_lots)

    # ── Trade execution ───────────────────────────────────────────────────

    def open_trade(self, signal: dict) -> dict:
        """Open a trade on MT5."""
        symbol = signal.get("symbol", "")
        direction = signal.get("direction", "BUY")
        order_type = signal.get("order_type", "MARKET")
        entry = float(signal.get("entry_price", 0))
        sl = float(signal.get("stop_loss", 0))
        tp = float(signal.get("take_profit", signal.get("take_profit_1", 0)))
        lots = float(signal.get("lot_size", 0.01))
        # MT5 comment: max 31 chars, ASCII only, no special chars
        raw_comment = signal.get("comment", "TW-ICT")[:31]
        comment = ''.join(c for c in raw_comment if c.isascii() and (c.isalnum() or c in ' -_.'))[:31] or "TW"

        if not MT5_AVAILABLE:
            ticket = int(datetime.now().timestamp())
            logger.info("SIM OPEN %s %s %s @ %.5f lots=%.2f", order_type, direction, symbol, entry, lots)
            return {"success": True, "ticket": str(ticket), "simulated": True}

        with _mt5_lock:
            self._ensure_connected()

            # Normalize symbol
            symbol = self._normalize_symbol(symbol)
            if not symbol:
                return {"success": False, "error": f"Symbol not found: {signal.get('symbol')}"}

            # Normalize lots
            lots = self._normalize_lots(symbol, lots)

            is_buy = direction.upper() == "BUY"

            # ALWAYS use MARKET orders for intraday trading — no pending orders
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return {"success": False, "error": f"No tick data for {symbol}"}
            price = tick.ask if is_buy else tick.bid
            action = mt5.TRADE_ACTION_DEAL
            otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
            if order_type.upper() != "MARKET":
                logger.info("Overriding %s to MARKET for %s %s", order_type, direction, symbol)

            request = {
                "action": action,
                "symbol": symbol,
                "volume": lots,
                "type": otype,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": 20250101,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            logger.info("MT5 OPEN: %s %s %s lots=%.2f price=%.5f sl=%.5f tp=%.5f",
                         order_type, direction, symbol, lots, price, sl, tp)

            result = mt5.order_send(request)
            if result is None:
                err = mt5.last_error()
                logger.error("MT5 order_send returned None: %s", err)
                # Full shutdown + reinitialize inside the lock
                mt5.shutdown()
                import time; time.sleep(1)
                kwargs = {}
                if self.path:     kwargs["path"] = self.path
                if self.login:    kwargs["login"] = self.login
                if self.password: kwargs["password"] = self.password
                if self.server:   kwargs["server"] = self.server
                mt5.initialize(**kwargs)
                # Update price after reconnect
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    request["price"] = tick.ask if is_buy else tick.bid
                result = mt5.order_send(request)
                if result is None:
                    return {"success": False, "error": f"order_send None after reconnect: {mt5.last_error()}"}

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("MT5 order failed: retcode=%d comment='%s'", result.retcode, result.comment)
                return {"success": False, "error": f"retcode {result.retcode}: {result.comment}"}

            logger.info("MT5 OPEN OK: ticket=%s %s %s %s @ %.5f", result.order, order_type, direction, symbol, price)
            return {"success": True, "ticket": str(result.order), "message": "Order placed"}

    def modify_sl(self, ticket: str, new_sl: float, symbol: str = "") -> dict:
        """Modify stop loss of an open position."""
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            return {"success": False, "error": f"Invalid ticket: {ticket}"}
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"SL -> {new_sl}"}

        with _mt5_lock:
            self._ensure_connected()
            pos = mt5.positions_get(ticket=ticket_int)
            if not pos:
                return {"success": False, "error": f"Position not found: {ticket}"}
            p = pos[0]
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket_int,
                "sl": new_sl,
                "tp": p.tp,
            }
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                code = result.retcode if result else -1
                return {"success": False, "error": f"SLTP failed: {code}"}
            return {"success": True, "ticket": ticket, "message": f"SL modified to {new_sl}"}

    def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        """Close a percentage of the position."""
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            return {"success": False, "error": f"Invalid ticket: {ticket}"}
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"Closed {percent}%"}

        with _mt5_lock:
            self._ensure_connected()
            pos = mt5.positions_get(ticket=ticket_int)
            if not pos:
                return {"success": False, "error": f"Position not found: {ticket}"}
            p = pos[0]
            close_vol = round(p.volume * percent, 2)
            step = mt5.symbol_info(p.symbol).volume_step or 0.01
            close_vol = max(step, round(round(close_vol / step) * step, 2))
            is_buy = p.type == mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(p.symbol).bid if is_buy else mt5.symbol_info_tick(p.symbol).ask
            otype = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket_int,
                "symbol": p.symbol,
                "volume": close_vol,
                "type": otype,
                "price": price,
                "deviation": 10,
                "magic": 20250101,
                "comment": "TW-PARTIAL",
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                code = result.retcode if result else -1
                return {"success": False, "error": f"Partial close failed: {code}"}
            return {"success": True, "ticket": ticket, "closed_volume": close_vol}

    def close_trade(self, ticket: str, symbol: str = "") -> dict:
        """Fully close a position or cancel a pending order."""
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            if not symbol:
                return {"success": False, "error": "No ticket or symbol"}
            with _mt5_lock:
                self._ensure_connected()
                return self._close_all_by_symbol(symbol)
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": "Closed"}

        with _mt5_lock:
            self._ensure_connected()
            pos = mt5.positions_get(ticket=ticket_int)
            if pos:
                return self._close_position(pos[0])
            orders = mt5.orders_get(ticket=ticket_int)
            if orders:
                request = {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket_int}
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    return {"success": True, "ticket": ticket, "message": "Pending order cancelled"}
                return {"success": False, "error": f"Cancel failed: {result.retcode if result else -1}"}
            return {"success": False, "error": f"Position/order not found: {ticket}"}

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

    # ── Helpers ────────────────────────────────────────────────────────────

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

    def _close_position(self, p) -> dict:
        is_buy = p.type == mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(p.symbol).bid if is_buy else mt5.symbol_info_tick(p.symbol).ask
        otype = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": p.ticket,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": otype,
            "price": price,
            "deviation": 10,
            "magic": 20250101,
            "comment": "TW-CLOSE",
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else -1
            return {"success": False, "error": f"Close failed: {code}"}

        return {"success": True, "ticket": str(p.ticket), "close_price": price, "message": "Closed"}

    def _close_all_by_symbol(self, symbol: str) -> dict:
        norm = self._normalize_symbol(symbol)
        closed = 0
        for p in (mt5.positions_get(symbol=norm) or []):
            r = self._close_position(p)
            if r.get("success"):
                closed += 1
        return {"success": True, "message": f"Closed {closed} positions for {symbol}"}


# Singleton
_instance: Optional[MT5Direct] = None

def get_mt5_direct() -> MT5Direct:
    global _instance
    if _instance is None:
        _instance = MT5Direct()
    return _instance
