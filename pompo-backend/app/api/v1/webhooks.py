"""Provider webhook ingestion and administrative inspection endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.models.user import User
from app.schemas.webhook import WebhookEventResponse, WebhookIngestResponse
from app.services.webhook import (
    WebhookDuplicateError,
    WebhookError,
    WebhookForbiddenError,
    WebhookInvalidError,
    WebhookNotFoundError,
    WebhookService,
    WebhookSignatureError,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def get_webhook_service(session: DbSessionDep) -> WebhookService:
    return WebhookService(session)


WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]


def _webhook_error(exc: WebhookError) -> HTTPException:
    if isinstance(exc, WebhookNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, WebhookForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, WebhookSignatureError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    if isinstance(exc, WebhookInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _event_response(event) -> WebhookEventResponse:
    return WebhookEventResponse(
        id=event.id,
        public_identifier=event.public_identifier,
        provider_id=event.provider_id,
        provider_event_id=event.provider_event_id,
        transaction_id=event.transaction_id,
        payment_attempt_id=event.payment_attempt_id,
        event_type=event.event_type,
        event_version=event.event_version,
        payment_reference=event.payment_reference,
        provider_transaction_reference=event.provider_transaction_reference,
        received_at=event.received_at,
        processed_at=event.processed_at,
        processing_status=event.processing_status.value,
        processing_attempts=event.processing_attempts,
        signature_verified=event.signature_verified,
        timestamp_validated=event.timestamp_validated,
        failure_category=event.failure_category.value if event.failure_category else None,
        failure_code=event.failure_code,
        payload=event.payload,
    )


@router.post("/{provider_code}", response_model=WebhookIngestResponse)
async def ingest_webhook(
    provider_code: str,
    request: Request,
    service: WebhookServiceDep,
) -> WebhookIngestResponse:
    """Accept an asynchronous provider callback. Signature verification is provider-specific."""
    body = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    try:
        event = await service.ingest(provider_code, headers=headers, body=body)
    except WebhookDuplicateError as exc:
        return WebhookIngestResponse(
            status="accepted",
            event_id=exc.event.public_identifier,
            duplicate=True,
        )
    except WebhookError as exc:
        raise _webhook_error(exc) from exc
    return WebhookIngestResponse(status="accepted", event_id=event.public_identifier)


@router.get("", response_model=list[WebhookEventResponse])
async def list_webhook_events(
    current_user: Annotated[User, Depends(require_permission("webhooks:read"))],
    service: WebhookServiceDep,
    provider_code: str | None = None,
    processing_status: str | None = None,
    event_type: str | None = None,
    payment_reference: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[WebhookEventResponse]:
    try:
        events = await service.list_events(
            current_user,
            provider_code=provider_code,
            processing_status=processing_status,
            event_type=event_type,
            payment_reference=payment_reference,
            limit=limit,
            offset=offset,
        )
    except WebhookError as exc:
        raise _webhook_error(exc) from exc
    return [_event_response(event) for event in events]


@router.get("/events/{event_id}", response_model=WebhookEventResponse)
async def get_webhook_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("webhooks:read"))],
    service: WebhookServiceDep,
) -> WebhookEventResponse:
    try:
        event = await service.get_event(current_user, event_id)
    except WebhookError as exc:
        raise _webhook_error(exc) from exc
    return _event_response(event)
