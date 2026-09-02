"""Base application settings using Pydantic BaseSettings."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class BaseAppSettings(BaseSettings):
    """Shared settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_name: str = "POMPO"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = Field(min_length=32)
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000"

    database_url: PostgresDsn
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)
    database_pool_timeout: int = Field(default=30, ge=1)
    database_echo: bool = False

    redis_url: RedisDsn
    redis_max_connections: int = Field(default=20, ge=1, le=200)

    celery_broker_url: RedisDsn
    celery_result_backend: RedisDsn

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1)

    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_auth_failures: int = Field(default=20, ge=1)
    outbound_webhook_timeout_seconds: int = Field(default=10, ge=1, le=60)
    outbound_webhook_max_attempts: int = Field(default=5, ge=1, le=20)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def validate_secret_strength(cls, value: str, info) -> str:
        """Reject placeholder secrets in non-development environments."""
        placeholder_markers = ("change-me", "changeme", "replace-me", "your-secret")
        lowered = value.lower()
        if any(marker in lowered for marker in placeholder_markers):
            env = info.data.get("app_env", AppEnvironment.DEVELOPMENT)
            if env == AppEnvironment.PRODUCTION:
                raise ValueError(
                    f"{info.field_name} must be replaced with a secure value in production"
                )
        return value

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse comma-separated allowed hosts."""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_str(self) -> str:
        """Return database URL as a plain string for SQLAlchemy."""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """Return Redis URL as a plain string."""
        return str(self.redis_url)

    @property
    def celery_broker_url_str(self) -> str:
        """Return Celery broker URL as a plain string."""
        return str(self.celery_broker_url)

    @property
    def celery_result_backend_str(self) -> str:
        """Return Celery result backend URL as a plain string."""
        return str(self.celery_result_backend)


class DevelopmentSettings(BaseAppSettings):
    """Development environment overrides."""

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"
    log_json: bool = False

    # The admin frontend is reached as either host name during local work, and
    # they are distinct origins to the browser. Listing both here avoids the
    # failure where the app loads but every API call is blocked by CORS.
    # Production inherits the restrictive base default and must set
    # CORS_ORIGINS explicitly.
    allowed_hosts: str = "localhost,127.0.0.1,[::1],backend"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # An admin dashboard issues many calls per screen, and inside Docker every
    # request from the host arrives with the gateway's IP — so one shared bucket
    # covers the whole development session. The production default stays at 100.
    rate_limit_requests: int = Field(default=1000, ge=1)


class TestingSettings(BaseAppSettings):
    """Testing environment overrides."""

    app_env: AppEnvironment = AppEnvironment.TESTING
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"
    log_json: bool = False
    allowed_hosts: str = "*"
    database_pool_size: int = 5
    database_max_overflow: int = 5
    # GitHub CI and local pytest share one Redis IP bucket (127.0.0.1) across
    # the full HTTP suite. Production stays at 100. Dedicated tests still
    # assert 429 via a middleware stub limit of 1 or per-client rate_limit_requests.
    rate_limit_requests: int = Field(default=10000, ge=1)


class ProductionSettings(BaseAppSettings):
    """Production environment overrides."""

    app_env: AppEnvironment = AppEnvironment.PRODUCTION
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = True
    database_echo: bool = False


def _resolve_settings_class() -> type[BaseAppSettings]:
    """Select settings class based on APP_ENV environment variable."""
    import os

    env = os.getenv("APP_ENV", AppEnvironment.DEVELOPMENT.value).lower()
    mapping: dict[str, type[BaseAppSettings]] = {
        AppEnvironment.DEVELOPMENT.value: DevelopmentSettings,
        AppEnvironment.TESTING.value: TestingSettings,
        AppEnvironment.PRODUCTION.value: ProductionSettings,
    }
    return mapping.get(env, DevelopmentSettings)


@lru_cache
def get_settings() -> BaseAppSettings:
    """Return cached settings instance for dependency injection."""
    settings_class = _resolve_settings_class()
    return settings_class()
