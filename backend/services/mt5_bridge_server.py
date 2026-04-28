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
    "US30": ["US_30", "US30", "DJ30", "#DJ30"],
    "NAS100": ["US_TECH100", "NAS100", "USTEC", "#NAS100"],
    "US500": ["US_500", "US500", "SP500", "#SP500"],
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
    """Reinitialize MT5 without shutdown (shutdown blocks indefinitely).
    Verifies the login matches MT5_LOGIN — initialize(path=...) can silently
    route to the wrong pipe when multiple MT5 terminals are installed
    (documented issue, mql5 forum 351590)."""
    if not MT5_AVAILABLE:
        return
    kw = _init_kwargs()
    ok = mt5.initialize(**kw)
    if not ok:
        logger.error("fresh_connect FAILED: %s", mt5.last_error())
        return
    if MT5_LOGIN:
        info = mt5.account_info()
        if info and info.login != MT5_LOGIN:
            logger.error("fresh_connect routed to wrong account %d (expected %d)",
                         info.login, MT5_LOGIN)


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
    """Strict comment sanitizer — AvaTrade actively rejects comments with
    certain patterns (empirically: 31-char + double spaces + words like
    'Block'/'Breaker'/'-TP' triggers genuine -2 'Invalid comment argument').

    Empirically proven tolerant: short ASCII alphanum + single hyphen,
    max 20 chars, no consecutive spaces, no weird patterns.

    Strategy: keep only [A-Za-z0-9_-], single hyphen prefix 'TW-',
    collapse whitespace, cap at 20 chars. Fallback to 'TW' if empty.
    """
    if not raw:
        return "TW"
    # Strip to ascii alnum + hyphen + underscore only (no spaces, no dots,
    # no '+' which the old code already removed). Collapse everything else
    # into a single hyphen separator.
    import re as _re
    clean = _re.sub(r'[^A-Za-z0-9_-]+', '-', raw)
    clean = _re.sub(r'-+', '-', clean).strip('-')
    if len(clean) > 20:
        clean = clean[:20].rstrip('-')
    return clean or "TW"


# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(title="MT5 Bridge", version="1.0.0")


_mt5_initialized = False
_keepalive_thread = None
_keepalive_symbol = "EURUSD"

# Global lock: serializes every mt5.* call AND every order_send subprocess.
# Rationale: while an order_send subprocess is running, ANY mt5.* call from
# the bridge (keepalive tick, positions, candles) touches the same MT5
# terminal and corrupts the subprocess's pipe — subprocess gets
# 'order_check None (-2, Invalid comment)'. Holding this lock around all
# mt5 interactions + during the subprocess eliminates the conflict.
import threading as _threading
_MT5_LOCK = _threading.Lock()

def _keepalive_loop():
    """Heartbeat with symbol_info_tick — keeps the IPC pipe warm.
    MUST acquire _MT5_LOCK to not collide with an in-flight order_send
    subprocess. Uses non-blocking acquire so if the lock is held by a
    subprocess, this skip is harmless."""
    import time
    while True:
        time.sleep(2)  # 2s instead of 1s — lighter pressure on the terminal
        if _mt5_initialized and MT5_AVAILABLE:
            if not _MT5_LOCK.acquire(blocking=False):
                continue  # order_send in flight, skip this heartbeat
            try:
                mt5.symbol_info_tick(_keepalive_symbol)
            except Exception as e:
                logger.warning("Keepalive tick error: %s", e)
            finally:
                _MT5_LOCK.release()


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
    with _MT5_LOCK:
        info = mt5.account_info()
    return {"status": "ok", "mt5_available": True, "connected": info is not None,
            "account": info.login if info else None}


@app.post("/reset")
def reset():
    """Force a clean re-initialization of the MT5 session. Used by the
    backend keep-alive when it detects connected=false — instead of
    waiting for the next implicit _ensure_init, drop the global flag and
    immediately try to relink. Returns the same shape as /health."""
    if not MT5_AVAILABLE:
        return {"status": "ok", "mt5_available": False, "connected": True, "reset": False}
    global _mt5_initialized
    with _MT5_LOCK:
        try:
            mt5.shutdown()
        except Exception as exc:
            logger.warning("mt5.shutdown during /reset raised: %s", exc)
        _mt5_initialized = False
        ok = _connect()
        info = mt5.account_info() if ok else None
    return {"status": "ok", "mt5_available": True,
            "connected": info is not None,
            "account": info.login if info else None,
            "reset": True, "ok": bool(ok)}


