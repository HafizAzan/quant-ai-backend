"""Seed settings defaults + sample platform API keys.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_settings
  .venv\\Scripts\\python -m app.scripts.seed_settings --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.models.settings import UserApiKey, UserSettings
from app.models.user import User
from app.services.settings_service import SettingsService


async def seed_for_user(session, user: User) -> None:
    service = SettingsService(session)
    s = await service.ensure_settings(user.id)
    s.two_factor_enabled = True
    s.session_timeout = "30"
    s.primary_engine = "gpt-4o-finance"
    s.temperature = 0.45
    s.autonomous_execution = True
    s.max_drawdown_daily = "2.5"
    s.max_position_size = "5000"
    s.max_leverage = "10"

    existing = await session.execute(
        select(UserApiKey).where(UserApiKey.user_id == user.id, UserApiKey.revoked_at.is_(None)).limit(1)
    )
    if existing.scalar_one_or_none() is None:
        session.add(
            UserApiKey(
                user_id=user.id,
                label="Production Bot V1",
                key_prefix="ak_live_7x9...",
                key_hash=hash_password("ak_seed_placeholder_live"),
                permission="read-write",
            )
        )
        session.add(
            UserApiKey(
                user_id=user.id,
                label="Backtesting Suite",
                key_prefix="ak_test_4f2...",
                key_hash=hash_password("ak_seed_placeholder_test"),
                permission="read-only",
            )
        )


async def main(email: str | None) -> None:
    async with AsyncSessionLocal() as session:
        q = select(User)
        if email:
            q = q.where(User.email == email)
        users = (await session.execute(q)).scalars().all()
        for user in users:
            await seed_for_user(session, user)
            print(f"seeded settings for {user.email}")
        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
