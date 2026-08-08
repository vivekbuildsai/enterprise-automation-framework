from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from framework.api.builders.request_spec import RequestSpec
from framework.api.constants import ContentType, Headers
from framework.exceptions import ConfigurationError

_BODY_FIELDS = ("json_body", "xml_body", "form_data", "files")


class RequestBuilder:
    """Fluent builder for `RequestSpec` (Builder Pattern). Every method
    returns `self`, so a request is assembled as a readable chain:

        RequestBuilder("POST", Endpoints.USERS)
            .header("X-Test-Run", run_id)
            .json_body(CreateUserRequest(first_name="Ada"))
            .build()

    Exactly one body type may be set — mixing e.g. `.json_body()` and
    `.form_data()` on the same request is almost always a mistake, so it's
    caught here rather than surfacing as a confusing transport-layer error.
    """

    def __init__(self, method: str, endpoint: str) -> None:
        self._spec = RequestSpec(method=method.upper(), endpoint=endpoint)

    def header(self, key: str, value: str) -> RequestBuilder:
        self._spec.headers[key] = value
        return self

    def headers(self, headers: dict[str, str]) -> RequestBuilder:
        self._spec.headers.update(headers)
        return self

    def query_param(self, key: str, value: Any) -> RequestBuilder:
        self._spec.query_params[key] = value
        return self

    def query_params(self, params: dict[str, Any]) -> RequestBuilder:
        self._spec.query_params.update(params)
        return self

    def path_param(self, key: str, value: Any) -> RequestBuilder:
        self._spec.path_params[key] = value
        return self

    def path_params(self, params: dict[str, Any]) -> RequestBuilder:
        self._spec.path_params.update(params)
        return self

    def json_body(self, body: BaseModel | dict[str, Any] | list[Any]) -> RequestBuilder:
        self._guard_single_body("json_body")
        self._spec.json_body = body.model_dump(mode="json") if isinstance(body, BaseModel) else body
        self._spec.headers.setdefault(Headers.CONTENT_TYPE, ContentType.JSON)
        return self

    def xml_body(self, body: str) -> RequestBuilder:
        self._guard_single_body("xml_body")
        self._spec.xml_body = body
        self._spec.headers.setdefault(Headers.CONTENT_TYPE, ContentType.XML)
        return self

    def form_data(self, data: dict[str, Any]) -> RequestBuilder:
        self._guard_single_body("form_data")
        self._spec.form_data = data
        self._spec.headers.setdefault(Headers.CONTENT_TYPE, ContentType.FORM_URLENCODED)
        return self

    def multipart(self, files: dict[str, Any]) -> RequestBuilder:
        """`files` follows httpx's own convention: each value is either
        `(filename, fileobj_or_bytes)` or `(filename, fileobj_or_bytes, content_type)`.
        """
        self._guard_single_body("files")
        self._spec.files = files
        return self

    def file_upload(
        self, field_name: str, file_path: str | Path, *, content_type: str | None = None
    ) -> RequestBuilder:
        """Convenience over `.multipart()` for the common case of uploading
        one real file from disk.
        """
        path = Path(file_path)
        file_bytes = path.read_bytes()
        entry = (path.name, file_bytes, content_type) if content_type else (path.name, file_bytes)
        return self.multipart({field_name: entry})

    def build(self) -> RequestSpec:
        return self._spec

    def _guard_single_body(self, field_name: str) -> None:
        already_set = [
            f for f in _BODY_FIELDS if f != field_name and getattr(self._spec, f) is not None
        ]
        if already_set:
            raise ConfigurationError(
                f"Cannot set '{field_name}' — request body already set via {already_set}. "
                "Only one body type (json/xml/form/multipart) is allowed per request."
            )
