"""Authentication endpoints: login, refresh, logout, current user."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import AuthServiceDep, CurrentUserDep, OptionalCurrentUserDep
from app.core.security.exceptions import (
    AuthError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitAuthError,
    TokenExpiredError,
    TokenReplayError,
)
from app.schemas.auth import (
    AuthenticatedUserResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GenericSecurityResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RequestEmailVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
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
        is_email_verified=tokens.is_email_verified,
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
        is_email_verified=tokens.is_email_verified,
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
        is_email_verified=current_user.is_email_verified,
        phone=current_user.phone,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> None:
    try:
        await auth_service.change_password(
            current_user, payload.current_password, payload.new_password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password"
        ) from exc


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(current_user: CurrentUserDep, auth_service: AuthServiceDep) -> None:
    await auth_service.logout_all(current_user)


@router.post("/verify-email/request", response_model=GenericSecurityResponse)
async def request_email_verification(
    payload: RequestEmailVerificationRequest,
    request: Request,
    auth_service: AuthServiceDep,
    current_user: OptionalCurrentUserDep = None,
) -> GenericSecurityResponse:
    """Request a fresh email verification link. Does not reveal account existence."""
    user_agent, ip_address = _client_context(request)
    target_user = current_user
    if target_user is None and payload.email:
        target_user = await auth_service._users.get_by_email(payload.email.strip().lower())

    if target_user is not None and target_user.is_active and not target_user.is_email_verified:
        try:
            await auth_service.request_email_verification(
                target_user, user_agent=user_agent, ip_address=ip_address
            )
        except RateLimitAuthError:
            pass

    return GenericSecurityResponse(
        detail="If an unverified account matches, verification instructions have been dispatched.",
        email_delivery="not_configured",
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthServiceDep,
) -> VerifyEmailResponse:
    """Verify an account email with a single-use token."""
    try:
        user = await auth_service.verify_email(payload.token)
    except TokenReplayError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has already been used",
        ) from exc
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        ) from exc
    except (InvalidTokenError, AuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        ) from exc

    return VerifyEmailResponse(
        detail="Email successfully verified",
        is_email_verified=user.is_email_verified,
    )


@router.post("/forgot-password", response_model=GenericSecurityResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthServiceDep,
) -> GenericSecurityResponse:
    """Request a password reset link. Generic response prevents email enumeration."""
    user_agent, ip_address = _client_context(request)
    await auth_service.request_password_reset(
        payload.email, user_agent=user_agent, ip_address=ip_address
    )
    return GenericSecurityResponse(
        detail="If an account matches that email, password reset instructions have been sent.",
        email_delivery="not_configured",
    )


@router.post("/reset-password", response_model=GenericSecurityResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthServiceDep,
) -> GenericSecurityResponse:
    """Reset a password with a single-use token. Revokes existing refresh sessions."""
    try:
        await auth_service.reset_password(payload.token, payload.new_password)
    except TokenReplayError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has already been used",
        ) from exc
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        ) from exc
    except (InvalidTokenError, AuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        ) from exc

    return GenericSecurityResponse(
        detail="Password has been successfully reset. Please log in with your new password.",
        email_delivery="not_configured",
    )
