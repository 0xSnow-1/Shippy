# Roadmap

High-level implementation order in very small phases for Shippy.

Each phase is sized to 1-3 days and ends with a verification command.

Each phase is a task list.
The verify box is the last item.
Tick the verify box only when the verify command passes.

Phases are sequential unless marked parallel-safe.

Every phase gets a spec directory under `specs/` with `plan.md`, `requirements.md`, and `validation.md`.

## Phase 0: Scaffold

- [x] `uv` environment with locked dependencies
- [x] `ruff` and `pytest` wired
- [x] Package layout for `shippy`
- [x] `.env.example` (Bedrock trio, LangSmith, API key, integration token names)
- [x] `.gitignore`
- [x] Verify: `uv run pytest` and `uv run ruff check .` pass.

## Phase 1: Self-hosted BookStack (our own Docker instance, not any company's)

- [x] Pinned BookStack Docker image
- [x] Idempotent seed script (15-20 fake e-commerce SOPs with versions, 5-10 fake client profiles)
- [x] Planted traps in the seed data: one stale SOP, one conflicting pair, one keyword decoy, one unanswerable question
- [x] Our own API token, minted by us as instance admin

No company system is touched anywhere in this project.
Every integration targets an account or instance we control.

- [x] Verify: `docker compose up` then `curl -H "Authorization: Token $ID:$SECRET" localhost:8080/api/pages` returns seeded pages.

Verify result 2026-10-09: HTTP 200, 24 seeded pages, all five trap slugs present.

## MVP leg: phases 2-6

Five phases.
The finish line: one demo where a question via REST returns a cited answer or a refusal, and one approved `create_task` action executes with its audit trail.

### Phase 2: Dual ingestion

