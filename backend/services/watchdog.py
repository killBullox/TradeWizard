"""
watchdog.py — Independent process that monitors TradeWizard components and auto-restarts them.

Run as standalone:  python backend/services/watchdog.py
Install as service: install_watchdog.bat (uses nssm)

Monitors every 30 seconds:
  1. Backend API (/api/health)
  2. MT5 Bridge (/health)
  3. MT5 terminal process (terminal64.exe)

If a component fails 3 consecutive checks:
  - Restarts the component
  - Sends WhatsApp alarm
  - Logs the event

Configuration via env vars or .env file:
  WATCHDOG_INTERVAL     = 30       (seconds between checks)
  WATCHDOG_MAX_FAILURES = 3        (consecutive fails before restart)
  BACKEND_URL           = http://localhost:8000
  MT5_BRIDGE_URL        = http://localhost:5002
  MT5_TERMINAL_PATH     = C:\Program Files\MetaTrader 5\terminal64.exe
"""

import asyncio
import logging
import os
import sys
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Setup logging to file + console
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "watchdog.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("watchdog")

# ── Load .env if available ────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

# ── Configuration ─────────────────────────────────────────────────────────────
CHECK_INTERVAL     = int(os.getenv("WATCHDOG_INTERVAL", "30"))
MAX_FAILURES       = int(os.getenv("WATCHDOG_MAX_FAILURES", "3"))
BACKEND_URL        = os.getenv("BACKEND_URL", "http://localhost:8000")
MT5_BRIDGE_URL     = os.getenv("MT5_BRIDGE_URL", "http://localhost:5002")
MT5_TERMINAL_PATH  = os.getenv("MT5_TERMINAL_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

# Project root (for restart commands)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── WhatsApp alarm (direct Twilio call, independent of backend) ───────────────
TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM   = os.getenv("TWILIO_WHATSAPP_FROM", "")
WHATSAPP_TO   = os.getenv("WHATSAPP_TO", "")


async def _send_whatsapp(message: str):
    """Send WhatsApp message directly via Twilio API (independent of backend)."""
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, WHATSAPP_TO]):
        logger.warning("WhatsApp not configured — alarm not sent")
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, data={
                "From": TWILIO_FROM,
                "To": WHATSAPP_TO,
                "Body": message,
            }, auth=(TWILIO_SID, TWILIO_TOKEN))
            if r.status_code in (200, 201):
                logger.info("WhatsApp alarm sent")
            else:
                logger.warning("WhatsApp send failed: %d %s", r.status_code, r.text[:200])
    except Exception as exc:
        logger.error("WhatsApp send error: %s", exc)


# ── Health check functions ────────────────────────────────────────────────────

async def check_backend() -> tuple[bool, str]:
    """Check if TradeWizard backend is responding."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{BACKEND_URL}/api/health")
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "unknown")
                if status == "critical":
                    return False, f"Backend reports critical status: {data}"
                return True, f"Backend OK (status={status}, uptime={data.get('uptime_seconds', '?')}s)"
            return False, f"Backend returned HTTP {r.status_code}"
    except Exception as exc:
        return False, f"Backend unreachable: {exc}"


async def check_mt5_connection() -> tuple[bool, str]:
    """Check if MT5 is connected via the backend health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{BACKEND_URL}/api/health")
            if r.status_code == 200:
                data = r.json()
                mt5_status = data.get("mt5", {})
                if isinstance(mt5_status, dict) and mt5_status.get("connected"):
                    return True, "MT5 connected (direct)"
                return False, f"MT5 not connected: {mt5_status}"
            return False, f"Backend returned HTTP {r.status_code}"
    except Exception as exc:
        return False, f"Cannot check MT5: {exc}"


