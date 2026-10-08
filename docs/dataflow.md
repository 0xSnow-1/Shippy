# Shippy: The Problem and the Data Flow

This document explains what Shippy fixes and how every request moves through the system.
Tech choices appear inline at each step.

---

## The problem

Operations staff need procedures to do their jobs.
These procedures live in a company wiki as SOPs.
An SOP means Standard Operating Procedure. It is a step-by-step guide.

Today, staff search the wiki by hand.
They read the document.
They copy the steps into a task tool.
They paste a summary into a chat message.
This process is slow and it makes mistakes.

The expensive mistake happens like this.
Staff act on an old version of an SOP.
Or they misremember a step.
Or they invent a step that does not exist.
The wrong action costs more time than the original task saved.

No record exists afterward.
Nobody can reconstruct why the system did something.

## What Shippy solves

Shippy is one service that closes all three gaps.

1. It answers procedural questions with a source and a quote. Every quoted citation is verified verbatim against retrieved chunks.
2. It runs follow-up actions through a gate. A human approves every write action.
3. It logs every decision to an append-only record. Any run can be replayed later.

An append-only record means rows only get added. Nothing gets edited or deleted.

## The two surfaces

Shippy has exactly two entrances.

- Slack is the human surface. A person types a question and clicks approval buttons.
- REST is the machine surface. Other programs call Shippy over HTTP with an API key.

REST means Representational State Transfer. It is the standard web API style.
Both surfaces run the same engine behind them.

## The moving parts and their tech

| Part | Technology | One-line job |
|---|---|---|
| Human surface | Slack Bolt app, Socket Mode, Block Kit | Receives messages and approval clicks |
| Machine surface | FastAPI + uvicorn, API-key middleware | Serves REST and SSE streaming |
| Harness (step runner) | LangGraph | Plans, executes, verifies. Cap: 4 steps |
| Tool-call loop | Raw function-calling loop under LangGraph | Asks the LLM for tool calls, runs them, returns results |
| LLM | Claude Haiku on AWS Bedrock (`ChatBedrockConverse`) | Composes answers and plans tool use |
| Offline LLM | `MockLLM` with canned replies | Runs every test with zero network and zero cost |
| Knowledge store | Chroma (embedded), two collections | Holds SOP and client chunks for search |
| Keyword search | `rank_bm25` | Finds exact keyword matches |
| Dense search | Chroma local embedding function | Finds meaning matches. No API key needed |
| Merge math | RRF (Reciprocal Rank Fusion) | Merges both search result lists into one ranking |
| State memory | SQLite in WAL mode | Pending runs, approvals, task store, email outbox |
| Audit memory | SQLite `run_events` table, append-only | One row per event, forever |
| Wiki | BookStack, pinned Docker image, self-hosted | Stores the source SOPs, versioned |
| Tracing | LangSmith | Records every graph step, LLM call, tool call |
| Orchestration | Docker Compose | One command starts the whole stack |

### Direct answers to the design questions

**Where is the memory?**
There are two memories, and they do different jobs.
The knowledge memory is Chroma. It stores the SOP corpus for retrieval. It never stores conversation history.
The working memory is SQLite. It stores pending runs, approval state, task rows, and outbox rows until they resolve.
The audit memory is also SQLite: the `run_events` table. It keeps history forever.
Shippy has no personal chat memory across separate questions. Each request starts fresh. Only run state and the audit log persist.

**Where is the LLM?**
The LLM sits behind a provider interface.
Live mode builds `ChatBedrockConverse` from `langchain-aws`, authenticated with `AWS_BEARER_TOKEN_BEDROCK`.
Offline mode builds `MockLLM` instead.
The harness calls the LLM at exactly two points: composing a cited answer from retrieved chunks, and planning tool calls for a workflow.
The LLM never ranks retrieval results, never validates citations, never passes the gate, and never writes log rows. Those jobs are plain code.

