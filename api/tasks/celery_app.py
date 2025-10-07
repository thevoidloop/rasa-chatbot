"""
Celery application configuration
"""
from celery import Celery
import os

# Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "training_platform",
    broker=redis_url,
    backend=redis_url
)

# Configuration
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    result_expires=3600,
)

# Auto-discover tasks
# celery_app.autodiscover_tasks(['api.tasks'])

@celery_app.task
def test_task():
    """Simple test task"""
    return "Celery is working!"
