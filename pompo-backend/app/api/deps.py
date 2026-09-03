"""FastAPI dependency injection providers."""

from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config.base import BaseAppSettings, get_settings
from app.core.security.exceptions import AuthError
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.database.session import get_db_session
from app.models.user import User
from app.services.auth import AuthService
from app.services.authorization import AuthorizationService
from app.services.health import HealthService
from app.services.redis import RedisService


def get_app_settings() -> BaseAppSettings:
    """Provide application settings."""
    return get_settings()


SettingsDep = Annotated[BaseAppSettings, Depends(get_app_settings)]


def get_redis_service(request: Request) -> RedisService:
    """Provide Redis service from application state."""
    return request.app.state.redis_service


RedisDep = Annotated[RedisService, Depends(get_redis_service)]


def get_db_engine(request: Request) -> AsyncEngine:
    """Provide database engine from application state."""
    return request.app.state.engine


EngineDep = Annotated[AsyncEngine, Depends(get_db_engine)]


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_health_service(
    settings: SettingsDep,
    engine: EngineDep,
    redis: RedisDep,
) -> HealthService:
    """Provide health check service."""
    return HealthService(settings=settings, engine=engine, redis_service=redis)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


@lru_cache
def get_jwt_config() -> JWTConfig:
    """Provide JWT configuration singleton."""
    return JWTConfig(get_settings())


JWTConfigDep = Annotated[JWTConfig, Depends(get_jwt_config)]


@lru_cache
def get_password_hasher() -> PasswordHasher:
    """Provide password hasher singleton."""
    return PasswordHasher()


PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]


def get_auth_service(
    session: DbSessionDep,
    jwt_config: JWTConfigDep,
    password_hasher: PasswordHasherDep,
) -> AuthService:
    """Provide a request-scoped AuthService bound to this request's DB session."""
    return AuthService(session=session, jwt_config=jwt_config, password_hasher=password_hasher)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_authorization_service(session: DbSessionDep) -> AuthorizationService:
    """Provide a request-scoped authorization service."""
    from app.repositories.rbac import AuthorizationRepository

    return AuthorizationService(AuthorizationRepository(session))


AuthorizationServiceDep = Annotated[AuthorizationService, Depends(get_authorization_service)]


# auto_error=False so a missing/malformed Authorization header falls through
# to our own 401 below, rather than HTTPBearer's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: AuthServiceDep,
) -> User:
    """Resolve the authenticated user from the Authorization: Bearer header.

    Reusable by any endpoint that needs "who is calling this" without yet
    caring "what are they allowed to do" (that's M004's RequirePermission-
    style dependency, layered on top of this one).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: AuthServiceDep,
) -> User | None:
    """Resolve current user if Authorization header is present, else None."""
    if credentials is None:
        return None
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except AuthError:
        return None


OptionalCurrentUserDep = Annotated[User | None, Depends(get_optional_current_user)]


async def require_platform_admin(
    current_user: CurrentUserDep,
    authorization_service: AuthorizationServiceDep,
) -> User:
    """Require the platform_admin role for Master Admin control-plane reads."""
    from app.services.authorization import AuthorizationDeniedError

    try:
        return await authorization_service.require_platform_admin(current_user)
    except AuthorizationDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        ) from exc


def require_permission(permission_code: str) -> Callable[..., Awaitable[User]]:
    """Build a reusable dependency requiring one exact permission code."""

    async def permission_dependency(
        current_user: CurrentUserDep,
        authorization_service: AuthorizationServiceDep,
    ) -> User:
        from app.services.authorization import AuthorizationDeniedError

        try:
            return await authorization_service.require_permission(current_user, permission_code)
        except AuthorizationDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            ) from exc

    return permission_dependency
