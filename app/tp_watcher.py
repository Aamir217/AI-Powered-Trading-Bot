import asyncio
import logging

from app.config import settings
from app.metaapi_broker import close_position, get_position
from app.strategy_state import state

logger = logging.getLogger("tp_watcher")


async def watch_take_profit() -> None:
    """Background loop: close the open position the moment its floating
    profit reaches take_profit_usd. Runs only when DRY_RUN is false.
    """
    while True:
        try:
            if state.open_position_id is not None:
                pos = await get_position(state.open_position_id)
                if pos is None:
                    # Closed outside the bot (SL, manual, margin call) - resync.
                    logger.info(
                        "Tracked position %s no longer open - resyncing state",
                        state.open_position_id,
                    )
                    state.register_close(0.0)
                elif pos.get("profit", 0.0) >= settings.take_profit_usd:
                    profit = pos.get("profit", 0.0)
                    await close_position(state.open_position_id)
                    logger.info(
                        "Take-profit hit ($%.2f): closed position %s",
                        profit,
                        state.open_position_id,
                    )
                    state.register_close(profit)
        except Exception:
            logger.exception("Error in take-profit watcher")
        await asyncio.sleep(settings.tp_poll_seconds)
