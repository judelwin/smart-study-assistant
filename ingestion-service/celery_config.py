import os
from celery import Celery
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379"
    CELERY_REDIS_URL: Optional[str] = None  # Optional, for Celery-specific Redis URL
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/classgpt"

    class Config:
        env_file = ".env"

settings = Settings()

print("ENV REDIS_URL:", os.environ.get("REDIS_URL"))
print("ENV CELERY_REDIS_URL:", os.environ.get("CELERY_REDIS_URL"))

# Use CELERY_REDIS_URL if set, otherwise fall back to REDIS_URL
celery_broker_url = settings.CELERY_REDIS_URL or settings.REDIS_URL
print("CELERY BROKER URL:", celery_broker_url)

# Create Celery app
celery_app = Celery(
    "ingestion_service",
    broker=celery_broker_url,
    backend=celery_broker_url,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
) 