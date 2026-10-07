# Requirements - Phase 0: Scaffold

## Context

Shippy answers procedural questions with citations.
Shippy also runs approved multi-step workflows.
Everything happens through an auditable REST service.
The mission file is `specs/constitution/mission.md`.
Phase 0 is the first phase in `specs/constitution/roadmap.md`.
The roadmap states that phases 1-3 block every later phase.
So Phase 0 unlocks the whole roadmap.

The repository today is a bare `uv init` output:
- The project name is `internal-agent`.
- No tools are installed.
- No lint or test config exists.
- No `shippy` folder exists.
- No `.env.example` exists.
- No `.gitignore` exists.

Two groups of files already exist and stay unchanged:
- `docs/learn_asana.md`
- The constitution files in `specs/constitution/`

The tech choices come from `specs/constitution/tech-stack.md`: Python 3.12, `uv`, `ruff`, `pytest`, `respx`.

## Scope

The builder confirmed the scope on 2026-10-08: roadmap Phase 0 only.

### In scope

1. A `uv` environment with locked dependencies.
2. `ruff` and `pytest`, runnable through `uv run`.
3. A package folder named `shippy` that Python can import.
4. `.env.example` with the Bedrock trio, LangSmith names, API key, and integration token names.
5. `.gitignore`.
6. A minimal smoke test suite.

The smoke test is a required addition to the roadmap text.
Reason: `uv run pytest` returns exit code 5 when no tests exist.
Exit code 5 fails the roadmap's own verify command for this phase.

### Out of scope

- Renaming the project from `internal-agent` to `shippy`.
- README content, CI setup (phase 16), Docker and BookStack (phase 1), ingestion (phase 2).
- Any runtime behavior.
- Real secret values in any file.
- A packaging tool such as hatchling. See decision D2.
- Adapter SDKs such as Slack Bolt or Google OAuth libraries. Those arrive in their own phases.

## Decisions

**D1 - Scope is roadmap Phase 0 deliverables only.**
The builder confirmed this choice.
Nothing extra enters this phase.

**D2 - The `shippy` folder sits at the project root. No packaging tool is used.**
Python finds the folder when commands run from the project root.
The options `-c` and `-m` add the current folder to Python's search path.
The pytest setting `pythonpath = ["."]` does the same for tests.
A packaging tool (hatchling plus an editable install) would make imports work from any folder.
We do not need that behavior today, so we do not pay its setup cost.
We add packaging later only if a command needs `shippy` from outside the project root.

**D3 - Core runtime dependencies install now: `langgraph`, `fastapi`, `uvicorn`, `langchain-aws`, `chromadb`, `rank_bm25`, `httpx`.**
These are the layers named in the tech stack table.
Adapter SDKs are deferred, so this phase stays a thin slice.

**D4 - Dev tooling lives in a `uv` dependency group named `dev`: `pytest`, `ruff`, `respx`.**
`uv run` picks them up without global installs.

**D5 - `.env.example` documents names only.**
Every secret-valued entry is empty.
Only `BEDROCK_MODEL_ID` and `BEDROCK_REGION` carry values, taken from the tech stack, because they are not secrets.

**D6 - `ruff` runs its default rule set at `target-version = "py312"`.**
Rules can tighten later without blocking this phase.

**D7 - `pytest` collects from `tests/`, and a smoke test exists from Phase 0 onward.**
Two settings make imports work: `testpaths` points to `tests/`, and `pythonpath` points to the project root.
The smoke test keeps the roadmap verify command at exit code 0 from the moment it is introduced.

## Deliverable files

- `pyproject.toml` (edited)
- `uv.lock` (generated)
- `shippy/__init__.py`
- `tests/test_smoke.py`
- `tests/test_import_shippy.py`
- `.env.example`
- `.gitignore`

## Open questions

- [ ] Do the drafted integration token names (`ASANA_PAT`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, Gmail names) stay unchanged?
  Resolve when phases 10-12 design their adapters.

---
*Created: 2026-10-08*
*Rewritten: 2026-10-08 - flat package folder, no packaging tool, ASD-STE 100 style*
