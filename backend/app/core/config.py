from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, PostgresDsn, field_validator


class Settings(BaseSettings):
    project_name: str = "Triage System"
    api_prefix: str = "/api"
    backend_cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: PostgresDsn | str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/triage")
    use_pgvector: bool = True
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 14

    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_http_path: Optional[str] = None
    databricks_warehouse_id: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("backend_cors_origins", mode="before")
    def split_cors(cls, value):  # noqa: N805
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @field_validator("use_pgvector", mode="before")
    def disable_pgvector_for_sqlite(cls, value, info):  # noqa: N805
        url = str(info.data.get("database_url") or self_default_database())  # type: ignore
        if url.startswith("sqlite"):
            return False
        return value


def self_default_database() -> str:
    return "postgresql+psycopg://postgres:postgres@localhost:5432/triage"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
