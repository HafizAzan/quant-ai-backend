from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.strategy import BacktestRun, Strategy, StrategyEdge, StrategyNode


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, obj: object) -> None:
        await self.session.delete(obj)

    async def get(self, user_id: UUID, strategy_id: UUID) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy)
            .options(
                selectinload(Strategy.nodes),
                selectinload(Strategy.edges),
                selectinload(Strategy.backtests),
            )
            .where(Strategy.id == strategy_id, Strategy.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_strategies(
        self,
        user_id: UUID,
        *,
        query: str | None = None,
        market: str | None = None,
        exchange: str | None = None,
        strategy_type: str | None = None,
        status: str | None = None,
        risk: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Strategy], int]:
        filters = [Strategy.user_id == user_id]
        if status and status != "all":
            filters.append(Strategy.status == status)
        else:
            filters.append(Strategy.status != "archived")
        if exchange and exchange != "all":
            filters.append(Strategy.exchange == exchange)
        if strategy_type and strategy_type != "all":
            filters.append(Strategy.strategy_type == strategy_type)
        if risk and risk != "all":
            filters.append(Strategy.estimated_risk == risk)
        if market and market != "all":
            filters.append(Strategy.markets.contains([market]))
        if query:
            q = f"%{query.lower()}%"
            filters.append(
                or_(
                    func.lower(Strategy.name).like(q),
                    func.lower(Strategy.symbol).like(q),
                    func.lower(Strategy.author).like(q),
                    func.lower(Strategy.strategy_type).like(q),
                )
            )

        total = int(
            (await self.session.execute(select(func.count()).select_from(Strategy).where(*filters))).scalar_one()
        )
        result = await self.session.execute(
            select(Strategy)
            .where(*filters)
            .order_by(Strategy.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def clear_canvas(self, strategy_id: UUID) -> None:
        nodes = await self.session.execute(select(StrategyNode).where(StrategyNode.strategy_id == strategy_id))
        for node in nodes.scalars().all():
            await self.session.delete(node)
        edges = await self.session.execute(select(StrategyEdge).where(StrategyEdge.strategy_id == strategy_id))
        for edge in edges.scalars().all():
            await self.session.delete(edge)

    async def list_backtests(self, strategy_id: UUID, *, limit: int = 20) -> list[BacktestRun]:
        result = await self.session.execute(
            select(BacktestRun)
            .where(BacktestRun.strategy_id == strategy_id)
            .order_by(BacktestRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
