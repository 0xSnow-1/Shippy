# Plan - Phase 6: Slack and Gmail adapters

> Numbered task groups. Each group holds `- [x]` items and ends with one `Verify:` line.

## Group 1: Write the three spec files

- [x] Create `specs/2026-10-19-phase-6-adapters/requirements.md`
- [x] Create `specs/2026-10-19-phase-6-adapters/validation.md`
- [x] Create `specs/2026-10-19-phase-6-adapters/plan.md` (this file)
- [x] Verify: All three spec files exist and are readable.

## Group 2: Read the interfaces this phase builds on

- [x] Read `shippy/tools.py` for the dual-mode `create_task` pattern
- [x] Read `shippy/store.py` for the schema string and insert helpers
- [x] Read `docs/learn_asana.md` for the house provider write-up style
- [x] Confirm `.env.example` already lists the Slack and Gmail variable names
- [x] Verify: The interfaces are known and phase 6 reuses them without change.

## Group 3: Extend the store

- [x] Add a `messages` table to the schema string in `shippy/store.py`
- [x] Add an `outbox` table to the schema string
- [x] Add append-only UPDATE and DELETE triggers for both new tables
- [x] Add `insert_message(conn, ...)` and `insert_outbox(conn, ...)` helpers in the `insert_task` style
- [x] Verify: `store.connect` on a fresh temp file creates both tables and both refuse an UPDATE.

## Group 4: Implement dual-mode `send_message`

- [x] Create `shippy/tools_slack.py` with `send_message(channel, text)`
- [x] Live mode: `POST https://slack.com/api/chat.postMessage`, `Bearer` auth, JSON `channel` and `text`, `ok: false` raises `MessageError`
- [x] Fallback mode: insert a row into `messages` when `SLACK_BOT_TOKEN` is empty
- [x] Both modes return `{mode, message_id, message_ref}`
- [x] Verify: `uv run python -c "from shippy.tools_slack import send_message"` succeeds and a fallback call lands a row.

## Group 5: Implement dual-mode `send_email`

- [x] Create `shippy/tools_email.py` with `send_email(to, subject, body)`
- [x] Live mode: refresh-token exchange at `https://oauth2.googleapis.com/token`, then `POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with a base64url RFC 822 `raw` body
- [x] Fallback mode: insert a row into `outbox` when any OAuth variable is empty
- [x] Both modes return `{mode, message_id, message_ref}`
- [x] Verify: `uv run python -c "from shippy.tools_email import send_email"` succeeds and a fallback call lands an outbox row.

## Group 6: Add the tests

- [x] Create `tests/test_tools_slack.py`: `respx` live contract pinned to Slack's schema, fallback lands a `messages` row, missing arguments raise
- [x] Create `tests/test_tools_email.py`: `respx` live contract pinned to Gmail's token and send schemas, fallback lands an `outbox` row, missing arguments raise
- [x] Keep every test offline: `respx`, `tmp_path` SQLite, `monkeypatch.delenv` for every credential variable
- [x] Verify: `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py` passes.

## Group 7: Full gates and outbox proof

- [x] `uv run pytest` full suite passes
- [x] `uv run ruff check .` is clean
- [x] `uv run python -c "import shippy"` passes
- [x] Read one fallback email row back from SQLite and show its columns
- [x] Verify: All commands return exit code 0 and the outbox row is visible.

## Group 8: Docs and bookkeeping

- [x] Write `docs/learn_gmail.md` in the `docs/learn_asana.md` style
- [x] Write `docs/phase-guides/phase-6-adapters.md` with the four questions
- [x] Mark the phase 6 row done in `docs/phase-guides/README.md`
- [x] Tick the phase 4 boxes in `specs/constitution/roadmap.md` and add its verify-result line
- [x] Tick the phase 6 boxes in `specs/constitution/roadmap.md` and add its verify-result line
- [x] Verify: The guide, the README row, and both roadmap sections are updated.

## Group 9: Cleanup, commit, pull request

- [x] Run the no-comments, unslop, and single-paved-path cleanup pass
- [x] Tick every passed item in this plan and in `validation.md`
- [x] Commit on `phase6-adapters`, push it, open a ready-for-review PR
- [x] Confirm the PR prints `draft: no`
- [x] Verify: PR is open, not a draft, and the `done:` status line carries its URL.
