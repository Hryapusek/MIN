from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from messenger.shared.signing.types import InitialKeyActivationPolicy, LocalKeyBootstrapPolicy, SigningBackend


_MODULE_ROOT = Path(__file__).resolve().parents[3]


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
    db_username: str = "messenger"
    db_password: str = "change-me"
    db_host: str = "localhost"
    db_port: int = 5432
    db_database: str = "messenger"

    token_signing_backend: SigningBackend = SigningBackend.LOCAL
    signing_provider_name: str = Field(default="local-primary", min_length=1, max_length=64)
    signing_algorithm: Literal["RS256"] = "RS256"
    initial_key_activation_policy: InitialKeyActivationPolicy = InitialKeyActivationPolicy.IF_REGISTRY_EMPTY
    key_manager_sync_interval_seconds: int = Field(default=30, ge=1)

    jwt_issuer: str = "http://localhost:8000"
    jwt_audience: str = "messenger-api"
    access_token_ttl_seconds: int = Field(default=900, ge=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1)

    local_signing_key_directory: Path = _MODULE_ROOT / ".local" / "signing-keys"
    local_key_bootstrap_policy: LocalKeyBootstrapPolicy = LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY
    local_rsa_key_size: int = Field(default=2048, ge=2048)
    local_signing_strict_permissions: bool = False

    vault_addr: str = "http://localhost:8200"
    vault_transit_mount: str = "transit"
    vault_jwt_key_name: str = "auth-jwt"
    vault_token_file: Path | None = None

    @property
    def resolved_local_signing_key_directory(self) -> Path:
        path = self.local_signing_key_directory.expanduser()
        if path.is_absolute():
            return path
        return (_MODULE_ROOT / path).resolve()

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
