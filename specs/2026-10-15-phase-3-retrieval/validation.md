# Validation - Phase 3: Retrieval, citation contract, evals

## Definition of done

1. `uv run pytest tests/test_contract.py` exits 0 with 5 tests passing.
2. `uv run python -m shippy.eval` prints `pass rate: 5/5`.
3. Every trap case in the eval output shows `PASS` (meaning it refused as expected).
4. `uv run pytest` exits 0 (all tests in the suite, not just the new ones).
5. `uv run ruff check .` exits 0.
6. `uv run python -c "import shippy"` exits 0.

## Gates

### Gate 1: Tests pass

```bash
uv run pytest tests/test_contract.py -v
```

Expected: 5 tests, all `PASSED`. Exit code 0.

### Gate 2: Eval runner passes

```bash
uv run python -m shippy.eval
```

Expected output format:
```
PASS happy_path
PASS version_conflict
PASS conflicting_pair
PASS keyword_decoy
PASS unanswerable
pass rate: 5/5
```

Every trap case (`version_conflict`, `conflicting_pair`, `keyword_decoy`, `unanswerable`) must print `PASS`.
`PASS` for a trap means the case refused, as expected.

### Gate 3: Full test suite

```bash
uv run pytest
```

Expected: all tests pass. Exit code 0.

### Gate 4: Linter

```bash
uv run ruff check .
```

Expected: no output. Exit code 0.

### Gate 5: Import smoke

```bash
uv run python -c "import shippy"
```

Expected: exit code 0.

## Run procedure

Run gates in order.
A gate failure stops the run.
Fix the issue, then restart from gate 1.

## Merge criteria

- [ ] Gate 1 passes
- [ ] Gate 2 passes (pass rate 5/5, all traps refuse)
- [ ] Gate 3 passes
- [ ] Gate 4 passes
- [ ] Gate 5 passes
- [ ] Phase guide written
- [ ] README table updated

## Failure triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `no_match` when a match is expected | Distance floor too strict | Raise the floor constant in `retrieve.py` |
| Trap returns `ok` instead of refusal | Floor too loose or conflict detection broken | Lower floor or fix `validate.py` conflict logic |
| `QuoteNotFound` for a valid quote | Quote is not a verbatim substring | Ensure `MockLLM` returns exact text from chunk |
| `ImportError` on `BedrockLLM` import | `langchain-aws` missing | Run `uv sync` |
| Eval crashes on corpus load | `scripts/corpus/sops.json` format changed | Check corpus shape against `test_corpus.py` |
