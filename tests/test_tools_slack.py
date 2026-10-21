from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

from shippy.store import connect
from shippy.tools_slack import MessageError, send_message

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


@respx.mock
def test_live_contract() -> None:
    route = respx.post(SLACK_POST_MESSAGE_URL).respond(
        json={"ok": True, "channel": "C0 OPS", "ts": "1729368000.000100"}
    )

    result = send_message(
        channel="#ops-returns",
        text="The damaged parcel claim SOP is approved.",
        token="xoxb-fake-token-123",
    )

    request = route.calls.last.request
    assert request.method == "POST"
    assert str(request.url) == SLACK_POST_MESSAGE_URL
    assert request.headers["Authorization"] == "Bearer xoxb-fake-token-123"
    payload = {
        "channel": "#ops-returns",
        "text": "The damaged parcel claim SOP is approved.",
    }
    assert json.loads(request.content) == payload
    assert result == {
        "mode": "live",
        "message_id": "1729368000.000100",
        "message_ref": "slack:1729368000.000100",
    }
    assert "xoxb-fake-token-123" not in str(result)


@respx.mock
def test_live_ok_false_raises() -> None:
    respx.post(SLACK_POST_MESSAGE_URL).respond(json={"ok": False, "error": "channel_not_found"})

    with pytest.raises(MessageError, match="channel_not_found"):
        send_message(channel="#missing", text="hello", token="xoxb-fake-token-123")


@respx.mock
def test_fallback_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    result = send_message(
        channel="#ops-returns",
        text="The damaged parcel claim SOP is approved.",
        db_path=tmp_path / "slack.db",
    )

    assert result["mode"] == "fallback"
    assert result["message_ref"].startswith("local:")
    conn = connect(tmp_path / "slack.db")
    try:
        row = conn.execute(
            "SELECT channel, text, mode FROM messages WHERE message_ref = ?",
            (result["message_ref"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["channel"] == "#ops-returns"
    assert row["text"] == "The damaged parcel claim SOP is approved."
    assert row["mode"] == "fallback"


@respx.mock
def test_required_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    with pytest.raises(MessageError, match="channel is required"):
        send_message(channel="", text="hello", db_path=tmp_path / "slack.db")
    with pytest.raises(MessageError, match="text is required"):
        send_message(channel="#ops", text="   ", db_path=tmp_path / "slack.db")
    with pytest.raises(MessageError, match="channel is required"):
        send_message(channel="  ", text="hello", token="xoxb-fake-token-123")
    with pytest.raises(MessageError, match="text is required"):
        send_message(channel="#ops", text="", token="xoxb-fake-token-123")
