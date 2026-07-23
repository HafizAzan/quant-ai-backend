from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.risk_agent import RiskAgent
from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.exchange import (
    ExchangeAccountOut,
    ExchangeConnectRequest,
    ExchangeSyncOut,
    PlaceOrderOut,
    PlaceOrderRequest,
)
from app.services.exchange_service import ExchangeService

router = APIRouter(prefix="/exchange", tags=["Exchange"])


def get_exchange_service(session: AsyncSession = Depends(get_db)) -> ExchangeService:
    return ExchangeService(session)


@router.get("/accounts", response_model=APIResponse[list[ExchangeAccountOut]])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    service: ExchangeService = Depends(get_exchange_service),
) -> APIResponse[list[ExchangeAccountOut]]:
    return APIResponse(data=await service.list_accounts(current_user.id))


@router.post("/connect", response_model=APIResponse[ExchangeAccountOut])
async def connect_exchange(
    payload: ExchangeConnectRequest,
    current_user: User = Depends(get_current_user),
    service: ExchangeService = Depends(get_exchange_service),
) -> APIResponse[ExchangeAccountOut]:
    return APIResponse(message="Exchange connected", data=await service.connect(current_user.id, payload))


@router.post("/accounts/{account_id}/disconnect", response_model=APIResponse[None])
async def disconnect_exchange(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ExchangeService = Depends(get_exchange_service),
) -> APIResponse[None]:
    await service.disconnect(current_user.id, account_id)
    return APIResponse(message="Exchange disconnected", data=None)


@router.post("/sync", response_model=APIResponse[ExchangeSyncOut])
async def sync_balances(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ExchangeService = Depends(get_exchange_service),
) -> APIResponse[ExchangeSyncOut]:
    return APIResponse(data=await service.sync(current_user.id, account_id))


@router.post("/orders", response_model=APIResponse[PlaceOrderOut])
async def place_order(
    payload: PlaceOrderRequest,
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ExchangeService = Depends(get_exchange_service),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PlaceOrderOut]:
    # Rough notional for risk (price unknown → quantity * 100 placeholder when needed)
    notional = payload.quantity * (payload.price or 100.0)
    risk = await RiskAgent(session).check_order(current_user.id, notional_usd=notional, leverage=1)
    if not risk.allowed:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"blockers": risk.blockers})
    data = await service.place_order(current_user.id, payload, account_id)
    return APIResponse(message="Order submitted", data=data)
