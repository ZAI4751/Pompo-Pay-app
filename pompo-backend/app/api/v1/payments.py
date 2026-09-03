"""Payment-core endpoints shared by POS and customer clients."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.payments.customer_status import customer_status_detail, customer_status_label
from app.payments.providers import ProviderError
from app.payments.registry import ProviderRegistry
from app.api.v1.provider_views import catalog_response
from app.models.payment import Transaction
from app.schemas.payment import (
    MerchantPaymentSummaryResponse,
    PaymentAttemptResponse,
    PaymentCreate,
    PaymentReceiptResponse,
    PaymentRepeatRequest,
    PaymentResponse,
    ProviderCatalogResponse,
    ProviderCatalogUpdate,
)
from app.schemas.qr import PaymentFromQRRequest
from app.services.qr import QRError as QRServiceError, QRService
from app.services.payment import (
    PaymentConflictError,
    PaymentError,
    PaymentForbiddenError,
    PaymentInvalidError,
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


def _payment_response(transaction: Transaction) -> PaymentResponse:
    attempts = []
    for attempt in transaction.attempts or []:
        attempts.append(
            PaymentAttemptResponse(
                id=attempt.id,
                attempt_number=attempt.attempt_number,
                status=attempt.status.value if hasattr(attempt.status, "value") else str(attempt.status),
                provider_reference=attempt.provider_reference,
                provider_status=attempt.provider_status,
                duration_ms=attempt.duration_ms,
                failure_code=attempt.failure_code,
                retryable=attempt.retryable,
                failure_reason=attempt.failure_reason,
            )
        )
    merchant = getattr(transaction, "merchant", None)
    branch = getattr(transaction, "branch", None)
    till = getattr(transaction, "till", None)
    return PaymentResponse(
        id=transaction.id,
        reference=transaction.reference,
        merchant_id=transaction.merchant_id,
        branch_id=transaction.branch_id,
        till_id=transaction.till_id,
        amount=transaction.amount,
        currency=transaction.currency,
        payment_method=transaction.payment_method,
        status=transaction.status.value if hasattr(transaction.status, "value") else str(transaction.status),
        description=transaction.description,
        failure_reason=transaction.failure_reason,
        attempts=attempts,
        merchant_name=getattr(merchant, "name", None),
        branch_name=getattr(branch, "name", None),
        till_name=getattr(till, "name", None),
        created_at=getattr(transaction, "created_at", None),
        completed_at=transaction.completed_at,
        customer_status=customer_status_label(
            transaction.status.value if hasattr(transaction.status, "value") else str(transaction.status)
        ),
        status_detail=customer_status_detail(
            transaction.status.value if hasattr(transaction.status, "value") else str(transaction.status)
        ),
    )


def get_payment_service(session: DbSessionDep) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


def get_provider_catalog_service(session: DbSessionDep) -> ProviderCatalogService:
    return ProviderCatalogService(session)


ProviderCatalogServiceDep = Annotated[
    ProviderCatalogService, Depends(get_provider_catalog_service)
]


def get_qr_service(session: DbSessionDep) -> QRService:
    return QRService(session)


QRServiceDep = Annotated[QRService, Depends(get_qr_service)]


def _qr_payment_error(exc: QRServiceError) -> HTTPException:
    from app.services.qr import (
        QRConflictError,
        QRForbiddenError,
        QRInvalidError,
        QRNotFoundError,
    )

    if isinstance(exc, QRNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, QRConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, QRForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, QRInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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
    if isinstance(exc, PaymentInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
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
    "/from-qr",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def create_payment_from_qr(
    payload: PaymentFromQRRequest,
    current_user: CurrentUserDep,
    qr_service: QRServiceDep,
) -> PaymentResponse:
    try:
        transaction = await qr_service.initiate_payment_from_qr(
            current_user, payload.model_dump(exclude_none=True)
        )
    except QRServiceError as exc:
        raise _qr_payment_error(exc) from exc
    return transaction


@router.get(
    "/mine",
    response_model=list[PaymentResponse],
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def list_my_payments(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    merchant_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    reference: str | None = Query(default=None),
    q: str | None = Query(default=None),
    amount_min: Decimal | None = Query(default=None),
    amount_max: Decimal | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
) -> list[PaymentResponse]:
    try:
        rows = await service.list_my_payments(
            current_user,
            limit=limit,
            offset=offset,
            merchant_id=merchant_id,
            status=status,
            reference=reference,
            query_text=q,
            amount_min=amount_min,
            amount_max=amount_max,
            created_from=created_from,
            created_to=created_to,
        )
    except PaymentError as exc:
        raise _error(exc) from exc
    return [_payment_response(row) for row in rows]


@router.get(
    "",
    response_model=list[PaymentResponse],
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def list_merchant_payments(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    reference: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[PaymentResponse]:
    try:
        rows = await service.list_merchant_payments(
            current_user,
            limit=limit,
            offset=offset,
            status=status,
            reference=reference,
            query_text=q,
        )
    except PaymentError as exc:
        raise _error(exc) from exc
    return [_payment_response(row) for row in rows]


@router.get(
    "/summary",
    response_model=MerchantPaymentSummaryResponse,
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def merchant_payment_summary(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> MerchantPaymentSummaryResponse:
    try:
        payload = await service.merchant_summary(current_user)
    except PaymentError as exc:
        raise _error(exc) from exc
    return MerchantPaymentSummaryResponse(**payload)


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


@router.post(
    "/{reference}/repeat",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def repeat_payment(
    reference: str,
    payload: PaymentRepeatRequest,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    try:
        transaction = await service.repeat_payment(
            current_user, reference, payload.model_dump(exclude_none=True)
        )
    except PaymentError as exc:
        raise _error(exc) from exc
    return _payment_response(transaction)


@router.get(
    "/{reference}/receipt",
    response_model=PaymentReceiptResponse,
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def get_payment_receipt(
    reference: str,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> PaymentReceiptResponse:
    try:
        payload = await service.get_receipt(current_user, reference)
    except PaymentError as exc:
        raise _error(exc) from exc
    return PaymentReceiptResponse(**payload)


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
        transaction = await service.get_payment(current_user, reference)
    except PaymentError as exc:
        raise _error(exc) from exc
    return _payment_response(transaction)
