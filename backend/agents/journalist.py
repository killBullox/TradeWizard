"""
Journalist (JR)
Handles journaling, performance monitoring, and post-trade review meetings.
Synthesizes insights for system self-improvement.
"""

import json
import os
from datetime import datetime
from .base_agent import BaseAgent, MODEL_STANDARD

SYSTEM_MODE = os.getenv("SYSTEM_MODE", "production").lower()
LEARNING_RULES_ACTIVE = (SYSTEM_MODE == "lab")


_BASE_PROMPT = """You are the Journalist (JR) — the institutional memory and performance analyst
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

_CONFIG_CHANGE_WHITELIST_PROMPT = """
## CONFIG_CHANGE WHITELIST — ALWAYS ACTIVE (production + lab)

Every entry in `system_improvements` MUST carry a `config_change` with a
`key` that is on the whitelist below. Any other key name is SILENTLY
REJECTED by the system validator — the improvement becomes a no-op and
the meeting produces zero effect. This applies to every meeting type,
including user-convened EMERGENCY meetings.

### Tunable parameters you can change (write to these keys):
- `rm_min_sl_atr_mult`     : SL = max(min_sl_pips, ATR × this). Default 1.0.
                             Raise to 1.5 if SLs are being hit too often by noise.
                             Lower to 0.7 if SLs are never hit and wins are small.
- `rm_max_tp_atr_mult`     : Max TP1 = ATR × this. Default 2.0.
                             Raise to 3.0 if trades close at max-duration with
                             unreached TP. Lower if TPs are never hit.
- `rm_min_rr_gate`         : Reject trade if RR below this. Default 1.2.
                             Lower to 1.0 early when you need volume for learning.
                             Raise to 1.5 when win rate is proven and you want
                             only the best setups.
- `rm_sl_cap_atr_mult`     : Absolute cap on SL width. Default 2.5.
- `rm_min_sl_pips_floor`   : Additional absolute floor on SL. Default 0.
- `max_trade_duration_hours`: Force-close after this. Default 6. Raise to 12
                             if many trades close at duration with small P&L.
- `min_sl_pips`            : Absolute floor on SL pips. Tunable. Default 20.
                             When setup SL is tighter than this AND
                             `sl_accommodation_enabled`=1, SL is widened to
                             min_sl_pips and lot is resized automatically.
- `double_entry_cooldown_minutes`: Block new trades on same symbol for N
                             minutes after last trade opens. Default 60.
                             Raise if over-exposure on the same pair is a
                             recurring failure mode.
- `sl_accommodation_enabled`: 0/1. If 1, widen tight SLs to min_sl_pips
                             instead of rejecting. Default 1.
- `tp_atr_rolling_window_trades`: N closed trades to compute rolling ATR
                             used as TP-size floor. 0 disables. Default 20.
- `overlap_block_enabled`  : 0/1. If 1, block new entries during configured
                             session-overlap windows (high-volatility).
                             Default 1.
- `rr_ratio`, `max_open_trades`, `analysis_interval`: self-evident.

JSON-valued keys (must be emitted as a JSON string in `new_value`):
- `overlap_windows_utc`    : Array of {"start":"HH:MM","end":"HH:MM"} UTC
                             windows. Default
                             `[{"start":"12:00","end":"13:00"},{"start":"14:00","end":"15:30"}]`.
                             Edit when session overlaps shift.

⚠️ STRICT WHITELIST. Only these EXACT keys are accepted. ANY OTHER KEY NAME
— including `min_sl_pips_by_pair`, `setup_pair_ban`, `rr_tracking`,
`ictea_confluence_minimum`, `sl_validation_enforcement`,
`orderblock_xauusd_size_boost`, `kill_zone_enforcement` — WILL BE
SILENTLY REJECTED by the validator and your proposal produces zero
effect. Do NOT invent new keys. If the change you want to express does
not map to one of the whitelisted keys, instead encode it as a
`proposed_rule` (FILTER/BOOST/BLOCK/ADJUST_PARAM) — the rule engine
handles per-symbol and per-setup logic at runtime.

🚫 PROTECTED (never propose changes to these — they are the user's
capital contract): `max_risk_usd`, `risk_percent`, `paper_mode`,
`mt5_login`, `mt5_password`, `mt5_server`, `mt5_bridge_url`,
`model_mode`.

### Required shape of each system_improvement

```
{
  "category": "RISK",
  "improvement": "SLs too tight — 7/10 losses hit SL within 30 min",
  "config_change": {"key": "rm_min_sl_atr_mult", "new_value": "1.5"}
}
```

