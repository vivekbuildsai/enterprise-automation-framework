from __future__ import annotations

from collections.abc import Callable

from framework.api.middleware.allure_middleware import attach_request, attach_response
from framework.api.middleware.correlation_middleware import inject_correlation_id
from framework.api.middleware.logging_middleware import log_request, log_response

__all__ = [
    "attach_request",
    "attach_response",
    "build_event_hooks",
    "inject_correlation_id",
    "log_request",
    "log_response",
]


def build_event_hooks() -> dict[str, list[Callable[..., None]]]:
    """The full request/response middleware chain, in the order it must run:
    correlation ID first (everything downstream logs/attaches it), then
    structured logging, then Allure reporting. Passed straight to
    `httpx.Client(event_hooks=...)`.
    """
    return {
        "request": [inject_correlation_id, log_request, attach_request],
        "response": [log_response, attach_response],
    }
