"""Production CORS allow-list: union canonical hosts, never wildcard, never localhost."""

from app.core.config.base import (
    AppEnvironment,
    CANONICAL_PRODUCTION_CORS_ORIGINS,
    ProductionSettings,
)

_REQUIRED = {
    "app_env": AppEnvironment.PRODUCTION,
    "debug": False,
    "secret_key": "a" * 48,
    "jwt_secret_key": "b" * 48,
    "database_url": "postgresql+asyncpg://u:p@localhost:5432/pompo",
    "redis_url": "redis://localhost:6379/0",
    "celery_broker_url": "redis://localhost:6379/1",
    "celery_result_backend": "redis://localhost:6379/2",
    "allowed_hosts": "pompo-api-production.up.railway.app",
}


def test_production_cors_unions_canonical_origins_without_dropping_existing() -> None:
    settings = ProductionSettings(
        **_REQUIRED,
        cors_origins="https://pompo-pay-app.vercel.app,https://preview-extra.vercel.app/",
    )
    origins = settings.cors_origins_list
    assert "https://pay.pompo.mw" in origins
    assert "https://pompo-pay-app.vercel.app" in origins
    assert "https://preview-extra.vercel.app" in origins
    assert origins.count("https://pompo-pay-app.vercel.app") == 1
    assert "*" not in origins


def test_production_cors_strips_wildcard_and_localhost() -> None:
    settings = ProductionSettings(
        **_REQUIRED,
        cors_origins="*,http://localhost:3000,https://legacy-admin.example",
    )
    origins = settings.cors_origins_list
    assert "*" not in origins
    assert "http://localhost:3000" not in origins
    assert "https://legacy-admin.example" in origins
    for expected in CANONICAL_PRODUCTION_CORS_ORIGINS:
        assert expected in origins


def test_production_default_cors_is_canonical_https_only() -> None:
    settings = ProductionSettings(**_REQUIRED)
    assert settings.debug is False
    assert settings.cors_origins_list == list(CANONICAL_PRODUCTION_CORS_ORIGINS)
