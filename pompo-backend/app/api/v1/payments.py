"""Payment-core endpoints shared by POS and customer clients."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.payments.providers import ProviderError
from app.payments.registry import ProviderRegistry
from app.api.v1.provider_views import catalog_response
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    ProviderCatalogResponse,
    ProviderCatalogUpdate,
)
from app.services.payment import (
    PaymentConflictError,
    PaymentError,
    PaymentForbiddenError,
    PaymentNotFoundError,
    PaymentService,
)
from app.services.providers import (
    ProviderCatalogConflictError,
    ProviderCatalogError,
    ProviderCatalogForbiddenError,
    ProviderCatalogInvalidError,
    ProviderCatalogNotFoundError,
    ProviderCatalogService,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


def get_payment_service(session: DbSessionDep) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


def get_provider_catalog_service(session: DbSessionDep) -> ProviderCatalogService:
    return ProviderCatalogService(session)


ProviderCatalogServiceDep = Annotated[
    ProviderCatalogService, Depends(get_provider_catalog_service)
]


def _catalog_error(exc: ProviderCatalogError) -> HTTPException:
    if isinstance(exc, ProviderCatalogNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProviderCatalogConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ProviderCatalogForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ProviderCatalogInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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


@router.get("/providers", response_model=list[ProviderCatalogResponse])
async def list_providers(
    current_user: CurrentUserDep, service: ProviderCatalogServiceDep
) -> list[ProviderCatalogResponse]:
    try:
        providers = await service.list_catalog(current_user)
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return [await catalog_response(provider, service) for provider in providers]


@router.get("/providers/{provider_code}", response_model=ProviderCatalogResponse)
async def get_provider(
    provider_code: str, current_user: CurrentUserDep, service: ProviderCatalogServiceDep
) -> ProviderCatalogResponse:
    try:
        provider = await service.get_catalog_entry(current_user, provider_code)
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return await catalog_response(provider, service)


@router.patch("/providers/{provider_code}", response_model=ProviderCatalogResponse)
async def update_provider(
    provider_code: str,
    payload: ProviderCatalogUpdate,
    current_user: CurrentUserDep,
    service: ProviderCatalogServiceDep,
) -> ProviderCatalogResponse:
    try:
        provider = await service.update_catalog_entry(
            current_user, provider_code, payload.model_dump(exclude_unset=True)
        )
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return await catalog_response(provider, service)


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
