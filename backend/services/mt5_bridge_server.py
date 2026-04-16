"""
mt5_bridge_server.py — Standalone HTTP bridge for MetaTrader5.
Runs as a separate process to avoid IPC pipe corruption.
All MT5 operations go through this server.

Usage:  python backend/services/mt5_bridge_server.py
"""

import logging
import os
import sys
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mt5_bridge: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("mt5_bridge")

# ── Load .env if running standalone ───────────────────────────────────
from dotenv import load_dotenv
# Walk up to find .env
_here = os.path.dirname(os.path.abspath(__file__))
for _d in [_here, os.path.join(_here, ".."), os.path.join(_here, "..", "..")]:
    _env = os.path.join(_d, ".env")
    if os.path.exists(_env):
        load_dotenv(_env)
        break

# ── MT5 import ────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not installed — bridge will run in simulation mode")

# ── Config ────────────────────────────────────────────────────────────
MT5_PATH = os.getenv("MT5_PATH", "")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# ── Symbol aliases ────────────────────────────────────────────────────
_SYMBOL_ALIASES = {
    "XAUUSD": ["GOLD", "#GOLD", "XAUUSD", "XAUUSDm"],
    "XAGUSD": ["SILVER", "#SILVER", "XAGUSD"],
    "US30": ["US30", "DJ30", "#DJ30"],
    "NAS100": ["NAS100", "USTEC", "#NAS100"],
    "US500": ["US500", "SP500", "#SP500"],
}


# ── Helpers ───────────────────────────────────────────────────────────
def _init_kwargs():
    kw = {}
    if MT5_PATH:     kw["path"] = MT5_PATH
    if MT5_LOGIN:    kw["login"] = MT5_LOGIN
    if MT5_PASSWORD: kw["password"] = MT5_PASSWORD
    if MT5_SERVER:   kw["server"] = MT5_SERVER
    kw["timeout"] = 10000  # 10 second timeout instead of default 60s
    return kw


def _connect() -> bool:
    """Initialize MT5 connection."""
    if not MT5_AVAILABLE:
        return True
    kw = _init_kwargs()
    for attempt in range(3):
        if mt5.initialize(**kw):
            info = mt5.account_info()
            if info:
                logger.info("MT5 connected — Account %s | Balance %.2f %s",
                            info.login, info.balance, info.currency)
                # Verify correct account
                if MT5_LOGIN and info.login != MT5_LOGIN:
                    logger.warning("Connected to wrong account %d (expected %d), retrying...",
                                   info.login, MT5_LOGIN)
                    mt5.shutdown()
                    import time; time.sleep(2)
                    continue
            return True
        logger.warning("MT5 connect attempt %d/3 failed: %s", attempt + 1, mt5.last_error())
        import time; time.sleep(2)
    logger.error("MT5 connection failed after 3 attempts")
    return False


def _fresh_connect():
    """Reinitialize MT5 without shutdown (shutdown blocks indefinitely)."""
    if not MT5_AVAILABLE:
        return
    kw = _init_kwargs()
    ok = mt5.initialize(**kw)
    if not ok:
            logger.error("fresh_connect FAILED after shutdown: %s", mt5.last_error())


def _normalize_symbol(raw: str) -> str:
    if not MT5_AVAILABLE:
        return raw
    info = mt5.symbol_info(raw)
    if info:
        mt5.symbol_select(raw, True)
        return raw
    for alias in _SYMBOL_ALIASES.get(raw.upper(), []):
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


def _normalize_lots(symbol: str, lots: float) -> float:
    if not MT5_AVAILABLE:
        return round(lots, 2)
    info = mt5.symbol_info(symbol)
    if not info:
        return round(lots, 2)
    step = info.volume_step or 0.01
    lots = max(info.volume_min, min(lots, info.volume_max))
    return round(round(lots / step) * step, 2)


def _sanitize_comment(raw: str) -> str:
    """ASCII only, max 31 chars."""
    clean = ''.join(c for c in raw if c.isascii() and (c.isalnum() or c in ' -_.'))[:31]
    return clean or "TW"


# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(title="MT5 Bridge", version="1.0.0")


_mt5_initialized = False
_keepalive_thread = None

def _keepalive_loop():
    """Ping MT5 every 60s with order_check to keep the order pipe alive.
    account_info() works even with a dead pipe — order_check exercises
    the same code path as order_send."""
    import time
    while True:
        time.sleep(60)
        if _mt5_initialized and MT5_AVAILABLE:
            try:
                # Use order_check (not account_info) to keep the order pipe warm
                tick = mt5.symbol_info_tick("EURUSD")
                if tick:
                    check = mt5.order_check({
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": "EURUSD",
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY,
                        "price": tick.ask,
                    })
                    if check is None:
                        logger.warning("Keepalive: order_check returned None — reconnecting...")
                        _connect()
                else:
                    logger.warning("Keepalive: no tick data — reconnecting...")
                    _connect()
            except Exception as e:
                logger.warning("Keepalive error: %s", e)

