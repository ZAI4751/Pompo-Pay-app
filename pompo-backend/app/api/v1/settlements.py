"""Settlement ingestion and administrative inspection endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import DbSessionDep, require_permission
from app.models.user import User
from app.schemas.settlement import (
    ReconciliationResponse,
    ReconciliationResolveRequest,
    ReconciliationRunCreate,
    ReconciliationRunResponse,
    ReconciliationSummaryResponse,
    SettlementBatchResponse,
    SettlementIngestRequest,
    SettlementIngestResponse,
    SettlementResponse,
    SettlementSummaryResponse,
)
from app.services.settlement import (
    SettlementDuplicateError,
    SettlementError,
    SettlementForbiddenError,
    SettlementInvalidError,
    SettlementNotFoundError,
    SettlementService,
    SettlementSignatureError,
)

settlement_router = APIRouter(prefix="/settlements", tags=["Settlements"])
reconciliation_router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


def get_settlement_service(session: DbSessionDep) -> SettlementService:
    return SettlementService(session)


SettlementServiceDep = Annotated[SettlementService, Depends(get_settlement_service)]


def _error(exc: SettlementError) -> HTTPException:
    if isinstance(exc, SettlementNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SettlementForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, SettlementSignatureError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid settlement signature")
    if isinstance(exc, SettlementInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, SettlementDuplicateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _settlement_response(settlement) -> SettlementResponse:
    recon = settlement.reconciliation
    return SettlementResponse(
        id=settlement.id,
        public_identifier=settlement.public_identifier,
        batch_id=settlement.batch_id,
        provider_id=settlement.provider_id,
        provider_settlement_reference=settlement.provider_settlement_reference,
        transaction_id=settlement.transaction_id,
        payment_attempt_id=settlement.payment_attempt_id,
        merchant_id=settlement.merchant_id,
        branch_id=settlement.branch_id,
        payment_reference=settlement.payment_reference,
        provider_transaction_reference=settlement.provider_transaction_reference,
        gross_amount=settlement.gross_amount,
        provider_fee=settlement.provider_fee,
        pompo_fee=settlement.pompo_fee,
        merchant_net=settlement.merchant_net,
        currency=settlement.currency,
        status=settlement.status.value,
        settlement_date=settlement.settlement_date,
        received_at=settlement.received_at,
        created_at=settlement.created_at,
        updated_at=settlement.updated_at,
        reconciliation=_recon_response(recon) if recon is not None else None,
    )


def _recon_response(record) -> ReconciliationResponse:
    return ReconciliationResponse(
        id=record.id,
        public_identifier=record.public_identifier,
        settlement_id=record.settlement_id,
        transaction_id=record.transaction_id,
        status=record.status.value,
        mismatch_category=record.mismatch_category.value if record.mismatch_category else None,
        expected_amount=record.expected_amount,
        actual_amount=record.actual_amount,
        variance=record.variance,
        expected_provider_fee=record.expected_provider_fee,
        actual_provider_fee=record.actual_provider_fee,
        expected_pompo_fee=record.expected_pompo_fee,
        actual_pompo_fee=record.actual_pompo_fee,
        expected_currency=record.expected_currency,
        actual_currency=record.actual_currency,
        pompo_reference=record.pompo_reference,
        provider_reference=record.provider_reference,
        detected_at=record.detected_at,
        resolved_at=record.resolved_at,
        resolution_note=record.resolution_note,
    )


@settlement_router.post(
    "/ingest/{provider_code}",
    response_model=SettlementIngestResponse,
    summary="Ingest a signed provider settlement batch",
    description="Unauthenticated HMAC ingest. Requires a valid provider signature. A payment webhook is not a settlement.",
)
async def ingest_provider_settlement(
    provider_code: str,
    request: Request,
    service: SettlementServiceDep,
) -> SettlementIngestResponse:
    body = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    try:
        batch, duplicate = await service.ingest_signed(provider_code, headers=headers, body=body)
    except SettlementError as exc:
        raise _error(exc) from exc
    return SettlementIngestResponse(
        status="accepted",
        batch_id=batch.public_identifier,
        duplicate=duplicate,
        record_count=batch.record_count,
    )


@settlement_router.post(
    "",
    response_model=SettlementIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Administratively ingest a normalized settlement batch",
)
async def ingest_admin_settlement(
    payload: SettlementIngestRequest,
    current_user: Annotated[User, Depends(require_permission("settlements:create"))],
    service: SettlementServiceDep,
) -> SettlementIngestResponse:
    body = {
        "batch_reference": payload.batch_reference,
        "settlement_date": payload.settlement_date.isoformat(),
        "currency": payload.currency,
        "records": [
            record.model_dump(mode="json") | {
                "settlement_reference": record.settlement_reference,
                "provider_transaction_id": record.provider_transaction_id,
            }
            for record in payload.records
        ],
    }
    try:
        batch, duplicate = await service.ingest_admin(current_user, payload.provider_code, body)
    except SettlementError as exc:
        raise _error(exc) from exc
    return SettlementIngestResponse(
        status="accepted",
        batch_id=batch.public_identifier,
        duplicate=duplicate,
        record_count=batch.record_count,
    )


@settlement_router.get("/summary", response_model=SettlementSummaryResponse)
async def settlement_summary(
    current_user: Annotated[User, Depends(require_permission("settlements:read"))],
    service: SettlementServiceDep,
) -> SettlementSummaryResponse:
    try:
        data = await service.settlement_summary(current_user)
    except SettlementError as exc:
        raise _error(exc) from exc
    return SettlementSummaryResponse.model_validate(data)


@settlement_router.get("/batches", response_model=list[SettlementBatchResponse])
async def list_settlement_batches(
    current_user: Annotated[User, Depends(require_permission("settlements:read"))],
    service: SettlementServiceDep,
    provider_code: str | None = None,
    settlement_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SettlementBatchResponse]:
    try:
        batches = await service.list_batches(
            current_user,
            provider_code=provider_code,
            settlement_date=settlement_date,
            limit=limit,
            offset=offset,
        )
    except SettlementError as exc:
        raise _error(exc) from exc
    return [SettlementBatchResponse.model_validate(batch) for batch in batches]


@settlement_router.get("/batches/{batch_id}", response_model=SettlementBatchResponse)
async def get_settlement_batch(
    batch_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("settlements:read"))],
    service: SettlementServiceDep,
) -> SettlementBatchResponse:
    try:
        batch = await service.get_batch(current_user, batch_id)
    except SettlementError as exc:
        raise _error(exc) from exc
    return SettlementBatchResponse.model_validate(batch)


@settlement_router.get("", response_model=list[SettlementResponse])
async def list_settlements(
    current_user: Annotated[User, Depends(require_permission("settlements:read"))],
    service: SettlementServiceDep,
    provider_code: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    settlement_date: date | None = None,
    batch_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SettlementResponse]:
    try:
        settlements = await service.list_settlements(
            current_user,
            provider_code=provider_code,
            status=status_filter,
            settlement_date=settlement_date,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
    except SettlementError as exc:
        raise _error(exc) from exc
    return [_settlement_response(item) for item in settlements]


@settlement_router.get("/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(
    settlement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("settlements:read"))],
    service: SettlementServiceDep,
) -> SettlementResponse:
    try:
        settlement = await service.get_settlement(current_user, settlement_id)
    except SettlementError as exc:
        raise _error(exc) from exc
    return _settlement_response(settlement)


@reconciliation_router.get("/summary", response_model=ReconciliationSummaryResponse)
async def reconciliation_summary(
    current_user: Annotated[User, Depends(require_permission("reconciliation:read"))],
    service: SettlementServiceDep,
) -> ReconciliationSummaryResponse:
    try:
        data = await service.reconciliation_summary(current_user)
    except SettlementError as exc:
        raise _error(exc) from exc
    return ReconciliationSummaryResponse(
        total_settlements=int(data["total_settlements"]),
        total_gross=data["total_gross"],
        total_provider_fees=data["total_provider_fees"],
        total_pompo_fees=data["total_pompo_fees"],
        total_merchant_net=data["total_merchant_net"],
        matched=int(data.get("matched", 0)),
        partial_match=int(data.get("partial_match", 0)),
        unmatched=int(data.get("unmatched", 0)),
        discrepancy=int(data.get("discrepancy", 0)),
        investigation=int(data.get("investigation", 0)),
        resolved=int(data.get("resolved", 0)),
        matched_rate=str(data["matched_rate"]),
        unmatched_count=int(data["unmatched_count"]),
        discrepancy_total=data["discrepancy_total"],
    )


@reconciliation_router.get("/runs", response_model=list[ReconciliationRunResponse])
async def list_reconciliation_runs(
    current_user: Annotated[User, Depends(require_permission("reconciliation:read"))],
    service: SettlementServiceDep,
    provider_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReconciliationRunResponse]:
    try:
        runs = await service.list_runs(
            current_user, provider_code=provider_code, limit=limit, offset=offset
        )
    except SettlementError as exc:
        raise _error(exc) from exc
    return [ReconciliationRunResponse.model_validate(run) for run in runs]


@reconciliation_router.post(
    "/runs",
    response_model=ReconciliationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reconciliation_run(
    payload: ReconciliationRunCreate,
    current_user: Annotated[User, Depends(require_permission("reconciliation:update"))],
    service: SettlementServiceDep,
) -> ReconciliationRunResponse:
    try:
        run = await service.create_run(
            current_user,
            provider_code=payload.provider_code,
            window_start=payload.window_start,
            window_end=payload.window_end,
        )
    except SettlementError as exc:
        raise _error(exc) from exc
    return ReconciliationRunResponse.model_validate(run)


@reconciliation_router.get("/runs/{run_id}", response_model=ReconciliationRunResponse)
async def get_reconciliation_run(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("reconciliation:read"))],
    service: SettlementServiceDep,
) -> ReconciliationRunResponse:
    try:
        run = await service.get_run(current_user, run_id)
    except SettlementError as exc:
        raise _error(exc) from exc
    return ReconciliationRunResponse.model_validate(run)


@reconciliation_router.get("", response_model=list[ReconciliationResponse])
async def list_reconciliation_records(
    current_user: Annotated[User, Depends(require_permission("reconciliation:read"))],
    service: SettlementServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    provider_code: str | None = None,
    run_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReconciliationResponse]:
    try:
        records = await service.list_reconciliation(
            current_user,
            status=status_filter,
            provider_code=provider_code,
            run_id=run_id,
            limit=limit,
            offset=offset,
        )
    except SettlementError as exc:
        raise _error(exc) from exc
    return [_recon_response(record) for record in records]


@reconciliation_router.get("/{record_id}", response_model=ReconciliationResponse)
async def get_reconciliation_record(
    record_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("reconciliation:read"))],
    service: SettlementServiceDep,
) -> ReconciliationResponse:
    try:
        record = await service.get_reconciliation(current_user, record_id)
    except SettlementError as exc:
        raise _error(exc) from exc
    return _recon_response(record)


@reconciliation_router.post("/{record_id}/resolve", response_model=ReconciliationResponse)
async def resolve_reconciliation_record(
    record_id: uuid.UUID,
    payload: ReconciliationResolveRequest,
    current_user: Annotated[User, Depends(require_permission("reconciliation:update"))],
    service: SettlementServiceDep,
) -> ReconciliationResponse:
    try:
        record = await service.resolve(current_user, record_id, note=payload.note)
    except SettlementError as exc:
        raise _error(exc) from exc
    return _recon_response(record)
