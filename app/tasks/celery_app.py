from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "quantai",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks.alerts", "app.tasks.prices"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "publish-price-ticks": {
            "task": "app.tasks.prices.publish_price_ticks",
            "schedule": 5.0,
        },
        "evaluate-alerts-all": {
            "task": "app.tasks.alerts.evaluate_alerts_all_users",
            "schedule": crontab(minute="*/2"),
        },
    },
)
