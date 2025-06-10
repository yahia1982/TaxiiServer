from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TAXII Server"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://postgres:algerie@localhost/taxii_db"
    # Secrets for JWT
    SECRET_KEY: str = "a_very_secret_key"  # CHANGE THIS!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env")

    # First Superuser (for initial setup or development)
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "changethispassword"
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"


settings = Settings()
