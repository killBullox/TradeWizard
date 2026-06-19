"""
audit.py — Hourly kill-zone audit that compares Production vs Lab.

Produces a Markdown snapshot that is appended to docs/weekly_lab_report.md.
The snapshot is short (one section per run) so the cumulative file stays
readable over a 5-day test window.

Usage:
    python backend/scripts/audit.py                 # local, hits localhost
    python backend/scripts/audit.py --via-ssh       # via ssh to the VPS
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta

REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "weekly_lab_report.md")
PROD_URL = os.environ.get("PROD_URL", "http://localhost:8000")
LAB_URL  = os.environ.get("LAB_URL",  "http://localhost:8001")


def _http_get(url: str, timeout: int = 10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"error": str(exc)}


def _ssh_get(host: str, url: str):
    try:
        r = subprocess.run(
            ["ssh", host, f"curl -s {url}"],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return {"error": f"ssh failed: {r.stderr[-200:]}"}
        return json.loads(r.stdout)
    except Exception as exc:
        return {"error": str(exc)}


def collect(via_ssh: bool, ssh_host: str = ""):
    fn = (lambda url: _ssh_get(ssh_host, url)) if via_ssh else _http_get
    out = {
        "when": datetime.now(timezone.utc).isoformat(),
        "prod": {},
        "lab": {},
    }
    for side, base in (("prod", PROD_URL), ("lab", LAB_URL)):
        out[side]["mode"]         = fn(f"{base}/api/system-mode")
        out[side]["config"]       = fn(f"{base}/api/config")
        out[side]["trades"]       = fn(f"{base}/api/trades?limit=100")
        out[side]["analytics"]    = fn(f"{base}/api/analytics")
        out[side]["rules_stats"]  = fn(f"{base}/api/learning-rules/stats")
    return out


def summarize(side_data: dict) -> dict:
    """Pull out key metrics for the report."""
    trades = side_data.get("trades") or []
    if isinstance(trades, dict):
        trades = []

    today = datetime.now(timezone.utc).date()
    today_trades = [t for t in trades
                    if isinstance(t, dict)
                    and (t.get("open_time", "") or "").startswith(today.isoformat())]

    closed = [t for t in trades if isinstance(t, dict) and t.get("status") == "CLOSED"]
    wins = sum(1 for t in closed if t.get("result") == "WIN")
    losses = sum(1 for t in closed if t.get("result") == "LOSS")
    active = sum(1 for t in trades if isinstance(t, dict) and t.get("status") == "ACTIVE")
    cancelled_today = sum(1 for t in today_trades if t.get("status") == "CANCELLED")
    total_pnl = sum(t.get("pnl_usd") or 0 for t in closed)

    rules = side_data.get("rules_stats") or {}
    by_status = rules.get("by_status", {}) if isinstance(rules, dict) else {}

    return {
        "trades_total":       len(trades),
        "trades_today":       len(today_trades),
        "active":             active,
        "closed_win":         wins,
        "closed_loss":        losses,
        "win_rate":           round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else None,
        "total_pnl":          round(total_pnl, 2),
        "cancelled_today":    cancelled_today,
        "rules_candidate":    by_status.get("CANDIDATE", 0),
        "rules_active":       by_status.get("ACTIVE", 0),
        "rules_confirmed":    by_status.get("CONFIRMED", 0),
        "rules_deprecated":   by_status.get("DEPRECATED", 0),
        "avg_rule_accuracy":  rules.get("avg_accuracy") if isinstance(rules, dict) else None,
    }


def render_markdown(data: dict) -> str:
    prod = summarize(data["prod"])
    lab  = summarize(data["lab"])
    when = datetime.fromisoformat(data["when"]).strftime("%Y-%m-%d %H:%M UTC")

    prod_ok = "ok" if data["prod"].get("mode", {}).get("mode") else "DOWN"
    lab_ok  = "ok" if data["lab"].get("mode",  {}).get("mode") else "DOWN"

    return f"""
## {when}

| Metric                | Production ({prod_ok}) | Lab ({lab_ok}) |
|-----------------------|------------------------|----------------|
| Trades total (last 100)| {prod['trades_total']}                | {lab['trades_total']}         |
| Trades today          | {prod['trades_today']}                | {lab['trades_today']}         |
| Active                | {prod['active']}                      | {lab['active']}               |
| Closed W/L            | {prod['closed_win']} / {prod['closed_loss']} | {lab['closed_win']} / {lab['closed_loss']} |
| Win rate              | {prod['win_rate']}%                   | {lab['win_rate']}%            |
| Total P&L             | ${prod['total_pnl']}                  | ${lab['total_pnl']}           |
| Cancelled today       | {prod['cancelled_today']}             | {lab['cancelled_today']}      |
| Rules CANDIDATE       | {prod['rules_candidate']}             | {lab['rules_candidate']}      |
| Rules ACTIVE          | {prod['rules_active']}                | {lab['rules_active']}         |
| Rules CONFIRMED       | {prod['rules_confirmed']}             | {lab['rules_confirmed']}      |
| Rules DEPRECATED      | {prod['rules_deprecated']}            | {lab['rules_deprecated']}     |
| Avg rule accuracy     | {prod['avg_rule_accuracy']}%          | {lab['avg_rule_accuracy']}%   |
"""


def append_report(snapshot_md: str):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    if not os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("# TradeWizard — Weekly Lab vs Production Report\n\n")
            f.write(f"Auto-generated hourly during kill zone. Started {datetime.now(timezone.utc).date()}.\n")
    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write(snapshot_md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--via-ssh", action="store_true",
                     help="Fetch metrics through SSH (for running on local machine against VPS)")
    ap.add_argument("--ssh-host", default="Administrator@185.218.126.96",
                     help="ssh host for --via-ssh mode")
    ap.add_argument("--print-only", action="store_true",
                     help="Print markdown to stdout, do not append to report file")
    args = ap.parse_args()

    data = collect(args.via_ssh, args.ssh_host)
    md = render_markdown(data)
    if args.print_only:
        print(md)
        return
    append_report(md)
    print(md)
    print(f"\n→ appended to {REPORT_PATH}")


if __name__ == "__main__":
    main()
