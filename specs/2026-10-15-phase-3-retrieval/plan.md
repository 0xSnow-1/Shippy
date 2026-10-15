# Plan - Phase 3: Retrieval, citation contract, evals

## Group 1: Spec files

- [ ] Write `specs/2026-10-15-phase-3-retrieval/requirements.md`
- [ ] Write `specs/2026-10-15-phase-3-retrieval/plan.md`
- [ ] Write `specs/2026-10-15-phase-3-retrieval/validation.md`

Verify: all three files exist under `specs/2026-10-15-phase-3-retrieval/`.

## Group 2: Retrieval module

- [ ] Write `shippy/retrieve.py` with `search_sop(query, collection, k, floor) -> SearchResult`
- [ ] `SearchResult` is a dataclass: `status` (`ok` or `no_match`), `chunks` (list of chunk dicts)
- [ ] Apply relevance floor: chunks above the distance floor are dropped; if none remain, return `no_match`
- [ ] Collection is always `sops`; collection object is injected so tests can pass a fake

Verify: `uv run ruff check shippy/retrieve.py` passes.

## Group 3: Composer and provider interface

- [ ] Write `shippy/compose.py`
- [ ] `LLMProvider` protocol: one method `complete(prompt: str) -> str`
- [ ] `MockLLM(responses: dict[str, str])` implements the protocol; matches first key found in prompt
- [ ] `BedrockLLM` implements the protocol; imports `ChatBedrockConverse` at function call time only
- [ ] `compose(query, chunks, provider) -> Answer`; `Answer` dataclass: `answer`, `quote`, `proposed_action`
- [ ] Composer builds a plain-text prompt and calls `provider.complete`; parses JSON response

Verify: `uv run ruff check shippy/compose.py` passes.

## Group 4: Validator

- [ ] Write `shippy/validate.py`
- [ ] `validate(answer, chunks) -> ValidationResult`
- [ ] `ValidationResult` dataclass: `ok` bool, `status` str, `reason` str, `sources` list of str
- [ ] Verbatim substring check: `answer.quote` must appear in at least one chunk text
- [ ] Version-conflict check: two chunks with the same `sop_id` but different `version` values refuse
- [ ] `no_match` pass-through: if retrieval returned `no_match`, return refusal immediately
- [ ] Source links built from `BOOKSTACK_URL` env var and chunk `sop_id` metadata

Verify: `uv run ruff check shippy/validate.py` passes.

## Group 5: Tests

- [ ] Write `tests/test_contract.py`
- [ ] Test: happy path — retrieval finds a chunk, composer returns a valid quote, validator passes
- [ ] Test: trap 1 — version-conflict query returns refusal (restocking fee old vs current)
- [ ] Test: trap 2 — conflicting-pair query returns refusal (VIP escalation ops vs finance)
- [ ] Test: trap 3 — keyword-decoy query returns `no_match` refusal (COD remittance, not a refund SOP)
- [ ] Test: trap 4 — unanswerable query returns `no_match` refusal (no SOP exists for the topic)
- [ ] All tests run offline: fake Chroma collection, `MockLLM`, no network

Verify: `uv run pytest tests/test_contract.py` passes.

## Group 6: Eval runner

- [ ] Write `shippy/eval.py` as a runnable module
- [ ] Builds an in-memory Chroma collection from `scripts/corpus/sops.json`
- [ ] Runs the same five cases as `test_contract.py`
- [ ] Prints one line per case: `PASS` or `FAIL` with the case name
- [ ] Prints final pass rate: `pass rate: N/5`
- [ ] Every trap case must refuse; the happy path must pass

Verify: `uv run python -m shippy.eval` prints `pass rate: 5/5` and every trap shows `PASS`.

## Group 7: Phase guide and docs

- [ ] Write `docs/phase-guides/phase-3-retrieval-and-evals.md`
- [ ] Update `docs/phase-guides/README.md` table: mark phase 3 done, add phases 5 and 6 rows
- [ ] Tick the phase 3 verify box in `specs/constitution/roadmap.md`

Verify: `uv run pytest` and `uv run ruff check .` pass; `uv run python -m shippy.eval` prints `pass rate: 5/5`.
