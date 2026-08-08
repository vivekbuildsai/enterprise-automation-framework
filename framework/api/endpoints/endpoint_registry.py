"""Centralized endpoint templates — the only place a URL path literal should
ever appear. Services build requests from these constants (with
`RequestBuilder`/`ApiClient` resolving `{param}` placeholders), so a path
change is a one-line edit here instead of a grep-and-replace across tests.

Add one class per domain as new services are built (mirrors the telecom
module list in the platform roadmap — `SubscriberEndpoints`,
`OrderEndpoints`, etc. would follow this same shape). Today there's one
domain, matching the sample slice this milestone implements end-to-end.
"""

from __future__ import annotations


class Endpoints:
    """Sample-provider (dummyjson.com) endpoints — auth + users."""

    LOGIN = "/auth/login"
    AUTH_ME = "/auth/me"

    USERS = "/users"
    USER_BY_ID = "/users/{id}"
    USER_ADD = "/users/add"
    USER_SEARCH = "/users/search"
