from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import UserApiKey, UserSettings


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_settings(self, user_id: UUID) -> UserSettings | None:
        result = await self.session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()

    async def add_settings(self, row: UserSettings) -> UserSettings:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_api_keys(self, user_id: UUID) -> list[UserApiKey]:
        result = await self.session.execute(
            select(UserApiKey)
            .where(UserApiKey.user_id == user_id, UserApiKey.revoked_at.is_(None))
            .order_by(UserApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_api_key(self, user_id: UUID, key_id: UUID) -> UserApiKey | None:
        result = await self.session.execute(
            select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_api_key(self, row: UserApiKey) -> UserApiKey:
        self.session.add(row)
        await self.session.flush()
        return row

    async def flush(self) -> None:
        await self.session.flush()
