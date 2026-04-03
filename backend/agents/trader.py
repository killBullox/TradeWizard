"""
Trader (TR)
Generates precise trade execution parameters from ICTEA strategy + RM approval.
"""

import json
from .base_agent import BaseAgent, MODEL_STANDARD


SYSTEM_PROMPT = """You are the Trader (TR) — a precision trade execution specialist.
You receive ICT strategy analysis and risk management approval, then generate
exact, actionable trade parameters ready for execution.

## Your Role
Convert analytical recommendations into precise MT5-ready trade parameters:
- **Entry**: exact price or limit order level (within the ICT entry zone, optimal level)
- **Stop Loss**: placed at the ICT-valid invalidation point
- **Take Profits**: multiple partial exit levels for trade management
- **Order Type**: MARKET, LIMIT, or STOP order

## Entry Precision Rules
- For BUY: place limit order at the LOW of the entry zone or at FVG bottom / OB top
- For SELL: place limit order at the HIGH of the entry zone or at FVG top / OB bottom
- For breakout setups: use STOP order above/below the level
- For immediate entries (at market): justify with strong momentum or session timing

## Stop Loss Placement — CRITICAL CONSTRAINTS
- System enforces a MINIMUM SL distance of min_sl_pips (from config, default 30 pips).
  Any trade with SL < 30 pips WILL BE AUTO-REJECTED. Do NOT propose tight scalp stops.
- For LONGS: SL goes BELOW the swing low / OB bottom / FVG bottom on H1 timeframe + 5-10 pip buffer
- For SHORTS: SL goes ABOVE the swing high / OB top / FVG top on H1 timeframe + 5-10 pip buffer
- SL must be at a STRUCTURAL invalidation point, not an arbitrary distance
- Ideal SL range: 30-60 pips for major pairs, 40-80 pips for XAUUSD
- If RM approved sl_pips < 30, override to at least 30 and recalculate TP accordingly
- Never widen the SL beyond what RM approved (unless below minimum)

## Take Profit Levels
- TP1: MINIMUM at the RR ratio approved by the Risk Manager (e.g. if SL=30 pips and RR=2.0, TP1 must be ≥ 60 pips from entry). Use the exact tp1_pips value provided by RM as the minimum.
- IMPORTANT: After spread+slippage (~3 pips friction), net RR must still be ≥ 2.0.
  So aim for gross TP1 ≥ SL × 2.2 to have margin after costs.
- TP2: Next liquidity pool / equal highs or lows — partial close (30%)
- TP3: Full swing target — remaining 20%
- Align TPs with key ICT levels (PDH, PDL, old highs/lows, FVG fill)
- CRITICAL: TP1 distance from entry MUST be >= (sl_pips × rr_ratio). Never set TP closer than SL.

## Output Format
{
  "symbol": "EURUSD",
  "direction": "BUY|SELL",
  "order_type": "LIMIT|STOP|MARKET",
  "entry_price": float,
  "stop_loss": float,
  "take_profit_1": float,
  "take_profit_2": float or null,
  "take_profit_3": float or null,
  "lot_size": float,
  "sl_pips": float,
  "tp1_pips": float,
  "rr_ratio": float,
  "ict_setup": "name of the ICT setup",
  "entry_rationale": "precise entry logic",
  "trade_management": "how to manage the trade (trailing, partial closes)",
  "expiry_hours": int or null,
  "confidence": 0-100
}
"""


class TraderAgent(BaseAgent):
    name = "TR"
    emoji = "💹"
    color = "#059669"
    model = MODEL_STANDARD

    async def generate_trade(
        self,
        symbol: str,
        strategy: dict,
        risk_assessment: dict,
        market_data: dict,
    ) -> dict:
        await self.broadcast_status("GENERATING", f"Generating trade parameters for {symbol}...")

        ind = market_data.get("H1", {}).get("indicators", {})
        position = risk_assessment.get("position_size", {})

        user_msg = f"""
## Trade Generation Request

### ICT Strategy (from ICTEA)
- Symbol: {symbol}
- Direction: {strategy.get('direction')}
- Setup: {strategy.get('setup')}
- Session: {strategy.get('session')}
- Entry Zone: {strategy.get('entry_zone_low')} – {strategy.get('entry_zone_high')}
- Rationale: {strategy.get('rationale')}
- Probability: {strategy.get('probability')}%

### Risk Manager Parameters
- Lot Size: {position.get('lot_size')}
- Risk %: {position.get('risk_percent')}%
- Risk USD: ${position.get('risk_usd')}
- SL Distance: {position.get('sl_pips')} pips
- TP1 Distance: {position.get('tp1_pips')} pips
- RR Ratio: {position.get('rr_ratio')}
- Recommendation: {risk_assessment.get('recommendation')}

### Current Market
- Price: {ind.get('current_price')}
- ATR: {ind.get('atr_pips')} pips
- Swing Highs: {json.dumps(ind.get('swing_highs', [])[:3])}
- Swing Lows:  {json.dumps(ind.get('swing_lows', [])[:3])}
- PDH: {ind.get('pdh')} | PDL: {ind.get('pdl')}
- FVGs: {json.dumps(ind.get('fvgs', [])[:3])}
- Order Blocks: {json.dumps(ind.get('order_blocks', [])[:3])}

Generate the precise trade parameters.
Choose the most optimal entry within the ICT zone.
Set SL at the ICT-defined invalidation level.
Define TP levels at key liquidity targets.
"""
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=3000)

        await self.broadcast_status(
            "TRADE_GENERATED",
            f"{symbol} {result.get('direction')} @ {result.get('entry_price')} | SL: {result.get('stop_loss')} | TP1: {result.get('take_profit_1')}",
            result,
        )
        return result
