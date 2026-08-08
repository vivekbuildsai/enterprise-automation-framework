# Response Validators

`framework.api.validators.ResponseValidator` — fluent, chainable assertions
over an `httpx.Response` (the API-layer equivalent of `Assert`/`SoftAssert`
for the UI layer). Every `expect_*` method returns `self` and raises
immediately on failure — there's intentionally no soft-fail mode, because a
malformed API response usually makes every subsequent check meaningless
(e.g. asserting field values on a 500 error body).

```python
from framework.api.validators import ResponseValidator

(
    ResponseValidator(response)
    .expect_status(200)
    .expect_header("Content-Type", "application/json; charset=utf-8")
    .expect_response_time_under(2000)
    .expect_json_field("username", "emilys")
    .expect_schema("user_schema")
)
```

## Status code

```python
.expect_status(200)              # exact
.expect_status({200, 201})       # any of a set — useful when a provider's
                                  # exact success code is inconsistent
```

## Headers and cookies

```python
.expect_header("X-Request-Id")                 # presence only
.expect_header("Content-Type", "application/json")  # presence + value
.expect_cookie("session")
.expect_cookie("session", "abc123")
```

## Response time

```python
.expect_response_time_under(2000)  # milliseconds
```

If the response's timing genuinely isn't available (e.g. a response built
directly by an `httpx.MockTransport` handler in an offline unit test — there
was no real I/O to time), this check is **skipped** rather than raised or
crashed on; there's nothing meaningful to assert against a mocked response.

## JSON fields — including nested and collections

Dotted/indexed path syntax (`a.b.c`, `a.0.b`, or `a[0].b` — both index
styles work):

```python
.expect_json_field("username", "emilys")
.expect_json_field("address.city", "London")
.expect_json_field("users.0.id", 1)
.expect_json_field_present("accessToken")   # just checks it exists
```

A missing field raises with the exact path and reason (`"Field 'user.email'
not found in response (path='user.email')"`), not a raw `KeyError` traceback.

## Collections

```python
.expect_collection_size("users", exact=5)
.expect_collection_size("users", min_size=1, max_size=100)
```

## Schema validation

```python
.expect_schema("user_schema")   # validates response.json() against
                                 # framework/api/schemas/user_schema.json
```

See [Schemas.md](Schemas.md) for how schemas are stored and resolved.

## Escape hatch

```python
body = ResponseValidator(response).json()   # the raw parsed body, for
                                             # assertions this class doesn't cover
```

## Exceptions

| Raised by | Exception |
|---|---|
| Any `expect_*` failure (status/header/cookie/time/field/collection) | `ApiResponseValidationError` |
| `expect_schema` failure | `ApiSchemaValidationError` |

Both derive from the framework-wide `ValidationError`, so code that only
cares "did validation fail" can catch one type.
