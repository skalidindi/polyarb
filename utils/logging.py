"""Logging utilities with structlog for performance."""

import logging
import sys
from typing import Any

import structlog
import orjson


def setup_structlog(
    level: str = "INFO", log_file: str | None = None, development: bool = True
) -> Any:
    """Set up structlog configuration for high-performance logging."""
    
    # Configure structlog
    if development:
        # Pretty console output for development
        processors = [
            structlog.dev.set_exc_info,
            structlog.processors.add_log_level,
            structlog.processors.add_logger_name,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Fast JSON output for production
        processors = [
            structlog.processors.add_log_level,
            structlog.processors.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
        level=level.upper(),
    )

    # Disable standard library logging in production for performance
    if not development:
        logging.getLogger().disabled = True
        
    return structlog.get_logger("polyarb")


def setup_logging(
    level: str = "INFO", format_string: str | None = None, log_file: str | None = None
) -> logging.Logger:
    """Legacy logging setup - kept for compatibility."""
    
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Create logger
    logger = logging.getLogger("polyarb")
    logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> Any:
    """Get a structlog logger instance."""
    return structlog.get_logger(f"polyarb.{name}")


def get_legacy_logger(name: str) -> logging.Logger:
    """Get a legacy logging instance."""
    return logging.getLogger(f"polyarb.{name}")
