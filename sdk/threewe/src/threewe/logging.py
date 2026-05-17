# SPDX-License-Identifier: Apache-2.0
"""Structured logging with correlation IDs for cross-layer tracing.

Requires the optional ``logging`` extra: ``pip install threewe[logging]``.
Falls back to stdlib logging when structlog is not installed.

Usage::

    from threewe.logging import configure_logging, get_logger, correlation_context

    configure_logging(json=True)
    log = get_logger(__name__)

    with correlation_context() as cid:
        log.info("navigation_started", target_x=2.0, target_y=1.5)
"""

from __future__ import annotations

import contextvars
import logging as _stdlib_logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    """Generate a short unique correlation ID."""
    return uuid.uuid4().hex[:16]


@contextmanager
def correlation_context(cid: str | None = None) -> Generator[str, None, None]:
    """Set a correlation ID for the current async/thread context."""
    if cid is None:
        cid = new_correlation_id()
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)


def get_correlation_id() -> str:
    """Return the current correlation ID (empty string if unset)."""
    return _correlation_id.get("")


def _add_correlation_id(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    cid = _correlation_id.get("")
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_logging(json: bool = False, level: str = "INFO") -> None:
    """Configure structured logging output. Call once at application startup.

    Args:
        json: Emit JSON lines (for log aggregation). Default: human-readable console.
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    try:
        import structlog
    except ImportError as e:
        raise ImportError(
            "structlog is required for structured logging. "
            "Install with: pip install threewe[logging]"
        ) from e

    log_level = getattr(_stdlib_logging, level.upper(), _stdlib_logging.INFO)
    _stdlib_logging.basicConfig(format="%(message)s", level=log_level, force=True)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_correlation_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a structured logger, falling back to stdlib if structlog is unavailable."""
    try:
        import structlog

        return structlog.get_logger(name)
    except ImportError:
        return _stdlib_logging.getLogger(name)