@app.get("/account")
def account():
    if not MT5_AVAILABLE:
        return {"balance": 10000.0, "equity": 10000.0, "currency": "USD", "simulated": True}
    with _MT5_LOCK:
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
    with _MT5_LOCK:
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


_TF_MAP = {
    "M1": mt5.TIMEFRAME_M1 if MT5_AVAILABLE else None,
    "M5": mt5.TIMEFRAME_M5 if MT5_AVAILABLE else None,
    "M15": mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None,
    "M30": mt5.TIMEFRAME_M30 if MT5_AVAILABLE else None,
    "H1": mt5.TIMEFRAME_H1 if MT5_AVAILABLE else None,
    "H4": mt5.TIMEFRAME_H4 if MT5_AVAILABLE else None,
    "D1": mt5.TIMEFRAME_D1 if MT5_AVAILABLE else None,
    "W1": mt5.TIMEFRAME_W1 if MT5_AVAILABLE else None,
} if MT5_AVAILABLE else {}


def _serialize_rates(rates) -> list[dict]:
    if rates is None or len(rates) == 0:
        return []
    out = []
    for r in rates:
        ts = datetime.utcfromtimestamp(int(r[0])).strftime("%Y-%m-%dT%H:%M:%S")
        out.append({
            "time": ts, "open": round(float(r[1]), 6),
            "high": round(float(r[2]), 6), "low": round(float(r[3]), 6),
            "close": round(float(r[4]), 6), "volume": int(r[5]),
        })
    return out


@app.get("/candles")
def candles(symbol: str = Query(...), timeframe: str = Query("H1"), count: int = Query(500)):
    if not MT5_AVAILABLE:
        return []
    with _MT5_LOCK:
        sym = _normalize_symbol(symbol)
        if not sym:
            return []
        tf_id = _TF_MAP.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(sym, tf_id, 0, min(count, 50000))
    return _serialize_rates(rates)


@app.get("/candles/range")
def candles_range(symbol: str = Query(...), timeframe: str = Query("M1"),
                  from_ts: str = Query(...), to_ts: str = Query(...)):
    """Fetch candles between two ISO datetimes. Used by the backtester to
    pull M1 bars for precise intra-H1-candle entry/exit timestamps. The
    backtester was calling this endpoint and getting silent 404s, falling
    back to H1-resolution timestamps and the 'M1 not available' warning.
    Now wired through mt5.copy_rates_range."""
    if not MT5_AVAILABLE:
        return {"candles": [], "error": "mt5_unavailable"}
    try:
        # Accept ISO with or without T separator, with or without trailing Z
        def _parse(s: str) -> datetime:
            s = s.replace("Z", "").replace("T", " ")
            return datetime.fromisoformat(s)
        dt_from = _parse(from_ts)
        dt_to   = _parse(to_ts)
    except Exception as exc:
        return {"candles": [], "error": f"bad timestamp: {exc}"}
    with _MT5_LOCK:
        sym = _normalize_symbol(symbol)
        if not sym:
            return {"candles": [], "error": f"unknown symbol: {symbol}"}
        tf_id = _TF_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M1)
        rates = mt5.copy_rates_range(sym, tf_id, dt_from, dt_to)
    return {"candles": _serialize_rates(rates), "count": len(rates) if rates is not None else 0}


@app.get("/tick")
def tick(symbol: str = Query(...)):
    if not MT5_AVAILABLE:
        return {"bid": 1.0, "ask": 1.0, "simulated": True}
    with _MT5_LOCK:
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

