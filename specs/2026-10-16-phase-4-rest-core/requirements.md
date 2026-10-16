# Requirements - Phase 4: REST core

## Context

Shippy answers procedural questions with citations.
Phase 3 built retrieval, the answer composer, and the citation contract:

- `shippy/retrieve.py`: `search_sop(query, collection, k, floor) -> SearchResult`, status `ok` or `no_match`.
- `shippy/compose.py`: `compose(query, chunks, provider) -> Answer`; `MockLLM` and `BedrockLLM`.
- `shippy/validate.py`: `validate(result, answer) -> ValidationResult`; verbatim quote check, version-conflict refusal, no_match refusal.

Phase 3 lives on branch `phase3-retrieval` (PR #2), not on `main`.
Phase 4 stacks on that branch so it reuses the real modules.
The captain's brief assumed phases 0-3 were on `main`.
That assumption is wrong for phase 3, so phase 4 branches from `phase3-retrieval`.

Phase 4 adds the HTTP surface: a FastAPI app exposing `POST /lookup` behind an API key, and an open `GET /health`.

## Scope

### In scope

1. `shippy/app.py`: FastAPI app factory `get_app`, API-key middleware on `/lookup`, open `GET /health`.
2. `shippy/routes.py`: `POST /lookup` wiring retrieval, composition, and validation.
3. Reuse of phase 3 modules: `retrieve`, `compose`, `validate`.
4. A no_match refusal that still lists the closest source pages.
5. `tests/test_lookup.py`: wrong key (401), cited answer with source ID and verbatim quote, unanswerable refusal with source links, version-conflict refusal, open health.
6. Phase guide and README update.

### Out of scope

- New retrieval or contract logic; phase 3 owns it.
- Gated write, audit log, Asana (phase 5).
- Slack or Gmail (phase 6).
- Hybrid BM25/RRF retrieval (post-MVP backlog).
- Any HTTP surface beyond `/lookup` and `/health`.
- Changes to phase 0-3 guides, corpus JSON, or `docker-compose.yml`.

## Decisions

**D1 - Reuse, do not duplicate, phase 3.**
`app.py` and `routes.py` call the existing `retrieve`, `compose`, and `validate` modules.
No new retrieval or contract code.

**D2 - App factory.**
`shippy.app:get_app()` builds the app on demand.
It takes optional `search`, `provider`, and `api_key` arguments.
Tests inject a fake search and a `MockLLM`.

**D3 - Auth scope.**
The API-key middleware gates paths under `/lookup` only.
`GET /health` answers without a key.
The key comes from `SHIPPY_API_KEY`.

**D4 - Retrieval from `sops` only.**
The route opens the `sops` collection and calls `search_sop`.
The `clients` collection stays un-routed, as phase 3 decided.

**D5 - Answer shape.**
A grounded answer returns `{answer, quote, proposed_action, source_id, source_links}`.
A refusal returns `{answer: "", quote: "", proposed_action: "none", refused: true, reason, source_links}`.
Refusals use HTTP 200 because they are correct outcomes, not server faults.

**D6 - no_match still lists sources.**
`search_sop` hides chunks above the relevance floor.
On `no_match` the route re-queries with a permissive floor.
The refusal links to the closest pages for the reader.

**D7 - Provider default and injection.**
The live app defaults to `BedrockLLM`.
Tests inject `MockLLM` with canned JSON, so the suite needs no network or credentials.

**D8 - Offline tests.**
`tests/test_lookup.py` injects a fake search over fixed chunks.
It never opens Chroma and never calls a model.

## Divergence from the brief

The brief said to open the PR against `main`.
Phase 3 is unmerged, so phase 4 stacks on `phase3-retrieval` and targets `main`.
The phase 4 diff is clean once phase 3 merges.

## Deliverable files

- `shippy/app.py`
- `shippy/routes.py`
- `tests/test_lookup.py`
- `docs/phase-guides/phase-4-rest-core.md`
- `docs/phase-guides/README.md` (edited)

## Open questions

- [ ] Should phase 4 own a live `GET /health` readiness check on the index?
  Resolve when a load balancer needs it.
