# API Framework

`framework/api/` is an independent, reusable module for API automation. It
does not depend on the UI layer (`framework/pages`, `framework/drivers`) in
either direction — a pure-API test suite works with zero Playwright installed,
and vice versa. See [Architecture.md](Architecture.md) for how this fits into
the platform as a whole.

## Layers

```
framework/api/
├── client/       ApiClient — the only thing that talks to httpx.Client
├── auth/         Pluggable httpx.Auth strategies + AuthFactory
├── builders/     RequestBuilder (fluent) -> RequestSpec (plain data)
├── validators/   ResponseValidator (fluent) + JSON path resolver
├── schemas/      *.json schema files + SchemaRegistry loader
├── endpoints/    Endpoints — centralized path templates, no hardcoded URLs
├── models/       Pydantic request/response models
├── services/     Domain facades (AuthService, UserService, ApiValidator)
├── middleware/   httpx event hooks: correlation ID, logging, Allure
├── utilities/    Small cross-cutting helpers (e.g. elapsed-time safety)
├── exceptions/   API-specific exception hierarchy
├── fixtures/     pytest fixtures wiring config -> ApiClient -> services
└── constants/    Header names, content types, retry policy, timeouts
```

Dependency direction: `services` depends on `client` + `models` + `endpoints`
+ `validators`; `client` depends on `auth` + `builders` + `middleware`; none
of them depend on `services`. Tests call `services` (or `client` directly for
ad-hoc/negative cases) — they never import `httpx` themselves.

## Request lifecycle

```
RequestBuilder          ApiClient                    httpx.Client
  .header(...)             .get/post/put/...            event_hooks:
  .json_body(...)    -->   ._send() -> RequestSpec  -->    request:  [correlation, log, allure]
  .build()                 ._execute()                     response: [log, allure]
                              - safe method? retry via tenacity
                              - unsafe method? single attempt
                            ._dispatch() -> httpx.Response
```

A retryable failure (transient connection/timeout error, or a response with
status in `RetryPolicy.RETRYABLE_STATUS_CODES`) is retried with exponential
backoff **only** for methods in `RetryPolicy.SAFE_METHODS` (GET, HEAD,
OPTIONS, PUT, DELETE) — POST/PATCH are never auto-retried, since retrying a
non-idempotent call could duplicate a side effect. If retries are exhausted:
a transient exception becomes `ApiConnectionError`/`ApiTimeoutError`; a
persistently-bad status code is returned as the response as-is (not raised),
so `ResponseValidator` can assert on it like any other response.

## Sample slice

The framework is proven end-to-end against **dummyjson.com** — a public,
no-signup test API with real JWT-based login and working user CRUD.
(`reqres.in`, the more commonly used public test API, now requires a paid
signup API key for every endpoint; we don't have one, so it wasn't usable
here.) `Endpoints`/`AuthService`/`UserService`/the schemas and models are all
scoped to this sample domain — swap in your own application's real service
endpoints by adding new `Endpoints`/model/service classes following the
same shape.

## Hybrid validation (UI + API) — architecture, not wired up yet

`ApiValidator` (`framework/api/services/api_validator.py`) is the API-facing
half of the pattern a future UI test would use:

```python
login_page.login(user)                                     # UI action
api_validator.verify_login(user.username, user.password)    # API cross-check
dashboard.verify_homepage()                                  # UI assertion
```

`ApiValidator` is fully implemented and tested today — it composes
`ApiClient` + `ResponseValidator` + the Pydantic models to answer "is this
true according to the backend, not just the DOM". What's **not** built yet:
a combined UI+API pytest fixture (e.g. `hybrid_context`) that exposes both
`page` and `api_validator` together, gated by `ValidationMode` from
`framework.enums.validation_mode` (already defined in Milestone 1). Building
that fixture, and having `BaseTest`/UI test suites actually call it, is
Milestone 3+ work — see [FutureRoadmap.md](FutureRoadmap.md).

## See also

- [Authentication.md](Authentication.md) — every auth strategy, when to use which
- [RequestBuilder.md](RequestBuilder.md) — building requests (JSON/XML/form/multipart)
- [Validators.md](Validators.md) — response assertions
- [Schemas.md](Schemas.md) — JSON Schema validation and the schema registry
- [ExecutionGuide.md](ExecutionGuide.md) — running the API suites locally/CI/Docker
