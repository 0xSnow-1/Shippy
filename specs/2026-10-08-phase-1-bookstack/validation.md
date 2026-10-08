# Validation - Phase 1: Self-hosted BookStack

## Definition of done

Phase 1 is ready to merge when:

- All six gates below pass on the feature branch.
- Every merge criterion is checked.

## Gates

### Gate 1 - roadmap verify (curl with token)

Setup: the stack is running, and `.env` holds a valid token.

Load the environment first:

```bash
set -a; . ./.env; set +a
```

Command:

```bash
curl -s -H "Authorization: Token $BOOKSTACK_TOKEN" localhost:8080/api/pages
```

Pass condition: HTTP 200, a non-empty JSON list, and the four trap slugs present.

What a failure means:

- `curl: connection refused` means the stack is down or the port differs. Run `docker compose ps`.
- HTTP 401 means the token is missing or malformed. Format is `Token id:secret`.
- An empty list means the seed script has not run. Run it.

### Gate 2 - idempotent re-run

Command: `uv run python scripts/seed_bookstack.py`, run twice in a row.

Pass condition: the first run creates pages. The second run reports created 0, and the page count is unchanged.

### Gate 3 - test suite

Command: `uv run pytest`

Pass condition: exit code 0, including the new corpus and seed tests.

### Gate 4 - lint

Command: `uv run ruff check .`

Pass condition: no findings, exit code 0.

### Gate 5 - no secrets in git

Checks:

- `git status` never lists `.env`.
- `git check-ignore .env` prints `.env`.
- No changed file contains your token string. Search for the token id.

### Gate 6 - cold start (fresh volumes)

Procedure: `docker compose down -v`, then `docker compose up -d`, complete the group 2 setup again, seed twice, then run Gate 1.

Pass condition: the whole path works from zero.

Warning: `-v` deletes the database.
The admin account and the old token die with it.
Mint a new token after the wipe.

## Procedure

Run these from the project root, in order:

```bash
docker compose up -d
set -a; . ./.env; set +a
uv run python scripts/seed_bookstack.py
uv run python scripts/seed_bookstack.py
curl -s -H "Authorization: Token $BOOKSTACK_TOKEN" localhost:8080/api/pages
uv run pytest
uv run ruff check .
git status
```

Every command must return exit code 0.

## Merge criteria

- [ ] Gate 1 returns the seeded pages, trap slugs included.
- [ ] Gate 2 second run creates 0 pages.
- [ ] Gate 3 returns exit code 0.
- [ ] Gate 4 returns exit code 0.
- [ ] Gate 5 is clean: no `.env` in git, no token in any changed file.
- [ ] Gate 6 cold start passes from fresh volumes.
- [ ] Image tags in `requirements.md` D2 are explicit versions, not `latest`.
- [ ] The trap inventory in `requirements.md` matches the corpus slugs.
- [ ] Changed files match the deliverable list in `requirements.md`.

## Evidence

Save the Gate 1 page count, the Gate 2 summary lines, and the Gate 3 and Gate 4 output.
Put them in the PR description or the phase log.

## Failure triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl: connection refused` | Stack down, or wrong port | `docker compose ps`, check the `8080:80` mapping |
| HTTP 401 from the API | Bad or missing token | Re-mint in the UI, fix `.env`, format `Token id:secret` |
| Seed script waits, then times out | Migrations failed or slow | `docker compose logs bookstack` |
| Seed script gets 401 | Token not loaded into the environment | Run `set -a; . ./.env; set +a` first |
| Duplicate pages on re-run | Slug lookup is broken | Check `GET /api/pages/{slug}` on the pinned version. Fall back to search |
| Port 8080 already in use | Another service holds the port | Stop it. The roadmap pins 8080 |
| `ruff` findings in `scripts/` | Style issues | Fix, then re-run |
| Corpus test fails on counts | JSON edited badly | Fix `scripts/corpus/*.json` |

---
*Created: 2026-10-08*
