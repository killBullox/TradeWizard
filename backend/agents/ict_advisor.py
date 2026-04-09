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

### CRITICAL: Day Trading Constraints
- This is a DAY TRADING system — trades must be designed to reach TP1 within 2-6 hours.
- The system_config will contain min_sl_pips — the minimum SL distance enforced by the system.
- You MUST only propose setups where the structural invalidation point is at least min_sl_pips away from entry.
- TP1 MUST be reachable within the current session: max TP1 distance = 0.5 × ATR daily.
- Do NOT propose swing targets that take days to reach.
- Focus on INTRADAY liquidity: Previous Day High/Low, session highs/lows, intraday FVGs.
- If no intraday setup meets constraints, respond with NO_TRADE bias.

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

### Trading Constraints (from system config)
- Minimum SL: {system_config.get('min_sl_pips', '20')} pips — setups with tighter invalidation will be REJECTED
- Required RR: {system_config.get('rr_ratio', '2.0')} (net, after ~1.5 pips friction)
- Max open trades: {system_config.get('max_open_trades', '3')}
- ATR H1: {ind.get('atr_pips', 'N/A')} pips — use this to calibrate TP distance
- **Max TP1 distance: {round(float(ind.get('atr_pips', 15)) * 2, 0)} pips** (≈ 2x ATR H1, must be reachable in 2-6 hours on H1 timeframe)
- Max trade duration: {system_config.get('max_trade_duration_hours', '6')} hours

Perform a complete ICT DAY TRADING analysis for {symbol}.
Identify INTRADAY targets: PDH, PDL, session highs/lows, intraday FVG fills.
Propose 1-3 setups where TP1 is reachable WITHIN THE CURRENT SESSION.
If no intraday setup meets constraints, respond with bias=NEUTRAL and empty strategies.
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
