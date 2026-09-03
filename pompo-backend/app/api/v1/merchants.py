"""Merchant convenience routes and access evaluation."""

from fastapi import APIRouter

from app.api.v1.organization import get_my_merchant_access
from app.schemas.organization import MerchantAccessResponse

router = APIRouter(prefix="/merchants", tags=["Merchants"])

router.add_api_route(
    "/my-access",
    get_my_merchant_access,
    methods=["GET"],
    response_model=MerchantAccessResponse,
    summary="Get current user merchant access and operating context",
)
