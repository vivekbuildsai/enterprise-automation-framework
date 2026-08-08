from __future__ import annotations

import uuid

import httpx

from framework.api.constants import Headers


def inject_correlation_id(request: httpx.Request) -> None:
    """httpx request event hook: stamps every outgoing request with a
    correlation ID and request ID (unless the caller already set one, e.g.
    to propagate an ID received from an upstream UI action), so a single
    business operation can be traced across services in centralized logging
    even though this framework only ever sees one hop of it.
    """
    request.headers.setdefault(Headers.CORRELATION_ID, str(uuid.uuid4()))
    request.headers.setdefault(Headers.REQUEST_ID, str(uuid.uuid4()))
