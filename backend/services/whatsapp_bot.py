"""
whatsapp_bot.py — WhatsApp notification + command bot via Twilio for TradeWizard

Features
--------
- Push notifications: trade open/close, system health, meetings, errors
- Command handling via Twilio webhook
- Commands: /status /trades /close <id> /analyze [PAIR] /help

Configuration (.env)
--------------------
TWILIO_ACCOUNT_SID   = ACxxxxxx
TWILIO_AUTH_TOKEN     = your_auth_token
TWILIO_WHATSAPP_FROM = whatsapp:+14155238886   (Twilio sandbox or dedicated number)
WHATSAPP_TO          = whatsapp:+39xxxxxxxxxx   (your WhatsApp number)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger("whatsapp_bot")

# ── Emoji shorthand ────────────────────────────────────────────────────────────
E = {
    "open":    "📈", "close":  "📉", "win":   "🏆", "loss":  "💔",
    "be":      "🤝", "news":   "📰", "block": "🚫", "meet":  "🗣️",
    "improve": "⚡", "warn":   "⚠️", "err":   "🚨", "ok":    "✅",
    "info":    "ℹ️", "robot":  "🤖", "chart": "📊", "lock":  "🔒",
    "search":  "🔍", "clock":  "⏰",
}


class WhatsAppBot:
    """
    Async WhatsApp bot via Twilio API + TradeWizard notification methods.
    Same interface as TelegramBot for easy drop-in replacement.
    """

    TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,       # whatsapp:+14155238886
        to_number: str,         # whatsapp:+39xxxxxxxxxx
        orchestrator_ref: Any = None,
    ):
        self.sid       = account_sid
        self.token     = auth_token
        self.from_num  = from_number
        self.to_num    = to_number
        self._orc      = orchestrator_ref
        self._enabled  = bool(account_sid and auth_token and from_number and to_number)

        if not self._enabled:
            logger.info("WhatsApp bot disabled (missing Twilio credentials)")

    # ── Low-level API ─────────────────────────────────────────────────────────

    async def send_message(self, text: str, to: str | None = None) -> dict:
        """Send a WhatsApp message via Twilio API."""
        if not self._enabled:
            return {"ok": False, "note": "disabled"}

        url = self.TWILIO_API.format(sid=self.sid)
        data = {
            "From": self.from_num,
            "To": to or self.to_num,
            "Body": text,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    url,
                    data=data,
                    auth=(self.sid, self.token),
                )
                result = r.json()
                if r.status_code in (200, 201):
                    logger.debug("WhatsApp message sent: %s", result.get("sid", "?"))
                    return {"ok": True, "sid": result.get("sid")}
                else:
                    logger.warning("Twilio error %d: %s", r.status_code, result.get("message", ""))
                    return {"ok": False, "error": result.get("message", str(r.status_code))}
        except Exception as exc:
            logger.warning("WhatsApp send error: %s", exc)
            return {"ok": False, "error": str(exc)}

    # ── Notification helpers ──────────────────────────────────────────────────

    async def notify_trade_open(self, trade: dict):
        direction = trade.get("direction", "?")
        arrow     = "🟢" if direction == "BUY" else "🔴"
        symbol    = trade.get("symbol", "?")
        setup     = trade.get("ict_setup") or trade.get("strategy", {}).get("setup", "ICT")
        entry     = _fmt_price(trade.get("entry_price"))
        sl        = _fmt_price(trade.get("stop_loss"))
        tp1       = _fmt_price(trade.get("take_profit_1"))
        lot       = trade.get("lot_size", "?")
        rr        = trade.get("rr_ratio") or "?"
        tid       = trade.get("id", "?")
        ticket    = trade.get("mt5_ticket") or "SIM"

        msg = (
            f"{E['open']} *TRADE OPENED*\n\n"
            f"{arrow} *{symbol}* {direction}  |  #{tid}\n"
            f"Setup: {setup}\n"
            f"Entry: {entry}\n"
            f"SL: {sl}\n"
            f"TP1: {tp1}\n"
            f"Lot: {lot}  |  R:R 1:{rr}\n"
            f"Ticket: {ticket}\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg)

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

        msg = (
            f"{icon} *TRADE CLOSED — {label}*\n\n"
            f"*{symbol}* #{tid}  |  {setup}\n"
            f"Entry: {entry}  →  {close}\n"
            f"P&L: *{pnl_sign}{pnl_usd:.2f} $* ({pnl_sign}{pnl_pips:.1f} pips)\n"
            f"Reason: {reason}\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg)

    async def notify_news_block(self, event: dict, symbol: str):
        title    = event.get("title", "?")
        currency = event.get("currency", "?")
        impact   = event.get("impact", "High")

        msg = (
            f"{E['news']} *NEWS BLOCK*\n\n"
            f"Trading *{symbol}* suspended\n"
            f"Event: {title}\n"
            f"Currency: {currency} | Impact: {impact}"
        )
        await self.send_message(msg)

    async def notify_sl_trailed(self, symbol: str, trade_id: int, new_sl: float):
        msg = f"📍 *SL TRAILED*\n*{symbol}* #{trade_id}\nNew SL → {new_sl}\n_{_utcnow()}_"
        await self.send_message(msg)

    async def notify_partial_close(self, symbol: str, trade_id: int, percent: float):
        msg = f"💰 *PARTIAL CLOSE* {percent:.0%}\n*{symbol}* #{trade_id}\n_{_utcnow()}_"
        await self.send_message(msg)

    async def notify_meeting(self, meeting_type: str, conclusions: list, improvements: list):
        lines = [f"{E['meet']} *MEETING COMPLETED — {meeting_type}*\n"]
        if conclusions:
            lines.append("*Conclusions:*")
            for c in conclusions[:5]:
                lines.append(f"• {_truncate(str(c), 120)}")
        if improvements:
            lines.append(f"\n{E['improve']} *{len(improvements)} improvement(s) applied*")
            for i in improvements[:3]:
                imp_text = i.get("improvement") or str(i)
                lines.append(f"• {_truncate(imp_text, 100)}")
        lines.append(f"\n_{_utcnow()}_")
        await self.send_message("\n".join(lines))

    async def notify_error(self, message: str):
        await self.send_message(
            f"{E['err']} *SYSTEM ERROR*\n\n{_truncate(message, 300)}\n\n_{_utcnow()}_"
        )

    # ── System / watchdog notifications ──────────────────────────────────────

    async def notify_system_down(self, component: str, details: str = ""):
        msg = (
            f"{E['err']} *SYSTEM DOWN*\n\n"
            f"Component: *{component}*\n"
            f"{details}\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg)

    async def notify_mt5_disconnected(self):
        await self.send_message(
            f"{E['warn']} *MT5 DISCONNECTED*\n\n"
            f"MT5 bridge is not responding.\n"
            f"Attempting reconnection...\n\n"
            f"_{_utcnow()}_"
        )

    async def notify_restart(self, component: str, reason: str = ""):
        msg = (
            f"🔄 *RESTART*\n\n"
            f"Component: *{component}*\n"
            f"Reason: {reason or 'Watchdog auto-restart'}\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg)

    async def notify_daily_summary(self, stats: dict):
        trades_today = stats.get("trades_today", 0)
        wins         = stats.get("wins_today", 0)
        losses       = stats.get("losses_today", 0)
        pnl          = stats.get("pnl_today", 0.0)
        balance      = stats.get("balance", 0.0)
        uptime       = stats.get("uptime_hours", 0)
        pnl_sign     = "+" if pnl >= 0 else ""

        msg = (
            f"{E['chart']} *DAILY SUMMARY*\n\n"
            f"Trades: {trades_today} ({wins}W / {losses}L)\n"
            f"P&L: *{pnl_sign}{pnl:.2f} $*\n"
            f"Balance: ${balance:,.2f}\n"
            f"Uptime: {uptime:.1f}h\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg)

    async def send_status(self, status: dict, to: str | None = None):
        cfg     = status.get("config", {})
        perf    = status.get("performance", {})
        open_n  = status.get("open_trades", 0)
        closed  = status.get("closed_trades", 0)
        wr      = perf.get("win_rate", 0)
        running = status.get("running", False)

        msg = (
            f"{E['robot']} *TradeWizard Status*\n\n"
            f"{'🟢 Running' if running else '🔴 Stopped'}\n"
            f"Open trades: {open_n}\n"
            f"Closed trades: {closed}\n"
            f"Win rate: {wr}%\n"
            f"Balance: ${cfg.get('account_balance', '?')}\n"
            f"Risk/trade: {cfg.get('risk_percent', '?')}%\n"
            f"Max open: {cfg.get('max_open_trades', '?')}\n\n"
            f"_{_utcnow()}_"
        )
        await self.send_message(msg, to=to)

    # ── Webhook command handler (for incoming WhatsApp messages via Twilio) ───

    async def handle_webhook(self, form_data: dict) -> str:
        """Handle incoming WhatsApp message from Twilio webhook. Returns TwiML response."""
        body = (form_data.get("Body") or "").strip()
        from_num = form_data.get("From", "")

        if not body.startswith("/"):
            return ""  # Ignore non-command messages

        parts = body.split()
        command = parts[0].lower()
        args = parts[1:]

        logger.info("WhatsApp command %s from %s", command, from_num)

        try:
            response = await self._dispatch(command, args)
            await self.send_message(response, to=from_num)
        except Exception as exc:
            logger.error("WhatsApp command error: %s", exc)
            await self.send_message(f"{E['err']} Error: {exc}", to=from_num)

        return ""  # Empty TwiML — we send the response directly via API

    async def _dispatch(self, command: str, args: list) -> str:
        orc = self._orc

        if command in ("/start", "/help"):
            return (
                f"{E['robot']} *TradeWizard Bot*\n\n"
                "Multi-agent ICT forex trading system.\n\n"
                "*Commands:*\n"
                "/status — system overview\n"
                "/trades — open positions\n"
                "/analyze [PAIR] — trigger analysis\n"
                "/close <id> — close a trade\n"
                "/help — this message"
            )

        elif command == "/status":
            if orc:
                status = await orc.get_status()
                cfg  = status.get("config", {})
                perf = status.get("performance", {})
                running = status.get("running", False)
                return (
                    f"{'🟢 Running' if running else '🔴 Stopped'}\n"
                    f"Open: {status.get('open_trades', 0)} | Closed: {status.get('closed_trades', 0)}\n"
                    f"Win rate: {perf.get('win_rate', 0)}%\n"
                    f"Balance: ${cfg.get('account_balance', '?')}"
                )
            return f"{E['warn']} Orchestrator not ready"

        elif command == "/trades":
            if not orc:
                return f"{E['warn']} Orchestrator not ready"
            from models.database import async_session_factory, Trade
            from sqlalchemy import select
            async with async_session_factory() as s:
                result = await s.execute(select(Trade).where(Trade.status == "ACTIVE"))
                trades = result.scalars().all()
            if not trades:
                return f"{E['info']} No open trades."
            lines = [f"{E['chart']} *Open Trades ({len(trades)})*\n"]
            for t in trades:
                arrow = "🟢" if t.direction == "BUY" else "🔴"
                lines.append(
                    f"{arrow} *{t.symbol}* #{t.id} — {t.ict_setup or 'ICT'}\n"
                    f"  Entry: {_fmt_price(t.entry_price)}  SL: {_fmt_price(t.stop_loss)}\n"
                    f"  Lots: {t.lot_size}"
                )
            return "\n".join(lines)

        elif command == "/analyze":
            if not orc:
                return f"{E['warn']} Orchestrator not ready"
            symbol = args[0].upper() if args else None
            asyncio.create_task(orc.trigger_analysis(symbol))
            return f"{E['search']} Analysis triggered for *{symbol or 'all pairs'}*"

        elif command == "/close":
            if not orc:
                return f"{E['warn']} Orchestrator not ready"
            if not args:
                return f"{E['warn']} Usage: /close <trade_id>"
            try:
                tid = int(args[0])
            except ValueError:
                return f"{E['warn']} Invalid trade ID"
            result = await orc.close_trade_manually(tid, reason="Closed via WhatsApp")
            if result.get("success"):
                return f"{E['ok']} Trade #{tid} close requested."
            return f"{E['err']} {result.get('error', 'Unknown error')}"

        return f"{E['warn']} Unknown command: {command}\nTry /help"

    # ── Test ping ─────────────────────────────────────────────────────────────

    async def send_test(self) -> dict:
        return await self.send_message(
            f"{E['ok']} *TradeWizard connected!*\n\n"
            f"WhatsApp bot is online and ready.\n"
            f"Send /help to see available commands.\n\n"
            f"_{_utcnow()}_"
        )


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
_instance: Optional[WhatsAppBot] = None


def get_whatsapp_bot(orchestrator=None) -> WhatsAppBot:
    global _instance
    sid       = os.getenv("TWILIO_ACCOUNT_SID", "")
    token     = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num  = os.getenv("TWILIO_WHATSAPP_FROM", "")
    to_num    = os.getenv("WHATSAPP_TO", "")
    if _instance is None:
        _instance = WhatsAppBot(
            account_sid=sid, auth_token=token,
            from_number=from_num, to_number=to_num,
            orchestrator_ref=orchestrator,
        )
    elif orchestrator is not None:
        _instance._orc = orchestrator
    return _instance
