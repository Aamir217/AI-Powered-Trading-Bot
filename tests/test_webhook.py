import os
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TRADINGVIEW_WEBHOOK_SECRET", "test-secret")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import TradeDecision  # noqa: E402

client = TestClient(app)

PAYLOAD = {
    "secret": "test-secret",
    "ticker": "BTCUSD",
    "action": "buy",
    "price": 65000.0,
    "strategy": "test-strategy",
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_rejects_bad_secret():
    resp = client.post("/webhook/tradingview", json={**PAYLOAD, "secret": "wrong"})
    assert resp.status_code == 401


def test_webhook_approved_dry_run():
    with patch("app.main.analyze_signal") as mock_analyze:
        mock_analyze.return_value = TradeDecision(
            approved=True, reasoning="looks fine", confidence=0.9
        )
        resp = client.post("/webhook/tradingview", json=PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "executed"
    assert body["result"]["status"] == "dry_run"


def test_webhook_rejected_signal():
    with patch("app.main.analyze_signal") as mock_analyze:
        mock_analyze.return_value = TradeDecision(
            approved=False, reasoning="too noisy", confidence=0.3
        )
        resp = client.post("/webhook/tradingview", json=PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
