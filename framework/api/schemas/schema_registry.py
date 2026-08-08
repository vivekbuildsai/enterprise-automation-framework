from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from framework.api.exceptions import ApiSchemaValidationError
from framework.exceptions import ConfigurationError

_SCHEMAS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _registry() -> Registry:
    """One `referencing.Registry` covering every `*.json` file in this
    directory, so a schema can `$ref` a sibling schema by filename (see
    `user_list_schema.json` -> `user_schema.json`) without each caller
    having to know about that relationship.
    """
    resources = []
    for schema_path in _SCHEMAS_DIR.glob("*.json"):
        contents = json.loads(schema_path.read_text(encoding="utf-8"))
        resources.append(
            (schema_path.name, Resource.from_contents(contents, default_specification=DRAFT7))
        )
    return Registry().with_resources(resources)


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load `<name>.json` (or `<name>` if already suffixed) from this
    directory. Schemas are stored as plain files, not Python code, so a
    non-engineer can review/update the contract without reading Python.
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    schema_path = _SCHEMAS_DIR / filename
    if not schema_path.exists():
        raise ConfigurationError(f"No JSON schema named '{filename}' in {_SCHEMAS_DIR}")
    return json.loads(schema_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def validate_against_schema(instance: Any, schema_name: str) -> None:
    """Validate `instance` (already-parsed JSON — typically `response.json()`)
    against a named schema, raising `ApiSchemaValidationError` with the
    concrete failure (which field, why) rather than a generic assertion.
    """
    schema = load_schema(schema_name)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema, registry=_registry())

    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise ApiSchemaValidationError(f"Response failed schema '{schema_name}': {details}")
