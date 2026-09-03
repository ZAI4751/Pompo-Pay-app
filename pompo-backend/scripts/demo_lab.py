"""Shared constants and safety gates for the POMPO demonstration lab.

These identities exist so a human operator can log into each legitimate
authorization context. They are not production staff accounts.

Production seeding/reset requires an explicit confirmation token so a
normal production deploy cannot wipe or create demo data accidentally.
"""

from __future__ import annotations

import os

from app.core.config.base import AppEnvironment

PRODUCTION_CONFIRM_TOKEN = "I_UNDERSTAND_THIS_IS_DEMO_DATA"

DEMO_MERCHANT_NAME = "POMPO Demo Merchant"
DEMO_BRANCH_NAME = "POMPO Demo Branch"
DEMO_TILL_NAME = "POMPO Demo Till"
DEMO_TILL_CODE = "DEMO-TILL-01"

DEMO_ADMIN_EMAIL = "demo.admin@pompo.mw"
DEMO_MERCHANT_EMAIL = "demo.merchant@pompo.mw"
DEMO_CUSTOMER_EMAIL = "demo.customer@pompo.mw"

# Documented operator passwords. Override with env vars in any shared environment.
DEMO_ADMIN_PASSWORD = os.getenv("POMPO_DEMO_ADMIN_PASSWORD", "PompoDemoAdmin2026!")
DEMO_MERCHANT_PASSWORD = os.getenv("POMPO_DEMO_MERCHANT_PASSWORD", "PompoDemoMerch2026!")
DEMO_CUSTOMER_PASSWORD = os.getenv("POMPO_DEMO_CUSTOMER_PASSWORD", "PompoDemoCust2026!")


class DemoLabRefused(RuntimeError):
    """Raised when demo seed/reset is blocked in production."""


def require_demo_lab_allowed(
    app_env: AppEnvironment,
    *,
    confirm: str | None = None,
) -> None:
    """Refuse production unless POMPO_ALLOW_DEMO_SEED matches the confirm token."""
    if app_env is not AppEnvironment.PRODUCTION:
        return
    token = confirm if confirm is not None else os.getenv("POMPO_ALLOW_DEMO_SEED", "")
    if token != PRODUCTION_CONFIRM_TOKEN:
        raise DemoLabRefused(
            "Refusing to mutate demo identities in production. "
            "This script is for local/lab use. To override, set "
            f"POMPO_ALLOW_DEMO_SEED={PRODUCTION_CONFIRM_TOKEN}"
        )
