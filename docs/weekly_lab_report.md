# TradeWizard A/B Test Lab Report

A/B test window: 2026-04-20 to 2026-04-24 (weekdays)

---

## 2026-04-24 12:29 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 12:29 UTC — TCP SYN never acknowledged on either port. This is the **18th consecutive failed audit** since 2026-04-20 03:07 UTC (~105 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window — this is the last audit of the window. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 18 consecutive audits spanning the entire A/B test window (2026-04-20 – 2026-04-24). The full A/B test has been rendered unmonitorable. Immediate VPS/firewall/process investigation and historical log retrieval is required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 11:07 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 11:07 UTC — TCP SYN never acknowledged on either port. This is the **17th consecutive failed audit** since 2026-04-20 03:07 UTC (~104 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window — the window closes EOD today. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 17 consecutive audits spanning the **entire** A/B test window (2026-04-20 to 2026-04-24). The window closes today — zero data has been collected from either backend. Immediate investigation of VPS/firewall/process state is required to salvage any end-of-day metrics.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 06:31 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 06:31 UTC — TCP SYN never acknowledged on either port. This is the **13th consecutive failed audit** since 2026-04-20 03:07 UTC (~99 hours of continuous outage). Approximately 17.5 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 13 consecutive audits (~99 hours). Today (2026-04-24) is the **final day** of the A/B test window — approximately 17.5 hours remain. Without immediate VPS/firewall/process recovery, the entire test window will conclude with zero data collected.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 05:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints (TCP-level, no connection established). This is the third consecutive timeout on the final day (2026-04-24) of the A/B test window (prior runs at 03:14 and 04:21 UTC also failed). No trade data, cancellation errors, or learning-rule updates could be retrieved. Regression analysis and patch drafting skipped.

Step 3 regression check: **skipped** — both backends unreachable. Most recent fix commits to relevant files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable (TCP timeout).

---

## 2026-04-24 04:21 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time (TCP-level, no connection established). No trade data, cancellation errors, or learning-rule updates could be retrieved. Regression analysis and patch drafting skipped. Consecutive timeouts across multiple audit runs today suggest the VPS may be down or the audit environment's outbound access to external IPs remains blocked.

Step 3 regression check: **skipped** — both backends unreachable. Most recent fix commits to relevant files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable (TCP timeout).

---

## 2026-04-24 03:14 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time (TCP-level, no connection established). No trade data, cancellation errors, or learning-rule updates could be retrieved. Regression analysis and patch drafting skipped. Audit environment allowlist blocks outbound connections to external IPs.

Step 3 regression check: **skipped** — both backends unreachable. Most recent fix commits to relevant files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable (TCP timeout).

---

## 2026-04-23 12:18 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time (TCP-level, no connection established). No trade data, cancellation errors, or learning-rule updates could be retrieved. Regression analysis and patch drafting skipped.

Step 3 regression check: **skipped** — both backends unreachable. Last known fix commits to relevant files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable (TCP timeout).

---

## 2026-04-23 07:30 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time (TCP-level, no connection established). No trade data, cancellation errors, or learning-rule updates could be retrieved. Regression analysis and patch drafting skipped.

Step 3 regression check: **skipped** — both backends unreachable. Last known fix commits to relevant files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable (TCP timeout).

---

