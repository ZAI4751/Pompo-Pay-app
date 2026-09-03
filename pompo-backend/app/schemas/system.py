"""Read-only platform configuration projection for Master Admin.

These fields already exist on BaseAppSettings. The API never returns secrets
or connection strings, and it does not accept writes — runtime mutation of
environment configuration is not a supported capability.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field

from app.core.config.base import BaseAppSettings


_SECRET_FIELD_NAMES = frozenset(
    {
        "secret_key",
        "jwt_secret_key",
        "database_url",
        "database_url_str",
        "redis_url",
        "redis_url_str",
        "celery_broker_url",
        "celery_broker_url_str",
        "celery_result_backend",
        "celery_result_backend_str",
    }
)


class PlatformConfigResponse(BaseModel):
    """Safe, non-secret snapshot of process configuration."""

    configuration_source: Literal["environment"] = Field(
        default="environment",
        description="Values are loaded from process environment at startup.",
    )
    writable: Literal[False] = Field(
        default=False,
        description="This projection is read-only. Deploy a new environment to change it.",
    )
    app_name: str
    app_version: str
    app_env: str
    debug: bool
    api_v1_prefix: str
    allowed_hosts: list[str]
    cors_origins: list[str]
    database_pool_size: int
    database_max_overflow: int
    database_pool_timeout: int
    database_echo: bool
    redis_max_connections: int
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    jwt_refresh_token_expire_days: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    rate_limit_auth_failures: int
    outbound_webhook_timeout_seconds: int
    outbound_webhook_max_attempts: int
    log_level: str
    log_json: bool

    @classmethod
    def from_settings(cls, settings: BaseAppSettings) -> Self:
        """Project environment settings without secrets or DSNs."""
        return cls(
            app_name=settings.app_name,
            app_version=settings.app_version,
            app_env=settings.app_env.value,
            debug=settings.debug,
            api_v1_prefix=settings.api_v1_prefix,
            allowed_hosts=settings.allowed_hosts_list,
            cors_origins=settings.cors_origins_list,
            database_pool_size=settings.database_pool_size,
            database_max_overflow=settings.database_max_overflow,
            database_pool_timeout=settings.database_pool_timeout,
            database_echo=settings.database_echo,
            redis_max_connections=settings.redis_max_connections,
            jwt_algorithm=settings.jwt_algorithm,
            jwt_access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
            jwt_refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
            rate_limit_requests=settings.rate_limit_requests,
            rate_limit_window_seconds=settings.rate_limit_window_seconds,
            rate_limit_auth_failures=settings.rate_limit_auth_failures,
            outbound_webhook_timeout_seconds=settings.outbound_webhook_timeout_seconds,
            outbound_webhook_max_attempts=settings.outbound_webhook_max_attempts,
            log_level=settings.log_level,
            log_json=settings.log_json,
        )

    @staticmethod
    def secret_field_names() -> frozenset[str]:
        return _SECRET_FIELD_NAMES
