from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "secure_files",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.file_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "daily-db-backup": {
            "task": "app.tasks.backup_database",
            "schedule": crontab(hour=2, minute=0),
        }
    }
)
