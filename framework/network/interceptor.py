from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, Response

from framework.logger import get_logger

_logger = get_logger("NetworkInterceptor")


@dataclass(frozen=True, slots=True)
class CapturedExchange:
    """One request/response pair observed while a `NetworkInterceptor` was
    attached — the raw material a `WidgetDataExtractor` matches against and
    pulls dimension/metric values out of.
    """

    url: str
    method: str
    request_body: str | None
    status: int
    response_json: Any | None


class NetworkInterceptor:
    """Generic Playwright response capture — the network half of the
    UI-widget-vs-database validation pipeline (see
    `framework.database.clickhouse.DashboardRepository` for the database
    half). Records every response matching `url_pattern` while attached,
    parsing JSON bodies where possible. Makes no assumption about REST vs.
    JSON-RPC vs. any specific endpoint shape — see `JsonRpcInterceptor`
    for the JSON-RPC-flavored specialization.

    Usage::

        with NetworkInterceptor(page, url_pattern="**/api/**") as interceptor:
            page.click("text=Refresh dashboard")
            page.wait_for_load_state("networkidle")
        exchanges = interceptor.captured
    """

    def __init__(self, page: Page, *, url_pattern: str = "**/*") -> None:
        self._page = page
        self._url_pattern = url_pattern
        self.captured: list[CapturedExchange] = []
        # Compiled once per interceptor instance rather than on every
        # `_on_response` call — a busy page can emit hundreds of responses
        # while attached, and the pattern never changes for the lifetime
        # of one interceptor.
        self._compiled_pattern: re.Pattern[str] | None = (
            None
            if url_pattern in ("**/*", "*", "")
            else re.compile(re.escape(url_pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*"))
        )

    def _on_response(self, response: Response) -> None:
        if not response.url or not self._url_matches(response.url):
            return
        request = response.request
        body: Any | None
        try:
            body = response.json()
        except Exception:
            body = None
        exchange = CapturedExchange(
            url=response.url,
            method=request.method,
            request_body=request.post_data,
            status=response.status,
            response_json=body,
        )
        _logger.debug(f"Captured {exchange.method} {exchange.url} -> {exchange.status}")
        self.captured.append(exchange)

    def _url_matches(self, url: str) -> bool:
        if self._compiled_pattern is None:
            return True
        return (
            self._compiled_pattern.search(url) is not None
            or self._compiled_pattern.search(urlparse(url).path) is not None
        )

    def __enter__(self) -> NetworkInterceptor:
        self.captured = []
        self._page.on("response", self._on_response)
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._page.remove_listener("response", self._on_response)
