"""Payment-core endpoints shared by POS and customer clients."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.payments.providers import ProviderError
from app.payments.registry import ProviderRegistry
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment import (
    PaymentConflictError,
    PaymentError,
    PaymentForbiddenError,
    PaymentNotFoundError,
    PaymentService,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


def get_payment_service(session: DbSessionDep) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


def _error(exc: PaymentError) -> HTTPException:
    if isinstance(exc, PaymentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PaymentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, PaymentForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def create_payment(
    payload: PaymentCreate,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    try:
        return await service.create_payment(current_user, payload.model_dump())
    except PaymentError as exc:
        raise _error(exc) from exc


@router.post(
    "/{reference}/cancel",
    response_model=PaymentResponse,
    dependencies=[Depends(require_permission("transactions:cancel"))],
)
async def cancel_payment(
    reference: str,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    try:
        return await service.cancel_payment(current_user, reference)
    except PaymentError as exc:
        raise _error(exc) from exc


@router.post(
    "/{reference}/process",
    response_model=PaymentResponse,
    dependencies=[Depends(require_permission("transactions:update"))],
)
async def process_payment(
    reference: str,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    try:
        return await service.process_payment(current_user, reference)
    except PaymentError as exc:
        raise _error(exc) from exc


@router.get("/providers", dependencies=[Depends(require_permission("transactions:read"))])
async def list_providers() -> list[dict[str, object]]:
    return [
        {"code": adapter.code, "capabilities": adapter.capabilities.__dict__}
        for adapter in ProviderRegistry().list()
    ]


@router.get(
    "/providers/{provider_code}/capabilities",
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def provider_capabilities(provider_code: str) -> dict[str, object]:
    try:
        return ProviderRegistry().capabilities(provider_code).__dict__
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.get(
    "/{reference}",
    response_model=PaymentResponse,
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def get_payment(
    reference: str,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    try:
        return await service.get_payment(current_user, reference)
    except PaymentError as exc:
        raise _error(exc) from exc