def _pick_filling_mode(symbol_info) -> int:
    """Pick a filling mode the broker actually accepts RIGHT NOW.
    Ava flips between FOK/IOC/RETURN during the day; read the bitmask fresh."""
    fm = getattr(symbol_info, "filling_mode", 0) or 0
    if fm & 1:
        return mt5.ORDER_FILLING_FOK
    if fm & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _conform_stops(sym_info, tick, is_buy: bool, price: float,
                    sl: float, tp: float) -> tuple[float, float]:
    """Ensure SL/TP respect broker stops_level + freeze_level + spread.
    Ava's USDCHF widens stops_level at session boundaries; stale SL values
    become invalid and order_send returns -2 (Invalid stops masked as
    Invalid comment). Bumps SL/TP to the minimum required distance.
    Returns (sl, tp), both rounded to symbol digits. Zero stays zero."""
    point = sym_info.point or 0.00001
    digits = sym_info.digits or 5
    stops_level = (sym_info.trade_stops_level or 0) * point
    freeze_level = (sym_info.trade_freeze_level or 0) * point
    spread = max((tick.ask - tick.bid), 0)
    safety = 5 * point
    min_dist = max(stops_level, freeze_level) + spread + safety

    if sl:
        if is_buy:
            min_sl = price - min_dist
            if sl > min_sl:
                sl = min_sl
        else:
            min_sl = price + min_dist
            if sl < min_sl:
                sl = min_sl
        sl = round(sl, digits)
    if tp:
        if is_buy:
            min_tp = price + min_dist
            if tp < min_tp:
                tp = min_tp
        else:
            min_tp = price - min_dist
            if tp > min_tp:
                tp = min_tp
        tp = round(tp, digits)
    return sl, tp


def _deviation_for(symbol: str) -> int:
    """CHF pairs need wider deviation due to volatile spread at session rollover."""
    if "CHF" in symbol:
        return 200
    if "JPY" in symbol:
        return 100
    return 50


@app.post("/order_send")
def order_send(req: OrderRequest):
    _ensure_init()
    if not MT5_AVAILABLE:
        ticket = int(datetime.now().timestamp())
        logger.info("SIM OPEN %s %s @ lots=%.2f", req.direction, req.symbol, req.lot_size)
        return {"success": True, "ticket": str(ticket), "simulated": True}

    # Serialize: hold the lock for the ENTIRE order flow including the
    # subprocess call. No other mt5.* activity can run concurrently.
    with _MT5_LOCK:
        return _order_send_locked(req)


