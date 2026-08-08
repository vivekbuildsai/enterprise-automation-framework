from __future__ import annotations

from typing import Any, NoReturn

import httpx

from framework.api.exceptions import ApiResponseValidationError
from framework.api.schemas import validate_against_schema
from framework.api.utilities import get_elapsed_ms
from framework.api.validators.json_path import resolve_json_path
from framework.logger import get_logger

_logger = get_logger("ResponseValidator")


class ResponseValidator:
    """Fluent, chainable assertions over an `httpx.Response` (Facade Pattern,
    mirroring `Assert`/`SoftAssert` for the UI layer). Every `expect_*`
    method returns `self` and raises `ApiResponseValidationError` /
    `ApiSchemaValidationError` immediately on failure — there's no soft-fail
    mode here because a malformed API response usually means every
    subsequent check is meaningless (e.g. asserting fields on a 500 body).

    Usage:
        ResponseValidator(response) \\
            .expect_status(200) \\
            .expect_response_time_under(2000) \\
            .expect_json_field("username", "emilys") \\
            .expect_schema("user_schema")
    """

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def expect_status(self, expected: int | set[int], description: str = "") -> ResponseValidator:
        allowed = {expected} if isinstance(expected, int) else expected
        actual = self._response.status_code
        if actual not in allowed:
            body_preview = self._response.text[:500]
            self._fail(
                description or "Status code",
                f"expected one of {sorted(allowed)}, got {actual} (body: {body_preview})",
            )
        return self

    def expect_header(
        self, name: str, expected_value: str | None = None, description: str = ""
    ) -> ResponseValidator:
        if name not in self._response.headers:
            self._fail(description or f"Header '{name}'", "header not present")
        elif expected_value is not None and self._response.headers[name] != expected_value:
            self._fail(
                description or f"Header '{name}'",
                f"expected '{expected_value}', got '{self._response.headers[name]}'",
            )
        return self

    def expect_cookie(
        self, name: str, expected_value: str | None = None, description: str = ""
    ) -> ResponseValidator:
        if name not in self._response.cookies:
            self._fail(description or f"Cookie '{name}'", "cookie not present")
        elif expected_value is not None and self._response.cookies[name] != expected_value:
            self._fail(
                description or f"Cookie '{name}'",
                f"expected '{expected_value}', got '{self._response.cookies[name]}'",
            )
        return self

    def expect_response_time_under(self, max_ms: float, description: str = "") -> ResponseValidator:
        elapsed_ms = get_elapsed_ms(self._response)
        if elapsed_ms is None:
            # No real I/O was timed (e.g. an httpx.MockTransport-backed response in
            # an offline test) — there's nothing to assert against, so skip rather
            # than fail on an artifact of how the response was constructed.
            label = description or "Response time"
            _logger.debug(f"Skipping response-time check ({label}): elapsed unavailable")
            return self
        if elapsed_ms > max_ms:
            self._fail(
                description or "Response time",
                f"expected under {max_ms}ms, took {elapsed_ms:.0f}ms",
            )
        return self

    def expect_json_field(
        self, path: str, expected: Any, description: str = ""
    ) -> ResponseValidator:
        actual = self._resolve(path)
        if actual != expected:
            self._fail(description or f"Field '{path}'", f"expected '{expected}', got '{actual}'")
        return self

    def expect_json_field_present(self, path: str, description: str = "") -> ResponseValidator:
        self._resolve(path)  # raises via _fail if missing
        return self

    def expect_collection_size(
        self,
        path: str,
        *,
        exact: int | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        description: str = "",
    ) -> ResponseValidator:
        collection = self._resolve(path)
        if not isinstance(collection, list):
            self._fail(
                description or f"Collection '{path}'",
                f"expected a list, got {type(collection).__name__}",
            )

        size = len(collection)
        label = description or f"Collection '{path}' size"
        if exact is not None and size != exact:
            self._fail(label, f"expected exactly {exact}, got {size}")
        if min_size is not None and size < min_size:
            self._fail(label, f"expected at least {min_size}, got {size}")
        if max_size is not None and size > max_size:
            self._fail(label, f"expected at most {max_size}, got {size}")
        return self

    def expect_schema(self, schema_name: str) -> ResponseValidator:
        validate_against_schema(self._response.json(), schema_name)
        return self

    def json(self) -> Any:
        """Escape hatch to the raw parsed body for assertions this validator
        doesn't cover, without callers needing to hold onto the response too.
        """
        return self._response.json()

    def _resolve(self, path: str) -> Any:
        try:
            return resolve_json_path(self._response.json(), path)
        except (KeyError, IndexError) as exc:
            self._fail(f"Field '{path}'", str(exc))

    def _fail(self, subject: str, reason: str) -> NoReturn:
        message = f"{subject}: {reason}"
        _logger.error(f"Response validation failed — {message}")
        raise ApiResponseValidationError(message)
