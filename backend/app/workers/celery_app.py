from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "pellevista_content_autopilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-shopify-sync": {
            "task": "app.workers.tasks.sync_shopify_products",
            "schedule": crontab(hour=0, minute=5),
        },
        "daily-content-plan": {
            "task": "app.workers.tasks.create_daily_content_plan",
            "schedule": crontab(hour=0, minute=15),
        },
        "daily-asset-generation": {
            "task": "app.workers.tasks.generate_daily_assets",
            "schedule": crontab(hour=0, minute=30),
        },
        "daily-post-preparation": {
            "task": "app.workers.tasks.prepare_daily_posts",
            "schedule": crontab(hour=2, minute=0),
        },
        "publish-due-scheduled-posts": {
            "task": "app.workers.tasks.publish_due_scheduled_posts",
            "schedule": crontab(minute="*"),
        },
        "collect-due-analytics": {
            "task": "app.workers.tasks.collect_due_analytics",
            "schedule": crontab(minute="*/15"),
        },
    },
)