def _order_send_locked(req: OrderRequest) -> dict:
    import json as _json
    # FULL VERBOSE LOG — every parameter the backend sent + every parameter
    # we compute. This is the debug trail we need to find why real trades
    # fail while stress-test EURUSD 0.01 succeeds.
    logger.info("────── ORDER REQUEST DUMP ──────")
    logger.info("  raw req: %s", _json.dumps(req.model_dump(), default=str))

    symbol = _normalize_symbol(req.symbol)
    if not symbol:
        return {"success": False, "error": f"Symbol not found: {req.symbol}"}

    lots = _normalize_lots(symbol, req.lot_size)
    comment = _sanitize_comment(req.comment)
    is_buy = req.direction.upper() == "BUY"

    # Re-read symbol spec FRESH (stops_level, filling_mode, trade_mode change
    # during the session — caching them is the #1 cause of silent -2 errors).
    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        return {"success": False, "error": f"No symbol_info for {symbol}"}
    if not sym_info.visible:
        mt5.symbol_select(symbol, True)
        sym_info = mt5.symbol_info(symbol) or sym_info

    # Guard: the symbol must be in FULL trade mode. If the broker flipped it
    # to CLOSE_ONLY / LONG_ONLY / SHORT_ONLY / DISABLED, order_send will
    # return -2 and we want to know why instead of spinning retries.
    if sym_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        return {"success": False,
                "error": f"Symbol {symbol} trade_mode={sym_info.trade_mode} (not FULL) — broker restricted"}

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"success": False, "error": f"No tick data for {symbol}"}
    price = tick.ask if is_buy else tick.bid
    otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    # Reject stale ticks — a >500ms old tick on CHF during rollover is a
    # recipe for Invalid stops.
    tick_age_s = max(0, datetime.now().timestamp() - (tick.time or 0))
    if tick_age_s > 3:
        logger.warning("Stale tick for %s (age=%.1fs) — proceeding but wider deviation",
                       symbol, tick_age_s)

    if req.order_type.upper() != "MARKET":
        logger.info("Overriding %s to MARKET for %s %s", req.order_type, req.direction, symbol)

    # Conform SL/TP to broker-side minimum distance (stops_level + freeze_level + spread).
    sl, tp = _conform_stops(sym_info, tick, is_buy, price, req.stop_loss, req.take_profit)
    if sl != req.stop_loss or tp != req.take_profit:
        logger.info("Stops conformed for %s: sl %.5f→%.5f, tp %.5f→%.5f (stops_level=%d pts)",
                     symbol, req.stop_loss, sl, req.take_profit, tp,
                     sym_info.trade_stops_level or 0)

    # Filling mode read from THIS symbol's spec at THIS moment.
    filling = _pick_filling_mode(sym_info)
    deviation = _deviation_for(symbol)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": otype,
        "price": round(price, sym_info.digits or 5),
        "deviation": deviation,
        "magic": 20250101,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    if sl:
        request["sl"] = sl
    if tp:
        request["tp"] = tp

    # FULL DUMP of every conformed/computed parameter before subprocess call.
    logger.info("  symbol(normalized): %s", symbol)
    logger.info("  symbol_info: visible=%s trade_mode=%s stops_level=%s filling_bitmask=%s digits=%s point=%s",
                 sym_info.visible, sym_info.trade_mode, sym_info.trade_stops_level,
                 sym_info.filling_mode, sym_info.digits, sym_info.point)
    logger.info("  tick: bid=%s ask=%s time=%s (age=%.1fs)",
                 tick.bid, tick.ask, tick.time, tick_age_s)
    logger.info("  lots(norm)=%s  price(rounded)=%s  sl=%s  tp=%s",
                 lots, request["price"], sl, tp)
    logger.info("  deviation=%s  filling=%s  comment=%r (len=%d)",
                 deviation, filling, comment, len(comment))
    logger.info("  request dict: %s", _json.dumps(request, default=str))
    logger.info("────────────────────────────────")

    # EXECUTE VIA SUBPROCESS — a standalone Python process with fresh
    # initialize() was empirically proven to succeed (retcode 10009) where
    # the long-running bridge returns None. The bridge's in-process MT5
    # library session gets poisoned over time (documented MetaTrader5 bug);
    # a short-lived subprocess sidesteps that entirely.
    sub_result = _subprocess_order_v2(
        symbol=symbol,
        is_buy=is_buy,
        lot_size=lots,
        price=request["price"],
        sl=sl,
        tp=tp,
        deviation=deviation,
        filling=filling,
        comment=comment,
    )
    if sub_result.get("success"):
        logger.info("OPEN OK (subprocess): ticket=%s %s %s @ %.5f",
                    sub_result.get("ticket"), req.direction, symbol, price)
        return sub_result

    # Subprocess failed with a real retcode (not a wedge). Surface the error.
    err = sub_result.get("error", "unknown")
    logger.error("Subprocess order_send failed: %s", err)

    # If the subprocess itself couldn't even initialize, the Ava terminal
    # is likely stuck — suicide the bridge so the watchdog restarts Ava.
    if "init failed" in err.lower():
        import os as _os, threading as _th
        _th.Timer(0.5, lambda: _os._exit(1)).start()
        return {"success": False, "error": f"{err} (bridge will restart to force Ava reconnect)"}

    return sub_result


