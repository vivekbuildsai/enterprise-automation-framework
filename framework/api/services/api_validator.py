from __future__ import annotations

from framework.api.client import ApiClient
from framework.api.endpoints import Endpoints
from framework.api.models import LoginRequest, LoginResponse, User
from framework.api.validators import ResponseValidator


class ApiValidator:
    """The API-side half of hybrid (UI+API) validation.

    This is the piece a UI test would call *after* driving the browser, to
    cross-check that what the UI shows is backed by real state on the
    server — not just what the DOM happened to render:

        login_page.login(user)                       # UI action
        api_validator.verify_login(user.username, user.password)  # API cross-check
        dashboard.verify_homepage()                   # UI assertion

    Wiring this into UI test fixtures (a combined `hybrid_context` fixture
    exposing both `page` and `api_validator`, gated by `ValidationMode`) is
    intentionally **not done yet** — see `docs/APIFramework.md` "Hybrid
    validation" section for the planned fixture shape. This class only
    proves the API-facing contract is real and independently testable.

    Deliberately calls `ApiClient` directly rather than going through
    `AuthService`/`UserService`: those parse every response straight into
    their success-shape Pydantic model, so an error response (a 404, an
    invalid-login 400) would fail with a confusing "field required"
    validation error instead of the actual status-code mismatch this class
    exists to catch. Status is asserted *before* parsing here.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def verify_login(self, username: str, password: str) -> LoginResponse:
        """Re-authenticate via the API and assert it succeeds — confirms the
        credentials a UI login just used are valid at the source of truth,
        not just accepted by whatever the UI happened to check client-side.
        """
        request = LoginRequest(username=username, password=password)
        response = self._client.post(Endpoints.LOGIN, json=request.model_dump())
        ResponseValidator(response).expect_status(200)
        return LoginResponse.model_validate(response.json())

    def verify_user_exists(self, user_id: int) -> User:
        """Confirms a user the UI displays actually exists server-side with
        a 200 (as opposed to the UI rendering stale/cached/mocked data).
        """
        response = self._client.get(Endpoints.USER_BY_ID, path_params={"id": user_id})
        ResponseValidator(response).expect_status(200)
        return User.model_validate(response.json())

    def verify_user_field(self, user_id: int, field_path: str, expected: object) -> User:
        """Confirms one field of a user record matches `expected` at the API
        layer — the building block for "does the UI's displayed value match
        the backend's value" checks.
        """
        response = self._client.get(Endpoints.USER_BY_ID, path_params={"id": user_id})
        ResponseValidator(response).expect_status(200).expect_json_field(field_path, expected)
        return User.model_validate(response.json())
