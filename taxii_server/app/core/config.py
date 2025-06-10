from typing import List

from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TAXII Server"
    DATABASE_URL: str = "postgresql://postgres:algerie@localhost/taxii_db"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
