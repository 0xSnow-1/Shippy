# Requirements - Phase 6: Slack and Gmail adapters

## Context

Shippy answers procedural questions with citations.
Phases 0-5 are on `main`.
They give us a seeded BookStack, two Chroma collections, a citation contract, a FastAPI app, and one approved write with an audit trail.

- `shippy/tools.py` holds the dual-mode `create_task` pattern: live Asana PAT mode plus a SQLite fallback.
- `shippy/store.py` holds SQLite storage in WAL mode with `runs`, `run_events`, and `tasks` tables.
- `docs/learn_asana.md` documents the Asana contract and the two test modes.

Phase 6 is the last MVP phase.
It adds the second and third write targets: Slack and Gmail.
Each adapter follows the same dual-mode shape: a live mode that needs credentials, and a fallback mode that needs none.
Live activation stays optional.
The fallback modes prove every contract without tokens.

## Scope

### In scope

1. `shippy/tools_slack.py`: dual-mode `send_message` - live Slack mode plus a no-credential fallback.
2. `shippy/tools_email.py`: dual-mode `send_email` - live Gmail OAuth mode plus a SQLite outbox fallback.
3. `shippy/store.py`: new `messages` and `outbox` tables beside the existing ones, with insert helpers.
4. `tests/test_tools_slack.py` and `tests/test_tools_email.py`: `respx` contract tests for the live paths plus fallback-mode tests, all offline.
5. `docs/learn_gmail.md`: a short provider contract write-up, because the Gmail request shape needs documenting.
6. `docs/phase-guides/phase-6-adapters.md` and the README row.
7. Tick the phase 6 boxes in `specs/constitution/roadmap.md` after the verify gate passes.
8. Bookkeeping: tick the phase 4 boxes in the same roadmap file (phase 4 shipped but its boxes were never ticked).

### Out of scope

- Live Slack workspace or Google Cloud provisioning.
- Real Slack or Gmail credentials in tests.
- Routing the new tools through `/workflows/*` (workflow actions beyond `create_task` stay post-MVP).
- Any new HTTP surface.
- Hybrid BM25/RRF retrieval, LangGraph runner, Slack approval buttons, a CI workflow.
- Changes to phase 0-5 guides, corpus JSON files, or `docker-compose.yml`.
- A `docs/learn_slack.md` file (the Slack request shape is one POST; see decision D8).

## Decisions

**D1 - Two new tables in the same store module.**
`messages` holds fallback Slack messages.
`outbox` holds fallback emails.
Both live in the same SQLite file as `runs`, `run_events`, and `tasks`.
The schema string in `shippy/store.py` grows two `CREATE TABLE IF NOT EXISTS` blocks.

**D2 - Table shapes mirror the `tasks` table.**
`messages(id, message_ref UNIQUE, channel, text, mode, run_id, created_at)`.
`outbox(id, message_ref UNIQUE, recipient, subject, body, mode, run_id, created_at)`.
`mode` is `"live"` or `"fallback"`.
`run_id` is optional, ready for future workflow wiring.
`message_ref` follows the `task_ref` convention: `local:<hex>` in fallback, provider-prefixed in live mode.

**D3 - Append-only in spirit.**
Both new tables get the same `BEFORE UPDATE` and `BEFORE DELETE` abort triggers as `run_events`.
Outbound communication records are audit-relevant, so they can only grow.

**D4 - Dual-mode `send_message` in `shippy/tools_slack.py`.**
Signature `send_message(channel, text)`.
`SLACK_BOT_TOKEN` set means live mode.
Token empty or unset means fallback mode.
Live mode sends `POST https://slack.com/api/chat.postMessage` with `Authorization: Bearer <token>` and JSON `{"channel", "text"}`.
A response with `ok: false` raises `MessageError`.
Fallback mode inserts a row into `messages`.
Both modes return `{mode, message_id, message_ref}`.
Missing channel or text raises `MessageError`.

**D5 - Dual-mode `send_email` in `shippy/tools_email.py`.**
Signature `send_email(to, subject, body)`.
All three of `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN` set means live mode.
Any missing means fallback mode.
Live mode exchanges the refresh token for an access token at `https://oauth2.googleapis.com/token`, then sends `POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with a base64url-encoded RFC 822 message in `{"raw"}`.
One live path only; there is no access-token shortcut.
Fallback mode inserts a row into `outbox`.
Both modes return `{mode, message_id, message_ref}`.
Missing to, subject, or body raises `EmailError`.

**D6 - No new HTTP surface.**
The roadmap's phase 6 slice asks for tools, store tables, and tests only.
The tools stay importable modules.
Wiring them into `/workflows/*` is a future phase.

**D7 - `.env.example` already carries every variable name.**
`SLACK_BOT_TOKEN`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN` are already listed.
No edit is needed.
`SLACK_APP_TOKEN` stays for the post-MVP Socket Mode backlog.

**D8 - `docs/learn_gmail.md` yes, `docs/learn_slack.md` no.**
The Gmail live path has two steps and a base64url encoding rule.
That shape genuinely needs a short write-up in the house style of `docs/learn_asana.md`.
The Slack live path is one well-known POST; the `respx` contract test pins it.

**D9 - Offline tests only.**
Live paths run under `respx`, which fakes HTTP and blocks the network.
Fallback paths use a temp SQLite file and `monkeypatch.delenv` for every credential variable.
No test opens Chroma or calls a model.

**D10 - Exception naming matches the house pattern.**
`tools.py` defines `TaskError`.
`tools_slack.py` defines `MessageError`.
`tools_email.py` defines `EmailError`.

## Divergence from the brief

None on scope.
One tool-name substitution: the brief says to open the PR with `gh-axi`.
No `gh-axi` binary resolves in this session.
Plain `gh`, the same GitHub CLI, does the same job with no new dependency.

## Deliverable files

- `shippy/store.py` (edited: `messages`, `outbox`, insert helpers)
- `shippy/tools_slack.py` (new)
- `shippy/tools_email.py` (new)
- `tests/test_tools_slack.py` (new)
- `tests/test_tools_email.py` (new)
- `docs/learn_gmail.md` (new)
- `docs/phase-guides/phase-6-adapters.md` (new)
- `docs/phase-guides/README.md` (edited, phase 6 row)
- `specs/constitution/roadmap.md` (edited, phase 4 and phase 6 boxes)
- `specs/2026-10-19-phase-6-adapters/` (this spec)

## Open questions

- [ ] Should `send_message` and `send_email` join the workflow action set (`send_message`, `send_email` next to `create_task`)?
  Resolve when a runner needs an approved notification action.
- [ ] Should the Gmail live path cache the access token between calls?
  Resolve when a live demo hits Google's refresh-token rate limits.
