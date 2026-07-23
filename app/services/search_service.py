from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.journal import JournalEntry
from app.models.market import Asset
from app.models.search import SearchPin, SearchRecent
from app.models.strategy import Strategy
from app.repositories.search_repository import SearchRepository
from app.schemas.search import (
    SearchItemOut,
    SearchPinCreateRequest,
    SearchPinOut,
    SearchRecentCreateRequest,
    SearchRecentOut,
    SearchResultsOut,
    SearchSuggestionOut,
)
from app.services.search_catalog import SEARCH_CATALOG, score_item


def _catalog_to_out(item: dict, score: float) -> SearchItemOut:
    return SearchItemOut(
        id=item["id"],
        title=item["title"],
        subtitle=item.get("subtitle"),
        category=item["category"],
        kind=item["kind"],
        href=item["href"],
        keywords=list(item.get("keywords") or []),
        symbol=item.get("symbol"),
        icon=item.get("icon"),
        actions=list(item.get("actions") or []),
        boost=float(item.get("boost") or 0),
        is_command=bool(item.get("is_command")),
        score=score,
    )


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SearchRepository(session)

    async def search(self, user_id: UUID, query: str, limit: int = 20) -> SearchResultsOut:
        q = query.strip()
        scored: list[SearchItemOut] = []
        for item in SEARCH_CATALOG:
            s = score_item(q, item)
            if q and s <= float(item.get("boost") or 0):
                continue
            scored.append(_catalog_to_out(item, s))

        if q:
            like = f"%{q}%"
            assets = (
                await self.session.execute(select(Asset).where(or_(Asset.symbol.ilike(like), Asset.name.ilike(like))).limit(10))
            ).scalars().all()
            for a in assets:
                scored.append(
                    SearchItemOut(
                        id=f"db-asset-{a.id}",
                        title=a.symbol,
                        subtitle=a.name,
                        category="trading-pairs",
                        kind="asset",
                        href="/market",
                        symbol=a.symbol,
                        icon="asset",
                        actions=["open", "analyze", "open-chart"],
                        score=2.0,
                    )
                )
            strategies = (
                await self.session.execute(
                    select(Strategy).where(Strategy.user_id == user_id, Strategy.name.ilike(like)).limit(10)
                )
            ).scalars().all()
            for st in strategies:
                scored.append(
                    SearchItemOut(
                        id=f"db-strategy-{st.id}",
                        title=st.name,
                        subtitle="Strategy",
                        category="strategies",
                        kind="strategy",
                        href="/strategies",
                        icon="strategies",
                        actions=["open", "analyze"],
                        score=2.0,
                    )
                )
            alerts = (
                await self.session.execute(
                    select(Alert).where(
                        Alert.user_id == user_id,
                        or_(Alert.title.ilike(like), Alert.symbol.ilike(like)),
                    ).limit(10)
                )
            ).scalars().all()
            for al in alerts:
                scored.append(
                    SearchItemOut(
                        id=f"db-alert-{al.id}",
                        title=al.title,
                        subtitle=al.symbol,
                        category="alerts",
                        kind="alert",
                        href="/alerts",
                        symbol=al.symbol,
                        icon="alerts",
                        actions=["open"],
                        score=1.8,
                    )
                )
            journals = (
                await self.session.execute(
                    select(JournalEntry)
                    .where(
                        JournalEntry.user_id == user_id,
                        or_(JournalEntry.symbol.ilike(like), JournalEntry.notes.ilike(like)),
                    )
                    .limit(10)
                )
            ).scalars().all()
            for je in journals:
                scored.append(
                    SearchItemOut(
                        id=f"db-journal-{je.id}",
                        title=f"{je.symbol} {je.side}",
                        subtitle=je.strategy_tag or "Journal",
                        category="journal",
                        kind="journal",
                        href="/journal",
                        symbol=je.symbol,
                        icon="journal",
                        actions=["open"],
                        score=1.5,
                    )
                )

        scored.sort(key=lambda x: x.score, reverse=True)
        # de-dupe by id
        seen: set[str] = set()
        items: list[SearchItemOut] = []
        for it in scored:
            if it.id in seen:
                continue
            seen.add(it.id)
            items.append(it)
            if len(items) >= limit:
                break

        suggestions = await self._suggestions(user_id, q)
        return SearchResultsOut(query=q, items=items, suggestions=suggestions)

    async def _suggestions(self, user_id: UUID, query: str) -> list[SearchSuggestionOut]:
        out: list[SearchSuggestionOut] = []
        for pin in await self.repo.list_pins(user_id):
            out.append(
                SearchSuggestionOut(
                    id=f"pin-{pin.id}",
                    label=pin.title,
                    href=pin.href,
                    kind="pinned",
                )
            )
        for recent in await self.repo.list_recents(user_id, limit=5):
            out.append(
                SearchSuggestionOut(
                    id=f"recent-{recent.id}",
                    label=recent.title,
                    query=recent.query or None,
                    href=recent.href,
                    kind="recent",
                )
            )
        if query:
            out.append(
                SearchSuggestionOut(
                    id="ai-ask",
                    label=f"Ask AI: {query}",
                    description="Open AI Chat with this query",
                    query=query,
                    href="/ai-chat",
                    kind="ai",
                )
            )
        return out[:12]

    async def list_recents(self, user_id: UUID) -> list[SearchRecentOut]:
        rows = await self.repo.list_recents(user_id)
        return [
            SearchRecentOut(id=r.id, query=r.query, item_id=r.item_id, title=r.title, href=r.href, at=r.at)
            for r in rows
        ]

    async def add_recent(self, user_id: UUID, payload: SearchRecentCreateRequest) -> SearchRecentOut:
        row = SearchRecent(
            user_id=user_id,
            query=payload.query,
            item_id=payload.item_id,
            title=payload.title,
            href=payload.href,
        )
        await self.repo.add_recent(row)
        return SearchRecentOut(
            id=row.id, query=row.query, item_id=row.item_id, title=row.title, href=row.href, at=row.at
        )

    async def list_pins(self, user_id: UUID) -> list[SearchPinOut]:
        rows = await self.repo.list_pins(user_id)
        return [
            SearchPinOut(id=r.id, item_id=r.item_id, title=r.title, href=r.href, sort_order=r.sort_order)
            for r in rows
        ]

    async def add_pin(self, user_id: UUID, payload: SearchPinCreateRequest) -> SearchPinOut:
        existing = await self.repo.get_pin(user_id, payload.item_id)
        if existing:
            return SearchPinOut(
                id=existing.id,
                item_id=existing.item_id,
                title=existing.title,
                href=existing.href,
                sort_order=existing.sort_order,
            )
        pins = await self.repo.list_pins(user_id)
        row = SearchPin(
            user_id=user_id,
            item_id=payload.item_id,
            title=payload.title,
            href=payload.href,
            sort_order=len(pins),
        )
        await self.repo.add_pin(row)
        return SearchPinOut(id=row.id, item_id=row.item_id, title=row.title, href=row.href, sort_order=row.sort_order)

    async def remove_pin(self, user_id: UUID, item_id: str) -> None:
        await self.repo.delete_pin(user_id, item_id)
