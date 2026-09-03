"""Safety gates for the demonstration lab scripts."""

from app.core.config.base import AppEnvironment
from scripts.demo_lab import (
    PRODUCTION_CONFIRM_TOKEN,
    DemoLabRefused,
    require_demo_lab_allowed,
)


def test_demo_lab_refuses_production_without_confirm_token() -> None:
    try:
        require_demo_lab_allowed(AppEnvironment.PRODUCTION, confirm="")
        raise AssertionError("expected DemoLabRefused")
    except DemoLabRefused:
        pass


def test_demo_lab_allows_production_with_confirm_token() -> None:
    require_demo_lab_allowed(AppEnvironment.PRODUCTION, confirm=PRODUCTION_CONFIRM_TOKEN)


def test_demo_lab_allows_development_and_testing() -> None:
    require_demo_lab_allowed(AppEnvironment.DEVELOPMENT)
    require_demo_lab_allowed(AppEnvironment.TESTING)
