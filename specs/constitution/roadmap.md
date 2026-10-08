# Roadmap

High-level implementation order in very small phases for Shippy.

Each phase is sized to 1-3 days and ends with a verification command.

Each phase is a task list.
The verify box is the last item.
Tick the verify box only when the verify command passes.

Phases are sequential unless marked parallel-safe.

## Phase 0: Scaffold

- [x] `uv` environment with locked dependencies
- [x] `ruff` and `pytest` wired
- [x] Package layout for `shippy`
- [x] `.env.example` (Bedrock trio, LangSmith, API key, integration token names)
- [x] `.gitignore`
- [x] Verify: `uv run pytest` and `uv run ruff check .` pass.

## Phase 1: Self-hosted BookStack (our own Docker instance, not any company's)

- [ ] Pinned BookStack Docker image
- [ ] Idempotent seed script (15-20 fake e-commerce SOPs with versions, 5-10 fake client profiles)
- [ ] Planted traps in the seed data: one stale SOP, one conflicting pair, one keyword decoy, one unanswerable question
- [ ] Our own API token, minted by us as instance admin

No company system is touched anywhere in this project.
Every integration targets an account or instance we control.

- [ ] Verify: `docker compose up` then `curl -H "Authorization: Token $ID:$SECRET" localhost:8080/api/pages` returns seeded pages.

## Phase 2: SOP ingestion

- [ ] Pull pages via BookStack API
- [ ] Export Markdown
- [ ] Strip boilerplate
- [ ] Heading-based chunking
- [ ] Embed into Chroma with `sop_id`/`version`/`updated_at`
- [ ] Verify: `uv run python -m shippy.ingest sops` prints chunk count; stored chunks round-trip with metadata.

## Phase 3: Client corpus

- [ ] Ingest client profiles into a second Chroma collection with `client_id` metadata
- [ ] Verify: both collections list non-zero counts.

## Phase 4: Hybrid retriever

- [ ] BM25 + dense + RRF fusion
- [ ] Source-aware across both collections
- [ ] Returns source metadata
- [ ] Verify: `uv run pytest tests/test_retrieve.py` - known queries return expected source IDs.

## Phase 5: Citation contract

- [ ] Verbatim-quote validator (substring check)
- [ ] Confidence threshold
- [ ] Version-conflict refusal
- [ ] Verify: `uv run pytest tests/test_citation.py` - pass, missing-quote, and conflict-refusal cases green.

## Phase 6: Golden eval set

- [ ] 20 JSONL cases: expected source, expected refusal, expected routing
- [ ] Offline eval runner scoring retrieval only
- [ ] B0 naive-mode flag (dense-only, no citation contract) runnable on the same eval set
- [ ] Freeze the B0 baseline number before any tuning; record it in the eval report
- [ ] k-trial loop in the runner (each case runs k times; pass rate reported per k)

Parallel-safe from phase 4 onward.

- [ ] Verify: `uv run python -m shippy.eval` prints pass rate and the frozen B0 baseline; refusal cases at 100%.

## Phase 7: API core + auth

- [ ] FastAPI app
- [ ] API-key middleware
- [ ] `POST /lookup` (retriever + citation contract)
- [ ] SSE streaming variant
- [ ] `GET /health`
- [ ] Load script: 10-20 concurrent virtual users against the API
- [ ] Verify: `curl` with wrong key returns 401; stream yields chunks incrementally; cited answer under 8s p95 measured under concurrent load, not idle.

## Phase 8: Tool loop core

- [ ] Provider interface
- [ ] `MockLLM` with canned tool calls
- [ ] `ChatBedrockConverse` wiring with bearer token
- [ ] LangSmith tracing on graph/LLM/tool spans
- [ ] Raw tool-call loop
- [ ] Verify: offline test drives retrieve → tool_call → tool_result → final answer with no network; one live smoke test traces in LangSmith.

## Phase 9: Step runner

- [ ] LangGraph graph: plan → execute → verify
- [ ] Step cap 4
- [ ] Validation gate node
- [ ] Structured logs with run ID
- [ ] Episode smoke case: one simulated-staff episode ends in a programmatic final-state check with MockLLM
- [ ] Verify: pytest asserts cap enforcement, gate blocks writes missing citations, and the episode smoke case passes.

## Phase 10: Asana adapter (live)

