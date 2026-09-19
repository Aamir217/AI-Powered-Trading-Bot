from typing import Literal, Optional

from pydantic import BaseModel, Field


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
