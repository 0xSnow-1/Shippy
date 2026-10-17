from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

from shippy import store, tools


class WorkflowError(Exception):
    pass


class UnknownRunError(WorkflowError):
    pass


class InvalidStateError(WorkflowError):
    pass


class UnknownActionError(WorkflowError):
    pass


class TaskFailedError(WorkflowError):
    pass


def start(conn: sqlite3.Connection, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    if action != "create_task":
        raise UnknownActionError(f"unknown action: {action}")
    run_id = f"run-{uuid.uuid4().hex}"
    store.create_run(conn, run_id, action, payload, status="pending_approval")
    store.append_event(conn, run_id, "run_created", {"action": action})
    return {"run_id": run_id, "action": action, "status": "pending_approval"}


def approve(
    conn: sqlite3.Connection, run_id: str, db_path: str | Path | None = None
) -> dict[str, Any]:
    run = store.get_run(conn, run_id)
    if run is None:
        raise UnknownRunError("run not found")
    if run["status"] != "pending_approval":
        raise InvalidStateError(f"cannot approve run in status {run['status']}")

    store.set_run_status(conn, run_id, "approved")
    store.append_event(conn, run_id, "approved", {})

    payload = run["payload"]
    try:
        task = tools.create_task(
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            project=payload.get("project", ""),
            sop_ref=payload.get("sop_ref", ""),
            db_path=db_path,
        )
    except Exception as exc:
        store.set_run_status(conn, run_id, "failed")
        store.append_event(conn, run_id, "failed", {"error": str(exc)})
        raise TaskFailedError(str(exc)) from exc

    store.append_event(conn, run_id, "task_created", task)
    store.set_run_status(conn, run_id, "completed")
    return {"run_id": run_id, "status": "completed", "task": task}


def reject(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = store.get_run(conn, run_id)
    if run is None:
        raise UnknownRunError("run not found")
    if run["status"] != "pending_approval":
        raise InvalidStateError(f"cannot reject run in status {run['status']}")
    store.set_run_status(conn, run_id, "rejected")
    store.append_event(conn, run_id, "rejected", {})
    return {"run_id": run_id, "status": "rejected"}


def replay(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = store.get_run(conn, run_id)
    if run is None:
        raise UnknownRunError("run not found")
    return {"run_id": run_id, "status": run["status"], "events": store.read_events(conn, run_id)}
