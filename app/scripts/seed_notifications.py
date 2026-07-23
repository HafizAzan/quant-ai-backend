"""Seed header inbox notifications.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_notifications
  .venv\\Scripts\\python -m app.scripts.seed_notifications --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import NotificationService

SEEDS = [
    {
        "kind": "signal",
        "title": "AAPL breakout signal",
        "body": "Price crossed resistance at $198",
        "icon": "trending",
        "href": "/ai-analysis",
    },
    {
        "kind": "strategy",
        "title": "Strategy alert",
        "body": "Momentum bot triggered a buy",
        "icon": "trending",
        "href": "/strategies",
    },
    {
        "kind": "market",
        "title": "Market update",
        "body": "NASDAQ volatility elevated",
        "icon": "trending",
        "href": "/market",
    },
]


async def seed_for_user(session, user: User) -> None:
    existing = await session.execute(select(Notification).where(Notification.user_id == user.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return
    service = NotificationService(session)
    for item in SEEDS:
        await service.create(user.id, publish=False, **item)


async def main(email: str | None) -> None:
    async with AsyncSessionLocal() as session:
        q = select(User)
        if email:
            q = q.where(User.email == email)
        users = (await session.execute(q)).scalars().all()
        for user in users:
            await seed_for_user(session, user)
            print(f"seeded notifications for {user.email}")
        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
