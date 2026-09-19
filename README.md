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
