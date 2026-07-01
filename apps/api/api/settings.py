from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment / .env."""

    model_config = SettingsConfigDict(env_prefix="CLOUDTRIM_", env_file=".env", extra="ignore")

    app_name: str = "CloudTrim API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    # Browser origins allowed to call the API (the Next.js web app).
    cors_origins: list[str] = ["http://localhost:3000"]
    # Week 3: set both to run async (enqueue -> worker -> Postgres). With neither,
    # the API runs synchronously against an in-memory store (zero-dependency demo).
    database_url: str | None = None
    redis_url: str | None = None
    # Week 4 — GitHub App. Webhook signature secret + a token (App installation
    # token or PAT) used as the API bearer. Live tier only; tests inject a fake.
    github_webhook_secret: str | None = None
    github_token: str | None = None
    github_api_url: str = "https://api.github.com"
    # Production hardening (Week 5), all opt-in so the demo stays zero-config.
    api_keys: str = ""  # comma-separated; empty -> auth disabled (open)
    rate_limit_per_minute: int = 0  # 0 -> disabled

    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


settings = Settings()
