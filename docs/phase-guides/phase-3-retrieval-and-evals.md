# Phase 3: Retrieval, Citation Contract, and Evals

## What problem this solves

Phase 2 built the search index.
But an index alone cannot answer questions.
Phase 3 adds the layer that takes a question, finds relevant chunks, composes a cited answer, and validates that answer before returning it.

This phase defines the citation contract.
Every answer must carry a verbatim quote from the retrieved source.
When the system cannot meet that contract, it refuses and points to the source instead of guessing.

## What we built

| Module | File | Job |
|---|---|---|
| Retrieval | `shippy/retrieve.py` | Searches the `sops` Chroma collection; returns `no_match` below the relevance floor |
| Composer | `shippy/compose.py` | Sends retrieved chunks to an LLM; parses structured JSON output |
| Validator | `shippy/validate.py` | Checks the quote is verbatim; refuses on version conflict or no match |
| Provider interface | `shippy/compose.py` | `LLMProvider` protocol with `MockLLM` and `BedrockLLM` implementations |
| Contract tests | `tests/test_contract.py` | Five offline tests: one happy path and four trap cases |
| Eval runner | `shippy/eval.py` | Runs the same five cases and prints a pass rate |

## How each piece works

### Retrieval

`search_sop` queries the `sops` Chroma collection.
It returns the top-k chunks whose distance is at or below the relevance floor.
Distance is Chroma's default L2 distance.
A query with no chunks below the floor returns `status="no_match"`.

The `clients` collection is indexed from phase 2 but is never routed here.
Phase 3 answers SOP questions only.

### Answer composer

The composer builds a plain-text prompt from the query and the retrieved chunks.
It sends the prompt to an `LLMProvider` and parses the JSON response.
The response must contain three keys: `answer`, `quote`, and `proposed_action`.
`quote` must be a verbatim substring of one of the retrieved chunks.
The validator enforces this; the composer does not.

### Provider interface

`LLMProvider` is a Python `Protocol`.
Any class with a `complete(prompt: str) -> str` method satisfies it.

`MockLLM` takes a dict of query-substring-to-JSON-string.
It returns the first matching response.
Tests pass `MockLLM` directly; no network or credentials needed.

`BedrockLLM` wraps `ChatBedrockConverse` from `langchain-aws`.
It reads `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL_ID`, and `BEDROCK_REGION` from the environment.
It imports `langchain_aws` only inside the `complete` method.
This keeps tests clean: the import never runs at test time.

### Validator

The validator runs three checks in order.

1. **No-match check.** If retrieval returned `no_match`, refuse immediately.
2. **Version-conflict check.** If two chunks share the same `sop_id` but carry different `version` values, refuse.
3. **Quote check.** If the composer's `quote` is not a verbatim substring of any retrieved chunk, refuse.

Every refusal carries a list of source links built from `BOOKSTACK_URL` and the `sop_id` metadata keys.
When `BOOKSTACK_URL` is absent, links use a relative path.

## The four traps

The corpus contains five seeded trap pages.
Phase 3 tests all four trap categories.

| Trap | Pages involved | What it tests |
|---|---|---|
| Version conflict | `sop-restocking-fee` (v1) + `sop-restocking-fee-current` (v2), same `sop_id` | Validator refuses when same page has two version numbers in the result set |
| Conflicting pair | `sop-vip-escalation-ops` + `sop-vip-escalation-finance` | Validator refuses when LLM fabricates a quote not found in either chunk |
| Keyword decoy | `sop-cod-remittance-deadlines` | Validator refuses when retrieved chunk is topically adjacent but the LLM hallucinates a quote from a different SOP |
| Unanswerable | (no SOP matches) | Retrieval returns `no_match`; validator refuses with no source links |

## Why it is built this way

**Offline-first tests.**
Tests inject `SearchResult` directly and use `MockLLM`.
No network call is made during `uv run pytest`.

**Deterministic refusal, not probabilistic.**
The validator uses substring match and metadata comparison.
There is no confidence threshold.
Either the quote is verbatim or the answer is refused.

**`LLMProvider` as a protocol.**
The mock and live paths share one interface.
Swapping from `MockLLM` to `BedrockLLM` is a one-line change and needs no patching.

**`BedrockLLM` with lazy import.**
`langchain_aws` is imported inside `complete`, not at module load.
Tests never import Bedrock code.
Credentials are never checked at import time.

**Eval as a runnable module.**
`uv run python -m shippy.eval` runs the same five cases as the test suite.
It loads corpus text from `scripts/corpus/sops.json` directly.
No live Chroma index is needed.
The eval is deterministic and offline.

## What you can do now

```bash
uv run pytest tests/test_contract.py   # 5 tests, all pass
uv run python -m shippy.eval           # pass rate: 5/5
```

Every answer Shippy returns now carries a verbatim quote.
Every refusal carries a source link.
Phase 4 can wire this contract behind a REST endpoint.

---
*Created: 2026-10-15*
