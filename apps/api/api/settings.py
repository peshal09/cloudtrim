from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment / .env."""

    model_config = SettingsConfigDict(env_prefix="CLOUDTRIM_", env_file=".env", extra="ignore")

    app_name: str = "CloudTrim API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"


settings = Settings()
