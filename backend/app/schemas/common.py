"""Shared pydantic schemas (pagination envelope, messages)."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.pagination import Page

T = TypeVar("T")


class PageOut(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    page: Page = Field(description="pagination metadata")


class MessageOut(BaseModel):
    detail: str
