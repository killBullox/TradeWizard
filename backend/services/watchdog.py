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
    """Check MT5 connectivity — reads mt5_connected (bool) from /api/health."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{BACKEND_URL}/api/health")
            if r.status_code == 200:
                data = r.json()
                if data.get("mt5_connected") is True:
                    return True, "MT5 connected"
                return False, f"MT5 not connected (health={data.get('status')})"
            return False, f"Backend returned HTTP {r.status_code}"
    except Exception as exc:
        return False, f"Cannot check MT5: {exc}"


async def check_bridge() -> tuple[bool, str]:
    """Check MT5 bridge directly (port 5555)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:5555/health")
            if r.status_code == 200:
                d = r.json()
                if d.get("connected") and d.get("account"):
                    return True, f"Bridge OK (account={d['account']})"
                return False, f"Bridge not connected: {d}"
            return False, f"Bridge HTTP {r.status_code}"
    except Exception as exc:
        return False, f"Bridge unreachable: {exc}"


async def check_lab_backend() -> tuple[bool, str]:
    """Check lab backend on port 8001."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:8001/api/health")
            if r.status_code == 200:
                data = r.json()
                if data.get("status") in ("healthy", "degraded"):
                    return True, f"Lab {data.get('status')}"
                return False, f"Lab status={data.get('status')}"
            return False, f"Lab HTTP {r.status_code}"
    except Exception as exc:
        return False, f"Lab unreachable: {exc}"


async def check_analysis_freshness() -> tuple[bool, str]:
    """During an active kill zone (read from backend config in Rome time),
    last_analysis must be < 25 min old. Outside kill zones the backend
    legitimately skips analysis cycles (the orchestrator's analysis_loop
    logs 'Outside Kill Zone — skipping analysis cycle'), so freshness is
    not required.

    Previously this hardcoded 5 <= hour < 19. That assumed a single
    daily kill zone, but the real config has TWO separate windows
    (06:30-11:00 London + 14:00-17:00 NY in Rome time). The hardcoded
    window flagged a 'failure' between 11:00-14:00 every day and again
    pre-06:30 + post-17:00, triggering spurious RESTARTING events that
    bounced a perfectly healthy backend. Bug observed 2026-04-29 06:27
    Rome: 4 restart cycles fired before the 06:30 London open
    naturally refreshed last_analysis."""
    from datetime import datetime as _dt
    import json as _json
    try:
        from zoneinfo import ZoneInfo
        now_rome = _dt.now(ZoneInfo("Europe/Rome"))
    except Exception:
        now_rome = _dt.utcnow()

    # Pull kill_zones from the backend's own config — the same source the
    # orchestrator reads. Falls back to a wide default only if unreachable.
    kill_zones = [{"start": "06:30", "end": "11:00"}, {"start": "14:00", "end": "17:00"}]
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(f"{BACKEND_URL}/api/config")
            if r.status_code == 200:
                cfg = r.json()
                raw = cfg.get("kill_zones")
                if raw:
                    parsed = _json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(parsed, list) and parsed:
                        kill_zones = parsed
    except Exception:
        pass

    cur_min = now_rome.hour * 60 + now_rome.minute
    in_kz = False
    minutes_since_kz_open = None
    for w in kill_zones:
        try:
            sh, sm = map(int, w["start"].split(":"))
            eh, em = map(int, w["end"].split(":"))
            kz_start = sh * 60 + sm
            kz_end   = eh * 60 + em
            if kz_start <= cur_min < kz_end:
                in_kz = True
                minutes_since_kz_open = cur_min - kz_start
                break
        except Exception:
            continue
    if not in_kz:
        return True, "Outside kill zone — analysis freshness not required"
    # Grace period: at the boundary where a new kill zone opens, last_analysis
    # is still stale from the previous (closed) kill zone. The orchestrator
    # needs a few minutes to run its first cycle. Without this grace the
    # watchdog spam-restarts the backend at every kill zone open
    # (observed 2026-04-29 14:12 Rome = 12 min into NY open).
    KZ_OPEN_GRACE_MIN = 15
    if minutes_since_kz_open is not None and minutes_since_kz_open < KZ_OPEN_GRACE_MIN:
        return True, (f"Kill zone just opened {minutes_since_kz_open}min ago "
                      f"(grace {KZ_OPEN_GRACE_MIN}min) — analysis freshness not required yet")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{BACKEND_URL}/api/health")
            if r.status_code != 200:
                return False, f"Cannot check analysis: HTTP {r.status_code}"
            data = r.json()
            last = data.get("last_analysis")
            if not last:
                return False, "last_analysis is null during kill zone"
            try:
                last_dt = _dt.fromisoformat(last.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_min = (_dt.now(timezone.utc) - last_dt).total_seconds() / 60
                if age_min > 25:
                    return False, f"last_analysis is {age_min:.0f} min old (>25)"
                return True, f"Analysis fresh ({age_min:.0f} min ago)"
            except Exception as exc:
                return False, f"Cannot parse last_analysis: {exc}"
    except Exception as exc:
        return False, f"Cannot check analysis: {exc}"


async def check_bridge_wedge_rate() -> tuple[bool, str]:
    """Count 'wedged beyond recovery' lines in the bridge log over the last 5 min.
    If >=3, the Ava terminal itself is likely in a bad state — restart_fn will
    restart the Ava terminal (not just the bridge). Reads only the tail of the
    log to avoid O(n) scans of a huge file."""
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    log_path = LOG_DIR / "mt5_bridge.log"
    if not log_path.exists():
        return True, "no bridge log yet"
    try:
        # Read the last 8 KB — enough to cover ~5 min of typical log volume
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 16384))
            tail = f.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return True, f"cannot read bridge log: {exc}"

    cutoff = _dt.now(_tz.utc) - _td(minutes=5)
    count = 0
    for line in tail.splitlines():
        if "wedged beyond recovery" not in line:
            continue
        try:
            ts = _dt.fromisoformat(line[:19]).replace(tzinfo=_tz.utc)
            if ts >= cutoff:
                count += 1
        except Exception:
            pass

    if count >= 3:
        return False, f"{count} pipe wedges in last 5min — Ava terminal likely stuck"
    return True, f"{count} wedges in 5min (OK)"


async def check_cancellation_rate() -> tuple[bool, str]:
    """Alert if CANCELLED trades today exceed 10 on prod (usually means MT5 bug)."""
    from datetime import datetime as _dt
    today_iso = _dt.utcnow().date().isoformat()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{BACKEND_URL}/api/trades?limit=100")
            if r.status_code != 200:
                return True, "Cannot check CANCELLED count (non-fatal)"
            trades = r.json()
            cancelled_today = sum(
                1 for t in trades
                if t.get("status") == "CANCELLED"
                and str(t.get("open_time", "")).startswith(today_iso)
            )
            if cancelled_today >= 10:
                return False, f"{cancelled_today} CANCELLED trades today on prod — likely bug"
            return True, f"{cancelled_today} CANCELLED today (OK)"
    except Exception:
        return True, "Cannot check CANCELLED (non-fatal)"


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
    """Kill only the TradeWizard backend process (not all Python) and restart
    via schtasks. Handles the 'zombie task' case: Windows Task Scheduler may
    mark the task as 'Running' even when the child process has already died,
    and in that state schtasks /run refuses to start a new instance. We
    proactively send schtasks /end first to clear the zombie state."""
    logger.info("Restarting backend (prod)...")
    try:
        # 1. Kill the actual python child process, if any
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

        # 2. Clear any zombie task state at the scheduler level.
        # /end always returns 0 even if there is nothing to end — safe no-op.
        subprocess.run(["schtasks", "/end", "/tn", "TradeWizard"],
                        capture_output=True, text=True, timeout=10)
        time.sleep(2)

        # 3. Restart the task cleanly
        r = subprocess.run(
            ["schtasks", "/run", "/tn", "TradeWizard"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            logger.info("Backend restart via schtasks succeeded")
        else:
            logger.warning("schtasks /run failed (rc=%d): %s — falling back to direct start",
                           r.returncode, r.stderr.strip())
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


def restart_bridge():
    """Kill the bridge subprocess — the backend's watchdog thread will respawn it."""
    logger.info("Killing bridge subprocess so backend watchdog respawns it...")
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name='python.exe' and commandline like '%mt5_bridge_server%'",
             "get", "processid", "/value"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("ProcessId="):
                pid = line.split("=")[1].strip()
                if pid:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                    logger.info("Killed bridge PID %s", pid)
    except Exception as exc:
        logger.error("Bridge kill failed: %s", exc)


