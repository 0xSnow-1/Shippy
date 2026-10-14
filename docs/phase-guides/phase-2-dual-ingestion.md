# Phase 2: Dual ingestion

## What problem this solves

Phase 1 filled the wiki with 24 pages.
Nothing could search them yet.
Reading all 24 pages on every question would be slow.

This phase builds the index.
Ingestion means: pull the pages once, cut them into chunks, and store them for search.
A chunk is one block of page text.
Phase 3 will search those chunks.

## The one-sentence version

One command pulls every page from both books, cuts each page at its headings, and stores the chunks for search.

## What we built

| Piece | File | Job |
|---|---|---|
| Ingest pipeline | `shippy/ingest.py` | One module: pull, strip, chunk, embed, verify. |
| Env loader | `shippy/env.py` | Reads `.env` into the process. |
| Index folder | `data/chroma/` | Holds the stored chunks. Git ignores it. |
| Tests | `tests/test_ingest.py` | 17 offline tests. |
| Ignore rule | `.gitignore` | Keeps `data/` out of git. |

### The pipeline in six steps

| # | Step | Plain words |
|---|---|---|
| 1 | Pull | Ask BookStack for both books, then every page in each book. |
| 2 | Export | Ask BookStack for each page as markdown text. |
| 3 | Strip | Delete the export's title line. |
| 4 | Chunk | Cut each page at its `## ` headings. |
| 5 | Embed and store | Turn chunks into embeddings and save them in two collections. |
| 6 | Verify | Read every stored chunk back and compare it. |

**Markdown** is plain text with `##` heading marks.
**Chroma** is the search index that holds the chunks.
An **embedding** is a list of numbers built from text.
Similar meanings end up close together in that list.
A **collection** is one table of chunks inside Chroma.

### The two collections

| Collection | Book | Pages | Chunks |
|---|---|---|---|
| `sops` | `operations-sops` | 18 | 54 |
| `clients` | `client-profiles` | 6 | 18 |
| both | both books | 24 | 72 |

Every live run prints those counts.
It finishes with `round-trip: 72 chunks verified with metadata`.

## Why it is built this way

**One module, one command.**
`uv run python -m shippy.ingest` runs the whole pipeline.
No framework sits around it.
Phase 3 never imports this file.
It opens the index folder instead.

**Two collections, not one.**
SOP questions and client questions come from different books.
Two collections keep the answers separated.
Phase 3 searches `sops` first.
The pipeline stores client chunks, but nothing routes them yet.

**Chunking at `## ` headings.**
Phase 1 wrote every body with `## ` section headings.
Those headings give the chunker natural cut points.
One chunk holds one section, so no section is split in half.
Text before the first heading becomes its own chunk.

**The heading path line.**
Each chunk starts with `Title > Section`.
A search result shows one chunk without its page around it.
That first line tells the reader where the text came from.

**Chunk ids are `{slug}#{n}`.**
A **slug** is a page's short name in its URL, like `sop-restocking-fee`.
`n` counts from 0.
The same page always produces the same ids.
A reviewer can find any chunk in the index by name.

**Full rebuild on every run.**
Each run deletes both collections, then rebuilds them.
A page deleted in the wiki vanishes from the index.
No stale chunk survives a re-run.

**Metadata on every chunk: five keys.**

| Key | Holds | Why it matters |
|---|---|---|
| `sop_id` or `client_id` | The page slug | Phase 3 builds the wiki link from it. |
| `version` | How many saved versions the page has | Shows which saved version the text came from. |
| `updated_at` | Last edit timestamp | Separates old text from current text. |
| `title` | The page title | Names the source without a second lookup. |
| `book` | The book slug | Says which book the page came from. |

The `sops` collection uses `sop_id`.
The `clients` collection uses `client_id`.
Both collections carry the other four keys.

**Chroma, embedded.**
**Embedded** means Chroma runs inside our process and writes to a folder.
There is no server process to start.
Phase 3 opens the same folder and reads the same chunks.

**The default local embedding function.**
Chroma's default function runs on our own machine.
It needs no API key.
It downloads one small model file on first use.
Later runs need no network.
Tests inject a fake embedding, so `pytest` runs offline and fast.

**Fail loudly.**
Every error names what failed: a variable, a book, or a page slug.
The run prints `error: {message}` to stderr and exits 1.
A silent partial index would answer questions from missing pages.
**Format drift** means the export shape changed from what we expect.
Drift stops the run instead of corrupting the index.

**The round-trip check.**
**Round-trip** means: write the chunks in, read them back, then compare.
The comparison checks counts and all five metadata keys.
A mismatch raises an error naming the collection.
The run prints nothing until every chunk verifies.

**`.env` stays out of the code.**
`shippy/env.py` reads `KEY=VALUE` lines into the process environment.
It never overwrites a variable that is already set.
Shell exports win over file values.
We need no third-party library.

## The use case, as you

You maintain the SOPs in the wiki at `localhost:8080`.

Step 1. You edit a page and save it.
Step 2. You run `uv run python -m shippy.ingest`.
Step 3. The pipeline pulls all 24 pages and rebuilds the index.
Step 4. The three count lines tell you what the run stored.

If you delete a page, the next run leaves it out.
If a page has no section headings, the run fails and names it.

Without this phase, every question would need a live read of the whole wiki.

## What each piece does for you

| Piece | Your benefit |
|---|---|
| The one command | Rebuilds the whole index while you watch the counts. |
| The two collections | Keeps SOP text apart from client text. |
| The five metadata keys | Let a later answer link back to its wiki page. |
| The count lines | Prove what entered the index on this run. |
| The round-trip check | Catches a bad write before it serves a wrong answer. |
| The `data/` ignore rule | Keeps the index and secrets out of git. |

## The six gates

Gates are proof commands.
All six pass.

| Gate | Command | Result |
|---|---|---|
| 1 | `uv run python -m shippy.ingest` | exit 0, three count lines, metadata sample holds all five keys |
| 2 | Run the ingest twice | Both runs print identical counts |
| 3 | `uv run pytest` | 28 passed |
| 4 | `uv run ruff check .` | clean |
| 5 | `git status`, `git check-ignore data/chroma` | Neither `.env` nor `data/` is tracked |
| 6 | `docker compose stop`, then `uv run pytest` | Tests pass with the stack down |

Gate 6 is the important one.
It proves the tests mock BookStack and fake the embeddings.
The suite never touches the network.

Gate 5 proves the index never enters git.
`data/` and `.env` both stay ignored.

## How to run it yourself

```bash
docker compose up -d
set -a; . ./.env; set +a
uv run python -m shippy.ingest
uv run pytest
uv run ruff check .
```

The first live run downloads the embedding model into `~/.cache/chroma/`.
That download needs network once.
Every later run needs none.

To see the stored metadata, read one chunk back:

```bash
uv run python -c "
import chromadb
client = chromadb.PersistentClient('data/chroma')
sops = client.get_collection('sops')
print('sops:', sops.count())
print(sops.get(limit=1, include=['metadatas'])['metadatas'][0])
"
```

## What you can do now

- Run one command and get a verified index of all 24 pages.
- Read three count lines and know exactly what the run stored.
- Delete a page in the wiki, re-run, and watch it leave the index.
- Trust that every stored chunk carries its five metadata keys.
- Run the full test suite with the stack stopped.

## What this unlocks

Phase 3 searches these collections.
It reads `sops`, ranks the chunks, and answers with a quote and a link.
The `version` and `updated_at` keys let phase 3 check the stale-SOP trap from phase 1.

---
*Created: 2026-10-15*
