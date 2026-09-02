#!/usr/bin/env python3
"""Seed a throwaway local admin and run the M013 sandbox verifier.

Never prints passwords, API keys, or tokens. Refuses production APP_ENV.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("POMPO_API_BASE", "http://127.0.0.1:8000/api/v1")
os.environ.setdefault("POMPO_WEBHOOK_URL", "https://httpbingo.org/status/200")
os.environ["POMPO_ADMIN_EMAIL"] = os.environ.get("POMPO_ADMIN_EMAIL") or "m013local@pompo.test"
if not os.environ.get("POMPO_ADMIN_PASSWORD"):
    os.environ["POMPO_ADMIN_PASSWORD"] = secrets.token_urlsafe(24)


async def _run() -> int:
    from app.core.config.base import AppEnvironment, get_settings

    settings = get_settings()
    if settings.app_env is AppEnvironment.PRODUCTION:
        print("Refusing to seed a convenience admin in production")
        return 2

    import importlib.util

    seed_path = _ROOT / "scripts" / "seed_admin.py"
    seed_spec = importlib.util.spec_from_file_location("seed_admin", seed_path)
    if seed_spec is None or seed_spec.loader is None:
        print("Unable to load seed_admin.py")
        return 2
    seed_mod = importlib.util.module_from_spec(seed_spec)
    seed_spec.loader.exec_module(seed_mod)
    await seed_mod.seed_admin()

    verify_path = _ROOT / "scripts" / "verify_m013_sandbox.py"
    verify_spec = importlib.util.spec_from_file_location("verify_m013_sandbox", verify_path)
    if verify_spec is None or verify_spec.loader is None:
        print("Unable to load verify_m013_sandbox.py")
        return 2
    verify_mod = importlib.util.module_from_spec(verify_spec)
    verify_spec.loader.exec_module(verify_mod)
    return await verify_mod.main()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
