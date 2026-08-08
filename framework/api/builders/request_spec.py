from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestSpec:
    """Fully-resolved description of one HTTP request, produced by
    `RequestBuilder.build()` and consumed by `ApiClient`. Plain data — the
    builder does the assembly, the client does the I/O, neither knows about
    the other's internals.
    """

    method: str
    endpoint: str
    path_params: dict[str, Any] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    json_body: Any = None
    xml_body: str | None = None
    form_data: dict[str, Any] | None = None
    files: dict[str, Any] | None = None

    def resolved_path(self) -> str:
        """Substitute `{param}` placeholders in the endpoint template with
        `path_params`, e.g. `/api/users/{id}` + `{"id": 2}` -> `/api/users/2`.
        """
        try:
            return self.endpoint.format(**self.path_params)
        except KeyError as exc:
            raise ValueError(
                f"Missing path parameter {exc} for endpoint template '{self.endpoint}'"
            ) from exc
