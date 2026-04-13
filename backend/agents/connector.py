"""
Connector (CC) — Sends trades directly to MT5 via Python library.
No HTTP bridge needed — calls MetaTrader5 directly in-process.
"""

import json
import logging
import os
from datetime import datetime
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


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
        result = mt5.open_trade({
            "symbol": trade.get("symbol"),
            "direction": trade.get("direction"),
            "order_type": trade.get("order_type", "MARKET"),
            "entry_price": trade.get("entry_price"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit_1"),
            "lot_size": trade.get("lot_size"),
            "comment": f"TW-{trade.get('ict_setup', 'ICT')}"[:31],
        })

        if result.get("success"):
            await self.broadcast_status(
                "TRADE_SENT",
                f"Trade opened: ticket #{result.get('ticket', '?')}",
                result,
            )
        else:
            await self.broadcast_status(
                "SEND_FAILED",
                f"MT5 error: {result.get('error', 'Unknown')}",
                result,
            )
        return result

    async def modify_sl(self, ticket: str, new_sl: float, symbol: str) -> dict:
        await self.broadcast_status("MODIFYING_SL", f"Trailing SL for #{ticket} to {new_sl}...")
        mt5 = self._get_mt5()
        return mt5.modify_sl(ticket, new_sl, symbol)

    async def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        await self.broadcast_status("PARTIAL_CLOSE", f"Closing {percent:.0%} of #{ticket}...")
        mt5 = self._get_mt5()
        return mt5.close_partial(ticket, symbol, percent)

    async def close_trade(self, ticket: str, symbol: str) -> dict:
        await self.broadcast_status("CLOSING", f"Closing trade #{ticket}...")
        mt5 = self._get_mt5()
        return mt5.close_trade(ticket, symbol)
