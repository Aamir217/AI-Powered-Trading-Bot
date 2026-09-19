from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    tradingview_webhook_secret: str
    claude_model: str = "claude-sonnet-5"
    dry_run: bool = True


settings = Settings()