**Is this built without LangGraph?**
No. LangGraph IS the harness.
The harness is a LangGraph graph with named nodes: plan, execute, verify.
LangGraph enforces the step cap of 4 and hosts the validation gate node.
Under the graph sits a raw tool-call loop. That loop is the tested primitive LangGraph drives.

**Is it just a harness?**
Yes. Shippy's core is an agent harness: a controlled loop that retrieves, calls tools, gates writes, and logs everything.
FastAPI is a shell around the harness for machines.
Slack Bolt is a shell around the harness for humans.
Nothing else runs inside Shippy. The harness is the product.

## Data flow part 1: building the knowledge base (offline path)

This flow runs once at setup, then on a schedule.

```
BookStack wiki (Docker, self-hosted)
      │  REST API pull: GET /api/pages
      │  export: GET /api/pages/{id}/export/markdown
      ▼
Raw pages (Markdown)
      │  plain Python: strip boilerplate, chunk on headings
      ▼
Chunks with metadata: sop_id, version, updated_at
      │  embed: Chroma local embedding function (no API key)
      ▼
Chroma collection: "sops"
      +
Chroma collection: "clients"
```

Client profiles go to a second collection.
Each chunk carries its source ID and version number.
The version number enables stale-document detection later.
Ingestion fails loudly if the wiki format drifts.

## Data flow part 2: answering a question (read-only path)

A staff member asks: "How do I file an A-to-Z claim?"

```
Slack message (Bolt, Socket Mode)
   or
POST /lookup (FastAPI, X-API-Key check)
      │
      ▼
Harness node: retrieve_sop (LangGraph)
      │
      ├─▶ Chroma dense search ──────┐
      ├─▶ rank_bm25 keyword search ─┼─▶ RRF fusion ─▶ top chunks
      │                             │
      ▼                             ▼
LLM node (Claude Haiku or MockLLM): compose answer from chunks only
      │
      ▼
Citation validator (pure Python, no AI)
      │  check 1: every quote is a substring of a real chunk
      │  check 2: chunk versions do not conflict
      │
      ├─ pass ──▶ Answer with source ID + verbatim quote
      │                 │
      │                 ├─▶ Slack reply (Block Kit)
      │                 └─▶ SSE stream to REST client
      │
      └─ fail ──▶ REFUSAL: link to the original document
      │
      ▼
run_events row written (SQLite, append-only)
LangSmith span recorded for the graph and the LLM call
```

Two outcomes only.
Either the answer carries evidence, or the system refuses.
A vague middle ground does not exist.

The validator uses a substring check.
A substring check means plain text matching.
No AI decides whether the quote is real.

Memory used in this path:
Chroma supplies the knowledge.
SQLite receives the audit row.
No conversational history is read or written.

## Data flow part 3: running a workflow (write path)

Now the request needs an action, not just an answer.
Example: "File that claim and notify the account manager."

```
Slack message or POST /workflows/run
      │
      ▼
Harness graph (LangGraph): plan → execute → verify, max 4 steps
      │
      ├─ plan node: LLM picks tool calls
      │
      ├─ execute node: raw tool-call loop runs them
      │     ├─ retrieve_sop ─▶ Chroma (cited content)
      │     ├─ create_task ──▶ Asana API (live) or SQLite task store (offline)
      │     ├─ send_slack ───▶ Slack chat.postMessage
      │     └─ send_email ───▶ Gmail API (live) or SQLite outbox (offline)
      │
      ├─ verify node: gate checks citations, fields, target
      │
      ▼
VALIDATION GATE (LangGraph gate node, blocks here)
      │
      ├─ all pass ──▶ status = pending_approval, run state saved to SQLite
      │                     │
      │                     ▼
      │              Slack Block Kit message:
      │              [Approve] [Reject] buttons
      │                     │
      │              worker clicks Approve
      │                     │
      │                     ▼
      │              executor resumes from persisted SQLite run state
      │              real write executes (Asana / Slack / Gmail)
      │
      └─ any fail ──▶ run rejected, reason logged
      │
      ▼
Every transition appended to run_events (SQLite)
LangSmith records the full graph trace
```

