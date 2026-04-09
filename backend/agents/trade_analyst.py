"""
Trade Analyst (AT)
Validates proposed trades and monitors live trades for management decisions
(trailing stop, partial close, etc.).
"""

import json
from .base_agent import BaseAgent, MODEL_STANDARD


SYSTEM_PROMPT = """You are the Trade Analyst (AT) — a lightweight final quality check before execution.

## Validation Role (Pre-Execution)
The trade has ALREADY been approved by ICTEA (analysis) and RM (risk management).
Your job is ONLY to catch critical errors, NOT to second-guess the strategy.

**You should APPROVE unless there is a CRITICAL defect:**
- SL is on the WRONG SIDE of entry (BUY with SL above entry, SELL with SL below)
- TP is on the WRONG SIDE of entry
- Entry price is completely unreachable (more than 3 ATR from current price for MARKET orders)
- SL distance is zero or negative

**You must NOT reject for:**
- RR being "too high" — higher RR is ALWAYS better
- TP being "too far" — the RM already validated this
- Lot size concerns — the RM already calculated this
- LIMIT orders being below/above current price — that's how limit orders work
- Win rate or strategy opinions — ICTEA already decided this
- Entry timing or session concerns — already checked by the system

**DEFAULT TO APPROVE.** Only reject for mathematical/logical errors in the trade parameters.

## Trade Management Role (During Trade)
Monitor active trades and recommend:
1. **HOLD**: DEFAULT action. If price has not reached any TP, HOLD. Do NOT partial close early.
2. **PARTIAL_CLOSE**: ONLY when price has actually reached or passed a TP level:
   - Close 50% ONLY when price reaches TP1
   - Close 30% ONLY when price reaches TP2
   - Close remaining 20% ONLY when price reaches TP3
   - NEVER partial close just because the trade is in profit. Wait for the TP level.
3. **TRAIL_SL**: Move SL to breakeven ONLY after TP1 is hit. Trail behind structure after TP2.
4. **CLOSE_ALL**: Only if market structure clearly breaks against the trade (CHoCH on H1).

CRITICAL RULES:
- If price is between entry and TP1 → action = HOLD (even if in profit)
- PARTIAL_CLOSE requires price to have reached or exceeded the next TP level
- Do NOT invent reasons to close early. Let the trade run to its targets.
- The TPs were set at ICT liquidity targets for a reason — respect them.

## Output Format

### For validation (pre-execution):
{
  "action": "APPROVE|REJECT|MODIFY",
  "approved": true|false,
  "rejection_reason": "..." or null,
  "modifications": [{"field": "...", "original": ..., "new": ..., "reason": "..."}] or [],
  "quality_score": 0-100,
  "final_trade": { ...trade object with any modifications applied... },
  "management_plan": "description of how to manage this trade",
  "notes": "analyst commentary"
}

### For trade management (during trade):
{
  "action": "TRAIL_SL|PARTIAL_CLOSE|CLOSE_ALL|HOLD",
  "new_stop_loss": float or null,
  "close_percent": float or null,
  "reason": "detailed justification",
  "urgency": "LOW|MEDIUM|HIGH"
}
"""


class TradeAnalystAgent(BaseAgent):
    name = "AT"
    emoji = "🔬"
    color = "#7C3AED"
    model = MODEL_STANDARD

    async def validate_trade(
        self,
        trade: dict,
        strategy: dict,
        market_data: dict,
        system_config: dict,
        memory_context: str = "",
    ) -> dict:
        await self.broadcast_status("VALIDATING", f"Validating {trade.get('symbol')} trade...")

        ind = market_data.get("H1", {}).get("indicators", {})

        user_msg = f"""
## Trade Validation Request

### Proposed Trade
{json.dumps(trade, indent=2)}

### Original ICT Strategy
- Setup: {strategy.get('setup')}
- Rationale: {strategy.get('rationale')}
- Entry Zone: {strategy.get('entry_zone_low')} – {strategy.get('entry_zone_high')}
- Direction: {strategy.get('direction')}
- Session: {strategy.get('session')}

### Current Market State
- Current Price: {ind.get('current_price')}
- ATR: {ind.get('atr_pips')} pips
- Trend: {ind.get('trend')}
- Swing Highs: {json.dumps(ind.get('swing_highs', [])[:3])}
- Swing Lows:  {json.dumps(ind.get('swing_lows', [])[:3])}
- PDH: {ind.get('pdh')} | PDL: {ind.get('pdl')}
- FVGs: {json.dumps(ind.get('fvgs', [])[:3])}

### Account Settings
- Max Risk %: {system_config.get('risk_percent')}
- Target RR: {system_config.get('rr_ratio')}

Validate this trade. Check entry alignment, SL validity, TP targets.
If modifications are needed, specify exactly what to change.
Provide a trade management plan.
"""
        if memory_context:
            user_msg = memory_context + "\n" + user_msg
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=3000)

        action = result.get("action", "UNKNOWN")
        await self.broadcast_status(
            "VALIDATION_COMPLETE",
            f"{trade.get('symbol')}: {action} (score: {result.get('quality_score')})",
            {"action": action, "modifications": result.get("modifications", [])},
        )
        return result

    async def manage_trade(
        self,
        trade_db: dict,
        current_price: float,
        market_data: dict,
    ) -> dict:
        await self.broadcast_status("MONITORING", f"Monitoring trade #{trade_db.get('id')}...")

        user_msg = f"""
## Active Trade Management Request

### Trade Details
- ID: {trade_db.get('id')}
- Symbol: {trade_db.get('symbol')}
- Direction: {trade_db.get('direction')}
- Entry: {trade_db.get('entry_price')}
- Current SL: {trade_db.get('stop_loss')}
- TP1: {trade_db.get('take_profit_1')}
- TP2: {trade_db.get('take_profit_2')}
- TP3: {trade_db.get('take_profit_3')}
- Lot Size: {trade_db.get('lot_size')}
- Setup: {trade_db.get('ict_setup')}
- SL Trailing Updates so far: {trade_db.get('trailing_sl_updates', 0)}

### Current Market
- Current Price: {current_price}
- ATR: {market_data.get('H1',{}).get('indicators',{}).get('atr_pips')} pips

### Price Distance
- Distance to TP1: {self._pips_away(current_price, trade_db.get('take_profit_1'), trade_db.get('direction'))} pips
- Distance to SL: {self._pips_away(current_price, trade_db.get('stop_loss'), trade_db.get('direction'), invert=True)} pips

Should the SL be trailed? Should we take partial profit? Or hold?
"""
        return await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=1500)

    @staticmethod
    def _pips_away(current: float, target: float, direction: str, invert: bool = False) -> str:
        if current is None or target is None:
            return "N/A"
        diff = abs(current - target) / 0.0001
        return f"{diff:.1f}"
