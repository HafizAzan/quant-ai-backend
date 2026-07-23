from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalCoachItem, JournalEntry, JournalProfile, JournalTimelineEvent
from app.repositories.journal_repository import JournalRepository
from app.schemas.journal import (
    AiCoachItemOut,
    CreateJournalEntryRequest,
    JournalDeskOut,
    JournalEntryOut,
    JournalGroupOut,
    JournalListOut,
    JournalTimelineOut,
    TradeImprovementOut,
    TraderEvolutionOut,
    TradeScoreOut,
    UpdateJournalEntryRequest,
)

MISTAKE_LABELS = {
    "fomo_entry": "FOMO Entry",
    "revenge_trading": "Revenge Trading",
    "early_exit": "Early Exit",
    "late_entry": "Late Entry",
    "oversized_position": "Oversized Position",
    "ignored_stop_loss": "Ignored Stop Loss",
    "emotional_trading": "Emotional Trading",
    "overtrading": "Overtrading",
    "poor_risk_reward": "Poor Risk Reward",
    "high_impact_news": "Trading During High Impact News",
}

FILTER_OPTIONS = {
    "date_range": [
        {"value": "30d", "label": "Last 30 Days"},
        {"value": "7d", "label": "Last 7 Days"},
        {"value": "90d", "label": "Last 90 Days"},
        {"value": "all", "label": "All Time"},
    ],
    "asset": [
        {"value": "all", "label": "All Assets"},
        {"value": "BTC/USDT", "label": "BTC/USDT"},
        {"value": "ETH/USDT", "label": "ETH/USDT"},
        {"value": "SOL/USDT", "label": "SOL/USDT"},
    ],
    "strategy": [
        {"value": "all", "label": "Strategy Tags"},
        {"value": "SCALPING", "label": "Scalping"},
        {"value": "BREAKOUT", "label": "Breakout"},
        {"value": "SWING", "label": "Swing"},
    ],
    "outcome": [
        {"value": "all", "label": "Win / Loss"},
        {"value": "win", "label": "Wins"},
        {"value": "loss", "label": "Losses"},
    ],
}

DEFAULT_ANALYTICS = {
    "win_rate": "0%",
    "profit_factor": "0",
    "avg_win": "$0.00",
    "avg_loss": "$0.00",
    "avg_rr": "1:1",
    "avg_holding": "—",
    "max_drawdown": "0%",
    "expectancy": "$0.00",
    "best_day": "—",
    "worst_day": "—",
    "most_traded": "—",
    "best_timeframe": "—",
    "best_strategy": "—",
}


