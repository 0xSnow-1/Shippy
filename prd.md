# PRD: Shippy - SOP Agent Harness

Durable decisions (mission, stack, phase order) live in `specs/constitution/`.
This document specifies behavior: what Shippy does, its contracts, and its acceptance criteria.

## Summary

Shippy is a domain-specific agent harness for an e-commerce/retail operations team.

Employees ask SOP questions and run common multi-step workflows (retrieve SOP → create Asana task → notify Slack → optionally email) through a single, auditable, production-grade service.

Human interaction happens in Slack (questions and approval buttons).
Machine interaction happens over a REST API.
A credential-free demo script proves the same flow with local fallbacks.

Solo build, soft 3-5 week target, ordered by the phases in `specs/constitution/roadmap.md`.

## Problem

Operations staff find procedures by manual search, then hand-transcribe steps into tasks and messages.

This is slow and inconsistent: people act on stale or mis-remembered SOP versions.

The expensive failure mode is an operation executed from an outdated or hallucinated SOP: incorrect changes, escalations, and rework costing more than the original task.

Without a decision log, no one can reconstruct why an agent created a task or sent a message when something goes wrong.

Shippy makes that failure mode structurally impossible: every claim is cited, every write is gated, every run is logged.

## Goals

- One reliable path from question to correct SOP to completed follow-up action.
- Every agent action logged, attributable, and reversible by a human.
- Fully reproducible locally: one command brings up all services with seeded demo data.
- Credential-free and live-integration paths share one interface, so CI proves what production ships.

## Non-goals

- General autonomous agents or open-ended task execution.
- Replacing BookStack, Asana, Slack, or Gmail.
- A first-party GUI (REST is the machine contract; Slack is the human surface).
- SOP enforcement, ChatOps, autonomous scheduling (roadmap only).
- Pinecone or other managed vector services (Chroma embedded is sufficient).

## Users and surfaces

| Surface | Who | Purpose |
|---|---|---|
| Slack | Operations staff | Ask questions, receive cited answers, approve/reject write actions with buttons |
| REST API | Backend services, scripts | `POST /lookup`, `POST /workflows/run`, `GET /runs/{id}`, `GET /runs/{id}/status`, `GET /stats`, approve/reject |
| `scripts/demo.sh` | Anyone (no credentials) | End-to-end proof of the flow using fallback modes |

## Architecture

```
Slack (Block Kit buttons) ──> shippy-slack (Bolt, Socket Mode)
                                    │
REST clients ────────────> shippy-api (FastAPI, API-key auth)
                                    │
                          Shippy harness (LangGraph, cap 4 steps)
                          ├─ retrieve_sop  ──> hybrid retriever (BM25 + dense + RRF)
                          │                        └─> Chroma: sops + clients collections
                          ├─ create_task   ──> Asana (live PAT) | SQLite fallback
                          ├─ send_slack    ──> Slack chat.postMessage
                          ├─ send_email    ──> Gmail OAuth | outbox fallback
                          ├─ LLM           ──> Bedrock Claude Haiku (MockLLM offline)
                          └─ every step    ──> SQLite run_events (append-only)
                                               LangSmith (graph/LLM/tool spans)

Compose services: shippy-api, shippy-slack, bookstack (seeded, pinned image)
```

Run state lives in SQLite (WAL mode); the API and Slack connector coordinate through it.

## Core components

### 1. Ingestion pipeline

- BookStack self-hosted in Docker; we hold the API token ("Access System API" permission).
- Pull pages, export via `GET /api/pages/{id}/export/markdown`, strip boilerplate, chunk on headings.
- Corpus A: 15-20 e-commerce/retail ops SOPs with version history.
- Corpus B: 5-10 fake client account profiles in a second Chroma collection with `client_id` metadata.
- Every chunk carries `sop_id` or `client_id`, `version`, `updated_at`.
- Re-run on schedule (GitHub Actions cron); ingestion fails loudly on format drift.

### 2. Retrieval with citation contract

- Hybrid retrieval (BM25 + dense + RRF) with source routing across both collections.
- Every claim must include source ID and a verbatim quote; the validator checks the quote is a substring of the retrieved chunk.
- Below confidence threshold, or top chunks conflict on version → refuse and link to the source document instead of answering.

### 3. Workflow tools (function calling)

| Tool | Signature (abridged) | Live target |
|---|---|---|
| `retrieve_sop` | `(query) -> cited content` | Chroma (no external target) |
| `create_task` | `(title, description, project, sop_ref)` | Asana `POST /api/1.0/tasks`, PAT in env |
| `send_slack_message` | `(channel, text, sop_ref)` | Slack `chat.postMessage` |
| `send_email` | `(to, subject, body, sop_ref)` | Gmail API, OAuth testing-mode token |

Tools are deterministic, individually unit-tested with respx against published schemas, and permission-scoped.

### 4. Step runner

- Explicit single-pass plan → execute → verify in LangGraph, maximum 4 steps.
- Any write action requires: correct SOP cited, all required fields present, target resolved, human approval.
- Approval surfaces: Slack Block Kit approve/reject buttons (primary), `POST /runs/{id}/approve` / `reject` with API key (REST).
- Approval events write to `run_events`; the executor resumes from the persisted run state.

### 5. REST API

All endpoints require `X-API-Key` (401 otherwise).