def restart_ava_terminal():
    """Restart the Ava MT5 terminal via scheduled task."""
    logger.info("Restarting Ava terminal via task MT5-Ava...")
    try:
        # Kill existing Ava terminal(s)
        result = subprocess.run(
            ["wmic", "process", "where",
             r"name='terminal64.exe' and executablepath like '%Ava%'",
             "get", "processid", "/value"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("ProcessId="):
                pid = line.split("=")[1].strip()
                if pid:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
        # Start task MT5-Ava
        subprocess.run(["schtasks", "/run", "/tn", "MT5-Ava"], capture_output=True, timeout=10)
        logger.info("Ava terminal restart triggered")
    except Exception as exc:
        logger.error("Ava restart failed: %s", exc)


def restart_lab_backend():
    """Kill lab backend (PID filtered on port 8001) and re-run TradeWizardLab
    task. Like restart_backend, proactively clears any zombie task state
    before issuing /run."""
    logger.info("Restarting lab backend...")
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name='python.exe' and commandline like '%backend%main.py%'",
             "get", "processid", "/value"],
            capture_output=True, text=True, timeout=10,
        )
        for pline in result.stdout.strip().splitlines():
            if not pline.startswith("ProcessId="):
                continue
            pid = pline.split("=")[1].strip()
            if not pid:
                continue
            ns = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True, timeout=5,
            )
            if f":8001" in ns.stdout and f" {pid}\n" in ns.stdout:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                logger.info("Killed lab backend PID %s", pid)
                break
        # Clear zombie task state, then run
        subprocess.run(["schtasks", "/end", "/tn", "TradeWizardLab"],
                        capture_output=True, text=True, timeout=10)
        time.sleep(2)
        subprocess.run(["schtasks", "/run", "/tn", "TradeWizardLab"],
                        capture_output=True, timeout=10)
    except Exception as exc:
        logger.error("Lab restart failed: %s", exc)


