"""
Risk Manager (RM)
Evaluates risk for each proposed trade strategy.
"""

import json
from .base_agent import BaseAgent


SYSTEM_PROMPT = """You are the Risk Manager (RM) for a professional forex trading operation.
Your role is to protect trading capital by rigorously evaluating every proposed trade.

## Your Risk Framework

### Position Sizing
- Never risk more than the configured max_risk_percent per trade
- Account for current drawdown when sizing positions
- Formula: Lot size = (Account Balance × Risk%) / (SL distance in pips × Pip value)
- Consider spread costs in your calculations

### Statistical Edge
- Evaluate win probability based on historical ICT setup performance:
  * OTE (61.8-79% Fib) + FVG confluence: ~65% win rate
  * Pure Order Block: ~60% win rate
  * Liquidity Sweep + reversal: ~62% win rate
  * Silver Bullet (timed entry): ~67% win rate
  * SMT Divergence: ~63% win rate
- Factor in current market volatility (ATR-based)
- Session timing bonus: +5% probability during killzones
- HTF alignment bonus: +8% when LTF matches HTF bias

### Risk/Reward Assessment
- Minimum RR ratio: 1.5:1 (configurable)
- Prefer setups with RR ≥ 2:1
- Calculate Expected Value: EV = (Win% × Reward) - (Loss% × Risk)
- Positive EV ≥ 0.3 required to approve

### Portfolio-Level Risk
- Check current open trades count vs max_open_trades
- Correlation check: avoid similar direction trades on correlated pairs
  * EURUSD/GBPUSD/AUDUSD are positively correlated
  * USDJPY/USDCHF are positively correlated
  * Gold (XAUUSD) is often inversely correlated with USD

### Red Flags (auto-reject if present)
- RR < 1.2
- Win probability < 45%
- Expected Value < 0
- Max open trades already reached
- High-impact news in next 2 hours (if provided)

## Output Format
Respond with JSON:
{
  "approved": true|false,
  "risk_score": 0-100,
  "rejection_reason": "..." or null,
  "position_size": {
    "lot_size": float,
    "risk_usd": float,
    "risk_percent": float,
    "sl_pips": float,
    "tp1_pips": float,
    "tp2_pips": float or null,
    "rr_ratio": float
  },
  "probability_assessment": {
    "win_probability": float,
    "base_probability": float,
    "adjustments": [{"factor": "...", "delta": float}],
    "expected_value": float
  },
  "risk_factors": [
    {"factor": "...", "severity": "LOW|MEDIUM|HIGH", "description": "..."}
  ],
  "recommendation": "FULL_SIZE|HALF_SIZE|SKIP",
  "notes": "risk manager commentary"
}
"""


class RiskManagerAgent(BaseAgent):
    name = "RM"
    emoji = "⚖️"
    color = "#DC2626"

    async def evaluate(
        self,
        symbol: str,
        strategy: dict,
        market_data: dict,
        system_config: dict,
        open_trades_count: int = 0,
    ) -> dict:
        await self.broadcast_status(
            "EVALUATING",
            f"Evaluating risk for {symbol} {strategy.get('direction')} setup..."
        )

        ind = market_data.get("H1", {}).get("indicators", {})
        current_price = ind.get("current_price", 0)
        atr_pips = ind.get("atr_pips", 15)
        pip_value = ind.get("pip_value", 0.0001)
        account_balance = float(system_config.get("account_balance", 10000))
        max_risk = float(system_config.get("risk_percent", 1.0))
        rr_ratio = float(system_config.get("rr_ratio", 2.0))
        max_trades = int(system_config.get("max_open_trades", 3))

        user_msg = f"""
## Risk Evaluation Request

### Trade Setup
- Symbol: {symbol}
- Direction: {strategy.get('direction')}
- Setup Type: {strategy.get('setup')}
- ICTEA Probability: {strategy.get('probability')}%
- Entry Zone: {strategy.get('entry_zone_low')} – {strategy.get('entry_zone_high')}
- Session: {strategy.get('session')}
- Rationale: {strategy.get('rationale', '')}

### Account Parameters
- Account Balance: ${account_balance:,.2f}
- Max Risk Per Trade: {max_risk}%
- Target RR Ratio: {rr_ratio}
- Max Open Trades: {max_trades}
- Currently Open Trades: {open_trades_count}

### Market Conditions
- Current Price: {current_price}
- ATR (H1): {atr_pips} pips
- Pip Value: {pip_value}
- HTF Trend: {ind.get('trend', 'unknown')}
- PDH: {ind.get('pdh')}
- PDL: {ind.get('pdl')}

### Correlated Pairs Currently Trading: None

Evaluate the risk for this trade.
Calculate exact position size, win probability, expected value, and risk factors.
The SL should be placed below the Order Block / FVG (for longs) or above (for shorts),
approximately {atr_pips * 1.5:.0f} pips from entry (adjust based on setup).
TP1 at {rr_ratio}x risk, TP2 at {rr_ratio * 1.5:.1f}x risk if applicable.
"""
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=3000)

        status = "APPROVED ✅" if result.get("approved") else f"REJECTED ❌: {result.get('rejection_reason','')}"
        await self.broadcast_status(
            "EVALUATION_COMPLETE",
            f"{symbol} {strategy.get('direction')}: {status}",
            {"approved": result.get("approved"), "lot_size": result.get("position_size", {}).get("lot_size")},
        )
        return result
