"""Fixed values for the API layer: header names, content types, and the
default retry/timeout policy. Centralized so a header name typo can't
silently diverge between the client, middleware, and tests.
"""

from __future__ import annotations


class Headers:
    AUTHORIZATION = "Authorization"
    CONTENT_TYPE = "Content-Type"
    ACCEPT = "Accept"
    CORRELATION_ID = "X-Correlation-Id"
    REQUEST_ID = "X-Request-Id"
    API_KEY = "X-Api-Key"


class ContentType:
    JSON = "application/json"
    XML = "application/xml"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"


class RetryPolicy:
    MAX_ATTEMPTS = 3
    WAIT_MULTIPLIER_SECONDS = 0.5
    WAIT_MAX_SECONDS = 8
    # Only idempotent/safe methods are auto-retried on transient failures —
    # retrying POST/PATCH blindly can duplicate side effects.
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
    RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class DefaultTimeouts:
    CONNECT_SECONDS = 10
    READ_SECONDS = 30
    WRITE_SECONDS = 30
    POOL_SECONDS = 10
