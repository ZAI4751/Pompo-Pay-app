"""Authenticated read-only platform configuration for Master Admin."""

from fastapi import APIRouter, Depends

from app.api.deps import SettingsDep, require_platform_admin
from app.schemas.system import PlatformConfigResponse

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/config",
    response_model=PlatformConfigResponse,
    summary="Read-only platform configuration",
    description=(
        "Returns non-secret process configuration loaded from the environment. "
        "Secrets, database URLs, Redis URLs, and Celery URLs are never included. "
        "This endpoint does not accept updates. Restricted to platform_admin."
    ),
    dependencies=[Depends(require_platform_admin)],
)
async def get_platform_config(settings: SettingsDep) -> PlatformConfigResponse:
    """Return the running process configuration without secrets."""
    return PlatformConfigResponse.from_settings(settings)
