# Shippy

Shippy answers procedural questions with citations.
It searches a local Chroma index built from your operations SOPs.
It refuses when the retrieved text is ambiguous, stale, or missing.
It also runs gated write workflows.
A human approves each write, and every transition lands in an append-only audit trail.

## Prove it works

One command runs the whole system end to end.
It needs no API keys, no Docker, and no network beyond the one-time embedding model cache.

```bash
scripts/demo.sh
```

The demo builds both Chroma collections from `scripts/corpus/`, serves the real FastAPI app on a free local port with a deterministic mock LLM, and drives the HTTP surface with `curl`.
It prints a real `PASS` or `FAIL` line for each step and exits non-zero if any step fails.
All temporary state lives outside the worktree and is removed on exit.

The steps it proves, in order:

1. `GET /health` answers without a key.
2. `POST /lookup` refuses a wrong key with HTTP 401.
3. `POST /lookup` returns a cited answer with a source id and a verbatim quote.
4. An unanswerable question returns a refusal with source links.
5. A trap query about restocking fees returns a version-conflict refusal.
6. `POST /workflows/run` returns a run in `pending_approval`.
7. `POST /workflows/{id}/approve` completes the run and lands a fallback-mode task.
8. `GET /runs/{id}` replays the full audit trail in order.

To repeat the same proof against a live BookStack instance, put a `BOOKSTACK_TOKEN` in `.env` and run:

```bash
scripts/demo.sh --bookstack
```

That path starts BookStack with `docker compose up -d`, seeds the committed corpus, runs the live ingestion, and repeats the same eight steps.
The default path needs none of that.

## Credentials

The demo path needs no credentials at all.

| Credential | Required for | Notes |
|---|---|---|
| none | `scripts/demo.sh` | Mock LLM, local corpus, temp SQLite |
| `BOOKSTACK_TOKEN`, `BOOKSTACK_URL` | Live ingestion, `--bookstack` | BookStack personal token |
| `AWS_BEARER_TOKEN_BEDROCK` | Real LLM answers | Bedrock bearer token |
| `SHIPPY_API_KEY` | Protecting a deployed app | The demo sets its own key |
| `ASANA_PAT`, `ASANA_PROJECT_GID` | Live task creation | Empty means SQLite fallback mode |
| `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` | Slack adapters | Not wired yet |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` | Gmail adapters | Not wired yet |

Copy `.env.example` to `.env` and fill in only what you need.
Never commit `.env`.

## Switch the demo to Bedrock

The demo injects a deterministic mock LLM through `get_app(provider=...)`.
To exercise the real Bedrock path instead, export a bearer token and set the mode:

```bash
export AWS_BEARER_TOKEN_BEDROCK=...   # your Bedrock token
export SHIPPY_DEMO_LLM=bedrock
scripts/demo.sh
```

`SHIPPY_DEMO_LLM=bedrock` makes `scripts/demo_app.py` leave the provider unset, so `get_app()` builds the real `BedrockLLM`.
Every other step stays the same.
You can also override `BEDROCK_MODEL_ID` and `BEDROCK_REGION`; the defaults are in `.env.example`.

## Run the live BookStack ingestion

Live ingestion pulls pages from BookStack over its API and rebuilds the Chroma collections.

1. Start BookStack: `docker compose up -d`
2. Seed the corpus: `uv run python scripts/seed_bookstack.py`
3. Set `BOOKSTACK_URL` and `BOOKSTACK_TOKEN` in `.env`
4. Rebuild the index: `uv run python -m shippy.ingest`

`scripts/demo.sh --bookstack` runs those four steps for you, then proves the app over the live data.

## Tests and lint

```bash
uv run pytest
uv run ruff check .
uv run python -c "import shippy"
```

## Layout

```
shippy/               Application package
scripts/corpus/       Committed SOP and client pages
scripts/demo.sh       One-command end-to-end proof
scripts/demo_app.py   Demo server with injected dependencies
scripts/seed_bookstack.py  Corpus loader for a live BookStack
tests/                Offline test suite
specs/                Phase plans, requirements, and validation
```
