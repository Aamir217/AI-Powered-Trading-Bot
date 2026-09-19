import logging

from app.config import settings
from app.models import TradingViewAlert

logger = logging.getLogger("broker")


def execute(alert: TradingViewAlert) -> dict:
    """Send an order to a broker/exchange.

    DRY_RUN (the default) only logs the order instead of sending it anywhere.
    Wire in a real broker/exchange SDK here (e.g. ccxt, alpaca-py) once you're
    ready to trade live, and flip DRY_RUN=false in your .env.
    """
    if settings.dry_run:
        logger.info(
            "[DRY RUN] would %s %s @ %s", alert.action, alert.ticker, alert.price
        )
        return {"status": "dry_run", "action": alert.action, "ticker": alert.ticker}

    raise NotImplementedError(
        "DRY_RUN is false but no live broker integration is configured. "
        "Implement order submission in app/broker.py before disabling DRY_RUN."
    )
