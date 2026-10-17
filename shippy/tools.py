from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from shippy.store import connect, insert_task

ASANA_TASKS_URL = "https://app.asana.com/api/1.0/tasks"


class TaskError(Exception):
    pass


def _notes(description: str, sop_ref: str) -> str:
    if not sop_ref:
        return description
    line = f"SOP: {sop_ref}"
    if description:
        return f"{description}\n\n{line}"
    return line


def create_task(
    title: str,
    description: str,
    project: str,
    sop_ref: str,
    *,
    db_path: str | os.PathLike[str] | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    if not title or not title.strip():
        raise TaskError("title is required")
    if token is None:
        token = os.environ.get("ASANA_PAT", "").strip()
    project = project or os.environ.get("ASANA_PROJECT_GID", "").strip()

    if token:
        return _live_create_task(title, description, project, sop_ref, token, timeout)
    return _fallback_create_task(title, description, project, sop_ref, db_path)


def _live_create_task(
    title: str, description: str, project: str, sop_ref: str, token: str, timeout: float
) -> dict[str, Any]:
    if not project:
        raise TaskError("project is required in live mode")
    payload = {"data": {"name": title, "notes": _notes(description, sop_ref), "projects": [project]}}
    response = httpx.post(
        ASANA_TASKS_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    gid = str(response.json()["data"]["gid"])
    return {"mode": "live", "task_id": gid, "task_ref": f"asana:{gid}"}


def _fallback_create_task(
    title: str, description: str, project: str, sop_ref: str, db_path: Any
) -> dict[str, Any]:
    task_ref = f"local:{uuid.uuid4().hex}"
    conn = connect(db_path)
    try:
        task_id = insert_task(
            conn,
            title=title,
            description=description,
            project=project,
            sop_ref=sop_ref,
            mode="fallback",
            task_ref=task_ref,
        )
    finally:
        conn.close()
    return {"mode": "fallback", "task_id": str(task_id), "task_ref": task_ref}