The gate sits between planning and writing.
The harness may plan the write freely.
The write itself waits for a human.

Run state lives in SQLite while a run waits for approval.
The approval click can arrive minutes later, from another machine.
The executor resumes from that saved state, not from memory.

Slack Block Kit is Slack's UI toolkit for message buttons.

The step cap of 4 bounds the whole graph.
A runaway plan cannot loop forever. LangGraph cuts it off.

## Data flow part 4: reconstructing a run (audit path)

Any time, anyone can ask what happened.

```
GET /runs/{id} (FastAPI)
      │
      ▼
SQLite run_events table
      │  ordered by sequence number
      ▼
Full decision trail:
  prompt received
  chunks retrieved (IDs)
  plan produced
  tool calls made
  gate result
  approval event
  final output
  LangSmith trace link
```

The trail has one row per event.
The sequence number preserves order.
This table proves the zero-unlogged-actions guarantee.

## The two modes of every integration

Every external integration implements one interface with two modes.
One environment variable selects the mode.

| Integration | Live mode | Offline mode |
|---|---|---|
| Wiki | Self-hosted Docker (always live) | same |
| Chat | Our Slack workspace (Bolt, Socket Mode) | REST approve/reject endpoints |
| Tasks | Asana personal token | SQLite task store |
| Email | Gmail OAuth | SQLite outbox table |
| LLM | Claude Haiku on Bedrock | MockLLM with canned replies |
| Tracing | LangSmith | Local logs, no-op |

A mode switch reads one environment variable.
One interface, two backends.
This design lets CI prove the same contract that production ships.

Offline mode runs with zero credentials.
`scripts/demo.sh` drives the whole flow that way.
This is why CI never depends on live accounts.

respx pins the live HTTP contracts in tests.
respx is a library that mocks HTTP at the transport layer.
The tests therefore validate our adapters against the published API schemas without credentials.

## Where the money and time get measured

Three observability layers run in parallel.

1. `run_events` in SQLite. Source of all aggregates for `GET /stats`.
2. LangSmith. Traces each graph step, LLM call, and tool call.
3. Structured logs. Every line carries the run ID.

The run ID connects all three.
One ID answers: what happened, how long it took, what it cost.
`GET /stats` computes p50 and p95 latency, approval rate, error counts, and per-run token cost from `run_events`.

## Stack summary in one table

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12, `uv` | Fast iteration, locked dependencies |
| Lint and format | `ruff` | One tool, fast |
| Tests | `pytest` + `respx` | Offline tests plus HTTP contract tests |
| API | FastAPI + uvicorn | SSE streaming, API-key middleware, named in the job description |
| Harness | LangGraph | Step caps, gate nodes, native LangSmith tracing |
| LLM | Bedrock Claude Haiku, provider interface | Live path plus offline MockLLM behind the same port |
| Vector store | Chroma embedded | No service to operate at this corpus size |
| Search | BM25 + dense + RRF | Keywords and meanings both covered |
| Database | SQLite WAL | One file, no server, fits the demo stack |
| Chat | Slack Bolt, Socket Mode | Buttons for approvals, no public URL needed |
| Wiki | BookStack in Docker | Versioned SOPs, real REST API for ingestion |
| Tracing | LangSmith | Graph, LLM, and tool spans with one key |
| Packaging | Docker Compose | One command brings up everything |

## The design in one sentence

Shippy takes a request, retrieves evidence, composes a cited plan, passes a code-checked gate, waits for a human approval, executes the write, and appends every step to an immutable log.

That is the whole design.
Everything else in the repository exists to support, test, or prove that line.

---

*Created: 2026-10-08*
*Purpose: problem statement and end-to-end data flow with tech mapped to each step*