def _subprocess_order_v2(symbol: str, is_buy: bool, lot_size: float,
                          price: float, sl: float, tp: float,
                          deviation: int, filling: int, comment: str) -> dict:
    """Execute order in a short-lived Python subprocess.

    Empirically proven via diag_ordersend.py: a fresh Python process with
    mt5.initialize() successfully sends orders where the long-running bridge
    session returns None. Slower (~1-2s) but reliable.

    Runs order_check first to surface the REAL broker retcode (10030
    unsupported filling / 10016 invalid stops / etc) instead of the
    misleading -2 from the wrapper.
    """
    import subprocess, json
    # Subprocess script with verbose DEBUG lines to stderr so we can see
    # WHERE exactly it fails (init? order_check? order_send?).
    script = f"""
import MetaTrader5 as mt5, json, sys
sys.stderr.write('SUB: entry\\n')
ok = mt5.initialize(path=r'{MT5_PATH}', login={MT5_LOGIN}, password='{MT5_PASSWORD}', server='{MT5_SERVER}', timeout=10000)
sys.stderr.write(f'SUB: initialize={{ok}} last_err={{mt5.last_error()}}\\n')
if not ok:
    print(json.dumps({{"success":False,"error":"init failed: "+str(mt5.last_error())}}))
    sys.exit()
info = mt5.account_info()
sys.stderr.write(f'SUB: account={{info.login if info else None}} server={{info.server if info else None}}\\n')
si = mt5.symbol_info('{symbol}')
sys.stderr.write(f'SUB: symbol_info visible={{si.visible if si else None}} trade_mode={{si.trade_mode if si else None}} filling_bitmask={{si.filling_mode if si else None}} stops_level={{si.trade_stops_level if si else None}}\\n')
req = {{
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': '{symbol}',
    'volume': {lot_size},
    'type': mt5.ORDER_TYPE_BUY if {is_buy} else mt5.ORDER_TYPE_SELL,
    'price': {price},
    'deviation': {deviation},
    'magic': 20250101,
    'comment': {comment!r},
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': {filling},
}}
if {sl}: req['sl'] = {sl}
if {tp}: req['tp'] = {tp}
sys.stderr.write(f'SUB: request={{req}}\\n')
chk = mt5.order_check(req)
if chk is None:
    sys.stderr.write(f'SUB: order_check=None last_err={{mt5.last_error()}}\\n')
    print(json.dumps({{"success":False,"error":"order_check None: "+str(mt5.last_error())}}))
    sys.exit()
sys.stderr.write(f'SUB: order_check retcode={{chk.retcode}} comment={{chk.comment}}\\n')
if chk.retcode not in (0, 10009):
    print(json.dumps({{"success":False,"error":f"check {{chk.retcode}}: {{chk.comment}}"}}))
    sys.exit()
r = mt5.order_send(req)
sys.stderr.write(f'SUB: order_send retcode={{r.retcode if r else None}} comment={{r.comment if r else mt5.last_error()}}\\n')
if r and r.retcode == 10009:
    print(json.dumps({{"success":True,"ticket":str(r.order),"message":"subprocess open","price":r.price}}))
else:
    print(json.dumps({{"success":False,"error":f"retcode {{r.retcode if r else 'None'}}: {{r.comment if r else mt5.last_error()}}"}}))
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=25,
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        # Always log the full subprocess output — this is where the truth lives
        logger.info("SUBPROC stdout: %s", out[-1500:] if out else "(empty)")
        if err:
            logger.warning("SUBPROC stderr: %s", err[-800:])
        logger.info("SUBPROC exit=%d", proc.returncode)
        if out:
            return json.loads(out.splitlines()[-1])
        return {"success": False, "error": f"no output, stderr={err[-300:]}"}
    except Exception as e:
        logger.error("SUBPROC exception: %s", e)
        return {"success": False, "error": f"subprocess exception: {e}"}


def _subprocess_order(symbol: str, direction: str, lot_size: float,
                        stop_loss: float, take_profit: float, comment: str) -> dict:
    """Execute order in a fresh Python subprocess — bypasses wedged IPC pipe.
    The subprocess does a clean initialize+order_send+shutdown so it gets a
    virgin pipe from the MT5 terminal. Slower (~1-2s) but works when the
    main bridge is stuck."""
    import subprocess, json, tempfile
    script = f"""
import MetaTrader5 as mt5, json, sys
ok = mt5.initialize(path=r'{MT5_PATH}', login={MT5_LOGIN}, password='{MT5_PASSWORD}', server='{MT5_SERVER}', timeout=10000)
if not ok:
    print(json.dumps({{"success":False,"error":"init failed: "+str(mt5.last_error())}}))
    sys.exit()
if {MT5_LOGIN}:
    info = mt5.account_info()
    if info and info.login != {MT5_LOGIN}:
        print(json.dumps({{"success":False,"error":f"wrong login {{info.login}}"}}))
        mt5.shutdown()
        sys.exit()
is_buy = '{direction}'.upper() == 'BUY'
tick = mt5.symbol_info_tick('{symbol}')
if not tick:
    print(json.dumps({{"success":False,"error":"no tick"}}))
    sys.exit()
price = tick.ask if is_buy else tick.bid
req = {{
    'action': mt5.TRADE_ACTION_DEAL, 'symbol': '{symbol}', 'volume': {lot_size},
    'type': mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
    'price': price, 'deviation': 50, 'magic': 20250101,
    'comment': {comment!r}, 'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_FOK,
}}
if {stop_loss}: req['sl'] = {stop_loss}
if {take_profit}: req['tp'] = {take_profit}
r = mt5.order_send(req)
if r and r.retcode == 10009:
    print(json.dumps({{"success":True,"ticket":str(r.order),"message":"subprocess open"}}))
