from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from shippy.store import connect, insert_message

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


class MessageError(Exception):
    pass


def send_message(
    channel: str,
    text: str,
    *,
    db_path: str | os.PathLike[str] | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    if not channel or not channel.strip():
        raise MessageError("channel is required")
    if not text or not text.strip():
        raise MessageError("text is required")
    if token is None:
        token = os.environ.get("SLACK_BOT_TOKEN", "").strip()

    if token:
        return _live_send_message(channel, text, token, timeout)
    return _fallback_send_message(channel, text, db_path)


def _live_send_message(channel: str, text: str, token: str, timeout: float) -> dict[str, Any]:
    response = httpx.post(
        SLACK_POST_MESSAGE_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel, "text": text},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise MessageError(f"slack error: {data.get('error', 'unknown')}")
    ts = str(data["ts"])
    return {"mode": "live", "message_id": ts, "message_ref": f"slack:{ts}"}


def _fallback_send_message(
    channel: str, text: str, db_path: str | os.PathLike[str] | None
) -> dict[str, Any]:
    message_ref = f"local:{uuid.uuid4().hex}"
    conn = connect(db_path)
    try:
        message_id = insert_message(
            conn,
            channel=channel,
            text=text,
            mode="fallback",
            message_ref=message_ref,
        )
    finally:
        conn.close()
    return {"mode": "fallback", "message_id": str(message_id), "message_ref": message_ref}
