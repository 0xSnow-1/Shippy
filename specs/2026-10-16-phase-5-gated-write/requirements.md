# Requirements - Phase 5: Gated write, audit log, Asana

## Context

Shippy answers procedural questions with citations.
Phases 0-4 are on `main`.
They give us a seeded BookStack, two Chroma collections, a citation contract, and a FastAPI app.

- `shippy/retrieve.py` runs dense search over the `sops` collection.
- `shippy/compose.py` writes the answer and the provider interface.
- `shippy/validate.py` checks the quote and refuses bad answers.
- `shippy/app.py` exposes `get_app()` with API-key middleware on `/lookup` and open `GET /health`.
- `shippy/routes.py` wires `POST /lookup`.

Phase 5 adds the first write path.
A write needs three guards: state, approval, and proof.
State means the run sits in a known phase.
Approval means a person says yes before the write happens.
Proof means every transition lands in an append-only audit log.

The write target is Asana.
`docs/learn_asana.md` explains the Asana contract: one PAT, one POST endpoint, one contract test.
A PAT is a secret string that proves our identity to the Asana API.
Live tokens stay optional.
A SQLite fallback must prove the whole contract without any token.

## Scope

### In scope

1. `shippy/store.py`: SQLite storage in WAL mode, append-only `run_events` table, helpers to append an event and to read a run's events in insertion order.
2. `shippy/workflow.py`: run lifecycle - start a run, approve it, reject it, replay its events.
3. Route wiring in `shippy/routes.py` and `shippy/app.py`: `POST /workflows/run`, `POST /workflows/{id}/approve`, `POST /workflows/{id}/reject`, `GET /runs/{id}`, behind the existing API-key middleware.
4. `shippy/tools.py`: dual-mode `create_task` - live Asana PAT mode plus SQLite fallback mode.
5. `tests/test_workflow.py` and `tests/test_tools_task.py`, offline.
6. `respx` contract test pinned to Asana's request schema.
7. Phase guide `docs/phase-guides/phase-5-gated-write-asana.md` and the README row.
8. Tick the phase 5 boxes in `specs/constitution/roadmap.md` after the verify gate passes.

### Out of scope

- Slack or Gmail adapters (phase 6).
- Live Asana token activation or any live network call in tests.
- Hybrid BM25/RRF retrieval, LangGraph runner, golden eval set, `/stats`, demo script.
- Any HTTP surface beyond `/workflows/*`, `/runs/{id}`, `/lookup`, and `/health`.
- Changes to phase 0-4 guides, corpus JSON files, or `docker-compose.yml`.
- A `--demo` CLI for live Asana runs (live activation is post-MVP).

## Decisions

**D1 - Storage module `shippy/store.py`.**
SQLite file at `data/shippy.db`, which `.gitignore` already covers.
The path is overridable with `SHIPPY_DB_PATH` and with a function argument for tests.
Every connection sets `PRAGMA journal_mode=WAL`.

**D2 - Append-only by trigger.**
`run_events` gets `BEFORE UPDATE` and `BEFORE DELETE` triggers that raise an abort error.
SQLite has no native append-only flag, so triggers enforce it.
Rows can only be inserted.

**D3 - Event row shape.**
`run_events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, event TEXT, detail TEXT, created_at TEXT)`.
`detail` holds a JSON object.
`id` is insertion order, so reading `ORDER BY id` replays the trail.

**D4 - Runs table.**
`runs(run_id TEXT PRIMARY KEY, action TEXT, payload TEXT, status TEXT, created_at TEXT, updated_at TEXT)`.
Events are the audit trail.
The runs table holds the current state only.

**D5 - State machine.**
`pending_approval` starts every run.
`approve` moves it to `approved`, then `completed` after execution, or `failed` on error.
`reject` moves it to `rejected`.
Each transition appends one event.
An approve or reject on a run that is not `pending_approval` returns HTTP 409.

**D6 - Approve executes the action.**
The MVP demo is one approved `create_task` that lands with its audit trail.
A run body carries `action` and `payload`.
Phase 5 accepts `action: "create_task"` only; other actions return HTTP 400.
Approval executes `create_task` in its configured mode and appends a `task_created` event with the task id.

**D7 - Dual-mode `create_task` in `shippy/tools.py`.**
Signature `create_task(title, description, project, sop_ref)` per `docs/learn_asana.md`.
`ASANA_PAT` set means live mode.
`ASANA_PAT` empty or unset means fallback mode.
Live mode sends `POST https://app.asana.com/api/1.0/tasks` with `Authorization: Bearer <pat>` and JSON `{"data": {"name", "notes", "projects"}}`.
`projects` is a list holding one project gid.
Fallback mode inserts a row into the `tasks` table in the same SQLite file.
Both modes return the same dict shape: `mode`, `task_id`, `task_ref`.

**D8 - Auth scope grows to the write surface.**
The phase 4 middleware protects paths by prefix.
Phase 5 protects `/lookup`, `/workflows`, and `/runs` with the same `SHIPPY_API_KEY` check.
`/health` stays open.

**D9 - Offline tests.**
Workflow tests inject a fake search into `get_app()` and a temp database path.
Tool tests use `respx` for the live path and `tmp_path` SQLite for the fallback path.
No test opens Chroma, calls a model, or touches the network.

**D10 - `GET /runs/{id}` replay.**
Response: `{"run_id", "status", "events": [{"seq", "event", "detail", "created_at"}]}`.
`seq` is the row id.
Events arrive in insertion order.
An unknown run id returns HTTP 404.

**D11 - learn_asana drift noted, not followed blindly.**
`docs/learn_asana.md` names `src/shippy/tools/task.py` and a `--demo` flag.
This repo uses a flat `shippy/` package and ships no live CLI.
The tool lives at `shippy/tools.py`.
The demo flag stays post-MVP with live activation.

## Divergence from the brief

None on scope.
One tool-name substitution: the brief says to open the PR with `gh-axi`.
No `gh-axi` binary resolves in this session.
Plain `gh`, the same GitHub CLI, does the same job with no new dependency.

## Deliverable files

- `shippy/store.py`
- `shippy/workflow.py`
- `shippy/tools.py`
- `shippy/routes.py` (edited)
- `shippy/app.py` (edited)
- `tests/test_workflow.py`
- `tests/test_tools_task.py`
- `docs/phase-guides/phase-5-gated-write-asana.md`
- `docs/phase-guides/README.md` (edited, phase 5 row)
- `specs/constitution/roadmap.md` (edited, phase 5 boxes)
- `specs/2026-10-16-phase-5-gated-write/` (this spec)

## Open questions

- [ ] Should a rejected run keep its payload for re-submission with edits?
  Resolve when an operator asks to retry a rejected run.
- [ ] Should `GET /runs/{id}` require the API key forever, or open it for dashboards?
  Resolve when a dashboard needs it.
