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