- [x] Pull pages from both books via BookStack API (`operations-sops`, `client-profiles`)
- [x] Export Markdown via `GET /api/pages/{id}/export/markdown`
- [x] Strip boilerplate (the export's `# Title` line)
- [x] Heading-based chunking
- [x] Embed into two Chroma collections: `sops` and `clients`
- [x] Metadata on every chunk: `sop_id`/`client_id`, `version` (`revision_count`), `updated_at`
- [x] Verify: `uv run python -m shippy.ingest` prints both chunk counts; stored chunks round-trip with metadata.

Verify result 2026-10-14: `sops: 54 chunks from 18 pages`, `clients: 18 chunks from 6 pages`,
`round-trip: 72 chunks verified with metadata`. Metadata sample holds all five keys.

### Phase 3: Retrieval, citation contract, evals

- [ ] `search_sop` contract: natural-language `query` in, top-k chunks out, `no_match` status below the relevance floor
- [ ] Dense retrieval from `sops` only (clients indexed, not routed)
- [ ] Answer composer: one LLM call, structured output `{answer, quote, proposed_action}`
- [ ] Provider interface with `MockLLM` (offline) and Bedrock live path
- [ ] Deterministic validator: verbatim substring check, version-conflict refusal, `no_match` refusal
- [ ] Refusal payload carries wiki source links
- [ ] Eval runner over the four traps plus a happy path; runs offline, no network
- [ ] Verify: `uv run pytest tests/test_contract.py` passes; `uv run python -m shippy.eval` prints a pass rate and every trap case refuses.

### Phase 4: REST core

- [ ] FastAPI app
- [ ] API-key middleware on `/lookup`
- [ ] `POST /lookup` wires retrieval plus contract
- [ ] `GET /health` stays open
- [ ] Verify: `curl` with wrong key returns 401; correct key returns a cited answer with source ID and verbatim quote; unanswerable question returns a refusal with source links.

### Phase 5: Gated write, audit log, Asana

- [ ] Append-only `run_events` table in SQLite (WAL)
- [ ] Workflow state machine: `POST /workflows/run` returns `pending_approval`; `POST /workflows/{id}/approve|reject` advances it
- [ ] Event capture on every transition
- [ ] Dual-mode `create_task`: live Asana PAT mode + SQLite fallback
- [ ] `respx` contract test pinned to Asana's schema (implementation follows `docs/learn_asana.md`)
- [ ] `GET /runs/{id}` replays the event trail in order
- [ ] Verify: `uv run pytest tests/test_workflow.py tests/test_tools_task.py` passes; a fallback-mode run lands a task; `GET /runs/{id}` returns the full trail.

### Phase 6: Slack and Gmail adapters

- [ ] Dual-mode `send_message`: live Slack mode + no-credential fallback
- [ ] Dual-mode `send_email`: live Gmail OAuth mode + SQLite outbox fallback
- [ ] `respx` contract tests for both adapters
- [ ] Live activation stays optional per adapter; fallback modes prove every contract without tokens
- [ ] Verify: `uv run pytest tests/test_tools_slack.py tests/test_tools_email.py` passes; a fallback email lands in the outbox table.

## Post-MVP backlog

Everything deferred from the original 19-phase plan.
Pick-up order is free.

### Retrieval upgrades

- [ ] BM25 + dense + RRF fusion, source-aware across both collections
- [ ] Head-to-head: hybrid vs dense-only on known queries, same contract; the numbers are printed by the test run and decide if RRF stays

### Runner and chat surfaces

- [ ] LangGraph graph: plan → execute → verify, step cap 4, wall-clock timeout, validation gate node
- [ ] Slack approval buttons (Block Kit) that resume a paused run
- [ ] `GET /workflows/{id}/status` polling payload
- [ ] `scripts/demo.sh` (credential-free path end to end)
- [ ] LangSmith tracing on graph/LLM/tool spans

### Quality and observability

- [ ] Golden eval set: 20 JSONL cases, two flags (dense-only, no-contract), three frozen baselines
- [ ] CI gate: ruff, pytest, eval suite on every PR; golden-case and unlogged-action failures block merge
- [ ] `/stats`: latency percentiles, approval rate, error counts, per-run token cost from `run_events`
- [ ] Confidence threshold on the contract, only if evals justify it

### Live activation (human actions)

- [ ] Slack workspace and app creation (manifest, Socket Mode, tokens)
- [ ] Google Cloud project + `scripts/gmail_auth.sh` weekly Testing-mode re-auth
- [ ] Live smoke tests: Slack round-trip, one live Gmail in the inbox

### Docs and hardening

- [ ] README runbook (cold start under 5 minutes, Slack setup, Gmail weekly re-auth)
- [ ] One ADR per major decision (index in `docs/decisions.md`)
- [ ] Refresh the JD skill matrix
- [ ] Defense drill: a two-sentence answer per kept component
- [ ] Edge cases, latency tuning, seed-data polish, token rotation checks

## Dependency notes

MVP phases 2-6 run in order. Each blocks the next.

Phase 3 tests run offline: `MockLLM` plus the four seeded traps.

Live credentials are optional until Live activation items; fallback modes cover every verify box.

Human-only actions: Slack workspace creation, Google Cloud provisioning - scheduled when live activation starts.

---
*Created: 2026-10-07*
*Last amended: 2026-10-07 - Streamlit phase removed; Slack live, Asana live + learn_asana.md, Gmail live OAuth, demo.sh, LangSmith, API-key auth, Shippy naming*
*Last amended: 2026-10-08 - every phase rewritten as a task list with a verify box; phase 0 ticked*
*Last amended: 2026-10-08 - constraint-key work folded in: traps (1), B0 freeze (6), load (7), episode smoke (9), fault mode (10), pass^k (14), cron/replay (16), soak + baseline H (18)*
*Last amended: 2026-10-08 - phase 13 gains `GET /runs/{id}/status` for agent status polling (JD line 13)*
*Last amended: 2026-10-09 - grilling session: SSE and load script removed (7), constraint-key extras stripped (6, 9, 10, 14, 16, 18), BM25 head-to-head added (4), B0 split into two flags (6), wall-clock timeout added (9), Phase 17 expands to ADR set + defense drill, CI blocks golden cases and log completeness (16). Decisions in `docs/decisions.md`.*
*Last amended: 2026-10-14 - MVP reconstruction: 19 phases become five MVP phases (2-6) plus post-MVP backlog; hybrid retrieval, LangGraph runner, stats, CI gate, golden set deferred; REST + SQLite approval state machine; deterministic citation contract (no confidence threshold); client corpus indexed in phase 2; three dual-mode adapters folded into phases 5-6; three-file spec per phase kept; audit events from day one.*
