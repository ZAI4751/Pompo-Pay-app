"""Payment request and bill-split endpoints. Instructions only — no stored value."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.api.v1.payments import _payment_response
from app.schemas.customer import (
    BillSplitCreate,
    BillSplitResponse,
    PaymentRequestCreate,
    PaymentRequestPay,
    PaymentRequestResponse,
)
from app.schemas.payment import PaymentResponse
from app.services.payment_request import (
    PaymentRequestConflictError,
    PaymentRequestError,
    PaymentRequestForbiddenError,
    PaymentRequestInvalidError,
    PaymentRequestNotFoundError,
    PaymentRequestService,
)

router = APIRouter(prefix="/payment-requests", tags=["Payment Requests"])


def get_payment_request_service(session: DbSessionDep) -> PaymentRequestService:
    return PaymentRequestService(session)


PaymentRequestServiceDep = Annotated[PaymentRequestService, Depends(get_payment_request_service)]


def _error(exc: PaymentRequestError) -> HTTPException:
    if isinstance(exc, PaymentRequestNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PaymentRequestForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, PaymentRequestConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, PaymentRequestInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _request_response(row) -> PaymentRequestResponse:
    merchant = getattr(row, "merchant", None)
    branch = getattr(row, "branch", None)
    till = getattr(row, "till", None)
    requester = getattr(row, "requester", None)
    return PaymentRequestResponse(
        id=row.id,
        public_identifier=row.public_identifier,
        share_code=row.share_code,
        requester_id=row.requester_id,
        requester_name=getattr(requester, "full_name", None),
        payer_user_id=row.payer_user_id,
        merchant_id=row.merchant_id,
        merchant_name=getattr(merchant, "name", None),
        branch_name=getattr(branch, "name", None),
        till_name=getattr(till, "name", None),
        amount=row.amount,
        currency=row.currency,
        description=row.description,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        expires_at=row.expires_at,
        paid_at=row.paid_at,
        payment_reference=row.payment_reference,
        bill_split_id=row.bill_split_id,
        created_at=getattr(row, "created_at", None),
    )


def _split_response(split) -> BillSplitResponse:
    merchant = getattr(split, "merchant", None)
    return BillSplitResponse(
        id=split.id,
        public_identifier=split.public_identifier,
        total_amount=split.total_amount,
        currency=split.currency,
        description=split.description,
        status=split.status.value if hasattr(split.status, "value") else str(split.status),
        merchant_name=getattr(merchant, "name", None),
        expires_at=split.expires_at,
        requests=[_request_response(item) for item in (split.requests or [])],
    )


@router.post(
    "",
    response_model=PaymentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def create_payment_request(
    payload: PaymentRequestCreate,
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
) -> PaymentRequestResponse:
    try:
        row = await service.create(current_user, payload.model_dump(exclude_none=True))
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _request_response(row)


@router.post(
    "/splits",
    response_model=BillSplitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def create_bill_split(
    payload: BillSplitCreate,
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
) -> BillSplitResponse:
    try:
        split = await service.create_split(
            current_user,
            {
                **payload.model_dump(exclude_none=True),
                "participants": [item.model_dump() for item in payload.participants],
            },
        )
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _split_response(split)


@router.get(
    "",
    response_model=list[PaymentRequestResponse],
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def list_payment_requests(
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[PaymentRequestResponse]:
    try:
        rows = await service.list_mine(
            current_user, status=status_filter, limit=limit, offset=offset
        )
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return [_request_response(row) for row in rows]


@router.get("/public/{public_identifier}", response_model=PaymentRequestResponse)
async def inspect_payment_request(
    public_identifier: str, service: PaymentRequestServiceDep
) -> PaymentRequestResponse:
    try:
        row = await service.inspect_public(public_identifier)
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _request_response(row)


@router.get(
    "/{public_identifier}",
    response_model=PaymentRequestResponse,
    dependencies=[Depends(require_permission("transactions:read"))],
)
async def get_payment_request(
    public_identifier: str,
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
) -> PaymentRequestResponse:
    try:
        row = await service.get_owned(current_user, public_identifier)
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _request_response(row)


@router.post(
    "/{public_identifier}/cancel",
    response_model=PaymentRequestResponse,
    dependencies=[Depends(require_permission("transactions:update"))],
)
async def cancel_payment_request(
    public_identifier: str,
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
) -> PaymentRequestResponse:
    try:
        row = await service.cancel(current_user, public_identifier)
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _request_response(row)


@router.post(
    "/{public_identifier}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transactions:create"))],
)
async def pay_payment_request(
    public_identifier: str,
    payload: PaymentRequestPay,
    current_user: CurrentUserDep,
    service: PaymentRequestServiceDep,
) -> PaymentResponse:
    try:
        transaction = await service.pay(
            current_user, public_identifier, payload.model_dump(exclude_none=True)
        )
    except PaymentRequestError as exc:
        raise _error(exc) from exc
    return _payment_response(transaction)