- [ ] Dual-mode `create_task`: live PAT mode + SQLite fallback
- [ ] respx contract test pinned to Asana's schema
- [ ] Fault-profile mode shared by all adapters (env var selects: delay, HTTP error, empty body, schema break)

Implementation follows `docs/learn_asana.md` (read it first).

- [ ] Verify: `uv run pytest tests/test_tools_task.py` - both modes pass; one live task lands in your scratch project.

## Phase 11: Slack (live) + approval flow

- [ ] Create the free workspace and app (guided steps in README: manifest, Socket Mode, tokens)
- [ ] Build the Bolt connector
- [ ] Build the Block Kit approval message
- [ ] Handle approve/reject to resume the run

Parallel-safe with phase 10.

- [ ] Verify: manual round-trip - question in Slack, cited answer, button click, gate passes.

## Phase 12: Gmail adapter (live)

- [ ] Dual-mode `send_email`: live OAuth + outbox fallback
- [ ] Google Cloud project pre-provisioned by you
- [ ] `scripts/gmail_auth.sh` handles the weekly Testing-mode re-auth
- [ ] respx contract test
- [ ] Verify: `uv run pytest tests/test_tools_email.py` green; one live test email arrives in your inbox.

## Phase 13: Audit log + /runs/{id}

- [ ] Append-only `run_events` table
- [ ] Event capture across the runner
- [ ] `GET /runs/{id}` replay
- [ ] Verify: after any run, `curl localhost:8000/runs/$ID` returns the full decision trail in order.

## Phase 14: /workflows/run E2E

- [ ] Workflow initiation returning pending-approval handle
- [ ] REST approve/reject endpoints
- [ ] Slack approval path
- [ ] Write execution
- [ ] `scripts/demo.sh` (credential-free path end to end)
- [ ] Episode harness with simulated staff; pass^k over k=5 offline trials and k=3 live trials
- [ ] Verify: `bash scripts/demo.sh` completes clean on a fresh clone without any live tokens; live Slack round-trip also passes; episode harness prints pass^k with refusal cases at 100%.

## Phase 15: /stats + observability

- [ ] Latency percentiles
- [ ] Approval rate
- [ ] Error counts
- [ ] Per-run token cost from `run_events`
- [ ] Structured logs carry run IDs that link to LangSmith runs
- [ ] Verify: `curl localhost:8000/stats` returns populated metrics after sample traffic.

## Phase 16: CI eval gate

- [ ] GitHub Actions: ruff, pytest (respx contract tests included), eval suite on every PR
- [ ] Refusal regressions block merge
- [ ] Daily cron runs the eval suite; drift shows as a trend in the CI history
- [ ] Paired baseline check: challenger compares against frozen B0/B1 on the same cases only
- [ ] Replay command re-runs recorded `run_events` against a candidate build (shadow-style gate)
- [ ] Verify: open a test PR that breaks a golden case and confirm CI fails.

## Phase 17: Docs and ADRs

- [ ] README runbook (cold start under 5 minutes, Slack workspace setup, Gmail weekly re-auth)
- [ ] ADR: provider interface over OpenAI/Assistants
- [ ] ADR: Chroma over Pinecone
- [ ] Refresh the JD skill matrix
- [ ] Verify: follow README on a clean checkout without skipping steps.

## Phase 18: Buffer and hardening

- [ ] Edge cases
- [ ] Latency tuning
- [ ] Seed-data polish
- [ ] Token rotation checks
- [ ] Soak week: daily cron observed for drift; human baseline H recorded (n=5 timed manual BookStack tasks, self-measured)

## Dependency notes

Phases 1-3 block everything downstream.

Phase 6 can start in parallel with 4-5 once ingestion lands.

Phases 10 and 11 are parallel-safe with each other; both block phase 14.

Human-only actions: Slack workspace/app creation (phase 11), Google Cloud pre-provisioning (phase 12) - both are your clicks, scheduled ahead of their phases.

---
*Created: 2026-10-07*
*Last amended: 2026-10-07 - Streamlit phase removed; Slack live, Asana live + learn_asana.md, Gmail live OAuth, demo.sh, LangSmith, API-key auth, Shippy naming*
*Last amended: 2026-10-08 - every phase rewritten as a task list with a verify box; phase 0 ticked*
*Last amended: 2026-10-08 - constraint-key work folded in: traps (1), B0 freeze (6), load (7), episode smoke (9), fault mode (10), pass^k (14), cron/replay (16), soak + baseline H (18)*
