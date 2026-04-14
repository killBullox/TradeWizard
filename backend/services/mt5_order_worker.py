"""
mt5_order_worker.py — Dedicated subprocess for MT5 order execution.

This process does NOTHING except:
1. Initialize MT5 once
2. Read JSON commands from stdin
3. Execute order_send / modify_sl / close
4. Write JSON results to stdout

No get_candles, no get_positions, no symbol_info — those corrupt the IPC pipe.
This process keeps a clean MT5 session exclusively for write operations.

Usage: python mt5_order_worker.py
"""

import sys
import json
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mt5_worker: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("mt5_worker")

try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error("MetaTrader5 not installed")
    sys.exit(1)


def init_mt5():
    path = os.getenv("MT5_PATH", "")
    login = int(os.getenv("MT5_LOGIN", "0"))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")

    kwargs = {}
    if path:     kwargs["path"] = path
    if login:    kwargs["login"] = login
    if password: kwargs["password"] = password
    if server:   kwargs["server"] = server

    if not mt5.initialize(**kwargs):
        logger.error("MT5 init failed: %s", mt5.last_error())
        return False
    info = mt5.account_info()
    if info:
        logger.info("MT5 worker ready — account %d, balance %.2f", info.login, info.balance)
    return True


def fresh_init():
    """Full shutdown + initialize for a clean IPC pipe."""
    mt5.shutdown()
    return init_mt5()


def handle_order_send(cmd):
    symbol = cmd.get("symbol", "")
    direction = cmd.get("direction", "BUY")
    lots = float(cmd.get("lot_size", 0.01))
    sl = float(cmd.get("sl", 0))
    tp = float(cmd.get("tp", 0))
    comment = cmd.get("comment", "TW")[:31]
    # Sanitize comment
    comment = ''.join(c for c in comment if c.isascii() and (c.isalnum() or c in ' -_.'))[:31] or "TW"

    # Fresh init before every order
    if not fresh_init():
        return {"success": False, "error": "MT5 init failed"}

    # Normalize symbol
    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        # Try aliases
        for suffix in [".z", "m", "+", ".a", "-C", ".stp"]:
            sym_info = mt5.symbol_info(symbol + suffix)
            if sym_info:
                symbol = symbol + suffix
                break
        aliases = {
            "XAUUSD": ["GOLD", "#GOLD", "XAUUSDm"],
            "US30": ["DJ30", "#DJ30"],
            "NAS100": ["USTEC", "#NAS100"],
        }
        if not sym_info:
            for alias in aliases.get(symbol.upper(), []):
                sym_info = mt5.symbol_info(alias)
                if sym_info:
                    symbol = alias
                    break
    if not sym_info:
        return {"success": False, "error": f"Symbol not found: {cmd.get('symbol')}"}

    mt5.symbol_select(symbol, True)

    # Normalize lots
    step = sym_info.volume_step or 0.01
    lots = max(sym_info.volume_min, min(lots, sym_info.volume_max))
    lots = round(round(lots / step) * step, 2)

    is_buy = direction.upper() == "BUY"
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"success": False, "error": f"No tick for {symbol}"}

    price = tick.ask if is_buy else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 20250101,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    logger.info("ORDER: %s %s %s lots=%.2f price=%.5f sl=%.5f tp=%.5f",
                direction, symbol, "MARKET", lots, price, sl, tp)

    result = mt5.order_send(request)
    if result is None:
        err = mt5.last_error()
        logger.error("order_send None: %s — retrying with fresh init", err)
        fresh_init()
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            request["price"] = tick.ask if is_buy else tick.bid
        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "error": f"order_send None after retry: {mt5.last_error()}"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {"success": False, "error": f"retcode {result.retcode}: {result.comment}"}

    logger.info("OK: ticket=%s %s %s @ %.5f", result.order, direction, symbol, price)
    return {"success": True, "ticket": str(result.order)}


def handle_modify_sl(cmd):
    ticket = int(cmd.get("ticket", 0))
    new_sl = float(cmd.get("new_sl", 0))
    if not ticket:
        return {"success": False, "error": "No ticket"}

    fresh_init()
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        return {"success": False, "error": f"Position not found: {ticket}"}

    p = pos[0]
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": new_sl,
        "tp": p.tp,
    })
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        return {"success": False, "error": f"SLTP failed: {code}"}
    return {"success": True, "ticket": str(ticket)}


def handle_close(cmd):
    ticket = int(cmd.get("ticket", 0))
    if not ticket:
        return {"success": False, "error": "No ticket"}

    fresh_init()
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        # Try as pending order
        orders = mt5.orders_get(ticket=ticket)
        if orders:
            result = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"success": True, "ticket": str(ticket), "message": "Order cancelled"}
            return {"success": False, "error": f"Cancel failed: {result.retcode if result else -1}"}
        return {"success": False, "error": f"Not found: {ticket}"}

    p = pos[0]
    is_buy = p.type == mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(p.symbol).bid if is_buy else mt5.symbol_info_tick(p.symbol).ask

    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 10,
        "magic": 20250101,
        "comment": "TW-CLOSE",
        "type_filling": mt5.ORDER_FILLING_FOK,
    })
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else -1
        return {"success": False, "error": f"Close failed: {code}"}
    return {"success": True, "ticket": str(ticket), "close_price": price}


def handle_check_margin(cmd):
    symbol = cmd.get("symbol", "")
    direction = cmd.get("direction", "BUY")
    lots = float(cmd.get("lots", 0.01))

    fresh_init()
    info = mt5.account_info()
    if not info:
        return {"ok": False, "error": "No account info"}

    sym = mt5.symbol_info(symbol)
    if not sym:
        # Try GOLD alias
        for alias in ["GOLD", symbol + "m", symbol + ".z"]:
            sym = mt5.symbol_info(alias)
            if sym:
                symbol = alias
                break

    is_buy = direction.upper() == "BUY"
    otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"ok": False, "error": f"No tick for {symbol}", "margin_free": info.margin_free, "leverage": info.leverage, "equity": info.equity}

    price = tick.ask if is_buy else tick.bid
    check = mt5.order_check({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": otype,
        "price": price,
    })

    margin_req = check.margin if check else 0
    ok = check and (check.retcode == mt5.TRADE_RETCODE_DONE or info.margin_free > margin_req * 1.1)

    return {
        "ok": ok,
        "margin_required": round(margin_req, 2),
        "margin_free": round(info.margin_free, 2),
        "equity": round(info.equity, 2),
        "leverage": info.leverage,
    }


HANDLERS = {
    "order_send": handle_order_send,
    "modify_sl": handle_modify_sl,
    "close": handle_close,
    "check_margin": handle_check_margin,
    "ping": lambda cmd: {"pong": True},
}


def main():
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    logger.info("MT5 order worker starting...")
    if not init_mt5():
        logger.error("Failed to initialize MT5 — exiting")
        sys.exit(1)

    # Read single command from stdin, execute, output result, exit
    line = sys.stdin.readline().strip()
    if not line:
        sys.stdout.write(json.dumps({"error": "No input"}) + "\n")
        sys.stdout.flush()
        mt5.shutdown()
        return

    try:
        cmd = json.loads(line)
        action = cmd.get("action", "")
        handler = HANDLERS.get(action)
        if handler:
            result = handler(cmd)
        else:
            result = {"error": f"Unknown action: {action}"}
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        result = {"error": str(e)}

    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()
    mt5.shutdown()


if __name__ == "__main__":
    main()
