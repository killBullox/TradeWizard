"""
Connector (CC) — Sends trades directly to MT5 via Python library.
No HTTP bridge needed — calls MetaTrader5 directly in-process.

Split logic: each trade is sent as up to 3 independent MT5 positions,
each with its own TP. If lots are too small to split, fewer positions
are opened with the farthest TP as fallback.
"""

import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# TP split ratios: TP1 gets 50%, TP2 gets 30%, TP3 gets 20%
TP_SPLITS = [
    ("take_profit_1", 0.50),
    ("take_profit_2", 0.30),
    ("take_profit_3", 0.20),
]


class ConnectorAgent(BaseAgent):
    name = "CC"
    emoji = "🔌"
    color = "#0891B2"

    def __init__(self, broadcast_fn=None):
        super().__init__(broadcast_fn)
        self._mt5 = None  # lazy init

    def _get_mt5(self):
        if self._mt5 is None:
            from services.mt5_direct import get_mt5_direct
            self._mt5 = get_mt5_direct()
            if not self._mt5.connected:
                self._mt5.connect()
        return self._mt5

    async def open_trade(self, trade: dict) -> dict:
        await self.broadcast_status(
            "SENDING",
            f"Sending {trade.get('symbol')} {trade.get('direction')} to MT5..."
        )

        mt5 = self._get_mt5()
        symbol = trade.get("symbol")
        total_lots = float(trade.get("lot_size", 0.01))
        comment_base = f"TW-{trade.get('ict_setup', 'ICT')}"[:28]

        # Build list of (tp_price, lot_fraction) for each TP level
        splits = []
        for tp_key, ratio in TP_SPLITS:
            tp_price = trade.get(tp_key)
            if tp_price:
                splits.append((float(tp_price), ratio, tp_key))

        if not splits:
            return {"success": False, "error": "No take profit levels provided"}

        # Normalize lots per split using MT5's volume constraints
        min_lot = 0.01
        step = 0.01
        try:
            import MetaTrader5 as _mt5
            sym_info = _mt5.symbol_info(mt5._normalize_symbol(symbol))
            if sym_info:
                min_lot = sym_info.volume_min or 0.01
                step = sym_info.volume_step or 0.01
        except Exception:
            pass

        def norm(lots):
            lots = max(min_lot, lots)
            return round(round(lots / step) * step, 2)

        # Allocate lots to each split
        allocated = []
        remaining = total_lots
        for i, (tp_price, ratio, tp_key) in enumerate(splits):
            if i == len(splits) - 1:
                # Last split gets whatever remains
                lot = norm(remaining)
            else:
                lot = norm(total_lots * ratio)
            if lot > remaining:
                lot = norm(remaining)
            if lot < min_lot:
                break  # can't allocate more splits
            allocated.append((tp_price, lot, tp_key))
            remaining = round(remaining - lot, 2)
            if remaining < min_lot:
                break

        # If we couldn't split at all (lots too small), send one order with TP1
        if not allocated:
            tp1_price = splits[0][0]
            allocated = [(tp1_price, norm(total_lots), "take_profit_1")]

        # If leftover lots exist from rounding, add to last split
        if remaining >= min_lot and allocated:
            last_tp, last_lot, last_key = allocated[-1]
            allocated[-1] = (last_tp, norm(last_lot + remaining), last_key)

        # Send each split as an independent MT5 position
        tickets = []
        first_result = None
        for i, (tp_price, lot, tp_key) in enumerate(allocated):
            tag = f"TP{i+1}"
            result = mt5.open_trade({
                "symbol": symbol,
                "direction": trade.get("direction"),
                "order_type": trade.get("order_type", "MARKET"),
                "entry_price": trade.get("entry_price"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": tp_price,
                "lot_size": lot,
                "comment": f"{comment_base}-{tag}"[:31],
            })

            if result.get("success"):
                ticket = result.get("ticket", "?")
                tickets.append(ticket)
                logger.info("Split %s: %s lots @ TP=%.5f → ticket #%s", tag, lot, tp_price, ticket)
            else:
                logger.error("Split %s FAILED: %s", tag, result.get("error"))
                # If the first order fails, abort
                if i == 0:
                    await self.broadcast_status(
                        "SEND_FAILED",
                        f"MT5 error: {result.get('error', 'Unknown')}",
                        result,
                    )
                    return result

            if i == 0:
                first_result = result

        # Return combined result — ticket field has first ticket (for DB),
        # all_tickets has the full list
        combined = {
            "success": len(tickets) > 0,
            "ticket": tickets[0] if tickets else "UNKNOWN",
            "all_tickets": tickets,
            "splits": len(allocated),
            "message": f"Opened {len(tickets)} positions: {', '.join(f'#{t}' for t in tickets)}",
        }

        await self.broadcast_status(
            "TRADE_SENT",
            f"Opened {len(tickets)} split positions for {symbol}",
            combined,
        )
        return combined

    async def modify_sl(self, ticket: str, new_sl: float, symbol: str) -> dict:
        """Modify SL on a ticket. If ticket contains multiple (comma-separated), modify all."""
        mt5 = self._get_mt5()
        tickets = [t.strip() for t in ticket.split(",") if t.strip()]
        if len(tickets) <= 1:
            await self.broadcast_status("MODIFYING_SL", f"Trailing SL for #{ticket} to {new_sl}...")
            return mt5.modify_sl(ticket, new_sl, symbol)

        results = []
        for t in tickets:
            r = mt5.modify_sl(t, new_sl, symbol)
            results.append(r)
        ok = all(r.get("success") for r in results)
        return {"success": ok, "tickets": tickets, "results": results}

    async def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        await self.broadcast_status("PARTIAL_CLOSE", f"Closing {percent:.0%} of #{ticket}...")
        mt5 = self._get_mt5()
        return mt5.close_partial(ticket, symbol, percent)

    async def close_trade(self, ticket: str, symbol: str) -> dict:
        """Close a trade. If ticket contains multiple (comma-separated), close all."""
        mt5 = self._get_mt5()
        tickets = [t.strip() for t in ticket.split(",") if t.strip()]
        if len(tickets) <= 1:
            await self.broadcast_status("CLOSING", f"Closing trade #{ticket}...")
            return mt5.close_trade(ticket, symbol)

        await self.broadcast_status("CLOSING", f"Closing {len(tickets)} positions for {symbol}...")
        results = []
        for t in tickets:
            r = mt5.close_trade(t, symbol)
            results.append(r)
        ok = all(r.get("success") for r in results)
        return {"success": ok, "tickets": tickets, "results": results}
