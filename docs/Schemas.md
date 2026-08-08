# JSON Schema Validation

Schemas are stored as plain `.json` files under `framework/api/schemas/`,
not as Python code — a non-engineer can review or update a contract without
reading Python, and a schema diff in a PR is a readable JSON diff.

## Layout

```
framework/api/schemas/
├── schema_registry.py         # load_schema() / validate_against_schema()
├── login_response_schema.json
├── user_schema.json
└── user_list_schema.json      # $refs user_schema.json
```

## Writing a schema

Standard [JSON Schema Draft 7](https://json-schema.org/draft-07). Pin the
fields you actually assert on with `required`/`type`; leave
`"additionalProperties": true` unless you specifically want to catch a
provider adding/removing fields — most providers add fields over time, and a
schema that rejects unknown fields breaks the suite on every such addition.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "User",
  "type": "object",
  "required": ["id"],
  "properties": {
    "id": { "type": "integer" },
    "email": { "type": "string" }
  },
  "additionalProperties": true
}
```

## Cross-file references

A schema can `$ref` another file in the same directory by filename — used
by `user_list_schema.json` to reuse `user_schema.json` for each item in its
`users` array:

```json
"items": { "$ref": "user_schema.json" }
```

This works via a `referencing.Registry` built once (and cached) from every
`*.json` file in `framework/api/schemas/` — you don't need to register a new
schema file anywhere; dropping it in the directory is enough.

## Using a schema

Directly:

```python
from framework.api.schemas import validate_against_schema

validate_against_schema(response.json(), "user_schema")
```

Or via `ResponseValidator` (the usual way, so it chains with the rest of a
request's assertions):

```python
ResponseValidator(response).expect_status(200).expect_schema("user_schema")
```

A validation failure raises `ApiSchemaValidationError` naming every failing
field and why (not just the first one):

```
Response failed schema 'user_schema': id: 'id' is a required property
```

## Loading a schema without validating

```python
from framework.api.schemas import load_schema

schema = load_schema("user_schema")          # or "user_schema.json" — either works
```

Raises `ConfigurationError` (not a bare `FileNotFoundError`) if the name
doesn't match a file in the schemas directory.
