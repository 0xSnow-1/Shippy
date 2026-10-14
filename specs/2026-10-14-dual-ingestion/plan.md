# Plan - Phase 2: Dual ingestion

Feature directory: `specs/2026-10-14-dual-ingestion`
Branch: `spec/phase-2-sop-ingestion`
Roadmap source: `specs/constitution/roadmap.md`, Phase 2

This plan has 6 numbered task groups.
Each group ends with one verify step.
Finish the verify step before you start the next group.
Run all commands from the project root.

## 1. Prepare the index folder and the env loader

Goal: the index has a home on disk, and the code can read `.env`.

- [x] Create `shippy/env.py`.
- [x] Write one function `load_env(path=".env")`.
- [x] The function parses `KEY=VALUE` lines and sets `os.environ` entries.
- [x] The function never overwrites a variable that is already set.
- [x] A missing `.env` file is not an error. The CLI reports a missing variable later.
- [x] Add `data/` to `.gitignore`.
- [x] Create `shippy/ingest.py`.
- [x] In `shippy/ingest.py`, define `CHROMA_PATH = Path("data/chroma")`.
- [x] Confirm `git check-ignore data/chroma` prints `data/chroma`.

Verify: `uv run python -c "from shippy.env import load_env; load_env(); print('env ok')"` prints `env ok`, and `git check-ignore data/chroma` prints the path.

## 2. Fetch pages from both books

Goal: the pipeline reads both books and exports every page as Markdown.

- [x] Define `class IngestError(Exception)` in `shippy/ingest.py`.
- [x] Define the `BOOKS` constant. It maps book slug to `(collection name, id key)`:
      `operations-sops` gives `("sops", "sop_id")`, `client-profiles` gives `("clients", "client_id")`.
- [x] Load `BOOKSTACK_URL` and `BOOKSTACK_TOKEN` through `load_env`.
- [x] If either variable is missing, raise `IngestError` naming the variable.
- [x] Write `resolve_books(client)`. It calls `GET /api/books`.
- [x] It returns a dict of book slug to book id for the two slugs in `BOOKS`.
- [x] If a book slug is absent, raise `IngestError` naming the slug.
- [x] Write `fetch_pages(client, book_id)`. It calls `GET /api/pages?page={n}&count=100`.
- [x] Follow `page` until a response holds fewer than 100 items.
- [x] Keep only pages whose `book_id` matches. Sort the result by slug.
- [x] Write `export_markdown(client, page_id)`. It calls `GET /api/pages/{page_id}/export/markdown`.
- [x] Raise `IngestError` on a non-2xx response. The message holds the page slug and the status code.
- [x] Probe one live export now. Record its first three lines in the Notes section below.
- [x] Confirm the first line is `# {title}`.
- [x] Create `tests/test_ingest.py`. Mock all HTTP with `respx`.
- [x] Test: both books resolve from a mocked `GET /api/books`.
- [x] Test: a missing book raises with the slug in the message.
- [x] Test: pagination stops after a short page.
- [x] Test: a 404 export raises with the slug in the message.

Verify: with the stack up and `.env` loaded, the probe below prints `operations-sops 18`, `client-profiles 6`, and an export that starts with `# `. Then `uv run pytest tests/test_ingest.py` passes.

```bash
set -a; . ./.env; set +a
uv run python - <<'PY'
from shippy.env import load_env
load_env()
import os, httpx
from shippy.ingest import resolve_books, fetch_pages, export_markdown
headers = {"Authorization": "Token " + os.environ["BOOKSTACK_TOKEN"]}
with httpx.Client(base_url=os.environ["BOOKSTACK_URL"], headers=headers, timeout=30) as client:
    books = resolve_books(client)
    for slug, book_id in books.items():
        pages = fetch_pages(client, book_id)
        print(slug, len(pages))
    sample = pages[0]
    text = export_markdown(client, sample["id"])
    print("export first lines:", text.splitlines()[:3])
PY
```

## 3. Strip boilerplate and chunk on headings

Goal: a pure text transform with unit tests and no network.

