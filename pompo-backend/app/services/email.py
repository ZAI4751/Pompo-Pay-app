"""Transactional email dispatch boundary.

External transactional email delivery (SMTP/SES/SendGrid) is an external
dependency. When external email delivery is not configured, this service
safely records the action without logging plaintext credentials or tokens.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailDispatcher:
    """Boundary for email dispatching."""

    def __init__(self) -> None:
        self.is_configured = False

    async def send_verification_email(
        self,
        *,
        recipient_email: str,
        user_name: str,
        verification_link: str,
    ) -> dict[str, Any]:
        """Dispatch email verification link. Does not log the verification token."""
        if not self.is_configured:
            logger.info(
                "email_verification_dispatch_skipped",
                reason="email_service_not_configured",
                recipient=recipient_email,
            )
            return {"status": "not_configured", "recipient": recipient_email}

        # Future SMTP / SES delivery integration boundary
        return {"status": "sent", "recipient": recipient_email}

    async def send_password_reset_email(
        self,
        *,
        recipient_email: str,
        user_name: str,
        reset_link: str,
    ) -> dict[str, Any]:
        """Dispatch password reset link. Does not log the reset token."""
        if not self.is_configured:
            logger.info(
                "password_reset_dispatch_skipped",
                reason="email_service_not_configured",
                recipient=recipient_email,
            )
            return {"status": "not_configured", "recipient": recipient_email}

        # Future SMTP / SES delivery integration boundary
        return {"status": "sent", "recipient": recipient_email}

    async def send_account_reactivation_email(
        self,
        *,
        recipient_email: str,
        user_name: str,
        reactivation_link: str,
    ) -> dict[str, Any]:
        """Dispatch account reactivation link. Does not log the token."""
        if not self.is_configured:
            logger.info(
                "account_reactivation_dispatch_skipped",
                reason="email_service_not_configured",
                recipient=recipient_email,
            )
            return {"status": "not_configured", "recipient": recipient_email}

        return {"status": "sent", "recipient": recipient_email}
