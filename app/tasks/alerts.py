from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.services.alert_service import AlertService
from app.tasks.celery_app import celery_app


async def _evaluate_all() -> dict:
    checked_users = 0
    total_triggered = 0
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
        service = AlertService(session)
        for user in users:
            result = await service.evaluate(user.id)
            checked_users += 1
            total_triggered += result.triggered
        await session.commit()
    return {"users": checked_users, "triggered": total_triggered}


@celery_app.task(name="app.tasks.alerts.evaluate_alerts_all_users")
def evaluate_alerts_all_users() -> dict:
    return asyncio.run(_evaluate_all())
