# Validation - Phase 6: Slack and Gmail adapters

## Definition of done

- [x] `messages` and `outbox` tables exist in SQLite, created idempotently by `store.connect`.
- [x] Both new tables refuse updates and deletes.
- [x] `insert_message` writes a fallback Slack row and `insert_outbox` writes a fallback email row.
- [x] Live `send_message` matches Slack's `chat.postMessage` schema under `respx`, with no network.
- [x] Fallback `send_message` lands a `messages` row with no `SLACK_BOT_TOKEN`.
- [x] Live `send_email` matches Gmail's token-exchange and send schemas under `respx`, with no network.
- [x] Fallback `send_email` lands an `outbox` row with no Google OAuth variables.
- [x] A real SQLite read-back shows the fallback email row with its recipient, subject, and body.
- [x] Missing required arguments raise `MessageError` or `EmailError`.
- [x] `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py` passes.
- [x] `uv run ruff check .` is clean.
- [x] The phase guide exists and the README table marks phase 6 done.
- [x] The phase 4 and phase 6 roadmap boxes are ticked with verify-result lines.
- [x] No phase 0-5 guides, corpus JSON, or `docker-compose.yml` changed.

## Gates

1. Import smoke: `uv run python -c "import shippy; from shippy import tools_slack, tools_email"`
2. Phase tests: `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py`
3. Full suite: `uv run pytest`
4. Lint: `uv run ruff check .`
5. Outbox proof: run one fallback `send_email` against a temp database, then read the row back with the `sqlite3` CLI or Python and show its columns.

## Run procedure

1. Run gates 1-4.
2. Run gate 5 and save the printed row outside the worktree as proof.
3. Paste the real pytest output into the final summary and the status line.
4. Tick every passed box in this file and in `plan.md`.

## Evidence

- Phase tests: `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py` - 7 passed, 2026-10-19.
- Full suite: `uv run pytest` - 59 passed, 2026-10-19.
- Lint: `uv run ruff check .` - clean, 2026-10-19.
- Outbox proof: fallback `send_email` landed row id 1, ref `local:dcada2bf...`, recipient `ops@example.com`, subject `Refund window exception`, body `The SOP allows a 30-day refund window.`, mode `fallback`.

## Failure triage

| Failure | Likely cause | Action |
|---|---|---|
| Live Slack test sends no auth header | Token parameter not threaded to `httpx.post` | Pass `Authorization: Bearer` in the live helper. |
| Gmail raw message fails the base64 check | Standard base64 used instead of base64url | Use `urlsafe_b64encode` and strip padding per RFC 822 raw rules. |
| Fallback test inherits a real token | Credential env var leaked from the shell | `monkeypatch.delenv` every variable that selects live mode. |
| Outbox row missing | `insert_outbox` not called or wrong table name | Check the schema string and the helper's INSERT. |
| Second connect crashes on triggers | Triggers redefined without `IF NOT EXISTS` | Keep `CREATE TRIGGER IF NOT EXISTS` like `run_events`. |
| respx test hits the network | `@respx.mock` missing or route URL mismatch | Decorate the test and pin the exact provider URL. |
| ruff flags a new module | Import order or typing style drift | Match `tools.py`: `from __future__ import annotations`, stdlib, third-party, `shippy` groups. |

## Merge criteria

- [x] All gates pass.
- [x] Tests cover both modes of both adapters.
- [x] Proof in the final summary includes the real pytest output and the outbox row read-back.
- [x] PR is open, ready for review, and prints `draft: no`.
- [x] The guide matches the four questions and the README row is done.