@app.on_event("startup")
def startup():
    global _keepalive_thread
    logger.info("MT5 Bridge started on port 5555 — MT5 will connect on first request")
    _keepalive_thread = __import__('threading').Thread(target=_keepalive_loop, daemon=True)
    _keepalive_thread.start()


def _ensure_init():
    """Lazy MT5 initialization on first request."""
    global _mt5_initialized
    if _mt5_initialized or not MT5_AVAILABLE:
        return
    _connect()
    _mt5_initialized = True

@app.get("/health")
def health():
    if not MT5_AVAILABLE:
        return {"status": "ok", "mt5_available": False, "connected": True}
    _ensure_init()
    info = mt5.account_info()
    return {"status": "ok", "mt5_available": True, "connected": info is not None,
            "account": info.login if info else None}


@app.get("/account")
def account():
    if not MT5_AVAILABLE:
        return {"balance": 10000.0, "equity": 10000.0, "currency": "USD", "simulated": True}
    info = mt5.account_info()
    if not info:
        return {"error": "Not connected"}
    return {
        "login": info.login, "balance": info.balance, "equity": info.equity,
        "margin": info.margin, "margin_free": info.margin_free,
        "currency": info.currency, "leverage": info.leverage,
    }


@app.get("/positions")
def positions():
    if not MT5_AVAILABLE:
        return []
    pos = mt5.positions_get()
    if not pos:
        return []
    return [
        {
            "ticket": p.ticket, "symbol": p.symbol,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": p.volume, "price_open": p.price_open,
            "price_current": p.price_current, "sl": p.sl, "tp": p.tp,
            "profit": p.profit, "comment": p.comment,
        }
        for p in pos
    ]


@app.get("/candles")
def candles(symbol: str = Query(...), timeframe: str = Query("H1"), count: int = Query(500)):
    if not MT5_AVAILABLE:
        return []
    sym = _normalize_symbol(symbol)
    if not sym:
        return []
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
    }
    tf_id = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(sym, tf_id, 0, min(count, 50000))
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


@app.get("/tick")
def tick(symbol: str = Query(...)):
    if not MT5_AVAILABLE:
        return {"bid": 1.0, "ask": 1.0, "simulated": True}
    sym = _normalize_symbol(symbol)
    if not sym:
        return {"error": f"Symbol not found: {symbol}"}
    t = mt5.symbol_info_tick(sym)
    if not t:
        return {"error": f"No tick data for {sym}"}
    return {"bid": t.bid, "ask": t.ask, "last": t.last, "volume": t.volume, "time": t.time}


# ── Write models ──────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    symbol: str
    direction: str = "BUY"
    order_type: str = "MARKET"
    entry_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    lot_size: float = 0.01
    comment: str = "TW-ICT"


class ModifySLRequest(BaseModel):
    ticket: str
    new_sl: float
    symbol: str = ""


class CloseRequest(BaseModel):
    ticket: str = ""
    symbol: str = ""


class ClosePartialRequest(BaseModel):
    ticket: str
    symbol: str = ""
    percent: float = 0.5


class CheckMarginRequest(BaseModel):
    symbol: str
    direction: str
    lots: float


# ── Write endpoints ──────────────────────────────────────────────────

@app.post("/order_send")
def order_send(req: OrderRequest):
    _ensure_init()
    if not MT5_AVAILABLE:
        ticket = int(datetime.now().timestamp())
        logger.info("SIM OPEN %s %s @ lots=%.2f", req.direction, req.symbol, req.lot_size)
        return {"success": True, "ticket": str(ticket), "simulated": True}

    symbol = _normalize_symbol(req.symbol)
    if not symbol:
        return {"success": False, "error": f"Symbol not found: {req.symbol}"}

    lots = _normalize_lots(symbol, req.lot_size)
    comment = _sanitize_comment(req.comment)
    is_buy = req.direction.upper() == "BUY"

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"success": False, "error": f"No tick data for {symbol}"}
    price = tick.ask if is_buy else tick.bid
    otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    if req.order_type.upper() != "MARKET":
        logger.info("Overriding %s to MARKET for %s %s", req.order_type, req.direction, symbol)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": otype,
        "price": price,
        "sl": req.stop_loss,
        "tp": req.take_profit,
        "deviation": 10,
        "magic": 20250101,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    logger.info("MT5 OPEN: %s %s lots=%.2f price=%.5f sl=%.5f tp=%.5f",
                 req.direction, symbol, lots, price, req.stop_loss, req.take_profit)

    result = mt5.order_send(request)
    if result is None:
        err = mt5.last_error()
        logger.error("order_send returned None (1st try): %s", err)
        _fresh_connect()
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            request["price"] = tick.ask if is_buy else tick.bid
        result = mt5.order_send(request)
        if result is None:
            # Last resort: use a fresh subprocess for the order
            logger.warning("Retry failed too — trying subprocess fallback")
            return _subprocess_order(req)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error("Order failed: retcode=%d comment='%s'", result.retcode, result.comment)
        return {"success": False, "error": f"retcode {result.retcode}: {result.comment}"}

    logger.info("OPEN OK: ticket=%s %s %s @ %.5f", result.order, req.direction, symbol, price)
    return {"success": True, "ticket": str(result.order), "message": "Order placed"}