else:
    print(json.dumps({{"success":False,"error":f"retcode {{r.retcode if r else 'None'}}: {{r.comment if r else mt5.last_error()}}"}}))
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=20,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout.strip().splitlines()[-1])
        return {"success": False, "error": f"no output, stderr={proc.stderr[-300:]}"}
    except Exception as e:
        return {"success": False, "error": f"subprocess exception: {e}"}


@app.post("/modify_sl")
def modify_sl(req: ModifySLRequest):
    _ensure_init()
    ticket_int = int(req.ticket) if req.ticket and req.ticket.isdigit() else 0
    if not ticket_int:
        return {"success": False, "error": f"Invalid ticket: {req.ticket}"}
    if not MT5_AVAILABLE:
        return {"success": True, "ticket": req.ticket, "message": f"SL -> {req.new_sl}"}

    with _MT5_LOCK:
        return _modify_sl_locked(req, ticket_int)


def _modify_sl_locked(req, ticket_int):
    pos = mt5.positions_get(ticket=ticket_int)
    if not pos:
        return {"success": False, "error": f"Position not found: {req.ticket}"}
    p = pos[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket_int,
        "sl": req.new_sl,
    }
    if p.tp:
        request["tp"] = p.tp

    _fresh_connect()
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        err = mt5.last_error() if result is None else ""
        return {"success": False, "error": f"SLTP failed: {code} {err}"}
    return {"success": True, "ticket": str(ticket_int), "message": f"SL modified to {req.new_sl}"}


@app.post("/close")
def close(req: CloseRequest):
    _ensure_init()
    ticket_int = int(req.ticket) if req.ticket and req.ticket.isdigit() else 0
    if not MT5_AVAILABLE:
        return {"success": True, "ticket": req.ticket, "message": "Closed"}

    with _MT5_LOCK:
        return _close_locked(req, ticket_int)


def _close_locked(req, ticket_int):
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
        _fresh_connect()
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

    with _MT5_LOCK:
        return _close_partial_locked(req, ticket_int)


def _close_partial_locked(req, ticket_int):
    pos = mt5.positions_get(ticket=ticket_int)
    if not pos:
        return {"success": False, "error": f"Position not found: {req.ticket}"}
    p = pos[0]
    close_vol = round(p.volume * req.percent, 2)
    step = mt5.symbol_info(p.symbol).volume_step or 0.01
    close_vol = max(step, round(round(close_vol / step) * step, 2))
    is_buy = p.type == mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    price = tick.bid if is_buy else tick.ask
    otype = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket_int,
        "symbol": p.symbol,
        "volume": close_vol,
        "type": otype,
        "price": price,
        "deviation": 50,
        "magic": 20250101,
        "comment": "TW-PARTIAL",
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    _fresh_connect()
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        err = mt5.last_error() if result is None else ""
        return {"success": False, "error": f"Partial close failed: {code} {err}"}
    return {"success": True, "ticket": req.ticket, "closed_volume": close_vol}


@app.post("/check_margin")
def check_margin(req: CheckMarginRequest):
    _ensure_init()
    if not MT5_AVAILABLE:
        return {"ok": True, "margin_required": 0, "margin_free": 99999, "max_lots": req.lots, "simulated": True}

    with _MT5_LOCK:
        return _check_margin_locked(req)


def _check_margin_locked(req):
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
    tick = mt5.symbol_info_tick(p.symbol)
    price = tick.bid if is_buy else tick.ask
    otype = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": p.ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": otype,
        "price": price,
        "deviation": 50,
        "magic": 20250101,
        "comment": "TW-CLOSE",
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    _fresh_connect()
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        err = mt5.last_error() if result is None else ""
        return {"success": False, "error": f"Close failed: {code} {err}"}
    return {"success": True, "ticket": str(p.ticket), "close_price": price, "message": "Closed"}


def _find_max_lots(symbol, margin_free, sym_info, price, leverage):
    if sym_info.trade_contract_size <= 0 or price <= 0:
        return 0.01
    max_lots = (margin_free * 0.9 * leverage) / (sym_info.trade_contract_size * price)
    return _normalize_lots(symbol, max_lots)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5555, log_level="info")
