# TradeWizard A/B Test Lab Report

A/B test window: 2026-04-20 to 2026-04-24 (weekdays)

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
