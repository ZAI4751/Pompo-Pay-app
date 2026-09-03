"""Customer registration, profile, favorites, insights, and stats."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    JWTConfigDep,
    PasswordHasherDep,
    require_permission,
)
from app.schemas.auth import AuthenticatedUserResponse, authenticated_user_response
from app.schemas.customer import (
    CustomerInsightsResponse,
    CustomerProfileUpdate,
    CustomerRegisterRequest,
    CustomerRegisterResponse,
    CustomerStatsResponse,
    FavoriteCreate,
    FavoriteMerchantResponse,
    PreferenceResponse,
    PreferenceUpdate,
)
from app.services.customer import (
    CustomerConflictError,
    CustomerError,
    CustomerForbiddenError,
    CustomerInvalidError,
    CustomerNotFoundError,
    CustomerService,
    PHONE_VERIFICATION_STATUS,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


def get_customer_service(
    session: DbSessionDep, jwt_config: JWTConfigDep, password_hasher: PasswordHasherDep
) -> CustomerService:
    return CustomerService(session, jwt_config=jwt_config, password_hasher=password_hasher)


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]


def _error(exc: CustomerError) -> HTTPException:
    if isinstance(exc, CustomerNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CustomerConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, CustomerForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, CustomerInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _client_context(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/register", response_model=CustomerRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(
    payload: CustomerRegisterRequest,
    request: Request,
    service: CustomerServiceDep,
) -> CustomerRegisterResponse:
    """Public customer self-registration. Phone SMS verification is not configured."""
    user_agent, ip_address = _client_context(request)
    try:
        tokens, user = await service.register(
            payload.model_dump(), user_agent=user_agent, ip_address=ip_address
        )
    except CustomerError as exc:
        raise _error(exc) from exc
    return CustomerRegisterResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role_code="customer",
        phone_verification=PHONE_VERIFICATION_STATUS,
        is_email_verified=user.is_email_verified,
        email_verification="not_configured",
    )


@router.get("/me", response_model=AuthenticatedUserResponse)
async def get_customer_me(current_user: CurrentUserDep) -> AuthenticatedUserResponse:
    return authenticated_user_response(current_user)


@router.patch("/me", response_model=AuthenticatedUserResponse)
async def update_customer_me(
    payload: CustomerProfileUpdate,
    current_user: CurrentUserDep,
    service: CustomerServiceDep,
) -> AuthenticatedUserResponse:
    try:
        user = await service.update_profile(current_user, payload.model_dump(exclude_unset=True))
    except CustomerError as exc:
        raise _error(exc) from exc
    return authenticated_user_response(user)


@router.get("/me/preferences", response_model=PreferenceResponse)
async def get_preferences(
    current_user: CurrentUserDep, service: CustomerServiceDep
) -> PreferenceResponse:
    prefs = await service.get_preferences(current_user)
    return PreferenceResponse(
        notify_payment_success=prefs.notify_payment_success,
        notify_payment_failed=prefs.notify_payment_failed,
        notify_payment_updates=prefs.notify_payment_updates,
        notify_payment_requests=prefs.notify_payment_requests,
        preferred_mode=prefs.preferred_mode,
        phone_verification=PHONE_VERIFICATION_STATUS,
    )


@router.patch("/me/preferences", response_model=PreferenceResponse)
async def update_preferences(
    payload: PreferenceUpdate,
    current_user: CurrentUserDep,
    service: CustomerServiceDep,
) -> PreferenceResponse:
    prefs = await service.update_preferences(current_user, payload.model_dump(exclude_unset=True))
    return PreferenceResponse(
        notify_payment_success=prefs.notify_payment_success,
        notify_payment_failed=prefs.notify_payment_failed,
        notify_payment_updates=prefs.notify_payment_updates,
        notify_payment_requests=prefs.notify_payment_requests,
        preferred_mode=prefs.preferred_mode,
        phone_verification=PHONE_VERIFICATION_STATUS,
    )


@router.get("/me/merchants", response_model=list[FavoriteMerchantResponse])
async def list_my_merchants(
    current_user: CurrentUserDep, service: CustomerServiceDep
) -> list[FavoriteMerchantResponse]:
    rows = await service.list_merchants(current_user)
    return [FavoriteMerchantResponse(**row) for row in rows]


@router.post(
    "/me/favorites",
    response_model=FavoriteMerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    payload: FavoriteCreate,
    current_user: CurrentUserDep,
    service: CustomerServiceDep,
) -> FavoriteMerchantResponse:
    try:
        await service.add_favorite(current_user, payload.merchant_id)
    except CustomerError as exc:
        raise _error(exc) from exc
    rows = await service.list_merchants(current_user)
    match = next((row for row in rows if row["merchant_id"] == payload.merchant_id), None)
    if match is None:
        return FavoriteMerchantResponse(
            merchant_id=payload.merchant_id,
            merchant_name="",
            is_favorite=True,
            payment_count=0,
            is_active=True,
            last_payment_reference=None,
        )
    return FavoriteMerchantResponse(**match)


@router.delete("/me/favorites/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    merchant_id: UUID,
    current_user: CurrentUserDep,
    service: CustomerServiceDep,
) -> None:
    await service.remove_favorite(current_user, merchant_id)


@router.get("/me/insights", response_model=CustomerInsightsResponse)
async def customer_insights(
    current_user: CurrentUserDep, service: CustomerServiceDep
) -> CustomerInsightsResponse:
    payload = await service.insights(current_user)
    return CustomerInsightsResponse(**payload)


@router.get(
    "/stats",
    response_model=CustomerStatsResponse,
    dependencies=[Depends(require_permission("users:read"))],
)
async def customer_stats(
    current_user: CurrentUserDep, service: CustomerServiceDep
) -> CustomerStatsResponse:
    try:
        payload = await service.platform_stats(current_user)
    except CustomerError as exc:
        raise _error(exc) from exc
    return CustomerStatsResponse(**payload)
