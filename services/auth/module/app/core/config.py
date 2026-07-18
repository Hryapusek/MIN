from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.auth.types import SigningBackend


_MODULE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_MODULE_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "messenger-auth"
    environment: str = "development"

    db_driver: str = "postgresql+psycopg"
    db_username: str
    db_password: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_database: str = "messenger"

    token_signing_backend: SigningBackend = SigningBackend.LOCAL
    jwt_issuer: str = "http://localhost:8000"
    jwt_audience: str = "messenger-api"
    access_token_ttl_seconds: int = Field(default=900, ge=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1)

    # These values identify keys; they are not private key material.
    local_signing_key_reference: str = "env:LOCAL_JWT_PRIVATE_KEY_PEM"
    vault_addr: str = "http://localhost:8200"
    vault_transit_mount: str = "transit"
    vault_jwt_key_name: str = "auth-jwt"

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername=self.db_driver,
            username=self.db_username,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_database,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
