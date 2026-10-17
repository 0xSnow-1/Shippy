# Plan - Phase 5: Gated write, audit log, Asana

> Numbered task groups. Each group holds `- [ ]` items and ends with one `Verify:` line.

## Group 1: Write the three spec files

- [x] Create `specs/2026-10-16-phase-5-gated-write/requirements.md`
- [x] Create `specs/2026-10-16-phase-5-gated-write/validation.md`
- [x] Create `specs/2026-10-16-phase-5-gated-write/plan.md` (this file)
- [x] Verify: All three spec files exist and are readable.

## Group 2: Read the interfaces this phase builds on

- [x] Read `shippy/app.py` and `shippy/routes.py` for the phase 4 wiring and middleware
- [x] Read `docs/learn_asana.md` for the Asana request contract and the two test modes
- [x] Confirm `get_app()` signature and the `PROTECTED_PREFIX` check
- [x] Verify: The interfaces are known and phase 5 can reuse them without change.

## Group 3: Implement audit storage

- [x] Create `shippy/store.py` with a connection helper that sets WAL mode
- [x] Create `runs`, `run_events`, and `tasks` tables, idempotent
- [x] Make `run_events` append-only with UPDATE and DELETE triggers
- [x] Add `append_event(conn, run_id, event, detail)` and `read_events(conn, run_id)` in insertion order
- [x] Verify: A scratch run appends three events, reads them back in order, and a `DELETE` attempt fails.

## Group 4: Implement dual-mode `create_task`

- [x] Create `shippy/tools.py` with `create_task(title, description, project, sop_ref)`
- [x] Live mode: `POST https://app.asana.com/api/1.0/tasks`, `Bearer` auth, JSON `data.name`, `data.notes`, `data.projects`
- [x] Fallback mode: insert a row into `tasks` when `ASANA_PAT` is empty
- [x] Both modes return `{mode, task_id, task_ref}` with no PAT in any message
- [x] Verify: `uv run python -c "from shippy.tools import create_task"` succeeds and a fallback call lands a row.

## Group 5: Implement the workflow state machine

- [x] Create `shippy/workflow.py` with start, approve, reject, and replay functions
- [x] Start creates the run as `pending_approval` and appends `run_created`
- [x] Approve moves `pending_approval` -> `approved`, executes `create_task`, appends `approved` then `task_created`, ends `completed`
- [x] Reject moves `pending_approval` -> `rejected` and appends `rejected`
- [x] Wrong state returns a conflict; unknown run id returns not found
- [x] Replay returns a run's events in insertion order
- [x] Verify: A scratch start/approve/reject cycle writes one event per transition.

## Group 6: Wire the HTTP surface

- [x] Add `POST /workflows/run`, `POST /workflows/{id}/approve`, `POST /workflows/{id}/reject` to `shippy/routes.py`
- [x] Add `GET /runs/{id}` to `shippy/routes.py`
- [x] Protect `/workflows` and `/runs` with the existing API-key middleware in `shippy/app.py`
- [x] Thread a `db_path` argument through `get_app()` so tests can inject a temp database
- [x] Verify: `uv run python -c "from shippy import app; app.get_app()"` succeeds.

## Group 7: Add the tests

- [x] Create `tests/test_workflow.py`: start returns `pending_approval`, approve lands a fallback task, reject ends rejected, replay returns the full trail in order, wrong key returns 401, unknown id returns 404, double approve returns 409, WAL and append-only enforced
- [x] Create `tests/test_tools_task.py`: `respx` live contract pinned to Asana's schema, fallback lands a row in SQLite with no network
- [x] Keep every test offline: fake search, temp database, `respx`, monkeypatched env
- [x] Verify: `uv run pytest tests/test_workflow.py tests/test_tools_task.py` passes.

## Group 8: Full gates

- [x] `uv run pytest` full suite passes
- [x] `uv run ruff check .` is clean
- [x] `uv run python -c "import shippy"` passes
- [x] Verify: All three commands return exit code 0.

## Group 9: Phase guide and README

- [x] Write `docs/phase-guides/phase-5-gated-write-asana.md` with the four questions
- [x] Mark the phase 5 row done in `docs/phase-guides/README.md`
- [x] Verify: The guide exists and the README table lists phases 0-6 with 0-5 done.

## Group 10: Tick boxes, commit, pull request

- [x] Tick every passed item in this plan and in `validation.md`
- [x] Tick the phase 5 boxes in `specs/constitution/roadmap.md`
- [x] Commit on `phase5-gated-write`, push it, open a ready-for-review PR
- [x] Confirm the PR prints `draft: no`
- [x] Verify: PR is open, not a draft, and the `done:` status line carries its URL.
