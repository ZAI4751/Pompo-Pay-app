"""Idempotently seed sandbox payment-provider catalog rows.

Refuses to run when APP_ENV is production. Does not store secrets.

    docker compose exec backend python scripts/seed_providers.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config.base import get_settings
from app.database.engine import create_engine, dispose_engine
from app.payments.catalog import (
    ProductionCatalogSeedError,
    ensure_non_production_catalog_seed,
    seed_provider_catalog,
)


async def seed_providers() -> None:
    settings = get_settings()
    ensure_non_production_catalog_seed(settings.app_env)

    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            created = await seed_provider_catalog(session)
            await session.commit()
    finally:
        await dispose_engine()

    print(f"Provider catalog seed complete; created {created} row(s)")


if __name__ == "__main__":
    try:
        asyncio.run(seed_providers())
    except ProductionCatalogSeedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