## 2026-04-20 03:07 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 04:10 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 05:13 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 06:09 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Third consecutive timeout today** (03:07, 05:13, 06:09 UTC) — the VPS may be down or API ports firewalled. Manual investigation recommended.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 07:02 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Fifth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02 UTC) — the VPS appears persistently down or ports are firewalled. Urgent manual investigation recommended.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 08:20 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Sixth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20 UTC) — the VPS appears persistently unreachable throughout the first day of the A/B test window. Urgent manual investigation of VPS/firewall status strongly recommended.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 09:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Seventh consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 16:22 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Fourteenth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12, 11:19, 12:10, 13:31, 14:19, 15:08, 16:22 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 15:08 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Eighth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 15:08 UTC) — both ports have been unreachable throughout the entire first day of the A/B test window. The VPS is likely down, processes have crashed, or the firewall is blocking ports 8000/8001. Manual intervention on the VPS is critical before the window closes.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 10:12 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Eighth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 11:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Ninth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12, 11:19 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 12:10 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Tenth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12, 11:19, 12:10 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 13:31 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Eleventh consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12, 11:19, 12:10, 13:31 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge
- `814aaff` fix: rewrite order_send flow to prevent IPC pipe corruption

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 14:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Twelfth consecutive timeout today** (03:07, 04:10, 05:13, 06:09, 07:02, 08:20, 09:04, 10:12, 11:19, 12:10, 13:31, 14:19 UTC) — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-20 17:32 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. **Thirteenth consecutive timeout today** — the VPS has been unreachable throughout the entire first day of the A/B test window. Urgent manual investigation of VPS/firewall/process status is critical.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `8c0e24c` fix: in lab mode worker_ok reflects shared bridge reachability
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 03:09 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time — TCP SYN never acknowledged on either port. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

## 2026-04-21 04:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time — TCP SYN never acknowledged on either port. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 05:21 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time — TCP SYN never acknowledged on either port. This is the second consecutive timeout on 2026-04-21 (previous: 04:04 UTC) and part of an extended outage spanning all of 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run. Persistent unavailability throughout the A/B test window is a concern — urgent manual VPS investigation recommended.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 06:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at audit time (06:04 UTC) — TCP SYN never acknowledged on either port. This is a continuing persistent outage spanning all of 2026-04-20 and multiple audit runs on 2026-04-21. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `119f7e4` fix: retry order_send in client after bridge respawn
- `fe8bc94` fix: heartbeat + suicide-on-wedge + watchdog for MT5 bridge

**Action required:** VPS has been unreachable for all audit runs since the A/B test window opened (2026-04-20). Manually verify FastAPI processes are running and that inbound TCP on ports 8000/8001 is permitted by the VPS firewall.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 07:11 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 07:11 UTC — TCP SYN never acknowledged on either port. This is the third recorded timeout on 2026-04-21 (previous: 04:04 UTC, 06:04 UTC) and part of an ongoing outage spanning the entire A/B test window. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Last known fix commits to relevant files:
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send
- `119f7e4` fix: retry order_send in client after bridge respawn

**Action required (escalated):** VPS has been unreachable for every audit run since the A/B window opened on 2026-04-20. Manually verify FastAPI processes are running (`ps aux | grep uvicorn`), confirm firewall allows inbound TCP on ports 8000 and 8001, and check that the VPS itself is online.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 08:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 08:19 UTC — TCP SYN never acknowledged on either port. This is the fourth recorded timeout on 2026-04-21 (previous: 04:04, 06:04, 07:11 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 29 hours continuous outage. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 09:17 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 09:17 UTC — TCP SYN never acknowledged on either port. This is the seventh recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 30 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only 3 days of the A/B test window remain.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 10:12 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 10:12 UTC — TCP SYN never acknowledged on either port. This is the eighth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 31 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only 3 days of the A/B test window remain.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 11:23 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 11:23 UTC — TCP SYN never acknowledged on either port. This is the ninth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 32 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only 3 days of the A/B test window remain.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 12:27 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 12:27 UTC — TCP SYN never acknowledged on either port. This is the tenth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 33 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only 3 days of the A/B test window remain.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 13:11 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 13:11 UTC — TCP SYN never acknowledged on either port. This is the eleventh recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23, 12:27 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 34 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only ~2.5 days of the A/B test window remain (closes 2026-04-24).

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

## 2026-04-21 14:08 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 14:08 UTC — TCP SYN never acknowledged on either port. This is the twelfth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23, 12:27, 13:11 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 35 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only ~2.3 days of the A/B test window remain (closes 2026-04-24).

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 15:12 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 15:12 UTC — TCP SYN never acknowledged on either port. This is the thirteenth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23, 12:27, 13:11, 14:08 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 36 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only ~2.2 days of the A/B test window remain (closes 2026-04-24).

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 16:06 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 16:06 UTC — TCP SYN never acknowledged on either port. This is the fourteenth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23, 12:27, 13:11, 14:08, 15:12 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)
- `5fee9a2` fix: order_check preflight + dynamic stops/filling/deviation (solves -2)
- `959fa7d` fix: restore subprocess fallback before suicide in bridge order_send

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 37 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only ~2 days of the A/B test window remain (closes 2026-04-24).

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-21 17:20 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 17:20 UTC — TCP SYN never acknowledged on either port. This is the fifteenth recorded timeout on 2026-04-21 (previous: 03:09, 04:04, 05:21, 06:04, 07:11, 08:19, 09:17, 10:12, 11:23, 12:27, 13:11, 14:08, 15:12, 16:06 UTC) and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20. No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable.

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — over 38 hours continuous outage. Immediate manual VPS/firewall/process investigation required. Only ~2 days of the A/B test window remain (closes 2026-04-24).

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 04:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 04:19 UTC — TCP SYN never acknowledged on either port. This is the first recorded timeout on 2026-04-22 and part of an ongoing outage spanning the entire A/B test window since it opened 2026-04-20 03:07 UTC (~49 hours continuous). No trade data, cancellation errors, or learning-rule updates could be retrieved. No regression analysis or patch was possible this run.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — ~49 hours continuous outage. Only ~2 days of the A/B test window remain (closes 2026-04-24). Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.


