# Validation - Phase 4: REST core

## Definition of done

- [x] `shippy.app:get_app()` returns a FastAPI app.
- [x] The API-key middleware gates `/lookup` only.
- [x] `GET /health` returns 200 without a key.
- [x] `POST /lookup` with a wrong key returns 401.
- [x] `POST /lookup` with the right key returns a cited answer with source ID and verbatim quote.
- [x] An unanswerable question returns a refusal with source links.
- [x] A version conflict returns a refusal with source links.
- [x] Retrieval uses the `sops` collection only.
- [x] The route reuses the phase 3 `retrieve`, `compose`, and `validate` modules.
- [x] `uv run pytest tests/test_lookup.py` passes.
- [x] The phase guide is written and the README is updated.
- [x] No phase 0-3 guides, corpus JSON, or `docker-compose.yml` are changed.

## Gates

1. Import smoke: `uv run python -c "from shippy import app; app.get_app()"`
2. Tests: `uv run pytest tests/test_lookup.py -v`
3. Full suite: `uv run pytest`
4. Lint: `uv run ruff check .`

## Run procedure

1. Run gates 1-4.
2. Start the app: `SHIPPY_API_KEY=local-dev-key uv run uvicorn shippy.app:get_app --factory --port 8000`.
3. Prove with `curl`: wrong key (401), health (200), unanswerable (refusal with source links).
4. Prove the cited answer against the real index with a mock provider.

## Evidence

- `uv run pytest tests/test_lookup.py` -> `5 passed`.
- `uv run pytest` -> `36 passed`.
- `uv run ruff check .` -> clean.
- Wrong key -> `401 {"error":"unauthorized"}`.
- Unanswerable -> `refused: true`, `reason: "no matching SOP found"`, three source links.
- Cited answer -> `source_id: "sop-damaged-parcel-claims"` with a verbatim quote.

## Merge criteria

- [x] All gates pass.
- [x] Tests cover the required cases.
- [x] Proof in the final summary includes the pytest output with the 401 and the cited answer.
- [x] The guide matches the existing style and the README table is correct.
