"""
Celery application factory.
"""

import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "serpent",
    broker=redis_url,
    backend=redis_url,
    include=["app.workers.tasks.ingest"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="ingest",
    task_queues={
        "ingest": {"exchange": "ingest", "routing_key": "ingest"},
        "evaluate": {"exchange": "evaluate", "routing_key": "evaluate"},
    },
)
