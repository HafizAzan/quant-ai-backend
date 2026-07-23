from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchItemOut(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    category: str
    kind: str
    href: str
    keywords: list[str] = Field(default_factory=list)
    symbol: str | None = None
    icon: str | None = None
    actions: list[str] = Field(default_factory=list)
    boost: float = 0
    is_command: bool = False
    score: float = 0


class SearchResultsOut(BaseModel):
    query: str
    items: list[SearchItemOut]
    suggestions: list["SearchSuggestionOut"] = Field(default_factory=list)


class SearchSuggestionOut(BaseModel):
    id: str
    label: str
    description: str | None = None
    query: str | None = None
    href: str | None = None
    kind: str  # ai|recent|frequent|pinned|command


class SearchRecentOut(BaseModel):
    id: UUID
    query: str
    item_id: str | None = None
    title: str
    href: str | None = None
    at: datetime


class SearchRecentCreateRequest(BaseModel):
    query: str = Field(default="", max_length=255)
    item_id: str | None = Field(default=None, max_length=120)
    title: str = Field(..., min_length=1, max_length=255)
    href: str | None = Field(default=None, max_length=255)


class SearchPinOut(BaseModel):
    id: UUID
    item_id: str
    title: str
    href: str | None = None
    sort_order: int


class SearchPinCreateRequest(BaseModel):
    item_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=255)
    href: str | None = Field(default=None, max_length=255)
