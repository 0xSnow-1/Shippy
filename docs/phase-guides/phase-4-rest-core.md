# Phase 4: REST core

## What problem this solves

Phase 3 built retrieval and the citation contract.
Nothing outside the code could call them yet.
The operations team needs a network door, not a Python shell.

This phase builds that door.
It adds a FastAPI app with two endpoints.
One endpoint answers a question with a citation.
The other endpoint reports that the service is alive.

**FastAPI** is a small web framework for Python.
An **endpoint** is one URL the app answers.
**Middleware** is code that runs before every request.

## The one-sentence version

A POST to `/lookup` with a valid API key returns a cited answer or a refusal, and `/health` stays open.

## What we built

| Piece | File | Job |
|---|---|---|
| App factory | `shippy/app.py` | Builds the FastAPI app and the API-key gate. |
| Routes | `shippy/routes.py` | Wires `POST /lookup` to phase 3 and returns the JSON. |
| Tests | `tests/test_lookup.py` | Five offline tests. |
| Spec | `specs/2026-10-16-phase-4-rest-core/` | Plan, requirements, validation. |

Phase 4 adds no retrieval or contract code.
It calls the three phase 3 modules:

| Phase 3 module | What phase 4 uses it for |
|---|---|
| `shippy/retrieve.py` | `search_sop` reads the `sops` collection. |
| `shippy/compose.py` | `compose` writes `{answer, quote, proposed_action}`. |
| `shippy/validate.py` | `validate` checks the quote and the refusals. |

### The two endpoints

| Method | Path | Auth | Returns |
|---|---|---|---|
| POST | `/lookup` | API key required | A cited answer or a refusal. |
| GET | `/health` | Open | `{"status": "ok"}`. |

### The answer shape

A good answer carries five fields.

| Field | Holds |
|---|---|
| `answer` | One sentence that names the source. |
| `quote` | Text copied word for word from the source chunk. |
| `proposed_action` | A suggested next step. |
| `source_id` | The page slug, like `sop-damaged-parcel-claims`. |
| `source_links` | The wiki link to the source page. |

A refusal carries a reason and source links.

| Field | Holds |
|---|---|
| `refused` | `true`. |
| `reason` | Why the app refused. |
| `source_links` | Wiki links to the pages it considered. |

## Why it is built this way

**An app factory, not a module-level app.**
`shippy.app:get_app()` builds the app on demand.
It takes an optional `search`, `provider`, and `api_key`.
A test builds its own app and passes a fake search and a `MockLLM`.
No server starts. No index is needed. The tests stay offline.

**The API key gates only `/lookup`.**
`/health` must answer without a key.
A load balancer calls it before it knows any secret.
The middleware checks the path and lets `/health` through.
The key comes from `SHIPPY_API_KEY`.

**Phase 3 stays the single source of truth.**
Phase 4 adds no retrieval or contract logic.
It calls `search_sop`, `compose`, and `validate` as they are.
A fix to the contract lands in one place, not two.

**Retrieval is injected.**
`get_app(search=...)` takes the search function.
The live app opens the `sops` collection and calls `search_sop`.
Tests pass a small fake that returns chosen chunks.

**Dense search over `sops` only.**
The `clients` collection is indexed but not routed.
Client profiles answer a different kind of question.

**A refusal is a normal answer.**
A refusal returns HTTP 200, not an error code.
The client reads `refused` and shows the source links.
Only a spent server fault returns 5xx.

**No-match still lists sources.**
`search_sop` hides chunks above the relevance floor.
A no-match would then have no links.
The route asks again with a permissive floor.
The refusal links to the closest pages for the reader.

**The LLM provider is swappable.**
The live app uses `BedrockLLM`.
Tests inject `MockLLM` with canned JSON.
The suite needs no network and no credentials.

## What you can do now

Start the app and ask a question over HTTP.

```bash
SHIPPY_API_KEY=local-dev-key uv run uvicorn shippy.app:get_app --factory --port 8000
```

Check the open health endpoint:

```bash
curl -s localhost:8000/health
```

Ask the unanswerable question:

```bash
curl -s -X POST localhost:8000/lookup \
  -H "x-api-key: local-dev-key" \
  -H "content-type: application/json" \
  -d '{"query": "What is the payout limit for the 2026 carrier insurance claim?"}'
```

Use a wrong key and the app answers `401`.

A grounded question needs a live model.
With Bedrock credentials set, ask the happy path:

```bash
curl -s -X POST localhost:8000/lookup \
  -H "x-api-key: local-dev-key" \
  -H "content-type: application/json" \
  -d '{"query": "How do we file a carrier claim for a damaged parcel?"}'
```

## The gates

Gates are proof commands.

| Gate | Command | Result |
|---|---|---|
| 1 | `uv run pytest tests/test_lookup.py` | 5 passed |
| 2 | `uv run pytest` | 36 passed |
| 3 | `uv run ruff check .` | clean |
| 4 | Wrong key via `curl` | HTTP 401 |
| 5 | Health via `curl` | `{"status": "ok"}` |
| 6 | Unanswerable via `curl` | refusal with three source links |
| 7 | Cited answer via the real index | source id and verbatim quote |

Gate 1 needs no network and no index.
The tests inject a fake search, so they run in under a second.

## Note on the base branch

Phase 3 sits on branch `phase3-retrieval` (PR #2), not on `main`.
Phase 4 branches from that branch so it reuses the real modules.
It opens its PR against `main`.
Once phase 3 merges, the phase 4 diff is clean.

## What this unlocks

Phase 5 adds gated writes behind the same app.
It adds a workflow endpoint and an approval step.
The API-key pattern from this phase is reused there.

---
*Created: 2026-10-16*
