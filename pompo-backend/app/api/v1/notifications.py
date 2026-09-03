"""In-app notification inbox."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.schemas.customer import NotificationListResponse, NotificationResponse
from app.services.notification import (
    NotificationError,
    NotificationForbiddenError,
    NotificationNotFoundError,
    NotificationService,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(session: DbSessionDep) -> NotificationService:
    return NotificationService(session)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


def _error(exc: NotificationError) -> HTTPException:
    if isinstance(exc, NotificationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, NotificationForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _item(row) -> NotificationResponse:
    return NotificationResponse(
        id=row.id,
        public_identifier=row.public_identifier,
        notification_type=row.notification_type.value
        if hasattr(row.notification_type, "value")
        else str(row.notification_type),
        title=row.title,
        body=row.body,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        payment_reference=row.payment_reference,
        read_at=row.read_at,
        created_at=getattr(row, "created_at", None),
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationListResponse:
    items, unread = await service.list_for_user(
        current_user, unread_only=unread_only, limit=limit, offset=offset
    )
    return NotificationListResponse(unread_count=unread, items=[_item(row) for row in items])


@router.post("/read-all", response_model=NotificationListResponse)
async def mark_all_read(
    current_user: CurrentUserDep, service: NotificationServiceDep
) -> NotificationListResponse:
    await service.mark_all_read(current_user)
    items, unread = await service.list_for_user(current_user)
    return NotificationListResponse(unread_count=unread, items=[_item(row) for row in items])


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> NotificationResponse:
    try:
        row = await service.mark_read(current_user, notification_id)
    except NotificationError as exc:
        raise _error(exc) from exc
    return _item(row)
