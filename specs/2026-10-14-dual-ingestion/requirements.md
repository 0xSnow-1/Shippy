# Requirements - Phase 2: Dual ingestion

## Context

Shippy answers procedural questions with citations.
Phase 2 builds the index that phase 3 searches.
The roadmap marks MVP phases 2-6 as sequential.
Phase 2 blocks every later phase.

Ingestion is the build step of Shippy.
It pulls wiki pages from BookStack and writes them into a search index.
A chunk is one block of page text.
Phase 3 returns chunks as search results.
The index lives in Chroma.
Chroma is an embedded vector store: it writes to a folder and needs no server process.

Phase 1 seeded our own BookStack instance on 2026-10-09.
It holds 24 pages: 18 SOPs in book `operations-sops`, 6 profiles in book `client-profiles`.
All five trap pages live in those books.
The trap metadata (`version`, `updated_at`) comes from this phase.

Repository state at spec time, 2026-10-14:

- `shippy/` holds only `__init__.py`.
- `scripts/seed_bookstack.py` and `scripts/corpus/` seed the instance.
- `chromadb` 1.5.9 is installed since phase 0.
- `.gitignore` has no `data/` entry.
- The branch is `spec/phase-2-sop-ingestion`.

Tech choices come from `specs/constitution/tech-stack.md`.
Embeddings use Chroma's default local embedding function.
It needs no API key.
The roadmap defines the phase: pull, export, strip, chunk, embed, verify.
Sources: `specs/constitution/roadmap.md` Phase 2, `prd.md` section "1. Ingestion pipeline", `docs/dataflow.md` part 1.

The builder answered six questions in the interview on 2026-10-14.
The answers are decisions D2 to D7.

## Scope

### In scope

1. REST pull of both books, with pagination, via the BookStack API.
2. Markdown export per page via `GET /api/pages/{id}/export/markdown`.
3. Boilerplate strip: the export's `# Title` line.
4. Heading-based chunking at h2 boundaries.
5. Two Chroma collections: `sops` and `clients`.
6. Metadata on every chunk: id, version, updated_at, title, book.
7. One CLI entry: `uv run python -m shippy.ingest`.
8. Fail-loudly errors that name the failing page slug.
9. Offline tests: HTTP mocked with `respx`, fake embeddings, temp index folder.
10. One `.gitignore` entry: `data/`.

### Out of scope

- Retrieval, ranking, and the relevance floor (phase 3).
- Any REST API code (phase 4).
- Scheduled re-ingestion (post-MVP CI gate).
- Incremental ingestion. Every run rebuilds both collections.
- A configurable index path. The path is fixed at `data/chroma`.
- New dependencies in `pyproject.toml`.
- Real company data or real personal data.

## Decisions

**D1 - Scope is roadmap Phase 2 deliverables only.**
The builder confirmed this choice in the 2026-10-14 interview.
Nothing extra enters this phase.

**D2 - The index lives at `data/chroma/` and git ignores it.**
Answer 1 of the interview.
The folder persists on disk, so phase 3 opens the same folder in another process.
`data/` never enters git.

**D3 - Chunking splits at h2, and each chunk starts with its heading path.**
Answer 2 of the interview.
The heading path is the first line of the chunk: `Title > Section`, joined with ` > `.
Text before the first h2 becomes its own chunk.
The section's own `## ` line leaves the body; the path line replaces it.
Body words stay verbatim.
Chunk ids are deterministic: `{slug}#{n}`, counting from 0.

**D4 - Every run drops both collections and rebuilds them.**
Answer 3 of the interview.
A page deleted in the wiki vanishes from the index.
No stale chunk can survive a re-run.

**D5 - Every chunk carries five metadata keys.**
Answer 4 of the interview.
The id field holds the page slug, which covers the promised slug key.
`sops` chunks use key `sop_id`, `clients` chunks use key `client_id`.
The other four keys are shared: `version` (the page's `revision_count`), `updated_at`, `title`, `book` (the book slug).
Phase 3 builds wiki links from the id and `BOOKSTACK_URL`.

**D6 - The live CLI uses Chroma's default local embedding function. Tests inject a fake.**
Answer 5 of the interview.
The default function downloads one small model file on first use.
Tests pass a deterministic fake embedding function, so `pytest` runs offline and fast.
The embedding function sits behind one parameter, so it stays swappable.

**D7 - The ingest code is one module: `shippy/ingest.py`.**
Answer 6 of the interview.
`shippy/env.py` holds the tiny `.env` loader, reused by later phases.
The loader follows the phase 1 pattern: built-in parsing, no `python-dotenv`.

**D8 - Ingestion fails loudly.**
Any missing env variable, missing book, HTTP error, or format drift raises `IngestError`.
The message names the variable, the book slug, the page slug, or the status code.
`main` prints `error: {message}` to stderr and exits 1.
Format drift means the export does not start with `# {title}`, or a stripped page has no section.

**D9 - The test suite needs no network and no running BookStack.**
HTTP is mocked with `respx`.
Embeddings are faked.
The index writes to a `tmp_path` folder.
This keeps phase 3's offline guarantee intact from day one.

## Deliverable files

- `shippy/ingest.py`
- `shippy/env.py`
- `tests/test_ingest.py`
- `.gitignore` (edited: `data/` added)

## Open questions

- [x] Exact first-line format of the pinned BookStack markdown export.
  Probe it live in plan group 2 and record the result in the plan notes.
- [ ] Should `scripts/demo.sh` (post-MVP) override the index path with an env var?
  Resolve when `demo.sh` is built.

---
*Created: 2026-10-14*
