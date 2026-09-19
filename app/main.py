import hmac
import logging

from fastapi import FastAPI, HTTPException, Request

from app.broker import execute
from app.claude_client import analyze_signal
from app.config import settings
from app.models import TradingViewAlert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

app = FastAPI(title="AI-Powered Trading Bot")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dry_run": settings.dry_run}


@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request) -> dict:
    body = await request.json()
    try:
        alert = TradingViewAlert(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid alert payload: {exc}")

    if not hmac.compare_digest(alert.secret, settings.tradingview_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    logger.info("Received alert: %s %s @ %s", alert.action, alert.ticker, alert.price)

    decision = analyze_signal(alert)
    logger.info(
        "Claude decision: approved=%s confidence=%.2f reasoning=%s",
        decision.approved,
        decision.confidence,
        decision.reasoning,
    )

    if not decision.approved:
        return {"status": "rejected", "decision": decision.model_dump()}

    result = execute(alert)
    return {"status": "executed", "decision": decision.model_dump(), "result": result}
