"""Error monitoring and performance tracking utilities."""

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from .config import Config


def setup_sentry(config: Config) -> None:
    """Initialize Sentry error monitoring."""
    if not config.sentry_dsn:
        return

    # Configure Sentry integrations
    integrations = [
        LoggingIntegration(
            level=None,  # Don't capture logs automatically to avoid noise
            event_level=None,  # Only capture exceptions
        ),
    ]

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        integrations=integrations,
        environment="development" if config.development else "production",
        # Performance monitoring
        traces_sample_rate=1.0 if config.development else 0.1,
        profiles_sample_rate=1.0 if config.development else 0.1,
        # Error sampling
        sample_rate=1.0,
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send PII for trading bot
        max_breadcrumbs=50,
    )


def capture_exception(
    error: Exception, extra: dict[str, Any] | None = None
) -> str | None:
    """Capture an exception with optional extra context."""
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        return sentry_sdk.capture_exception(error)


def capture_message(
    message: str, level: str = "info", extra: dict[str, Any] | None = None
) -> str | None:
    """Capture a message with optional extra context."""
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        return sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str | None = None, username: str | None = None) -> None:
    """Set user context for error tracking."""
    sentry_sdk.set_user(
        {
            "id": user_id,
            "username": username,
        }
    )


def set_trading_context(
    market_id: str | None = None,
    strategy: str | None = None,
    opportunity_type: str | None = None,
) -> None:
    """Set trading-specific context for error tracking."""
    sentry_sdk.set_tag("market_id", market_id)
    sentry_sdk.set_tag("strategy", strategy)
    sentry_sdk.set_tag("opportunity_type", opportunity_type)


def performance_transaction(name: str, operation: str = "task"):
    """Context manager for performance monitoring of specific operations."""
    return sentry_sdk.start_transaction(name=name, op=operation)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """Add a breadcrumb for debugging context."""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )
