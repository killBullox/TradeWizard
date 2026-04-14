"""
mt5_direct.py — MT5 interface with subprocess worker for order execution.

Read operations (get_candles, get_positions, health) run in the main process.
Write operations (open_trade, modify_sl, close, check_margin) run in a
dedicated subprocess (mt5_order_worker.py) that keeps a clean IPC pipe.
"""

import logging
import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Optional

logger = logging.getLogger("mt5_direct")

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
        self._worker = None  # subprocess for order execution

    # ── Worker subprocess for write operations ───────────────────────────

    def _ensure_worker(self):
        """No-op — kept for compatibility. Orders now use _run_order_script."""
        pass

    def _send_to_worker(self, cmd: dict) -> dict:
        """Launch a fresh Python process for each MT5 write operation.
        Each process: initialize → execute → shutdown → exit.
        This is the ONLY approach that works 100% reliably."""
        try:
            worker_script = os.path.join(os.path.dirname(__file__), "mt5_order_worker.py")
            proc = subprocess.run(
                [sys.executable, worker_script],
                input=json.dumps(cmd) + "\n",
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )

            # Parent stays connected — worker uses its own MT5 session
            if proc.stdout.strip():
                return json.loads(proc.stdout.strip().split("\n")[-1])
            logger.error("Worker produced no output. stderr: %s", proc.stderr[-500:] if proc.stderr else "")
            return {"success": False, "error": "Worker produced no output"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Worker timed out (30s)"}
        except Exception as e:
            logger.error("Worker error: %s", e)
            return {"success": False, "error": str(e)}

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            logger.info("MT5 not available — simulation mode")
            self.connected = True
            return True
        return self._connect_impl()

    def _connect_impl(self) -> bool:
        kwargs = {}
        if self.path:     kwargs["path"] = self.path
        if self.login:    kwargs["login"] = self.login
        if self.password: kwargs["password"] = self.password
        if self.server:   kwargs["server"] = self.server

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
        """Reconnect if not connected (e.g. after worker shutdown the parent's session)."""
        if not MT5_AVAILABLE:
            return
        if not self.connected:
            self._connect_impl()

    def _fresh_connect(self):
        """Shutdown + reinitialize MT5 for a clean IPC pipe. Called before every write operation."""
        if not MT5_AVAILABLE:
            return
        import threading
        tid = threading.current_thread().name
        mt5.shutdown()
        kwargs = {}
        if self.path:     kwargs["path"] = self.path
        if self.login:    kwargs["login"] = self.login
        if self.password: kwargs["password"] = self.password
        if self.server:   kwargs["server"] = self.server
        init_ok = mt5.initialize(**kwargs)
        if not init_ok:
            logger.error("MT5 fresh_connect FAILED on thread %s: %s (path=%s login=%s server=%s)",
                         tid, mt5.last_error(), self.path, self.login, self.server)
            return
        info = mt5.account_info()
        logger.info("MT5 fresh_connect OK on thread %s — account %s, init=%s",
                     tid, info.login if info else "NONE", init_ok)
        self.connected = True

    def _ensure_correct_account(self):
        """Full check — verify connected to the RIGHT account. Used by write methods inside lock."""
        if not MT5_AVAILABLE:
            return
        info = mt5.account_info()
        wrong_account = (info is not None and self.login and info.login != self.login)
        if info is None or wrong_account:
            if wrong_account:
                logger.warning("MT5 connected to WRONG account %d (expected %d) — reconnecting...",
                               info.login, self.login)
            else:
                logger.warning("MT5 disconnected — reconnecting to correct account...")
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
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False

    def worker_status(self) -> dict:
        """Worker is now per-request (fresh process each time). Always 'ready'."""
        if not MT5_AVAILABLE:
            return {"running": True, "simulated": True}
        return {"running": True, "mode": "per-request"}

    def health(self) -> dict:
        if not MT5_AVAILABLE:
            return {"status": "ok", "mt5_available": False, "connected": True}
        return self._health_impl()

    def _health_impl(self):
        info = mt5.account_info()
        return {"status": "ok", "mt5_available": True, "connected": info is not None}

    def get_account_info(self) -> dict:
        if not MT5_AVAILABLE:
            return {"balance": 10000.0, "equity": 10000.0, "currency": "USD", "simulated": True}
        return self._get_account_info_impl()

    def _get_account_info_impl(self):
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
        if not MT5_AVAILABLE:
            return {"ok": True, "margin_required": 0, "margin_free": 99999, "max_lots": lots, "simulated": True}
        return self._send_to_worker({
            "action": "check_margin",
            "symbol": symbol,
            "direction": direction,
            "lots": lots,
        })

    def _check_margin_locked(self, symbol, direction, lots):
        """Check margin for the requested trade."""
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
        """Open a trade via the dedicated worker subprocess."""
        if not MT5_AVAILABLE:
            ticket = int(datetime.now().timestamp())
            return {"success": True, "ticket": str(ticket), "simulated": True}

        result = self._send_to_worker({
            "action": "order_send",
            "symbol": signal.get("symbol", ""),
            "direction": signal.get("direction", "BUY"),
            "lot_size": float(signal.get("lot_size", 0.01)),
            "sl": float(signal.get("stop_loss", 0)),
            "tp": float(signal.get("take_profit", signal.get("take_profit_1", 0))),
            "comment": signal.get("comment", "TW-ICT")[:31],
        })
        if result.get("success"):
            logger.info("MT5 OPEN OK (worker): ticket=%s %s %s",
                        result.get("ticket"), signal.get("direction"), signal.get("symbol"))
        else:
            logger.error("MT5 OPEN FAILED (worker): %s", result.get("error"))
        return result

    def _open_trade_impl(self, signal: dict) -> dict:
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

        # Fresh init immediately before order_send — NO other MT5 calls between
        # fresh_connect and order_send (they corrupt the IPC pipe)
        self._fresh_connect()
        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            logger.error("MT5 order_send returned None (1st try): %s", err)
            # Retry with fresh shutdown+init (clean pipe)
            self._fresh_connect()
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                request["price"] = tick.ask if is_buy else tick.bid
            result = mt5.order_send(request)
            if result is None:
                return {"success": False, "error": f"order_send None after retry: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("MT5 order failed: retcode=%d comment='%s'", result.retcode, result.comment)
            return {"success": False, "error": f"retcode {result.retcode}: {result.comment}"}

        logger.info("MT5 OPEN OK: ticket=%s %s %s %s @ %.5f", result.order, order_type, direction, symbol, price)
        return {"success": True, "ticket": str(result.order), "message": "Order placed"}

    def modify_sl(self, ticket: str, new_sl: float, symbol: str = "") -> dict:
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            return {"success": False, "error": f"Invalid ticket: {ticket}"}
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"SL -> {new_sl}"}
        return self._send_to_worker({"action": "modify_sl", "ticket": ticket_int, "new_sl": new_sl})

    def _modify_sl_impl(self, ticket_int, new_sl):
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
        return {"success": True, "ticket": str(ticket_int), "message": f"SL modified to {new_sl}"}

    def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            return {"success": False, "error": f"Invalid ticket: {ticket}"}
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": f"Closed {percent}%"}
        # Close partial = close the ticket entirely (split positions handle partial via separate tickets)
        return self._send_to_worker({"action": "close", "ticket": ticket_int})

    def _close_partial_impl(self, ticket_int, symbol, percent):
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
        ticket_int = int(ticket) if ticket and ticket.isdigit() else 0
        if not ticket_int:
            if not symbol:
                return {"success": False, "error": "No ticket or symbol"}
            return self._close_all_by_symbol(symbol)
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": "Closed"}
        return self._send_to_worker({"action": "close", "ticket": ticket_int})

    def _close_all_by_symbol_fresh(self, symbol):
        self._ensure_connected()
        return self._close_all_by_symbol(symbol)

    def _close_trade_impl(self, ticket_int, symbol):
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
        return self._get_positions_impl()

    def _get_positions_impl(self):
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
        return self._get_candles_impl(symbol, timeframe, count)

    def _get_candles_impl(self, symbol, timeframe, count):
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
