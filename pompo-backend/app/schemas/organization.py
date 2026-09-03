"""Pydantic contracts for merchant and branch administration."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MerchantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=100)
    contact_email: EmailStr
    contact_phone: str = Field(min_length=1, max_length=32)


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=100)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, min_length=1, max_length=32)
    is_active: bool | None = None


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_name: str | None
    registration_number: str | None
    contact_email: EmailStr
    contact_phone: str
    is_active: bool


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    address: str | None
    is_active: bool


class TillCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$")
    name: str = Field(min_length=1, max_length=255)


class TillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class TillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    merchant_id: uuid.UUID
    code: str
    name: str
    is_active: bool


class AccessibleMerchant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_name: str | None = None
    is_active: bool


class AccessibleBranch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    address: str | None = None
    is_active: bool


class AccessibleTill(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    merchant_id: uuid.UUID
    code: str
    name: str
    is_active: bool


class MerchantAccessResponse(BaseModel):
    """Authoritative backend evaluation of merchant capability for an account."""

    allowed: bool
    reason: str | None = None
    can_generate_qr: bool = False
    merchant: AccessibleMerchant | None = None
    merchants: list[AccessibleMerchant] = []
    branches: list[AccessibleBranch] = []
    tills: list[AccessibleTill] = []
    operating_branch_id: uuid.UUID | None = None
    operating_till_id: uuid.UUID | None = None
    permissions: list[str] = []