🔴 HARD RULES (non-negotiable, all meeting types):
1. `config_change` is MANDATORY for every entry in system_improvements.
   No config_change → entry is discarded by the system, the meeting
   produces zero effect. If you have no actionable change, return
   system_improvements: [] (empty array) rather than narrative-only
   entries.
2. `config_change.key` MUST be one of the whitelisted keys above.
   Inventing names (e.g. `ATOMIC_REJECTION_SL_MINIMUM`,
   `KILL_ZONE_MARKET_BAN`, `audusd_tp_pips`, `position_sizing_dynamic_enabled`)
   is forbidden and produces zero effect — the validator silently
   rejects unknown keys. If the change you want to express does not
   map to a whitelisted key, either (a) find the closest mapping
   (e.g. "minimum SL 20 pips" → `min_sl_pips=20`) OR (b) omit the
   improvement entirely.
3. `config_change.new_value` MUST be a string representation of a
   number (e.g. "1.5", "0.8", "12").
4. You MAY return system_improvements: [] when the evidence doesn't
   support any concrete parameter change. An empty but honest output
   is better than a useless full output.
5. If you want to express per-symbol or per-setup logic (like
   "ban LiquiditySweep on XAUUSD" or "minimum SL 50 pips for XAUUSD"),
   in LAB mode emit a `proposed_rule` (see schema below); in PRODUCTION
   mode such granular logic is not auto-applied, so either skip it or
   encode it as the closest global `config_change` that approximates
   the intent.

Be explicit about WHY based on the trades reviewed. Only the keys listed
above are accepted — other keys will be rejected by the validator.
"""


_RULES_PROMPT_EXTENSION = """
## LAB MODE — AUTO-ADAPTIVE MANDATE

You are the meta-learner of an autonomous trading lab. Your primary job is
to MAKE THE SYSTEM BETTER BY CHANGING ITS OWN PARAMETERS. The system must
improve week over week without any human touching the code. Every meeting
you MUST propose concrete `config_change` entries in `system_improvements`
when the trade data supports it — following the CONFIG_CHANGE WHITELIST
rules above.

### How to decide changes (evidence-based):

PRIMARY SOURCE OF TRUTH: the SETUP DIAGNOSTICS table in the context
(per-cell breakdown of setup × symbol × session with n, WR, avg_RR,
expectancy, failure types, counter-trend %, verdict). Read it FIRST.
Every proposal must cite specific cells from it.

**Symmetric tuning principle** — auto-tuning must both TIGHTEN AND LOOSEN.
Never only loosen. If quality is degrading, your job is to restrict.

Reasoning playbook:
1. **Scan the cells for FAILING verdicts** (WR<40% or expectancy≤-0.10, n≥3).
   Each FAILING cell with n≥3 is a candidate for a proposed_rule BLOCK or
   FILTER targeted at that exact (setup, symbol, session). Do NOT solve
   cell-level failures by loosening global gates — that worsens the other
   cells. Use proposed_rules for targeted action.

2. **Scan the cells for WORKING verdicts** (WR≥55% and expectancy≥+0.15, n≥5).
   Each WORKING cell is a candidate for BOOST (INCREASE_SIZE) — reward what
   works rather than averaging it down with relaxations elsewhere.

3. **Only after cell-level action**, examine GLOBAL failure_patterns:
   - SL-hit >60% of losses AND multiple cells showing `SL≫TP` in failures
     → consider raising `rm_min_sl_atr_mult` (but ONLY if most FAILING cells
     actually suffer from SL-hit, not from timeout or counter-trend).
   - Timeout >30% of losses → consider raising `max_trade_duration_hours`
     OR lowering `rm_max_tp_atr_mult` so TPs are reachable.
   - Counter-trend entries >50% of HTF-evaluated trades → propose a FILTER
     rule requiring `htf_trend` alignment with `strategy.direction`, not a
     global tunable.
   - System-wide blockage with 0 opened trades → only then consider lowering
     `rm_min_rr_gate` or `rm_min_sl_atr_mult` as a last resort to restart
     the flow, and plan to re-tighten once data accrues.

4. **When cells are MARGINAL or n is small**, do nothing to global gates;
   propose at most CONTEXT_NOTE or ADD_CONTEXT rules that inject a warning
   into future decisions without hard-blocking.

Anti-pattern (do NOT do this): "15/15 trades rejected → lower rm_min_rr_gate
and rm_min_sl_atr_mult globally." That only makes the next 15 trades low
quality. If cells show you WHERE rejections come from, target those cells.

