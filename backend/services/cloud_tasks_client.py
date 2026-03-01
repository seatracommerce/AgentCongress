"""Enqueue HTTP target tasks to Google Cloud Tasks. Used to split long-running poll into per-debate tasks."""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import get_settings

logger = logging.getLogger(__name__)


def _queue_path() -> str | None:
    s = get_settings()
    if not all([s.cloud_tasks_project_id, s.cloud_tasks_location, s.cloud_tasks_queue_name]):
        return None
    return (
        f"projects/{s.cloud_tasks_project_id}/locations/{s.cloud_tasks_location}/queues/{s.cloud_tasks_queue_name}"
    )


def is_cloud_tasks_configured() -> bool:
    """True if service_url and queue are set."""
    s = get_settings()
    return bool(s.service_url and _queue_path())


def enqueue_poll_task() -> str | None:
    """Enqueue one task that will POST to /admin/tasks/poll. Returns task name or None if not configured."""
    path = _queue_path()
    if not path:
        return None
    s = get_settings()
    url = f"{s.service_url.rstrip('/')}/admin/tasks/poll"
    return _create_http_task(path, url, body=None)


def enqueue_debate_task(bill_id: int) -> str | None:
    """Enqueue one task that will POST to /admin/tasks/debate with body {"bill_id": bill_id}."""
    path = _queue_path()
    if not path:
        return None
    s = get_settings()
    url = f"{s.service_url.rstrip('/')}/admin/tasks/debate"
    return _create_http_task(path, url, body={"bill_id": bill_id})


def _create_http_task(queue_path: str, url: str, body: dict[str, Any] | None) -> str | None:
    """Create an HTTP target task. Sync; call from async with asyncio.to_thread if needed."""
    try:
        from google.cloud import tasks_v2
    except ImportError:
        logger.warning("google-cloud-tasks not installed; cannot enqueue")
        return None

    s = get_settings()
    client = tasks_v2.CloudTasksClient()
    payload = json.dumps(body).encode("utf-8") if body else b""
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if s.scheduler_secret:
        headers["X-Scheduler-Secret"] = s.scheduler_secret

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            url=url,
            http_method=tasks_v2.HttpMethod.POST,
            body=payload,
            headers=headers,
        )
    )
    response = client.create_task(parent=queue_path, task=task)
    logger.info("Enqueued task %s -> %s", response.name, url)
    return response.name