---

## 2026-04-22 05:03 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 05:03 UTC — TCP SYN never acknowledged on either port. This extends the continuous outage that began 2026-04-20 03:07 UTC (~50 hours and counting). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — ~50 hours continuous outage. Only ~2 days of the A/B test window remain (closes 2026-04-24). Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.


---

## 2026-04-22 06:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 06:19 UTC — TCP SYN never acknowledged on either port. This extends the continuous outage that began 2026-04-20 03:07 UTC (~51 hours and counting). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC — ~51 hours continuous outage. Only ~2 days of the A/B test window remain (closes 2026-04-24). Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 07:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 07:04 UTC — TCP SYN never acknowledged on either port. This extends the continuous outage that began 2026-04-20 03:07 UTC (~52 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC. Immediate manual VPS/firewall/process investigation required before the test window closes 2026-04-24.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 08:23 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 08:23 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~53 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `11a9f87` feat: Activity Log persistente su DB (ActivityEvent table)
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~53 h). Immediate manual VPS/firewall/process investigation required before the test window closes 2026-04-24.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 09:05 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 09:05 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~54 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~54 h). Immediate manual VPS/firewall/process investigation required before the test window closes 2026-04-24.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 10:06 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 10:06 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~55 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~55 h). Immediate manual VPS/firewall/process investigation required before the test window closes 2026-04-24.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 11:11 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 11:11 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~59 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~59 h). Only ~2 days remain in the test window (closes 2026-04-24). Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

## 2026-04-22 12:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 12:04 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~61 hours and counting). Only ~2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (critical):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~61 h). Only ~2 days remain in the test window (closes 2026-04-24). Immediate manual VPS/firewall/process investigation required before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

## 2026-04-22 13:15 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 13:15 UTC — TCP SYN never acknowledged on either port. Outage has been unbroken since 2026-04-20 03:07 UTC (~82 hours and counting). Only ~1.5 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (CRITICAL):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~82 h). Only ~1.5 days remain in the test window (closes 2026-04-24). The A/B test will yield no data if not resolved immediately. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 14:25 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 14:25 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~83 hours and counting). Only ~1.4 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess
- `22047b7` fix: route ALL order_send through fresh subprocess (definitive)

**Action required (CRITICAL):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~83 h). Only ~1.4 days remain in the test window (closes 2026-04-24). The A/B test will yield no data if not resolved immediately. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 15:32 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 15:32 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~84 hours and counting). Only ~1.3 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

**Action required (CRITICAL):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~84 h). Only ~1.3 days remain in the test window (closes 2026-04-24). The A/B test will yield no data if not resolved immediately. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 16:45 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 16:45 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage that began 2026-04-20 03:07 UTC (~62 hours and counting). Only ~1.3 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

