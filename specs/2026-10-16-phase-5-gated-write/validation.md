# Validation - Phase 5: Gated write, audit log, Asana

## Definition of done

- [x] `run_events` exists in SQLite, opened in WAL mode.
- [x] `run_events` is append-only: update and delete attempts fail.
- [x] `append_event` writes a row and `read_events` returns a run's rows in insertion order.
- [x] `POST /workflows/run` returns a run id with status `pending_approval`.
- [x] `POST /workflows/{id}/approve` advances the run and lands a fallback-mode task.
- [x] `POST /workflows/{id}/reject` advances the run to `rejected`.
- [x] Every transition appends exactly one event.
- [x] `GET /runs/{id}` returns the full trail in order for the run.
- [x] Live `create_task` matches Asana's schema under `respx`, with no network.
- [x] Fallback `create_task` lands a row with no `ASANA_PAT`.
- [x] Workflow and run routes reject a wrong API key with 401.
- [x] `/health` still answers open.
- [x] `uv run pytest tests/test_workflow.py tests/test_tools_task.py` passes.
- [x] The phase guide exists and the README table is updated.
- [x] No phase 0-4 guides, corpus JSON, or `docker-compose.yml` changed.

## Gates

1. Import smoke: `uv run python -c "import shippy"`
2. App factory: `uv run python -c "from shippy import app; app.get_app()"`
3. Phase tests: `uv run pytest tests/test_workflow.py tests/test_tools_task.py`
4. Full suite: `uv run pytest`
5. Lint: `uv run ruff check .`

## Run procedure

1. Run gates 1-5.
2. Save the phase test output as proof outside the worktree.
3. Run one end-to-end scratch flow against a temp database:
   start a run, approve it, read `GET /runs/{id}`, and show the trail.
4. Paste the real pytest output, including the fallback landing and the replay, into the final summary and the status line.

## Evidence

- Phase tests: `uv run pytest tests/test_workflow.py tests/test_tools_task.py` - 16 passed, 2026-10-17.
- Full suite: `uv run pytest` - 52 passed, 2026-10-17.
- Lint: `uv run ruff check .` - clean, 2026-10-17.
- Scratch trail: start/approve/reject over TestClient; approve trail `run_created`, `approved`, `task_created`; reject trail `run_created`, `rejected`.

## Failure triage

| Failure | Likely cause | Action |
|---|---|---|
| `run_events` update succeeds | Trigger not created | Recreate schema, check `CREATE TRIGGER` idempotency. |
| WAL not active | `PRAGMA` set after table use or on wrong connection | Set `journal_mode` on every fresh connection in `connect()`. |
| Replay out of order | Ordering by timestamp instead of row id | Order by `id` ascending. |
| Live contract test sends no body | httpx client call missing `json=` | Pass the payload as `json=`, not `data=`. |
| Fallback test hits network | `ASANA_PAT` inherited from shell env | `monkeypatch.delenv("ASANA_PAT", raising=False)`. |
| Chroma opens in a test | `get_app()` without injected search | Pass `search=` and `db_path=` in every workflow test. |
| 401 missing on workflow route | Middleware prefix not extended | Check `PROTECTED_PREFIXES` covers `/workflows` and `/runs`. |
| Double approve returns 200 | State check missing | Return 409 when status is not `pending_approval`. |

## Merge criteria

- [x] All gates pass.
- [x] Tests cover both task modes and the full event trail.
- [x] Proof in the final summary includes the real pytest output.
- [x] PR is open, ready for review, and prints `draft: no`.
- [x] The guide matches the four questions and the README row is done.
