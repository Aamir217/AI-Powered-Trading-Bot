import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TRADINGVIEW_WEBHOOK_SECRET", "test-secret")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.strategy_state import state  # noqa: E402

client = TestClient(app)

SECRET = "test-secret"


def _reset_state():
    state.open_position_id = None
    state.open_direction = None
    state.daily_realized_profit = 0.0
    state.halted_today = False


def test_buy_opens_position_in_dry_run():
    _reset_state()
    resp = client.post(
        "/webhook/strategy",
        json={"secret": SECRET, "action": "buy", "ticker": "OANDA:XAUUSD"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dry_run_opened"
    assert state.open_position_id is not None
    assert state.open_direction == "buy"


def test_second_signal_skipped_while_position_open():
    _reset_state()
    client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "buy", "ticker": "XAUUSD"}
    )
    resp = client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "sell", "ticker": "XAUUSD"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "skipped"
    assert "already open" in body["reason"]


def test_close_clears_open_position():
    _reset_state()
    client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "buy", "ticker": "XAUUSD"}
    )
    resp = client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "close", "ticker": "XAUUSD"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dry_run_closed"
    assert state.open_position_id is None


def test_close_with_no_open_position():
    _reset_state()
    resp = client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "close", "ticker": "XAUUSD"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_open_position"


def test_daily_target_halts_further_trades():
    _reset_state()
    state.daily_realized_profit = 10.0
    state.halted_today = True
    resp = client.post(
        "/webhook/strategy", json={"secret": SECRET, "action": "buy", "ticker": "XAUUSD"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "skipped"
    assert "daily profit target" in body["reason"]


def test_bad_secret_rejected():
    _reset_state()
    resp = client.post(
        "/webhook/strategy", json={"secret": "wrong", "action": "buy", "ticker": "XAUUSD"}
    )
    assert resp.status_code == 401


def test_ticker_prefix_is_stripped():
    _reset_state()
    resp = client.post(
        "/webhook/strategy",
        json={"secret": SECRET, "action": "buy", "ticker": "OANDA:XAUUSD"},
    )
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "XAUUSD"
