# Plan - Phase 0: Scaffold

Feature directory: `specs/2026-10-08-phase-0-scaffold`
Branch: `spec/phase-0-scaffold`
Roadmap source: `specs/constitution/roadmap.md`, Phase 0

This plan has 5 numbered task groups.
Each group ends with one verify step.
Finish the verify step before you start the next group.
Run all commands from the project root.

## 1. Build the uv environment

Goal: one locked environment holds all software for this project.

- [x] In `pyproject.toml`, add these runtime tools to `dependencies`: `langgraph`, `fastapi`, `uvicorn`, `langchain-aws`, `chromadb`, `rank_bm25`, `httpx`.
- [x] In `pyproject.toml`, add a `[dependency-groups]` section with a `dev` list: `pytest`, `ruff`, `respx`.
- [x] Keep `requires-python = ">=3.12"` and the current project name.
- [x] Run `uv lock`. Then run `uv sync`.

Verify: `uv run python -c "import langgraph, fastapi, uvicorn, langchain_aws, chromadb, rank_bm25, httpx"` returns exit code 0.

## 2. Wire ruff and pytest

Goal: lint and test commands run through `uv run`, with no global setup.

- [x] In `pyproject.toml`, add `[tool.ruff]` with `target-version = "py312"`.
- [x] In `pyproject.toml`, add `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `pythonpath = ["."]`.
  `pythonpath = ["."]` puts the project root on Python's search path.
  Without this line, tests cannot import `shippy`.
- [x] Create the folder `tests/`.
- [x] Create `tests/test_smoke.py`.
  The test checks that the Python version is 3.12 or newer.

Verify: `uv run ruff check .` returns exit code 0, and `uv run pytest` returns exit code 0.

## 3. Create the shippy package folder

Goal: Python finds our code with a plain `import shippy`.

- [x] Create the folder `shippy/` at the project root.
- [x] Create `shippy/__init__.py` with one line: `__version__ = "0.1.0"`.
- [x] Create `tests/test_import_shippy.py`.
  The test imports `shippy` and checks that `__version__` is not empty.

We use no packaging tool.
No hatchling and no editable install.
Python finds `shippy` for two reasons:
- The options `-c` and `-m` add the current folder to Python's search path.
- The pytest setting `pythonpath = ["."]` does the same for tests.
Both work only when you run from the project root.

Verify: `uv run python -c "import shippy"` returns exit code 0, and `uv run pytest` passes.

## 4. Create .env.example and .gitignore

Goal: one file lists every setting name. Git never stores real secrets.

- [x] Create `.env.example`. Add these names with empty values:
  - Bedrock trio: `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL_ID`, `BEDROCK_REGION`
  - LangSmith: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`
  - Shippy API key: `SHIPPY_API_KEY`
  - Integration tokens: `BOOKSTACK_URL`, `BOOKSTACK_TOKEN`, `ASANA_PAT`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
- [x] Give values to only two names: `BEDROCK_MODEL_ID` and `BEDROCK_REGION`.
  Copy their values from `specs/constitution/tech-stack.md`.
  These two values are not secrets.
- [x] Create `.gitignore`. Add: `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`.

Verify: `git check-ignore .env` prints `.env`. `git check-ignore .env.example` prints nothing.

## 5. Run the final check

Goal: the roadmap verify command for Phase 0 passes.

- [x] Run all four from the project root: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run python -c "import shippy"`.
- [x] Run `git status`. It lists only scaffold files: `pyproject.toml`, `uv.lock`, `shippy/`, `tests/`, `.env.example`, `.gitignore`.
- [x] Open `.env.example`. It contains no secret values.
- [x] Search the changed files for tokens. No real token is present.

Verify: all four commands return exit code 0.

---
*Created: 2026-10-08*
*Rewritten: 2026-10-08 - flat package folder, no packaging tool, ASD-STE 100 style*
*Last amended: 2026-10-08 - all task boxes ticked after phase 0 verification passed*
