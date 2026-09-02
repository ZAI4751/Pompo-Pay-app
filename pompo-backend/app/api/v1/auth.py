"""Authentication endpoints: login, refresh, logout, current user."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.core.security.exceptions import (
    AuthError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.schemas.auth import (
    AuthenticatedUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_GENERIC_LOGIN_ERROR = "Incorrect email or password"
_GENERIC_TOKEN_ERROR = "Invalid or expired refresh token"


def _client_context(request: Request) -> tuple[str | None, str | None]:
    """Extract user-agent / client IP for refresh-session bookkeeping."""
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, auth_service: AuthServiceDep) -> TokenResponse:
    """Authenticate with email/password and issue a token pair.

    Unknown email, wrong password, and disabled accounts all return the
    same generic 401 — see AuthService.login for why.
    """
    user_agent, ip_address = _client_context(request)
    try:
        tokens, _user = await auth_service.login(
            email=payload.email,
            password=payload.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR
        ) from exc

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, request: Request, auth_service: AuthServiceDep
) -> TokenResponse:
    """Rotate a refresh token and issue a new access/refresh pair."""
    user_agent, ip_address = _client_context(request)
    try:
        tokens, _user = await auth_service.refresh(
            payload.refresh_token, user_agent=user_agent, ip_address=ip_address
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_TOKEN_ERROR
        ) from exc

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, auth_service: AuthServiceDep) -> None:
    """Revoke the refresh session behind the given token.

    Always returns 204, even for an already-invalid/expired/unknown token —
    logout must not reveal token validity, and must be safe to call twice.
    """
    await auth_service.logout(payload.refresh_token)


@router.get("/me", response_model=AuthenticatedUserResponse)
async def get_me(current_user: CurrentUserDep) -> AuthenticatedUserResponse:
    """Return the caller's own profile, resolved from the access token."""
    role = current_user.role
    return AuthenticatedUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        merchant_id=current_user.merchant_id,
        branch_id=current_user.branch_id,
        role_id=current_user.role_id,
        role_code=role.code if role is not None else "",
        is_active=current_user.is_active,
    )
