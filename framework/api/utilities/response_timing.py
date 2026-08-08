from __future__ import annotations

import httpx


def get_elapsed_ms(response: httpx.Response) -> float | None:
    """`response.elapsed` raises `RuntimeError` unless httpx's real timer
    wrapping ran — which it doesn't for responses built directly by a
    `httpx.MockTransport` handler (no real I/O to time). Since MockTransport
    is the standard way to unit-test an API client offline, logging and
    response-time assertions need to tolerate "unknown" rather than crash.
    Returns `None` when timing isn't available instead of raising.
    """
    try:
        return response.elapsed.total_seconds() * 1000
    except RuntimeError:
        return None