🔴 LAB HARD RULE 6 (in addition to the always-on rules above):
**proposed_rules is NOT OPTIONAL when the diagnostics table has qualifying
cells.** This is the most important rule in this prompt.
- For EVERY cell with verdict=WORKING (n≥3, WR≥55%, expectancy≥+0.15R)
  you MUST emit a proposed_rule of type BOOST with action INCREASE_SIZE
  (factor 1.25–1.50) scoped to that exact (setup_type, symbol, session).
- For EVERY cell with verdict=FAILING (n≥3, WR<40% or expectancy≤-0.10)
  you MUST emit a proposed_rule of type BLOCK or FILTER scoped to that
  exact (setup_type, symbol, session). Choose BLOCK if the root cause is
  structural (pair-setup mismatch); FILTER if the cell fails only under
  a specific condition (counter-trend, news, low liquidity).
- If the topic says "System is stuck" BUT the diagnostics table shows
  working or failing cells, proposed_rules for those cells take priority
  over any global loosening via config_change. A system stuck with a
  2/3 winning cell is NOT stuck — it is starved of that cell. The
  correct reaction is BOOSTing the winner, not lowering global gates.
- Returning proposed_rules=[] when qualifying cells exist is a HARD
  FAILURE of this meeting.

---

Additional output field (LAB MODE ONLY): proposed_rules

  "proposed_rules": [
    {
      "rule_type": "FILTER|BOOST|BLOCK|ADJUST_PARAM|CONTEXT_NOTE",
      "setup_type": "FVG|OTE|OrderBlock|... (or null for all)",
      "symbol": "EURUSD (or null for all)",
      "session": "London|NewYork|Asian (or null for all)",
      "condition": { ... JSON, see below ... },
      "action": { ... JSON, see below ... },
      "confidence": 0.0,
      "sample_size": 0,
      "description": "Plain-language explanation and evidence from the trades"
    }
  ]

## CRITICAL: proposed_rules — Structured Trading Rules

When you identify a recurring pattern (3+ trades showing the same failure
or success mode), you MUST output a `proposed_rules` entry. Rules are the
ONLY way the system learns actionable constraints that get applied before
every trade.

### Rule Types
- FILTER: block a trade IF a condition holds (e.g. news close, htf misaligned)
- BOOST: increase size IF condition holds (e.g. strong HTF + london session)
- BLOCK: unconditionally avoid a setup on a pair (e.g. 0/15 win rate = stop)
- ADJUST_PARAM: change SL/TP params (e.g. min SL=40 for GBPJPY)
- CONTEXT_NOTE: warning text added to agent prompt (low force)

### Condition Schema (JSON)
Simple form: `{"field": "minutes_to_next_news", "op": "<", "value": 30}`
Supported ops: "<", ">", "<=", ">=", "==", "!="
Supported fields: "minutes_to_next_news", "news_impact", "session",
  "htf_trend", "daily_range_used_pct", "spread_pips", "atr_pips_h1",
  "day_of_week", "hour_utc", "open_trades_count"
Compound form: `{"and": [cond1, cond2]}` or `{"or": [cond1, cond2]}`
Dynamic refs: `"value": "strategy.direction"` — compared against strategy field

### Action Schema (JSON)
- `{"type": "BLOCK", "reason": "..."}` — hard stop
- `{"type": "REDUCE_SIZE", "factor": 0.5}` — halve lot
- `{"type": "INCREASE_SIZE", "factor": 1.5}` — boost lot
- `{"type": "ADJUST_SL", "min_pips": 40}` — force min SL
- `{"type": "ADD_CONTEXT", "text": "..."}` — prompt injection

### Example
From "FVG/EURUSD lost 3 times during high-impact news within 15min":
```
{
  "rule_type": "FILTER",
  "setup_type": "FVG",
  "symbol": "EURUSD",
  "condition": {"and": [
    {"field": "minutes_to_next_news", "op": "<", "value": 30},
    {"field": "news_impact", "op": "==", "value": "high"}
  ]},
  "action": {"type": "BLOCK", "reason": "FVG/EURUSD 0/3 WR with news<30m"},
  "confidence": 0.6,
  "sample_size": 3,
  "description": "Trades #45, #47, #51 all LOSS with news<30m"
}
```

