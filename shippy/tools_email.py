from __future__ import annotations

import base64
import os
import uuid
from typing import Any

import httpx

from shippy.store import connect, insert_outbox

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class EmailError(Exception):
    pass


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    db_path: str | os.PathLike[str] | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    if not to or not to.strip():
        raise EmailError("to is required")
    if not subject or not subject.strip():
        raise EmailError("subject is required")
    if not body or not body.strip():
        raise EmailError("body is required")

    if client_id is None:
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if client_secret is None:
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if refresh_token is None:
        refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()

    if client_id and client_secret and refresh_token:
        return _live_send_email(to, subject, body, client_id, client_secret, refresh_token, timeout)
    return _fallback_send_email(to, subject, body, db_path)


def _live_send_email(
    to: str,
    subject: str,
    body: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    timeout: float,
) -> dict[str, Any]:
    token_response = httpx.post(
        GMAIL_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=timeout,
    )
    token_response.raise_for_status()
    access_token = str(token_response.json()["access_token"])

    raw = base64.urlsafe_b64encode(_rfc822(to, subject, body)).decode("ascii")
    response = httpx.post(
        GMAIL_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
        timeout=timeout,
    )
    response.raise_for_status()
    gmail_id = str(response.json()["id"])
    return {"mode": "live", "message_id": gmail_id, "message_ref": f"gmail:{gmail_id}"}


def _rfc822(to: str, subject: str, body: str) -> bytes:
    return f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode()


def _fallback_send_email(
    to: str, subject: str, body: str, db_path: str | os.PathLike[str] | None
) -> dict[str, Any]:
    message_ref = f"local:{uuid.uuid4().hex}"
    conn = connect(db_path)
    try:
        message_id = insert_outbox(
            conn,
            recipient=to,
            subject=subject,
            body=body,
            mode="fallback",
            message_ref=message_ref,
        )
    finally:
        conn.close()
    return {"mode": "fallback", "message_id": str(message_id), "message_ref": message_ref}
