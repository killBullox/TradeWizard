# TradeWizard MT5 Integration — Installation Guide

Two integration methods are available. Choose the one that fits your setup.

---

## Method A — MQL5 Expert Advisor (Recommended)

The EA runs directly inside MetaTrader 5 as a TCP server.
TradeWizard's Python backend sends HTTP webhooks to it.

### Requirements
- MetaTrader 5 terminal, Build **2361** or newer
- `Tools → Options → Expert Advisors → Allow automated trading` ✓
- No additional Python packages needed

### Step 1 — Copy files to MT5

Copy the four `.mqh` / `.mq5` files to your MT5 data folder:

| File | Destination |
|------|-------------|
| `TW_Defines.mqh`     | `<MT5 Data>\MQL5\Include\` |
| `TW_JsonParser.mqh`  | `<MT5 Data>\MQL5\Include\` |
| `TW_HMAC.mqh`        | `<MT5 Data>\MQL5\Include\` |
| `TradeWizard_EA.mq5` | `<MT5 Data>\MQL5\Experts\` |

> Find your MT5 Data folder:
> `File → Open Data Folder` inside MetaTrader 5

### Step 2 — Compile

1. Open **MetaEditor** (`F4` from MT5 chart)
2. Open `TradeWizard_EA.mq5`
3. Press **F7** (Compile)
4. Confirm **0 errors** in the Toolbox tab

### Step 3 — Attach to a chart

1. In MT5 open any chart (e.g. EURUSD M5)
2. Drag `TradeWizard_EA` from Navigator → Expert Advisors onto the chart
3. In the EA inputs dialog:

| Input | Default | Description |
|-------|---------|-------------|
| `InpPort` | `5000` | Webhook listen port |
| `InpSecret` | `tradewizard_secret` | Must match `.env` `MT5_WEBHOOK_SECRET` |
| `InpVerifyHMAC` | `true` | Verify HMAC signatures |
| `InpMaxLot` | `1.0` | Safety cap on lot size |
| `InpSlippage` | `10` | Max slippage in points |
| `InpVerbose` | `true` | Enable detailed logging |

4. Click OK — the EA shows a green smiley face on the chart
5. Check Experts tab: `TradeWizard EA started — listening on port 5000`

### Step 4 — Configure TradeWizard backend

Edit your `.env` file:

```env
MT5_WEBHOOK_URL=http://192.168.1.X:5000/webhook   # IP of the MT5 PC
MT5_WEBHOOK_SECRET=tradewizard_secret              # Match InpSecret above
```

Restart the TradeWizard backend. The Connector agent will now send real orders.

### Firewall note

If MT5 is on a different PC than the TradeWizard backend, open port 5000 TCP
in Windows Firewall on the MT5 machine:

```powershell
netsh advfirewall firewall add rule name="TradeWizard EA" ^
  dir=in action=allow protocol=TCP localport=5000
```

---

## Method B — Python Bridge (Windows / MT5 Python API)

Use this if you prefer Python-side control or want deeper account integration.

### Requirements
- Windows machine with MetaTrader 5 installed
- Python 3.8+

```bash
pip install MetaTrader5 fastapi uvicorn
```

### Step 1 — Configure

Add to your `.env`:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Live
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe   # optional
MT5_BRIDGE_PORT=5001
MT5_WEBHOOK_URL=http://localhost:5001/webhook
```

### Step 2 — Run the bridge

```bash
cd TradeWizard
python backend/mt5_bridge.py
```

The bridge starts a REST server on port 5001 that accepts the same webhook
format as the MQL5 EA.

### Step 3 — Test the connection

```bash
curl http://localhost:5001/health
# → {"status":"ok","mt5_available":true,"connected":true}

curl http://localhost:5001/account
# → {"login":12345678,"balance":10000.0,...}
```

---

## Webhook signal format

Both methods accept the same JSON payload:

### OPEN
```json
{
  "action":      "OPEN",
  "symbol":      "EURUSD",
  "direction":   "BUY",
  "order_type":  "LIMIT",
  "entry_price": 1.08500,
  "stop_loss":   1.08200,
  "take_profit": 1.09100,
  "lot_size":    0.10,
  "comment":     "TW-ICT-FVG"
}
```

### MODIFY_SL
```json
{
  "action":  "MODIFY_SL",
  "ticket":  "123456",
  "new_sl":  1.08350
}
```

### CLOSE_PARTIAL
```json
{
  "action":  "CLOSE_PARTIAL",
  "ticket":  "123456",
  "percent": 50
}
```

### CLOSE
```json
{
  "action": "CLOSE",
  "ticket": "123456"
}
```

### Response format
```json
{"success": true,  "ticket": "123456", "message": "Market order placed"}
{"success": false, "error":  "Symbol not found: EURUSD"}
```

---

## Simulation mode (no MT5)

If `MT5_WEBHOOK_URL` is empty in `.env`, the Connector agent automatically
runs in **simulation mode** — it generates realistic responses without
contacting any MT5 terminal. This is the default out-of-the-box behavior.

To explicitly enable simulation:

```env
MT5_WEBHOOK_URL=
```

The dashboard will show `[SIM]` next to trade actions.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| EA smiley is red/grey | Check `Allow automated trading` in Options |
| `SocketBind failed` | Port 5000 already in use; change `InpPort` |
| `HMAC verification failed` | `InpSecret` must exactly match `MT5_WEBHOOK_SECRET` in `.env` |
| `Symbol not found` | Your broker uses suffixes — EA tries `.z`, `m`, `+`, `pro` automatically |
| Python bridge: `Login failed` | Check MT5_LOGIN / MT5_PASSWORD / MT5_SERVER |
| Connection refused | Check firewall; ensure MT5 terminal is running |
