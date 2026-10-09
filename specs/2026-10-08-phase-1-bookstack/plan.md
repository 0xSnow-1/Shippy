# Plan - Phase 1: Self-hosted BookStack

Feature directory: `specs/2026-10-08-phase-1-bookstack`
Branch: `spec/phase-1-bookstack`
Roadmap source: `specs/constitution/roadmap.md`, Phase 1

This plan has 6 numbered task groups.
Each group ends with one verify step.
Finish the verify step before you start the next group.
Run all commands from the project root.

## 1. Build the Docker Compose stack

Goal: one command starts BookStack with its database.

- [x] Create `docker-compose.yml` at the project root.
- [x] Add a `bookstack` service. Use the official image with an explicit version tag. Never use `latest`.
- [x] Add a `db` service for MariaDB, also with an explicit version tag.
- [x] Publish the BookStack port as `8080:80`. Host port 8080 matches the roadmap verify command.
- [x] Do not publish the MariaDB port to the host. The database stays on the internal Compose network.
- [x] Add named volumes for BookStack uploads and for database data.
- [x] Give `db` a healthcheck. Make `bookstack` wait with `depends_on: condition: service_healthy`.
- [x] Set `APP_URL=http://localhost:8080` and the four `DB_*` variables pointing at the `db` service.
- [x] Set the database password to `${BOOKSTACK_DB_PASSWORD:-shippy-local-dev}`. The default keeps a fresh clone working with no `.env`.
- [x] Add `BOOKSTACK_DB_PASSWORD=` (empty value) to `.env.example`.
- [x] Write the chosen image tags into `requirements.md`, decision D2.

Verify: `docker compose up -d` starts both services, and `curl -fsS localhost:8080` returns HTTP 200.

## 2. Mint the API token (manual admin UI)

Goal: we hold our own token for our own instance.

This group needs human clicks.
BookStack offers no API for token creation.

- [x] Copy `.env.example` to `.env`. Confirm `git check-ignore .env` lists it.
- [x] Run `docker compose up -d`. Open `http://localhost:8080`.
- [x] Set the admin account on our own instance. We are the instance admin.
- [x] Open Your Account, then Authentication, then the API Tokens section, then Create Token.
- [x] Copy the token into `.env` as `BOOKSTACK_TOKEN`. Its format is `id:secret`.
- [x] Set `BOOKSTACK_URL=http://localhost:8080` in `.env`.
- [x] Never commit `.env`. Never paste the token into any other file.

Notes from the run on 2026-10-09:

- The token path is Your Account -> Authentication, not the profile page.
- `linuxserver/bookstack:26.09.1` has no "Access System API" checkbox.
  API permissions follow the user account instead.
- This image has no web installer.
  `GET /install` returns 404 on a fresh volume.
  The image seeds an `Admin` row, and `bookstack:create-admin --initial` sets its details.
  The local password is `shippy-local-admin`.
  Gate 6 uses that command and that password.
- The token is minted by driving the admin UI over HTTP.
  The secret is shown once, on the redirect after the create form.
  It is read from that page and written straight into `.env`.
- The plan originally verified with `/api/users/me`.
  That route does not exist in the pinned version.
  The verify command below uses `/api/users/1` instead.

Verify: with `.env` loaded (`set -a; . ./.env; set +a`), this command returns admin user JSON:

```bash
curl -s -H "Authorization: Token $BOOKSTACK_TOKEN" "$BOOKSTACK_URL/api/users/1"
```

## 3. Write the seed script skeleton

Goal: one Python entrypoint fills the instance, and re-runs are safe.

- [x] Create `scripts/seed_bookstack.py`.
- [x] Read `BOOKSTACK_URL` and `BOOKSTACK_TOKEN` from the environment. Load `.env` with a small built-in parser (about 10 lines). Add no new dependency to `pyproject.toml`.
- [x] Wait for the API before seeding: poll `GET /api/pages` until it returns 200, timeout 120s. First boot runs database migrations.
- [x] Resolve the two books by slug first: `operations-sops` and `client-profiles`. Create any missing book with the same idempotency rule as pages.
- [x] List `GET /api/pages` once and match each corpus entry by slug. Skip a hit, create a miss.
- [x] If an entry carries `revised_markdown`, send the update after all pages are created. BookStack then stores a revision. That gives the SOP its version history.
- [x] Print one summary line: created, skipped, failed counts. Exit non-zero if any request failed.
- [x] Structure the code as small functions that take an `httpx.Client`. The test below mocks that client.
- [x] Create `tests/test_seed_bookstack.py` with `respx`. One case where the page exists: assert skip, no POST. One case where it is missing: assert POST fires.

Notes from the run on 2026-10-09:

- The plan asked for `GET /api/pages/{slug}`.
  The pinned version casts `{id}` with `intval`, so a slug never resolves.
  A slug lookup must come from the `GET /api/pages` list instead.
  The same rule applies to books.
