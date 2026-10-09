# Phase 0: Scaffold

## What problem this solves

Shippy needs a place to live.

Before this phase the repo was a pile of notes.
No package. No tests. No linter. No shared environment.

This phase builds the empty skeleton.
Every later phase drops code into that skeleton.

## What we built

| Piece | File | Job |
|---|---|---|
| Python package | `shippy/` | Home of all app code. |
| Dependency lock | `pyproject.toml`, `uv.lock` | Pins every library version. |
| Linter | `ruff` | Catches style and simple bugs before review. |
| Test runner | `pytest` | Runs automated checks. |
| HTTP mocking | `respx` | Lets tests fake an API with no network. |
| Secrets template | `.env.example` | Lists the names of every secret, with empty values. |
| Ignore rules | `.gitignore` | Keeps secrets and junk out of git. |

## Why it is built this way

**`uv` and a lock file.**
`uv` installs Python packages fast.
The lock file records the exact version that worked.
A fresh clone installs the same versions you have.

**`shippy/` as a flat package at the project root.**
No nested `src/` folder.
Python imports it directly from the project root.
One less layer to explain.

**`pythonpath = ["."]` in the pytest config.**
This lets tests do `import shippy` without install steps.
Run tests from the project root and it just works.

**`.env.example` holds names, `.env` holds values.**
The example file is safe to commit.
It documents what a new developer must fill in.
The real `.env` is git-ignored, so the secrets never leak.

**`respx` from the start.**
Later phases talk to BookStack, Asana, Slack, and Gmail.
Tests must never hit those services for real.
`respx` fakes the HTTP layer.

## Libraries already installed

They are declared now so no later phase has to touch the dependency file.

| Library | Used from |
|---|---|
| `langgraph` | Phase 9, the step runner |
| `fastapi`, `uvicorn` | Phase 7, the REST API |
| `langchain-aws` | Phase 8, the Bedrock connection |
| `chromadb` | Phase 2, the vector index |
| `rank_bm25` | Phase 4, keyword search |
| `httpx` | Phase 1 and 2, BookStack calls |

## What you can do now

```bash
uv run pytest          # 1 test, checks the Python version
uv run ruff check .    # clean
```

Nothing is wired together yet.
The skeleton holds the tools.
Later phases add the machine.

## Cost

No running services. No credentials. No Docker.

---
*Created: 2026-10-09*
