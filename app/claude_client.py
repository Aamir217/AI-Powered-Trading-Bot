import json

from anthropic import Anthropic

from app.config import settings
from app.models import TradeDecision, TradingViewAlert

_client = Anthropic(api_key=settings.anthropic_api_key)

_TOOL = {
    "name": "record_trade_decision",
    "description": "Record whether the incoming TradingView signal should be acted on.",
    "input_schema": {
        "type": "object",
        "properties": {
            "approved": {
                "type": "boolean",
                "description": "Whether the trade signal should be executed.",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation for the decision.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in this decision, from 0.0 to 1.0.",
            },
        },
        "required": ["approved", "reasoning", "confidence"],
    },
}


def analyze_signal(alert: TradingViewAlert) -> TradeDecision:
    """Ask Claude to sanity-check a TradingView alert before it is acted on."""
    prompt = (
        "A TradingView alert fired for the following signal. Decide whether "
        "it looks reasonable to act on, given only the information provided. "
        "Be conservative: if the signal looks noisy, contradictory, or you lack "
        "enough context, set approved=false.\n\n"
        f"{json.dumps(alert.model_dump(exclude={'secret'}), indent=2)}"
    )

    response = _client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "record_trade_decision"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_trade_decision":
            return TradeDecision(**block.input)

    raise RuntimeError("Claude did not return a trade decision")
