"""Lightweight support request endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.schemas.customer import SupportRequestCreate, SupportRequestResponse
from app.services.support import (
    SupportError,
    SupportForbiddenError,
    SupportInvalidError,
    SupportNotFoundError,
    SupportService,
)

router = APIRouter(prefix="/support-requests", tags=["Support"])


def get_support_service(session: DbSessionDep) -> SupportService:
    return SupportService(session)


SupportServiceDep = Annotated[SupportService, Depends(get_support_service)]


def _error(exc: SupportError) -> HTTPException:
    if isinstance(exc, SupportNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SupportForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, SupportInvalidError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _item(row) -> SupportRequestResponse:
    return SupportRequestResponse(
        id=row.id,
        public_identifier=row.public_identifier,
        category=row.category.value if hasattr(row.category, "value") else str(row.category),
        subject=row.subject,
        message=row.message,
        payment_reference=row.payment_reference,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        created_at=getattr(row, "created_at", None),
    )


@router.post("", response_model=SupportRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_support_request(
    payload: SupportRequestCreate,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SupportRequestResponse:
    try:
        row = await service.create(current_user, payload.model_dump(exclude_none=True))
    except SupportError as exc:
        raise _error(exc) from exc
    return _item(row)


@router.get("", response_model=list[SupportRequestResponse])
async def list_support_requests(
    current_user: CurrentUserDep,
    service: SupportServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[SupportRequestResponse]:
    rows = await service.list_visible(current_user, limit=limit, offset=offset)
    return [_item(row) for row in rows]


@router.get("/{public_identifier}", response_model=SupportRequestResponse)
async def get_support_request(
    public_identifier: str,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SupportRequestResponse:
    try:
        row = await service.get_visible(current_user, public_identifier)
    except SupportError as exc:
        raise _error(exc) from exc
    return _item(row)
