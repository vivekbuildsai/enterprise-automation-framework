"""API-layer exception hierarchy.

All API exceptions derive from the framework-wide `ApiRequestError` /
`ValidationError` so callers that only care about "something went wrong with
an API call" can catch one type, while callers that need to distinguish
transport failures from validation failures can catch the specific subclass.
"""

from __future__ import annotations

from framework.exceptions import ApiRequestError, ValidationError


class ApiConnectionError(ApiRequestError):
    """Raised when the underlying transport cannot reach the host at all
    (DNS failure, connection refused, TLS handshake failure).
    """


class ApiTimeoutError(ApiRequestError):
    """Raised when a request exceeds its configured timeout."""


class ApiAuthenticationError(ApiRequestError):
    """Raised when an auth strategy cannot obtain or apply credentials
    (e.g. token endpoint failure, missing client secret).
    """


class ApiSchemaValidationError(ValidationError):
    """Raised when a response body fails JSON Schema validation."""


class ApiResponseValidationError(ValidationError):
    """Raised when a response fails a non-schema assertion (status code,
    header, cookie, response time, field value, ...).
    """
