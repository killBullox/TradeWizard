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

    async def emergency_meeting(
        self,
        topic: str,
        trades: list,
        performance_stats: dict,
        system_config: dict,
    ) -> dict:
        """User-convened emergency meeting. Agents must be critical and challenging, not compliant."""
        await self.broadcast_status("EMERGENCY_MEETING", f"Emergency meeting convened: {topic[:60]}")
        await self.broadcast({
            "type":         "meeting_started",
            "meeting_type": "EMERGENCY",
            "participants": ["ICTEA", "RM", "TR", "AT", "JR"],
            "timestamp":    datetime.utcnow().isoformat(),
        })

        trades_summary = []
        for t in trades[-20:]:
            d = t if isinstance(t, dict) else {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            trades_summary.append({
                "symbol":      d.get("symbol"),
                "direction":   d.get("direction"),
                "setup":       d.get("ict_setup"),
                "result":      d.get("result"),
                "pnl_usd":     d.get("pnl_usd"),
                "entry":       d.get("entry_price"),
                "exit":        d.get("close_price"),
                "sl":          d.get("stop_loss"),
                "tp1":         d.get("take_profit_1"),
                "open_time":   str(d.get("open_time", ""))[:16],
                "close_time":  str(d.get("close_time", ""))[:16],
            })

        emergency_prompt = f"""
## 🚨 EMERGENCY MEETING — Convened by the Head Trader

### Topic Raised by the Head Trader:
{topic}

### Recent Trades
{json.dumps(trades_summary, indent=2)}

### Current System Configuration
{json.dumps(system_config, indent=2)}

### Performance Statistics
{json.dumps(performance_stats, indent=2)}

---

## CRITICAL INSTRUCTION FOR ALL AGENTS:

This meeting was called by the Head Trader because they have serious concerns.
Your role is NOT to reassure or validate — it is to provide HONEST, RIGOROUS analysis.

Rules for this meeting:
1. **Be critical and data-driven.** If the Head Trader's concern is valid, say so clearly and explain WHY with evidence from the trade data.
2. **Challenge assumptions.** If the Head Trader's concern contains a misunderstanding or is partially wrong, push back with reasoning and data — do not just agree.
3. **No sycophancy.** Phrases like "you're absolutely right", "great point", "I agree completely" are forbidden. Engage with the substance.
4. **Quantify everything.** Don't say "SL is too tight" — say "average SL is 22 pips, with typical slippage of 2-3 pips that represents 10-14% friction on each trade."
5. **Disagree openly if warranted.** If the data does NOT support the concern, say so directly.
6. **Propose concrete changes** with specific numbers, not vague directions.

Each agent must respond from their own perspective:
- **ICTEA**: Are the setups technically valid? Are we entering at the right levels?
- **RM**: Is the risk/reward realistic? Are SLs appropriately sized vs ATR and spread costs?
- **TR**: Is execution timing correct? Are we entering at market or limit?
- **AT**: What do the trade durations and PnL distributions tell us?
- **JR**: What is the objective verdict? What must change immediately?
"""
        result = await self._call_claude_structured(SYSTEM_PROMPT, emergency_prompt, max_tokens=5000)
        await self.broadcast({
            "type":         "meeting_completed",
            "meeting_type": "EMERGENCY",
            "improvements": result.get("system_improvements", []),
            "timestamp":    datetime.utcnow().isoformat(),
        })
        return result

    async def emergency_meeting_interactive(
        self,
        topic: str,
        trades: list,
        performance_stats: dict,
        system_config: dict,
        agents: dict,        # {"ICTEA": agent, "RM": agent, "TR": agent, "AT": agent}
        meeting_state: dict, # shared state with user_queue
    ) -> dict:
        """Interactive emergency meeting: each agent responds separately, user can intervene."""
        import asyncio

        user_queue: asyncio.Queue = meeting_state["user_queue"]

        # Build trade summary (same as non-interactive)
        trades_summary = []
        for t in trades[-20:]:
            d = t if isinstance(t, dict) else {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            trades_summary.append({
                "symbol": d.get("symbol"), "direction": d.get("direction"),
                "setup": d.get("ict_setup"), "result": d.get("result"),
                "pnl_usd": d.get("pnl_usd"), "entry": d.get("entry_price"),
                "sl": d.get("stop_loss"), "tp1": d.get("take_profit_1"),
                "open_time": str(d.get("open_time", ""))[:16],
                "close_time": str(d.get("close_time", ""))[:16],
            })

        base_context = (
            f"## EMERGENCY MEETING — Topic: {topic}\n\n"
            f"### Recent Trades\n{json.dumps(trades_summary, indent=2)}\n\n"
            f"### System Config\n{json.dumps(system_config, indent=2)}\n\n"
            f"### Performance\n{json.dumps(performance_stats, indent=2)}\n"
        )

        meeting_rules = (
            "\n## CRITICAL MEETING RULES:\n"
            "1. Be critical and data-driven. If the concern is valid, say so with evidence.\n"
            "2. Challenge assumptions — push back if data doesn't support the concern.\n"
            "3. No sycophancy. No 'you're absolutely right' or 'great point'.\n"
            "4. Quantify everything with numbers from the trade data.\n"
            "5. Disagree openly if warranted.\n"
            "6. Propose concrete changes with specific numbers.\n"
            "7. Respond in 150-250 words MAX. Be concise and direct.\n"
            "8. Respond in the SAME LANGUAGE as the topic (if Italian, respond in Italian).\n"
        )

        agent_roles = {
            "ICTEA": "You are ICTEA (ICT Expert Advisor). Focus on: Are the setups technically valid? Are entry levels correct? Is the ICT methodology being applied properly?",
            "RM":    "You are RM (Risk Manager). Focus on: Is the risk/reward realistic? Are SLs appropriately sized vs ATR and spread costs? Is position sizing correct?",
            "TR":    "You are TR (Trader). Focus on: Is execution timing correct? Market vs limit orders? Are entries within kill zones? Is slippage being managed?",
            "AT":    "You are AT (Trade Analyst). Focus on: What do trade durations and PnL distributions tell us? Are there statistical patterns in wins/losses?",
        }
        agent_order = ["ICTEA", "RM", "TR", "AT"]

        transcript: list[dict] = []
        meeting_state["transcript"] = transcript

        await self.broadcast({
            "type": "meeting_started",
            "meeting_type": "EMERGENCY",
            "interactive": True,
            "participants": ["ICTEA", "RM", "TR", "AT", "JR"],
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
        })

        round_num = 0
        while True:
            round_num += 1
            meeting_state["round"] = round_num

            # --- Each agent speaks ---
            for agent_name in agent_order:
                agent = agents[agent_name]

                await self.broadcast({
                    "type": "meeting_agent_turn",
                    "agent": agent_name,
                    "emoji": agent.emoji,
                    "color": agent.color,
                    "round": round_num,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Build prompt with full transcript context
                transcript_text = ""
                for entry in transcript:
                    speaker = entry.get("speaker", "?")
                    text = entry.get("message", "")
                    transcript_text += f"\n**{speaker}**: {text}\n"

                round_label = f" (Round {round_num})" if round_num > 1 else ""
                prompt = (
                    f"{agent_roles[agent_name]}\n\n"
                    f"{base_context}\n"
                    f"{meeting_rules}\n"
                    f"{'## Discussion so far:' + transcript_text if transcript_text else ''}\n"
                    f"---\nRespond to the Head Trader's concern{round_label}. "
                    f"{'Build on previous discussion, do NOT repeat what others said.' if transcript_text else ''}"
                )

                # Use agent's own _call_claude (broadcasts agent_thinking + agent_response)
                raw = await agent._call_claude(
                    f"You are {agent_name} in an emergency meeting. {agent_roles[agent_name]}",
                    prompt,
                    max_tokens=1500,
                    use_thinking=True,
                )

                transcript.append({"speaker": agent_name, "message": raw, "round": round_num})

                await self.broadcast({
                    "type": "meeting_agent_response",
                    "agent": agent_name,
                    "emoji": agent.emoji,
                    "color": agent.color,
                    "message": raw[:500] + ("..." if len(raw) > 500 else ""),
                    "full_response": raw,
                    "round": round_num,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Wait briefly for user input after each agent
                try:
                    user_msg = await asyncio.wait_for(user_queue.get(), timeout=5.0)
                    if user_msg == "__APPROVE__":
                        # User approved early — skip to verdict
                        break
                    transcript.append({"speaker": "HEAD_TRADER", "message": user_msg, "round": round_num})
                    await self.broadcast({
                        "type": "meeting_user_message",
                        "message": user_msg,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except asyncio.TimeoutError:
                    pass  # No user input, continue to next agent
            else:
                # All agents spoke — now JR produces verdict
                # (the `else` on the for-loop runs only if we didn't `break`)
                pass

            # --- JR Verdict ---
            transcript_text = ""
            for entry in transcript:
                transcript_text += f"\n**{entry['speaker']}**: {entry['message']}\n"

            verdict_prompt = (
                f"## EMERGENCY MEETING VERDICT\n\n"
                f"Topic: {topic}\n\n"
                f"## Full Discussion:\n{transcript_text}\n\n"
                f"---\n"
                f"As the Journalist (JR), produce the final verdict.\n"
                f"Synthesize ALL agent perspectives and Head Trader comments.\n"
                f"Respond in the SAME LANGUAGE as the discussion.\n\n"
                f"Return a JSON object with:\n"
                f'{{"conclusions": ["conclusion 1", "conclusion 2", ...], '
                f'"system_improvements": [{{"category": "...", "improvement": "...", '
                f'"config_change": {{"key": "...", "new_value": "..."}}}}], '
                f'"setup_memory_updates": [{{"setup_type": "...", "lessons": ["..."], '
                f'"failure_patterns": ["..."], "success_patterns": ["..."]}}]}}\n\n'
                f"IMPORTANT: Respond ONLY with valid JSON."
            )

            verdict_parsed = await self._call_claude_structured(
                SYSTEM_PROMPT, verdict_prompt, max_tokens=3000
            )
            verdict_result = json.dumps(verdict_parsed, indent=2, default=str)

            transcript.append({"speaker": "JR", "message": verdict_result, "round": round_num, "is_verdict": True})

            await self.broadcast({
                "type": "meeting_verdict",
                "conclusions": verdict_parsed.get("conclusions", []),
                "improvements": verdict_parsed.get("system_improvements", []),
                "round": round_num,
                "full_response": verdict_result,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # --- Wait for user: approve or continue ---
            while True:
                try:
                    user_msg = await asyncio.wait_for(user_queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    # 5 min timeout — auto-approve
                    user_msg = "__APPROVE__"

                if user_msg == "__APPROVE__":
                    await self.broadcast({
                        "type": "meeting_completed",
                        "meeting_type": "EMERGENCY",
                        "conclusions": verdict_parsed.get("conclusions", []),
                        "improvements": verdict_parsed.get("system_improvements", []),
                        "rounds": round_num,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    return verdict_parsed
                else:
                    # User wants to continue — add their message and start new round
                    transcript.append({"speaker": "HEAD_TRADER", "message": user_msg, "round": round_num})
                    await self.broadcast({
                        "type": "meeting_user_message",
                        "message": user_msg,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    break  # Break inner while, continue outer while (new round)

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
