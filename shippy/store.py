from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_NAME = "data/shippy.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events (run_id);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_ref TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    project TEXT NOT NULL DEFAULT '',
    sop_ref TEXT NOT NULL DEFAULT '',
    mode TEXT NOT NULL,
    run_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS run_events_no_update
BEFORE UPDATE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'run_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS run_events_no_delete
BEFORE DELETE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'run_events is append-only');
END;
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(os.environ.get("SHIPPY_DB_PATH", DEFAULT_DB_NAME))


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def append_event(
    conn: sqlite3.Connection, run_id: str, event: str, detail: dict[str, Any] | None = None
) -> int:
    cursor = conn.execute(
        "INSERT INTO run_events (run_id, event, detail, created_at) VALUES (?, ?, ?, ?)",
        (run_id, event, json.dumps(detail or {}), now_iso()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def read_events(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, event, detail, created_at FROM run_events"
        " WHERE run_id = ? ORDER BY id ASC",
        (run_id,),
    ).fetchall()
    return [
        {
            "seq": row["id"],
            "event": row["event"],
            "detail": json.loads(row["detail"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def create_run(
    conn: sqlite3.Connection, run_id: str, action: str, payload: dict[str, Any], status: str
) -> None:
    stamp = now_iso()
    conn.execute(
        "INSERT INTO runs (run_id, action, payload, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, action, json.dumps(payload), status, stamp, stamp),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT run_id, action, payload, status, created_at, updated_at FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "run_id": row["run_id"],
        "action": row["action"],
        "payload": json.loads(row["payload"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def set_run_status(conn: sqlite3.Connection, run_id: str, status: str) -> None:
    conn.execute(
        "UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?",
        (status, now_iso(), run_id),
    )
    conn.commit()


def insert_task(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str,
    project: str,
    sop_ref: str,
    mode: str,
    run_id: str | None = None,
    task_ref: str | None = None,
) -> int:
    ref = task_ref or f"local:{uuid.uuid4().hex}"
    cursor = conn.execute(
        "INSERT INTO tasks (task_ref, title, description, project, sop_ref, mode, run_id, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ref, title, description, project, sop_ref, mode, run_id, now_iso()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, task_ref, title, description, project, sop_ref, mode, run_id, created_at"
        " FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)