- [x] Write `strip_boilerplate(markdown, title)` in `shippy/ingest.py`.
- [x] It deletes the leading `# {title}` line.
- [x] It deletes blank lines that sit directly under that line.
- [x] If the first line is not `# {title}`, raise `IngestError`. Format drift stops the run.
- [x] Write `chunk_page(page, book_slug, markdown, id_key)`.
- [x] It calls `strip_boilerplate` first.
- [x] It returns a list of dicts with keys `id`, `text`, `metadata`.
- [x] A chunk boundary is an h2 line (`## `).
- [x] Text before the first h2 becomes one chunk with id `{slug}#0`.
- [x] Every h2 section becomes one chunk with id `{slug}#{n}`. `n` counts from 0.
- [x] The first line of each chunk text is the heading path. Join the parts with ` > `.
- [x] The path holds the page title and the section heading text.
- [x] Remove the section's own `## ` line from the body. The path line replaces it.
- [x] Body words stay verbatim.
- [x] The metadata dict holds `{id_key: slug}`, `version` (the page's `revision_count`), `updated_at`, `title`, and `book` (the book slug).
- [x] A stripped page with no h2 and no text raises `IngestError`.
- [x] Tests cover: title line removed, wrong title rejected, three sections make three chunks, ids are stable, the path line is exact, the preamble chunk exists when text precedes the first h2, and missing sections raise.

Verify: `uv run pytest tests/test_ingest.py` passes.

## 4. Write chunks into two Chroma collections

Goal: chunks are stored once and read back with metadata.

- [x] Write `write_collection(chunks, name, path, embedding_fn=None)`.
- [x] Open `chromadb.PersistentClient(path=path)`.
- [x] Apply the drop rule: delete collection `name` when it exists, then create it.
- [x] Pass `embedding_fn` to the collection only when it is not `None`.
- [x] `None` means Chroma's default local embedding function.
- [x] Call `add` once with the ids, texts, and metadata dicts from the chunks.
- [x] After `add`, read every id back with `get` and compare count and metadata.
- [x] A mismatch raises `IngestError` naming the collection.
- [x] Tests use `tmp_path` as the Chroma folder.
- [x] Tests pass a fake embedding function: a fixed-size deterministic vector per document.
- [x] Test: a second `PersistentClient` on the same path reads the metadata back.
- [x] Test: writing twice keeps only the second write (the drop rule).

Verify: `uv run pytest tests/test_ingest.py` passes.

## 5. Wire the CLI entry point

Goal: one command runs the whole pipeline and reports both counts.

- [x] Write `main(embedding_fn=None, path=CHROMA_PATH)` in `shippy/ingest.py`.
- [x] `main` loads env, opens one `httpx.Client`, resolves books, fetches and exports every page, chunks, and writes each collection.
- [x] `main` catches `IngestError` and `httpx.HTTPError`. It prints `error: {message}` to stderr and returns 1.
- [x] On success, `main` returns 0.
- [x] Print `sops: {chunks} chunks from {pages} pages`.
- [x] Print `clients: {chunks} chunks from {pages} pages`.
- [x] Print `round-trip: {chunks} chunks verified with metadata`.
- [x] Add `if __name__ == "__main__": raise SystemExit(main())`.
- [x] Test `main` offline: `respx` HTTP, fake embedding, `tmp_path` folder, monkeypatched environment.
- [x] The test asserts exit code 0, the three printed lines, and both collection counts.

Verify: `uv run pytest` passes the whole suite, and `uv run ruff check .` reports no findings.

## 6. Run the roadmap check

Goal: the roadmap verify command for Phase 2 passes.

- [x] Start the stack: `docker compose up -d`.
- [x] Load `.env`: `set -a; . ./.env; set +a`.
- [x] Run `uv run python -m shippy.ingest`. Record both counts in the Notes section.
- [x] Run it a second time. The counts match the first run.
- [x] Run the metadata snippet in `validation.md` Gate 1. The sample metadata holds all five keys.
- [x] Run the full gates: `uv run pytest`, `uv run ruff check .`, `uv run python -c "import shippy"`.
- [x] Check for leaks: `git status` lists neither `.env` nor `data/`. No changed file contains the token id.
- [x] Tick the Phase 2 verify box in `specs/constitution/roadmap.md`.

Verify: every command above returns exit code 0, and the ingest output prints non-zero counts for `sops` and `clients`.

## Notes

Record implementation findings here: the observed export format, the actual chunk counts, and the first-run model download time.

- Live export probe, 2026-10-14.
  The export came from page `client-profile-bramblewick-retail`.
  Its first three lines were `# Client Profile - Bramblewick Retail`, an empty line, `## Account`.
  The first line is `# {title}` as the plan expects.
- The phase 1 volumes were gone on 2026-10-14.
  I re-created the admin with `bookstack:create-admin`.
  I minted a new API token over HTTP and wrote it into `.env`.
  The seed script then printed `created=24 skipped=0 failed=0`, then `created=0 skipped=24 failed=0`.
- BookStack page objects call the title field `name`.
  `chunk_page` reads `page["name"]` and stores it under the metadata key `title`.
- Live ingest run 1, 2026-10-14: `sops: 54 chunks from 18 pages`, `clients: 18 chunks from 6 pages`, `round-trip: 72 chunks verified with metadata`.
  Exit code 0, elapsed 17 seconds.
- Live ingest run 2, 2026-10-14: identical counts (54, 18, 72).
  Exit code 0.
- The local embedding model was already in `~/.cache/chroma/onnx_models/` from 2026-10-09.
  No model download ran on 2026-10-14.
- Gate 1 metadata sample: `{'updated_at': '2026-10-14T14:39:07.000000Z', 'version': 1, 'book': 'operations-sops', 'sop_id': 'sop-address-correction', 'title': 'SOP - Address Correction'}`.
  All five keys are present.

---
*Created: 2026-10-14*
