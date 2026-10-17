from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shippy import store
from shippy.app import get_app
from shippy.compose import MockLLM
from shippy.retrieve import RELEVANCE_FLOOR, SearchResult

API_KEY = "test-key"
HEADERS = {"x-api-key": API_KEY}
PAYLOAD = {
    "title": "Chase the damaged parcel claim",
    "description": "File the claim with the carrier.",
    "project": "99887766",
    "sop_ref": "sop-damaged-parcel-claims",
}


def fake_search(query: str, floor: float = RELEVANCE_FLOOR) -> SearchResult:
    return SearchResult(status="no_match", chunks=[])


def db_file(tmp_path: Path) -> Path:
    return tmp_path / "w.db"


def make_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("ASANA_PAT", raising=False)
    return TestClient(
        get_app(
            search=fake_search,
            provider=MockLLM({}),
            api_key=API_KEY,
            db_path=db_file(tmp_path),
        )
    )


def start_run(client: TestClient) -> str:
    response = client.post(
        "/workflows/run",
        json={"action": "create_task", "payload": PAYLOAD},
        headers=HEADERS,
    )
    assert response.status_code == 200
    return response.json()["run_id"]


def test_start_returns_pending_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/workflows/run",
        json={"action": "create_task", "payload": PAYLOAD},
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("run-")
    assert body["action"] == "create_task"
    assert body["status"] == "pending_approval"


def test_approve_lands_fallback_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)

    response = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] == "completed"
    assert body["task"]["mode"] == "fallback"

    conn = store.connect(db_file(tmp_path))
    try:
        rows = conn.execute("SELECT id, mode FROM tasks").fetchall()
        events = store.read_events(conn, run_id)
    finally:
        conn.close()
    assert [row["mode"] for row in rows] == ["fallback"]
    task_created = [event for event in events if event["event"] == "task_created"]
    assert task_created[0]["detail"]["task_id"] == str(rows[0]["id"])


def test_reject_ends_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)

    response = client.post(f"/workflows/{run_id}/reject", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {"run_id": run_id, "status": "rejected"}
    trail = client.get(f"/runs/{run_id}", headers=HEADERS).json()
    assert trail["status"] == "rejected"
    assert [event["event"] for event in trail["events"]] == ["run_created", "rejected"]


def test_replay_returns_full_trail_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)
    approve = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)
    assert approve.status_code == 200

    response = client.get(f"/runs/{run_id}", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] == "completed"
    events = body["events"]
    assert [event["event"] for event in events] == ["run_created", "approved", "task_created"]
    seqs = [event["seq"] for event in events]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)
    assert all(set(event) == {"seq", "event", "detail", "created_at"} for event in events)


def test_wrong_key_returns_401(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/workflows/run",
        json={"action": "create_task", "payload": PAYLOAD},
        headers={"x-api-key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_unknown_run_returns_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.get("/runs/run-missing", headers=HEADERS)

    assert response.status_code == 404
    assert response.json() == {"error": "run not found"}


def test_double_approve_returns_409(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)

    first = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)
    second = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)

    assert first.status_code == 200
    assert second.status_code == 409


def test_unsupported_action_returns_400(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/workflows/run",
        json={"action": "delete_project", "payload": PAYLOAD},
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert response.json() == {"error": "unknown action: delete_project"}


def test_db_runs_in_wal_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    start_run(client)

    conn = store.connect(db_file(tmp_path))
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()

    assert mode == "wal"


def test_run_events_reject_update_and_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)

    conn = store.connect(db_file(tmp_path))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE run_events SET event = 'tampered' WHERE run_id = ?", (run_id,))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM run_events WHERE run_id = ?", (run_id,))
        assert store.read_events(conn, run_id)[0]["event"] == "run_created"
    finally:
        conn.close()


def test_approve_rejected_run_returns_409(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    run_id = start_run(client)
    reject = client.post(f"/workflows/{run_id}/reject", headers=HEADERS)
    assert reject.status_code == 200

    response = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)

    assert response.status_code == 409


def test_missing_body_returns_400(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.post("/workflows/run", content="not json", headers=HEADERS)

    assert response.status_code == 400
    assert response.json() == {"error": "action and payload are required"}


def test_approve_tool_failure_marks_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    start = client.post(
        "/workflows/run",
        json={"action": "create_task", "payload": {**PAYLOAD, "title": ""}},
        headers=HEADERS,
    )
    run_id = start.json()["run_id"]

    approve = client.post(f"/workflows/{run_id}/approve", headers=HEADERS)

    assert approve.status_code == 500
    trail = client.get(f"/runs/{run_id}", headers=HEADERS).json()
    assert trail["status"] == "failed"
    assert [event["event"] for event in trail["events"]] == ["run_created", "approved", "failed"]
