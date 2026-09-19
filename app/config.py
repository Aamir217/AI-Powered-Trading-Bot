from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    tradingview_webhook_secret: str
    claude_model: str = "claude-sonnet-5"
    dry_run: bool = True

    # MetaApi (cloud MT4/MT5) credentials - required only when dry_run is false.
    metaapi_token: str = ""
    metaapi_account_id: str = ""

    # BLACK-GOLD strategy rules
    lot_size: float = 0.01
    take_profit_usd: float = 10.0
    daily_profit_target_usd: float = 10.0
    tp_poll_seconds: float = 5.0


settings = Settings()
