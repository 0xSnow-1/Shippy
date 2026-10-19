# Plan - v1 demo runbook

> Numbered task groups. Each group holds `- [ ]` items and ends with one `Verify:` line.

## Group 1: Write the three spec files

- [x] Create `specs/2026-10-19-v1-demo/requirements.md`
- [x] Create `specs/2026-10-19-v1-demo/validation.md`
- [x] Create `specs/2026-10-19-v1-demo/plan.md` (this file)
- [x] Verify: All three spec files exist and are readable.

## Group 2: Read the interfaces the demo builds on

- [x] Read `shippy/app.py` for `get_app(search=..., provider=..., api_key=..., db_path=...)`
- [x] Read `shippy/ingest.py` for `chunk_page` and `write_collection`
- [x] Read `shippy/compose.py` for `MockLLM` and `LLMProvider`
- [x] Confirm the corpus files at `scripts/corpus/sops.json` and `scripts/corpus/clients.json`
- [x] Verify: The demo can inject every dependency through the existing factory with no app changes.

## Group 3: Probe retrieval over a corpus-built index

- [x] Build a scratch Chroma index from the corpus with real embeddings
- [x] Measure distances for the happy-path query, the unanswerable query, and the restocking trap
- [x] Confirm the restocking query retrieves both revisions of `sop-restocking-fee-current` within the relevance floor
- [x] Verify: A happy path matches within floor `1.0`, an unanswerable query lands above it, and the trap retrieves two versions of one `sop_id`.

## Group 4: Implement the demo server helper

- [x] Create `scripts/demo_app.py`
- [x] Build both collections from the committed corpus into `SHIPPY_DEMO_CHROMA`
- [x] Keep both revisions of a revised corpus page under the same `sop_id` with versions 1 and 2
- [x] Inject `MockLLM` through `get_app` unless `SHIPPY_DEMO_LLM=bedrock`
- [x] Bind the workflow database to `SHIPPY_DEMO_DB`
- [x] Print index size, LLM mode, and listen address on startup
- [x] Verify: `SHIPPY_DEMO_*` set, `uv run python scripts/demo_app.py` serves `/health`.

## Group 5: Implement the one-command demo

- [x] Create `scripts/demo.sh` with no required arguments
- [x] Put all temporary state under `mktemp -d` outside the worktree
- [x] Pick a free port, start the server, and wait for `/health`
- [x] Unset `ASANA_PAT` and `AWS_BEARER_TOKEN_BEDROCK` so the run proves the credential-free path
- [x] Stop the server and delete temp state on exit with a trap
- [x] Drive all eight proof steps over HTTP with `curl`
- [x] Print the real status code and JSON body for every step
- [x] Print one `PASS` or `FAIL` line per step and exit non-zero on any failure
- [x] Verify: `scripts/demo.sh` runs to completion and prints `DEMO PASSED (8/8 steps)`.

## Group 6: Optional live BookStack path

- [x] Add a `--bookstack` flag to `scripts/demo.sh`
- [x] Require Docker and a `.env` with `BOOKSTACK_TOKEN`, and fail with a clear message otherwise
- [x] Run `docker compose up -d`, wait for BookStack, seed the corpus, run live ingestion into the temp index
- [x] Repeat the same eight proof steps over the live data
- [x] Verify: The default path still needs no Docker and no credentials.

## Group 7: Write the README

- [x] Explain what Shippy is in a short paragraph
- [x] Document the one-command cold start
- [x] List required versus optional credentials
- [x] Document `SHIPPY_DEMO_LLM=bedrock` for the real model path
- [x] Document the live BookStack ingestion and `--bookstack`
- [x] Document the test and lint commands
- [x] Verify: A new reader can run the demo from the README alone.

## Group 8: Full gates

- [x] `scripts/demo.sh` passes 8/8 and its full output is saved outside the worktree
- [x] `uv run pytest` passes
- [x] `uv run ruff check .` is clean
- [x] `uv run python -c "import shippy"` passes
- [x] No corpus JSON, `docker-compose.yml`, or phase 0-5 behavior changed
- [x] Verify: All gates return exit code 0.

## Group 9: Tick boxes, commit, pull request

- [x] Tick every passed item in this plan and in `validation.md`
- [x] Commit on `v1-demo-runbook`, push it, open a ready-for-review PR
- [x] Confirm the PR prints `draft: no`
- [x] Verify: PR is open, not a draft, and the `done:` status line carries its URL.
