# Request Builder

`framework/api/builders/request_builder.py` — a fluent builder that produces
a `RequestSpec` (plain data), which `ApiClient` executes. Every method
returns `self`, so a request reads as one chain.

## Basic usage

```python
from framework.api.builders import RequestBuilder

spec = (
    RequestBuilder("POST", "/users/{id}")
    .path_param("id", 7)
    .query_param("verbose", "1")
    .header("X-Test-Run", run_id)
    .json_body({"firstName": "Ada"})
    .build()
)
```

In practice you rarely build a `RequestSpec` by hand — `ApiClient.get/post/
put/patch/delete/head/options(endpoint, path_params=..., query_params=...,
headers=..., json=...)` builds one internally via `RequestBuilder` for you.
Reach for `RequestBuilder` directly (via `ApiClient.request(builder)`) when
you need something the convenience methods can't express: multipart,
file upload, XML, or form-encoded bodies.

## Path and query parameters

```python
RequestBuilder("GET", "/users/{id}").path_param("id", 2)     # -> /users/2
RequestBuilder("GET", "/users").query_params({"limit": 5, "skip": 10})
```

A missing path parameter raises a clear `ValueError` naming the missing key
(`RequestSpec.resolved_path()`) rather than a confusing `KeyError` from
`str.format`.

## Headers

```python
RequestBuilder("GET", "/x").header("X-Trace", "abc").headers({"Accept": "application/json"})
```

## Body — exactly one type per request

`.json_body()`, `.xml_body()`, `.form_data()`, and `.multipart()`/`.file_upload()`
are mutually exclusive — calling a second one raises `ConfigurationError`
naming which body type was already set. This catches an easy mistake (e.g.
copy-pasting a JSON test and forgetting to remove a leftover `.form_data()`
call) at request-build time instead of producing a confusing wire-format bug.

```python
RequestBuilder("POST", "/login").json_body({"username": "ada", "password": "x"})
# .json_body() also accepts a Pydantic model directly:
RequestBuilder("POST", "/login").json_body(LoginRequest(username="ada", password="x"))

RequestBuilder("POST", "/legacy").xml_body("<login><user>ada</user></login>")

RequestBuilder("POST", "/legacy-form").form_data({"username": "ada"})

RequestBuilder("POST", "/upload").multipart({"file": ("report.csv", b"a,b\n1,2\n")})
RequestBuilder("POST", "/upload").file_upload("file", "/path/to/report.csv")
```

`.file_upload()` is a convenience over `.multipart()` for the common case of
uploading a real file from disk — it reads the bytes and infers the filename.

## Building and executing

```python
response = api_client.request(
    RequestBuilder("POST", "/upload").file_upload("file", path)
)
```

`.build()` returns the `RequestSpec`; you rarely call it directly — `ApiClient.request()`
calls it for you.
