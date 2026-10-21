# Phase 6: Slack and Gmail adapters

## What problem this phase solves

Phase 5 creates tasks in one system: Asana.
Operations teams also need Shippy to notify people.
Notifications travel on two channels: Slack messages and email.

Both channels need the same two properties as the task tool.
A live mode talks to the real provider when credentials exist.
A fallback mode proves the whole contract with no credentials at all.

This phase adds both adapters.
It also completes the MVP finish line.

**OAuth** is a way to grant limited access without sharing a password.
An **outbox** is a local table that holds emails our tool did not send yet.
A **contract test** checks that our request matches the provider's rules.

## The one-sentence version

`send_message` posts to Slack or lands a local row, `send_email` sends through Gmail or lands an outbox row, and every path is proven offline.

## What we built

| Piece | File | Job |
|---|---|---|
| Slack tool | `shippy/tools_slack.py` | `send_message` in two modes, live Slack or SQLite fallback. |
| Email tool | `shippy/tools_email.py` | `send_email` in two modes, live Gmail OAuth or SQLite outbox fallback. |
| Store tables | `shippy/store.py` | Append-only `messages` and `outbox` tables with insert helpers. |
| Slack tests | `tests/test_tools_slack.py` | `respx` contract, fallback row, argument checks. |
| Gmail tests | `tests/test_tools_email.py` | `respx` contract for both Google endpoints, outbox row, argument checks. |
| Gmail write-up | `docs/learn_gmail.md` | The OAuth flow and the RFC 822 raw message, in the `learn_asana.md` style. |
| Spec | `specs/2026-10-19-phase-6-adapters/` | Plan, requirements, validation. |

### The four adapter contracts

| Tool | Live endpoint | Fallback table | Credential that selects live mode |
|---|---|---|---|
| `send_message` | `POST https://slack.com/api/chat.postMessage` | `messages` | `SLACK_BOT_TOKEN` |
| `send_email` | token exchange, then `POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send` | `outbox` | all three of `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` |

Both tools share the phase 5 result shape: `{mode, message_id, message_ref}`.
Fallback refs start with `local:`.
Live refs carry the provider name: `slack:<ts>` or `gmail:<id>`.

### The Gmail live path has two steps

Step one exchanges the refresh token for a short-lived access token.
Step two posts a base64url-encoded RFC 822 message to the send endpoint.
`docs/learn_gmail.md` documents both requests.

## Why it is built this way

**The same dual-mode shape as `create_task`.**
One function signature.
One result dict.
A credential variable picks the mode.
Reviewers learn the pattern once.

**Append-only tables for both fallbacks.**
`messages` and `outbox` get the same UPDATE and DELETE abort triggers as `run_events`.
Outbound communication is audit-relevant, so rows can only grow.

**One live path for Gmail.**
The tool always exchanges the refresh token.
There is no access-token shortcut to maintain.
The `respx` test pins both requests.

**No new HTTP surface.**
The roadmap slice asks for tools, tables, and tests.
Wiring the tools into `/workflows/*` can wait for a runner that needs it.

**Slack gets a code contract, Gmail gets a doc too.**
The Slack request is one well-known POST; the test pins it.
The Gmail request has two steps and an encoding rule, so `docs/learn_gmail.md` exists.

## What you can do now

Call either tool from a Python shell with no credentials.
The message lands in SQLite:

```bash
SHIPPY_DB_PATH=/tmp/shippy.db uv run python -c "
from shippy.tools_slack import send_message
print(send_message('#ops-returns', 'Claim SOP approved.'))
"
```

```bash
SHIPPY_DB_PATH=/tmp/shippy.db uv run python -c "
from shippy.tools_email import send_email
print(send_email('ops@example.com', 'Refund window', 'The SOP allows 30 days.'))
"
```

Read the rows back:

```bash
sqlite3 /tmp/shippy.db 'SELECT * FROM messages; SELECT * FROM outbox;'
```

With real credentials in `.env`, the same calls hit Slack and Gmail.
Live activation stays optional; nothing in the test suite needs a token.

## The gates

Gates are proof commands.

| Gate | Command | Result |
|---|---|---|
| 1 | `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py` | 7 passed |
| 2 | `uv run pytest` | 59 passed |
| 3 | `uv run ruff check .` | clean |
| 4 | `uv run python -c "import shippy"` | passes |
| 5 | Fallback `send_email`, then read the `outbox` row | row lands with recipient, subject, body |

Gate 1 needs no network, no tokens, and no index.
The tests use `respx` and a temp database.

## What this unlocks

The MVP is complete.
Shippy answers a question with a citation or a refusal over REST.
One approved action executes with its audit trail.
Slack and Gmail are ready for live activation when a human provisions them.

---
*Created: 2026-10-19*
