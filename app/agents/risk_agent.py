from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.settings_repository import SettingsRepository
from app.services.settings_service import SettingsService


@dataclass
class RiskCheckResult:
    allowed: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    max_position_size: float | None = None
    max_leverage: float | None = None


def _f(v: str | float | int | None) -> float | None:
    if v is None:
        return None
    try:
        return float(Decimal(str(v)))
    except (InvalidOperation, ValueError):
        return None


class RiskAgent:
    """Enforces user Settings risk limits against proposed trades."""

    name = "risk"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings_service = SettingsService(session)
        self.settings_repo = SettingsRepository(session)

    async def check_order(
        self,
        user_id: UUID,
        *,
        notional_usd: float,
        leverage: float | int = 1,
        daily_drawdown_pct: float | None = None,
    ) -> RiskCheckResult:
        s = await self.settings_service.ensure_settings(user_id)
        max_pos = _f(s.max_position_size) or 5000.0
        max_lev = _f(s.max_leverage) or 10.0
        max_dd = _f(s.max_drawdown_daily) or 2.5
        crit_dd = _f(s.critical_stop_drawdown_pct) or 15.0

        warnings: list[str] = []
        blockers: list[str] = []

        if notional_usd > max_pos:
            blockers.append(f"Order notional ${notional_usd:,.2f} exceeds max position size ${max_pos:,.2f}")
        elif notional_usd > max_pos * 0.8:
            warnings.append("Order size is near your max position limit")

        if float(leverage) > max_lev:
            blockers.append(f"Leverage {leverage}x exceeds max leverage {max_lev:g}x")

        if daily_drawdown_pct is not None and daily_drawdown_pct >= max_dd:
            blockers.append(f"Daily drawdown {daily_drawdown_pct:.2f}% exceeds limit {max_dd:g}%")

        if s.critical_stop_enabled and daily_drawdown_pct is not None and daily_drawdown_pct >= crit_dd:
            blockers.append(
                f"Critical stop: global drawdown {daily_drawdown_pct:.2f}% >= {crit_dd:g}% — trading locked"
            )

        if s.autonomous_execution is False and notional_usd > max_pos * 0.5:
            warnings.append("Autonomous execution is off — confirm manually before live send")

        return RiskCheckResult(
            allowed=len(blockers) == 0,
            warnings=warnings,
            blockers=blockers,
            max_position_size=max_pos,
            max_leverage=max_lev,
        )
