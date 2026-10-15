# Requirements - Phase 3: Retrieval, citation contract, evals

## Context

Shippy answers procedural questions with citations.
Phase 2 built the search index.
Phase 3 adds the layer that searches the index and produces cited answers.

A retrieval call takes a natural-language question and returns the top-k matching chunks.
A chunk is the unit of stored text from phase 2.
The composer sends the chunks to an LLM and produces a structured answer.
The validator checks that the answer is safe to return.

The roadmap marks Phase 3 as the first MVP phase that produces an answer.
Phases 4-6 depend on this contract being correct.

Repository state at spec time, 2026-10-15:

- `shippy/` holds `__init__.py`, `env.py`, `ingest.py`.
- Two Chroma collections exist: `sops` (54 chunks) and `clients` (18 chunks).
- All five trap slugs are indexed.
- `langchain-aws`, `chromadb`, and `langgraph` are installed since phase 0.
- No HTTP surface exists yet (phase 4).

## Scope

### In scope

1. `search_sop`: natural-language query in, top-k chunks out, `no_match` status below the relevance floor.
2. Dense retrieval from `sops` only. The `clients` collection is indexed but never routed.
3. Answer composer: one LLM call, structured output `{answer, quote, proposed_action}`.
4. Provider interface with `MockLLM` (offline) and a Bedrock live path.
5. Deterministic validator: verbatim substring check, version-conflict refusal, `no_match` refusal.
6. Refusal payload carries wiki source links.
7. Eval runner: `uv run python -m shippy.eval` prints pass rate; every trap case refuses.
8. `tests/test_contract.py`: four trap cases plus one happy path, all offline.
9. Phase spec files: `plan.md`, `requirements.md`, `validation.md`.
10. Phase guide: `docs/phase-guides/phase-3-retrieval-and-evals.md`.
11. Updated README table in `docs/phase-guides/README.md`.

### Out of scope

- FastAPI or any HTTP surface (phase 4).
- Workflow state, audit log, Asana (phase 5).
- Slack or Gmail adapters (phase 6).
- Hybrid BM25 + RRF fusion (post-MVP backlog).
- Retrieval from the `clients` collection.
- Any scheduled or incremental ingestion.

## Decisions

**D1: Relevance floor.**
Chroma returns a distance score.
Lower distance means closer match.
The floor is a maximum allowed distance.
Chunks above the floor return `no_match`.
Value: `1.0` (Chroma L2 distance; tuned against the corpus so trap queries land above it).

**D2: Provider interface.**
`LLMProvider` is a protocol with one method: `complete(prompt) -> str`.
`MockLLM` implements it with canned JSON.
`BedrockLLM` implements it with `ChatBedrockConverse`.
`BedrockLLM` imports without credentials and is instantiated only when selected by environment variable.

**D3: Structured answer format.**
The composer sends the retrieved chunks and the query to the LLM.
The LLM returns JSON with three keys: `answer`, `quote`, `proposed_action`.
The composer parses and returns this as a dataclass.

**D4: Version-conflict detection.**
When the top-k results contain two or more chunks with the same section heading path but different versions, the validator refuses.
The conflict check compares the `sop_id` metadata key for chunks with different `version` values.

**D5: Verbatim quote check.**
The validator checks that `quote` is a verbatim substring of one of the retrieved chunk texts.
If no chunk contains the quote, the validator refuses.

**D6: Refusal payload.**
Every refusal returns `{status: "refused", reason: str, sources: list[str]}`.
`sources` is a list of wiki URLs built from `BOOKSTACK_URL` and the chunk `sop_id`.
When `BOOKSTACK_URL` is absent, sources use a relative path.

**D7: MockLLM design.**
`MockLLM` takes a `responses` dict mapping query substring to JSON string.
The `complete` method matches the first query substring found.
If none match, it raises `ValueError`.
This lets each test control the LLM response without patching.

**D8: Eval corpus.**
The eval runner builds an in-memory Chroma collection from the corpus JSON files.
It does not read from `data/chroma` at runtime.
This keeps the eval deterministic and offline.

**D9: Chroma embedding for tests and eval.**
Tests and the eval runner use the same `FakeEmbeddingFunction` class from `test_ingest.py`.
To avoid duplication, the function is extracted into `shippy/_fake_embeddings.py` and used by both.
Wait - this adds production code for a test concern.
Better: duplicate the minimal class in `tests/helpers.py` and import it in `test_contract.py` and in `shippy/eval.py`.
The eval module lives under `shippy/` as a runnable module.
A shared test helper under `tests/` is not imported by `shippy/eval.py`.
Resolution: put the fake embedding class in `shippy/eval.py` only, and import it in `tests/test_contract.py`.
This keeps eval self-contained and avoids a test-concern module in the package.

**D10: No confidence threshold.**
The roadmap explicitly removes the confidence threshold.
`no_match` is the only floor: distance-based, binary.
No probabilistic scoring.

## Open questions

None. All blocking questions resolved by the roadmap and existing decisions.

## Deliverable files

| File | Purpose |
|---|---|
| `shippy/retrieve.py` | `search_sop` function, relevance floor |
| `shippy/compose.py` | Answer composer, `LLMProvider` protocol, `MockLLM`, `BedrockLLM` |
| `shippy/validate.py` | Deterministic validator |
| `shippy/eval.py` | Eval runner, `__main__` entry |
| `tests/test_contract.py` | Four trap cases plus happy path |
| `specs/2026-10-15-phase-3-retrieval/` | This spec directory |
| `docs/phase-guides/phase-3-retrieval-and-evals.md` | Phase guide |
| `docs/phase-guides/README.md` | Updated table |
