from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Response model for a user record. `extra="allow"` because the sample
    provider (dummyjson.com) returns dozens of fields (address, bank,
    company, ...) we have no business asserting on — pinning only the ones
    this framework actually validates keeps the model resilient to the
    provider adding fields, while still catching a regression in the ones
    that matter.
    """

    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str = Field(default="", alias="firstName")
    last_name: str = Field(default="", alias="lastName")
    # dummyjson returns `null` (not "") for an unset email on a freshly
    # created user, so this has to tolerate None even though most reads
    # give back a real string.
    email: str | None = ""
    username: str = ""
    age: int | None = None
    gender: str = ""


class UserListResponse(BaseModel):
    users: list[User]
    total: int
    skip: int
    limit: int


class CreateUserRequest(BaseModel):
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    age: int | None = None
    email: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class UpdateUserRequest(BaseModel):
    """All fields optional — a PATCH-style partial update. `exclude_none`
    when serializing (see `UserService.update_user`) so unset fields aren't
    sent as explicit `null`s.
    """

    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    age: int | None = None

    model_config = ConfigDict(populate_by_name=True)


class DeleteUserResponse(User):
    is_deleted: bool = Field(default=False, alias="isDeleted")
    deleted_on: str = Field(default="", alias="deletedOn")
