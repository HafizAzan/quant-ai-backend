from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatThreadDetailOut,
    ChatThreadListOut,
    ChatThreadOut,
    ChatWorkspaceOut,
    CommandsListOut,
    CreateThreadRequest,
    ResolveCommandOut,
    ResolveCommandRequest,
    SendMessageOut,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.schemas.common import APIResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["AI Chat"])
commands_router = APIRouter(prefix="/commands", tags=["Commands"])


def get_chat_service(session: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(session)


@router.get("/workspace", response_model=APIResponse[ChatWorkspaceOut])
async def get_chat_workspace(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatWorkspaceOut]:
    _ = current_user
    return APIResponse(data=service.get_workspace())


@router.get("/threads", response_model=APIResponse[ChatThreadListOut])
async def list_threads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatThreadListOut]:
    data = await service.list_threads(current_user.id, page=page, page_size=page_size)
    return APIResponse(data=data)


@router.post("/threads", response_model=APIResponse[ChatThreadDetailOut])
async def create_thread(
    payload: CreateThreadRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatThreadDetailOut]:
    data = await service.create_thread(current_user.id, payload or CreateThreadRequest())
    return APIResponse(message="Chat created", data=data)


@router.get("/threads/{thread_id}", response_model=APIResponse[ChatThreadDetailOut])
async def get_thread(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatThreadDetailOut]:
    data = await service.get_thread(current_user.id, thread_id)
    return APIResponse(data=data)


@router.patch("/threads/{thread_id}", response_model=APIResponse[ChatThreadOut])
async def update_thread(
    thread_id: UUID,
    payload: UpdateThreadRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatThreadOut]:
    data = await service.update_thread(current_user.id, thread_id, payload)
    return APIResponse(message="Chat updated", data=data)


@router.delete("/threads/{thread_id}", response_model=APIResponse[None])
async def delete_thread(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[None]:
    await service.delete_thread(current_user.id, thread_id)
    return APIResponse(message="Chat deleted", data=None)


@router.post("/threads/{thread_id}/messages", response_model=APIResponse[SendMessageOut])
async def send_message(
    thread_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[SendMessageOut]:
    data = await service.send_message(current_user.id, thread_id, payload)
    return APIResponse(message="Message sent", data=data)


@commands_router.get("", response_model=APIResponse[CommandsListOut])
async def list_commands(
    q: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[CommandsListOut]:
    _ = current_user
    return APIResponse(data=service.list_commands(q))


@commands_router.post("/resolve", response_model=APIResponse[ResolveCommandOut])
async def resolve_command(
    payload: ResolveCommandRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ResolveCommandOut]:
    _ = current_user
    return APIResponse(data=service.resolve_command(payload.query))


@commands_router.get("/resolve", response_model=APIResponse[ResolveCommandOut])
async def resolve_command_get(
    query: str = Query(..., min_length=1, max_length=2000),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> APIResponse[ResolveCommandOut]:
    _ = current_user
    return APIResponse(data=service.resolve_command(query))
