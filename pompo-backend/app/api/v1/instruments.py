"""Customer payment-method APIs. Token references are never returned."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.models.payment import PaymentInstrument
from app.schemas.instrument import (
    PaymentMethodCatalogItem,
    PaymentMethodCreate,
    PaymentMethodResponse,
)
from app.services.instrument import (
    InstrumentConflictError,
    InstrumentError,
    InstrumentForbiddenError,
    InstrumentInvalidError,
    InstrumentNotFoundError,
    PaymentInstrumentService,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment methods"])


def get_instrument_service(session: DbSessionDep) -> PaymentInstrumentService:
    return PaymentInstrumentService(session)


InstrumentServiceDep = Annotated[PaymentInstrumentService, Depends(get_instrument_service)]


def _error(exc: InstrumentError) -> HTTPException:
    if isinstance(exc, InstrumentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, InstrumentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, InstrumentForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, InstrumentInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _response(row: PaymentInstrument, *, include_customer: bool = False) -> PaymentMethodResponse:
    provider = row.provider
    customer = getattr(row, "customer", None)
    return PaymentMethodResponse(
        id=row.public_identifier,
        provider_code=provider.code.value,
        provider_display_name=provider.display_name,
        instrument_type=row.instrument_type.value,
        display_name=row.display_name,
        masked_identifier=row.masked_identifier,
        status=row.status.value,
        authorization_state=row.authorization_state.value,
        is_default=row.is_default,
        is_sandbox=row.is_sandbox,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        customer_email=customer.email if include_customer and customer is not None else None,
    )


@router.get("/catalog", response_model=list[PaymentMethodCatalogItem])
async def payment_method_catalog(
    service: InstrumentServiceDep,
) -> list[PaymentMethodCatalogItem]:
    return [PaymentMethodCatalogItem(**item) for item in service.catalog()]


@router.get("/admin", response_model=list[PaymentMethodResponse], dependencies=[Depends(require_permission("users:read"))])
async def admin_list_payment_methods(
    current_user: CurrentUserDep,
    service: InstrumentServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[PaymentMethodResponse]:
    try:
        rows = await service.list_admin(current_user, limit=limit, offset=offset)
    except InstrumentError as exc:
        raise _error(exc) from exc
    return [_response(row, include_customer=True) for row in rows]


@router.get("", response_model=list[PaymentMethodResponse])
async def list_payment_methods(
    current_user: CurrentUserDep, service: InstrumentServiceDep
) -> list[PaymentMethodResponse]:
    rows = await service.list_mine(current_user)
    return [_response(row) for row in rows]


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    payload: PaymentMethodCreate,
    current_user: CurrentUserDep,
    service: InstrumentServiceDep,
) -> PaymentMethodResponse:
    try:
        row = await service.enroll(current_user, payload.model_dump())
    except InstrumentError as exc:
        raise _error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _response(row)


@router.get("/{public_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    public_id: str, current_user: CurrentUserDep, service: InstrumentServiceDep
) -> PaymentMethodResponse:
    try:
        row = await service.get_mine(current_user, public_id)
    except InstrumentError as exc:
        raise _error(exc) from exc
    return _response(row)


@router.post("/{public_id}/default", response_model=PaymentMethodResponse)
async def set_default_payment_method(
    public_id: str, current_user: CurrentUserDep, service: InstrumentServiceDep
) -> PaymentMethodResponse:
    try:
        row = await service.set_default(current_user, public_id)
    except InstrumentError as exc:
        raise _error(exc) from exc
    return _response(row)


@router.post("/{public_id}/verify", response_model=PaymentMethodResponse)
async def verify_payment_method(
    public_id: str, current_user: CurrentUserDep, service: InstrumentServiceDep
) -> PaymentMethodResponse:
    try:
        row = await service.verify(current_user, public_id)
    except InstrumentError as exc:
        raise _error(exc) from exc
    return _response(row)


@router.delete("/{public_id}", response_model=PaymentMethodResponse)
async def revoke_payment_method(
    public_id: str, current_user: CurrentUserDep, service: InstrumentServiceDep
) -> PaymentMethodResponse:
    try:
        row = await service.revoke(current_user, public_id)
    except InstrumentError as exc:
        raise _error(exc) from exc
    return _response(row)
