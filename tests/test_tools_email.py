from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import respx

from shippy.store import connect
from shippy.tools_email import EmailError, send_email

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


@respx.mock
def test_live_contract() -> None:
    token_route = respx.post(GMAIL_TOKEN_URL).respond(json={"access_token": "ya29-fake-access"})
    send_route = respx.post(GMAIL_SEND_URL).respond(json={"id": "18f0000000000000000"})

    result = send_email(
        to="ops@example.com",
        subject="Refund window exception",
        body="The SOP allows a 30-day refund window.",
        client_id="fake-client-id",
        client_secret="fake-client-secret",
        refresh_token="fake-refresh-token",
    )

    token_request = token_route.calls.last.request
    assert token_request.method == "POST"
    assert str(token_request.url) == GMAIL_TOKEN_URL
    form = parse_qs(token_request.content.decode("utf-8"))
    assert form["grant_type"] == ["refresh_token"]
    assert form["client_id"] == ["fake-client-id"]
    assert form["client_secret"] == ["fake-client-secret"]
    assert form["refresh_token"] == ["fake-refresh-token"]

    send_request = send_route.calls.last.request
    assert send_request.method == "POST"
    assert str(send_request.url) == GMAIL_SEND_URL
    assert send_request.headers["Authorization"] == "Bearer ya29-fake-access"
    raw = json.loads(send_request.content)["raw"]
    message = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert message == (
        "To: ops@example.com\r\n"
        "Subject: Refund window exception\r\n"
        "\r\n"
        "The SOP allows a 30-day refund window."
    )
    assert result == {
        "mode": "live",
        "message_id": "18f0000000000000000",
        "message_ref": "gmail:18f0000000000000000",
    }
    assert "fake-refresh-token" not in str(result)


@respx.mock
def test_fallback_outbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)

    result = send_email(
        to="ops@example.com",
        subject="Refund window exception",
        body="The SOP allows a 30-day refund window.",
        db_path=tmp_path / "email.db",
    )

    assert result["mode"] == "fallback"
    assert result["message_ref"].startswith("local:")
    conn = connect(tmp_path / "email.db")
    try:
        row = conn.execute(
            "SELECT recipient, subject, body, mode FROM outbox WHERE message_ref = ?",
            (result["message_ref"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["recipient"] == "ops@example.com"
    assert row["subject"] == "Refund window exception"
    assert row["body"] == "The SOP allows a 30-day refund window."
    assert row["mode"] == "fallback"


@respx.mock
def test_required_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)

    with pytest.raises(EmailError, match="to is required"):
        send_email(to="", subject="s", body="b", db_path=tmp_path / "email.db")
    with pytest.raises(EmailError, match="subject is required"):
        send_email(to="ops@example.com", subject="  ", body="b", db_path=tmp_path / "email.db")
    with pytest.raises(EmailError, match="body is required"):
        send_email(to="ops@example.com", subject="s", body="", db_path=tmp_path / "email.db")
    with pytest.raises(EmailError, match="to is required"):
        send_email(to=" ", subject="s", body="b", client_id="id", client_secret="c", refresh_token="r")
