"""
backup.py — Automated daily backup of TradeWizard critical files.

Backs up:
  - tradewizard.db (database with all trades, config, memory)
  - .env (API keys and credentials)

Retention: keeps last 7 days, deletes older backups.
Sends WhatsApp notification on success or failure.

Run standalone:  python backend/services/backup.py
Or integrated:   called by watchdog or scheduled task daily.
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger("backup")

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR   = PROJECT_ROOT / "backups"
DB_PATH      = PROJECT_ROOT / "tradewizard.db"
ENV_PATH     = PROJECT_ROOT / ".env"
RETENTION_DAYS = 7

# Load .env for WhatsApp credentials
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


async def _send_whatsapp(message: str):
    """Send WhatsApp notification via Twilio."""
    import httpx
    sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num = os.getenv("TWILIO_WHATSAPP_FROM", "")
    to_num   = os.getenv("WHATSAPP_TO", "")
    if not all([sid, token, from_num, to_num]):
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, data={
                "From": from_num, "To": to_num, "Body": message,
            }, auth=(sid, token))
    except Exception as exc:
        logger.error("WhatsApp notification failed: %s", exc)


def run_backup() -> dict:
    """
    Create a timestamped backup of DB and .env.
    Returns dict with status, files backed up, and any errors.
    """
    now = datetime.now(ZoneInfo("Europe/Rome"))
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    day_folder = BACKUP_DIR / now.strftime("%Y-%m-%d")

    result = {
        "timestamp": now.isoformat(),
        "folder": str(day_folder),
        "files": [],
        "errors": [],
        "cleaned": 0,
    }

    # Create backup directory
    try:
        day_folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        result["errors"].append(f"Cannot create backup dir: {exc}")
        return result

    # Backup database
    if DB_PATH.exists():
        dest = day_folder / f"tradewizard_{timestamp}.db"
        try:
            shutil.copy2(DB_PATH, dest)
            size_mb = dest.stat().st_size / 1024 / 1024
            result["files"].append(f"tradewizard.db ({size_mb:.1f} MB)")
            logger.info("Backed up DB: %s (%.1f MB)", dest, size_mb)
        except Exception as exc:
            result["errors"].append(f"DB backup failed: {exc}")
            logger.error("DB backup failed: %s", exc)
    else:
        result["errors"].append("tradewizard.db not found")

    # Backup .env
    if ENV_PATH.exists():
        dest = day_folder / f"env_{timestamp}.bak"
        try:
            shutil.copy2(ENV_PATH, dest)
            result["files"].append(".env")
            logger.info("Backed up .env: %s", dest)
        except Exception as exc:
            result["errors"].append(f".env backup failed: {exc}")
    else:
        result["errors"].append(".env not found")

    # Cleanup old backups
    result["cleaned"] = _cleanup_old_backups()

    return result


def _cleanup_old_backups() -> int:
    """Remove backup folders older than RETENTION_DAYS. Returns count removed."""
    if not BACKUP_DIR.exists():
        return 0

    removed = 0
    # Use Rome date so the cleanup window matches the day-foldering above
    # (run_backup names folders with Rome's calendar date). Avoid
    # datetime.now() naked — its tz depends on the host machine.
    cutoff = datetime.now(ZoneInfo("Europe/Rome")).date()
    from datetime import timedelta
    cutoff_date = cutoff - timedelta(days=RETENTION_DAYS)

    for item in sorted(BACKUP_DIR.iterdir()):
        if not item.is_dir():
            continue
        try:
            folder_date = datetime.strptime(item.name, "%Y-%m-%d").date()
            if folder_date < cutoff_date:
                shutil.rmtree(item)
                removed += 1
                logger.info("Removed old backup: %s", item.name)
        except ValueError:
            continue  # Skip folders that don't match date format

    return removed


async def run_backup_with_notification():
    """Run backup and send WhatsApp notification."""
    result = run_backup()

    if result["errors"]:
        msg = (
            f"🚨 *BACKUP FAILED*\n\n"
            f"Errors:\n" +
            "\n".join(f"• {e}" for e in result["errors"]) +
            f"\n\nFiles OK: {', '.join(result['files']) or 'none'}"
        )
    else:
        msg = (
            f"💾 *BACKUP COMPLETED*\n\n"
            f"Files: {', '.join(result['files'])}\n"
            f"Folder: {Path(result['folder']).name}\n"
            f"Old backups cleaned: {result['cleaned']}\n"
            f"Retention: {RETENTION_DAYS} days"
        )

    await _send_whatsapp(msg)
    return result


# ── Standalone execution ──────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = asyncio.run(run_backup_with_notification())
    print(f"\nBackup result: {len(result['files'])} files, {len(result['errors'])} errors")
    if result["errors"]:
        for e in result["errors"]:
            print(f"  ERROR: {e}")
