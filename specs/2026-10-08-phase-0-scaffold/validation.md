# Validation - Phase 0: Scaffold

## Definition of done

Phase 0 is ready to merge when:
- All three gates below return exit code 0 on the feature branch.
- Every merge criterion is checked.

## Gates

### Gate 1 - test suite (from the roadmap)

Command: `uv run pytest`

Pass condition: tests run and pass. Exit code 0.

What a failure means:
- Exit code 5 means no tests exist. Check the `tests/` folder and the `testpaths` setting.
- Import error means Python cannot find `shippy`. Check that you run from the project root and that `pythonpath = ["."]` is set.

### Gate 2 - lint (from the roadmap)

Command: `uv run ruff check .`

Pass condition: no findings. Exit code 0.

### Gate 3 - package import (smoke)

Command: `uv run python -c "import shippy"`

Pass condition: exit code 0, no output.

This command works because you run it from the project root.
Python adds the current folder to its search path when you use `-c`.

## Procedure

Run these from the project root, in order:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -c "import shippy"
```

All four commands must return exit code 0.

## Merge criteria

- [ ] Gate 1 returns exit code 0.
- [ ] Gate 2 returns exit code 0.
- [ ] Gate 3 returns exit code 0.
- [ ] `uv.lock` exists and is committed.
- [ ] `git check-ignore .env` prints `.env`, so git ignores the secret file.
- [ ] `git check-ignore .env.example` prints nothing, so git accepts the example file.
- [ ] `.env.example` has empty values for every secret name.
- [ ] No changed file contains a token, key, or password.
- [ ] Changed files are only: `pyproject.toml`, `uv.lock`, `shippy/`, `tests/`, `.env.example`, `.gitignore`.

## Evidence

Save the output of all three gates.
Put it in the PR description or the phase log.

## Failure triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `pytest` exits with code 5 | No tests exist, or `testpaths` is wrong | Check `tests/test_smoke.py` and the pytest settings |
| `ImportError: shippy` inside pytest | `pythonpath` is missing | Add `pythonpath = ["."]` to the pytest settings |
| `ImportError: shippy` in gate 3 | The command ran outside the project root | Move to the project root and run again |
| `ruff` reports files inside `.venv` | `.venv` is not excluded | Add `.venv` to the ruff exclude list |
| `git check-ignore .env` exits with code 1 | The `.env` rule is missing | Add `.env` to `.gitignore` |

---
*Created: 2026-10-08*
*Rewritten: 2026-10-08 - flat package folder, no packaging tool, ASD-STE 100 style*
