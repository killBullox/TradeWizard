"""
BaseAgent — shared interface for all TradeWizard agents.
Each agent wraps a Claude call with its own system prompt.
"""

import json
import os
import logging
from datetime import datetime
from typing import Any, Optional, Callable, Awaitable
import anthropic

logger = logging.getLogger(__name__)

# Model assignments by role — balance quality vs cost
MODEL_ANALYST  = "claude-sonnet-4-6"         # ICT Advisor: strong reasoning, 5× cheaper than Opus
MODEL_STANDARD = "claude-haiku-4-5-20251001"  # RM, Trader, AT, Journalist: fast & cheap
MODEL = MODEL_ANALYST  # default fallback


class BaseAgent:
    name: str = "BaseAgent"
    emoji: str = "🤖"
    color: str = "#666666"
    model: str = MODEL_ANALYST   # override per-agent to MODEL_STANDARD to save cost

    def __init__(self, broadcast_fn: Optional[Callable[[dict], Awaitable[None]]] = None):
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.broadcast = broadcast_fn or self._noop_broadcast
        self._conversation_history: list[dict] = []

    # ------------------------------------------------------------------
    # Core: call Claude with adaptive thinking
    # ------------------------------------------------------------------
    async def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        use_thinking: bool = True,
    ) -> str:
        await self.broadcast({
            "type": "agent_thinking",
            "agent": self.name,
            "emoji": self.emoji,
            "color": self.color,
            "message": f"Analyzing...",
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Haiku doesn't support extended thinking — disable it automatically
        supports_thinking = "opus" in self.model or "sonnet" in self.model
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        if use_thinking and supports_thinking:
            kwargs["thinking"] = {"type": "adaptive"}

        response = await self.client.messages.create(**kwargs)

        text_blocks = [b.text for b in response.content if b.type == "text"]
        result = "\n".join(text_blocks)

        await self.broadcast({
            "type": "agent_response",
            "agent": self.name,
            "emoji": self.emoji,
            "color": self.color,
            "message": result[:500] + ("..." if len(result) > 500 else ""),
            "full_response": result,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return result

    async def _call_claude_structured(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> dict:
        """Call Claude and parse the JSON response."""
        full_prompt = (
            f"{user_message}\n\n"
            "IMPORTANT: Respond ONLY with a valid JSON object. "
            "No markdown fences, no explanations outside the JSON."
        )
        raw = await self._call_claude(system_prompt, full_prompt, max_tokens, use_thinking=True)
        return self._extract_json(raw)

    def _extract_json(self, text: str) -> dict:
        """Try to extract a JSON object from possibly wrapped text."""
        text = text.strip()
        # Strip markdown code fences if present
        for marker in ["```json", "```JSON", "```"]:
            if text.startswith(marker):
                text = text[len(marker):]
                end = text.rfind("```")
                if end != -1:
                    text = text[:end]
                break
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Attempt to find first { ... } block
            start = text.find("{")
            end   = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        logger.error(f"[{self.name}] Failed to parse JSON: {text[:200]}")
        return {"error": "Failed to parse response", "raw": text}

    async def broadcast_status(self, action: str, message: str, data: dict | None = None):
        await self.broadcast({
            "type": "agent_status",
            "agent": self.name,
            "emoji": self.emoji,
            "color": self.color,
            "action": action,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    @staticmethod
    async def _noop_broadcast(msg: dict):
        pass
