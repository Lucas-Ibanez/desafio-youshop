"""Configuração tipada lida do .env (CONTEXTO, seção 17.1)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: SecretStr = SecretStr("")
    promessa_db_url: str = "sqlite:///var/promessa.db"
    checker_model: str = "gemini-3.5-flash-lite"
    classifier_model: str = "gemini-3.5-flash-lite"
    explainer_model: str = "gemini-3.5-flash-lite"
    checker_use_llm: bool = True
    llm_offline: bool = False
    llm_cache_dir: str = ".cache/llm"
    confidence_threshold: float = 0.8
    min_sales_for_indicator: int = 30
    urgency_stale_days: int = 7
    link_base_url: str = "https://youshop.example/l/"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def has_api_key(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.gemini_api_key.get_secret_value().strip())