# Persistent alert log — appended to so the backend can expose via /api/alerts
ALERTS_FILE = LOG_DIR / "alerts.log"


def _log_alert(level: str, component: str, message: str):
    """Append alert to alerts.log with ISO timestamp (UTC)."""
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{ts}\t{level}\t{component}\t{message}\n"
    try:
        with open(ALERTS_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


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
                _log_alert("INFO", self.name, f"RECOVERED after {self.failures} failures: {msg}")
                await _send_whatsapp(
                    f"✅ *{self.name} RECOVERED*\n\n{msg}\n\n"
                    f"After {self.failures} consecutive failures."
                )
            self.failures = 0
            return True

        self.failures += 1
        logger.warning("[%s] Failure %d/%d: %s", self.name, self.failures, MAX_FAILURES, msg)
        _log_alert("WARN", self.name, f"failure {self.failures}/{MAX_FAILURES}: {msg}")

        if self.failures >= MAX_FAILURES:
            now = time.time()
            if now - self.last_restart > self.cooldown:
                logger.error("[%s] %d consecutive failures — RESTARTING", self.name, self.failures)
                _log_alert("ERROR", self.name, f"RESTARTING after {self.failures} failures: {msg}")
                await _send_whatsapp(
                    f"🔄 *RESTARTING {self.name}*\n\n"
                    f"Failed {self.failures}x consecutively.\n"
                    f"Last status: {msg}\n"
                    f"Restart #{self.total_restarts + 1}"
                )
                try:
                    self.restart_fn()
                except Exception as exc:
                    logger.error("[%s] restart_fn raised: %s", self.name, exc)
                self.last_restart = now
                self.total_restarts += 1
                self.failures = 0  # Reset counter after restart
            else:
                remaining = int(self.cooldown - (now - self.last_restart))
                logger.info("[%s] Cooldown active (%ds remaining)", self.name, remaining)
                _log_alert("WARN", self.name, f"STILL DOWN (cooldown {remaining}s): {msg}")
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
        ComponentMonitor("Backend (prod)", check_backend, restart_backend, is_async=True),
        ComponentMonitor("Backend (lab)", check_lab_backend, restart_lab_backend, is_async=True),
        ComponentMonitor("MT5 Bridge", check_bridge, restart_bridge, is_async=True),
        ComponentMonitor("MT5 Connection", check_mt5_connection, restart_ava_terminal, is_async=True),
        ComponentMonitor("MT5 Terminal", check_mt5_terminal, restart_mt5_terminal, is_async=False),
        ComponentMonitor("Bridge wedge rate", check_bridge_wedge_rate, restart_ava_terminal, is_async=True),
        ComponentMonitor("Analysis freshness", check_analysis_freshness, restart_backend, is_async=True),
        ComponentMonitor("Cancellation rate", check_cancellation_rate, lambda: None, is_async=True),
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
