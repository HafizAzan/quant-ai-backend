"""Create/update an admin user and seed all modules for them.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_admin
  .venv\\Scripts\\python -m app.scripts.seed_admin --email you@example.com --password 'Secret1' --name 'Admin'
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.scripts.seed_alerts import seed_for_user as seed_alerts
from app.scripts.seed_analysis import seed_for_user as seed_analysis
from app.scripts.seed_chat import seed_for_user as seed_chat
from app.scripts.seed_journal import seed_for_user as seed_journal
from app.scripts.seed_live import seed_for_user as seed_live
from app.scripts.seed_markets import seed as seed_markets
from app.scripts.seed_notifications import seed_for_user as seed_notifications
from app.scripts.seed_paper import seed_for_user as seed_paper
from app.scripts.seed_portfolio import seed_for_user as seed_portfolio
from app.scripts.seed_settings import seed_for_user as seed_settings
from app.scripts.seed_strategies import seed_for_user as seed_strategies


async def ensure_admin(*, email: str, password: str, full_name: str) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=email.lower(),
                full_name=full_name,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value,
                is_active=True,
                is_email_verified=True,
            )
            session.add(user)
            await session.flush()
            print(f"created admin {user.email}")
        else:
            user.full_name = full_name
            user.hashed_password = hash_password(password)
            user.role = UserRole.ADMIN.value
            user.is_active = True
            user.is_email_verified = True
            await session.flush()
            print(f"updated admin {user.email}")
        await session.commit()
        await session.refresh(user)
        return user


async def seed_all(email: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None:
            raise SystemExit(f"user not found: {email}")

        await seed_settings(session, user)
        print("  + settings")
        await seed_notifications(session, user)
        print("  + notifications")
        await seed_portfolio(session, user.id)
        print("  + portfolio")
        await seed_paper(session, user.id)
        print("  + paper")
        await seed_analysis(session, user.id)
        print("  + analysis")
        await seed_alerts(session, user.id)
        print("  + alerts")
        await seed_journal(session, user.id)
        print("  + journal")
        await seed_chat(session, user.id)
        print("  + chat")
        await seed_strategies(session, user.id)
        print("  + strategies")
        await seed_live(session, user.id)
        print("  + live")
        await session.commit()
        print(f"seeded all modules for {user.email} (role={user.role})")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="azanahmedkhan.dev@gmail.com")
    parser.add_argument("--password", default="Az@n123")
    parser.add_argument("--name", default="Azan Ahmed Khan")
    args = parser.parse_args()

    await ensure_admin(email=args.email, password=args.password, full_name=args.name)
    print("seeding markets…")
    await seed_markets()
    print("seeding user modules…")
    await seed_all(args.email)


if __name__ == "__main__":
    asyncio.run(main())
