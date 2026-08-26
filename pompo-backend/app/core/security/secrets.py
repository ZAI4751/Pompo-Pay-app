"""Secret management and environment validation."""

from app.core.config.base import AppEnvironment, BaseAppSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecretValidator:
    """Validates that required secrets are configured for the current environment."""

    PLACEHOLDER_MARKERS = ("change-me", "changeme", "replace-me", "your-secret", "example")

    def __init__(self, settings: BaseAppSettings) -> None:
        self._settings = settings

    def validate(self) -> list[str]:
        """Validate secrets and return a list of warnings or errors."""
        issues: list[str] = []

        if self._settings.app_env == AppEnvironment.PRODUCTION:
            issues.extend(self._validate_production_secrets())
        elif self._settings.app_env == AppEnvironment.DEVELOPMENT:
            issues.extend(self._validate_development_secrets())

        for issue in issues:
            logger.warning("secret_validation_issue", issue=issue)

        return issues

    def _validate_production_secrets(self) -> list[str]:
        """Ensure production secrets are not placeholders."""
        issues: list[str] = []
        secrets_to_check = {
            "secret_key": self._settings.secret_key,
            "jwt_secret_key": self._settings.jwt_secret_key,
        }
        for name, value in secrets_to_check.items():
            if any(marker in value.lower() for marker in self.PLACEHOLDER_MARKERS):
                issues.append(f"{name} contains a placeholder value in production")
        return issues

    def _validate_development_secrets(self) -> list[str]:
        """Warn about placeholder secrets in development."""
        issues: list[str] = []
        if any(marker in self._settings.secret_key.lower() for marker in self.PLACEHOLDER_MARKERS):
            issues.append("secret_key is using a placeholder value (acceptable in development)")
        return issues

    def raise_if_invalid(self) -> None:
        """Raise RuntimeError if critical validation fails in production."""
        issues = self.validate()
        critical = [i for i in issues if "production" in i.lower()]
        if critical:
            raise RuntimeError(
                f"Secret validation failed: {'; '.join(critical)}"
            )
