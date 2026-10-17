from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

from shippy.store import connect
from shippy.tools import TaskError, create_task

ASANA_TASKS_URL = "https://app.asana.com/api/1.0/tasks"


@respx.mock
def test_live_contract() -> None:
    route = respx.post(ASANA_TASKS_URL).respond(json={"data": {"gid": "1209876543210"}})
    title = "Chase the damaged parcel claim"

    result = create_task(
        title=title,
        description="File the claim with the carrier.",
        project="99887766",
        sop_ref="sop-damaged-parcel-claims",
        token="fake-pat-123",
    )

    request = route.calls.last.request
    assert request.method == "POST"
    assert str(request.url) == ASANA_TASKS_URL
    assert request.headers["Authorization"] == "Bearer fake-pat-123"
    data = json.loads(request.content)["data"]
    assert set(data) == {"name", "notes", "projects"}
    assert data["name"] == title
    assert "SOP: sop-damaged-parcel-claims" in data["notes"]
    assert data["projects"] == ["99887766"]
    assert result == {
        "mode": "live",
        "task_id": "1209876543210",
        "task_ref": "asana:1209876543210",
    }
    assert "fake-pat-123" not in str(result)


@respx.mock
def test_fallback_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASANA_PAT", raising=False)

    result = create_task(
        title="Chase the damaged parcel claim",
        description="File the claim with the carrier.",
        project="",
        sop_ref="sop-damaged-parcel-claims",
        db_path=tmp_path / "tasks.db",
    )

    assert result["mode"] == "fallback"
    assert result["task_ref"].startswith("local:")
    conn = connect(tmp_path / "tasks.db")
    try:
        row = conn.execute(
            "SELECT title, mode FROM tasks WHERE task_ref = ?", (result["task_ref"],)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["title"] == "Chase the damaged parcel claim"
    assert row["mode"] == "fallback"


@respx.mock
def test_title_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASANA_PAT", raising=False)

    with pytest.raises(TaskError, match="title is required"):
        create_task(
            title="",
            description="",
            project="",
            sop_ref="",
            db_path=tmp_path / "tasks.db",
        )
    with pytest.raises(TaskError, match="title is required"):
        create_task(
            title="   ",
            description="",
            project="",
            sop_ref="",
            token="fake-pat-123",
        )
