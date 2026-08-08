from __future__ import annotations

import httpx

from framework.api.constants import Headers
from framework.api.utilities import get_elapsed_ms
from framework.logger import get_logger

_logger = get_logger("ApiClient")

_REDACTED_HEADERS = frozenset(
    {Headers.AUTHORIZATION.lower(), Headers.API_KEY.lower(), "cookie", "set-cookie"}
)
_REDACTED_VALUE = "***REDACTED***"


def _safe_headers(headers: httpx.Headers) -> dict[str, str]:
    return {
        k: (_REDACTED_VALUE if k.lower() in _REDACTED_HEADERS else v) for k, v in headers.items()
    }


def log_request(request: httpx.Request) -> None:
    """httpx request event hook. Logs method/URL/headers/body with secrets
    redacted, tagged with the correlation ID `inject_correlation_id` already
    stamped on the request (hooks run in registration order).

    Multipart/file-upload bodies are streamed rather than eagerly buffered,
    so `.content` raises `RequestNotRead` until `.read()` materializes it —
    same reason `log_response` reads the response before touching `.text`.
    """
    request.read()
    correlation_id = request.headers.get(Headers.CORRELATION_ID, "-")
    body_preview = (
        request.content[:2000].decode("utf-8", errors="replace") if request.content else ""
    )
    _logger.info(
        f"[{correlation_id}] --> {request.method} {request.url} "
        f"headers={_safe_headers(request.headers)} body={body_preview}"
    )


def log_response(response: httpx.Response) -> None:
    """httpx response event hook. Reads the body here (safe per httpx docs —
    hooks fire before user code touches `.content`) so both this log line
    and the caller's later `.json()`/`.text` see the same materialized body.
    """
    response.read()
    correlation_id = response.request.headers.get(Headers.CORRELATION_ID, "-")
    elapsed_ms = get_elapsed_ms(response)
    elapsed_label = f"{elapsed_ms:.0f}ms" if elapsed_ms is not None else "n/a"
    body_preview = response.text[:2000]
    _logger.info(
        f"[{correlation_id}] <-- {response.status_code} {response.request.url} "
        f"({elapsed_label}) headers={_safe_headers(response.headers)} body={body_preview}"
    )
