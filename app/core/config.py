from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Transport Reliability and Delay Analytics API"
    project_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://transport_api:transport_api@localhost:5432/transport_api"
    admin_api_key: str = "changeme-admin-key"
    operator_api_key: str = "changeme-operator-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
