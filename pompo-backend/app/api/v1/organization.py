"""Tenant-scoped merchant and branch administration endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.schemas.organization import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    MerchantCreate,
    MerchantResponse,
    MerchantUpdate,
)
from app.services.organization import (
    OrganizationConflictError,
    OrganizationError,
    OrganizationNotFoundError,
    OrganizationService,
)

router = APIRouter(prefix="/organization", tags=["Organization Administration"])


def get_organization_service(session: DbSessionDep) -> OrganizationService:
    return OrganizationService(session)


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]


def _error(exc: OrganizationError) -> HTTPException:
    if isinstance(exc, OrganizationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, OrganizationConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/merchants", response_model=list[MerchantResponse])
async def list_merchants(current_user: CurrentUserDep, service: OrganizationServiceDep) -> list:
    try:
        return await service.list_merchants(current_user)
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.post("/merchants", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    payload: MerchantCreate, current_user: CurrentUserDep, service: OrganizationServiceDep
) -> MerchantResponse:
    try:
        return await service.create_merchant(current_user, payload.model_dump())
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.get("/merchants/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: uuid.UUID, current_user: CurrentUserDep, service: OrganizationServiceDep
) -> MerchantResponse:
    try:
        return await service.get_merchant(current_user, merchant_id)
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.patch("/merchants/{merchant_id}", response_model=MerchantResponse)
async def update_merchant(
    merchant_id: uuid.UUID,
    payload: MerchantUpdate,
    current_user: CurrentUserDep,
    service: OrganizationServiceDep,
) -> MerchantResponse:
    try:
        return await service.update_merchant(
            current_user, merchant_id, payload.model_dump(exclude_unset=True)
        )
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.delete("/merchants/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant(
    merchant_id: uuid.UUID, current_user: CurrentUserDep, service: OrganizationServiceDep
) -> None:
    try:
        await service.delete_merchant(current_user, merchant_id)
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.get("/merchants/{merchant_id}/branches", response_model=list[BranchResponse])
async def list_branches(
    merchant_id: uuid.UUID, current_user: CurrentUserDep, service: OrganizationServiceDep
) -> list:
    try:
        return await service.list_branches(current_user, merchant_id)
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.post(
    "/merchants/{merchant_id}/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(
    merchant_id: uuid.UUID,
    payload: BranchCreate,
    current_user: CurrentUserDep,
    service: OrganizationServiceDep,
) -> BranchResponse:
    try:
        return await service.create_branch(current_user, merchant_id, payload.model_dump())
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.patch("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: uuid.UUID,
    payload: BranchUpdate,
    current_user: CurrentUserDep,
    service: OrganizationServiceDep,
) -> BranchResponse:
    try:
        return await service.update_branch(
            current_user, branch_id, payload.model_dump(exclude_unset=True)
        )
    except OrganizationError as exc:
        raise _error(exc) from exc


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    branch_id: uuid.UUID, current_user: CurrentUserDep, service: OrganizationServiceDep
) -> None:
    try:
        await service.delete_branch(current_user, branch_id)
    except OrganizationError as exc:
        raise _error(exc) from exc
