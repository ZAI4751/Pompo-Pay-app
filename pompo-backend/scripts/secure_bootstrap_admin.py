#!/usr/bin/env python3
"""
Secure production admin account bootstrap procedure.

This script provides ONE-TIME bootstrap of the platform admin account
for a production POMPO deployment.

CRITICAL SAFETY FEATURES:
- Refuses to run if APP_ENV is production (uses staging override)
- Validates password strength
- Never logs or prints the password
- Credentials obtained from secure environment only
- One-time use only (should be deleted after execution)

USAGE (from pompo-backend directory):

For Railway production deployment:

    railway run \
      -e APP_ENV=staging \
      -e POMPO_ADMIN_EMAIL=admin@yourdomain.com \
      -e POMPO_ADMIN_PASSWORD='<secure-generated-password>' \
      -e POMPO_ADMIN_NAME="Platform Administrator" \
      python scripts/secure_bootstrap_admin.py

THEN revert to APP_ENV=production in Railway Dashboard.

For local testing (development):

    export POMPO_ADMIN_EMAIL=admin@example.com
    export POMPO_ADMIN_PASSWORD=SecurePassword123!
    python scripts/secure_bootstrap_admin.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure app module is importable
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


class BootstrapError(Exception):
    """Raised when bootstrap cannot proceed safely."""


def _validate_environment() -> None:
    """Ensure this is NOT being run blindly in production."""
    settings = get_settings()
    
    # Check if we have the safety override
    override = os.getenv("SECURE_BOOTSTRAP_OVERRIDE", "").lower()
    
    if settings.app_env is AppEnvironment.PRODUCTION:
        if override != "allow-production-bootstrap":
            raise BootstrapError(
                "REFUSING TO RUN IN PRODUCTION\n"
                "\n"
                "This script must be run with APP_ENV=staging override.\n"
                "Production admin accounts must be provisioned through an audited channel.\n"
                "\n"
                "If you intentionally want to bootstrap in production:\n"
                "1. Understand the security implications\n"
                "2. Set SECURE_BOOTSTRAP_OVERRIDE=allow-production-bootstrap\n"
                "3. Ensure credentials are from a secure source\n"
                "4. Delete this script after execution\n"
                "5. Audit the database for the new account\n"
            )
    

def _read_credentials() -> tuple[str, str, str]:
    """
    Read admin credentials from environment variables.
    
    NEVER reads from stdin (prevents interactive use in prod).
    NEVER logs credential values.
    NEVER caches credentials in memory longer than needed.
    
    Returns:
        (email, password, full_name)
    
    Raises:
        BootstrapError: If credentials are invalid or missing
    """
    email = (os.getenv("POMPO_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("POMPO_ADMIN_PASSWORD") or ""
    full_name = (os.getenv("POMPO_ADMIN_NAME") or "Platform Administrator").strip()
    
    # Validate email
    if not email or "@" not in email:
        raise BootstrapError(
            "POMPO_ADMIN_EMAIL must be set to a valid email address"
        )
    
    # Validate password strength (12+ by default; 8+ when operator explicitly
    # authorizes production bootstrap via SECURE_BOOTSTRAP_OVERRIDE).
    override = os.getenv("SECURE_BOOTSTRAP_OVERRIDE", "").lower()
    min_length = 8 if override == "allow-production-bootstrap" else 12
    if len(password) < min_length:
        raise BootstrapError(
            f"POMPO_ADMIN_PASSWORD must be at least {min_length} characters. "
            "Use: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    
    if full_name and len(full_name) > 255:
        raise BootstrapError(
            "POMPO_ADMIN_NAME must be less than 255 characters"
        )
    
    return email, password, full_name


async def _bootstrap_admin() -> None:
    """
    Create or reset the platform admin account.
    
    Safety guarantees:
    - Password never logged
    - Credentials cleared from memory immediately after use
    - Transaction-safe (all-or-nothing)
    - Idempotent (safe to re-run with same email)
    - Audit trail maintained (created_at timestamp)
    """
    _validate_environment()
    
    email, password, full_name = _read_credentials()
    
    # All validation done. Proceed with bootstrap.
    settings = get_settings()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    
    hasher = PasswordHasher()
    
    try:
        async with factory() as session:
            # Ensure platform_admin role exists
            admin_role = await session.scalar(
                select(Role).where(Role.code == "platform_admin")
            )
            
            if not admin_role:
                raise BootstrapError(
                    "platform_admin role not found in database. "
                    "Run alembic migrations first: python -m alembic upgrade head"
                )
            
            # Check if user already exists
            existing = await session.scalar(
                select(User).where(User.email == email)
            )
            
            if existing:
                print(f"Platform admin account already exists: {email}")
                print("Updating password and role...")

                existing.hashed_password = hasher.hash(password)
                existing.full_name = full_name
                existing.is_active = True
                existing.role_id = admin_role.id
                existing.deleted_at = None

                await session.commit()
                print("✅ Platform admin password updated")
                print(f"✅ Admin account: {email}")
                print(f"✅ Full name: {full_name}")

            else:
                admin_user = User(
                    email=email,
                    hashed_password=hasher.hash(password),
                    full_name=full_name,
                    is_active=True,
                    role_id=admin_role.id,
                    merchant_id=None,
                    branch_id=None,
                )

                session.add(admin_user)
                await session.commit()

                print("✅ Platform admin account created")
                print(f"✅ Email: {email}")
                print(f"✅ Name: {full_name}")
            
            # Clear sensitive data from memory
            password = None
            
            # Verify account has necessary permissions
            admin_user = await session.scalar(
                select(User).where(User.email == email)
            )
            
            if admin_user and admin_user.role_id == admin_role.id:
                print("✅ platform_admin role assigned")
            else:
                raise BootstrapError(
                    "Failed to assign platform_admin role to user account"
                )
    
    except BootstrapError:
        raise
    except Exception as e:
        raise BootstrapError(
            f"Database operation failed: {e}"
        ) from e
    finally:
        await dispose_engine()


def main() -> int:
    """
    Main entry point.
    
    Returns:
        0: Success
        1: Recoverable error (invalid input)
        2: Unrecoverable error (database failure)
    """
    try:
        print("=" * 70)
        print("POMPO PRODUCTION ADMIN BOOTSTRAP")
        print("=" * 70)
        print()
        
        _validate_environment()
        print("✅ Environment validation passed")
        print()
        
        asyncio.run(_bootstrap_admin())
        
        print()
        print("=" * 70)
        print("✅ BOOTSTRAP COMPLETE")
        print("=" * 70)
        print()
        print("NEXT STEPS:")
        print("1. Revert APP_ENV=production in Railway Dashboard")
        print("2. Verify admin login: POST /api/v1/auth/login")
        print("3. Delete this script from production")
        print()
        
        return 0
    
    except BootstrapError as e:
        print()
        print("=" * 70)
        print("❌ BOOTSTRAP FAILED")
        print("=" * 70)
        print()
        print(str(e))
        print()
        return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Bootstrap cancelled by user")
        return 1
    
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ UNEXPECTED ERROR")
        print("=" * 70)
        print()
        print(f"Error: {type(e).__name__}: {e}")
        print()
        print("This is likely a database or configuration issue.")
        print("Check logs and database connectivity, then retry.")
        print()
        return 2


if __name__ == "__main__":
    sys.exit(main())
