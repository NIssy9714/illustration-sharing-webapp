from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(default="dev", validation_alias="APP_ENV")
    app_name: str = Field(default="portfolio-api", validation_alias="APP_NAME")

    secret_key: str = Field(validation_alias="SECRET_KEY")
    database_url: str = Field(validation_alias="DATABASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()

