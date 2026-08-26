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


class TokenResponse(BaseModel):
    """Access + refresh token pair returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class AuthenticatedUserResponse(BaseModel):
    """Safe user representation returned by /auth/me.

    Deliberately excludes ``hashed_password`` and does not (yet) include
    role/permission details — that's M004's job.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    merchant_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    role_id: uuid.UUID
    is_active: bool
