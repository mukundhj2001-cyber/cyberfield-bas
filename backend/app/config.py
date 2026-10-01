from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{DATA_DIR / 'cyberfield.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    llm_provider: str = "mock"  # mock | openai | anthropic
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
    company_name: str = "Cyberfield Support"
    brand_name: str = "Cyberfield BAS"
    ai_name: str = "Cyberfield AI"

    # Gmail — leave unset for mock sync (default)
    gmail_mode: str = "mock"  # mock | oauth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_refresh_token: str | None = None

    # n8n webhooks — when set, require X-Webhook-Secret header
    n8n_webhook_secret: str | None = None

    # Business inbox filter — drop newsletters / social / marketing on ingest
    business_filter_enabled: bool = True
    # Comma-separated domains always treated as business (e.g. acme.com,vendor.example)
    business_email_domains: str = ""
    # Optional LLM refinement for borderline mail when a real provider is keyed
    business_filter_use_llm: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
