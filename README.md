# AI-Powered Trading Bot

Connects TradingView alerts to Claude for signal analysis, with a pluggable
broker execution layer (dry-run/logging by default).

```
TradingView alert --webhook--> FastAPI server --> Claude API (sanity-check) --> broker.py (execute or log)
```

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `ANTHROPIC_API_KEY` - your Claude API key from https://console.anthropic.com/
- `TRADINGVIEW_WEBHOOK_SECRET` - any random string; it must also be embedded in
  your TradingView alert message (see below) so the endpoint can reject
  requests that don't include it. TradingView alerts can't send custom HTTP
  headers, which is why the secret lives inside the JSON body instead.
- `DRY_RUN` - keep this `true` until you've wired up a real broker in
  `app/broker.py`. In dry-run mode, alerts are analyzed and logged, not traded.

## 2. Run the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

TradingView must be able to reach this server over the public internet.
Options:
- Deploy it (Render, Fly.io, a VPS, etc.) and use its public URL.
- For local testing, expose it with a tunnel: `ngrok http 8000`.

## 3. Create the TradingView alert

In TradingView, open **Alerts** on your chart/strategy and create a new alert:

1. **Condition**: your strategy or indicator condition.
2. **Webhook URL**: `https://<your-host>/webhook/tradingview`
3. **Message** (JSON body TradingView will POST):

```json
{
  "secret": "change-me",
  "ticker": "{{ticker}}",
  "action": "buy",
  "price": {{close}},
  "strategy": "my-strategy",
  "interval": "{{interval}}",
  "timestamp": "{{timenow}}"
}
```

- Replace `"secret"` with the same value as `TRADINGVIEW_WEBHOOK_SECRET`.
- Set `"action"` to `"buy"`, `"sell"`, or `"close"` (use separate alerts per
  action, or drive it from a Pine Script `alert()` call with a dynamic
  message).
- `{{ticker}}`, `{{close}}`, `{{interval}}`, `{{timenow}}` are TradingView
  placeholder variables filled in automatically when the alert fires.

## 4. What happens on each alert

1. FastAPI validates the shared secret and payload shape (`app/models.py`).
2. The alert is sent to Claude (`app/claude_client.py`), which returns a
   structured `{approved, reasoning, confidence}` decision - a sanity check
   before anything is acted on.
3. If approved, `app/broker.py` executes the trade. By default (`DRY_RUN=true`)
   it only logs what it *would* do.
4. If rejected, the alert is logged and no order is sent.

## 5. Going live

`app/broker.py` currently only supports dry-run logging. Before setting
`DRY_RUN=false`, implement real order submission there using your
broker/exchange's SDK (e.g. `ccxt`, `alpaca-py`, `ib_insync`), including your
own risk controls (position sizing, max exposure, kill switch). This repo
intentionally ships without live-trading code wired in.

## Tests

```bash
pytest
```

---

## BLACK-GOLD indicator auto-trader (`/webhook/strategy`)

A second, deterministic endpoint for the custom `TIJARA TRADER BLACK GOLD`
Pine indicator. Unlike `/webhook/tradingview` above, it does **not** ask
Claude for a sanity check - it mechanically follows these rules:

1. Buy `LOT_SIZE` lots instantly on the green dot (Long Signal).
2. Sell `LOT_SIZE` lots instantly on the red dot (Short Signal).
3. Close the open trade instantly on either black dot (Exit Long / Exit Short).
4. Only one trade open at a time - new entry signals are ignored while a
   trade is running.
5. Close the trade the instant its floating profit reaches `TAKE_PROFIT_USD`
   (checked every `TP_POLL_SECONDS` seconds by a background watcher).
6. Once realized profit for the day reaches `DAILY_PROFIT_TARGET_USD`, no
   more trades are opened until the next calendar day.

### Broker connection

`0.01` lot sizing means MetaTrader, so trades are placed via
[MetaApi.cloud](https://metaapi.cloud/) (`app/metaapi_broker.py`), which
connects to your existing MT4/MT5 broker account over the cloud - no need to
keep a Windows terminal running. To set it up:

1. Create a MetaApi.cloud account and add your MT4/MT5 account (**use a demo
   account while testing this strategy**).
2. Generate an API token and copy your MetaApi account id.
3. Put them in `.env` as `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`.
4. Keep `DRY_RUN=true` until you've confirmed the logic behaves as expected
   in the logs - it will log every buy/sell/close it *would* make without
   placing real orders or requiring MetaApi credentials at all.
5. Once you're ready to test on the demo account, set `DRY_RUN=false` and
   restart the server.

### TradingView alerts to create

The indicator already defines four `alertcondition()`s. Create one
TradingView alert per condition, each pointing at
`https://<your-host>/webhook/strategy` with the JSON message shown:

| Alert condition | Message JSON |
|---|---|
| Long Signal | `{"secret": "change-me", "action": "buy", "ticker": "{{ticker}}"}` |
| Short Signal | `{"secret": "change-me", "action": "sell", "ticker": "{{ticker}}"}` |
| Exit Long Signal | `{"secret": "change-me", "action": "close", "ticker": "{{ticker}}"}` |
| Exit Short Signal | `{"secret": "change-me", "action": "close", "ticker": "{{ticker}}"}` |

Replace `"secret"` with your `TRADINGVIEW_WEBHOOK_SECRET`. Set each alert's
**Expiration** to "Open-ended" and trigger to "Once Per Bar Close" (or "Once
Per Bar" if you want the fastest possible reaction, at the cost of
repainting risk on the still-forming bar).

### Notes / limitations

- State (open position, daily profit) is kept in memory - it resets if the
  server restarts. Fine for testing; for unattended live use you'd want to
  persist it (e.g. to a small database) and reconcile against MetaApi on
  startup.
- The take-profit check polls every `TP_POLL_SECONDS` seconds rather than
  setting a broker-side TP price, since $10 profit doesn't map to a fixed
  price distance across instruments/lot sizes. Lower `TP_POLL_SECONDS` for
  tighter reaction time at the cost of more API calls.
- If your TradingView ticker format doesn't match your broker's symbol
  (e.g. `OANDA:XAUUSD` vs `XAUUSD`), the exchange prefix before `:` is
  stripped automatically; adjust `app/models.py` if your broker needs
  further remapping.