| Endpoint | Behavior |
|---|---|
| `POST /lookup` | SOP question → cited answer; SSE streaming variant emits tokens incrementally |
| `POST /workflows/run` | Initiates a workflow; returns pending-approval handle `{run_id, status: "pending_approval"}` |
| `POST /runs/{id}/approve` | Approves a pending write; resumes execution |
| `POST /runs/{id}/reject` | Rejects; run closes with rejection event |
| `GET /runs/{id}` | Full decision log: inputs, retrieved chunk IDs, plan, tool calls, approvals, outputs, LangSmith run link |
| `GET /runs/{id}/status` | Small polling payload for progress displays: `{run_id, state, step}`; callers poll during approval waits |
| `GET /health` | Liveness |
| `GET /stats` | Latency p50/p95, approval rate, error counts, per-run token cost |

### 6. Audit log

Append-only SQLite `run_events` table: `run_id`, `seq`, `ts`, `event_type`, `payload_json`.
Events cover prompt, retrieved chunk IDs, model output, tool calls, approvals, results, refusals.

### 7. Evaluation and CI

- 20 golden cases (JSONL): expected source ID, expected routing (sops vs clients), expected refusal.
- Offline mode (MockLLM + local stores) runs in GitHub Actions on every PR alongside ruff and pytest.
- Refusal-correctness regressions block merge.

### 8. Observability

- LangSmith captures graph, LLM, and tool spans for every live run.
- Structured JSON logs carry `run_id` on every line; `GET /runs/{id}` links to the LangSmith run.
- `/stats` aggregates from `run_events`.

### 9. Learning docs

`docs/learn_asana.md`: STE-inspired explainer covering PAT, respx, contract tests, and the safety rules for the Asana integration, so the builder can follow every step.
Other integrations are documented in the README.

## Integrations: liveness matrix

| Integration | Live mode | No-credential mode |
|---|---|---|
| BookStack | Self-hosted Docker (always live) | same |
| Slack | Own free workspace, Socket Mode | REST approve/reject |
| Asana | Personal free PAT + scratch project | SQLite task store |
| Gmail | Personal OAuth client, Testing status, 7-day re-auth via `scripts/gmail_auth.sh` | Outbox table |
| LLM | Bedrock Claude Haiku (`ChatBedrockConverse`, bearer token) | `MockLLM` |
| Tracing | LangSmith | No-op / local logs |

## Success metrics

| Metric | Target | How measured |
|---|---|---|
| Answer groundedness (source cited + verbatim quote) | ≥ 95% | Audit log sampling |
| Human approval rate (as-is) | ≥ 85% | Approval events / writes |
| Time-to-resolution, question → approved task | < 60s | Run timestamps |
| Refusal correctness (stale/conflicting) | 100% of 20-case eval | CI gate |
| Tool call success rate | ≥ 99% | Run logs |
| p95 lookup latency | < 8s | `/stats` |
| Zero unlogged agent actions | 0 | Completeness check |
| Cold-start demo | `docker compose up` → working stack in < 5 min | README runbook |
| Credential-free demo | `scripts/demo.sh` passes with no live tokens | CI |

## Risks and mitigations

- Hallucinated steps → citation contract + refusal threshold + CI eval gate.
- Stale chunks → version/timestamp metadata, stale chunks excluded.
- Runaway writes → step cap, approval on all writes, per-tool scope.
- Slack/Asana live paths untested in CI → respx contract tests pinned to published schemas; thin adapters.
- Gmail refresh token expires every 7 days (Testing mode) → `scripts/gmail_auth.sh` + runbook note; failure mode is a clean tool error, never a hang.
- Bedrock bearer token rotation → token only in `.env`, `.env.example` documents names; smoke test in phase 8 fails loudly.
- BookStack image drift → pinned digest, idempotent seed script, ingestion fails loudly.
- Secrets leakage → `.env` git-ignored, never logged, API keys compared with constant-time equality.

## Scope (soft target, priority order)

Week 1: phases 0-3 (scaffold, BookStack, ingestion, both corpora).
Week 2: phases 4-7 (retriever, citation, eval set, API + auth).
Week 3: phases 8-10 (tool loop + Bedrock, step runner, Asana live + learn doc).
Week 4: phases 11-14 (Slack live, Gmail live, audit log, workflow E2E + demo.sh).
Week 5: phases 15-18 (stats, CI gate, docs/ADRs, buffer).

### Explicitly deferred

- Pinecone, Angular embedding, autonomous scheduling, SOP enforcement, ChatOps.
- Google OAuth app verification (stays in Testing status for single-user operation).
- Rate limiting and multi-tenant auth (documented as future hardening).

## Definition of done

- `docker compose up` yields healthy Shippy API, Slack connector, and seeded BookStack.
- Ask a question in Slack → cited answer with verbatim quote in under 8 seconds.
- Approve a workflow with the Slack button → Asana task created in the scratch project → full trail in `GET /runs/{id}`.
- `scripts/demo.sh` completes the same flow on a fresh clone with zero live tokens.
- Eval suite green in CI: 20 golden cases, 100% correct refusals.
- README runbook + both ADRs merged; `docs/learn_asana.md` readable by the builder without outside help.

---
*Created: 2026-10-07*
*Rewritten: 2026-10-07 - from MAG-internal spec to Shippy self-hosted internal tool; references specs/constitution/ for durable decisions*
