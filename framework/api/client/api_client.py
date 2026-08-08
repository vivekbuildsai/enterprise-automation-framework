from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from framework.api.builders import RequestBuilder, RequestSpec
from framework.api.constants import RetryPolicy
from framework.api.exceptions import ApiConnectionError, ApiTimeoutError
from framework.api.middleware import build_event_hooks
from framework.exceptions import ApiRequestError
from framework.logger import get_logger

_logger = get_logger("ApiClient")

_TRANSIENT_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
)


class ApiClient:
    """Facade over `httpx.Client`: every REST verb, the middleware chain
    (correlation ID, structured logging, Allure attachment), and retry policy
    live here so page/service/test code never touches httpx directly — the
    same role `BasePage` plays over Playwright for the UI layer.

    One `ApiClient` per service/base-URL (see `framework/api/fixtures`),
    reusable across many requests within a test — it owns a real
    `httpx.Client` connection pool, so it should be closed (`.close()` / used
    as a context manager) when the test/session ends.
    """

    def __init__(
        self,
        base_url: str,
        *,
        auth: httpx.Auth | None = None,
        timeout_seconds: float = 30,
        default_headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is the seam for offline tests: pass an
        `httpx.MockTransport` to exercise this client (including its retry
        and middleware chain) against a fake server with zero network I/O.
        """
        self._client = httpx.Client(
            base_url=base_url,
            auth=auth,
            timeout=timeout_seconds,
            headers=default_headers or {},
            event_hooks=build_event_hooks(),
            transport=transport,
        )

    # -- REST verbs ------------------------------------------------------
    def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("GET", endpoint), **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("POST", endpoint), **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("PUT", endpoint), **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("PATCH", endpoint), **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("DELETE", endpoint), **kwargs)

    def head(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("HEAD", endpoint), **kwargs)

    def options(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return self._send(RequestBuilder("OPTIONS", endpoint), **kwargs)

    def request(self, builder: RequestBuilder) -> httpx.Response:
        """Execute a fully-assembled `RequestBuilder` — the entry point for
        anything the `get`/`post`/... convenience methods can't express
        (multipart uploads, XML bodies, form data).
        """
        return self._execute(builder.build())

    # -- Internals ---------------------------------------------------------
    def _send(
        self,
        builder: RequestBuilder,
        *,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        if path_params:
            builder.path_params(path_params)
        if query_params:
            builder.query_params(query_params)
        if headers:
            builder.headers(headers)
        if json is not None:
            builder.json_body(json)
        return self._execute(builder.build())

    def _execute(self, spec: RequestSpec) -> httpx.Response:
        if spec.method in RetryPolicy.SAFE_METHODS:
            return self._execute_with_retry(spec)
        try:
            return self._dispatch(spec)
        except _TRANSIENT_EXCEPTIONS as exc:
            raise self._translate_transport_error(spec, exc) from exc

    def _execute_with_retry(self, spec: RequestSpec) -> httpx.Response:
        retrying = Retrying(
            stop=stop_after_attempt(RetryPolicy.MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=RetryPolicy.WAIT_MULTIPLIER_SECONDS, max=RetryPolicy.WAIT_MAX_SECONDS
            ),
            retry=(
                retry_if_exception_type(_TRANSIENT_EXCEPTIONS)
                | retry_if_result(
                    lambda response: response.status_code in RetryPolicy.RETRYABLE_STATUS_CODES
                )
            ),
            reraise=True,
        )
        try:
            return retrying(self._dispatch, spec)
        except _TRANSIENT_EXCEPTIONS as exc:
            raise self._translate_transport_error(spec, exc) from exc
        except RetryError as exc:
            # Retries were exhausted on a *retryable status code*, not a raised
            # exception (reraise=True only re-raises when the last attempt
            # itself raised) — return that last response as-is so callers can
            # inspect/assert on it like any other response, instead of getting
            # an opaque tenacity.RetryError.
            return exc.last_attempt.result()  # type: ignore[no-any-return]

    def _dispatch(self, spec: RequestSpec) -> httpx.Response:
        try:
            return self._client.request(
                spec.method,
                spec.resolved_path(),
                params=spec.query_params or None,
                headers=spec.headers or None,
                json=spec.json_body,
                content=spec.xml_body,
                data=spec.form_data,
                files=spec.files,
            )
        except _TRANSIENT_EXCEPTIONS:
            # Left untranslated here so the retry wrapper (which matches on
            # the raw httpx exception types) can see and retry it; it's
            # translated to an Api*Error once retries are actually exhausted
            # (see `_execute_with_retry` / `_execute`).
            raise
        except httpx.HTTPError as exc:
            raise ApiRequestError(f"{spec.method} {spec.endpoint} failed: {exc}") from exc

    @staticmethod
    def _translate_transport_error(spec: RequestSpec, exc: Exception) -> ApiRequestError:
        if isinstance(exc, httpx.ConnectTimeout | httpx.ReadTimeout | httpx.PoolTimeout):
            return ApiTimeoutError(f"{spec.method} {spec.endpoint} timed out: {exc}")
        return ApiConnectionError(f"{spec.method} {spec.endpoint} connection failed: {exc}")

    def clear_cookies(self) -> None:
        """`httpx.Client` persists cookies (e.g. a session cookie set by a
        login response) across every subsequent request on the same client.
        That's usually what you want — but a negative test asserting "no
        auth -> 401" on a client that previously logged in would otherwise
        still authenticate via the leftover cookie. Call this first, or use
        a fresh `ApiClient` for that test.
        """
        self._client.cookies.clear()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