def _subprocess_order(req) -> dict:
    """Execute order in a fresh subprocess — guaranteed clean IPC pipe."""
    import subprocess, json
    script = f"""
import MetaTrader5 as mt5, json, sys
mt5.initialize(path=r'{MT5_PATH}', login={MT5_LOGIN}, password='{MT5_PASSWORD}', server='{MT5_SERVER}')
sym = '{req.symbol}'
info = mt5.symbol_info(sym)
if not info:
    for alias in {list(_SYMBOL_ALIASES.get(req.symbol.upper(), []))}:
        info = mt5.symbol_info(alias)
        if info: sym = alias; break
    if not info:
        for sfx in ['.z','m','+','.a']:
            info = mt5.symbol_info(sym+sfx)
            if info: sym = sym+sfx; break
if not info:
    print(json.dumps({{"success":False,"error":"Symbol not found"}}))
    sys.exit()
mt5.symbol_select(sym, True)
step = info.volume_step or 0.01
lots = max(info.volume_min, min({req.lot_size}, info.volume_max))
lots = round(round(lots/step)*step, 2)
is_buy = '{req.direction}'.upper() == 'BUY'
tick = mt5.symbol_info_tick(sym)
price = tick.ask if is_buy else tick.bid
r = mt5.order_send({{
    'action': mt5.TRADE_ACTION_DEAL, 'symbol': sym, 'volume': lots,
    'type': mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
    'price': price, 'sl': {req.stop_loss}, 'tp': {req.take_profit},
    'deviation': 10, 'magic': 20250101,
    'comment': '{"".join(c for c in req.comment[:31] if c.isascii() and (c.isalnum() or c in " -_."))}',
    'type_time': mt5.ORDER_TIME_GTC, 'type_filling': mt5.ORDER_FILLING_FOK,
}})
if r and r.retcode == 10009:
    print(json.dumps({{"success":True,"ticket":str(r.order)}}))
else:
    print(json.dumps({{"success":False,"error":f"retcode {{r.retcode if r else 'None'}}: {{r.comment if r else mt5.last_error()}}"}}))
mt5.shutdown()
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
        )
        if proc.stdout.strip():
            result = json.loads(proc.stdout.strip())
            if result.get("success"):
                logger.info("SUBPROCESS OK: ticket=%s %s %s", result.get("ticket"), req.direction, req.symbol)
            else:
                logger.error("SUBPROCESS FAILED: %s", result.get("error"))
            return result
        logger.error("Subprocess no output. stderr: %s", proc.stderr[-300:] if proc.stderr else "")
        return {"success": False, "error": "Subprocess no output"}
    except Exception as e:
        logger.error("Subprocess error: %s", e)
        return {"success": False, "error": str(e)}


@app.post("/modify_sl")
def modify_sl(req: ModifySLRequest):
    _ensure_init()
    ticket_int = int(req.ticket) if req.ticket and req.ticket.isdigit() else 0
    if not ticket_int:
        return {"success": False, "error": f"Invalid ticket: {req.ticket}"}
    if not MT5_AVAILABLE:
        return {"success": True, "ticket": req.ticket, "message": f"SL -> {req.new_sl}"}

    pos = mt5.positions_get(ticket=ticket_int)
    if not pos:
        return {"success": False, "error": f"Position not found: {req.ticket}"}
    p = pos[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket_int,
        "sl": req.new_sl,
        "tp": p.tp,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        return {"success": False, "error": f"SLTP failed: {code}"}
    return {"success": True, "ticket": str(ticket_int), "message": f"SL modified to {req.new_sl}"}


@app.post("/close")
def close(req: CloseRequest):
    _ensure_init()
    ticket_int = int(req.ticket) if req.ticket and req.ticket.isdigit() else 0
    if not MT5_AVAILABLE:
        return {"success": True, "ticket": req.ticket, "message": "Closed"}

    if not ticket_int:
        if not req.symbol:
            return {"success": False, "error": "No ticket or symbol"}
        # Close all by symbol
        sym = _normalize_symbol(req.symbol)
        closed = 0
        for p in (mt5.positions_get(symbol=sym) or []):
            r = _close_position(p)
            if r.get("success"):
                closed += 1
        return {"success": True, "message": f"Closed {closed} positions for {req.symbol}"}

    pos = mt5.positions_get(ticket=ticket_int)
    if pos:
        return _close_position(pos[0])

    orders = mt5.orders_get(ticket=ticket_int)
    if orders:
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket_int}
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return {"success": True, "ticket": req.ticket, "message": "Pending order cancelled"}
        return {"success": False, "error": f"Cancel failed: {result.retcode if result else -1}"}

    return {"success": False, "error": f"Position/order not found: {req.ticket}"}


@app.post("/close_partial")
def close_partial(req: ClosePartialRequest):
    _ensure_init()
    ticket_int = int(req.ticket) if req.ticket and req.ticket.isdigit() else 0
    if not ticket_int:
        return {"success": False, "error": f"Invalid ticket: {req.ticket}"}
    if not MT5_AVAILABLE:
        return {"success": True, "ticket": req.ticket, "message": f"Closed {req.percent*100}%"}

    pos = mt5.positions_get(ticket=ticket_int)
    if not pos:
        return {"success": False, "error": f"Position not found: {req.ticket}"}
    p = pos[0]
    close_vol = round(p.volume * req.percent, 2)
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
    return {"success": True, "ticket": req.ticket, "closed_volume": close_vol}


@app.post("/check_margin")
def check_margin(req: CheckMarginRequest):
    _ensure_init()
    if not MT5_AVAILABLE:
        return {"ok": True, "margin_required": 0, "margin_free": 99999, "max_lots": req.lots, "simulated": True}

    symbol = _normalize_symbol(req.symbol)
    if not symbol:
        return {"ok": False, "margin_required": 0, "margin_free": 0, "max_lots": 0,
                "error": f"Symbol not found: {req.symbol}"}

    account = mt5.account_info()
    if not account:
        return {"ok": False, "margin_required": 0, "margin_free": 0, "max_lots": 0,
                "error": "Cannot get account info"}

    margin_free = account.margin_free
    leverage = account.leverage or 100
    is_buy = req.direction.upper() == "BUY"
    otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"ok": False, "margin_required": 0, "margin_free": margin_free, "max_lots": 0,
                "error": f"No tick data for {symbol}"}
    price = tick.ask if is_buy else tick.bid

    check_req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": req.lots,
        "type": otype,
        "price": price,
    }
    check = mt5.order_check(check_req)
    if check is None:
        sym_info = mt5.symbol_info(symbol)
        if sym_info and sym_info.trade_contract_size > 0:
            margin_est = (req.lots * sym_info.trade_contract_size * price) / leverage
            ok = margin_free > margin_est * 1.1
            max_lots = req.lots if ok else _find_max_lots(symbol, margin_free, sym_info, price, leverage)
            return {"ok": ok, "margin_required": round(margin_est, 2),
                    "margin_free": round(margin_free, 2), "max_lots": max_lots, "leverage": leverage}
        return {"ok": False, "margin_required": 0, "margin_free": round(margin_free, 2),
                "max_lots": 0, "leverage": leverage, "error": "order_check failed and no symbol info"}

    margin_required = check.margin or 0

    # When margin_required is 0 but retcode is not DONE, estimate the real margin
    if margin_required == 0 and check.retcode != mt5.TRADE_RETCODE_DONE:
        calc = mt5.order_calc_margin(otype, symbol, req.lots, price)
        if calc is not None and calc > 0:
            margin_required = round(calc, 2)
            logger.info("order_calc_margin for %.2f %s: $%.2f", req.lots, symbol, margin_required)
        else:
            sym_info = mt5.symbol_info(symbol)
            if sym_info and sym_info.trade_contract_size > 0:
                margin_required = round((req.lots * sym_info.trade_contract_size * price) / leverage, 2)

    ok = check.retcode == mt5.TRADE_RETCODE_DONE or margin_free > margin_required * 1.1
    max_lots = req.lots
    if not ok and margin_required > 0:
        ratio = (margin_free * 0.9) / margin_required
        max_lots = _normalize_lots(symbol, req.lots * ratio)

    return {
        "ok": ok, "margin_required": round(margin_required, 2),
        "margin_free": round(margin_free, 2), "max_lots": max_lots,
        "leverage": leverage, "retcode": check.retcode, "comment": check.comment,
    }


def _close_position(p) -> dict:
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


def _find_max_lots(symbol, margin_free, sym_info, price, leverage):
    if sym_info.trade_contract_size <= 0 or price <= 0:
        return 0.01
    max_lots = (margin_free * 0.9 * leverage) / (sym_info.trade_contract_size * price)
    return _normalize_lots(symbol, max_lots)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5555, log_level="info")
