"""Create or reset a platform-administrator account for local development.

Without at least one account there is no way to exercise the real login flow,
so this exists to bootstrap the admin frontend against the backend.

Credentials come from the environment and are never written to source, printed,
or logged:

    POMPO_ADMIN_EMAIL     required
    POMPO_ADMIN_PASSWORD  required (minimum 8 characters)
    POMPO_ADMIN_NAME      optional, defaults to "Platform Administrator"

Usage:

    docker compose exec -e POMPO_ADMIN_EMAIL=... -e POMPO_ADMIN_PASSWORD=... \
        backend python scripts/seed_admin.py

Refuses to run when APP_ENV is production: real administrators must be
provisioned through an audited path, not a convenience script.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config.base import AppEnvironment, get_settings
from app.core.security.password import PasswordHasher
from app.database.engine import create_engine, dispose_engine
from app.models import Role, User
from app.permissions.catalog import SYSTEM_ROLES

ADMIN_ROLE_CODE = "platform_admin"
MIN_PASSWORD_LENGTH = 8


class SeedError(RuntimeError):
    """Raised when the script cannot safely proceed."""


def _read_credentials() -> tuple[str, str, str]:
    """Read and validate admin credentials from the environment."""
    email = (os.getenv("POMPO_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("POMPO_ADMIN_PASSWORD") or ""
    full_name = (os.getenv("POMPO_ADMIN_NAME") or "Platform Administrator").strip()

    if not email or "@" not in email:
        raise SeedError("POMPO_ADMIN_EMAIL must be set to a valid email address")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SeedError(
            f"POMPO_ADMIN_PASSWORD must be set and at least {MIN_PASSWORD_LENGTH} characters"
        )

    return email, password, full_name


async def seed_admin() -> None:
    """Create the platform admin, or reset its password if it already exists."""
    settings = get_settings()
    if settings.app_env is AppEnvironment.PRODUCTION:
        raise SeedError(
            "Refusing to run in production; provision administrators via an audited path"
        )

    email, password, full_name = _read_credentials()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    try:
        async with factory() as session:
            role = await session.scalar(select(Role).where(Role.code == ADMIN_ROLE_CODE))
            if role is None:
                raise SeedError(
                    f"Role {ADMIN_ROLE_CODE!r} not found — run scripts/seed_rbac.py first "
                    f"(known system roles: {', '.join(sorted(SYSTEM_ROLES))})"
                )

            hashed_password = PasswordHasher().hash(password)
            user = await session.scalar(select(User).where(User.email == email))

            if user is None:
                session.add(
                    User(
                        email=email,
                        full_name=full_name,
                        hashed_password=hashed_password,
                        role_id=role.id,
                        # Platform administrators are not scoped to a tenant.
                        merchant_id=None,
                        branch_id=None,
                        is_active=True,
                    )
                )
                action = "created"
            else:
                user.hashed_password = hashed_password
                user.role_id = role.id
                user.is_active = True
                # Undo a previous soft delete so the account can authenticate.
                user.deleted_at = None
                action = "password reset"

            await session.commit()
    finally:
        await dispose_engine()

    print(f"Platform administrator {action}: {email} (role: {ADMIN_ROLE_CODE})")


if __name__ == "__main__":
    try:
        asyncio.run(seed_admin())
    except SeedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
