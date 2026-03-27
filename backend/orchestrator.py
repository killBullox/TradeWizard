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
from sqlalchemy import select

from models.database import (
    async_session_factory, Trade, AgentLog, JournalEntry, Meeting,
    init_db, get_config, set_config,
)
from agents import (
    ICTAdvisorAgent, RiskManagerAgent, TraderAgent,
    TradeAnalystAgent, ConnectorAgent, JournalistAgent,
)
from services.forex_data import get_multi_timeframe_data, fetch_ohlcv
from services.news_filter import get_news_filter, NewsFilter
from services.telegram_bot import get_telegram_bot, TelegramBot
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
        self._paper: PaperAccount | None = None

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
            paper_bal = float(await get_config("paper_balance", s) or 10000.0)
        self._paper = get_paper_account(
            broadcast_fn=self.broadcast,
            initial_balance=paper_bal,
        )
        paper_on = (await self._get_config_value("paper_mode")) == "true"
        if paper_on:
            await self._paper.start()

        # Initialize Telegram bot
        self._tg = get_telegram_bot(orchestrator=self)
        polling  = os.getenv("TELEGRAM_POLLING", "true").lower() == "true"
        if polling:
            self._tg.start_polling()

        self._analysis_task = asyncio.create_task(self._analysis_loop())
        self._monitor_task  = asyncio.create_task(self._monitor_loop())
        await self.broadcast({"type": "system_started", "timestamp": datetime.utcnow().isoformat()})
        logger.info("Orchestrator started")

    async def stop(self):
        self._running = False
        if self._tg:
            self._tg.stop_polling()
        if self._paper:
            await self._paper.stop()
        for task in (self._analysis_task, self._monitor_task):
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
        """Check if current Rome time falls within any configured Kill Zone window."""
        async with async_session_factory() as s:
            raw = await get_config("kill_zones", s)

        # Default: London 07-11, NY 13-18 ora di Roma
        windows = [{"start": "07:00", "end": "11:00"}, {"start": "13:00", "end": "18:00"}]
        if raw:
            try:
                windows = json.loads(raw)
            except Exception:
                pass

        rome = datetime.now(ZoneInfo("Europe/Rome"))
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
        while self._running:
            if await self._in_kill_zone():
                try:
                    await self._run_analysis_cycle()
                except Exception as e:
                    logger.error(f"Analysis loop error: {e}", exc_info=True)
                    await self.broadcast({"type": "error", "message": str(e)})
            else:
                logger.info("Outside Kill Zone — skipping analysis cycle")
            await asyncio.sleep(await self._get_interval())

    async def _get_interval(self) -> int:
        async with async_session_factory() as s:
            val = await get_config("analysis_interval", s)
        return int(val or 3600)

    async def _run_analysis_cycle(self):
        async with async_session_factory() as s:
            pairs_raw  = await get_config("enabled_pairs", s)
            config     = await self._load_config(s)
            open_count = await self._count_open_trades(s)

        pairs = json.loads(pairs_raw or '["EURUSD","GBPUSD"]')

        await self.broadcast({
            "type": "analysis_cycle_started",
            "pairs": pairs,
            "timestamp": datetime.utcnow().isoformat(),
        })

        for symbol in pairs:
            if not self._running:
                break
            await self._analyze_and_trade(symbol, config, open_count)
            await asyncio.sleep(2)  # brief pause between pairs

    async def _analyze_and_trade(self, symbol: str, config: dict, open_count: int):
        try:
            # 0. News filter — block analysis if high-impact event is near
            if self._news:
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
                    if self._tg:
                        asyncio.create_task(self._tg.notify_news_block(event.to_dict(), symbol))
                    return

            # 1. Fetch market data
            market_data = await get_multi_timeframe_data(symbol)

            # 2. ICTEA Analysis
            ict_analysis = await self.ictea.analyze(symbol, market_data, config)
            await self._log_agent("ICTEA", "ANALYSIS", f"Analyzed {symbol}", ict_analysis)

            if ict_analysis.get("bias") == "NEUTRAL":
                await self.broadcast({"type": "skip", "symbol": symbol, "reason": "NEUTRAL bias"})
                return

            strategies = ict_analysis.get("strategies", [])
            if not strategies:
                return

            # Take highest-probability strategy
            strategy = max(strategies, key=lambda s: s.get("probability", 0))

            # 3. Risk Manager
            rm_result = await self.rm.evaluate(symbol, strategy, market_data, config, open_count)
            await self._log_agent("RM", "EVALUATION", f"Evaluated {symbol}", rm_result)

            if not rm_result.get("approved"):
                reason = rm_result.get("rejection_reason", "Rejected by RM")
                await self.broadcast({"type": "trade_rejected", "symbol": symbol, "reason": reason, "agent": "RM"})
                return

            # 4. Trader — generate precise parameters
            trade_params = await self.tr.generate_trade(symbol, strategy, rm_result, market_data)
            await self._log_agent("TR", "TRADE_GENERATED", f"Generated trade for {symbol}", trade_params)

            # 5. Trade Analyst — validate
            validation = await self.at.validate_trade(trade_params, strategy, market_data, config)
            await self._log_agent("AT", "VALIDATION", f"Validated {symbol}", validation)

            if not validation.get("approved"):
                reason = validation.get("rejection_reason", "Rejected by AT")
                await self.broadcast({"type": "trade_rejected", "symbol": symbol, "reason": reason, "agent": "AT"})
                return

            # Apply AT modifications if any
            final_trade = validation.get("final_trade", trade_params)
            if isinstance(final_trade, dict) and not final_trade.get("error"):
                trade_params = {**trade_params, **final_trade}

            # Hard mathematical sanity check — reject before execution if params are invalid
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
                await self._update_trade_ticket(trade_id, cc_result.get("ticket", "SIM"))

            # 8. Journalist — document
            analysis_chain = {
                "ictea": ict_analysis, "strategy": strategy,
                "risk": rm_result, "validation": validation,
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
            if self._tg:
                asyncio.create_task(self._tg.notify_trade_open({
                    **trade_params,
                    "id": trade_id,
                    "ict_setup": strategy.get("setup"),
                    "mt5_ticket": cc_result.get("ticket"),
                    "rr_ratio": rm_result.get("position_size", {}).get("rr_ratio", 2.0),
                }))

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
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
            await asyncio.sleep(60)

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

                decision = await self.at.manage_trade(
                    {
                        "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                        "entry_price": trade.entry_price, "stop_loss": trade.stop_loss,
                        "take_profit_1": trade.take_profit_1, "take_profit_2": trade.take_profit_2,
                        "take_profit_3": trade.take_profit_3, "lot_size": trade.lot_size,
                        "ict_setup": trade.ict_setup, "trailing_sl_updates": trade.trailing_sl_updates,
                    },
                    current_price,
                    {"H1": data},
                )

                action = decision.get("action", "HOLD")

                if action == "TRAIL_SL" and decision.get("new_stop_loss"):
                    new_sl = decision["new_stop_loss"]
                    await self.cc.modify_sl(trade.mt5_ticket or "", new_sl, trade.symbol)
                    await self._update_trade_sl(trade.id, new_sl)
                    await self.broadcast({
                        "type": "sl_trailed",
                        "trade_id": trade.id,
                        "symbol": trade.symbol,
                        "new_sl": new_sl,
                        "reason": decision.get("reason"),
                    })
                    if self._tg:
                        asyncio.create_task(self._tg.notify_sl_trailed(trade.symbol, trade.id, new_sl))

                elif action == "PARTIAL_CLOSE" and decision.get("close_percent"):
                    pct = decision["close_percent"]
                    await self.cc.close_partial(trade.mt5_ticket or "", trade.symbol, pct)
                    await self.broadcast({"type": "partial_close", "trade_id": trade.id, "percent": pct})
                    if self._tg:
                        asyncio.create_task(self._tg.notify_partial_close(trade.symbol, trade.id, pct))

                elif action in ("CLOSE_ALL", "CLOSE"):
                    await self._close_trade(trade, current_price, "AT Management Decision")

            except Exception as e:
                logger.error(f"Monitor error for trade {trade.id}: {e}")

    async def _close_trade(self, trade, close_price: float, reason: str):
        cc_result = await self.cc.close_trade(trade.mt5_ticket or "", trade.symbol)

        entry = trade.entry_price or 0
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

        # Update performance stats
        await self._update_performance_stats(result_str, pnl_pips)

        await self.broadcast({
            "type": "trade_closed",
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "result": result_str,
            "pnl_usd": pnl_usd,
            "pnl_pips": pnl_pips,
            "reason": reason,
        })
        if self._tg:
            asyncio.create_task(self._tg.notify_trade_close(
                {
                    "id": trade.id, "symbol": trade.symbol, "direction": trade.direction,
                    "entry_price": trade.entry_price, "close_price": close_price,
                    "ict_setup": trade.ict_setup, "result": result_str,
                },
                pnl_usd, pnl_pips, reason,
            ))

        # Trigger post-trade meeting
        asyncio.create_task(self._schedule_meeting("POST_TRADE", [trade]))

    # ------------------------------------------------------------------ #
    #  Meeting & Self-Improvement
    # ------------------------------------------------------------------ #
    async def _schedule_meeting(self, meeting_type: str, trades: list, delay: int = 5):
        await asyncio.sleep(delay)
        await self.run_meeting(meeting_type, trades)

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

        meeting_result = await self.jr.conduct_meeting(meeting_type, trade_dicts, perf, config)

        # Apply system improvements
        improvements = meeting_result.get("system_improvements", [])
        if improvements:
            await self._apply_improvements(improvements)

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

    async def _apply_improvements(self, improvements: list):
        """Apply system config changes proposed by JR."""
        async with async_session_factory() as s:
            for imp in improvements:
                change = imp.get("config_change", {})
                if change and change.get("key") and change.get("new_value") is not None:
                    key = change["key"]
                    val = str(change["new_value"])
                    await set_config(key, val, s)
                    await self.broadcast({
                        "type": "config_updated",
                        "key": key,
                        "value": val,
                        "reason": imp.get("improvement", ""),
                    })
                    logger.info(f"System improvement applied: {key} = {val}")

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
        await self._close_trade(trade, close_price, reason)
        return {"success": True}

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

        # Min SL = 0.5 × ATR (same logic as backtester)
        atr_pips = float((market_data.get("H1") or {}).get("indicators", {}).get("atr_pips") or 0)
        min_sl_pips = max(atr_pips * 0.5, pip * 10 / pip)  # at least 0.5 ATR, fallback 10 pips
        if sl_pips < min_sl_pips:
            return f"SL too tight: {sl_pips:.1f} pips (min {min_sl_pips:.1f} = 0.5×ATR)"

        # RR must meet configured minimum (default 2.0)
        required_rr = float((config or {}).get("rr_ratio") or 2.0)
        actual_rr   = tp_pips / sl_pips if sl_pips else 0
        if actual_rr < required_rr - 0.001:  # small tolerance for floating-point
            return f"RR {actual_rr:.2f} below required {required_rr} (SL={sl_pips:.1f}p TP={tp_pips:.1f}p)"

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
