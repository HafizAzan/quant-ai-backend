from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageBlockOut(BaseModel):
    type: str
    text: str | None = None
    columns: list[dict[str, str]] | None = None
    rows: list[dict[str, Any]] | None = None
    trend_key: str | None = None
    language: str | None = None
    code: str | None = None
    ordered: bool | None = None
    items: list[str] | None = None
    tone: str | None = None
    label: str | None = None
    src: str | None = None


class MessageSectionOut(BaseModel):
    id: str
    title: str
    default_open: bool = True
    blocks: list[dict[str, Any]] = Field(default_factory=list)


class CommandIntentOut(BaseModel):
    command_id: str
    kind: str
    module: str
    href: str
    label: str
    raw: str
    confidence: float
    params: dict[str, Any] = Field(default_factory=dict)


class CommandExecutionResultOut(BaseModel):
    intent: CommandIntentOut
    status: str = "ready"
    summary: str
    cta_label: str
    cta_href: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str | None = None
    image_label: str | None = None
    sections: list[dict[str, Any]] | None = None
    blocks: list[dict[str, Any]] | None = None
    command_result: CommandExecutionResultOut | None = None
    stream_status: str = "complete"
    created_at: datetime


class ChatThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    preview: str
    symbol: str | None = None
    bias: str
    confidence: int
    engine: str
    tokens_used: int
    tokens_limit: int
    timestamp: str
    created_at: datetime
    updated_at: datetime


class ChatThreadDetailOut(ChatThreadOut):
    messages: list[ChatMessageOut] = Field(default_factory=list)


class ChatThreadListOut(BaseModel):
    items: list[ChatThreadOut]
    total: int


class CreateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    symbol: str | None = Field(default=None, max_length=32)


class UpdateThreadRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)
    image_label: str | None = Field(default=None, max_length=255)
    symbol: str | None = Field(default=None, max_length=32)


class SendMessageOut(BaseModel):
    thread: ChatThreadOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut


class PlatformCommandOut(BaseModel):
    id: str
    label: str
    description: str
    kind: str
    module: str
    href: str
    examples: list[str]
    keywords: list[str]
    param_keys: list[str] = Field(default_factory=list)
    slash: str | None = None


class CommandsListOut(BaseModel):
    items: list[PlatformCommandOut]
    prompts: list[str]


class ResolveCommandRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class ResolveCommandOut(BaseModel):
    matched: bool
    result: CommandExecutionResultOut | None = None
    suggestions: list[PlatformCommandOut] = Field(default_factory=list)


class ChatWorkspaceOut(BaseModel):
    engine: str
    tokens_used: int
    tokens_limit: int
    suggested_prompts: list[str]
    empty_state_prompts: list[str]
    response_actions: list[dict[str, str]]
    quick_actions: list[dict[str, str]]
    symbol_options: list[dict[str, str]]
    market_cap: dict[str, Any]
    fear_greed: dict[str, Any]
    realtime_signals: list[dict[str, Any]]
    pro_analysis: dict[str, str]
    commands: list[PlatformCommandOut]
