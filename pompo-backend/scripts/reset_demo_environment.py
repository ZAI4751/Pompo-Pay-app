"""Reset POMPO demonstration lab to a known operator baseline.

Developer-only. Not exposed to production users or the mobile UI.

What this does:
  - Revokes every active QR on the POMPO Demo Till so the operator is not
    left with conflicting terminal codes
  - Re-runs the idempotent demo seeder (identities, branch/till, instruments,
    one static QR, one dynamic QR)

What this does NOT do:
  - Global database wipe
  - Deletion of other merchants, customers, or settlements
  - Deletion of historical demo payments (settlement FKs are RESTRICT;
    payment history remains a known baseline the operator can filter)

Usage (local Docker):

    docker compose exec backend python scripts/reset_demo_environment.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config.base import get_settings
from app.database.engine import create_engine, dispose_engine
from app.models import Merchant
from app.models.enums import QRStatus
from app.models.payment import QRCode
from scripts.demo_lab import DEMO_MERCHANT_NAME, DEMO_TILL_CODE, DemoLabRefused, require_demo_lab_allowed
from scripts.seed_demo_environment import seed_demo_environment


async def revoke_demo_terminal_qrs() -> int:
    """Revoke active QRs belonging to the demo merchant. Returns the number revoked."""
    settings = get_settings()
    require_demo_lab_allowed(settings.app_env)
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    revoked = 0
    try:
        async with session_factory() as session:
            merchant = await session.scalar(select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME))
            if merchant is None:
                print("[reset] Demo merchant not found — seed will create it.")
                return 0
            active = (
                await session.execute(
                    select(QRCode).where(
                        QRCode.merchant_id == merchant.id,
                        QRCode.status == QRStatus.ACTIVE,
                    )
                )
            ).scalars().all()
            now = datetime.now(UTC)
            for qr in active:
                qr.status = QRStatus.REVOKED
                qr.revoked_at = now
                revoked += 1
            await session.commit()
            print(f"[reset] Revoked {revoked} active QR(s) for {DEMO_MERCHANT_NAME} ({DEMO_TILL_CODE}).")
            return revoked
    finally:
        await dispose_engine()


async def reset_demo_environment() -> None:
    await revoke_demo_terminal_qrs()
    print("[reset] Re-seeding demonstration identities and baseline QRs...")
    await seed_demo_environment()


if __name__ == "__main__":
    try:
        asyncio.run(reset_demo_environment())
    except DemoLabRefused as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
