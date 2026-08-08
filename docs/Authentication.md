# Authentication

All strategies live in `framework/api/auth/` and are `httpx.Auth` subclasses
— that's the entire plug-in contract. Pass one to `ApiClient(auth=...)` for
every request on that client, or to an individual `httpx` call for a
one-off override. Nothing in `ApiClient` branches on which strategy is in
use; the extension point *is* the type system (`httpx.Auth`).

## Strategies

| Class | Use when | Notes |
|---|---|---|
| `NoAuth` | Public endpoints | Explicit no-op, not a `None` special case |
| `BearerTokenAuth(token)` | You already have a static/short-lived token | e.g. from a prior login call |
| `JwtAuth(access_token, refresh_token=callable)` | Token can expire mid-suite | Retries once on 401 by calling `refresh_token()` for a new token |
| `BasicAuthStrategy(username, password)` | RFC 7617 Basic auth | Thin wrapper over `httpx.BasicAuth` |
| `ApiKeyAuth(key, key_name=..., location="header"\|"query")` | Provider uses a static API key | Header by default; some providers require a query param |
| `CookieAuth(name, value)` | Session-cookie-based auth | Sets `Cookie` directly — not for CSRF-token flows |
| `OAuth2ClientCredentialsAuth(token_url, client_id, client_secret, scope=None)` | Machine-to-machine (RFC 6749 §4.4) | Fetches + caches a token, auto-refreshes ~30s before expiry |
| `OAuth2AuthorizationCodeAuth(token_url, client_id, client_secret, redirect_uri, authorization_code)` | User-delegated auth (RFC 6749 §4.1) | Exchanges a code you already obtained for a token; refreshes via `refresh_token` grant if the provider issues one |

## `AuthFactory` — config-driven auth

For the strategies fully determined by static config, `AuthFactory.from_config(config)`
builds the right one from an `ApiEndpointConfig` (`config/environments/*.yaml`):

```yaml
api:
  my_service:
    base_url: "https://api.example.com"
    auth_type: oauth2          # none | basic | api_key | oauth2
    token_url: "https://idp.example.com/token"
    client_id: "${MY_CLIENT_ID:-}"
    client_secret: "${MY_CLIENT_SECRET:-}"
```

```python
config = settings.api["my_service"]
auth = AuthFactory.from_config(config)
client = ApiClient(str(config.base_url), auth=auth)
```

`bearer`, `jwt`, and `oauth2_authorization_code` are **not** buildable by
`AuthFactory` — they need a token/code obtained at runtime (a login call, a
user-consent redirect), so construct them directly once you have that:

```python
login = auth_service.login(username, password)
authed_client = ApiClient(base_url, auth=BearerTokenAuth(login.access_token))
```

`mtls` is accepted as an `auth_type` value but raises from `AuthFactory` —
client certificates are a transport-level concern (configured on the
`httpx.Client`/`ApiClient` itself), not something an `Auth` strategy
expresses.

## Secrets

Never hardcode a token/secret in test code or YAML. Environment YAML files
use `${VAR:-default}` placeholders resolved from `.env`/process environment
at load time (see `framework/config/settings.py`); the same pattern the UI
layer uses for `ui.login_username`/`ui.login_password`.

## Writing a new strategy

Subclass `httpx.Auth` and implement `auth_flow(request)` as a generator:

```python
class MyAuth(httpx.Auth):
    def auth_flow(self, request: httpx.Request):
        request.headers["X-My-Auth"] = self._token
        response = yield request
        if response.status_code == 401:
            # inspect response, refresh, yield request again if you want a retry
            ...
```

Yielding once sends one request; yielding again after inspecting the
`response` you get back retries with the modified request (this is how
`JwtAuth`'s refresh-on-401 works).
