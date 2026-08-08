from __future__ import annotations

import allure
import httpx

from framework.api.constants import Headers
from framework.logger import get_logger

_logger = get_logger("ApiClient")


def attach_request(request: httpx.Request) -> None:
    """httpx request event hook: attaches the outgoing request to the Allure
    report. Best-effort — if there's no active Allure test context (e.g. a
    script run outside pytest), attaching is skipped rather than failing the
    actual API call.
    """
    try:
        body = request.content.decode("utf-8", errors="replace") if request.content else ""
        allure.attach(
            f"{request.method} {request.url}\n\n{dict(request.headers)}\n\n{body}",
            name=f"API Request: {request.method} {request.url.path}",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:  # noqa: BLE001 - reporting must never break the test
        _logger.debug("Skipped Allure request attachment (no active test context)")


def attach_response(response: httpx.Response) -> None:
    """httpx response event hook: attaches the response (status/headers/body)
    to the Allure report, plus a JSON attachment when the body is JSON so
    it renders nicely in the report instead of as a text blob.
    """
    try:
        correlation_id = response.request.headers.get(Headers.CORRELATION_ID, "-")
        allure.attach(
            f"Status: {response.status_code}\nCorrelation-Id: {correlation_id}\n\n"
            f"{dict(response.headers)}\n\n{response.text}",
            name=f"API Response: {response.status_code} {response.request.url.path}",
            attachment_type=allure.attachment_type.TEXT,
        )
        content_type = response.headers.get(Headers.CONTENT_TYPE, "")
        if "json" in content_type:
            allure.attach(
                response.text,
                name="Response JSON",
                attachment_type=allure.attachment_type.JSON,
            )
    except Exception:  # noqa: BLE001 - reporting must never break the test
        _logger.debug("Skipped Allure response attachment (no active test context)")
