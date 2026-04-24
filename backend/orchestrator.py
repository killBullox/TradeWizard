"""
Orchestrator
Manages the full multi-agent trading workflow:
ICTEA → RM → TR → AT → CC → JR
Also handles: live trade monitoring, post-trade meetings, system self-improvement.
"""

import json
import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Callable, Awaitable
from sqlalchemy import select, desc

from models.database import (
    async_session_factory, Trade, AgentLog, JournalEntry, Meeting,
    init_db, get_config, set_config,
)
from services.strategy_memory import (
    build_context_string as _build_memory,
    update_from_trade   as _mem_update_trade,
    update_from_meeting as _mem_update_meeting,
)
from agents import (
    ICTAdvisorAgent, RiskManagerAgent, TraderAgent,
    TradeAnalystAgent, ConnectorAgent, JournalistAgent,
)
from services.forex_data import get_multi_timeframe_data, fetch_ohlcv
from services.news_filter import get_news_filter, NewsFilter
from services.telegram_bot import get_telegram_bot, TelegramBot
from services.whatsapp_bot import get_whatsapp_bot, WhatsAppBot
from services.paper_account import get_paper_account, PaperAccount

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, broadcast_fn: Callable[[dict], Awaitable[None]] | None = None):
        bfn = broadcast_fn or self._noop

        self.ictea = ICTAdvisorAgent(bfn)
        self.rm    = RiskManagerAgent(bfn)
        self.tr    = TraderAgent(bfn)
        self.at    = TradeAnalystAgent(bfn)
        self.cc    = ConnectorAgent(bfn)
        self.jr    = JournalistAgent(bfn)

        self.broadcast = bfn
        self._running  = False
        self._analysis_task: asyncio.Task | None = None
        self._monitor_task:  asyncio.Task | None = None
        self._news:  NewsFilter   | None = None
        self._tg:    TelegramBot  | None = None
        self._wa:    WhatsAppBot  | None = None
        self._paper: PaperAccount | None = None
        self._active_meeting: dict | None = None  # interactive meeting state

    # ------------------------------------------------------------------ #
    #  Notification helper (sends to all configured channels)
    # ------------------------------------------------------------------ #
    async def _notify(self, method: str, *args, **kwargs):
        """Call a notification method on all active bots (Telegram + WhatsApp)."""
        for bot in (self._tg, self._wa):
            if bot and hasattr(bot, method):
                try:
                    asyncio.create_task(getattr(bot, method)(*args, **kwargs))
                except Exception as exc:
                    logger.warning("Notification %s failed on %s: %s", method, type(bot).__name__, exc)

    # ------------------------------------------------------------------ #
    #  Startup / Shutdown
    # ------------------------------------------------------------------ #
    async def start(self):
        await init_db()
        self._running = True

        # Initialize news filter from config
        async with async_session_factory() as s:
            block_before = int(await get_config("news_block_minutes_before", s) or 30)
            block_after  = int(await get_config("news_block_minutes_after",  s) or 30)
            block_medium = (await get_config("news_block_medium", s) or "false").lower() == "true"
        self._news = get_news_filter(block_before, block_after, block_medium)
        # Pre-warm the calendar cache
        asyncio.create_task(self._news.force_refresh())

        # Initialize paper trading account
        async with async_session_factory() as s:
            paper_bal = await get_config("paper_balance", s)
            if not paper_bal:
                # Fall back to the account_balance from Settings
                paper_bal = await get_config("account_balance", s)
            paper_bal = float(paper_bal or 10000.0)
        self._paper = get_paper_account(
            broadcast_fn=self.broadcast,
            initial_balance=paper_bal,
        )
        paper_on = (await self._get_config_value("paper_mode")) == "true"
        if paper_on:
            await self._paper.start()

        # Initialize notification bots
        self._tg = get_telegram_bot(orchestrator=self)
        polling  = os.getenv("TELEGRAM_POLLING", "true").lower() == "true"
        if polling:
            self._tg.start_polling()
        self._wa = get_whatsapp_bot(orchestrator=self)

        # Lab-only: apply the exploration profile ONCE in the life of this
        # lab DB. Keyed on a sentinel config entry `lab_exploration_applied`
        # so the seeding is genuinely one-shot regardless of any trade
        # history already present. After this, the Journalist and auto-
        # tuning loop own the parameters.
        if os.environ.get("SYSTEM_MODE", "production").lower() == "lab":
            try:
                async with async_session_factory() as s:
                    applied = await get_config("lab_exploration_applied", s)
                if applied != "true":
                    exploration = {
                        "rm_min_rr_gate":     "1.0",
                        "rm_max_tp_atr_mult": "3.0",
                        "rm_min_sl_atr_mult": "0.8",
                        "max_trade_duration_hours": "12",
                    }
                    async with async_session_factory() as s:
                        for k, v in exploration.items():
                            await set_config(k, v, s)
                        await set_config("lab_exploration_applied", "true", s)
                    logger.info("Lab exploration profile applied (one-shot): %s", exploration)
            except Exception as exc:
                logger.warning("Lab exploration seed failed: %s", exc)

        self._analysis_task = asyncio.create_task(self._analysis_loop())
        self._monitor_task  = asyncio.create_task(self._monitor_loop())
        # Lab-only: autonomous tuning loop that analyzes rejects and nudges
        # config parameters when the system is stuck (no trades opening).
        if os.environ.get("SYSTEM_MODE", "production").lower() == "lab":
            self._autotune_task = asyncio.create_task(self._autonomous_tuning_loop())
        else:
            self._autotune_task = None
        await self.broadcast({"type": "system_started", "timestamp": datetime.utcnow().isoformat()})
        logger.info("Orchestrator started")

    async def stop(self):
        self._running = False
        if self._tg:
            self._tg.stop_polling()
        if self._paper:
            await self._paper.stop()
        for task in (self._analysis_task, self._monitor_task, getattr(self, '_autotune_task', None)):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await self.broadcast({"type": "system_stopped", "timestamp": datetime.utcnow().isoformat()})

    # ------------------------------------------------------------------ #
    #  Main Analysis Loop  (runs every analysis_interval seconds)
    # ------------------------------------------------------------------ #
    async def _in_kill_zone(self) -> bool:
        """Check if current Rome time falls within any configured Kill Zone window.
        Respects the trade_on_weekend setting (default: off)."""
        async with async_session_factory() as s:
            raw             = await get_config("kill_zones", s)
            trade_weekend   = await get_config("trade_on_weekend", s)

        rome = datetime.now(ZoneInfo("Europe/Rome"))

        # Weekend check: Saturday=5, Sunday=6
        is_weekend = rome.weekday() >= 5
        allow_weekend = (trade_weekend or "false").lower() == "true"
        if is_weekend and not allow_weekend:
            return False

        # Default: London 07-11, NY 13-18 ora di Roma
        windows = [{"start": "07:00", "end": "11:00"}, {"start": "13:00", "end": "18:00"}]
        if raw:
            try:
                windows = json.loads(raw)
            except Exception:
                pass

        current_min = rome.hour * 60 + rome.minute
        for w in windows:
            try:
                sh, sm = map(int, w["start"].split(":"))
                eh, em = map(int, w["end"].split(":"))
                if sh * 60 + sm <= current_min < eh * 60 + em:
                    return True
            except Exception:
                continue
        return False

    async def _analysis_loop(self):
        # Brief startup delay so the WS clients can connect first
        await asyncio.sleep(10)
        _was_in_kz = False  # track kill zone transitions for post-KZ meetings
        while self._running:
            in_kz = await self._in_kill_zone()
            now_str = datetime.now(ZoneInfo("Europe/Rome")).strftime("%H:%M")
            if in_kz:
                _was_in_kz = True
                await self.broadcast({"type": "heartbeat", "message": f"🔄 Ciclo analisi [{now_str}]"})
                try:
                    await self._run_analysis_cycle()
                except Exception as e:
                    logger.error(f"Analysis loop error: {e}", exc_info=True)
                    await self.broadcast({"type": "error", "message": str(e)})
            else:
                # Just exited a kill zone → trigger KILLZONE_REVIEW meeting.
                # In lab mode, also trigger AUTO_TUNING (reflect on parameters
                # at every session end, not only when stuck) so the system
                # keeps nudging its own config daily.
                if _was_in_kz:
                    _was_in_kz = False
                    logger.info("Kill zone ended — scheduling KILLZONE_REVIEW meeting")
                    asyncio.create_task(self._run_killzone_review())
                    if os.environ.get("SYSTEM_MODE", "production").lower() == "lab":
                        logger.info("Kill zone ended (lab) — scheduling AUTO_TUNING meeting")
                        asyncio.create_task(self._run_auto_tuning_meeting())
                else:
                    await self.broadcast({"type": "heartbeat", "message": f"😴 Fuori Kill Zone [{now_str}]"})
                    logger.info("Outside Kill Zone — skipping analysis cycle")
            try:
                await asyncio.sleep(await self._get_interval())
            except Exception as e:
                logger.error(f"Analysis loop sleep error: {e}", exc_info=True)
                await asyncio.sleep(900)  # fallback interval

    async def _autonomous_tuning_loop(self):
        """LAB-ONLY. Every 4h during kill zone, if the system has been stuck
        (too few trades opened/closed in the last 4h and many rejects),
        trigger an AUTO_TUNING meeting. The meeting receives as context
        the rejection reasons and proposes config_change for tunable
        parameters. This is how the system unblocks itself without any
        human intervention.

        max_risk_usd and risk_percent are in PROTECTED_CONFIG_KEYS and
        cannot be changed by the meeting — the capital-at-risk contract
        is invariant by design.
        """
        INTERVAL_SEC = 4 * 3600  # 4 hours
        STUCK_THRESHOLD = 3       # <3 trades (opened+closed) in last window
        # Brief startup delay so boot activity doesn't trigger immediately
        await asyncio.sleep(60)
        while self._running:
            try:
                if await self._in_kill_zone():
                    if await self._is_stuck(hours=4, threshold=STUCK_THRESHOLD):
                        logger.info("Lab stuck — triggering AUTO_TUNING meeting")
                        try:
                            await self._run_auto_tuning_meeting()
                        except Exception as exc:
                            logger.warning("Auto-tuning meeting failed: %s", exc)
            except Exception as exc:
                logger.warning("Autonomous tuning loop error: %s", exc)
            await asyncio.sleep(INTERVAL_SEC)

    async def _is_stuck(self, hours: int = 4, threshold: int = 3) -> bool:
        """Return True if very few trade events happened in the last N hours.
        Signals that the system's constraints are too tight."""
        from datetime import timedelta as _td
        cutoff = datetime.utcnow() - _td(hours=hours)
        async with async_session_factory() as s:
            q = select(Trade).where(Trade.created_at >= cutoff)
            rows = (await s.execute(q)).scalars().all()
        active_or_recent = [t for t in rows
                            if t.status in ("ACTIVE", "CLOSED", "PROPOSED", "APPROVED")]
        return len(active_or_recent) < threshold

    async def _run_auto_tuning_meeting(self):
        """Collect rejected trades + rejection reasons from the last 4h and
        run a meeting whose agenda is exclusively: 'unblock the system by
        adjusting tunable parameters'."""
        from datetime import timedelta as _td
        cutoff = datetime.utcnow() - _td(hours=4)
        async with async_session_factory() as s:
            log_q = (select(AgentLog)
                     .where(AgentLog.action == "REJECTED")
                     .where(AgentLog.timestamp >= cutoff)
                     .order_by(desc(AgentLog.timestamp))
                     .limit(50))
            rejects = (await s.execute(log_q)).scalars().all()
            trade_q = (select(Trade)
                       .where(Trade.created_at >= cutoff)
                       .order_by(desc(Trade.created_at))
                       .limit(30))
            recent_trades = (await s.execute(trade_q)).scalars().all()
            config = await self._load_config(s)

        # Format rejects for the meeting prompt
        reject_lines = []
        for r in rejects:
            reject_lines.append(f"- {str(r.timestamp)[:19]} {r.agent_name}: {(r.message or '')[:160]}")
        rejects_context = "\n".join(reject_lines) if reject_lines else "(no rejections in window)"

        async with async_session_factory() as _sp:
            _perf_raw = await get_config("system_performance", _sp)
        perf = json.loads(_perf_raw or "{}")
        trades_dicts = []
        for t in recent_trades:
            trades_dicts.append({
                "id": t.id, "symbol": t.symbol, "direction": t.direction,
                "status": t.status, "result": t.result,
                "pnl_usd": t.pnl_usd, "ict_setup": t.ict_setup,
                "entry_price": t.entry_price, "close_price": t.close_price,
                "open_time": str(t.open_time)[:16],
            })

        current_memory = await build_context_string()

        # Re-use conduct_meeting with a dedicated meeting type. The
        # Journalist prompt already has the AUTO-ADAPTIVE MANDATE section
        # that lists the tunable keys and when to change them.
        topic = (
            "AUTO_TUNING. System is stuck. Analyze the rejection reasons "
            "below and propose at least one config_change to unblock trades. "
            "Remember: max_risk_usd and risk_percent are PROTECTED — do NOT "
            "propose changes to those. Every other tunable is fair game.\n\n"
            f"RECENT REJECTIONS:\n{rejects_context}"
        )
        result = await self.jr.conduct_meeting(
            "AUTO_TUNING", trades_dicts, perf, config,
            current_memory=current_memory,
            post_trade_context=topic,
        )
        improvements = result.get("system_improvements", [])
        if improvements:
            await self._apply_improvements(improvements)
            logger.info("Auto-tuning applied %d config changes", len(improvements))
            await self.broadcast({"type": "config_updated",
                                   "key": "auto-tuning",
                                   "value": f"{len(improvements)} changes",
                                   "reason": "Lab autonomous tuning"})
        # Save meeting record
        async with async_session_factory() as s:
            meeting = Meeting(
                meeting_type="AUTO_TUNING",
                trigger="Autonomous (lab stuck)",
                participants="JR",
                agenda=topic[:500],
                summary=json.dumps(result.get("conclusions", []), default=str)[:2000],
                improvements=json.dumps(improvements, default=str)[:4000],
                status="COMPLETED",
                completed_at=datetime.utcnow(),
            )
            s.add(meeting)
            await s.commit()

    async def _run_killzone_review(self):
        """Post-killzone deep review: what happened during this session, what could have been better."""
        try:
            await asyncio.sleep(120)  # 2-minute delay to let last trades settle
            await self.run_meeting("KILLZONE_REVIEW")
            logger.info("KILLZONE_REVIEW meeting completed")
        except Exception as exc:
            logger.error("KILLZONE_REVIEW meeting failed: %s", exc)

    async def _get_interval(self) -> int:
        async with async_session_factory() as s:
            val = await get_config("analysis_interval", s)
        return int(val or 3600)

    async def _run_analysis_cycle(self):
        async with async_session_factory() as s:
            pairs_raw  = await get_config("enabled_pairs", s)
            config     = await self._load_config(s)
            open_count = await self._count_open_trades(s)

        # Override account_balance with real MT5 balance (not static config)
        try:
            from services.mt5_direct import get_mt5_direct
            mt5_info = get_mt5_direct().get_account_info()
            if not mt5_info.get("error") and not mt5_info.get("simulated"):
                real_balance = mt5_info.get("balance", 0)
                real_equity = mt5_info.get("equity", 0)
                if real_balance > 0:
                    config["account_balance"] = str(real_balance)
                    config["_mt5_equity"] = str(real_equity)
                    config["_mt5_margin_free"] = str(mt5_info.get("margin_free", 0))
                    config["_mt5_leverage"] = str(mt5_info.get("leverage", 100))
                    logger.info("MT5 live balance: $%.2f (equity $%.2f, free $%.2f, leva 1:%s)",
                                real_balance, real_equity,
                                mt5_info.get("margin_free", 0), mt5_info.get("leverage", 100))
        except Exception as exc:
            logger.warning("Could not read MT5 balance, using config value: %s", exc)

        pairs = json.loads(pairs_raw or '["EURUSD","GBPUSD"]')

        await self.broadcast({
            "type": "analysis_cycle_started",
            "pairs": pairs,
            "timestamp": datetime.utcnow().isoformat(),
        })

        for symbol in pairs:
            if not self._running:
                break
            # Refresh open_count before each symbol so a trade opened mid-cycle
            # is counted and doesn't allow exceeding max_open_trades
            async with async_session_factory() as s:
                open_count = await self._count_open_trades(s)
            await self._analyze_and_trade(symbol, config, open_count)
            await asyncio.sleep(2)  # brief pause between pairs

    async def _analyze_and_trade(self, symbol: str, config: dict, open_count: int):
        try:
            # 0. News filter — block analysis if high-impact event is near
            news_enabled = config.get("news_block_enabled", "true").lower() != "false"
            if self._news and news_enabled:
                blocked, event = await self._news.is_blocked(symbol)
                if blocked and event:
                    msg = f"{event.title} [{event.currency}] @ {event.time.strftime('%H:%M')} UTC"
                    await self.broadcast({
                        "type":    "news_block",
                        "symbol":  symbol,
                        "event":   event.to_dict(),
                        "message": msg,
                    })
                    logger.info("News block: %s — %s", symbol, msg)
                    await self._notify("notify_news_block", event.to_dict(), symbol)
                    return

            # 1. Fetch market data from MT5 (EXCLUSIVELY)
            market_data = await get_multi_timeframe_data(symbol)

            # CRITICAL: abort if MT5 data is unavailable
            h1_data = market_data.get("H1", {})
            if h1_data.get("mt5_error") or not h1_data.get("candles"):
                mt5_err = h1_data.get("mt5_error", "No candles returned")
                logger.error("MT5 data unavailable for %s — skipping analysis: %s", symbol, mt5_err)
                await self.broadcast({
                    "type": "error",
                    "symbol": symbol,
                    "message": f"MT5 data unavailable: {mt5_err}. Analysis suspended.",
                })
                return

            # 2. Load strategy memory — injected into all agent prompts for continuous learning
            memory_ctx = await _build_memory()

            # 3. ICTEA Analysis (with memory context)
            ict_analysis = await self.ictea.analyze(symbol, market_data, config, memory_context=memory_ctx)
            await self._log_agent("ICTEA", "ANALYSIS", f"Analyzed {symbol}", ict_analysis)

            if ict_analysis.get("bias") == "NEUTRAL":
                await self.broadcast({"type": "skip", "symbol": symbol, "reason": "NEUTRAL bias"})
                return

            strategies = ict_analysis.get("strategies", [])
            if not strategies:
                return

            # Take highest-probability strategy
            strategy = max(strategies, key=lambda s: s.get("probability", 0))

            # 4. Hard limit checks — enforced in code
            max_open = int(config.get("max_open_trades", 3))
            if open_count >= max_open:
                await self.broadcast({"type": "trade_rejected", "symbol": symbol,
                                      "reason": f"Max open trades reached ({open_count}/{max_open})", "agent": "RM"})
                return

            # 4b. No duplicate trades on the same pair
            async with async_session_factory() as s:
                existing = await s.execute(
                    select(Trade).where(Trade.status == "ACTIVE", Trade.symbol == symbol)
                )
                if existing.scalars().first():
                    await self.broadcast({"type": "trade_rejected", "symbol": symbol,
                                          "reason": f"Already have an active trade on {symbol}", "agent": "SYS"})
                    return

            # 4c. Rule Engine — evaluate learning_rules BEFORE the RM
            from services.rule_engine import build_market_context, evaluate_trade as eval_rules
            market_context = build_market_context(market_data, symbol, config, open_count)
            strategy["_market_context"] = market_context
            setup_type = strategy.get("setup", "")
            session = market_context.get("session")
            verdict = await eval_rules(setup_type, symbol, session, market_context, strategy)

            if verdict.action == "BLOCK":
                logger.info("Trade BLOCKED by rules: %s — %s", symbol, verdict.reasons)
                await self._log_agent("SYS", "RULE_BLOCK",
                                       f"Trade blocked by learning rules: {symbol}",
                                       {"rules": verdict.rules_applied, "reasons": verdict.reasons})
                await self.broadcast({"type": "trade_rejected", "symbol": symbol,
                                      "reason": " | ".join(verdict.reasons), "agent": "RULE_ENGINE"})
                return

            # Inject context_notes from rules into the ICTEA memory context (already ran),
            # but we log them so they show in trade history.
            if verdict.context_notes:
                logger.info("Rule context notes for %s: %s", symbol, verdict.context_notes)

            # Pass rule verdict into RM so size_factor and adjustments take effect
            strategy["_rule_verdict"] = verdict.to_dict()

            # 5. Risk Manager (with memory context + rule verdict)
            rm_result = await self.rm.evaluate(symbol, strategy, market_data, config, open_count, memory_context=memory_ctx)
            await self._log_agent("RM", "EVALUATION", f"Evaluated {symbol}", rm_result)

            if not rm_result.get("approved"):
                reason = rm_result.get("rejection_reason", "Rejected by RM")
                await self.broadcast({"type": "trade_rejected", "symbol": symbol, "reason": reason, "agent": "RM"})
                return

            # 4. Trader — generate precise parameters
            trade_params = await self.tr.generate_trade(symbol, strategy, rm_result, market_data)
            await self._log_agent("TR", "TRADE_GENERATED", f"Generated trade for {symbol}", trade_params)

            # Guard: enforce RM's SL if TR generated a tighter one
            rm_sl_pips = rm_result.get("position_size", {}).get("sl_pips", 0)
            if rm_sl_pips > 0:
                entry = float(trade_params.get("entry_price", 0))
                sl = float(trade_params.get("stop_loss", 0))
                pip = 0.01 if "JPY" in symbol else (1.0 if symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)
                actual_sl_pips = abs(entry - sl) / pip if entry and sl else 0
                if actual_sl_pips < rm_sl_pips * 0.8:  # TR's SL is too tight vs RM
                    sign = -1 if trade_params.get("direction") == "BUY" else 1
                    new_sl = round(entry + sign * rm_sl_pips * pip, 6)
                    logger.info("SL enforced: TR gave %.1fp, RM wants %.1fp → SL %.5f", actual_sl_pips, rm_sl_pips, new_sl)
                    trade_params["stop_loss"] = new_sl

            # Guard: enforce minimum RR on TP1 using RM-approved values if LLM returned bad params
            trade_params = self._enforce_rr(trade_params, rm_result, config)

            # Enforce lot size using ACTUAL entry/SL from trade_params (not RM's sl_pips which can be 0)
            self._enforce_lot_size(rm_result, trade_params, symbol, config)
            pos = rm_result.get("position_size", {})
            await self._log_agent("SYS", "LOT_ENFORCED",
                f"{symbol} {trade_params.get('direction')} → {pos.get('lot_size','?')} lots "
                f"(risk ${pos.get('risk_usd','?')} / {pos.get('sl_pips','?')} pip SL)",
                {"lot": pos.get("lot_size"), "risk_usd": pos.get("risk_usd"),
                 "sl_pips": pos.get("sl_pips"), "risk_mode": pos.get("risk_mode")})

            # 5b. Margin check — prevent 10019 "No money" errors
            margin_ok = await self._check_margin(symbol, trade_params, rm_result, config, open_count)
            if not margin_ok:
                await self._log_agent("SYS", "REJECTED", f"Insufficient margin for {symbol}", trade_params)
                await self.broadcast({"type": "trade_rejected", "symbol": symbol,
                                      "reason": "Insufficient margin (10019 prevention)", "agent": "SYS"})
                return

            logger.info(">>> MARGIN CHECK PASSED for %s, lot_size=%.2f — proceeding to sanity check", symbol, float(trade_params.get("lot_size", 0)))

            # 6. Hard mathematical sanity check — the ONLY gatekeeper after RM approval
            # AT validation removed: was blocking valid trades despite clear "APPROVE" prompt.
            # Sanity check covers all critical defects (SL/TP side, min SL, net RR) in code.
            rejection = self._sanity_check_trade(trade_params, market_data, config)
            if rejection:
                await self._log_agent("SYS", "REJECTED", f"Sanity check failed: {rejection}", trade_params)
                await self.broadcast({"type": "trade_rejected", "symbol": symbol, "reason": rejection, "agent": "SYS"})
                return

            # 6. Save to DB — mark as paper if paper mode is on
            paper_on = await self._is_paper_mode()
            trade_id = await self._save_trade(
                symbol, strategy, rm_result, trade_params, ict_analysis,
                is_paper=paper_on,
            )

            # 7. Connector — send to MT5 (or paper account)
            if paper_on and self._paper:
                cc_result = self._paper.open_position(trade_id, trade_params)
                await self._log_agent("CC", "PAPER_OPEN", f"Paper open {symbol}", cc_result)
            else:
                cc_result = await self.cc.open_trade({**trade_params, "id": trade_id})
                await self._log_agent("CC", "TRADE_SENT", f"Sent {symbol} to MT5", cc_result)

            if cc_result.get("success"):
                all_tickets = cc_result.get("all_tickets", [cc_result.get("ticket", "UNKNOWN")])
                ticket_str = ",".join(str(t) for t in all_tickets)
                await self._update_trade_ticket(trade_id, ticket_str)
                logger.info("Trade #%d sent to MT5: tickets=%s (%d splits)",
                            trade_id, ticket_str, cc_result.get("splits", 1))

                # Read the REAL fill price from MT5 and update entry_price.
                # Without this, the DB keeps the proposed price (not the fill),
                # and P&L is calculated off a wrong baseline.
                if not paper_on:
                    try:
                        from services.mt5_direct import get_mt5_direct
                        mt5 = get_mt5_direct()
                        positions = mt5.get_positions() or []
                        tw_tickets_int = {int(t) for t in all_tickets if str(t).isdigit()}
                        fills = [(float(p.get("volume", 0)), float(p.get("price_open", 0)))
                                  for p in positions
                                  if p.get("ticket") in tw_tickets_int and p.get("price_open")]
                        if fills:
                            total_vol = sum(v for v, _ in fills) or 1
                            avg_entry = sum(v * px for v, px in fills) / total_vol
                            async with async_session_factory() as s:
                                t = await s.get(Trade, trade_id)
                                if t:
                                    old = t.entry_price
                                    t.entry_price = round(avg_entry, 6)
                                    await s.commit()
                            logger.info("Trade #%d entry_price realigned: %.6f → %.6f (MT5 fill)",
                                         trade_id, old or 0, avg_entry)
                    except Exception as exc:
                        logger.warning("Could not realign entry_price for #%d: %s", trade_id, exc)
            else:
                error = cc_result.get("error", "Unknown error")
                logger.error("Trade #%d MT5 FAILED: %s | Full result: %s", trade_id, error, cc_result)
                await self._log_agent("CC", "MT5_FAILED", f"MT5 execution failed for {symbol}: {error}", cc_result)
                await self._append_close_note(trade_id, f"MT5 FAILED: {error}")
                # Cancel the trade — don't leave ghost trades without MT5 ticket
                async with async_session_factory() as s:
                    t = await s.get(Trade, trade_id)
                    if t:
                        t.status = "CANCELLED"
                        t.close_notes = (t.close_notes or "") + f"\n[AUTO] Cancelled: MT5 execution failed"
                        await s.commit()
                logger.info("Trade #%d cancelled due to MT5 failure", trade_id)
                return

            # 8. Journalist — document
            analysis_chain = {
                "ictea": ict_analysis, "strategy": strategy,
                "risk": rm_result, "validation": {},
            }
            jr_entry = await self.jr.journal_trade_open(
                {**trade_params, "id": trade_id, "ict_setup": strategy.get("setup")},
                analysis_chain,
            )
            await self._save_journal(trade_id, "TRADE_OPEN", jr_entry)

            open_count += 1
            await self.broadcast({
                "type": "trade_opened",
                "trade_id": trade_id,
                "symbol": symbol,
                "direction": trade_params.get("direction"),
                "entry": trade_params.get("entry_price"),
                "sl": trade_params.get("stop_loss"),
                "tp1": trade_params.get("take_profit_1"),
                "ticket": cc_result.get("ticket"),
                "timestamp": datetime.utcnow().isoformat(),
            })
            await self._notify("notify_trade_open", {
                **trade_params,
                "id": trade_id,
                "ict_setup": strategy.get("setup"),
                "mt5_ticket": cc_result.get("ticket"),
                "rr_ratio": rm_result.get("position_size", {}).get("rr_ratio", 2.0),
            })

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            await self._log_agent("SYS", "ERROR", f"Analysis failed for {symbol}: {e}", {"traceback": str(e)})
            await self.broadcast({"type": "error", "symbol": symbol, "message": str(e)})

    # ------------------------------------------------------------------ #
    #  Trade Monitor Loop  (checks active trades every 60 seconds)
    # ------------------------------------------------------------------ #
    async def _monitor_loop(self):
        while self._running:
            try:
                await self._monitor_active_trades()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)
            try:
                await self._reconcile_mt5_positions()
            except Exception as e:
                logger.error(f"Reconcile error: {e}", exc_info=True)
            await asyncio.sleep(60)

    async def _reconcile_mt5_positions(self):
        """Reconcile DB state with actual MT5 positions.

        Two failure modes we fix:
        1. Trade marked CLOSED in DB but MT5 still has the ticket → retry close.
           Happens when the original close order failed (pipe wedge, broker
           offline, etc.) but the DB row was flipped to CLOSED anyway.
        2. Trade marked ACTIVE in DB but MT5 no longer has the ticket → mark
           it CLOSED in the DB. Happens when SL/TP was hit on the broker side
           while we weren't watching.
        """
        # Production only — lab uses paper execution, no MT5 reconciliation needed
        if os.environ.get("SYSTEM_MODE", "production").lower() == "lab":
            return

        # 1) Get live MT5 tickets
        try:
            from services.mt5_direct import get_mt5_direct
            mt5 = get_mt5_direct()
            positions = mt5.get_positions() or []
        except Exception as exc:
            logger.debug(f"Reconcile: cannot fetch positions: {exc}")
            return
        live_tickets = {str(p.get("ticket")) for p in positions if p.get("ticket")}

        # 2) Find DB trades that might be out of sync
        from datetime import timedelta as _td
        cutoff = datetime.utcnow() - _td(days=7)  # only look at recent trades
        async with async_session_factory() as s:
            result = await s.execute(
                select(Trade)
                .where(Trade.mt5_ticket.isnot(None))
                .where(Trade.is_paper == False)
                .where(Trade.open_time >= cutoff)
            )
            rows = result.scalars().all()

        for t in rows:
            if not t.mt5_ticket:
                continue
            tw_tickets = {tk.strip() for tk in t.mt5_ticket.split(",") if tk.strip()}
            still_open = tw_tickets & live_tickets

            # Case 1: DB says CLOSED/CANCELLED but MT5 still has at least one ticket
            if t.status in ("CLOSED", "CANCELLED") and still_open:
                logger.warning(
                    "Reconcile: trade #%d status=%s but MT5 still has %s — retrying close",
                    t.id, t.status, still_open,
                )
                closed_count = 0
                for ticket in still_open:
                    try:
                        res = mt5.close_trade(ticket, t.symbol)
                        if res and res.get("success"):
                            closed_count += 1
                            logger.info("Reconcile: closed orphan ticket %s (trade #%d)", ticket, t.id)
                        else:
                            logger.warning("Reconcile: close failed for %s: %s",
                                            ticket, res.get("error") if res else "no-response")
                    except Exception as exc:
                        logger.warning("Reconcile close error %s: %s", ticket, exc)
                if closed_count > 0:
                    await self._append_close_note(
                        t.id,
                        f"[RECONCILE] closed {closed_count}/{len(still_open)} orphan tickets"
                    )

            # Case 2: DB says ACTIVE but MT5 no longer has any of the tickets
            elif t.status == "ACTIVE" and tw_tickets and not still_open:
                logger.warning(
                    "Reconcile: trade #%d status=ACTIVE but MT5 closed all tickets — marking CLOSED",
                    t.id,
                )
                # Fetch current price for a best-effort close_price
                try:
                    data = await fetch_ohlcv(t.symbol, "H1", 5)
                    price = data.get("indicators", {}).get("current_price", t.entry_price)
                except Exception:
                    price = t.entry_price
                # Use existing close flow — it updates stats, memory, meeting trigger
                await self._close_trade(t, price, "Reconcile: MT5 closed externally")

            # Case 3: DB says ACTIVE, tickets match MT5 — verify entry_price matches
            # MT5 fill price. If off by more than 5 pips, realign (fixes the mismatch
            # on trades opened before the fill-price sync was added).
            elif t.status == "ACTIVE" and still_open:
                fills = [(float(p.get("volume", 0)), float(p.get("price_open", 0)))
                          for p in positions
                          if str(p.get("ticket")) in still_open and p.get("price_open")]
                if fills:
                    total_vol = sum(v for v, _ in fills) or 1
                    avg_entry = sum(v * px for v, px in fills) / total_vol
                    pip = 0.01 if "JPY" in t.symbol else (1.0 if t.symbol in ("XAUUSD", "US30", "NAS100", "US500") else 0.0001)
                    diff_pips = abs((t.entry_price or 0) - avg_entry) / pip if t.entry_price else 0
                    if diff_pips > 5:
                        logger.warning(
                            "Reconcile: trade #%d entry_price mismatch (DB=%.6f, MT5=%.6f, %.1fp) — realigning",
                            t.id, t.entry_price, avg_entry, diff_pips,
                        )
                        async with async_session_factory() as s:
                            row = await s.get(Trade, t.id)
                            if row:
                                row.entry_price = round(avg_entry, 6)
                                await s.commit()

    async def _monitor_active_trades(self):
        async with async_session_factory() as s:
            result = await s.execute(
                select(Trade).where(Trade.status == "ACTIVE")
            )
            trades = result.scalars().all()

        for trade in trades:
            try:
                data = await fetch_ohlcv(trade.symbol, "H1", 50)
                current_price = data.get("indicators", {}).get("current_price", 0)

                if not current_price:
                    continue  # Skip if no price data available

                # ── SPLIT TICKET SYNC: detect MT5-closed split positions ──
                await self._sync_split_tickets(trade, current_price)
                # Reload trade in case _sync_split_tickets changed status
                async with async_session_factory() as _s:
                    trade = await _s.get(Trade, trade.id)
                    if not trade or trade.status != "ACTIVE":
                        continue

                # ── HARD CHECK: Max trade duration (day trading constraint) ──
                if trade.open_time:
                    from zoneinfo import ZoneInfo as _ZI
                    now = datetime.now(_ZI("Europe/Rome"))
                    open_time = trade.open_time.replace(tzinfo=_ZI("Europe/Rome")) if trade.open_time.tzinfo is None else trade.open_time
                    hours_open = (now - open_time).total_seconds() / 3600
                    max_hours = float(config.get("max_trade_duration_hours", "8") if hasattr(self, '_last_config') else "8")
                    try:
                        async with async_session_factory() as _s:
                            _mh = await get_config("max_trade_duration_hours", _s)
                            max_hours = float(_mh) if _mh else 8.0
                    except Exception:
                        max_hours = 8.0
                    if hours_open > max_hours:
                        logger.warning("MAX DURATION on trade #%d %s — open %.1fh (max %.0fh)",
                                       trade.id, trade.symbol, hours_open, max_hours)
                        await self._append_close_note(trade.id,
                            f"Max duration reached: {hours_open:.1f}h > {max_hours:.0f}h — force close @ {current_price:.5f}")
                        await self._close_trade(trade, current_price, f"Max duration {max_hours:.0f}h exceeded")
                        await self._notify("notify_trade_close", {
                            "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                            "entry_price": trade.entry_price, "close_price": current_price,
                            "ict_setup": trade.ict_setup,
                            "result": "WIN" if self._calc_trade_pnl(trade, current_price) > 0 else "LOSS",
                        }, self._calc_trade_pnl(trade, current_price), self._calc_trade_pips(trade, current_price),
                           f"Max duration {max_hours:.0f}h exceeded")
                        continue

                # ── HARD CHECK: Auto-close on SL hit (code-enforced, not LLM) ──
                sl = trade.stop_loss or 0
                if sl > 0:
                    sl_hit = (
                        (trade.direction == "BUY"  and current_price <= sl) or
                        (trade.direction == "SELL" and current_price >= sl)
                    )
                    if sl_hit:
                        logger.warning("SL HIT on trade #%d %s @ %.5f (SL=%.5f)",
                                       trade.id, trade.symbol, current_price, sl)
                        await self._append_close_note(trade.id,
                            f"SL HIT @ {current_price:.5f} (SL={sl:.5f})")
                        await self._close_trade(trade, sl, "Stop Loss Hit")
                        await self._notify("notify_trade_close", {
                            "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                            "entry_price": trade.entry_price, "close_price": sl,
                            "ict_setup": trade.ict_setup, "result": "LOSS",
                        }, self._calc_trade_pnl(trade, sl), self._calc_trade_pips(trade, sl), "Stop Loss Hit")
                        continue

                # ── HARD CHECK: Auto-partial-close on TP hit (code-enforced) ──
                tp_hits = trade.tp_hits or 0
                next_tp = (
                    trade.take_profit_1 if tp_hits < 1 else
                    trade.take_profit_2 if tp_hits < 2 else
                    trade.take_profit_3 if tp_hits < 3 else None
                )
                if next_tp:
                    tp_reached = (
                        (trade.direction == "BUY"  and current_price >= next_tp) or
                        (trade.direction == "SELL" and current_price <= next_tp)
                    )
                    if tp_reached:
                        tp_num = tp_hits + 1
                        logger.info("TP%d HIT on trade #%d %s @ %.5f (TP=%.5f)",
                                    tp_num, trade.id, trade.symbol, current_price, next_tp)
                        pct = 0.5 if tp_num == 1 else (0.3 if tp_num == 2 else 1.0)
                        await self.cc.close_partial(trade.mt5_ticket or "", trade.symbol, pct)
                        await self._consume_next_tp(trade.id)
                        await self._append_close_note(trade.id,
                            f"TP{tp_num} HIT @ {current_price:.5f} — auto partial close {int(pct*100)}%")
                        # Move SL to breakeven after TP1
                        if tp_num == 1:
                            entry = trade.entry_price or 0
                            if entry:
                                await self.cc.modify_sl(trade.mt5_ticket or "", entry, trade.symbol)
                                await self._update_trade_sl(trade.id, entry)
                                if self._paper:
                                    self._paper.modify_sl(trade.id, entry)
                                await self._append_close_note(trade.id, f"SL spostato a breakeven ({entry:.5f}) dopo TP1")
                        # Move SL to TP1 after TP2
                        elif tp_num == 2 and trade.take_profit_1:
                            await self.cc.modify_sl(trade.mt5_ticket or "", trade.take_profit_1, trade.symbol)
                            await self._update_trade_sl(trade.id, trade.take_profit_1)
                            if self._paper:
                                self._paper.modify_sl(trade.id, trade.take_profit_1)
                            await self._append_close_note(trade.id, f"SL trailato a TP1 ({trade.take_profit_1:.5f}) dopo TP2")
                        await self.broadcast({"type": "partial_close", "trade_id": trade.id, "percent": pct})
                        await self._notify("notify_partial_close", trade.symbol, trade.id, pct)
                        if tp_num == 3:
                            # All TPs hit — close remaining
                            await self._close_trade(trade, current_price, "All TPs reached")
                        continue

                # ── AT agent: only for TRAIL_SL and early exit decisions ──
                decision = await self.at.manage_trade(
                    {
                        "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                        "entry_price": trade.entry_price, "stop_loss": trade.stop_loss,
                        # Null out already-hit TPs so AT targets the correct next level
                        "take_profit_1": trade.take_profit_1 if tp_hits < 1 else None,
                        "take_profit_2": trade.take_profit_2 if tp_hits < 2 else None,
                        "take_profit_3": trade.take_profit_3 if tp_hits < 3 else None,
                        "lot_size": trade.lot_size,
                        "ict_setup": trade.ict_setup, "trailing_sl_updates": trade.trailing_sl_updates,
                    },
                    current_price,
                    {"H1": data},
                )

                action = decision.get("action", "HOLD")

                if action == "TRAIL_SL" and decision.get("new_stop_loss"):
                    new_sl = decision["new_stop_loss"]
                    at_reason = decision.get("reason", "")
                    await self.cc.modify_sl(trade.mt5_ticket or "", new_sl, trade.symbol)
                    await self._update_trade_sl(trade.id, new_sl)
                    await self._append_close_note(trade.id,
                        f"SL trailato → {new_sl:.5f}" + (f" — {at_reason}" if at_reason else ""))
                    await self.broadcast({
                        "type": "sl_trailed",
                        "trade_id": trade.id,
                        "symbol": trade.symbol,
                        "new_sl": new_sl,
                        "reason": decision.get("reason"),
                    })
                    await self._notify("notify_sl_trailed", trade.symbol, trade.id, new_sl)

                elif action == "PARTIAL_CLOSE" and decision.get("close_percent"):
                    pct = decision["close_percent"]
                    tp_num = (trade.tp_hits or 0) + 1
                    at_reason = decision.get("reason", "")

                    # HARD CHECK: only partial close if price actually reached the next TP
                    next_tp = (
                        trade.take_profit_1 if tp_num == 1 else
                        trade.take_profit_2 if tp_num == 2 else
                        trade.take_profit_3 if tp_num == 3 else None
                    )
                    if next_tp is not None:
                        tp_reached = (
                            (trade.direction == "BUY"  and current_price >= next_tp) or
                            (trade.direction == "SELL" and current_price <= next_tp)
                        )
                        if not tp_reached:
                            logger.info(f"Trade #{trade.id}: AT wanted PARTIAL_CLOSE but price "
                                        f"{current_price} has not reached TP{tp_num} ({next_tp}). Holding.")
                            await self._append_close_note(trade.id,
                                f"[BLOCKED] AT partial close denied: price {current_price:.5f} "
                                f"not at TP{tp_num} ({next_tp:.5f})")
                            continue
                    await self.cc.close_partial(trade.mt5_ticket or "", trade.symbol, pct)
                    await self._consume_next_tp(trade.id)
                    await self._append_close_note(trade.id,
                        f"PARTIAL CLOSE {int(pct*100)}% su TP{tp_num} @ {current_price:.5f}" +
                        (f" — {at_reason}" if at_reason else ""))

                    # Move SL to breakeven after TP1 hit (protects the remaining position)
                    entry = trade.entry_price or 0
                    current_sl = trade.stop_loss or 0
                    be_needed = entry and (
                        (trade.direction == "BUY"  and current_sl < entry) or
                        (trade.direction == "SELL" and current_sl > entry)
                    )
                    if be_needed:
                        await self.cc.modify_sl(trade.mt5_ticket or "", entry, trade.symbol)
                        await self._update_trade_sl(trade.id, entry)
                        if self._paper:
                            self._paper.modify_sl(trade.id, entry)
                        await self._append_close_note(trade.id, f"SL spostato a breakeven ({entry:.5f})")
                        await self.broadcast({
                            "type": "sl_trailed",
                            "trade_id": trade.id,
                            "symbol": trade.symbol,
                            "new_sl": entry,
                            "reason": "Breakeven after TP1 hit",
                        })
                        logger.info("SL moved to breakeven %.5f for trade #%d after partial close", entry, trade.id)

                    await self.broadcast({"type": "partial_close", "trade_id": trade.id, "percent": pct})
                    await self._notify("notify_partial_close", trade.symbol, trade.id, pct)

                elif action in ("CLOSE_ALL", "CLOSE"):
                    at_reason = decision.get("reason", "")
                    await self._append_close_note(trade.id,
                        f"CLOSE @ {current_price:.5f}" + (f" — {at_reason}" if at_reason else ""))
                    await self._close_trade(trade, current_price, "AT Management Decision")

            except Exception as e:
                logger.error(f"Monitor error for trade {trade.id}: {e}")

    async def _sync_split_tickets(self, trade, current_price: float):
        """For split trades (multiple tickets), detect which MT5 positions have been
        closed, determine if closed by TP or SL, update accordingly."""
        ticket_str = trade.mt5_ticket or ""
        tickets = [t.strip() for t in ticket_str.split(",") if t.strip()]
        if len(tickets) <= 1:
            return  # single ticket — handled by existing TP/SL logic

        try:
            from services.mt5_direct import get_mt5_direct
            mt5 = get_mt5_direct()
            if not mt5.connected:
                return

            open_positions = mt5.get_positions()
            open_tickets = {str(p["ticket"]) for p in open_positions}

            still_open = [t for t in tickets if t in open_tickets]
            just_closed = [t for t in tickets if t not in open_tickets]

            if not just_closed:
                return  # all splits still open, nothing to do

            # Determine close reason: TP hit or SL hit
            # Compare current price to entry, SL, and TPs
            entry = trade.entry_price or 0
            sl = trade.stop_loss or 0
            tp1 = trade.take_profit_1
            tp2 = trade.take_profit_2
            tp3 = trade.take_profit_3
            is_buy = trade.direction == "BUY"
            tp_hits_before = trade.tp_hits or 0

            # Check if price reached any TP
            tp_reached = False
            if is_buy:
                if (tp1 and current_price >= tp1) or (tp2 and current_price >= tp2) or (tp3 and current_price >= tp3):
                    tp_reached = True
                sl_hit = sl > 0 and current_price <= sl
            else:
                if (tp1 and current_price <= tp1) or (tp2 and current_price <= tp2) or (tp3 and current_price <= tp3):
                    tp_reached = True
                sl_hit = sl > 0 and current_price >= sl

            # Also check if close price is near entry (breakeven SL)
            pip = 0.01 if "JPY" in (trade.symbol or "") else (1.0 if trade.symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)
            near_entry = abs(current_price - entry) / pip < 5 if entry else False

            if tp_reached:
                close_reason = "TP"
                new_tp_hits = tp_hits_before + len(just_closed)
            elif sl_hit:
                close_reason = "SL"
                new_tp_hits = tp_hits_before
            elif near_entry:
                close_reason = "BE"  # breakeven
                new_tp_hits = tp_hits_before
            else:
                close_reason = "UNKNOWN"
                new_tp_hits = tp_hits_before

            logger.info("Split sync trade #%d: %d/%d positions closed (%s) (tickets %s, price=%.5f)",
                        trade.id, len(just_closed), len(tickets), close_reason, just_closed, current_price)

            # Move SL to breakeven on surviving positions only if TP was hit
            if still_open:
                if close_reason == "TP" and entry:
                    for t in still_open:
                        await self.cc.modify_sl(t, entry, trade.symbol)
                    await self._update_trade_sl(trade.id, entry)
                    await self._append_close_note(trade.id,
                        f"TP hit: {len(just_closed)} posizioni chiuse, "
                        f"SL → breakeven ({entry:.5f}) su {len(still_open)} rimanenti")
                elif close_reason in ("SL", "BE"):
                    await self._append_close_note(trade.id,
                        f"{close_reason}: {len(just_closed)} posizioni chiuse @ {current_price:.5f}, "
                        f"{len(still_open)} ancora aperte")

                # Update stored tickets
                async with async_session_factory() as s:
                    t = await s.get(Trade, trade.id)
                    if t:
                        t.mt5_ticket = ",".join(still_open)
                        t.tp_hits = new_tp_hits
                        await s.commit()
            else:
                # All positions closed — determine final close price and reason
                if close_reason == "SL" or close_reason == "BE":
                    close_price = sl if sl_hit else entry
                    reason = f"SL Hit" if sl_hit else "Breakeven"
                elif close_reason == "TP":
                    close_price = current_price
                    reason = "All TPs reached"
                else:
                    close_price = current_price
                    reason = "All split positions closed by MT5"

                await self._append_close_note(trade.id,
                    f"Tutte le {len(tickets)} posizioni chiuse ({close_reason}) @ {close_price:.5f}")
                await self._close_trade(trade, close_price, reason)

        except Exception as exc:
            logger.warning("Split ticket sync error for trade #%d: %s", trade.id, exc)

    def _calc_trade_pips(self, trade, price: float) -> float:
        pip = 0.01 if "JPY" in (trade.symbol or "") else (1.0 if trade.symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)
        if trade.direction == "BUY":
            return round((price - (trade.entry_price or 0)) / pip, 1)
        return round(((trade.entry_price or 0) - price) / pip, 1)

    def _calc_trade_pnl(self, trade, price: float) -> float:
        pips = self._calc_trade_pips(trade, price)
        _pip_usd = {"XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
                    "USDJPY": 6.5, "EURJPY": 6.5, "GBPJPY": 6.5}
        pip_usd = _pip_usd.get(trade.symbol or "", 10.0)
        return round(pips * pip_usd * (trade.lot_size or 0.01), 2)

    async def _close_trade(self, trade, close_price: float, reason: str):
        entry = trade.entry_price or 0

        # GUARD: a zero or nonsensical close_price produces phantom pnl of
        # thousands of dollars. Reject instead of committing the garbage.
        # Acceptable range: within 20% of entry. Anything outside is a bug
        # upstream (stale tick, failed fetch, etc.) — abort the close.
        if not close_price or close_price <= 0:
            logger.error("REFUSING to close trade #%d with close_price=%s — bug upstream; using entry as fallback",
                          trade.id, close_price)
            close_price = entry  # fallback: breakeven, avoids phantom pnl
            reason = f"{reason} [GUARDED: close_price was 0/negative]"
        elif entry > 0 and abs(close_price - entry) / entry > 0.20:
            logger.error("REFUSING to close trade #%d: close_price=%.5f too far from entry=%.5f (>20%%)",
                          trade.id, close_price, entry)
            close_price = entry
            reason = f"{reason} [GUARDED: close_price insane vs entry]"

        cc_result = await self.cc.close_trade(trade.mt5_ticket or "", trade.symbol)

        sym = trade.symbol
        pip_val = 0.01 if "JPY" in sym else (1.0 if sym in ("XAUUSD","US30","NAS100","US500") else 0.0001)
        if trade.direction == "BUY":
            pnl_pips = (close_price - entry) / pip_val
        else:
            pnl_pips = (entry - close_price) / pip_val
        # USD value per pip per lot — JPY pairs need /rate correction
        _pip_usd = {
            "XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
            "USDJPY": 6.5,  "EURJPY": 6.5,  "GBPJPY": 6.5,  "AUDJPY": 6.5,
            "CHFJPY": 6.5,  "CADJPY": 6.5,  "NZDJPY": 6.5,
            "USDCHF": 11.0, "EURCHF": 11.0, "GBPCHF": 11.0,
            "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25,
        }
        pip_value_usd = _pip_usd.get(sym, 10.0)  # default $10/pip/lot for USD-quote pairs
        pnl_usd = pnl_pips * pip_value_usd * (trade.lot_size or 1)

        result_str = "WIN" if pnl_usd > 0 else ("LOSS" if pnl_usd < 0 else "BREAKEVEN")

        async with async_session_factory() as s:
            trade_obj = await s.get(Trade, trade.id)
            if trade_obj:
                trade_obj.status      = "CLOSED"
                trade_obj.close_price = close_price
                trade_obj.close_time  = datetime.utcnow()
                trade_obj.pnl_pips    = round(pnl_pips, 1)
                trade_obj.pnl_usd     = round(pnl_usd, 2)
                trade_obj.result      = result_str
                await s.commit()

        # Journal close
        jr_entry = await self.jr.journal_trade_close(
            {"id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
             "entry_price": trade.entry_price, "stop_loss": trade.stop_loss,
             "take_profit_1": trade.take_profit_1, "lot_size": trade.lot_size,
             "ict_setup": trade.ict_setup, "trailing_sl_updates": trade.trailing_sl_updates},
            close_price, pnl_usd, reason,
        )
        await self._save_journal(trade.id, "TRADE_CLOSE", jr_entry)

        # Update performance stats + strategy memory (continuous learning)
        await self._update_performance_stats(result_str, pnl_pips)
        asyncio.create_task(_mem_update_trade(trade.ict_setup or "Unknown", trade.symbol, pnl_usd, result_str))

        # Rule-engine feedback: update accuracy of learning_rules that matched this trade
        try:
            rules_applied_json = trade_obj.rules_applied if trade_obj else None
            if rules_applied_json:
                rule_ids = json.loads(rules_applied_json)
                if rule_ids:
                    from services.rule_engine import validate_after_trade
                    asyncio.create_task(validate_after_trade(trade.id, rule_ids, result_str))
        except Exception as exc:
            logger.warning("Rule feedback update failed: %s", exc)

        await self.broadcast({
            "type": "trade_closed",
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "result": result_str,
            "pnl_usd": pnl_usd,
            "pnl_pips": pnl_pips,
            "reason": reason,
        })
        await self._notify("notify_trade_close",
            {
                "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                "entry_price": trade.entry_price, "close_price": close_price,
                "ict_setup": trade.ict_setup, "result": result_str,
            },
            pnl_usd, pnl_pips, reason,
        )

        # Trigger post-trade meeting (debounced — waits 30s to batch multiple closes)
        if not hasattr(self, '_pending_meeting_trades'):
            self._pending_meeting_trades = []
            self._meeting_debounce_task = None
        self._pending_meeting_trades.append(trade)
        if self._meeting_debounce_task is None or self._meeting_debounce_task.done():
            self._meeting_debounce_task = asyncio.create_task(self._debounced_meeting())

    async def _debounced_meeting(self):
        """Wait 30s to batch multiple trade closes into one meeting."""
        await asyncio.sleep(30)
        trades = list(self._pending_meeting_trades)
        self._pending_meeting_trades.clear()
        if trades:
            await self.run_meeting("POST_TRADE", trades)

    # ------------------------------------------------------------------ #
    #  Meeting & Self-Improvement
    # ------------------------------------------------------------------ #

    async def run_meeting(self, meeting_type: str = "POST_TRADE", trades: list | None = None):
        async with async_session_factory() as s:
            config = await self._load_config(s)
            perf_raw = await get_config("system_performance", s)
            perf = json.loads(perf_raw or "{}")

            if trades is None:
                result = await s.execute(
                    select(Trade).where(Trade.status == "CLOSED").order_by(Trade.close_time.desc()).limit(20)
                )
                trades = result.scalars().all()

        trade_dicts = []
        for t in trades:
            if hasattr(t, "__dict__"):
                trade_dicts.append({
                    k: v for k, v in t.__dict__.items()
                    if not k.startswith("_")
                })
            else:
                trade_dicts.append(t)

        # Load current strategy memory to include in meeting context
        current_memory = await _build_memory()

        # Build "what happened after close" context for KILLZONE_REVIEW
        post_ctx = await self._build_post_trade_context(trade_dicts) if meeting_type == "KILLZONE_REVIEW" else ""

        meeting_result = await self.jr.conduct_meeting(
            meeting_type, trade_dicts, perf, config,
            current_memory=current_memory,
            post_trade_context=post_ctx,
        )

        # Apply system improvements to config
        improvements = meeting_result.get("system_improvements", [])
        if improvements:
            await self._apply_improvements(improvements)

        # Apply strategy memory updates — this is the continuous learning core
        memory_updates = meeting_result.get("setup_memory_updates", [])
        if memory_updates:
            await _mem_update_meeting(memory_updates)
            logger.info("Strategy memory updated: %d setup entries from %s", len(memory_updates), meeting_type)

        # Save meeting to DB
        async with async_session_factory() as s:
            meeting = Meeting(
                meeting_type=meeting_type,
                trigger="Scheduled" if meeting_type == "WEEKLY_REVIEW" else "Post-Trade",
                participants="ICTEA,RM,TR,AT,JR",
                agenda=f"{meeting_type} review",
                summary=meeting_result.get("content", ""),
                conclusions=json.dumps(meeting_result.get("conclusions", [])),
                improvements=json.dumps(improvements),
                status="COMPLETED",
                completed_at=datetime.utcnow(),
            )
            s.add(meeting)
            await s.commit()

            # Ingest proposed_rules from meeting — new learning pipeline
            proposed = meeting_result.get("proposed_rules", [])
            if proposed:
                try:
                    from services.learning_rules import ingest_proposed_rules
                    ids = await ingest_proposed_rules(proposed, source_type="MEETING",
                                                        source_id=meeting.id)
                    logger.info("Ingested %d learning rules from meeting #%d",
                                len(ids), meeting.id)
                except Exception as exc:
                    logger.warning("Rule ingest failed: %s", exc)

            je = JournalEntry(
                meeting_id=meeting.id,
                entry_type="MEETING_SUMMARY",
                content=json.dumps(meeting_result),
                created_at=datetime.utcnow(),
            )
            s.add(je)
            await s.commit()

        await self.broadcast({
            "type": "meeting_summary",
            "meeting_type": meeting_type,
            "improvements": improvements,
            "conclusions": meeting_result.get("conclusions", []),
        })
        if self._tg and (improvements or meeting_result.get("conclusions")):
            asyncio.create_task(self._tg.notify_meeting(
                meeting_type,
                meeting_result.get("conclusions", []),
                improvements,
            ))

        return meeting_result

    async def _build_post_trade_context(self, trade_dicts: list) -> str:
        """For each closed trade, fetch a few candles AFTER close to see if more profit was available."""
        lines = []
        for t in trade_dicts[-8:]:  # last 8 trades only to keep context size manageable
            if not t.get("close_price") or not t.get("close_time"):
                continue
            sym     = t.get("symbol", "")
            entry   = t.get("entry_price", 0)
            close_p = t.get("close_price", 0)
            tp1     = t.get("take_profit_1")
            tp2     = t.get("take_profit_2")
            direction = t.get("direction", "BUY")
            result  = t.get("result", "?")
            try:
                data = await fetch_ohlcv(sym, "H1", 5)
                current = data.get("indicators", {}).get("current_price", 0)
                if current and close_p and entry:
                    pip = 0.01 if "JPY" in sym else (1.0 if sym in ("XAUUSD","US30","NAS100","US500") else 0.0001)
                    pips_after = (current - close_p) / pip if direction == "BUY" else (close_p - current) / pip
                    continued = pips_after > 0
                    lines.append(
                        f"#{t.get('id')} {sym} {direction} {result}: "
                        f"Closed @{close_p} | After close price moved "
                        f"{'FURTHER in trade direction' if continued else 'AGAINST trade direction'} "
                        f"({abs(pips_after):.1f} pips) | "
                        f"TP1={tp1} TP2={tp2}"
                    )
            except Exception:
                pass
        return "\n".join(lines) if lines else ""

    # ------------------------------------------------------------------ #
    #  Interactive Emergency Meeting
    # ------------------------------------------------------------------ #
    async def start_interactive_meeting(self, topic: str):
        """Launch an interactive emergency meeting with per-agent responses."""
        if self._active_meeting:
            return {"error": "A meeting is already in progress"}

        self._active_meeting = {
            "topic": topic,
            "transcript": [],
            "user_queue": asyncio.Queue(),
            "round": 0,
        }

        # Load context — both closed AND open trades
        async with async_session_factory() as s:
            config   = await self._load_config(s)
            perf_raw = await get_config("system_performance", s)
            perf     = json.loads(perf_raw or "{}")
            # Closed trades (last 20)
            result   = await s.execute(
                select(Trade).where(Trade.status == "CLOSED")
                    .order_by(Trade.close_time.desc()).limit(20)
            )
            closed_trades = result.scalars().all()
            # Open/active trades
            result = await s.execute(
                select(Trade).where(Trade.status.in_(["ACTIVE", "PROPOSED", "APPROVED"]))
            )
            open_trades = result.scalars().all()
            trades = list(open_trades) + list(closed_trades)

        try:
            final = await self.jr.emergency_meeting_interactive(
                topic=topic,
                trades=trades,
                performance_stats=perf,
                system_config=config,
                agents={"ICTEA": self.ictea, "RM": self.rm, "TR": self.tr, "AT": self.at},
                meeting_state=self._active_meeting,
            )
            # Debug: log verdict content
            logger.info(f"[MEETING] Verdict keys: {list(final.keys())}")
            logger.info(f"[MEETING] conclusions: {final.get('conclusions', 'MISSING')}")
            logger.info(f"[MEETING] system_improvements: {final.get('system_improvements', 'MISSING')}")
            if "error" in final:
                logger.error(f"[MEETING] Verdict parse error! raw: {final.get('raw', '')[:500]}")

            # Apply improvements
            improvements = final.get("system_improvements", [])
            if improvements:
                await self._apply_improvements(improvements)
            # Save meeting to DB — use all possible key variations
            conclusions = final.get("conclusions") or final.get("conclusion") or final.get("verdict") or []
            if isinstance(conclusions, str):
                conclusions = [conclusions]
            async with async_session_factory() as s:
                meeting = Meeting(
                    meeting_type="EMERGENCY",
                    trigger="User (Interactive)",
                    participants="ICTEA,RM,TR,AT,JR",
                    agenda=topic[:500],
                    summary=json.dumps(conclusions, default=str),
                    improvements=json.dumps(improvements, default=str),
                    created_at=datetime.now(ZoneInfo("Europe/Rome")),
                )
                s.add(meeting)
                await s.flush()  # get meeting.id
                # Create journal entry for the meeting
                journal_content = f"Emergency Meeting: {topic[:200]}\n\n"
                journal_content += "Conclusioni:\n"
                for c in conclusions:
                    journal_content += f"• {c}\n"
                if improvements:
                    journal_content += "\nImprovements:\n"
                    for imp in improvements:
                        journal_content += f"• [{imp.get('category', '')}] {imp.get('improvement', '')}\n"
                journal = JournalEntry(
                    meeting_id=meeting.id,
                    entry_type="MEETING_SUMMARY",
                    content=journal_content,
                    metrics=json.dumps({
                        "conclusions_count": len(conclusions),
                        "improvements_count": len(improvements),
                        "rounds": self._active_meeting.get("round", 1) if self._active_meeting else 1,
                    }, default=str),
                    created_at=datetime.now(ZoneInfo("Europe/Rome")),
                )
                s.add(journal)
                await s.commit()
            logger.info(f"[MEETING] Saved to DB: {len(conclusions)} conclusions, {len(improvements)} improvements")
            # Update strategy memory
            mem_updates = final.get("setup_memory_updates") or final.get("memory_updates") or []
            if mem_updates:
                await _mem_update_meeting(mem_updates)
        except Exception as exc:
            logger.error("Interactive meeting failed: %s", exc, exc_info=True)
            await self.broadcast({"type": "error", "message": f"Meeting failed: {exc}"})
            # Don't silently close — broadcast explicit meeting_completed so frontend knows
            await self.broadcast({
                "type": "meeting_completed",
                "meeting_type": "EMERGENCY",
                "conclusions": [f"Meeting terminated due to error: {exc}"],
                "improvements": [],
                "error": True,
                "timestamp": datetime.utcnow().isoformat(),
            })
        finally:
            self._active_meeting = None

    def send_meeting_message(self, text: str):
        """Queue a user message for the active meeting."""
        if self._active_meeting:
            self._active_meeting["user_queue"].put_nowait(text)

    def approve_meeting_close(self):
        """Signal that the user approves the meeting verdict."""
        if self._active_meeting:
            self._active_meeting["user_queue"].put_nowait("__APPROVE__")

    # Keys that must contain valid JSON arrays/objects
    _JSON_CONFIG_KEYS = frozenset({
        "enabled_pairs", "kill_zones", "ict_strategies", "system_performance",
        "paper_mode_exit_criteria", "trading_sessions",
    })
    # Keys that must be numeric
    _NUMERIC_CONFIG_KEYS = frozenset({
        "risk_percent", "rr_ratio", "max_open_trades", "account_balance",
        "analysis_interval", "max_risk_usd", "min_sl_pips", "paper_balance",
        "news_block_minutes_before", "news_block_minutes_after",
        "max_consecutive_losses", "trade_max_duration_hours",
        # RM self-adapting parameters (meetings propose changes, auto-applied)
        "rm_min_sl_atr_mult", "rm_max_tp_atr_mult", "rm_min_rr_gate",
        "rm_sl_cap_atr_mult", "rm_min_sl_pips_floor", "max_trade_duration_hours",
    })
    # Keys that agents are NOT allowed to change (user-only).
    # HARD INVARIANT: max_risk_usd and risk_percent are the only risk-capital
    # parameters. They are the contract between the trader and the system:
    # "you can optimize everything but never risk more per trade than this."
    # No meeting, no rule, no agent can mutate these.
    _PROTECTED_CONFIG_KEYS = frozenset({
        "mt5_login", "mt5_password", "mt5_server", "oanda_api_key",
        "oanda_practice", "mt5_bridge_url", "paper_mode", "model_mode",
        "max_risk_usd", "risk_percent",
    })

    def _validate_config_change(self, key: str, val: str) -> str | None:
        """Return rejection reason if the proposed config change is invalid, else None."""
        if key in self._PROTECTED_CONFIG_KEYS:
            return f"Key '{key}' is protected and cannot be changed by agents"
        if key in self._JSON_CONFIG_KEYS:
            try:
                parsed = json.loads(val)
                if not isinstance(parsed, (list, dict)):
                    return f"Key '{key}' requires a JSON array/object, got {type(parsed).__name__}"
            except (json.JSONDecodeError, TypeError):
                return f"Key '{key}' requires valid JSON, got: {val[:80]}"
            return None
        if key in self._NUMERIC_CONFIG_KEYS:
            try:
                float(val)
            except (ValueError, TypeError):
                return f"Key '{key}' requires a number, got: {val[:80]}"
            return None
        # Unknown key — the meeting invented a name that does not exist.
        # We surface this loudly so it's obvious the proposal had zero effect.
        return f"Key '{key}' is not a recognized tunable parameter (whitelist only). If you want per-symbol/per-setup logic, emit a proposed_rule instead."

    async def _apply_improvements(self, improvements: list):
        """Apply system config changes proposed by JR — with validation.
        Pre-filter: entries without a valid config_change are counted but
        discarded without noise. We log a single summary line per meeting
        so it's clear how many of the proposed improvements actually took
        effect (vs how many were narrative-only)."""
        applied = 0
        discarded_no_change = 0
        rejected_invalid = 0
        async with async_session_factory() as s:
            for imp in improvements:
                change = imp.get("config_change") or {}
                if not change or not change.get("key") or change.get("new_value") is None:
                    discarded_no_change += 1
                    continue
                key = change["key"]
                val = str(change["new_value"])
                rejection = self._validate_config_change(key, val)
                if rejection:
                    rejected_invalid += 1
                    logger.warning("Improvement REJECTED: %s=%s — %s", key, val[:80], rejection)
                    await self.broadcast({
                        "type": "config_update_rejected",
                        "key": key, "value": val[:100], "reason": rejection,
                    })
                    continue
                await set_config(key, val, s)
                applied += 1
                await self.broadcast({
                    "type": "config_updated",
                    "key": key, "value": val,
                    "reason": imp.get("improvement", ""),
                })
                logger.info("System improvement applied: %s = %s", key, val)
        logger.info(
            "Meeting improvements summary: %d applied, %d narrative-only discarded, %d rejected",
            applied, discarded_no_change, rejected_invalid,
        )

    # ------------------------------------------------------------------ #
    #  Manual Actions
    # ------------------------------------------------------------------ #
    async def trigger_analysis(self, symbol: str | None = None):
        """Manually trigger analysis for one or all pairs."""
        async with async_session_factory() as s:
            pairs_raw = await get_config("enabled_pairs", s)
            config    = await self._load_config(s)
            open_count = await self._count_open_trades(s)

        pairs = [symbol] if symbol else json.loads(pairs_raw or '["EURUSD"]')
        for p in pairs:
            await self._analyze_and_trade(p, config, open_count)

    async def close_trade_manually(self, trade_id: int, reason: str = "Manual close"):
        async with async_session_factory() as s:
            trade = await s.get(Trade, trade_id)
            if not trade or trade.status != "ACTIVE":
                return {"error": "Trade not found or not active"}

        data = await fetch_ohlcv(trade.symbol, "H1", 5)
        close_price = data.get("indicators", {}).get("current_price", trade.entry_price)
        await self._append_close_note(trade_id, f"Chiuso manualmente @ {close_price:.5f}")
        await self._close_trade(trade, close_price, reason)
        return {"success": True}

    async def lock_profit(self, trade_id: int) -> dict:
        """Lock profit: close the TP1 position and move SL to breakeven on remaining positions."""
        async with async_session_factory() as s:
            trade = await s.get(Trade, trade_id)
            if not trade or trade.status != "ACTIVE":
                return {"error": "Trade not found or not active"}

        sym = trade.symbol or ""
        pip = 0.01 if "JPY" in sym else (1.0 if sym in ("XAUUSD","US30","NAS100","US500") else 0.0001)
        entry = trade.entry_price or 0
        buffer = 3 * pip  # 3 pips above entry for BUY, below for SELL

        if trade.direction == "BUY":
            new_sl = round(entry + buffer, 6)
        else:
            new_sl = round(entry - buffer, 6)

        tickets = [t.strip() for t in (trade.mt5_ticket or "").split(",") if t.strip()]

        if len(tickets) >= 2:
            # Split mode: close first ticket (TP1 position), move SL on the rest
            tp1_ticket = tickets[0]
            remaining_tickets = tickets[1:]

            # 1. Close the TP1 position entirely
            await self.cc.close_trade(tp1_ticket, sym)
            await self._append_close_note(trade_id, f"Lock profit: chiusa posizione TP1 (ticket #{tp1_ticket})")
            await self.broadcast({"type": "partial_close", "trade_id": trade_id, "percent": 0.50})

            # 2. Move SL to breakeven on remaining positions
            for t in remaining_tickets:
                await self.cc.modify_sl(t, new_sl, sym)
            await self._update_trade_sl(trade_id, new_sl)

            # Update stored tickets (remove the closed one)
            await self._update_trade_ticket(trade_id, ",".join(remaining_tickets))
            await self._consume_next_tp(trade_id)

            await self._append_close_note(trade_id,
                f"Lock profit: SL spostato a entry+3pip ({new_sl:.5f}) su {len(remaining_tickets)} posizioni rimanenti")
            logger.info("Lock profit on trade #%d: closed TP1 ticket #%s, SL → %.5f on %s",
                        trade_id, tp1_ticket, new_sl, remaining_tickets)
        else:
            # Legacy single-ticket mode: partial close + move SL
            ticket = tickets[0] if tickets else ""
            pct = 0.50
            await self.cc.close_partial(ticket, sym, pct)
            await self._append_close_note(trade_id, f"Lock profit: chiuso {int(pct*100)}% della posizione")
            await self.broadcast({"type": "partial_close", "trade_id": trade_id, "percent": pct})

            await self.cc.modify_sl(ticket, new_sl, sym)
            await self._update_trade_sl(trade_id, new_sl)
            logger.info("Lock profit on trade #%d (single ticket): closed %d%%, SL → %.5f",
                        trade_id, int(pct*100), new_sl)

        if self._paper:
            self._paper.modify_sl(trade_id, new_sl)

        await self.broadcast({
            "type": "sl_trailed", "trade_id": trade_id,
            "symbol": sym, "new_sl": new_sl, "reason": "Lock profit (manual)",
        })

        return {"success": True, "new_sl": new_sl}

    async def modify_tps(self, trade_id: int, tp1=None, tp2=None, tp3=None) -> dict:
        """Update TP levels for an active trade."""
        async with async_session_factory() as s:
            trade = await s.get(Trade, trade_id)
            if not trade or trade.status != "ACTIVE":
                return {"error": "Trade not found or not active"}

            updated = []
            if tp1 is not None:
                trade.take_profit_1 = float(tp1)
                updated.append(f"TP1={tp1}")
            if tp2 is not None:
                trade.take_profit_2 = float(tp2)
                updated.append(f"TP2={tp2}")
            if tp3 is not None:
                trade.take_profit_3 = float(tp3)
                updated.append(f"TP3={tp3}")
            await s.commit()

        await self._append_close_note(trade_id, f"TP modificati manualmente: {', '.join(updated)}")
        logger.info("TPs modified on trade #%d: %s", trade_id, ", ".join(updated))
        return {"success": True, "updated": updated}

    @property
    def news_filter(self) -> NewsFilter | None:
        return self._news

    @property
    def telegram(self) -> TelegramBot | None:
        return self._tg

    async def get_status(self) -> dict:
        async with async_session_factory() as s:
            open_trades = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
            open_list = open_trades.scalars().all()
            closed = await s.execute(select(Trade).where(Trade.status == "CLOSED"))
            closed_list = closed.scalars().all()
            config = await self._load_config(s)
            perf_raw = await get_config("system_performance", s)

        paper_summary = self._paper.get_summary() if self._paper else {}
        paper_on      = config.get("paper_mode", "false") == "true"
        return {
            "running":      self._running,
            "open_trades":  len(open_list),
            "closed_trades":len(closed_list),
            "config":       config,
            "performance":  json.loads(perf_raw or "{}"),
            "paper_mode":   paper_on,
            "paper":        paper_summary,
        }

    # ------------------------------------------------------------------ #
    #  DB Helpers
    # ------------------------------------------------------------------ #
    async def _save_trade(self, symbol, strategy, rm_result, trade_params, ict_analysis, is_paper: bool = False) -> int:
        position = rm_result.get("position_size", {})
        rule_verdict = strategy.get("_rule_verdict") or {}
        async with async_session_factory() as s:
            trade = Trade(
                symbol=symbol,
                direction=trade_params.get("direction", strategy.get("direction")),
                status="ACTIVE",
                entry_price=trade_params.get("entry_price"),
                stop_loss=trade_params.get("stop_loss"),
                take_profit_1=trade_params.get("take_profit_1"),
                take_profit_2=trade_params.get("take_profit_2"),
                take_profit_3=trade_params.get("take_profit_3"),
                lot_size=position.get("lot_size", trade_params.get("lot_size", 0.01)),
                risk_percent=position.get("risk_percent", 1.0),
                rr_ratio=position.get("rr_ratio", 2.0),
                ict_setup=strategy.get("setup", "ICT"),
                ict_context=json.dumps(ict_analysis),
                risk_analysis=json.dumps(rm_result),
                analyst_verdict=json.dumps({}),
                open_time=datetime.utcnow(),
                is_paper=is_paper,
                market_context=json.dumps(strategy.get("_market_context") or {}),
                rules_applied=json.dumps(rule_verdict.get("rules_applied", [])),
            )
            s.add(trade)
            await s.commit()
            await s.refresh(trade)
            return trade.id

    async def _update_trade_ticket(self, trade_id: int, ticket: str):
        async with async_session_factory() as s:
            t = await s.get(Trade, trade_id)
            if t:
                t.mt5_ticket = ticket
                await s.commit()

    async def _consume_next_tp(self, trade_id: int):
        """After a partial close, increment tp_hits so AT won't re-trigger the same TP.
        Original TP prices are kept intact for UI display."""
        async with async_session_factory() as s:
            t = await s.get(Trade, trade_id)
            if not t:
                return
            t.tp_hits = (t.tp_hits or 0) + 1
            await s.commit()

    async def _append_close_note(self, trade_id: int, note: str):
        """Append a timestamped note to trade.close_notes for audit trail."""
        from datetime import datetime as _dt
        ts = _dt.utcnow().strftime("%H:%M")
        async with async_session_factory() as s:
            t = await s.get(Trade, trade_id)
            if t:
                existing = t.close_notes or ""
                t.close_notes = (existing + "\n" if existing else "") + f"[{ts}] {note}"
                await s.commit()

    async def _update_trade_sl(self, trade_id: int, new_sl: float):
        async with async_session_factory() as s:
            t = await s.get(Trade, trade_id)
            if t:
                t.stop_loss = new_sl
                t.trailing_sl_updates += 1
                await s.commit()

    async def _log_agent(self, agent: str, action: str, msg: str, data: dict, trade_id: int | None = None):
        async with async_session_factory() as s:
            log = AgentLog(
                trade_id=trade_id,
                agent_name=agent,
                action=action,
                message=msg,
                data=json.dumps(data),
                timestamp=datetime.utcnow(),
            )
            s.add(log)
            await s.commit()

    async def _save_journal(self, trade_id: int, entry_type: str, jr_result: dict):
        async with async_session_factory() as s:
            je = JournalEntry(
                trade_id=trade_id,
                entry_type=entry_type,
                content=jr_result.get("content", json.dumps(jr_result)),
                metrics=json.dumps(jr_result.get("key_metrics", {})),
                created_at=datetime.utcnow(),
            )
            s.add(je)
            await s.commit()

    async def _count_open_trades(self, s) -> int:
        result = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
        return len(result.scalars().all())

    async def _load_config(self, s) -> dict:
        from models.database import SystemConfig
        result = await s.execute(select(SystemConfig))
        rows = result.scalars().all()
        return {r.key: r.value for r in rows}

    async def _update_performance_stats(self, result: str, pnl_pips: float):
        async with async_session_factory() as s:
            raw = await get_config("system_performance", s)
            stats = json.loads(raw or "{}")
            stats["total_trades"] = stats.get("total_trades", 0) + 1
            if result == "WIN":
                stats["wins"] = stats.get("wins", 0) + 1
            elif result == "LOSS":
                stats["losses"] = stats.get("losses", 0) + 1
            else:
                stats["breakeven"] = stats.get("breakeven", 0) + 1
            total = stats["total_trades"]
            stats["win_rate"] = round(stats.get("wins", 0) / total * 100, 1) if total > 0 else 0
            await set_config("system_performance", json.dumps(stats), s)

    async def _is_paper_mode(self) -> bool:
        async with async_session_factory() as s:
            val = await get_config("paper_mode", s)
        return (val or "false").lower() == "true"

    def _enforce_lot_size(self, rm_result: dict, trade_params: dict, symbol: str, config: dict):
        """Compute lot size from max_risk_usd (fixed USD) or risk_percent (% of balance).
        Uses actual entry/SL from trade_params to compute sl_pips reliably (RM's sl_pips can be 0).
        Overwrites lot_size in both rm_result['position_size'] and trade_params."""
        try:
            max_risk_usd = float(config.get("max_risk_usd") or 0)
            balance      = float(config.get("account_balance") or 10000)
            risk_pct     = float(config.get("risk_percent") or 1.0)
            risk_usd     = max_risk_usd if max_risk_usd > 0 else balance * risk_pct / 100

            # Compute sl_pips from actual entry/SL prices — much more reliable than RM's LLM output
            entry = float(trade_params.get("entry_price") or 0)
            sl    = float(trade_params.get("stop_loss") or 0)
            if not entry or not sl:
                logger.warning("_enforce_lot_size: missing entry/SL for %s, skipping", symbol)
                return

            pip = 0.01 if "JPY" in symbol else (1.0 if symbol in ("XAUUSD", "XAGUSD", "US30", "NAS100", "US500") else 0.0001)
            sl_pips = abs(entry - sl) / pip
            if sl_pips <= 0:
                logger.warning("_enforce_lot_size: sl_pips=0 for %s (entry=%.5f sl=%.5f)", symbol, entry, sl)
                return

            _pip_usd = {"XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
                        "USDJPY": 6.5, "EURJPY": 6.5, "GBPJPY": 6.5, "AUDJPY": 6.5,
                        "CHFJPY": 6.5, "CADJPY": 6.5, "NZDJPY": 6.5,
                        "USDCHF": 11.0, "EURCHF": 11.0,
                        "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25}
            pip_usd = _pip_usd.get(symbol, 10.0)

            lot = max(0.01, round(risk_usd / (sl_pips * pip_usd), 2))
            pos = rm_result.setdefault("position_size", {})
            pos["lot_size"]  = lot
            pos["risk_usd"]  = round(risk_usd, 2)
            pos["sl_pips"]   = round(sl_pips, 1)
            pos["risk_mode"] = "fixed_usd" if max_risk_usd > 0 else "percent"
            trade_params["lot_size"] = lot  # ensure _save_trade picks up the enforced value
            logger.info("Lot enforced for %s: %.2f lots (risk $%.2f / %.1f pip SL @ entry %.5f sl %.5f)",
                        symbol, lot, risk_usd, sl_pips, entry, sl)
        except Exception as exc:
            logger.warning("_enforce_lot_size failed: %s", exc)

    def _enforce_rr(self, trade_params: dict, rm_result: dict, config: dict) -> dict:
        """Enforce correct TP ordering (TP1 < TP2 < TP3 distance from entry for BUY, inverted for SELL)
        and minimum RR on TP1. Fixes LLM-generated inverted or too-close TP levels."""
        try:
            direction = trade_params.get("direction", "")
            entry     = float(trade_params.get("entry_price") or 0)
            sl        = float(trade_params.get("stop_loss") or 0)
            if not entry or not sl:
                return trade_params

            symbol      = trade_params.get("symbol", "")
            pip         = 0.01 if "JPY" in symbol else (1.0 if symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)
            sl_pips     = abs(entry - sl) / pip
            required_rr = float(config.get("rr_ratio") or 2.0)
            sign        = 1 if direction == "BUY" else -1

            # TP1: use RM's tp1_pips (already ATR-calibrated) as the target
            tp1 = float(trade_params.get("take_profit_1") or 0)
            rm_tp1_pips = float((rm_result.get("position_size") or {}).get("tp1_pips") or 0)
            if tp1 and rm_tp1_pips > 0:
                tp1_pips = abs(entry - tp1) / pip
                # If TR's TP1 is too far or too close, use RM's value
                if tp1_pips > rm_tp1_pips * 1.3 or tp1_pips < sl_pips * 1.1:
                    tp1 = round(entry + sign * rm_tp1_pips * pip, 5)
                    trade_params = {**trade_params, "take_profit_1": tp1}
                    logger.info("RR enforced TP1 for %s %s → %.5f", symbol, direction, tp1)

            # TP2/TP3: must be further from entry than TP1 (in the correct direction)
            tp1_dist = abs(tp1 - entry) / pip if tp1 else rm_tp1_pips or sl_pips * 1.5
            for key, multiplier in [("take_profit_2", 1.5), ("take_profit_3", 2.0)]:
                tp = trade_params.get(key)
                if not tp:
                    continue
                tp = float(tp)
                tp_dist = abs(tp - entry) / pip
                # Wrong direction OR closer than TP1 → recompute
                correct_side = (tp > entry) if direction == "BUY" else (tp < entry)
                if not correct_side or tp_dist < tp1_dist - 0.05 * sl_pips:
                    tp = round(entry + sign * sl_pips * required_rr * multiplier * pip, 5)
                    trade_params = {**trade_params, key: tp}
                    logger.info("TP ordering enforced %s for %s %s → %.5f", key, symbol, direction, tp)
        except Exception:
            pass
        return trade_params

    async def _check_margin(self, symbol: str, trade_params: dict, rm_result: dict, config: dict, open_count: int = 0) -> bool:
        """Check MT5 margin before sending trade.
        Budget per trade = margin_free / remaining_slots.
        Reduces lot size if possible, rejects if not.
        Returns True if trade can proceed, False if rejected."""
        try:
            from services.mt5_direct import get_mt5_direct
            mt5 = get_mt5_direct()
            if not mt5.connected:
                return True  # can't check, let MT5 reject it naturally

            direction = trade_params.get("direction", "BUY")
            lots = float(trade_params.get("lot_size", 0.01))
            max_trades = int(config.get("max_open_trades", 3))

            result = mt5.check_margin(symbol, direction, lots)
            if result.get("simulated"):
                return True

            margin_free = result.get("margin_free", 0)
            equity = result.get("equity", margin_free)
            margin_req = result.get("margin_required", 0)
            leverage = result.get("leverage", 0)

            # Budget per trade = free margin / remaining slots
            # First trade: free/4, second: free/3, third: free/2, last: all free
            remaining_slots = max(1, max_trades - open_count)
            margin_budget = margin_free / remaining_slots

            # If margin_req is 0, order_check failed — estimate margin from budget
            if margin_req == 0 and lots > 0:
                # Estimate: cap lots so total margin stays within budget
                # Ava broker real margins: ~$8500/lot forex, ~$60000/lot gold
                est_per_lot = 60000 if "XAU" in symbol or "GOLD" in symbol.upper() else 8500
                max_lots_est = margin_budget / est_per_lot
                if max_lots_est < lots:
                    reduced = round(max(0.01, max_lots_est), 2)
                    logger.warning("Margin check returned $0 for %s — estimating. Reducing lots %.2f → %.2f (budget $%.0f)",
                                   symbol, lots, reduced, margin_budget)
                    trade_params["lot_size"] = reduced
                    pos = rm_result.setdefault("position_size", {})
                    pos["lot_size"] = reduced
                return True

            # Check against the per-trade budget, not total margin_free
            if margin_req <= margin_budget:
                logger.info("Margin OK: %s needs $%.0f, budget $%.0f (free $%.0f / %d trades, leva 1:%d)",
                            symbol, margin_req, margin_budget, margin_free, max_trades, leverage)
                return True

            # Over budget — scale down lots to fit
            if margin_req > 0:
                ratio = (margin_budget * 0.9) / margin_req  # 10% safety buffer
                reduced_lots = round(max(0.01, lots * ratio), 2)
            else:
                reduced_lots = 0

            if reduced_lots >= 0.01:
                logger.warning(
                    "Margin check: %s needs $%.0f margin but budget is $%.0f "
                    "(free $%.0f / %d trades, leva 1:%d). Reducing lots %.2f → %.2f",
                    symbol, margin_req, margin_budget, margin_free, max_trades, leverage, lots, reduced_lots,
                )
                trade_params["lot_size"] = reduced_lots
                pos = rm_result.setdefault("position_size", {})
                pos["lot_size"] = reduced_lots
                pos["margin_reduced"] = True
                await self.broadcast({
                    "type": "margin_warning", "symbol": symbol,
                    "message": (f"Lot ridotto da {lots} a {reduced_lots} — "
                                f"budget margine ${margin_budget:.0f} per trade "
                                f"(${margin_free:.0f} / {max_trades} trades, leva 1:{leverage})"),
                })
                return True
            else:
                logger.error(
                    "Margin check FAILED: %s needs $%.0f, budget $%.0f "
                    "(free $%.0f / %d trades, leva 1:%d). Cannot afford even 0.01 lots.",
                    symbol, margin_req, margin_budget, margin_free, max_trades, leverage,
                )
                await self.broadcast({
                    "type": "trade_rejected", "symbol": symbol,
                    "reason": (f"Margine insufficiente: serve ${margin_req:.0f}, "
                               f"budget ${margin_budget:.0f} per trade "
                               f"(${margin_free:.0f} / {max_trades} trades, leva 1:{leverage})"),
                    "agent": "SYS",
                })
                return False
        except Exception as exc:
            logger.warning("Margin check error (proceeding anyway): %s", exc)
            return True  # don't block on check errors

    def _sanity_check_trade(self, trade_params: dict, market_data: dict, config: dict | None = None) -> str | None:
        """Return rejection reason string if trade params are mathematically invalid, else None."""
        direction = trade_params.get("direction", "")
        entry     = float(trade_params.get("entry_price") or 0)
        sl        = float(trade_params.get("stop_loss") or 0)
        tp        = float(trade_params.get("take_profit_1") or 0)
        symbol    = trade_params.get("symbol", "")

        if not entry or not sl or not tp:
            return "Missing entry/SL/TP values"

        # Pip size per symbol
        pip = 0.01 if "JPY" in symbol else (1.0 if symbol in ("XAUUSD","US30","NAS100","US500") else 0.0001)

        sl_pips = abs(entry - sl) / pip
        tp_pips = abs(entry - tp) / pip

        # Min SL — multiplier on ATR driven by the tunable rm_min_sl_atr_mult
        # (was hardcoded 0.5). Halved coefficient kept as floor safety.
        atr_pips = float((market_data.get("H1") or {}).get("indicators", {}).get("atr_pips") or 0)
        cfg_min_sl = float((config or {}).get("min_sl_pips") or 30)
        min_sl_mult = float((config or {}).get("rm_min_sl_atr_mult") or 1.0)
        min_sl_pips = max(atr_pips * min_sl_mult * 0.5, cfg_min_sl)
        if sl_pips < min_sl_pips - 0.1:
            return f"SL too tight: {sl_pips:.1f} pips (min {min_sl_pips:.1f}, cfg_min={cfg_min_sl}p, {min_sl_mult*0.5}×ATR={atr_pips*min_sl_mult*0.5:.1f}p)"

        # Max TP1 distance driven by rm_max_tp_atr_mult (was hardcoded 2).
        max_tp_mult = float((config or {}).get("rm_max_tp_atr_mult") or 2.0)
        max_tp1_pips = atr_pips * max_tp_mult if atr_pips > 0 else 999
        if tp_pips > max_tp1_pips:
            return (f"TP1 too far for intraday: {tp_pips:.0f} pips "
                    f"(max {max_tp1_pips:.0f}p = {max_tp_mult}x ATR H1 {atr_pips:.0f}p)")

        # RR check — floor now driven by rm_min_rr_gate (was hardcoded 1.2).
        required_rr = float((config or {}).get("rr_ratio") or 2.0)
        rr_floor    = float((config or {}).get("rm_min_rr_gate") or 1.2)
        friction_pips = 1.5
        max_net_rr = (max_tp1_pips - friction_pips) / (sl_pips + friction_pips) if sl_pips > 0 else 0
        effective_rr = max(rr_floor, min(required_rr, max_net_rr))

        actual_rr = tp_pips / sl_pips if sl_pips else 0
        net_tp_pips = tp_pips - friction_pips
        net_sl_pips = sl_pips + friction_pips
        net_rr = net_tp_pips / net_sl_pips if net_sl_pips > 0 else 0
        if net_rr < effective_rr * 0.95:  # 5% tolerance — avoid rejecting trades that miss by 0.02-0.06
            return (f"Net RR {net_rr:.2f} below required {effective_rr:.2f} "
                    f"(gross RR={actual_rr:.2f}, friction={friction_pips}p, "
                    f"ATR-limited max RR={max_net_rr:.2f})")

        # Direction logic
        if direction == "BUY":
            if sl >= entry:
                return f"BUY: SL {sl} must be below entry {entry}"
            if tp <= entry:
                return f"BUY: TP {tp} must be above entry {entry}"
        elif direction == "SELL":
            if sl <= entry:
                return f"SELL: SL {sl} must be above entry {entry}"
            if tp >= entry:
                return f"SELL: TP {tp} must be below entry {entry}"

        # Current price must not already be past SL
        current = float((market_data.get("H1") or {}).get("indicators", {}).get("current_price") or 0)
        if current:
            if direction == "BUY"  and current <= sl:
                return f"Current price {current} already at/below SL {sl}"
            if direction == "SELL" and current >= sl:
                return f"Current price {current} already at/above SL {sl}"

        return None

    async def _get_config_value(self, key: str) -> str:
        async with async_session_factory() as s:
            return await get_config(key, s) or ""

    @property
    def paper_account(self) -> PaperAccount | None:
        return self._paper

    async def enable_paper_mode(self, balance: float | None = None):
        async with async_session_factory() as s:
            await set_config("paper_mode", "true", s)
            if balance is not None:
                await set_config("paper_balance", str(balance), s)
        if self._paper:
            if balance:
                self._paper.balance = balance
                self._paper.initial_balance = balance
            if not self._paper._running:
                await self._paper.start()

    async def disable_paper_mode(self):
        async with async_session_factory() as s:
            await set_config("paper_mode", "false", s)
        if self._paper:
            await self._paper.stop()

    @staticmethod
    async def _noop(msg: dict):
        pass
