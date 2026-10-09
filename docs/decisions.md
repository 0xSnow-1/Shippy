# Decision Record

Every major design decision in Shippy has an owner and a verdict here.
This file exists so no decision is ever unowned again.
It closes the grilling session of 2026-10-09.

## Standing principle

No complexity unless needed.
A component stays only while it earns its place.
The eval suite names when a simple default breaks.
Then that one component upgrades, nothing else.

## Ownership table

| Component | Originally chosen by | Final verdict | Owner now |
|---|---|---|---|
| Bedrock Claude Haiku + provider interface | Builder (no OpenAI key, working credentials) | Keep | Builder |
| BM25 + dense + RRF hybrid retrieval | Builder | Keep, pending head-to-head | Builder runs the test |
| Approval gate on every write | Agent | Keep, eyes open: friction known, reason known | Builder |
| LangGraph step runner | Agent (false JD claim in tech-stack.md) | Keep | Builder, reasons corrected |
| SQLite WAL + append-only audit log | Agent | Keep, builder writes the code | Builder |
| CI golden-case gate | Agent | Keep, builder writes the workflow | Builder |
| MockLLM + offline mode | Agent | Keep | Builder, defended via ADR |
| 4-step cap | Agent | Keep | Builder, defended via drill |
| Slack Bolt + Socket Mode | Agent (partly forced) | Keep, agent writes the connector | Builder defends it |
| Gmail live OAuth | Agent (JD-forced) | Keep live, build last | Builder |
| LangSmith tracing | Builder (existing keys) | Keep | Builder |
| Chroma, BookStack, FastAPI | Job description (natural) | Keep | Builder's ignore-JD rule |
| Project name Shippy | Agent | Keep | Builder |
| SSE streaming | Agent (false JD claim) | Cut from v1 | Builder's verdict |
| Constraint-key extras (simulator, pass^k, faults, load, soak, replay, human baseline, k-loop) | Agent (research program) | Cut to spine, doc kept as future-work | Builder's verdict |
| B0 baseline design (two variables at once) | Agent | Split into two flags | Builder's verdict |
| Slack workspace + Asana PAT setup | Human-only action | Set up now | Builder's clicks |

## Five LLM-implementation defaults

These five decisions are forced by the PRD.
They were examined on 2026-10-09 and skipped under the standing principle.
Each default is owned, and each has an upgrade trigger.
The eval suite is the trigger source.

### D1 - Answer path: fixed pipeline

Default: retrieve once, one LLM call composes from those chunks, validator checks.
No agentic re-retrieval in `POST /lookup`.
PRD: `prd.md` `POST /lookup` row.

Upgrade trigger: golden cases show vague phrasing failing at a rate we will not accept.
Upgrade to: follow-up `retrieve_sop` calls inside the step cap.

### D2 - Plan shape: single-pass plan

Default: the LLM emits the whole tool plan in one shot.
The human approves that plan.
Execution runs with no new LLM calls.
PRD: single-pass plan, execute, verify, maximum 4 steps.

Upgrade trigger: tool results routinely invalidate the plan, and the E2E demo shows it.
Upgrade to: iterative per-step planning; the gate pauses before the first write.

### D3 - Citation mechanism: generate then validate

Default: prompt for quotes, substring-check the output, refuse on miss.
PRD: every claim carries a source ID and a verbatim quote.

Upgrade trigger: refusals are dominated by paraphrased near-misses, not real hallucinations.
Upgrade to: schema-constrained extraction through structured output or a function call.

### D4 - Refusal threshold: retrieval scores

Default: dense, BM25, and RRF score margin plus the version-conflict rule.
Plain code, stable in CI.
PRD: below confidence threshold, or sources conflict, refuse.

Upgrade trigger: the planted decoy trap passes when it should refuse.
Upgrade to: an LLM answerability check before the gate.

### D5 - MockLLM: canned replies

Default: fixed replies keyed by input.
Tests prove code paths: validator, gate, refusal logic, audit rows.
Phase 6 evals score retrieval only.
PRD: offline mode runs in GitHub Actions on every PR.

Upgrade trigger: live smoke tests fail while CI stays green.
Upgrade to: fixture-driven per-case replies, then a non-blocking live canary.

## PRD gaps: one-line defaults

The PRD does not define these.
Each has a default and a time.

1. Confidence threshold value: set in Phase 5 by testing against the planted traps.
   Per-collection values only if the traps demand it.
2. LLM permission map: the dataflow rule stands, now owned.
   The LLM composes answers and plans tools.
   It never ranks, validates, gates, or writes logs.
   Those jobs are plain code.
3. Sampling params, timeout, retry: Bedrock defaults in Phase 8.
   Change only if golden cases flake.
   Add throttle backoff only if live smoke hits it.
4. Token budget and wall-clock timeout: the step cap of 4 stands.
   Add one wall-clock timeout line when the runner is built in Phase 9.
   Add a token budget only if `/stats` shows a real problem.
5. Source routing: query both collections, merge, take the top chunk.
   No router.
   The eval asserts the winning chunk's collection.
6. Prompt versioning: golden cases in CI catch prompt regressions.
   No extra machinery in v1.
   Note prompt edits in the pull request when cases move.
7. Mid-run LLM failure: catch, log a `run_events` row, close the run with a clean refusal.
   Same pattern as the Gmail tool-error rule.

## Phase 1 decisions

Taken on 2026-10-09 while building the BookStack phase.

| Decision | Why | Owner |
|---|---|---|
| Slug lookup uses one `GET /api/pages` list, not `GET /api/pages/{slug}` | The pinned build casts `{id}` with `intval`, so a slug can never resolve | Builder |
| Page and book slugs must equal the slug of their title, and the seed asserts the match | BookStack rejects a `slug` field on create. A mismatch would duplicate pages on re-run | Builder |
| Revisions run in a second pass behind a 1.1 second wait | Keeps the stale trap page strictly older at second precision | Builder |
| The admin comes from `bookstack:create-admin --initial` | The pinned image has no web installer. `GET /install` returns 404 on a fresh volume | Builder |
| The local admin password is `shippy-local-admin` | Cold start must repeat without a lost credential. Recorded in the Phase 1 plan, group 2 | Builder |
| D5 widened to allow driving the admin UI over HTTP | Gate 6 must repeat without a human every time. The builder approved and ran it on 2026-10-09 | Builder |

## Study contract

One ADR per major decision in Phase 17, written by the builder.
Defense drill before docs merge: a two-sentence answer per kept component.
A component that fails the drill gets simplified or cut.
The drill list covers everything the builder could not defend in the calibration round:
SQLite dual purpose, MockLLM and offline mode, CI evals, the 4-step cap,
Bolt and Socket Mode, the LangGraph rationale, and the strip decisions above.

---
*Created: 2026-10-09*
*Purpose: ownership record for every design decision; closes the grilling session*
