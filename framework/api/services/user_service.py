from __future__ import annotations

import httpx

from framework.api.client import ApiClient
from framework.api.endpoints import Endpoints
from framework.api.models import (
    CreateUserRequest,
    DeleteUserResponse,
    UpdateUserRequest,
    User,
    UserListResponse,
)


class UserService:
    """Domain facade over `ApiClient` for user CRUD. Same `last_response`
    convention as `AuthService` — see its docstring.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self.last_response: httpx.Response | None = None

    def list_users(self, *, limit: int | None = None, skip: int | None = None) -> UserListResponse:
        query_params = {k: v for k, v in {"limit": limit, "skip": skip}.items() if v is not None}
        self.last_response = self._client.get(Endpoints.USERS, query_params=query_params)
        return UserListResponse.model_validate(self.last_response.json())

    def get_user(self, user_id: int) -> User:
        self.last_response = self._client.get(Endpoints.USER_BY_ID, path_params={"id": user_id})
        return User.model_validate(self.last_response.json())

    def create_user(self, request: CreateUserRequest) -> User:
        self.last_response = self._client.post(
            Endpoints.USER_ADD, json=request.model_dump(by_alias=True)
        )
        return User.model_validate(self.last_response.json())

    def update_user(self, user_id: int, request: UpdateUserRequest) -> User:
        self.last_response = self._client.put(
            Endpoints.USER_BY_ID,
            path_params={"id": user_id},
            json=request.model_dump(by_alias=True, exclude_none=True),
        )
        return User.model_validate(self.last_response.json())

    def delete_user(self, user_id: int) -> DeleteUserResponse:
        self.last_response = self._client.delete(Endpoints.USER_BY_ID, path_params={"id": user_id})
        return DeleteUserResponse.model_validate(self.last_response.json())
