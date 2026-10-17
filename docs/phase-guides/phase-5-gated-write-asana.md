# Phase 5: Gated write, audit log, Asana

## What problem this phase solves

Phases 0-4 answer questions.
They never change anything in the world.
The operations team also needs Shippy to create work items after a person says yes.

A write needs three guards.
State means the run sits in a known phase.
Approval means a person approves before the write happens.
Proof means every transition lands in an append-only log.

This phase adds all three guards.
It also adds the first write target, Asana.

**Asana** is a task tracking service.
A **PAT** (Personal Access Token) is a secret string that proves our identity to the Asana API.
An **append-only** table accepts new rows and refuses updates and deletes.

## The one-sentence version

A workflow run waits in `pending_approval`, an approve call executes `create_task` and writes one audit event per transition, and `GET /runs/{id}` replays the whole trail.

## What we built

| Piece | File | Job |
|---|---|---|
| Audit store | `shippy/store.py` | SQLite in WAL mode, append-only `run_events`, helpers for runs, events, and tasks. |
| State machine | `shippy/workflow.py` | Start, approve, reject, replay. One event per transition. |
| Task tool | `shippy/tools.py` | `create_task` in two modes, live Asana or SQLite fallback. |
| Routes | `shippy/routes.py` | Four new endpoints in `create_workflow_router`. |
| App wiring | `shippy/app.py` | API-key gate now covers `/workflows` and `/runs`. |
| Tests | `tests/test_workflow.py`, `tests/test_tools_task.py` | 16 offline tests. |
| Spec | `specs/2026-10-16-phase-5-gated-write/` | Plan, requirements, validation. |

### The four new endpoints

| Method | Path | Auth | Returns |
|---|---|---|---|
| POST | `/workflows/run` | API key required | A new run in `pending_approval`. |
| POST | `/workflows/{id}/approve` | API key required | The run ends `completed` with a created task. |
| POST | `/workflows/{id}/reject` | API key required | The run ends `rejected`. |
| GET | `/runs/{id}` | API key required | The run status and its full event trail. |

### The run lifecycle

Every run starts in `pending_approval`.
Only two actions can move it.

| From | Action | To | Event written |
|---|---|---|---|
| (new run) | start | `pending_approval` | `run_created` |
| `pending_approval` | approve, task lands | `approved`, then `completed` | `approved`, then `task_created` |
| `pending_approval` | approve, task fails | `failed` | `failed` |
| `pending_approval` | reject | `rejected` | `rejected` |

Any other move answers HTTP 409.
An unknown run id answers 404.
An action other than `create_task` answers 400.

### The two task modes

| Mode | Target | Used when |
|---|---|---|
| Live | Real Asana API | `.env` has `ASANA_PAT` |
| Fallback | Local `tasks` table | No PAT (tests, CI, demos) |

Both modes share one signature and one result shape, `{mode, task_id, task_ref}`.
The live path sends `POST https://app.asana.com/api/1.0/tasks` with a `Bearer` token.
A `respx` test pins that request shape. respx is a test library that fakes HTTP requests.

## Why it is built this way

**Append-only by trigger.**
SQLite has no native append-only flag.
Two triggers raise an abort on any `UPDATE` or `DELETE` of `run_events` rows.
The audit trail can only grow.

**WAL mode.**
`PRAGMA journal_mode=WAL` lets readers work while a writer appends.
Each connection sets it in `store.connect`.

**Approval before execution.**
`POST /workflows/run` never touches Asana.
The write happens only inside the approve call.
A person with the API key holds the gate.

**One event per transition.**
`run_events.id` increases by insertion.
Replay orders by `id`, so the trail cannot reorder.
`GET /runs/{id}` returns events as `{seq, event, detail, created_at}`.

**The fallback proves the contract without secrets.**
CI has no Asana PAT.
The fallback path lands a row in the same SQLite file.
Tests cover both modes offline.

**The same middleware, a longer prefix list.**
Phase 4 gated `/lookup` only.
`PROTECTED_PREFIXES` now holds `/lookup`, `/workflows`, and `/runs`.
`/health` stays open.

**The router style matches phase 4.**
`create_workflow_router` closes over `db_path`.
Handlers open one connection per request and close it in `finally`.
Tests inject a temp database through `get_app(db_path=...)`.

## What you can do now

Start the app with a database file:

```bash
SHIPPY_API_KEY=local-dev-key SHIPPY_DB_PATH=/tmp/shippy.db \
  uv run uvicorn shippy.app:get_app --factory --port 8000
```

Start a run. It waits for approval:

```bash
curl -s -X POST localhost:8000/workflows/run \
  -H "x-api-key: local-dev-key" \
  -H "content-type: application/json" \
  -d '{"action": "create_task", "payload": {"title": "Chase the damaged parcel claim", "description": "File the claim with the carrier.", "sop_ref": "sop-damaged-parcel-claims"}}'
```

Approve it. With no `ASANA_PAT` the task lands in SQLite:

```bash
curl -s -X POST localhost:8000/workflows/run-<id>/approve \
  -H "x-api-key: local-dev-key"
```

Replay the audit trail:

```bash
curl -s localhost:8000/runs/run-<id> -H "x-api-key: local-dev-key"
```

You get `run_created`, `approved`, and `task_created` in that order.

Reject a run instead, and the trail ends in `rejected`.
A second approve answers 409.

## The gates

Gates are proof commands.

| Gate | Command | Result |
|---|---|---|
| 1 | `uv run pytest tests/test_workflow.py tests/test_tools_task.py` | 16 passed |
| 2 | `uv run pytest` | 52 passed |
| 3 | `uv run ruff check .` | clean |
| 4 | `uv run python -c "import shippy"` | passes |
| 5 | Fallback approve run | task row lands, trail ends `completed` |
| 6 | `GET /runs/{id}` | full trail in order |

Gate 1 needs no network, no PAT, and no index.
The workflow tests inject a fake search and a temp database.

## What this unlocks

Phase 6 adds Slack and Gmail adapters.
They reuse the same dual-mode tool pattern and the same audit trail.

---
*Created: 2026-10-17*
