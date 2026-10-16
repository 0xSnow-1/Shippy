# Plan - Phase 4: REST core

> Numbered task groups. Each group holds `- [x]` items and ends with one `Verify:` line.

## Group 1: Write the three spec files

- [x] Create `specs/2026-10-16-phase-4-rest-core/requirements.md`
- [x] Create `specs/2026-10-16-phase-4-rest-core/validation.md`
- [x] Create `specs/2026-10-16-phase-4-rest-core/plan.md` (this file)
- [x] Verify: All three spec files exist and are readable.

## Group 2: Read phase 3 interfaces

- [x] Read `shippy/retrieve.py`, `shippy/compose.py`, `shippy/validate.py` on `phase3-retrieval`
- [x] Confirm `search_sop`, `compose`, and `validate` signatures
- [x] Confirm how `SearchResult` carries chunks and status
- [x] Verify: The interfaces are known and phase 4 can call them.

## Group 3: Implement the HTTP surface

- [x] Implement `shippy/routes.py` with `POST /lookup` wiring retrieval, compose, and validate
- [x] Implement `shippy/app.py` with `get_app()`, API-key middleware on `/lookup`, open `GET /health`
- [x] Make the search function and LLM provider injectable
- [x] Give a `no_match` refusal the closest source links
- [x] Verify: `uv run python -c "from shippy import app; app.get_app()"` succeeds.

## Group 4: Add tests

- [x] Create `tests/test_lookup.py` covering wrong key (401), cited answer with source ID and verbatim quote, unanswerable refusal with source links, version-conflict refusal, and open health
- [x] Inject a fake search and `MockLLM` so tests stay offline
- [x] Verify: `uv run pytest tests/test_lookup.py` passes.

## Group 5: Runtime proof

- [x] Run the app live and `curl` wrong key (401), health (200), and the unanswerable refusal
- [x] Show the cited answer against the real index with a mock provider
- [x] Verify: The 401, the cited answer, and the refusal all appear in the output.

## Group 6: Phase guide and README

- [x] Write `docs/phase-guides/phase-4-rest-core.md`
- [x] Mark the phase 4 row done in `docs/phase-guides/README.md`
- [x] Verify: The guide exists and the README table lists phases 0-6.
