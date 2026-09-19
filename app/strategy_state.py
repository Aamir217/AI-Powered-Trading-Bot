import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings

logger = logging.getLogger("strategy_state")


@dataclass
class StrategyState:
    open_position_id: Optional[str] = None
    open_direction: Optional[str] = None  # "buy" or "sell"
    daily_realized_profit: float = 0.0
    daily_date: dt.date = field(default_factory=dt.date.today)
    halted_today: bool = False

    def roll_day_if_needed(self) -> None:
        today = dt.date.today()
        if today != self.daily_date:
            logger.info("New trading day - resetting daily profit counter")
            self.daily_date = today
            self.daily_realized_profit = 0.0
            self.halted_today = False

    def can_open_trade(self) -> bool:
        self.roll_day_if_needed()
        return self.open_position_id is None and not self.halted_today

    def register_open(self, position_id: str, direction: str) -> None:
        self.open_position_id = position_id
        self.open_direction = direction
        logger.info("Position opened: %s (%s)", position_id, direction)

    def register_close(self, realized_profit: float) -> None:
        self.roll_day_if_needed()
        self.daily_realized_profit += realized_profit
        logger.info(
            "Position %s closed, profit=%.2f, daily total=%.2f",
            self.open_position_id,
            realized_profit,
            self.daily_realized_profit,
        )
        self.open_position_id = None
        self.open_direction = None
        if self.daily_realized_profit >= settings.daily_profit_target_usd:
            self.halted_today = True
            logger.info(
                "Daily profit target of $%.2f reached - no more trades today",
                settings.daily_profit_target_usd,
            )


state = StrategyState()