def _date_group(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%B %d, %Y").upper()


def _grade(overall: int) -> str:
    if overall >= 95:
        return "A+"
    if overall >= 85:
        return "A"
    if overall >= 75:
        return "B"
    if overall >= 60:
        return "C"
    if overall >= 45:
        return "D"
    return "F"


def _default_score(outcome: str) -> dict:
    base = {"win": 82, "loss": 45, "breakeven": 60}.get(outcome, 60)
    return {
        "overall": base,
        "entry_quality": base,
        "exit_quality": max(base - 8, 30),
        "risk_management": base,
        "psychology": max(base - 10, 25),
        "execution": base,
        "patience": max(base - 12, 20),
        "rule_compliance": base,
        "grade": _grade(base),
    }


def _default_improvement(outcome: str) -> dict:
    if outcome == "win":
        return {
            "went_well": ["Followed plan", "Managed risk"],
            "went_wrong": [],
            "should_improve": ["Review exit timing"],
            "alternative_entry": None,
            "alternative_exit": None,
            "better_stop_loss": None,
            "better_take_profit": None,
            "professional_tips": ["Journal the setup checklist before entry"],
            "next_focus": "Hold to predefined TP unless structure breaks",
        }
    if outcome == "loss":
        return {
            "went_well": ["Honored stop loss"],
            "went_wrong": ["Entry timing"],
            "should_improve": ["Wait for confirmation"],
            "alternative_entry": None,
            "alternative_exit": None,
            "better_stop_loss": None,
            "better_take_profit": None,
            "professional_tips": ["Reduce size after consecutive losses"],
            "next_focus": "Zero FOMO entries for next 5 sessions",
        }
    return {
        "went_well": ["Limited downside"],
        "went_wrong": ["Thesis incomplete"],
        "should_improve": ["Clearer invalidation"],
        "alternative_entry": None,
        "alternative_exit": None,
        "better_stop_loss": None,
        "better_take_profit": None,
        "professional_tips": ["Skip low-conviction setups"],
        "next_focus": "Only trade A+ setups",
    }


class JournalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = JournalRepository(session)

    async def ensure_profile(self, user_id: UUID) -> JournalProfile:
        profile = await self.repo.get_profile(user_id)
        if profile is not None:
            return profile
        profile = JournalProfile(
            id=uuid4(),
            user_id=user_id,
            level="Beginner Trader",
            overall_score=0,
            discipline=0,
            psychology=0,
            risk_management=0,
            execution=0,
            biggest_weakness="Not enough logged trades yet.",
            current_mission="Log your next 10 trades with full notes.",
            estimated_improvement="+edge after 10 reviews",
            analytics=dict(DEFAULT_ANALYTICS),
            patterns=[],
            allocation=[],
            monthly_progress=[],
            daily_pnl=[],
            strategy_insight={
                "title": "AI Strategy Insight",
                "body": "Log more trades to unlock personalized strategy insights.",
                "action_label": "Open Journal",
            },
        )
        await self.repo.add(profile)
        await self.repo.flush()
        return profile

    def _score_out(self, raw: dict | None) -> TradeScoreOut:
        data = raw or {}
        return TradeScoreOut(
            overall=int(data.get("overall", 0)),
            entry_quality=int(data.get("entry_quality", data.get("entryQuality", 0))),
            exit_quality=int(data.get("exit_quality", data.get("exitQuality", 0))),
            risk_management=int(data.get("risk_management", data.get("riskManagement", 0))),
            psychology=int(data.get("psychology", 0)),
            execution=int(data.get("execution", 0)),
            patience=int(data.get("patience", 0)),
            rule_compliance=int(data.get("rule_compliance", data.get("ruleCompliance", 0))),
            grade=str(data.get("grade", "C")),
        )

    def _improvement_out(self, raw: dict | None) -> TradeImprovementOut:
        data = raw or {}
        return TradeImprovementOut(
            went_well=list(data.get("went_well", data.get("wentWell", [])) or []),
            went_wrong=list(data.get("went_wrong", data.get("wentWrong", [])) or []),
            should_improve=list(data.get("should_improve", data.get("shouldImprove", [])) or []),
            alternative_entry=data.get("alternative_entry", data.get("alternativeEntry")),
            alternative_exit=data.get("alternative_exit", data.get("alternativeExit")),
            better_stop_loss=data.get("better_stop_loss", data.get("betterStopLoss")),
            better_take_profit=data.get("better_take_profit", data.get("betterTakeProfit")),
            professional_tips=list(data.get("professional_tips", data.get("professionalTips", [])) or []),
            next_focus=str(data.get("next_focus", data.get("nextFocus", "")) or ""),
        )

    def _to_entry_out(self, entry: JournalEntry) -> JournalEntryOut:
        timeline = sorted(entry.timeline or [], key=lambda t: t.sort_order)
        return JournalEntryOut(
            id=entry.id,
            date_group=entry.date_group or _date_group(entry.traded_at),
            symbol=entry.symbol,
            side=entry.side,
            strategy_tag=entry.strategy_tag,
            emotion_tag=entry.emotion_tag,
            timeframe=entry.timeframe,
            market_condition=entry.market_condition,
            outcome=entry.outcome,
            pnl=entry.pnl,
            roi_percent=entry.roi_percent,
            risk_reward=entry.risk_reward,
            duration=entry.duration,
            exited_at=entry.exited_at_label,
            entry_price=entry.entry_price,
            exit_price=entry.exit_price,
            stop_loss=entry.stop_loss,
            take_profit=entry.take_profit,
            notes=entry.notes,
            psychology_notes=entry.psychology_notes,
            ai_summary=entry.ai_summary,
            score=self._score_out(entry.score if isinstance(entry.score, dict) else {}),
            mistakes=list(entry.mistakes or []),
            improvement=self._improvement_out(entry.improvement if isinstance(entry.improvement, dict) else {}),
            timeline=[
                JournalTimelineOut(
                    id=t.id,
                    kind=t.kind,
                    time=t.time_label,
                    title=t.title,
                    detail=t.detail,
                )
                for t in timeline
            ],
            candles=list(entry.candles or []),
            entry_time=int(entry.entry_time or 0),
            exit_time=int(entry.exit_time or 0),
            traded_at=entry.traded_at,
        )

    async def get_desk(self, user_id: UUID) -> JournalDeskOut:
        profile = await self.ensure_profile(user_id)
        coach = await self.repo.list_coach(user_id)
        insight = profile.strategy_insight or {}
        return JournalDeskOut(
            evolution=TraderEvolutionOut(
                level=profile.level,
                overall_score=profile.overall_score,
                discipline=profile.discipline,
                psychology=profile.psychology,
                risk_management=profile.risk_management,
                execution=profile.execution,
                biggest_weakness=profile.biggest_weakness,
                current_mission=profile.current_mission,
                estimated_improvement=profile.estimated_improvement,
            ),
            analytics=profile.analytics or dict(DEFAULT_ANALYTICS),
            patterns=list(profile.patterns or []),
            allocation=list(profile.allocation or []),
            monthly_progress=list(profile.monthly_progress or []),
            daily_pnl=list(profile.daily_pnl or []),
            coach=[
                AiCoachItemOut(
                    id=c.id,
                    title=c.title,
                    detail=c.detail,
                    action_label=c.action_label,
                )
                for c in coach
            ],
            strategy_insight={
                "title": str(insight.get("title", "AI Strategy Insight")),
                "body": str(insight.get("body", "")),
                "action_label": str(insight.get("action_label", insight.get("actionLabel", "Apply"))),
            },
            filter_options=FILTER_OPTIONS,
            mistake_labels=MISTAKE_LABELS,
        )

    async def list_entries(
        self,
        user_id: UUID,
        *,
        date_range: str = "30d",
        asset: str | None = None,
        strategy: str | None = None,
        outcome: str | None = None,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JournalListOut:
        await self.ensure_profile(user_id)
        items, total = await self.repo.list_entries(
            user_id,
            date_range=date_range,
            asset=asset,
            strategy=strategy,
            outcome=outcome,
            query=query,
            page=page,
            page_size=page_size,
        )
        outs = [self._to_entry_out(e) for e in items]
        grouped_map: dict[str, list[JournalEntryOut]] = {}
        for out in outs:
            grouped_map.setdefault(out.date_group, []).append(out)
        grouped = [JournalGroupOut(date=date, items=rows) for date, rows in grouped_map.items()]
        return JournalListOut(items=outs, grouped=grouped, total=total, page=page, page_size=page_size)

    async def get_entry(self, user_id: UUID, entry_id: UUID) -> JournalEntryOut:
        entry = await self.repo.get_entry(user_id, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
        return self._to_entry_out(entry)

    async def create_entry(self, user_id: UUID, payload: CreateJournalEntryRequest) -> JournalEntryOut:
        await self.ensure_profile(user_id)
        now = datetime.now(timezone.utc)
        score = _default_score(payload.outcome)
        improvement = _default_improvement(payload.outcome)
        entry = JournalEntry(
            id=uuid4(),
            user_id=user_id,
            paper_position_id=payload.paper_position_id,
            symbol=payload.symbol.upper() if "/" not in payload.symbol else payload.symbol,
            side=payload.side,
            strategy_tag=payload.strategy_tag.upper(),
            emotion_tag=payload.emotion_tag,
            timeframe=payload.timeframe,
            market_condition=payload.market_condition,
            outcome=payload.outcome,
            pnl=payload.pnl,
            roi_percent=payload.roi_percent,
            risk_reward=payload.risk_reward,
            duration=payload.duration,
            exited_at_label=payload.exited_at or now.strftime("%H:%M"),
            entry_price=payload.entry_price,
            exit_price=payload.exit_price,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            notes=payload.notes,
            psychology_notes=payload.psychology_notes,
            ai_summary=f"Manual journal entry · outcome {payload.outcome} · grade {score['grade']}.",
            score=score,
            mistakes=list(payload.mistakes or []),
            improvement=improvement,
            candles=[],
            entry_time=int(now.timestamp()) - 3600,
            exit_time=int(now.timestamp()),
            traded_at=now,
            date_group=_date_group(now),
        )
        await self.repo.add(entry)
        await self.repo.flush()

        events = [
            ("opened", entry.exited_at_label, "Trade Opened", f"{entry.side.title()} @ {entry.entry_price}"),
            ("final_exit", entry.exited_at_label, "Final Exit", f"Closed @ {entry.exit_price}"),
            ("ai_review", entry.exited_at_label, "AI Review Completed", f"Score {score['overall']} · Grade {score['grade']}"),
        ]
        for i, (kind, time_label, title, detail) in enumerate(events):
            await self.repo.add(
                JournalTimelineEvent(
                    id=uuid4(),
                    entry_id=entry.id,
                    kind=kind,
                    time_label=time_label,
                    title=title,
                    detail=detail,
                    sort_order=i,
                )
            )
        await self.session.commit()
        loaded = await self.repo.get_entry(user_id, entry.id)
        assert loaded is not None
        return self._to_entry_out(loaded)

    async def update_entry(
        self, user_id: UUID, entry_id: UUID, payload: UpdateJournalEntryRequest
    ) -> JournalEntryOut:
        entry = await self.repo.get_entry(user_id, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
        data = payload.model_dump(exclude_unset=True)
        if "notes" in data and data["notes"] is not None:
            entry.notes = data["notes"]
        if "psychology_notes" in data and data["psychology_notes"] is not None:
            entry.psychology_notes = data["psychology_notes"]
        if "emotion_tag" in data:
            entry.emotion_tag = data["emotion_tag"]
        if "strategy_tag" in data and data["strategy_tag"] is not None:
            entry.strategy_tag = data["strategy_tag"].upper()
        if "outcome" in data and data["outcome"] is not None:
            entry.outcome = data["outcome"]
        if "mistakes" in data and data["mistakes"] is not None:
            entry.mistakes = data["mistakes"]
        await self.session.commit()
        loaded = await self.repo.get_entry(user_id, entry_id)
        assert loaded is not None
        return self._to_entry_out(loaded)

    async def delete_entry(self, user_id: UUID, entry_id: UUID) -> None:
        entry = await self.repo.get_entry(user_id, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
        await self.repo.delete(entry)
        await self.session.commit()
