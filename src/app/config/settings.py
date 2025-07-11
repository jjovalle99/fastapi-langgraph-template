from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.database import DatabaseConfig
from app.config.paths import PathsConfig


class Settings(BaseSettings):
    environment: Literal["dev", "stage", "prod"] = Field(default="dev")
    db: DatabaseConfig = Field(default=...)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    def model_post_init(self, __context: Any) -> None:
        """Load the remaining environment variables from the .env file."""
        load_dotenv(dotenv_path=".env")
