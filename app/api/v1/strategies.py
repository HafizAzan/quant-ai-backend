from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.strategy import (
    AiAssistOut,
    AiAssistRequest,
    BacktestRunOut,
    CreateStrategyRequest,
    GenerateStrategyOut,
    GenerateStrategyRequest,
    RunBacktestRequest,
    SaveCanvasRequest,
    StrategiesWorkspaceOut,
    StrategyDetailOut,
    StrategyListOut,
    StrategyOut,
    UpdateStrategyRequest,
)
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategies", tags=["Strategies"])


def get_strategy_service(session: AsyncSession = Depends(get_db)) -> StrategyService:
    return StrategyService(session)


@router.get("/workspace", response_model=APIResponse[StrategiesWorkspaceOut])
async def get_strategies_workspace(
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategiesWorkspaceOut]:
    _ = current_user
    return APIResponse(data=service.get_workspace())


@router.get("", response_model=APIResponse[StrategyListOut])
async def list_strategies(
    query: str | None = Query(default=None, max_length=120),
    market: str | None = Query(default=None, max_length=32),
    exchange: str | None = Query(default=None, max_length=64),
    type: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=16),
    risk: str | None = Query(default=None, max_length=16),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyListOut]:
    data = await service.list_strategies(
        current_user.id,
        query=query,
        market=market,
        exchange=exchange,
        strategy_type=type,
        status=status,
        risk=risk,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=data)


@router.post("", response_model=APIResponse[StrategyDetailOut])
async def create_strategy(
    payload: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.create_strategy(current_user.id, payload)
    return APIResponse(message="Strategy created", data=data)


@router.post("/generate", response_model=APIResponse[GenerateStrategyOut])
async def generate_strategy(
    payload: GenerateStrategyRequest,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[GenerateStrategyOut]:
    data = await service.generate(current_user.id, payload)
    return APIResponse(message="Strategy generated", data=data)


@router.get("/{strategy_id}", response_model=APIResponse[StrategyDetailOut])
async def get_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.get_strategy(current_user.id, strategy_id)
    return APIResponse(data=data)


@router.patch("/{strategy_id}", response_model=APIResponse[StrategyDetailOut])
async def update_strategy(
    strategy_id: UUID,
    payload: UpdateStrategyRequest,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.update_strategy(current_user.id, strategy_id, payload)
    return APIResponse(message="Strategy updated", data=data)


@router.put("/{strategy_id}/canvas", response_model=APIResponse[StrategyDetailOut])
async def save_canvas(
    strategy_id: UUID,
    payload: SaveCanvasRequest,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.save_canvas(current_user.id, strategy_id, payload)
    return APIResponse(message="Canvas saved", data=data)


@router.post("/{strategy_id}/duplicate", response_model=APIResponse[StrategyDetailOut])
async def duplicate_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.duplicate(current_user.id, strategy_id)
    return APIResponse(message="Strategy duplicated", data=data)


@router.post("/{strategy_id}/archive", response_model=APIResponse[StrategyOut])
async def archive_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyOut]:
    data = await service.archive(current_user.id, strategy_id)
    return APIResponse(message="Strategy archived", data=data)


@router.post("/{strategy_id}/deploy", response_model=APIResponse[StrategyDetailOut])
async def deploy_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[StrategyDetailOut]:
    data = await service.deploy(current_user.id, strategy_id)
    return APIResponse(message="Strategy deployed", data=data)


@router.post("/{strategy_id}/backtest", response_model=APIResponse[BacktestRunOut])
async def run_backtest(
    strategy_id: UUID,
    payload: RunBacktestRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[BacktestRunOut]:
    data = await service.run_backtest(current_user.id, strategy_id, payload or RunBacktestRequest())
    return APIResponse(message="Backtest completed", data=data)


@router.get("/{strategy_id}/backtests", response_model=APIResponse[list[BacktestRunOut]])
async def list_backtests(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[list[BacktestRunOut]]:
    data = await service.list_backtests(current_user.id, strategy_id)
    return APIResponse(data=data)


@router.post("/{strategy_id}/ai-assist", response_model=APIResponse[AiAssistOut])
async def ai_assist(
    strategy_id: UUID,
    payload: AiAssistRequest,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[AiAssistOut]:
    data = await service.ai_assist(current_user.id, strategy_id, payload)
    return APIResponse(data=data)


@router.delete("/{strategy_id}", response_model=APIResponse[None])
async def delete_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> APIResponse[None]:
    await service.delete_strategy(current_user.id, strategy_id)
    return APIResponse(message="Strategy deleted", data=None)
