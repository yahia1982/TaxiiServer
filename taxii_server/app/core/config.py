from typing import List

from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TAXII Server"
    DATABASE_URL: str = "postgresql://postgres:algerie@localhost/taxii_db"
    JWKS_URLS:List[AnyUrl] = ["https://auth.bfore.ai/file/accespublic/.wellknown/jwks.json", "https://dev-xtl66rao.us.auth0.com/.well-known/jwks.json", "https://bforeai-dev.us.auth0.com/.well-known/jwks.json"]

    model_config = SettingsConfigDict(env_file=".env")



settings = Settings()
