"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import User


class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    """POST /auth/refresh request body."""

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """POST /auth/logout request body."""

    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password request body."""

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=72)


class DeactivateAccountRequest(BaseModel):
    """POST /auth/deactivate-account request body.

    ``confirmation`` must be the exact string ``DEACTIVATE``. A client-side
    boolean is not accepted as proof of intent.
    """

    current_password: str = Field(min_length=1, max_length=256)
    confirmation: str = Field(min_length=1, max_length=32)


class ReactivateAccountRequestBody(BaseModel):
    """POST /auth/reactivate-account/request request body."""

    email: EmailStr


class ReactivateAccountConfirmRequest(BaseModel):
    """POST /auth/reactivate-account request body."""

    token: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class LogoutAllRequest(BaseModel):
    """POST /auth/logout-all request body. Refresh token is optional extra revoke."""

    refresh_token: str | None = Field(default=None, min_length=1)


class TokenResponse(BaseModel):
    """Access + refresh token pair returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")
    is_email_verified: bool = False


class AuthenticatedUserResponse(BaseModel):
    """Safe user representation returned by /auth/me.

    ``role_code`` is the system/custom role slug used by mobile mode switching.
    Permission catalogs are still loaded from the RBAC API, not this payload.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    merchant_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    role_id: uuid.UUID
    role_code: str = ""
    is_active: bool
    account_status: str = "active"
    deactivated_at: datetime | None = None
    reactivated_at: datetime | None = None
    is_email_verified: bool = False
    phone: str | None = None


def authenticated_user_response(user: User) -> AuthenticatedUserResponse:
    """Map a User ORM row to the public authenticated-user contract."""
    role = user.role
    return AuthenticatedUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        merchant_id=user.merchant_id,
        branch_id=user.branch_id,
        role_id=user.role_id,
        role_code=role.code if role is not None else "",
        is_active=user.is_active,
        account_status=user.account_status,
        deactivated_at=user.deactivated_at,
        reactivated_at=user.reactivated_at,
        is_email_verified=user.is_email_verified,
        phone=user.phone,
    )


class RequestEmailVerificationRequest(BaseModel):
    """POST /auth/verify-email/request request body."""

    email: EmailStr | None = None


class VerifyEmailRequest(BaseModel):
    """POST /auth/verify-email request body."""

    token: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password request body."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password request body."""

    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=72)


class GenericSecurityResponse(BaseModel):
    """Generic response for security operations to avoid enumeration."""

    detail: str
    email_delivery: str = "not_configured"


class VerifyEmailResponse(BaseModel):
    """Response after verifying an email token."""

    detail: str
    is_email_verified: bool
