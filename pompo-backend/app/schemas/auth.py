"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    is_email_verified: bool = False
    phone: str | None = None


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
