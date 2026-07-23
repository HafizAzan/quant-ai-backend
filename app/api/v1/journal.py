from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.journal import (
    CreateJournalEntryRequest,
    JournalDeskOut,
    JournalEntryOut,
    JournalListOut,
    UpdateJournalEntryRequest,
)
from app.services.journal_service import JournalService

router = APIRouter(prefix="/journal", tags=["Journal"])


def get_journal_service(session: AsyncSession = Depends(get_db)) -> JournalService:
    return JournalService(session)


@router.get("/desk", response_model=APIResponse[JournalDeskOut])
async def get_journal_desk(
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[JournalDeskOut]:
    data = await service.get_desk(current_user.id)
    return APIResponse(data=data)


@router.get("", response_model=APIResponse[JournalListOut])
async def list_journal_entries(
    date_range: str = Query(default="30d", pattern="^(7d|30d|90d|all)$"),
    asset: str | None = Query(default=None, max_length=32),
    strategy: str | None = Query(default=None, max_length=32),
    outcome: str | None = Query(default=None, pattern="^(all|win|loss|breakeven)$"),
    query: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[JournalListOut]:
    data = await service.list_entries(
        current_user.id,
        date_range=date_range,
        asset=asset,
        strategy=strategy,
        outcome=outcome,
        query=query,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=data)


@router.post("", response_model=APIResponse[JournalEntryOut])
async def create_journal_entry(
    payload: CreateJournalEntryRequest,
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[JournalEntryOut]:
    data = await service.create_entry(current_user.id, payload)
    return APIResponse(message="Journal entry created", data=data)


@router.get("/{entry_id}", response_model=APIResponse[JournalEntryOut])
async def get_journal_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[JournalEntryOut]:
    data = await service.get_entry(current_user.id, entry_id)
    return APIResponse(data=data)


@router.patch("/{entry_id}", response_model=APIResponse[JournalEntryOut])
async def update_journal_entry(
    entry_id: UUID,
    payload: UpdateJournalEntryRequest,
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[JournalEntryOut]:
    data = await service.update_entry(current_user.id, entry_id, payload)
    return APIResponse(message="Journal entry updated", data=data)


@router.delete("/{entry_id}", response_model=APIResponse[None])
async def delete_journal_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> APIResponse[None]:
    await service.delete_entry(current_user.id, entry_id)
    return APIResponse(message="Journal entry deleted", data=None)
