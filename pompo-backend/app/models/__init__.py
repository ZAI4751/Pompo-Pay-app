"""SQLAlchemy models package.

Importing this package registers every mapped class on ``Base.metadata`` —
required for Alembic autogenerate and for ``Base.metadata.create_all`` in
tests. Always import models via this package (``from app.models import Base``
or ``import app.models``) rather than importing individual model modules
directly in migration/bootstrap code, or new models may be silently excluded
from metadata.
"""

from app.models.base import Base
from app.models.organization import Branch, Merchant, Till
from app.models.user import Permission, Role, RolePermission, User
from app.models.auth import RefreshSession
from app.models.payment import (
    PaymentAttempt,
    PaymentProvider,
    QRCode,
    Receipt,
    Transaction,
    WebhookEvent,
)
from app.models.audit import APIKey, AuditLog
from app.models.settlement import (
    PricingSchedule,
    ReconciliationRecord,
    ReconciliationRun,
    Settlement,
    SettlementBatch,
)

__all__ = [
    "Base",
    "Merchant",
    "Branch",
    "Till",
    "Role",
    "Permission",
    "RolePermission",
    "User",
    "RefreshSession",
    "PaymentProvider",
    "Transaction",
    "PaymentAttempt",
    "WebhookEvent",
    "QRCode",
    "Receipt",
    "APIKey",
    "AuditLog",
    "PricingSchedule",
    "SettlementBatch",
    "Settlement",
    "ReconciliationRun",
    "ReconciliationRecord",
]
