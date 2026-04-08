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
        self.mt5_secret = os.environ.get("MT5_WEBHOOK_SECRET", "tradewizard_secret")
        self._mt5_bridge_url = None  # loaded from DB on first use
        self.simulation_mode = False  # will be set based on bridge availability

    async def _get_mt5_url(self) -> str:
        """Get MT5 bridge URL from DB config (cached after first call)."""
        if self._mt5_bridge_url:
            return self._mt5_bridge_url
        try:
            from models.database import async_session_factory, get_config
            async with async_session_factory() as s:
                url = await get_config("mt5_bridge_url", s)
                if url:
                    self._mt5_bridge_url = url.rstrip("/") + "/webhook"
                    self.simulation_mode = False
                    return self._mt5_bridge_url
        except Exception:
            pass
        # Fallback to env var or default bridge
        env_url = os.environ.get("MT5_WEBHOOK_URL") or os.environ.get("MT5_BRIDGE_URL")
        if env_url:
            self._mt5_bridge_url = env_url.rstrip("/") + ("/webhook" if "/webhook" not in env_url else "")
            self.simulation_mode = False
        else:
            self._mt5_bridge_url = "http://localhost:5002/webhook"
            self.simulation_mode = False  # try bridge anyway, simulate only on connect failure
        return self._mt5_bridge_url

    def _sign_payload(self, payload: str) -> str:
        return hmac.new(
            self.mt5_secret.encode(),
            payload.encode(),
            "sha256",
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
        mt5_url = await self._get_mt5_url()

        try:
            body = json.dumps(payload)
            signature = self._sign_payload(body)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    mt5_url,
                    content=body,
                    headers={
                        "Content-Type":      "application/json",
                        "X-TW-Signature":    signature,
                        "X-TW-Agent":        "ConnectorCC",
                    },
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("simulated"):
                        logger.warning("MT5 bridge returned simulated response — MT5 may not be available")
                    return result
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.ConnectError:
            logger.error("MT5 bridge not reachable at %s — falling back to simulation", mt5_url)
            return self._simulate_response(payload)
        except Exception as e:
            logger.error("MT5 bridge error: %s", e)
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