- A page slug is generated from its title.
  BookStack rejects a `slug` field on create.
  So the seed asserts that the returned slug equals the corpus slug and stops on a mismatch.
- Revisions run in a second pass after every page exists.
  That pass waits 1.1 seconds first.
  This guarantees a strictly older `updated_at` for the stale trap page.
- The live verify needs the corpus from group 4, so it ran after group 4.

Verify: with the stack up, run `uv run python scripts/seed_bookstack.py` twice. The first run creates pages. The second run creates 0 and skips everything.

Result: run 1 printed `created=24 skipped=0 failed=0`. Run 2 printed `created=0 skipped=24 failed=0`. Both exited 0.

## 4. Author the corpus

Goal: realistic fake content that later phases retrieve, quote, and score.

The trap pages from group 5 count toward the SOP total.

- [x] Create `scripts/corpus/sops.json`. Hold 15-20 SOP entries.
- [x] Give every entry `slug`, `title`, and `markdown`. Add `revised_markdown` where version history matters.
- [x] Cover e-commerce operations: returns, refunds, shipping, inventory, chargebacks, escalations, complaints, safety.
- [x] Write bodies with headings. Phase 2 chunks on headings, so headings give the chunker structure.
- [x] Give each SOP enough text to produce several chunks. Two to four headings per SOP is a good size.
- [x] Create `scripts/corpus/clients.json`. Hold 5-10 fake client profiles with the same keys.
- [x] Use clearly fictional company and person names. No real personal data. No company system data.
- [x] Create `tests/test_corpus.py`. It checks counts, required keys, and unique slugs.

Notes from the run on 2026-10-09:

- `sops.json` holds 18 SOPs and `clients.json` holds 6 profiles.
- The test also checks `slug == slugify(title)`.
  BookStack builds the slug from the title, so a mismatch would create duplicates on re-run.
  The test mirrors the slug rule of the pinned version.

Verify: `uv run pytest tests/test_corpus.py` passes.

Result: `8 passed` for the whole suite, including both corpus tests. `uv run ruff check .` reports no findings.

## 5. Plant the four traps

Goal: known bad data with recorded expected outcomes.

- [x] Stale SOP: add `sop-restocking-fee` (older `updated_at`, 10% fee) and `sop-restocking-fee-current` (newer, 0% fee). The old page is superseded.
- [x] Conflicting pair: add `sop-vip-escalation-ops` and `sop-vip-escalation-finance`. They give opposite escalation targets for the same procedure, with no version precedence.
- [x] Keyword decoy: add `sop-cod-remittance-deadlines`. It reuses the keywords of a common refund question but answers a different question.
- [x] Unanswerable question: record it in `requirements.md`. No page answers it: "What is the payout limit for the 2026 carrier insurance claim?"
- [x] Write the trap inventory into `requirements.md`: slugs, planted facts, expected behavior, consuming phase.
- [x] Extend `tests/test_corpus.py`: assert all four trap slugs exist in the corpus.

Notes from the run on 2026-10-09:

- The inventory and the unanswerable question were already in `requirements.md`.
  The test now proves they stay in step with the corpus.
- The stale page shows `updated_at=2026-10-09T05:04:35Z`.
  The current page shows `2026-10-09T05:04:44Z`.
  The stale page has `revision_count=1`, the current page has `revision_count=2`.
- The conflicting pair differs only in the escalation target.
  Both sections otherwise read the same, so no version rule can separate them.

Verify: `uv run pytest tests/test_corpus.py` passes with the trap assertions, and every trap slug in `requirements.md` matches a corpus slug.

Result: `11 passed`. The trap test reads `requirements.md` and checks every trap slug, so a mismatch fails the run.

## 6. Run the final roadmap check

Goal: the roadmap verify command for Phase 1 passes.

- [x] Restart the stack: `docker compose down`, then `docker compose up -d`.
- [x] Run the seed script twice. The second run reports 0 created.
- [x] Run the roadmap command with your token: `curl -H "Authorization: Token $ID:$SECRET" localhost:8080/api/pages`. It returns the seeded pages.
- [x] Run the full gates: `uv run pytest` and `uv run ruff check .`.
- [x] Check for leaks: `git status` shows no `.env`. No changed file contains your token.

Result from 2026-10-09:

- Restart came up healthy. The seed printed `created=0 skipped=24 failed=0` on both runs.
- The roadmap curl returned HTTP 200 with 24 pages. All five trap slugs were in the response.
- `uv run pytest` printed `11 passed`. `uv run ruff check .` printed `All checks passed!`.
- `git status` does not list `.env`. `git check-ignore .env` prints `.env`.
- Only `.env` holds the token id. No other file in the tree holds it.

Verify: every command above returns exit code 0, and the curl response lists non-zero pages including the trap slugs.

All commands returned exit code 0.

---
*Created: 2026-10-08*
