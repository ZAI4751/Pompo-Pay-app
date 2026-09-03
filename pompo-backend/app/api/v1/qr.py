"""QR payment endpoints."""

from __future__ import annotations

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.core.config.base import get_settings
from app.models.payment import QRCode
from app.schemas.qr import (
    DynamicQRCreate,
    QRInspectResponse,
    QRResponse,
    StaticQRCreate,
)
from app.services.qr import (
    QRConflictError,
    QRError,
    QRForbiddenError,
    QRInvalidError,
    QRNotFoundError,
    QRService,
)

router = APIRouter(prefix="/qr", tags=["QR Payments"])


def get_qr_service(session: DbSessionDep) -> QRService:
    return QRService(session)


QRServiceDep = Annotated[QRService, Depends(get_qr_service)]


def _error(exc: QRError) -> HTTPException:
    if isinstance(exc, QRNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, QRConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, QRForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _payment_url(public_identifier: str) -> str:
    settings = get_settings()
    return f"{settings.public_checkout_base_url.rstrip('/')}/p/{public_identifier}"


def _qr_response(qr: QRCode) -> QRResponse:
    return QRResponse(
        public_identifier=qr.public_identifier,
        qr_type=qr.qr_type.value,
        version=qr.version,
        status=qr.status.value,
        encoded_payload=qr.payload,
        payment_url=_payment_url(qr.public_identifier),
        merchant_id=qr.merchant_id,
        branch_id=qr.branch_id,
        till_id=qr.till_id,
        merchant_name=qr.merchant.name,
        branch_name=qr.branch.name,
        till_name=qr.till.name,
        amount=qr.amount,
        currency=qr.currency,
        payment_reference=qr.payment_reference,
        expires_at=qr.expires_at,
        created_at=qr.created_at,
        revoked_at=qr.revoked_at,
    )


def _inspect_response(qr: QRCode) -> QRInspectResponse:
    return QRInspectResponse(
        public_identifier=qr.public_identifier,
        qr_type=qr.qr_type.value,
        version=qr.version,
        status=qr.status.value,
        merchant_name=qr.merchant.name,
        branch_name=qr.branch.name,
        till_name=qr.till.name,
        amount=qr.amount,
        currency=qr.currency,
        payment_reference=qr.payment_reference,
        expires_at=qr.expires_at,
        payment_url=_payment_url(qr.public_identifier),
    )


@router.post(
    "/static",
    response_model=QRResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("qr:create"))],
)
async def create_static_qr(
    payload: StaticQRCreate,
    current_user: CurrentUserDep,
    service: QRServiceDep,
) -> QRResponse:
    try:
        qr = await service.create_static_qr(current_user, payload.model_dump())
    except QRError as exc:
        raise _error(exc) from exc
    return _qr_response(qr)


@router.post(
    "/dynamic",
    response_model=QRResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("qr:create"))],
)
async def create_dynamic_qr(
    payload: DynamicQRCreate,
    current_user: CurrentUserDep,
    service: QRServiceDep,
) -> QRResponse:
    try:
        qr = await service.create_dynamic_qr(current_user, payload.model_dump())
    except QRError as exc:
        raise _error(exc) from exc
    return _qr_response(qr)


@router.get(
    "",
    response_model=list[QRResponse],
    dependencies=[Depends(require_permission("qr:read"))],
)
async def list_qrs(
    current_user: CurrentUserDep,
    service: QRServiceDep,
    till_id: UUID | None = Query(default=None),
) -> list[QRResponse]:
    try:
        rows = await service.list_qrs(current_user, till_id=till_id)
    except QRError as exc:
        raise _error(exc) from exc
    return [_qr_response(qr) for qr in rows]


@router.get("/{public_identifier}", response_model=QRInspectResponse)
async def inspect_qr(
    public_identifier: str,
    service: QRServiceDep,
    allow_inactive: bool = Query(default=False),
) -> QRInspectResponse:
    """Public scan preview — safe merchant context only."""
    try:
        qr = await service.inspect_qr(public_identifier, allow_inactive=allow_inactive)
    except QRError as exc:
        raise _error(exc) from exc
    return _inspect_response(qr)


@router.get(
    "/{public_identifier}/admin",
    response_model=QRResponse,
    dependencies=[Depends(require_permission("qr:read"))],
)
async def get_qr_admin(
    public_identifier: str,
    current_user: CurrentUserDep,
    service: QRServiceDep,
) -> QRResponse:
    try:
        qr = await service.get_qr(current_user, public_identifier)
    except QRError as exc:
        raise _error(exc) from exc
    return _qr_response(qr)


@router.post(
    "/{public_identifier}/revoke",
    response_model=QRResponse,
    dependencies=[Depends(require_permission("qr:revoke"))],
)
async def revoke_qr(
    public_identifier: str,
    current_user: CurrentUserDep,
    service: QRServiceDep,
) -> QRResponse:
    try:
        qr = await service.revoke_qr(current_user, public_identifier)
    except QRError as exc:
        raise _error(exc) from exc
    return _qr_response(qr)
