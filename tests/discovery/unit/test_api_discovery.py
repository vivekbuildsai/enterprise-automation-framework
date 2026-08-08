from __future__ import annotations

import pytest

from framework.discovery import discover_from_openapi

pytestmark = pytest.mark.discovery

_SPEC = {
    "openapi": "3.0.0",
    "paths": {
        "/users": {
            "get": {
                "summary": "List users",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "array", "items": {"type": "object"}}
                            }
                        }
                    }
                },
            },
            "post": {
                "summary": "Create user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"content": {"application/json": {"schema": {"type": "object"}}}}
                },
            },
        },
        "/health": {"get": {"summary": "Health check"}},
    },
}


def test_discovers_every_declared_method() -> None:
    endpoints = discover_from_openapi(_SPEC)

    methods_by_path = {(e.method, e.path) for e in endpoints}
    assert ("GET", "/users") in methods_by_path
    assert ("POST", "/users") in methods_by_path
    assert ("GET", "/health") in methods_by_path
    assert len(endpoints) == 3


def test_extracts_request_and_response_schemas() -> None:
    endpoints = discover_from_openapi(_SPEC)
    create_user = next(e for e in endpoints if e.method == "POST" and e.path == "/users")

    assert create_user.request_schema is not None
    assert create_user.request_schema["properties"]["name"]["type"] == "string"
    assert create_user.response_schema == {"type": "object"}


def test_endpoint_with_no_schema_still_discovered() -> None:
    endpoints = discover_from_openapi(_SPEC)
    health = next(e for e in endpoints if e.path == "/health")

    assert health.summary == "Health check"
    assert health.request_schema is None
    assert health.response_schema is None


def test_never_invents_an_endpoint_not_in_the_spec() -> None:
    endpoints = discover_from_openapi(_SPEC)
    assert all(e.path in {"/users", "/health"} for e in endpoints)
