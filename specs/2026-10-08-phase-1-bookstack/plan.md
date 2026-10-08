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

- [ ] Create `docker-compose.yml` at the project root.
- [ ] Add a `bookstack` service. Use the official image with an explicit version tag. Never use `latest`.
- [ ] Add a `db` service for MariaDB, also with an explicit version tag.
- [ ] Publish the BookStack port as `8080:80`. Host port 8080 matches the roadmap verify command.
- [ ] Do not publish the MariaDB port to the host. The database stays on the internal Compose network.
- [ ] Add named volumes for BookStack uploads and for database data.
- [ ] Give `db` a healthcheck. Make `bookstack` wait with `depends_on: condition: service_healthy`.
- [ ] Set `APP_URL=http://localhost:8080` and the four `DB_*` variables pointing at the `db` service.
- [ ] Set the database password to `${BOOKSTACK_DB_PASSWORD:-shippy-local-dev}`. The default keeps a fresh clone working with no `.env`.
- [ ] Add `BOOKSTACK_DB_PASSWORD=` (empty value) to `.env.example`.
- [ ] Write the chosen image tags into `requirements.md`, decision D2.

Verify: `docker compose up -d` starts both services, and `curl -fsS localhost:8080` returns HTTP 200.

## 2. Mint the API token (manual admin UI)

Goal: we hold our own token for our own instance.

This group needs human clicks.
BookStack offers no API for token creation.

- [ ] Copy `.env.example` to `.env`. Confirm `git check-ignore .env` lists it.
- [ ] Run `docker compose up -d`. Open `http://localhost:8080`.
- [ ] Complete the first-run screen and create the admin account. We are the instance admin.
- [ ] Open your profile, then API Tokens, then New Token. Enable the "Access System API" permission.
- [ ] Copy the token into `.env` as `BOOKSTACK_TOKEN`. Its format is `id:secret`.
- [ ] Set `BOOKSTACK_URL=http://localhost:8080` in `.env`.
- [ ] Never commit `.env`. Never paste the token into any other file.

Verify: with `.env` loaded (`set -a; . ./.env; set +a`), this command returns admin user JSON:

```bash
curl -s -H "Authorization: Token $BOOKSTACK_TOKEN" "$BOOKSTACK_URL/api/users/me"
```

## 3. Write the seed script skeleton

Goal: one Python entrypoint fills the instance, and re-runs are safe.

- [ ] Create `scripts/seed_bookstack.py`.
- [ ] Read `BOOKSTACK_URL` and `BOOKSTACK_TOKEN` from the environment. Load `.env` with a small built-in parser (about 10 lines). Add no new dependency to `pyproject.toml`.
- [ ] Wait for the API before seeding: poll `GET /api/pages` until it returns 200, timeout 120s. First boot runs database migrations.
- [ ] Resolve the two books by slug first: `operations-sops` and `client-profiles`. Create any missing book with the same idempotency rule as pages.
- [ ] For every corpus entry: `GET /api/pages/{slug}`. On 404 create the page. On 200 skip it.
- [ ] If an entry carries `revised_markdown`, send the update after creation. BookStack then stores a revision. That gives the SOP its version history.
- [ ] Print one summary line: created, skipped, failed counts. Exit non-zero if any request failed.
- [ ] Structure the code as small functions that take an `httpx.Client`. The test below mocks that client.
- [ ] Create `tests/test_seed_bookstack.py` with `respx`. One case where the page exists: assert skip, no POST. One case where it is missing: assert POST fires.

Verify: with the stack up, run `uv run python scripts/seed_bookstack.py` twice. The first run creates pages. The second run creates 0 and skips everything.

## 4. Author the corpus

Goal: realistic fake content that later phases retrieve, quote, and score.

The trap pages from group 5 count toward the SOP total.

- [ ] Create `scripts/corpus/sops.json`. Hold 15-20 SOP entries.
- [ ] Give every entry `slug`, `title`, and `markdown`. Add `revised_markdown` where version history matters.
- [ ] Cover e-commerce operations: returns, refunds, shipping, inventory, chargebacks, escalations, complaints, safety.
- [ ] Write bodies with headings. Phase 2 chunks on headings, so headings give the chunker structure.
- [ ] Give each SOP enough text to produce several chunks. Two to four headings per SOP is a good size.
- [ ] Create `scripts/corpus/clients.json`. Hold 5-10 fake client profiles with the same keys.
- [ ] Use clearly fictional company and person names. No real personal data. No company system data.
- [ ] Create `tests/test_corpus.py`. It checks counts, required keys, and unique slugs.

Verify: `uv run pytest tests/test_corpus.py` passes.

## 5. Plant the four traps

Goal: known bad data with recorded expected outcomes.

- [ ] Stale SOP: add `sop-restocking-fee` (older `updated_at`, 10% fee) and `sop-restocking-fee-current` (newer, 0% fee). The old page is superseded.
- [ ] Conflicting pair: add `sop-vip-escalation-ops` and `sop-vip-escalation-finance`. They give opposite escalation targets for the same procedure, with no version precedence.
- [ ] Keyword decoy: add `sop-cod-remittance-deadlines`. It reuses the keywords of a common refund question but answers a different question.
- [ ] Unanswerable question: record it in `requirements.md`. No page answers it: "What is the payout limit for the 2026 carrier insurance claim?"
- [ ] Write the trap inventory into `requirements.md`: slugs, planted facts, expected behavior, consuming phase.
- [ ] Extend `tests/test_corpus.py`: assert all four trap slugs exist in the corpus.

Verify: `uv run pytest tests/test_corpus.py` passes with the trap assertions, and every trap slug in `requirements.md` matches a corpus slug.

## 6. Run the final roadmap check

Goal: the roadmap verify command for Phase 1 passes.

- [ ] Restart the stack: `docker compose down`, then `docker compose up -d`.
- [ ] Run the seed script twice. The second run reports 0 created.
- [ ] Run the roadmap command with your token: `curl -H "Authorization: Token $ID:$SECRET" localhost:8080/api/pages`. It returns the seeded pages.
- [ ] Run the full gates: `uv run pytest` and `uv run ruff check .`.
- [ ] Check for leaks: `git status` shows no `.env`. No changed file contains your token.

Verify: every command above returns exit code 0, and the curl response lists non-zero pages including the trap slugs.

---
*Created: 2026-10-08*
