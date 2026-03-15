from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://govtracker:govtracker@postgres:5432/govtracker"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://govtracker:govtracker@postgres:5432/govtracker"

    GOVUK_BASE_URL: str = "https://www.gov.uk"

    PARLIAMENT_MEMBERS_API_URL: str = "https://members-api.parliament.uk/api"
    PARLIAMENT_BILLS_API_URL: str = "https://bills-api.parliament.uk/api/v1"
    PARLIAMENT_QUESTIONS_API_URL: str = "https://questions-statements-api.parliament.uk/api"
    PARLIAMENT_DIVISIONS_API_URL: str = "https://commonsvotes-api.parliament.uk/data"

    SPACY_MODEL: str = "en_core_web_sm"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
