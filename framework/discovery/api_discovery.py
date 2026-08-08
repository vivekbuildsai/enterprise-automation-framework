from __future__ import annotations

from typing import Any

from framework.discovery.models import DiscoveredEndpoint

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def discover_from_openapi(spec: dict[str, Any]) -> list[DiscoveredEndpoint]:
    """Parses a standard OpenAPI 3.x (or Swagger 2.0) document's `paths`
    into `DiscoveredEndpoint`s. This is the authorized way to discover an
    API's surface: the spec is something the application team already
    publishes/shares, not something probed for by guessing endpoint
    names. Only ever emits endpoints the spec actually declares.
    """
    endpoints: list[DiscoveredEndpoint] = []
    for path, methods in spec.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.upper() not in _HTTP_METHODS or not isinstance(details, dict):
                continue
            endpoints.append(
                DiscoveredEndpoint(
                    method=method.upper(),
                    path=path,
                    summary=details.get("summary", ""),
                    request_schema=_request_schema(details),
                    response_schema=_response_schema(details),
                )
            )
    return endpoints


def _request_schema(details: dict[str, Any]) -> dict[str, Any] | None:
    content = details.get("requestBody", {}).get("content", {})
    schema: dict[str, Any] | None = content.get("application/json", {}).get("schema")
    return schema


def _response_schema(details: dict[str, Any]) -> dict[str, Any] | None:
    responses = details.get("responses", {})
    for status in ("200", "201", "default"):
        response = responses.get(status)
        if not isinstance(response, dict):
            continue
        content = response.get("content", {})
        schema: dict[str, Any] | None = content.get("application/json", {}).get("schema")
        if schema:
            return schema
    return None
