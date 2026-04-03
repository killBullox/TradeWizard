"""
ICT Expert Advisor (ICTEA)
Analyzes forex pairs using Inner Circle Trader methodology and proposes strategies.
"""

import json
from typing import Any
from .base_agent import BaseAgent


SYSTEM_PROMPT = """You are the ICT Expert Advisor (ICTEA) — an elite forex analyst with deep mastery of
Inner Circle Trader (ICT) methodology. You think and speak exclusively through the lens of ICT concepts.

## Your Core ICT Knowledge Base

### Market Structure
- Break of Structure (BOS): confirms trend continuation
- Change of Character (CHoCH): signals potential reversal
- Higher Highs/Higher Lows (bullish), Lower Highs/Lower Lows (bearish)

### Liquidity Concepts
- Buy-Side Liquidity (BSL): resting above swing highs (stop hunts)
- Sell-Side Liquidity (SSL): resting below swing lows
- Equal Highs/Lows: strong liquidity pools
- Liquidity Sweep / Stop Hunt: price takes liquidity before reversing

### Price Delivery & PD Arrays
- Fair Value Gap (FVG / Imbalance): 3-candle gap where price trades inefficiently
- Order Block (OB): last opposing candle before an impulsive move
- Breaker Block: failed Order Block that switches polarity
- Mitigation Block: area of unfinished business
- Optimal Trade Entry (OTE): Fibonacci retracement 61.8%–79% of a swing

### Time & Sessions
- New York AM session (09:30–11:00 EST): highest probability setups
- London Open (02:00–05:00 EST): liquidity grabs
- Killzones: specific high-probability time windows
- Midnight Open, NY Open, London Open as reference points

### Higher Timeframe Bias
- Always establish HTF bias first (D1 / H4)
- LTF (H1 / M15) entries must align with HTF direction
- Only trade with the institutional flow

### CRITICAL: Stop Loss & Timeframe Constraints
- System enforces a MINIMUM SL of min_sl_pips (from config, default 30 pips).
- This means you MUST propose setups on H1 or higher timeframes — NOT M1/M5 scalping.
- Entry zones must be wide enough that SL at the structural invalidation point is ≥ 30 pips from entry.
- If the nearest invalidation is only 10-15 pips away, DO NOT propose the setup — it will be rejected.
- Think in terms of swing structure: SL goes below/above the SWING LOW/HIGH or ORDER BLOCK, not just a few pips from entry.
- Ideal SL range: 30-60 pips for majors, 40-80 pips for XAUUSD.
- If ATR is low and no setup gives ≥ 30 pip SL, respond with NO_TRADE bias.

### ICT Patterns
- Silver Bullet (specific time-based FVG strategy)
- Power of 3 (Accumulation → Manipulation → Distribution)
- London Judas Swing
- SMT Divergence (Smart Money Technique)
- NWOG / NDOG (New Week / Day Opening Gaps)

## Your Output Format
Always respond with a JSON object containing:
{
  "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": 0-100,
  "htf_analysis": "D1/H4 analysis",
  "ltf_analysis": "H1/M15 analysis",
  "key_levels": [{"level": float, "type": "FVG|OB|Liquidity|PDH|PDL", "direction": "bull|bear"}],
  "strategies": [
    {
      "name": "strategy name",
      "setup": "FVG|OrderBlock|LiquiditySweep|OTE|SilverBullet",
      "direction": "BUY|SELL",
      "entry_zone_high": float,
      "entry_zone_low": float,
      "rationale": "detailed ICT rationale",
      "probability": 0-100,
      "session": "London|NewYork|Asian",
      "timeframe_entry": "H1|M15|M5"
    }
  ],
  "invalidation": "what would invalidate this analysis",
  "notes": "additional ICT observations"
}
"""


class ICTAdvisorAgent(BaseAgent):
    name = "ICTEA"
    emoji = "🎯"
    color = "#4F46E5"

    async def analyze(
        self,
        symbol: str,
        market_data: dict,
        system_config: dict,
        memory_context: str = "",
    ) -> dict:
        # Economy mode (default): Haiku — fast, cheap, no thinking tokens
        # Quality mode: Sonnet — deeper reasoning for live trading
        mode = system_config.get("model_mode", "economy")
        self.model = (
            "claude-sonnet-4-6" if mode == "quality"
            else "claude-haiku-4-5-20251001"
        )
        await self.broadcast_status("ANALYZING", f"Analyzing {symbol} with ICT methodology [{mode}]...")

        h4 = market_data.get("H4", {})
        h1 = market_data.get("H1", {})
        ind = h1.get("indicators", h4.get("indicators", {}))

        user_msg = f"""
## Market Analysis Request: {symbol}

### H4 Timeframe Indicators
- Current Price: {ind.get('current_price')}
- Trend (EMA20 vs EMA50): {ind.get('trend')}
- ATR: {ind.get('atr')} ({ind.get('atr_pips')} pips)
- Previous Day High: {ind.get('pdh')}
- Previous Day Low: {ind.get('pdl')}
- Previous Day Close: {ind.get('pdc')}
- EMA 20: {ind.get('ema20')}
- EMA 50: {ind.get('ema50')}

### Recent Swing Points (H1)
- Swing Highs: {json.dumps(ind.get('swing_highs', [])[:3])}
- Swing Lows:  {json.dumps(ind.get('swing_lows', [])[:3])}

### Detected Structures
- Fair Value Gaps: {json.dumps(ind.get('fvgs', []))}
- Order Blocks:    {json.dumps(ind.get('order_blocks', []))}

### Active ICT Strategies to Consider
{', '.join(system_config.get('ict_strategies', ['FVG','OrderBlock','Liquidity']))}

### H4 Last 10 Candles (OHLC)
{self._format_candles(h4.get('candles', [])[-10:])}

### H1 Last 20 Candles (OHLC)
{self._format_candles(h1.get('candles', [])[-20:])}

Perform a complete ICT analysis for {symbol}.
Identify the current HTF bias, key PD arrays, liquidity pools,
and propose 1-3 high-probability trade setups.
"""
        if memory_context:
            user_msg = memory_context + "\n" + user_msg
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=4096)

        await self.broadcast_status(
            "ANALYSIS_COMPLETE",
            f"{symbol}: {result.get('bias','?')} bias, {len(result.get('strategies',[]))} setup(s) found",
            {"symbol": symbol, "strategies": result.get("strategies", [])},
        )
        return result

    @staticmethod
    def _format_candles(candles: list) -> str:
        if not candles:
            return "No data"
        lines = ["Time | Open | High | Low | Close"]
        for c in candles:
            t = c.get("time", "")[:16]
            lines.append(f"{t} | {c.get('open')} | {c.get('high')} | {c.get('low')} | {c.get('close')}")
        return "\n".join(lines)
