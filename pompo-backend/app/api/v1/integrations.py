"""POS / developer integration APIs and Master Admin client management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import CurrentUserDep, DbSessionDep, RedisDep, require_permission
from app.integrations.errors import IntegrationAPIError
from app.integrations.scopes import CREATE_PAYMENT_SCOPES, CREATE_QR_SCOPES, READ_PAYMENT_SCOPES
from app.models.enums import OutboundWebhookStatus
from app.models.payment import QRCode, Transaction
from app.repositories.integration import OutboundWebhookDeliveryRepository
from app.schemas.integration import (
    APIKeyCreatedResponse,
    IntegrationClientCreate,
    IntegrationClientCreatedResponse,
    IntegrationClientResponse,
    IntegrationClientUpdate,
    IntegrationErrorBody,
    IntegrationPaymentCreate,
    IntegrationPaymentResponse,
    IntegrationQRResponse,
    OutboundWebhookDeliveryResponse,
    WebhookEndpointCreate,
    WebhookEndpointResponse,
    WebhookEndpointUpdate,
    WebhookSecretCreatedResponse,
)
from app.services.integration import (
    APIClientPrincipal,
    IntegrationConflictError,
    IntegrationError,
    IntegrationForbiddenError,
    IntegrationInvalidError,
    IntegrationNotFoundError,
    IntegrationService,
)
from app.services.payment import (
    PaymentConflictError,
    PaymentError,
    PaymentForbiddenError,
    PaymentInvalidError,
    PaymentNotFoundError,
    PaymentService,
)
from app.services.qr import QRError, QRForbiddenError, QRInvalidError, QRNotFoundError, QRService

router = APIRouter(prefix="/integrations", tags=["Integrations"])

_MACHINE_ERROR_RESPONSES = {
    401: {
        "model": IntegrationErrorBody,
        "description": "invalid_api_key, revoked_api_key, expired_api_key, api_key_inactive",
    },
    403: {"model": IntegrationErrorBody, "description": "insufficient_scope"},
    404: {"model": IntegrationErrorBody, "description": "payment_not_found"},
    409: {"model": IntegrationErrorBody, "description": "idempotency_conflict"},
    422: {
        "model": IntegrationErrorBody,
        "description": "invalid_merchant_context, invalid_branch_context, invalid_till_context, invalid_amount, invalid_request, unsupported_currency",
    },
    429: {"model": IntegrationErrorBody, "description": "rate_limited"},
}

_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="POMPO integration API key (pompo_test_… / pompo_live_…). Shown only at creation.",
)
_bearer_scheme = HTTPBearer(auto_error=False)


def get_integration_service(session: DbSessionDep) -> IntegrationService:
    return IntegrationService(session)


IntegrationServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]


def get_payment_service(session: DbSessionDep) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


def get_qr_service(session: DbSessionDep) -> QRService:
    return QRService(session)


QRServiceDep = Annotated[QRService, Depends(get_qr_service)]


def _admin_error(exc: IntegrationError) -> HTTPException:
    if isinstance(exc, IntegrationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, IntegrationConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, IntegrationInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


def _payment_error(exc: PaymentError | QRError) -> IntegrationAPIError:
    if isinstance(exc, (PaymentNotFoundError, QRNotFoundError)):
        return IntegrationAPIError("payment_not_found", "Payment not found")
    if isinstance(exc, (PaymentConflictError,)):
        return IntegrationAPIError("idempotency_conflict", str(exc))
    if isinstance(exc, (PaymentForbiddenError, QRForbiddenError)):
        message = str(exc)
        lowered = message.lower()
        if "merchant" in lowered:
            return IntegrationAPIError("invalid_merchant_context", message)
        if "branch" in lowered:
            return IntegrationAPIError("invalid_branch_context", message)
        if "till" in lowered:
            return IntegrationAPIError("invalid_till_context", message)
        return IntegrationAPIError("insufficient_scope", "Insufficient scope")
    if isinstance(exc, (PaymentInvalidError, QRInvalidError)):
        text = str(exc).lower()
        if "currency" in text:
            return IntegrationAPIError("unsupported_currency", str(exc))
        if "amount" in text:
            return IntegrationAPIError("invalid_amount", str(exc))
        if "merchant" in text:
            return IntegrationAPIError("invalid_merchant_context", str(exc))
        if "branch" in text:
            return IntegrationAPIError("invalid_branch_context", str(exc))
        if "till" in text:
            return IntegrationAPIError("invalid_till_context", str(exc))
        return IntegrationAPIError("invalid_request", str(exc))
    return IntegrationAPIError("invalid_request", str(exc))


def _endpoint_response(endpoint, *, secret_prefix: str | None) -> WebhookEndpointResponse:
    return WebhookEndpointResponse(
        id=endpoint.id,
        destination_url=endpoint.destination_url,
        is_active=endpoint.is_active,
        webhook_secret_prefix=secret_prefix,
        last_delivered_at=endpoint.last_delivered_at,
        last_failure_category=(
            endpoint.last_failure_category.value if endpoint.last_failure_category else None
        ),
        last_response_status_code=endpoint.last_response_status_code,
        created_at=endpoint.created_at,
    )


def _client_response(client) -> IntegrationClientResponse:
    prefix = client.webhook_secret_prefix
    return IntegrationClientResponse(
        id=client.id,
        public_id=client.public_id,
        name=client.name,
        client_type=client.client_type.value,
        environment=client.environment.value,
        status=client.status.value,
        merchant_id=client.merchant_id,
        branch_id=client.branch_id,
        till_id=client.till_id,
        scopes=list(client.scopes or []),
        webhook_url=client.webhook_url,
        webhook_secret_prefix=prefix,
        rate_limit_requests=client.rate_limit_requests,
        last_used_at=client.last_used_at,
        revoked_at=client.revoked_at,
        created_at=client.created_at,
        keys=[
            {
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "is_active": key.is_active,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at,
                "revoked_at": key.revoked_at,
                "created_at": key.created_at,
            }
            for key in (client.api_keys or [])
        ],
        endpoints=[
            _endpoint_response(endpoint, secret_prefix=prefix)
            for endpoint in (getattr(client, "webhook_endpoints", None) or [])
        ],
    )


def _payment_response(transaction: Transaction, qr: QRCode | None = None) -> IntegrationPaymentResponse:
    qr_payload = None
    if qr is not None:
        qr_payload = IntegrationQRResponse(
            public_identifier=qr.public_identifier,
            encoded_payload=qr.payload,
            qr_type=qr.qr_type.value,
            status=qr.status.value,
            expires_at=qr.expires_at,
        )
    return IntegrationPaymentResponse(
        reference=transaction.reference,
        status=transaction.status.value if hasattr(transaction.status, "value") else str(transaction.status),
        amount=transaction.amount,
        currency=transaction.currency,
        payment_method=transaction.payment_method,
        merchant_id=transaction.merchant_id,
        branch_id=transaction.branch_id,
        till_id=transaction.till_id,
        description=transaction.description,
        failure_reason=transaction.failure_reason,
        created_at=getattr(transaction, "created_at", None),
        completed_at=transaction.completed_at,
        qr=qr_payload,
    )


async def get_api_client_principal(
    request: Request,
    service: IntegrationServiceDep,
    redis: RedisDep,
    api_key_header: Annotated[str | None, Depends(_api_key_header)] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> APIClientPrincipal:
    raw = api_key_header
    if not raw and credentials is not None:
        raw = credentials.credentials
    client_ip = request.client.host if request.client else "unknown"
    fail_key = f"rate_limit:auth_fail:{client_ip}"
    try:
        principal = await service.authenticate_api_key(raw)
    except IntegrationAPIError:
        from app.core.config.base import get_settings

        settings = get_settings()
        try:
            current = await redis.increment(fail_key)
            if current == 1:
                await redis.expire(fail_key, settings.rate_limit_window_seconds)
            if current > settings.rate_limit_auth_failures:
                raise IntegrationAPIError("rate_limited", "Too many authentication failures")
        except IntegrationAPIError:
            raise
        except Exception:
            pass
        raise
    limit = principal.client.rate_limit_requests
    if limit:
        from app.core.config.base import get_settings

        settings = get_settings()
        bucket = f"rate_limit:client:{principal.client.public_id}"
        try:
            current = await redis.increment(bucket)
            if current == 1:
                await redis.expire(bucket, settings.rate_limit_window_seconds)
            if current > limit:
                raise IntegrationAPIError("rate_limited", "Rate limit exceeded")
        except IntegrationAPIError:
            raise
        except Exception:
            pass
    return principal


APIClientDep = Annotated[APIClientPrincipal, Depends(get_api_client_principal)]


@router.post(
    "/clients",
    response_model=IntegrationClientCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def create_integration_client(
    payload: IntegrationClientCreate,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> IntegrationClientCreatedResponse:
    """Create an integration client. The API key and webhook secret are returned once."""
    try:
        client, raw_key, webhook_secret = await service.create_client(
            current_user, payload.model_dump()
        )
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    body = _client_response(client)
    return IntegrationClientCreatedResponse(
        **body.model_dump(),
        api_key=raw_key,
        webhook_signing_secret=webhook_secret,
    )


@router.get(
    "/clients",
    response_model=list[IntegrationClientResponse],
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def list_integration_clients(
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
    merchant_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[IntegrationClientResponse]:
    try:
        rows = await service.list_clients(
            current_user, merchant_id=merchant_id, limit=limit, offset=offset
        )
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return [_client_response(row) for row in rows]


@router.get(
    "/clients/{client_id}",
    response_model=IntegrationClientResponse,
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def get_integration_client(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> IntegrationClientResponse:
    try:
        client = await service.get_client(current_user, client_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _client_response(client)


@router.patch(
    "/clients/{client_id}",
    response_model=IntegrationClientResponse,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def update_integration_client(
    client_id: uuid.UUID,
    payload: IntegrationClientUpdate,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> IntegrationClientResponse:
    try:
        client = await service.update_client(
            current_user, client_id, payload.model_dump(exclude_unset=True)
        )
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _client_response(client)


@router.post(
    "/clients/{client_id}/keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def rotate_integration_key(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
    revoke_others: bool = True,
    expires_at: datetime | None = Query(default=None),
) -> APIKeyCreatedResponse:
    try:
        client, raw_key = await service.rotate_key(
            current_user,
            client_id,
            revoke_others=revoke_others,
            expires_at=expires_at,
        )
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    prefix = raw_key[:16]
    return APIKeyCreatedResponse(client_id=client.id, key_prefix=prefix, api_key=raw_key)


@router.post(
    "/clients/{client_id}/keys/{key_id}/revoke",
    response_model=IntegrationClientResponse,
    dependencies=[Depends(require_permission("api_keys:revoke"))],
)
async def revoke_integration_key(
    client_id: uuid.UUID,
    key_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> IntegrationClientResponse:
    try:
        client = await service.revoke_key(current_user, client_id, key_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _client_response(client)


@router.post(
    "/clients/{client_id}/revoke",
    response_model=IntegrationClientResponse,
    dependencies=[Depends(require_permission("api_keys:revoke"))],
)
async def revoke_integration_client(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> IntegrationClientResponse:
    try:
        client = await service.revoke_client(current_user, client_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _client_response(client)


@router.post(
    "/clients/{client_id}/webhook-secret",
    response_model=WebhookSecretCreatedResponse,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def rotate_webhook_secret(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> WebhookSecretCreatedResponse:
    try:
        client, secret = await service.rotate_webhook_secret(current_user, client_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return WebhookSecretCreatedResponse(
        client_id=client.id,
        webhook_secret_prefix=client.webhook_secret_prefix or "",
        webhook_signing_secret=secret,
    )


@router.post(
    "/clients/{client_id}/endpoints",
    response_model=WebhookEndpointResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def add_webhook_endpoint(
    client_id: uuid.UUID,
    payload: WebhookEndpointCreate,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> WebhookEndpointResponse:
    try:
        client = await service.get_client(current_user, client_id)
        endpoint = await service.add_endpoint(current_user, client_id, payload.destination_url)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _endpoint_response(endpoint, secret_prefix=client.webhook_secret_prefix)


@router.get(
    "/clients/{client_id}/endpoints",
    response_model=list[WebhookEndpointResponse],
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def list_webhook_endpoints(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> list[WebhookEndpointResponse]:
    try:
        client = await service.get_client(current_user, client_id)
        rows = await service.list_endpoints(current_user, client_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return [_endpoint_response(row, secret_prefix=client.webhook_secret_prefix) for row in rows]


@router.patch(
    "/clients/{client_id}/endpoints/{endpoint_id}",
    response_model=WebhookEndpointResponse,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def update_webhook_endpoint(
    client_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    payload: WebhookEndpointUpdate,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
) -> WebhookEndpointResponse:
    try:
        client = await service.get_client(current_user, client_id)
        endpoint = await service.update_endpoint(
            current_user, client_id, endpoint_id, payload.model_dump(exclude_unset=True)
        )
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    return _endpoint_response(endpoint, secret_prefix=client.webhook_secret_prefix)


@router.get(
    "/clients/{client_id}/deliveries",
    response_model=list[OutboundWebhookDeliveryResponse],
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def list_client_deliveries(
    client_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
    session: DbSessionDep,
    delivery_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[OutboundWebhookDeliveryResponse]:
    try:
        await service.get_client(current_user, client_id)
    except IntegrationError as exc:
        raise _admin_error(exc) from exc
    status_filter = None
    if delivery_status:
        try:
            status_filter = OutboundWebhookStatus(delivery_status)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid delivery status",
            ) from exc
    rows = await OutboundWebhookDeliveryRepository(session).list_for_client(
        client_id, status=status_filter, limit=limit, offset=offset
    )
    return [
        OutboundWebhookDeliveryResponse(
            public_event_id=row.public_event_id,
            event_type=row.event_type,
            destination_url=row.destination_url,
            status=row.status.value,
            attempt_count=row.attempt_count,
            first_attempted_at=row.first_attempted_at,
            last_attempted_at=row.last_attempted_at,
            next_retry_at=row.next_retry_at,
            response_status_code=row.response_status_code,
            failure_category=row.failure_category.value if row.failure_category else None,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post(
    "/payments",
    response_model=IntegrationPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_MACHINE_ERROR_RESPONSES,
)
async def create_integration_payment(
    payload: IntegrationPaymentCreate,
    principal: APIClientDep,
    service: IntegrationServiceDep,
    payments: PaymentServiceDep,
    qr_service: QRServiceDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> IntegrationPaymentResponse:
    """Create a POS/developer payment using the authenticated client's till context."""
    service.require_scope(principal, CREATE_PAYMENT_SCOPES)
    merchant_id, branch_id, till_id = service.resolve_pos_context(
        principal,
        merchant_id=payload.merchant_id,
        branch_id=payload.branch_id,
        till_id=payload.till_id,
    )
    key = payload.idempotency_key or idempotency_key
    if not key:
        raise IntegrationAPIError("invalid_request", "Idempotency key is required")
    values = {
        "merchant_id": merchant_id,
        "branch_id": branch_id,
        "till_id": till_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "payment_method": payload.payment_method,
        "provider_code": payload.provider_code,
        "customer_phone": payload.customer_phone,
        "description": payload.description,
        "idempotency_key": key,
    }
    try:
        if payload.generate_qr:
            service.require_scope(principal, CREATE_QR_SCOPES)
            qr = await qr_service.create_dynamic_qr_for_client(
                principal.client, {**values, "expires_in_seconds": payload.expires_in_seconds}
            )
            transaction = qr.transaction
            if transaction is None and qr.payment_reference:
                transaction = await payments.get_payment_for_client(
                    principal.client, qr.payment_reference
                )
            if transaction is None:
                raise IntegrationAPIError("payment_not_found", "Payment not found")
            return _payment_response(transaction, qr)
        transaction = await payments.create_payment(None, values, api_client=principal.client)
    except (PaymentError, QRError) as exc:
        raise _payment_error(exc) from exc
    return _payment_response(transaction)


@router.get(
    "/payments/{reference}",
    response_model=IntegrationPaymentResponse,
    responses=_MACHINE_ERROR_RESPONSES,
)
async def get_integration_payment(
    reference: str,
    principal: APIClientDep,
    service: IntegrationServiceDep,
    payments: PaymentServiceDep,
) -> IntegrationPaymentResponse:
    service.require_scope(principal, READ_PAYMENT_SCOPES)
    try:
        transaction = await payments.get_payment_for_client(principal.client, reference)
    except PaymentError as exc:
        raise _payment_error(exc) from exc
    return _payment_response(transaction, transaction.qr_code)
