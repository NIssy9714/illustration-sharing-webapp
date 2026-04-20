from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: int
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=1000)
    filename: str | None = Field(default=None, max_length=255)


class PostPublic(BaseModel):
    id: int
    user_id: int
    title: str
    body: str | None
    filename: str | None
    created_at: datetime

