import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from app.broker import execute
from app.claude_client import analyze_signal
from app.config import settings
from app.metaapi_broker import close_position, get_position, open_buy, open_sell
from app.models import StrategyAlert, TradingViewAlert
from app.strategy_state import state
from app.tp_watcher import watch_take_profit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if not settings.dry_run:
        task = asyncio.create_task(watch_take_profit())
        logger.info("Take-profit watcher started")
    yield
    if task is not None:
        task.cancel()


app = FastAPI(title="AI-Powered Trading Bot", lifespan=lifespan)


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


@app.post("/webhook/strategy")
async def strategy_webhook(request: Request) -> dict:
    """Deterministic execution for the BLACK-GOLD indicator: buy on the green
    dot, sell on the red dot, close on either black (exit) dot. One position
    at a time, $take_profit_usd take-profit, $daily_profit_target_usd/day cap.
    """
    body = await request.json()
    try:
        alert = StrategyAlert(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid alert payload: {exc}")

    if not hmac.compare_digest(alert.secret, settings.tradingview_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    logger.info("Strategy alert: %s %s", alert.action, alert.ticker)

    if alert.action == "close":
        if state.open_position_id is None:
            return {"status": "no_open_position"}
        if settings.dry_run:
            logger.info("[DRY RUN] would close position %s", state.open_position_id)
            state.register_close(0.0)
            return {"status": "dry_run_closed"}
        pos = await get_position(state.open_position_id)
        result = await close_position(state.open_position_id)
        state.register_close(pos.get("profit", 0.0) if pos else 0.0)
        return {"status": "closed", "result": result}

    # buy / sell entry
    if not state.can_open_trade():
        reason = "daily profit target reached" if state.halted_today else "a trade is already open"
        logger.info("Skipping %s signal: %s", alert.action, reason)
        return {"status": "skipped", "reason": reason}

    if settings.dry_run:
        logger.info(
            "[DRY RUN] would open %s %s lot %s", alert.action, settings.lot_size, alert.ticker
        )
        state.register_open("dry-run", alert.action)
        return {"status": "dry_run_opened", "action": alert.action, "ticker": alert.ticker}

    if alert.action == "buy":
        result = await open_buy(alert.ticker, settings.lot_size)
    else:
        result = await open_sell(alert.ticker, settings.lot_size)

    position_id = result.get("positionId") or result.get("orderId")
    state.register_open(position_id, alert.action)
    return {"status": "opened", "action": alert.action, "result": result}