def check_mt5_terminal() -> tuple[bool, str]:
    """Check if MT5 terminal process is running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        if "terminal64.exe" in result.stdout:
            return True, "MT5 terminal running"
        return False, "MT5 terminal not running"
    except Exception as exc:
        return False, f"Cannot check MT5 terminal: {exc}"


# ── Restart functions ─────────────────────────────────────────────────────────

def restart_backend():
    """Kill only the TradeWizard backend process (not all Python) and restart via schtasks."""
    logger.info("Restarting backend...")
    try:
        # Kill ONLY python processes running TradeWizard's main.py
        # Use full project path to avoid killing TradeMachine or other apps
        tw_path = str(PROJECT_ROOT).replace("\\", "\\\\")
        wmic_filter = f"commandline like '%{tw_path}%' and commandline like '%main.py%'"
        result = subprocess.run(
            ["wmic", "process", "where", wmic_filter,
             "get", "processid", "/value"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("ProcessId="):
                pid = line.split("=")[1].strip()
                if pid:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                    logger.info("Killed backend PID %s", pid)
        time.sleep(3)
        # Restart via scheduled task (the standard way)
        r = subprocess.run(
            ["schtasks", "/run", "/tn", "TradeWizard"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            logger.info("Backend restart via schtasks succeeded")
        else:
            logger.warning("schtasks /run failed (rc=%d): %s — falling back to direct start",
                           r.returncode, r.stderr.strip())
            # Fallback: start directly
            subprocess.Popen(
                ["python", str(PROJECT_ROOT / "backend" / "main.py")],
                cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            logger.info("Backend started directly (fallback)")
    except Exception as exc:
        logger.error("Backend restart failed: %s", exc)


def restart_mt5_connection():
    """Restart MT5 terminal if not running (direct connection reconnects automatically)."""
    logger.info("MT5 disconnected — ensuring terminal is running...")
    restart_mt5_terminal()


def restart_mt5_terminal():
    """Start MT5 terminal if not running."""
    logger.info("Starting MT5 terminal...")
    path = Path(MT5_TERMINAL_PATH)
    if not path.exists():
        # Try common paths
        for p in [
            Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
            Path(r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"),
            Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "MetaQuotes" / "Terminal",
        ]:
            if p.exists():
                path = p
                break
    if not path.exists():
        logger.error("MT5 terminal not found at %s", path)
        return
    try:
        subprocess.Popen([str(path)], creationflags=subprocess.DETACHED_PROCESS)
        logger.info("MT5 terminal started: %s", path)
    except Exception as exc:
        logger.error("MT5 terminal start failed: %s", exc)


# ── Component state tracking ─────────────────────────────────────────────────

class ComponentMonitor:
    def __init__(self, name: str, check_fn, restart_fn, is_async: bool = True):
        self.name = name
        self.check_fn = check_fn
        self.restart_fn = restart_fn
        self.is_async = is_async
        self.failures = 0
        self.last_restart = 0.0
        self.total_restarts = 0
        self.last_status = "unknown"
        self.cooldown = 120  # seconds between restart attempts

    async def check(self) -> bool:
        if self.is_async:
            ok, msg = await self.check_fn()
        else:
            ok, msg = self.check_fn()

        self.last_status = msg

        if ok:
            if self.failures > 0:
                logger.info("[%s] Recovered after %d failures: %s", self.name, self.failures, msg)
                await _send_whatsapp(
                    f"✅ *{self.name} RECOVERED*\n\n{msg}\n\n"
                    f"After {self.failures} consecutive failures."
                )
            self.failures = 0
            return True

        self.failures += 1
        logger.warning("[%s] Failure %d/%d: %s", self.name, self.failures, MAX_FAILURES, msg)

        if self.failures >= MAX_FAILURES:
            now = time.time()
            if now - self.last_restart > self.cooldown:
                logger.error("[%s] %d consecutive failures — RESTARTING", self.name, self.failures)
                await _send_whatsapp(
                    f"🔄 *RESTARTING {self.name}*\n\n"
                    f"Failed {self.failures}x consecutively.\n"
                    f"Last status: {msg}\n"
                    f"Restart #{self.total_restarts + 1}"
                )
                self.restart_fn()
                self.last_restart = now
                self.total_restarts += 1
                self.failures = 0  # Reset counter after restart
            else:
                remaining = int(self.cooldown - (now - self.last_restart))
                logger.info("[%s] Cooldown active (%ds remaining)", self.name, remaining)
                # Still send alarm during cooldown
                await _send_whatsapp(
                    f"🚨 *{self.name} STILL DOWN*\n\n"
                    f"{msg}\n"
                    f"Cooldown: {remaining}s before next restart attempt."
                )

        return False


# ── Main watchdog loop ────────────────────────────────────────────────────────

async def main():
    logger.info("=" * 60)
    logger.info("TradeWizard Watchdog started")
    logger.info("Backend URL:    %s", BACKEND_URL)
    logger.info("MT5 Bridge URL: %s", MT5_BRIDGE_URL)
    logger.info("Check interval: %ds", CHECK_INTERVAL)
    logger.info("Max failures:   %d", MAX_FAILURES)
    logger.info("Log file:       %s", LOG_FILE)
    logger.info("=" * 60)

    await _send_whatsapp(
        f"🐕 *Watchdog started*\n\n"
        f"Monitoring TradeWizard components every {CHECK_INTERVAL}s.\n"
        f"Auto-restart after {MAX_FAILURES} consecutive failures."
    )

    monitors = [
        ComponentMonitor("Backend", check_backend, restart_backend, is_async=True),
        ComponentMonitor("MT5 Connection", check_mt5_connection, restart_mt5_connection, is_async=True),
        ComponentMonitor("MT5 Terminal", check_mt5_terminal, restart_mt5_terminal, is_async=False),
    ]

    # Daily backup tracker
    last_backup_date = None

    while True:
        for m in monitors:
            try:
                ok = await m.check()
                status_icon = "✅" if ok else "❌"
                logger.debug("%s %s: %s", status_icon, m.name, m.last_status)
            except Exception as exc:
                logger.error("Monitor error for %s: %s", m.name, exc)

        # Daily backup at 03:00 Rome time
        try:
            from zoneinfo import ZoneInfo
            now_rome = datetime.now(ZoneInfo("Europe/Rome"))
            today = now_rome.date()
            if now_rome.hour == 3 and last_backup_date != today:
                last_backup_date = today
                logger.info("Running daily backup...")
                from services.backup import run_backup_with_notification
                result = await run_backup_with_notification()
                logger.info("Backup done: %d files, %d errors", len(result["files"]), len(result["errors"]))
        except Exception as exc:
            logger.error("Backup error: %s", exc)

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Watchdog stopped by user")
    except Exception as exc:
        logger.critical("Watchdog crashed: %s", exc, exc_info=True)