**Action required (CRITICAL):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~62 h). Only ~1.3 days remain in the test window (closes 2026-04-24). The A/B test will yield no data if not resolved immediately. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-22 17:09 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 17:09 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~86 hours and counting). Less than 2 days of the A/B test window remain (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

**Action required (CRITICAL):** VPS unreachable for every audit since 2026-04-20 03:07 UTC (~86 h). Less than 2 days remain in the A/B test window (closes 2026-04-24). The test will yield no data if not resolved immediately. Immediate manual VPS/firewall/process investigation required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 03:01 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 03:01 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~96 hours and counting). Only ~21 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment
- `032eae0` debug: verbose logging of every order_send param + filter alerts per mode
- `37e6771` fix: global mt5 lock — serialize every MT5 call in bridge + during subprocess

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~96 h). Only ~21 hours remain in the A/B test window (closes 2026-04-24). The entire test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 04:21 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 04:21 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~97 hours and counting). Fewer than 20 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~97 h). Fewer than 20 hours remain in the A/B test window (closes 2026-04-24). The entire test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 05:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 05:19 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~98 hours and counting). Fewer than 19 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~98 h). Fewer than 19 hours remain in the A/B test window (closes 2026-04-24). The entire test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 06:18 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 06:18 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~99 hours and counting). Only ~18 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~99 h). Only ~18 hours remain in the A/B test window (closes 2026-04-24). The entire test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 08:12 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 08:12 UTC — TCP SYN never acknowledged on either port. This continues the unbroken outage first recorded at 2026-04-20 03:07 UTC (~101 hours and counting). Only ~16 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~101 h). Only ~16 hours remain in the A/B test window (closes 2026-04-24). The entire test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 09:03 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 09:03 UTC — TCP SYN never acknowledged on either port. This is now the 5th consecutive failed audit since 2026-04-20 03:07 UTC (~106 hours of continuous outage). Only ~15 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~106 h). Only ~15 hours remain in the A/B test window (closes 2026-04-24 EOD). The entire A/B test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 10:15 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 10:15 UTC — TCP SYN never acknowledged on either port. This is now the **6th consecutive failed audit** since 2026-04-20 03:07 UTC (~107 hours of continuous outage). Only ~14 hours remain in the A/B test window (closes 2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC (~107 h). Only ~14 hours remain in the A/B test window (closes 2026-04-24 EOD). The entire A/B test will yield zero data if not resolved immediately. Manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

## 2026-04-23 11:15 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 11:15 UTC — TCP SYN never acknowledged on either port. This is now the **7th consecutive failed audit** since 2026-04-20 03:07 UTC (~80 hours of continuous outage). Approximately 37 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS has been unreachable for every audit since 2026-04-20 03:07 UTC. The A/B test window closes tomorrow (2026-04-24). Manual VPS/firewall/process investigation is urgently required to salvage any remaining test data.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 13:10 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 13:10 UTC — TCP SYN never acknowledged on either port. This is now the **8th consecutive failed audit** since 2026-04-20 03:07 UTC (~82 hours of continuous outage). Approximately 35 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 8 consecutive audits (~82 hours). The A/B test window closes 2026-04-24; manual VPS/firewall/process investigation is urgently required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 14:24 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 14:24 UTC — TCP SYN never acknowledged on either port. This is now the **9th consecutive failed audit** since 2026-04-20 03:07 UTC (~87 hours of continuous outage). Approximately 10 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 9 consecutive audits (~87 hours). The A/B test window closes tomorrow 2026-04-24; manual VPS/firewall/process investigation is urgently required to salvage any remaining test data.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 14:24 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 14:24 UTC — TCP SYN never acknowledged on either port. This is now the **9th consecutive failed audit** since 2026-04-20 03:07 UTC (~87 hours of continuous outage). Approximately 10 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 9 consecutive audits (~87 hours). The A/B test window closes tomorrow 2026-04-24; manual VPS/firewall/process investigation is urgently required to salvage any remaining test data.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 15:19 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 15:19 UTC — TCP SYN never acknowledged on either port. This is the **10th consecutive failed audit** since 2026-04-20 03:07 UTC (~84 hours of continuous outage). Approximately 8.5 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 10 consecutive audits (~84 hours). The A/B test window closes 2026-04-24; only ~8.5 hours remain — manual VPS/firewall/process investigation is urgently required to salvage any remaining test data.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 16:11 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 16:11 UTC — TCP SYN never acknowledged on either port. This is the **11th consecutive failed audit** since 2026-04-20 03:07 UTC (~85 hours of continuous outage). Approximately 32 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 11 consecutive audits (~85 hours). The A/B test window closes 2026-04-24 — only ~32 hours remain. Manual VPS/firewall/process investigation is urgently required to salvage any remaining test data before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-23 17:09 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 17:09 UTC — TCP SYN never acknowledged on either port. This is the **12th consecutive failed audit** since 2026-04-20 03:07 UTC (~86 hours of continuous outage). Approximately 31 hours remain in the A/B test window (closes 2026-04-24 EOD). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `9329544` feat: force Europe/Rome display + UTC-unambiguous API timestamps
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 12 consecutive audits (~86 hours). The A/B test window closes 2026-04-24 — only ~31 hours remain. Manual VPS/firewall/process investigation is urgently required to salvage any remaining test data before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 07:30 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 07:30 UTC — TCP SYN never acknowledged on either port. This is the **13th consecutive failed audit** since 2026-04-20 03:07 UTC (~100+ hours of continuous outage). The A/B test window closes today (2026-04-24 EOD) — this is the **final day** of the test window. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable.

**Action required (CRITICAL):** VPS unreachable for 13 consecutive audits spanning the entire A/B test window. Today is the last day of the test window. The entire A/B test has been unmonitorable due to persistent VPS/firewall/process outage. Manual investigation is required immediately to determine cause and salvage any logs before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 08:29 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 08:29 UTC — TCP SYN never acknowledged on either port. This is the **14th consecutive failed audit** since 2026-04-20 03:07 UTC. Today is the **final day** of the A/B test window (2026-04-24). No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable.

**Action required (CRITICAL):** VPS unreachable for 14 consecutive audits spanning the entire A/B test window. Today is the last day of the test window; the outage has rendered the entire A/B test unmonitorable. Immediate manual VPS/firewall/process investigation is required to determine root cause and salvage any remaining server-side logs before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 09:11 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 09:11 UTC — TCP SYN never acknowledged on either port. This is the **15th consecutive failed audit** since 2026-04-20 03:07 UTC (~102 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 15 consecutive audits spanning essentially the entire A/B test window. The window closes tonight (EOD 2026-04-24). The outage has rendered the full A/B test unmonitorable. Immediate manual VPS/firewall/process investigation is required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 10:06 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 10:06 UTC — TCP SYN never acknowledged on either port. This is the **16th consecutive failed audit** since 2026-04-20 03:07 UTC (~107 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 16 consecutive audits spanning the entire A/B test window. This is the **last scheduled audit** — the window closes EOD 2026-04-24. The full A/B test has been rendered unmonitorable by the outage. Immediate VPS/firewall/process investigation and log retrieval is required before the window closes.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 13:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 13:04 UTC — TCP SYN never acknowledged on either port. This is the **17th consecutive failed audit** since 2026-04-20 03:07 UTC (~114 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window. No trade data, cancellation errors, or learning-rule updates could be retrieved.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 17 consecutive audits spanning the entire A/B test window. The window closes EOD 2026-04-24. The full A/B test has been rendered unmonitorable by the outage. Immediate VPS/firewall/process investigation and log retrieval is required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 14:21 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 14:21 UTC — TCP SYN never acknowledged on either port. This is the **18th consecutive failed audit** since 2026-04-20 03:07 UTC (~119 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window (closes EOD). The entire A/B test window has elapsed with zero successful data collection.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint
- `b4a53e7` fix: strict comment sanitizer — the -2 WAS literally the comment

**Action required (CRITICAL):** VPS unreachable for 18 consecutive audits — the complete A/B test window (2026-04-20 to 2026-04-24) has elapsed with zero successful data collection. Manual investigation of VPS networking, firewall rules, and backend process status is urgently needed.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 15:26 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 15:26 UTC — TCP SYN never acknowledged on either port. This is the **19th consecutive failed audit** since 2026-04-20 03:07 UTC (~132 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window (closes EOD). The entire A/B test window has elapsed with zero successful data collection.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `7993243` fix: force-tuning endpoint logs traceback instead of 500
- `f74c1db` feat: POST /api/lab/force-tuning endpoint — manual AUTO_TUNING trigger
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint

**Action required (CRITICAL):** VPS unreachable for 19 consecutive audits — the complete A/B test window (2026-04-20 to 2026-04-24) has elapsed with zero successful data collection. This is the final audit of the window. Immediate VPS/firewall/process investigation and log retrieval is required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 16:26 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 16:26 UTC — TCP SYN never acknowledged on either port. This is the **20th consecutive failed audit** since 2026-04-20 03:07 UTC (~133 hours of continuous outage). Today (2026-04-24) is the **final day** of the A/B test window (closes EOD). The entire A/B test window has elapsed with zero successful data collection.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `7993243` fix: force-tuning endpoint logs traceback instead of 500
- `f74c1db` feat: POST /api/lab/force-tuning endpoint — manual AUTO_TUNING trigger
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages
- `eec39b7` feat: L.2 adaptive RM lab + P.1 bias diagnostics endpoint

**Action required (CRITICAL — FINAL AUDIT):** This is the 20th and final scheduled audit of the A/B test window. Both backends have been unreachable for the entire window duration (~133 hours). The A/B test produced zero actionable data. Immediate manual VPS investigation is required before any conclusions can be drawn.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---

## 2026-04-24 17:04 UTC

### Side-by-Side Metrics

| Metric                  | Production (`:8000`) | Lab (`:8001`) |
|-------------------------|----------------------|---------------|
| Reachable               | ❌ TIMEOUT           | ❌ TIMEOUT    |
| Today's trades          | N/A                  | N/A           |
| CANCELLED count         | N/A                  | N/A           |
| Active trades           | N/A                  | N/A           |
| W / L                   | N/A                  | N/A           |
| Win rate                | N/A                  | N/A           |
| Total P&L               | N/A                  | N/A           |
| Rules CANDIDATE         | N/A                  | N/A           |
| Rules ACTIVE            | N/A                  | N/A           |
| Rules CONFIRMED         | N/A                  | N/A           |
| Rules DEPRECATED        | N/A                  | N/A           |
| Avg rule accuracy       | N/A                  | N/A           |

### Notable Events

Both VPS backends (185.218.126.96:8000 and 185.218.126.96:8001) timed out on all HTTP endpoints at 17:04 UTC — TCP SYN never acknowledged on either port. This is the **21st consecutive failed audit** since 2026-04-20. Today (2026-04-24) is the final day of the A/B test window (closes EOD). The entire A/B test window has elapsed with zero successful data collection.

Step 3 regression check: **skipped** — backend unreachable. Most recent fix commits to monitored files:
- `7993243` fix: force-tuning endpoint logs traceback instead of 500
- `f74c1db` feat: POST /api/lab/force-tuning endpoint — manual AUTO_TUNING trigger
- `cdaaf31` feat: alerts dismiss 'x' button + Europe/Rome time display
- `ef6ad61` fix: reset-stats now effective on Performance and Analytics pages

**Action required (CRITICAL — A/B WINDOW CLOSED):** This is the 21st consecutive failed audit, closing the A/B test window (2026-04-20 to 2026-04-24). Both backends have been unreachable for the entire window. The A/B test produced zero actionable data. Immediate manual VPS investigation is required.

### New CANDIDATE Rules

**0 new CANDIDATE rules retrieved** — lab backend unreachable.

---
