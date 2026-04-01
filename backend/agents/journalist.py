"""
Journalist (JR)
Handles journaling, performance monitoring, and post-trade review meetings.
Synthesizes insights for system self-improvement.
"""

import json
from datetime import datetime
from .base_agent import BaseAgent, MODEL_STANDARD


SYSTEM_PROMPT = """You are the Journalist (JR) — the institutional memory and performance analyst
of the TradeWizard multi-agent system.

## CRITICAL: Continuous Learning Mission
Your PRIMARY goal is to make the system learn from every single trade.
After EVERY meeting you MUST produce `setup_memory_updates` — specific, actionable
updates to the strategy memory for each setup reviewed.
This is how the system improves: agents read this memory before every trade.

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
  "meeting_type": "POST_TRADE|KILLZONE_REVIEW|WEEKLY_REVIEW",
  "participants": ["ICTEA", "RM", "TR", "AT"],
  "discussion_points": ["..."],
  "conclusions": ["..."],
  "action_items": [{"agent": "...", "action": "...", "priority": "HIGH|MEDIUM|LOW"}],
  "system_improvements": [
    {
      "category": "ICT|RISK|MANAGEMENT|STRATEGY",
      "improvement": "description",
      "config_change": {"key": "...", "new_value": "..."}
    }
  ],
  "setup_memory_updates": [
    {
      "setup_type": "FVG",
      "symbol": "EURUSD",
      "failure_patterns": ["specific reason this setup failed today"],
      "success_patterns": ["specific reason this setup worked"],
      "lessons": ["actionable lesson for next time"],
      "strategy_notes": "Overall guidance for this setup going forward"
    }
  ]
}
"""


class JournalistAgent(BaseAgent):
    name = "JR"
    emoji = "📝"
    color = "#92400E"
    model = MODEL_STANDARD

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
        current_memory: str = "",
        post_trade_context: str = "",
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
        for t in trades[-15:]:
            trades_summary.append({
                "symbol":    t.get("symbol"),
                "direction": t.get("direction"),
                "setup":     t.get("ict_setup"),
                "result":    t.get("result"),
                "pnl_usd":   t.get("pnl_usd"),
                "pnl_pips":  t.get("pnl_pips"),
                "entry":     t.get("entry_price"),
                "exit":      t.get("close_price"),
                "sl":        t.get("stop_loss"),
                "tp1":       t.get("take_profit_1"),
                "tp2":       t.get("take_profit_2"),
                "tp3":       t.get("take_profit_3"),
                "open_time": str(t.get("open_time", ""))[:16],
                "close_time": str(t.get("close_time", ""))[:16],
            })

        memory_section = f"\n### Current Strategy Memory\n{current_memory}\n" if current_memory else ""
        post_section   = f"\n### What Happened After Each Trade Closed\n{post_trade_context}\n" if post_trade_context else ""

        user_msg = f"""
## {meeting_type} Meeting
{memory_section}
### Performance Statistics
{json.dumps(performance_stats, indent=2)}

### Trades Reviewed (with full parameters)
{json.dumps(trades_summary, indent=2)}
{post_section}
### Current System Configuration
{json.dumps(system_config, indent=2)}

## Meeting Agenda
You are facilitating a rigorous review. The goal is CONTINUOUS IMPROVEMENT.
Principle: "O vinco o imparo — e anche quando vinco analizzo perché non ho vinto di più."

Analyse every single trade:
1. **Setup quality**: Was the ICT setup correctly identified? Were there confluence factors missed?
2. **Entry timing**: Was the entry optimal, or did we enter too early/late?
3. **TP management**: Did we leave money on the table? Was TP1 too close?
4. **SL placement**: Were stops too tight (premature), or too wide (excessive loss)?
5. **Setup failures**: For each losing setup type, WHY did it fail? Market structure, news, session?
6. **What happened after close**: If we closed at TP1 and price continued to TP3, note that.
7. **Pattern recognition**: Are there recurring failure patterns we must avoid?

MANDATORY: Produce `setup_memory_updates` for EVERY setup type reviewed.
These updates are the only way the system learns — without them, the same mistakes repeat.
Be specific and actionable, not generic.
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
