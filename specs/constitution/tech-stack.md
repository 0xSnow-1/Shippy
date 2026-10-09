# Tech Stack

Decisions live here.
The PRD (`prd.md`) specifies behavior; this file records what we build with and why.

## Runtime and tooling

Python 3.12 with `uv` for environment and dependency management.

`ruff` for lint and format.

`pytest` for tests, with `respx` for mocking HTTP in live-adapter contract tests.

## Core framework choices

| Layer | Choice | Why |
|---|---|---|
| Step runner | LangGraph | Builder's hands-on LangChain/LangGraph experience; the JD names LangChain; LangSmith traces graph nodes natively; plan/execute/verify maps straight onto the graph |
| API | FastAPI + uvicorn with API-key middleware | Named in the job description; API key gives every caller an identity |
| LLM | Claude Haiku on AWS Bedrock via `langchain_aws.ChatBedrockConverse` | Builder already runs this pattern in seven other projects; bearer-token auth, no AWS profiles needed |
| LLM portability | Provider interface + `MockLLM` | Unit tests run offline and free; Bedrock is the only live provider (ADR documents the choice over OpenAI) |
| Retrieval | Chroma (embedded) + `rank_bm25` + RRF fusion | Named in the job description; hybrid retrieval per PRD; BM25 keeps keyword search offline |
| Embeddings | Chroma default local embedding function | No API key required for retrieval development; swappable behind an interface |
| Persistence | SQLite (WAL mode) | PRD allows SQLite for v1; audit log, task store fallback, and email outbox all live here |
| Tracing | LangSmith | Keys already present in the builder's environment; captures LangGraph graph, LLM, and tool spans natively |
| Human surface | Slack (own free workspace) + `scripts/demo.sh` | Block Kit approval buttons are the primary UX; demo.sh is the credential-free proof path |
| Machine surface | REST only | The contract a backend team consumes; no first-party GUI |
| Orchestration | Docker Compose | Self-hosts BookStack; single-command reproducible demo |

## Bedrock wiring (established pattern)

Environment trio copied to `.env` (never committed; `.env.example` documents names only):

- `AWS_BEARER_TOKEN_BEDROCK`
- `BEDROCK_MODEL_ID` - default `anthropic.claude-haiku-4-5-20251001-v1:0`
- `BEDROCK_REGION` - `us-east-1`
- `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`

Instantiation: `ChatBedrockConverse(model=..., bedrock_api_key=os.getenv("AWS_BEARER_TOKEN_BEDROCK"), aws_region=...)`.
The bearer token must be forwarded explicitly (learned pattern from the Occlusion project's `tests/agent/test_bedrock_wiring.py`).

## Self-hosted services

BookStack runs as a pinned Docker image in the Compose stack.

We are the admin of this instance: a seed script creates 15-20 e-commerce/retail ops SOP pages with version history plus 5-10 fake client account profiles, then mints our own API token with "Access System API" permission.

Ingestion uses the real BookStack REST API including `GET /api/pages/{id}/export/markdown`, so the pipeline is production-identical.

## Integration adapters (all four live)

Every external integration implements one interface with two modes selected by environment variable:

| Adapter | Live mode | No-credential mode (CI / demo.sh) |
|---|---|---|
| Chat (Slack) | Own free workspace, Socket Mode, Block Kit approvals | REST approve/reject endpoints |
| Tasks (Asana) | Personal free account PAT, `POST /api/1.0/tasks` | SQLite task store |
| Email (Gmail) | Personal Google OAuth client, Testing status | Local outbox table |
| LLM | Bedrock Claude Haiku | `MockLLM` with canned tool calls |

Live Slack and Asana paths are contract-tested with `respx` against published API schemas, so CI validates them without credentials.

Gmail runs in Google OAuth "Testing" status with the builder as the sole test user.
Refresh tokens expire every 7 days; `scripts/gmail_auth.sh` re-authorizes and the runbook documents the weekly rhythm.

The Asana integration is explained end-to-end in `docs/learn_asana.md` (STE-inspired learning doc: PAT, respx, contract tests, safety rules).

## Rejected choices (with reasons)

Streamlit: dropped - the machine surface is REST, the human surface is Slack.
One first-party GUI would be a third surface to maintain.

OpenTelemetry + Jaeger: replaced by LangSmith - LangGraph traces natively, one less collector to operate.

Pinecone or managed vector services: unnecessary at this corpus size (ADR to document).

Postgres: SQLite satisfies the PRD v1 requirement and removes a service from the demo stack.

OpenAI / Assistants API: the job description names it, but the builder's working credentials and experience are Bedrock; a provider interface plus ADR covers the skill demonstration (ADR to document).

LangServe or frameworks beyond LangGraph: the PRD demands a single-pass capped runner, not open-ended orchestration.

SSE streaming: cut from v1 on 2026-10-09 - it proves none of the three promises, and the job description never names it. Revisit only if a REST consumer asks for incremental tokens.

## External dependencies

All integrations use free tiers: Slack free workspace, Asana free PAT, Google OAuth Testing, Bedrock bearer token and LangSmith keys already provisioned by the builder.

Zero paid new accounts.

---
*Created: 2026-10-07*
*Last amended: 2026-10-07 - Bedrock/ChatBedrockConverse, LangSmith over OTel, Streamlit dropped, live Slack/Asana/Gmail, API-key auth, named Shippy*
*Last amended: 2026-10-09 - grilling session: LangGraph and SSE rationales corrected (false JD claims removed), SSE added to rejected choices*
