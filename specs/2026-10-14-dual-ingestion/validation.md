# Validation - Phase 2: Dual ingestion

## Definition of done

Phase 2 is ready to merge when:

- All six gates below pass on the feature branch.
- Every merge criterion is checked.

## Gates

### Gate 1 - roadmap verify (live ingest)

Setup: the stack is running, and `.env` holds a valid token.

Load the environment first:

```bash
set -a; . ./.env; set +a
```

Command:

```bash
uv run python -m shippy.ingest
```

Pass condition: exit code 0, and stdout holds all three lines:

- `sops: {n} chunks from {p} pages` with n and p above 0.
- `clients: {n} chunks from {p} pages` with n and p above 0.
- `round-trip: {n} chunks verified with metadata` with n equal to both counts summed.

Then inspect the stored metadata:

```bash
uv run python -c "
import chromadb
client = chromadb.PersistentClient('data/chroma')
sops = client.get_collection('sops')
clients = client.get_collection('clients')
print('sops:', sops.count(), 'clients:', clients.count())
print(sops.get(limit=1, include=['metadatas'])['metadatas'][0])
"
```

Pass condition: both counts are above 0, and the sample dict holds `sop_id`, `version`, `updated_at`, `title`, and `book`.

Note: the first live run downloads the local embedding model into `~/.cache/chroma/`.
It needs network once. Later runs need no network.

What a failure means:

- `connection refused` means the stack is down. Run `docker compose up -d`.
- `error: BOOKSTACK_TOKEN ...` means `.env` is not loaded. Run `set -a; . ./.env; set +a`.
- `error: book ...` means the seed script has not run. Run `uv run python scripts/seed_bookstack.py`.
- `error: ... format drift ...` means the export shape changed. Record the actual shape in the plan notes.

### Gate 2 - re-run rule

Command: `uv run python -m shippy.ingest`, run twice in a row.

Pass condition: both runs exit 0, and both runs print the same three counts.

### Gate 3 - test suite

Command: `uv run pytest`

Pass condition: exit code 0, including the new `tests/test_ingest.py`.

### Gate 4 - lint

Command: `uv run ruff check .`

Pass condition: no findings, exit code 0.

### Gate 5 - no secrets and no index in git

Checks:

- `git status` never lists `.env` or `data/`.
- `git check-ignore data/chroma` prints `data/chroma`.
- `git check-ignore .env` prints `.env`.
- No changed file contains your token id. Search for the token id.

### Gate 6 - offline proof

Procedure: stop the stack, then run the test suite.

```bash
docker compose stop
uv run pytest
docker compose up -d
```

Pass condition: `pytest` exits 0 with the stack stopped.
This proves that tests mock BookStack and fake the embeddings.

## Procedure

Run these from the project root, in order:

```bash
docker compose up -d
set -a; . ./.env; set +a
uv run python -m shippy.ingest
uv run python -m shippy.ingest
uv run pytest
uv run ruff check .
uv run python -c "import shippy"
git status
git check-ignore data/chroma
```

Every command must return exit code 0.

## Merge criteria

- [x] Gate 1 prints both chunk counts and the round-trip line.
- [x] Gate 1 metadata sample holds all five keys.
- [x] Gate 2 second run prints identical counts.
- [x] Gate 3 returns exit code 0.
- [x] Gate 4 returns exit code 0.
- [x] Gate 5 is clean: no `.env`, no `data/`, no token in any changed file.
- [x] Gate 6 passes with the stack stopped.
- [x] Collection names in Chroma are exactly `sops` and `clients`.
- [x] Metadata keys match D5 in `requirements.md`.
- [x] Changed files match the deliverable list in `requirements.md`.
- [x] The Phase 2 verify box in the roadmap is ticked only after every gate passes.

## Evidence

Save these after the run:

- The three printed lines from Gate 1, both runs.
- The Gate 1 metadata sample dict.
- The `pytest` and `ruff` output lines.
- The Gate 6 `pytest` output with the stack stopped.

Put them in the PR description or the phase log.

## Failure triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` | Stack down | `docker compose up -d` |
| `error: BOOKSTACK_URL` or `BOOKSTACK_TOKEN` | `.env` not loaded | `set -a; . ./.env; set +a` |
| `error: book ... not found` | Seed script never ran | `uv run python scripts/seed_bookstack.py` |
| `error: ... status 401` | Token invalid or revoked | Re-mint in the admin UI, fix `.env` |
| Export first line is not `# {title}` | BookStack export format drift | Record the real shape in plan notes, adjust `strip_boilerplate`, update tests |
| Page with no `## ` section | Corpus or export changed | Read the named slug, fix the page, re-run |
| First run slow, model download error | No network, cold model cache | Run once with network, check `~/.cache/chroma/` |
| Round-trip mismatch after re-run | Drop rule broken | Check `delete_collection` path in `write_collection` |
| `data/` appears in `git status` | `.gitignore` entry missing | Add `data/` to `.gitignore` |
| Tests call the network | Fake embedding not injected | Check the test passes `embedding_fn` |
| Duplicate or stale chunks after a wiki delete | Collections not dropped | Verify the drop rule in Gate 2 |
| `ruff` findings | Style issues | Fix, then re-run |

---
*Created: 2026-10-14*
