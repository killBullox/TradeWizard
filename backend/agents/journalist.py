"""
Journalist (JR)
Handles journaling, performance monitoring, and post-trade review meetings.
Synthesizes insights for system self-improvement.
"""

import json
from datetime import datetime
from .base_agent import BaseAgent


SYSTEM_PROMPT = """You are the Journalist (JR) — the institutional memory and performance analyst
of the TradeWizard multi-agent system.

## Your Responsibilities

### 1. Real-Time Journaling
Document every action with context:
- Trade opens/closes with full context
- Agent decisions and rationale
- Market conditions at key moments
- Emotional neutrality — pure facts and analysis

### 2. Performance Monitoring
Track and analyze:
- Win rate per setup type (FVG, OB, Liquidity Sweep, etc.)
- Average RR achieved vs planned
- Session performance (London/NY/Asian)
- Drawdown analysis
- Best/worst performing pairs

### 3. Post-Trade Review Meetings
Facilitate debrief sessions between agents:
- What went right / wrong with the setup?
- Was the ICT analysis accurate?
- Was risk properly managed?
- What can be improved?
- Extract actionable lessons

### 4. System Self-Improvement
After each review, propose concrete improvements to:
- ICT strategy parameters
- Risk management rules
- Trade management procedures
- Which setups to favor/avoid
- Optimal session timing

## Writing Style
- Precise, data-driven
- Reference specific price levels and times
- Connect outcomes to decisions
- Always extract actionable insights

## Output Formats

### Journal Entry:
{
  "entry_type": "TRADE_OPEN|TRADE_CLOSE|TRADE_UPDATE|MEETING_SUMMARY|PERFORMANCE_REPORT",
  "title": "brief title",
  "content": "detailed narrative",
  "key_metrics": {"win_rate": ..., "avg_rr": ..., etc.},
  "insights": ["insight 1", "insight 2"],
  "timestamp": "ISO datetime"
}

### Meeting Summary:
{
  "meeting_type": "POST_TRADE|WEEKLY_REVIEW",
  "participants": ["ICTEA", "RM", "TR", "AT"],
  "discussion_points": ["..."],
  "conclusions": ["..."],
  "action_items": [{"agent": "...", "action": "...", "priority": "HIGH|MEDIUM|LOW"}],
  "system_improvements": [
    {
      "category": "ICT|RISK|MANAGEMENT|STRATEGY",
      "improvement": "description",
      "config_change": {"key": "...", "new_value": "..."}  // optional
    }
  ]
}
"""


class JournalistAgent(BaseAgent):
    name = "JR"
    emoji = "📝"
    color = "#92400E"

    async def journal_trade_open(self, trade: dict, analysis: dict) -> dict:
        await self.broadcast_status("JOURNALING", f"Documenting trade open: {trade.get('symbol')}...")

        user_msg = f"""
Write a journal entry for this trade opening.

### Trade Opened
{json.dumps(trade, indent=2)}

### Analysis Chain
- ICTEA Bias: {analysis.get('ictea', {}).get('bias')}
- Setup: {analysis.get('strategy', {}).get('setup')}
- RM Risk Score: {analysis.get('risk', {}).get('risk_score')}
- AT Quality Score: {analysis.get('validation', {}).get('quality_score')}
- Management Plan: {analysis.get('validation', {}).get('management_plan')}

Document the trade context, the ICT rationale, the risk parameters,
and the expected trade management approach.
"""
        return await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=2000)

    async def journal_trade_close(
        self,
        trade: dict,
        close_price: float,
        pnl_usd: float,
        reason: str,
    ) -> dict:
        await self.broadcast_status("JOURNALING", f"Documenting trade close: {trade.get('symbol')} | P&L: ${pnl_usd:.2f}...")

        result_str = "WIN" if pnl_usd > 0 else ("LOSS" if pnl_usd < 0 else "BREAKEVEN")
        rr_achieved = 0
        if trade.get("entry_price") and trade.get("stop_loss"):
            entry = trade["entry_price"]
            sl    = trade["stop_loss"]
            risk  = abs(entry - sl)
            reward = abs(close_price - entry)
            rr_achieved = round(reward / risk, 2) if risk > 0 else 0

        user_msg = f"""
Write a comprehensive post-trade journal entry.

### Trade Result: {result_str}
- Symbol: {trade.get('symbol')}
- Direction: {trade.get('direction')}
- Setup: {trade.get('ict_setup')}
- Entry: {trade.get('entry_price')}
- Exit: {close_price}
- SL was: {trade.get('stop_loss')}
- TP1 was: {trade.get('take_profit_1')}
- Lot Size: {trade.get('lot_size')}
- P&L: ${pnl_usd:.2f}
- RR Achieved: {rr_achieved}
- Close Reason: {reason}
- SL Trailing Updates: {trade.get('trailing_sl_updates', 0)}

Write a detailed post-trade analysis covering:
1. Was the ICT setup valid?
2. Was the entry optimal?
3. Was the trade managed correctly?
4. Key lessons learned
"""
        return await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=2500)

    async def conduct_meeting(
        self,
        meeting_type: str,
        trades: list,
        performance_stats: dict,
        system_config: dict,
    ) -> dict:
        await self.broadcast_status(
            "MEETING",
            f"Conducting {meeting_type} meeting with ICTEA, RM, TR, AT..."
        )

        await self.broadcast({
            "type": "meeting_started",
            "meeting_type": meeting_type,
            "participants": ["ICTEA", "RM", "TR", "AT", "JR"],
            "timestamp": datetime.utcnow().isoformat(),
        })

        trades_summary = []
        for t in trades[-10:]:  # Last 10 trades
            trades_summary.append({
                "symbol": t.get("symbol"),
                "direction": t.get("direction"),
                "setup": t.get("ict_setup"),
                "result": t.get("result"),
                "pnl": t.get("pnl_usd"),
                "rr": t.get("pnl_pips"),
            })

        user_msg = f"""
## {meeting_type} Meeting

You are facilitating a review meeting between ICTEA, RM, TR, and AT.

### Performance Statistics
{json.dumps(performance_stats, indent=2)}

### Recent Trades Reviewed
{json.dumps(trades_summary, indent=2)}

### Current System Configuration
{json.dumps(system_config, indent=2)}

Conduct the meeting. Analyze what's working and what isn't.
Propose specific, actionable improvements to the system.
Focus on:
1. ICT setup win rates — which setups are performing well?
2. Risk management — are position sizes correct?
3. Trade management — are we taking profits too early/late?
4. Session timing — which sessions perform best?
5. Configuration changes to improve system performance

Be specific about any config changes (e.g., "increase risk_percent to 1.2%",
"add CHOCH to ict_strategies", "reduce max_open_trades to 2").
"""
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=4096)

        await self.broadcast({
            "type": "meeting_completed",
            "meeting_type": meeting_type,
            "improvements": result.get("system_improvements", []),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return result

    async def generate_performance_report(self, stats: dict) -> dict:
        await self.broadcast_status("REPORTING", "Generating performance report...")

        user_msg = f"""
Generate a comprehensive performance report for the TradeWizard system.

### Statistics
{json.dumps(stats, indent=2)}

Provide:
1. Overall performance summary
2. Best/worst performing setups
3. Session analysis
4. Risk management effectiveness
5. Trend identification
6. Recommendations for the next trading period
"""
        return await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=3000)
