"""Pydantic contracts for RBAC administration."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str | None


class RoleResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_system_role: bool
    is_active: bool
    permission_codes: list[str] = Field(default_factory=list)


class RolePermissionResponse(BaseModel):
    role_id: uuid.UUID
    permission_id: uuid.UUID
    permission_code: str


class UserRoleAssignment(BaseModel):
    role_id: uuid.UUID
