from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TradingViewAlert(BaseModel):
    """Shape of the JSON message configured in a TradingView alert.

    See README.md for the alert message template this maps to.
    """

    secret: str
    ticker: str
    action: Literal["buy", "sell", "close"]
    price: float
    strategy: Optional[str] = None
    interval: Optional[str] = None
    timestamp: Optional[str] = None
    indicators: Optional[dict] = Field(default_factory=dict)


class TradeDecision(BaseModel):
    approved: bool
    reasoning: str
    confidence: float


class StrategyAlert(BaseModel):
    """Payload for the deterministic BLACK-GOLD indicator webhook.

    One alert per TradingView alertcondition: buy on the green dot, sell on
    the red dot, close on either black (exit) dot.
    """

    secret: str
    action: Literal["buy", "sell", "close"]
    ticker: str

    @field_validator("ticker")
    @classmethod
    def strip_exchange_prefix(cls, v: str) -> str:
        # TradingView tickers often look like "OANDA:XAUUSD" - MetaApi wants
        # just the broker symbol.
        return v.split(":")[-1]
