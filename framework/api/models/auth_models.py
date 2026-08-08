from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow"
    )  # provider may add fields over time; we only pin what we assert on

    id: int
    username: str
    email: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
