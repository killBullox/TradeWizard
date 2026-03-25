"""
Connector (CC)
Sends trade signals to MetaTrader 5 via HTTP webhook.
Also handles trade updates (SL modification, close).
"""

import json
import os
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional
import httpx
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ConnectorAgent(BaseAgent):
    name = "CC"
    emoji = "🔌"
    color = "#0891B2"

    def __init__(self, broadcast_fn=None):
        super().__init__(broadcast_fn)
        self.mt5_url = os.environ.get("MT5_WEBHOOK_URL", "http://localhost:5000/webhook")
        self.mt5_secret = os.environ.get("MT5_WEBHOOK_SECRET", "tradewizard_secret")
        self.simulation_mode = not os.environ.get("MT5_WEBHOOK_URL")

    def _sign_payload(self, payload: str) -> str:
        return hmac.new(
            self.mt5_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def open_trade(self, trade: dict) -> dict:
        await self.broadcast_status(
            "SENDING",
            f"{'[SIM] ' if self.simulation_mode else ''}Sending {trade.get('symbol')} {trade.get('direction')} to MT5..."
        )

        payload = {
            "action": "OPEN",
            "symbol":      trade.get("symbol"),
            "direction":   trade.get("direction"),
            "order_type":  trade.get("order_type", "LIMIT"),
            "entry_price": trade.get("entry_price"),
            "stop_loss":   trade.get("stop_loss"),
            "take_profit": trade.get("take_profit_1"),
            "lot_size":    trade.get("lot_size"),
            "comment":     f"TW-{trade.get('ict_setup','ICT')}",
            "timestamp":   datetime.utcnow().isoformat(),
        }

        result = await self._send_to_mt5(payload)

        if result.get("success"):
            await self.broadcast_status(
                "TRADE_SENT",
                f"✅ Trade opened: ticket #{result.get('ticket', 'SIM-001')}",
                result,
            )
        else:
            await self.broadcast_status(
                "SEND_FAILED",
                f"❌ MT5 error: {result.get('error', 'Unknown')}",
                result,
            )
        return result

    async def modify_sl(self, ticket: str, new_sl: float, symbol: str) -> dict:
        await self.broadcast_status("MODIFYING_SL", f"{'[SIM] ' if self.simulation_mode else ''}Trailing SL for #{ticket} to {new_sl}...")

        payload = {
            "action":    "MODIFY_SL",
            "ticket":    ticket,
            "symbol":    symbol,
            "new_sl":    new_sl,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._send_to_mt5(payload)

    async def close_partial(self, ticket: str, symbol: str, percent: float) -> dict:
        await self.broadcast_status("PARTIAL_CLOSE", f"{'[SIM] ' if self.simulation_mode else ''}Closing {percent}% of #{ticket}...")

        payload = {
            "action":    "CLOSE_PARTIAL",
            "ticket":    ticket,
            "symbol":    symbol,
            "percent":   percent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._send_to_mt5(payload)

    async def close_trade(self, ticket: str, symbol: str) -> dict:
        await self.broadcast_status("CLOSING", f"{'[SIM] ' if self.simulation_mode else ''}Closing trade #{ticket}...")

        payload = {
            "action":    "CLOSE",
            "ticket":    ticket,
            "symbol":    symbol,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._send_to_mt5(payload)

    async def _send_to_mt5(self, payload: dict) -> dict:
        if self.simulation_mode:
            return self._simulate_response(payload)

        try:
            body = json.dumps(payload)
            signature = self._sign_payload(body)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.mt5_url,
                    content=body,
                    headers={
                        "Content-Type":      "application/json",
                        "X-TW-Signature":    signature,
                        "X-TW-Agent":        "ConnectorCC",
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.ConnectError:
            logger.warning("MT5 webhook not reachable — falling back to simulation")
            return self._simulate_response(payload)
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _simulate_response(payload: dict) -> dict:
        import random
        action = payload.get("action", "")
        ticket = f"SIM-{random.randint(10000, 99999)}"

        base = {"success": True, "simulated": True, "timestamp": datetime.utcnow().isoformat()}

        if action == "OPEN":
            return {**base, "ticket": ticket, "executed_price": payload.get("entry_price"),
                    "message": f"[SIMULATION] Order {ticket} placed successfully"}
        elif action == "MODIFY_SL":
            return {**base, "ticket": payload.get("ticket"),
                    "message": f"[SIMULATION] SL modified to {payload.get('new_sl')}"}
        elif action == "CLOSE_PARTIAL":
            return {**base, "ticket": payload.get("ticket"),
                    "message": f"[SIMULATION] Closed {payload.get('percent')}%"}
        elif action == "CLOSE":
            return {**base, "ticket": payload.get("ticket"),
                    "message": f"[SIMULATION] Trade closed",
                    "close_price": payload.get("entry_price"),
                    "pnl_usd": random.uniform(-50, 150)}
        return {**base, "message": "[SIMULATION] Action executed"}
