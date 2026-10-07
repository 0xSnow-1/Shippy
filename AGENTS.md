# AGENTS.md

> Project-level instructions for AI agents working in this repository.
> Read this file before starting any task.

## Project overview

Shippy answers procedural questions with citations.
Shippy also runs gated workflows through a REST API.
It serves an e-commerce operations team.
Read `specs/constitution/mission.md`, `specs/constitution/tech-stack.md`, and `specs/constitution/roadmap.md` before any scope or design decision.

## Repository structure

```
shippy/       # Application code (flat package at the project root)
tests/        # Test suite
specs/        # Constitution and feature specs
docs/         # Learning docs and runbooks
scripts/      # Build and utility scripts (later phases)
```

## Conventions

### Code style

<!-- Language, formatter, linter, and any project-specific conventions. -->

### Naming

<!-- File naming, function naming, variable naming conventions. -->

### Testing

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_smoke.py
```

### Spec checkboxes

Plan and validation files in `specs/` track work with `- [ ]` boxes.
Tick a box (`- [x]`) when its item passes the verify step.

### Explanations to the human (ASD-STE 100 style)

You write for a human in the loop.
Use this style for every explanation you give the human.
That includes: explanations after code changes, work summaries, progress updates, and PR descriptions.

Rules:
- One idea per sentence.
- Write a maximum of 20 words per sentence.
- Use active voice and present tense.
- Use plain words.
- Define a new term in one short sentence right after the first use.
- Put each sentence on its own line.

Example:

> The scaffold is ready.
> I added the `shippy` folder at the project root.
> Python finds it because all commands run from the project root.
> No packaging tool is involved.

### Commits

<!-- Commit message format, branching strategy, PR conventions. -->

## Tool permissions

Allowed:
- Read and edit files under `shippy/`, `tests/`, `specs/`, `docs/`
- Run `uv sync`, `uv lock`
- Run `uv run pytest`, `uv run ruff check .`

Restricted (ask before proceeding):
- Changing dependencies in `pyproject.toml`
- Running destructive commands (`rm -rf`, database drops, etc.)
- Pushing branches or creating releases

Not allowed:
- Modifying CI/CD pipeline configuration without explicit instruction
- Installing new dependencies without explicit instruction

## Known constraints

- Run all commands from the project root.
- Python finds the `shippy` folder only when you are at the project root.

## Verification gates

Before marking any task complete, the agent must verify:

- [ ] Tests pass (`uv run pytest`)
- [ ] Linter passes (`uv run ruff check .`)
- [ ] Import smoke passes (`uv run python -c "import shippy"`)
- [ ] No new warnings introduced
- [ ] Changed files are within the permitted scope above

## Contact / escalation

If the agent cannot proceed without a decision that falls outside its permitted scope, it should stop and describe the blocker clearly rather than making an assumption.
