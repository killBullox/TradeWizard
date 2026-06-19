"""
telegram_bot.py — Telegram notification + command bot for TradeWizard

Features
--------
- Push notifications: trade open/close, news block, meeting improvements,
  system errors
- Command handling via long-polling (no public URL needed) or webhook
- Commands: /start /help /status /trades /news /analyze [PAIR] /close <id>

Configuration (.env)
--------------------
TELEGRAM_BOT_TOKEN   = 123456789:ABCdef...
TELEGRAM_CHAT_ID     = -100xxxxxxxxxx   (group) or plain user id
TELEGRAM_POLLING     = true             (false = webhook only)
TELEGRAM_WEBHOOK_URL = https://your.domain/telegram/webhook  (optional)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, Optional

import httpx

logger = logging.getLogger("telegram_bot")

# ── Emoji shorthand ────────────────────────────────────────────────────────────
E = {
    "open":    "📈", "close":  "📉", "win":   "🏆", "loss":  "💔",
    "be":      "🤝", "news":   "📰", "block": "🚫", "meet":  "🗣️",
    "improve": "⚡", "warn":   "⚠️", "err":   "🚨", "ok":    "✅",
    "info":    "ℹ️", "robot":  "🤖", "chart": "📊", "lock":  "🔒",
    "search":  "🔍", "clock":  "⏰",
}


class TelegramBot:
    """
    Thin async Telegram Bot API wrapper + TradeWizard notification methods.
    Uses httpx directly — no python-telegram-bot dependency needed.
    """

    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(
        self,
        token: str,
        chat_id: str,
        orchestrator_ref: Any = None,   # set after orchestrator is created
    ):
        self.token   = token
        self.chat_id = str(chat_id)
        self._orc    = orchestrator_ref
        self._offset = 0
        self._polling_task: Optional[asyncio.Task] = None
        self._enabled = bool(token and chat_id)

        if not self._enabled:
            logger.info("Telegram bot disabled (no token/chat_id configured)")

    # ── Low-level API ─────────────────────────────────────────────────────────

    async def _call(self, method: str, **kwargs) -> dict:
        url = self.BASE.format(token=self.token, method=method)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(url, json=kwargs)
                return r.json()
        except Exception as exc:
            logger.warning("Telegram API error (%s): %s", method, exc)
            return {"ok": False, "error": str(exc)}

    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
    ) -> dict:
        if not self._enabled:
            return {"ok": False, "note": "disabled"}
        return await self._call(
            "sendMessage",
            chat_id=chat_id or self.chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_preview,
        )

    # ── Notification helpers ──────────────────────────────────────────────────

    async def notify_trade_open(self, trade: dict):
        direction = trade.get("direction", "?")
        arrow     = "🟢" if direction == "BUY" else "🔴"
        symbol    = trade.get("symbol", "?")
        setup     = trade.get("ict_setup") or trade.get("strategy", {}).get("setup", "ICT")
        entry     = _fmt_price(trade.get("entry_price"))
        sl        = _fmt_price(trade.get("stop_loss"))
        tp1       = _fmt_price(trade.get("take_profit_1"))
        tp2       = _fmt_price(trade.get("take_profit_2"))
        lot       = trade.get("lot_size", "?")
        rr        = trade.get("rr_ratio") or "?"
        tid       = trade.get("id", "?")
        ticket    = trade.get("mt5_ticket") or "SIM"
        order_type = trade.get("order_type", "MARKET")

        lines = [
            f"{E['open']} <b>TRADE OPENED</b>",
            f"",
            f"{arrow} <b>{symbol}</b> {direction}  |  #{tid}",
            f"<code>Setup    </code> {setup}",
            f"<code>Type     </code> {order_type}",
            f"<code>Entry    </code> {entry}",
            f"<code>SL       </code> {sl}",
            f"<code>TP1      </code> {tp1}",
        ]
        if tp2 and tp2 != "—":
            lines.append(f"<code>TP2      </code> {tp2}")
        lines += [
            f"<code>Lot      </code> {lot}",
            f"<code>R:R      </code> 1:{rr}",
            f"<code>Ticket   </code> {ticket}",
            f"",
            f"<i>{_utcnow()}</i>",
        ]
        await self.send_message("\n".join(lines))

    async def notify_trade_close(self, trade: dict, pnl_usd: float, pnl_pips: float, reason: str):
        result = trade.get("result", "UNKNOWN")
        symbol = trade.get("symbol", "?")
        tid    = trade.get("id", "?")
        entry  = _fmt_price(trade.get("entry_price"))
        close  = _fmt_price(trade.get("close_price"))
        setup  = trade.get("ict_setup", "ICT")

        if result == "WIN":
            icon, label = E["win"], "WIN"
        elif result == "LOSS":
            icon, label = E["loss"], "LOSS"
        else:
            icon, label = E["be"], "BREAKEVEN"

        pnl_sign = "+" if pnl_usd >= 0 else ""

        lines = [
            f"{icon} <b>TRADE CLOSED — {label}</b>",
            f"",
            f"<b>{symbol}</b> #{tid}  |  {setup}",
            f"<code>Entry    </code> {entry}  →  {close}",
            f"<code>P&amp;L USD </code> <b>{pnl_sign}{pnl_usd:.2f} $</b>",
            f"<code>P&amp;L Pips</code> {pnl_sign}{pnl_pips:.1f} pips",
            f"<code>Reason   </code> {reason}",
            f"",
            f"<i>{_utcnow()}</i>",
        ]
        await self.send_message("\n".join(lines))

    async def notify_news_block(self, event: dict, symbol: str):
        title    = event.get("title", "?")
        currency = event.get("currency", "?")
        impact   = event.get("impact", "High")
        t        = event.get("time", "")
        try:
            t_fmt = datetime.fromisoformat(t).strftime("%H:%M UTC")
        except Exception:
            t_fmt = t

        lines = [
            f"{E['news']} <b>NEWS BLOCK</b>",
            f"",
            f"Trading <b>{symbol}</b> suspended",
            f"<code>Event    </code> {title}",
            f"<code>Currency </code> {currency}",
            f"<code>Impact   </code> {impact}",
            f"<code>Time     </code> {t_fmt}",
        ]
        await self.send_message("\n".join(lines))

    async def notify_sl_trailed(self, symbol: str, trade_id: int, new_sl: float):
        lines = [
            f"📍 <b>STOP LOSS TRAILED</b>",
            f"",
            f"<b>{symbol}</b>  #{trade_id}",
            f"New SL → <code>{new_sl}</code>",
            f"<i>{_utcnow()}</i>",
        ]
        await self.send_message("\n".join(lines))

    async def notify_partial_close(self, symbol: str, trade_id: int, percent: float):
        lines = [
            f"💰 <b>PARTIAL CLOSE</b>  {percent:.0f}%",
            f"<b>{symbol}</b>  #{trade_id}",
            f"<i>{_utcnow()}</i>",
        ]
        await self.send_message("\n".join(lines))

    async def notify_meeting(self, meeting_type: str, conclusions: list, improvements: list):
        n_imp = len(improvements)
        lines = [
            f"{E['meet']} <b>MEETING COMPLETED — {meeting_type}</b>",
            f"",
        ]
        if conclusions:
            lines.append("<b>Conclusions:</b>")
            for c in conclusions[:5]:
                lines.append(f"• {_truncate(str(c), 120)}")
        if improvements:
            lines.append(f"")
            lines.append(f"{E['improve']} <b>{n_imp} improvement(s) applied</b>")
            for i in improvements[:3]:
                imp_text = i.get("improvement") or str(i)
                lines.append(f"• {_truncate(imp_text, 100)}")
        lines.append(f"")
        lines.append(f"<i>{_utcnow()}</i>")
        await self.send_message("\n".join(lines))

    async def notify_error(self, message: str):
        await self.send_message(
            f"{E['err']} <b>SYSTEM ERROR</b>\n\n<code>{_truncate(message, 300)}</code>\n\n<i>{_utcnow()}</i>"
        )

    async def send_status(self, status: dict, chat_id: str | None = None):
        cfg     = status.get("config", {})
        perf    = status.get("performance", {})
        open_n  = status.get("open_trades", 0)
        closed  = status.get("closed_trades", 0)
        wr      = perf.get("win_rate", 0)
        running = status.get("running", False)

        lines = [
            f"{E['robot']} <b>TradeWizard Status</b>",
            f"",
            f"{'🟢 Running' if running else '🔴 Stopped'}",
            f"<code>Open trades  </code> {open_n}",
            f"<code>Closed trades</code> {closed}",
            f"<code>Win rate     </code> {wr}%",
            f"<code>Balance      </code> ${cfg.get('account_balance','?')}",
            f"<code>Risk/trade   </code> {cfg.get('risk_percent','?')}%",
            f"<code>Max open     </code> {cfg.get('max_open_trades','?')}",
            f"",
            f"<i>{_utcnow()}</i>",
        ]
        await self.send_message("\n".join(lines), chat_id=chat_id)

    # ── Long-polling ──────────────────────────────────────────────────────────

    def start_polling(self):
        if not self._enabled:
            return
        if self._polling_task and not self._polling_task.done():
            return
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram polling started")

    def stop_polling(self):
        if self._polling_task:
            self._polling_task.cancel()

    async def _poll_loop(self):
        while True:
            try:
                result = await self._call(
                    "getUpdates",
                    offset=self._offset,
                    timeout=25,
                    allowed_updates=["message"],
                )
                if result.get("ok"):
                    for update in result.get("result", []):
                        self._offset = update["update_id"] + 1
                        await self._handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Polling error: %s", exc)
                await asyncio.sleep(5)

    async def _handle_update(self, update: dict):
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        text    = (msg.get("text") or "").strip()
        from_id = str(msg.get("from", {}).get("id", ""))
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text.startswith("/"):
            return

        # Parse command and args
        parts   = text.split()
        command = parts[0].split("@")[0].lower()  # strip @botname suffix
        args    = parts[1:]

        logger.info("Command %s from %s", command, from_id)

        try:
            await self._dispatch(command, args, chat_id)
        except Exception as exc:
            logger.error("Command handler error: %s", exc)
            await self.send_message(f"{E['err']} Error: {exc}", chat_id=chat_id)

    async def _dispatch(self, command: str, args: list, chat_id: str):
        orc = self._orc

        if command == "/start":
            await self.send_message(
                f"{E['robot']} <b>TradeWizard Bot</b>\n\n"
                "Multi-agent ICT forex trading system.\n\n"
                "<b>Commands:</b>\n"
                "/status — system overview\n"
                "/trades — open positions\n"
                "/news — next high-impact events\n"
                "/analyze [PAIR] — trigger analysis\n"
                "/close &lt;id&gt; — close a trade\n"
                "/help — this message",
                chat_id=chat_id,
            )

        elif command == "/help":
            await self._dispatch("/start", [], chat_id)

        elif command == "/status":
            if orc:
                status = await orc.get_status()
                await self.send_status(status, chat_id=chat_id)
            else:
                await self.send_message(f"{E['warn']} Orchestrator not ready", chat_id=chat_id)

        elif command == "/trades":
            if not orc:
                await self.send_message(f"{E['warn']} Orchestrator not ready", chat_id=chat_id)
                return
            status = await orc.get_status()
            open_n = status.get("open_trades", 0)
            if open_n == 0:
                await self.send_message(f"{E['info']} No open trades right now.", chat_id=chat_id)
                return
            # Fetch live trade list via DB
            from models.database import async_session_factory, Trade
            from sqlalchemy import select
            async with async_session_factory() as s:
                result = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
                trades = result.scalars().all()
            lines = [f"{E['chart']} <b>Open Trades ({len(trades)})</b>\n"]
            for t in trades:
                arrow = "🟢" if t.direction == "BUY" else "🔴"
                lines.append(
                    f"{arrow} <b>{t.symbol}</b> #{t.id} — {t.ict_setup or 'ICT'}\n"
                    f"   Entry: {_fmt_price(t.entry_price)}  SL: {_fmt_price(t.stop_loss)}  TP: {_fmt_price(t.take_profit_1)}\n"
                    f"   Lots: {t.lot_size}  |  Ticket: {t.mt5_ticket or 'SIM'}"
                )
            await self.send_message("\n".join(lines), chat_id=chat_id)

        elif command == "/news":
            if not orc or not orc.news_filter:
                await self.send_message(f"{E['warn']} News filter not ready", chat_id=chat_id)
                return
            events = await orc.news_filter.upcoming_events(hours_ahead=12)
            if not events:
                await self.send_message(f"{E['ok']} No high-impact events in the next 12h", chat_id=chat_id)
                return
            lines = [f"{E['news']} <b>Upcoming High-Impact Events</b>\n"]
            for e in events[:8]:
                t_fmt = e.time.strftime("%a %H:%M UTC")
                mins  = int((e.time - datetime.now(timezone.utc)).total_seconds() / 60)
                time_str = f"in {mins}m" if mins >= 0 else f"{-mins}m ago"
                lines.append(
                    f"• <b>{e.currency}</b> — {e.title}\n"
                    f"  {t_fmt} ({time_str})  [{e.impact}]"
                )
            await self.send_message("\n".join(lines), chat_id=chat_id)

        elif command == "/analyze":
            if not orc:
                await self.send_message(f"{E['warn']} Orchestrator not ready", chat_id=chat_id)
                return
            symbol = args[0].upper() if args else None
            asyncio.create_task(orc.trigger_analysis(symbol))
            label = symbol or "all pairs"
            await self.send_message(f"{E['search']} Analysis triggered for <b>{label}</b>", chat_id=chat_id)

        elif command == "/close":
            if not orc:
                await self.send_message(f"{E['warn']} Orchestrator not ready", chat_id=chat_id)
                return
            if not args:
                await self.send_message(f"{E['warn']} Usage: /close &lt;trade_id&gt;", chat_id=chat_id)
                return
            try:
                tid = int(args[0])
            except ValueError:
                await self.send_message(f"{E['warn']} Invalid trade ID", chat_id=chat_id)
                return
            result = await orc.close_trade_manually(tid, reason=f"Closed via Telegram by user {from_id if 'from_id' in dir() else '?'}")
            if result.get("success"):
                await self.send_message(f"{E['ok']} Trade #{tid} close requested.", chat_id=chat_id)
            else:
                await self.send_message(f"{E['err']} {result.get('error','Unknown error')}", chat_id=chat_id)

        else:
            await self.send_message(
                f"{E['warn']} Unknown command: <code>{command}</code>\nTry /help",
                chat_id=chat_id,
            )

    # ── Webhook support ───────────────────────────────────────────────────────

    async def handle_webhook_update(self, update: dict):
        """Call this from the FastAPI webhook endpoint."""
        await self._handle_update(update)

    async def set_webhook(self, url: str) -> dict:
        return await self._call("setWebhook", url=url)

    async def delete_webhook(self) -> dict:
        return await self._call("deleteWebhook")

    async def get_me(self) -> dict:
        return await self._call("getMe")

    # ── Test ping ─────────────────────────────────────────────────────────────

    async def send_test(self) -> dict:
        result = await self.send_message(
            f"{E['ok']} <b>TradeWizard connected!</b>\n\n"
            f"Bot is online and ready.\nSend /help to see available commands.\n\n"
            f"<i>{_utcnow()}</i>"
        )
        return result


# ── Utility ───────────────────────────────────────────────────────────────────

def _fmt_price(val) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.5f}"
    except (TypeError, ValueError):
        return str(val)


def _truncate(s: str, n: int) -> str:
    return s[:n] + "…" if len(s) > n else s


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── Singleton factory ─────────────────────────────────────────────────────────
_instance: Optional[TelegramBot] = None


def get_telegram_bot(orchestrator=None) -> TelegramBot:
    global _instance
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if _instance is None:
        _instance = TelegramBot(token=token, chat_id=chat_id, orchestrator_ref=orchestrator)
    elif orchestrator is not None:
        _instance._orc = orchestrator
    return _instance