### When NOT to propose a rule
- Sample too small (<3 trades showing the pattern)
- Pattern is not reproducible (e.g. "market was unusual")
- Rule would contradict a recent confirmed rule
Leave `proposed_rules` as [] if nothing concrete emerges.
"""


# Compose final prompt — in production mode the rules extension is omitted
# to save tokens and avoid confusing the agent with unused output fields.
SYSTEM_PROMPT = (
    _BASE_PROMPT
    + _CONFIG_CHANGE_WHITELIST_PROMPT
    + (_RULES_PROMPT_EXTENSION if LEARNING_RULES_ACTIVE else "")
)


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
        # Raised from 4096 to 16000 because the meeting prompt in lab mode
        # (with AUTO-ADAPTIVE MANDATE + proposed_rules schema + examples)
        # is long and the response had been getting truncated mid-JSON,
        # producing parse errors and zero applied improvements.
        result = await self._call_claude_structured(SYSTEM_PROMPT, user_msg, max_tokens=16000)

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

        # Build trade summary — separate open and closed trades
        open_trades_summary = []
        closed_trades_summary = []
        for t in trades:
            d = t if isinstance(t, dict) else {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            trade_info = {
                "symbol": d.get("symbol"), "direction": d.get("direction"),
                "status": d.get("status"), "setup": d.get("ict_setup"),
                "result": d.get("result"), "pnl_usd": d.get("pnl_usd"),
                "entry": d.get("entry_price"), "sl": d.get("stop_loss"),
                "tp1": d.get("take_profit_1"), "tp2": d.get("take_profit_2"),
                "tp3": d.get("take_profit_3"), "lot_size": d.get("lot_size"),
                "tp_hits": d.get("tp_hits", 0),
                "open_time": str(d.get("open_time", ""))[:16],
                "close_time": str(d.get("close_time", ""))[:16],
            }
            if d.get("status") in ("ACTIVE", "PROPOSED", "APPROVED"):
                open_trades_summary.append(trade_info)
            else:
                closed_trades_summary.append(trade_info)

        base_context = (
            f"## EMERGENCY MEETING — Topic: {topic}\n\n"
            f"### Currently OPEN Trades ({len(open_trades_summary)})\n"
            f"{json.dumps(open_trades_summary, indent=2)}\n\n"
            f"### Recently CLOSED Trades ({len(closed_trades_summary)})\n"
            f"{json.dumps(closed_trades_summary[-20:], indent=2)}\n\n"
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

            # Step 1: Get a readable verdict summary (plain text)
            summary_prompt = (
                f"## EMERGENCY MEETING — FINAL VERDICT\n\n"
                f"Topic: {topic}\n\n"
                f"## Full Discussion:\n{transcript_text}\n\n"
                f"---\n"
                f"As JR, write a concise verdict (200 words max) summarizing:\n"
                f"1. Key conclusions (numbered list)\n"
                f"2. Concrete changes to implement\n"
                f"3. What each agent should do differently\n"
                f"Respond in the SAME LANGUAGE as the discussion. Plain text, no JSON."
            )
            verdict_text = await self._call_claude(
                SYSTEM_PROMPT, summary_prompt, max_tokens=1500, use_thinking=True
            )

            # Step 2: Extract structured data (JSON) in a separate call
            json_prompt = (
                f"Based on this meeting verdict:\n\n{verdict_text}\n\n"
                f"Extract the structured data as a JSON object. Keys:\n"
                f"- conclusions: array of 3-6 short conclusion strings\n"
                f"- system_improvements: array of objects with category, improvement, "
                f"config_change (key + new_value). ONLY include config changes for known "
                f"numeric or JSON keys. Leave config_change empty if no config change needed.\n"
                f"- setup_memory_updates: array of objects with setup_type, lessons, "
                f"failure_patterns, success_patterns\n\n"
                f"Respond ONLY with valid JSON. No markdown fences."
            )
            verdict_parsed = await self._call_claude_structured(
                "You extract structured data from meeting verdicts. Return ONLY valid JSON.",
                json_prompt, max_tokens=2000
            )

            import logging as _logging
            _log = _logging.getLogger(__name__)
            _log.info(f"[MEETING VERDICT] Keys: {list(verdict_parsed.keys())}, "
                      f"conclusions={len(verdict_parsed.get('conclusions', []))}, "
                      f"improvements={len(verdict_parsed.get('system_improvements', []))}")
            if "error" in verdict_parsed:
                _log.error(f"[MEETING VERDICT] Parse failed: {verdict_parsed.get('raw', '')[:300]}")
                # Fallback: save the text verdict as a single conclusion
                verdict_parsed = {
                    "conclusions": [verdict_text[:500]],
                    "system_improvements": [],
                    "setup_memory_updates": [],
                }

            transcript.append({"speaker": "JR", "message": verdict_text, "round": round_num, "is_verdict": True})

            await self.broadcast({
                "type": "meeting_verdict",
                "conclusions": verdict_parsed.get("conclusions", []),
                "improvements": verdict_parsed.get("system_improvements", []),
                "verdict_text": verdict_text,
                "round": round_num,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # --- Wait for user: approve or continue (no timeout — meeting stays open until user decides) ---
            while True:
                user_msg = await user_queue.get()

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
