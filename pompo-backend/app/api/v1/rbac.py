"""Protected RBAC administration endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbSessionDep, require_permission
from app.models import Permission, Role
from app.schemas.rbac import (
    PermissionResponse,
    RoleCreate,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
    UserRoleAssignment,
)
from app.services.rbac import (
    RBACConflictError,
    RBACError,
    RBACNotFoundError,
    RBACService,
)

router = APIRouter(prefix="/rbac", tags=["RBAC Administration"])


def get_rbac_service(session: DbSessionDep) -> RBACService:
    """Provide a request-scoped RBAC service."""
    return RBACService(session)


RBACServiceDep = Annotated[RBACService, Depends(get_rbac_service)]


def _error(exc: RBACError) -> HTTPException:
    if isinstance(exc, RBACNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, RBACConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


def _role_response(role: Role, permission_codes: list[str]) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
        permission_codes=permission_codes,
    )


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permission("roles:read"))],
)
async def list_roles(service: RBACServiceDep) -> list[RoleResponse]:
    roles = await service.list_roles()
    return [
        _role_response(role, await service.get_role_permission_codes(role.id)) for role in roles
    ]


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles:read"))],
)
async def get_role(role_id: uuid.UUID, service: RBACServiceDep) -> RoleResponse:
    try:
        role = await service.get_role(role_id)
        return _role_response(role, await service.get_role_permission_codes(role.id))
    except RBACError as exc:
        raise _error(exc) from exc


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("roles:create"))],
)
async def create_role(
    payload: RoleCreate,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> RoleResponse:
    try:
        role = await service.create_role(
            current_user, payload.code, payload.name, payload.description
        )
        return _role_response(role, [])
    except RBACError as exc:
        raise _error(exc) from exc


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles:update"))],
)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> RoleResponse:
    try:
        role = await service.update_role(
            current_user,
            role_id,
            payload.name,
            payload.description,
            payload.is_active,
        )
        return _role_response(role, await service.get_role_permission_codes(role.id))
    except RBACError as exc:
        raise _error(exc) from exc


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("roles:delete"))],
)
async def delete_role(
    role_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> None:
    try:
        await service.delete_role(current_user, role_id)
    except RBACError as exc:
        raise _error(exc) from exc


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission("permissions:read"))],
)
async def list_permissions(service: RBACServiceDep) -> list[Permission]:
    return await service.list_permissions()


@router.get(
    "/permissions/{permission_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission("permissions:read"))],
)
async def get_permission(
    permission_id: uuid.UUID,
    service: RBACServiceDep,
) -> Permission:
    try:
        return await service.get_permission(permission_id)
    except RBACError as exc:
        raise _error(exc) from exc


@router.post(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RolePermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("role_permissions:grant"))],
)
async def grant_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> RolePermissionResponse:
    try:
        assignment = await service.grant_permission(current_user, role_id, permission_id)
        permission = await service.get_permission(permission_id)
        return RolePermissionResponse(
            role_id=assignment.role_id,
            permission_id=assignment.permission_id,
            permission_code=permission.code,
        )
    except RBACError as exc:
        raise _error(exc) from exc


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("role_permissions:revoke"))],
)
async def revoke_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> None:
    try:
        await service.revoke_permission(current_user, role_id, permission_id)
    except RBACError as exc:
        raise _error(exc) from exc


@router.put(
    "/users/{user_id}/role",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("users:roles:assign"))],
)
async def assign_role(
    user_id: uuid.UUID,
    payload: UserRoleAssignment,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> None:
    try:
        await service.assign_role(current_user, user_id, payload.role_id)
    except RBACError as exc:
        raise _error(exc) from exc


@router.delete(
    "/users/{user_id}/role",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("users:roles:revoke"))],
)
async def remove_role(
    user_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: RBACServiceDep,
) -> None:
    try:
        await service.remove_role(current_user, user_id)
    except RBACError as exc:
        raise _error(exc) from exc
