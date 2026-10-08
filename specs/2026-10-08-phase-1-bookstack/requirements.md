# Requirements - Phase 1: Self-hosted BookStack

## Context

Shippy answers procedural questions with citations.
Phase 1 builds the data source that every later phase reads.
The roadmap states phases 1-3 block everything downstream.
This is the first phase that runs a live service.

The mission forbids touching any company system.
Every integration targets an account or instance we control.
So we self-host BookStack, and we are its admin.

Repository state today:

- No `docker-compose.yml` exists.
- No `scripts/` folder exists.
- `.env.example` already lists `BOOKSTACK_URL` and `BOOKSTACK_TOKEN`.
- Phase 0 installed `httpx`, `pytest`, and `respx`.

Tech choices come from `specs/constitution/tech-stack.md`.
Docker Compose orchestrates the stack.
The BookStack REST API serves the seed script now and ingestion in phase 2.

The trap requirements come from three sources:

- `realistic_constraint_key.md`, section "C2: Planted traps in the corpus".
- `prd.md`, lines 90 and 164.
- `specs/constitution/mission.md`, line 22.

## Scope

The builder confirmed the scope on 2026-10-08: roadmap Phase 1 only.

### In scope

1. A pinned BookStack image in a Docker Compose stack.
2. A MariaDB container for BookStack's database.
3. A manual admin-token mint procedure that we document.
4. An idempotent Python seed script: `httpx`, skip existing, add missing.
5. Corpus data: 15-20 SOP pages with versions, 5-10 fake client profiles.
6. The four planted traps plus their inventory in this file.
7. Tests for corpus structure and seed idempotency.
8. One new name in `.env.example`: `BOOKSTACK_DB_PASSWORD`.

### Out of scope

- Pulling pages, chunking, and embedding (phase 2).
- The second Chroma collection (phase 3).
- Eval cases and scoring (phase 6). We only plant the data and record expectations.
- The README runbook (phase 17).
- Any Shippy API code (phase 7).
- Real company data or real personal data.
- Image upgrades after the chosen pins.

## Decisions

**D1 - Scope is roadmap Phase 1 deliverables only.**
The builder confirmed this choice on 2026-10-08.
Nothing extra enters this phase.

**D2 - The stack is BookStack plus MariaDB on host port 8080.**
Both images use explicit version tags. Never `latest`.
The database port stays unpublished. Only the app reaches the host.
Chosen tags: recorded here at implementation.

**D3 - The seed script is Python with httpx at `scripts/seed_bookstack.py`.**
It runs as `uv run python scripts/seed_bookstack.py`.
This matches the client pattern that phase 2 ingestion will reuse.
The script loads `.env` with a small built-in parser.
No new dependency enters `pyproject.toml`.

**D4 - Idempotency rule: skip existing, add missing, keyed by page slug.**
Books use the same rule.
A re-run never edits and never duplicates an existing page.

**D5 - The API token is minted by hand in the admin UI.**
BookStack exposes no token-creation API.
The token lives only in `.env`, which git ignores.
The click path is in `plan.md`, group 2.

**D6 - Corpus content lives in JSON files under `scripts/corpus/`.**
Data stays separate from code.
Later phases and reviewers can read the corpus without reading Python.

**D7 - Each trap is recorded in this file: slug, planted fact, expected behavior, consuming phase.**
`tests/test_corpus.py` asserts that the slugs exist in the corpus.

**D8 - Corpus and seed logic get automated tests.**
`tests/test_corpus.py` checks counts, keys, unique slugs, and trap slugs.
`tests/test_seed_bookstack.py` mocks httpx with `respx`: one skip case, one create case.
The roadmap verify command stays the curl check.
The tests protect the re-run behavior between roadmap checks.

## Trap inventory

Seeded corpus counts include these pages.

| # | Trap | Planted pages (slug) | Expected behavior | First consumer |
|---|---|---|---|---|
| 1 | Stale SOP | `sop-restocking-fee` (older, 10% fee), `sop-restocking-fee-current` (newer, 0% fee) | Stale page is excluded or flagged by `updated_at` metadata. It is never cited alone as current policy. | Phase 2 metadata, phase 5 refusal, phase 6 eval |
| 2 | Conflicting pair | `sop-vip-escalation-ops`, `sop-vip-escalation-finance` | Opposite escalation targets, no version precedence. The citation contract must refuse. | Phase 5, phase 6 eval at 100% |
| 3 | Keyword decoy | `sop-cod-remittance-deadlines` | Shares keywords of the refund question but answers another question. It must not be cited as the answer. | Phase 4 routing, phase 6 eval |
| 4 | Unanswerable question | No page. Question: "What is the payout limit for the 2026 carrier insurance claim?" | No corpus support, so the system must refuse. | Phase 5 confidence refusal, phase 6 eval at 100% |

## Deliverable files

- `docker-compose.yml`
- `.env.example` (edited: `BOOKSTACK_DB_PASSWORD` added)
- `scripts/seed_bookstack.py`
- `scripts/corpus/sops.json`
- `scripts/corpus/clients.json`
- `tests/test_corpus.py`
- `tests/test_seed_bookstack.py`

## Open questions

- [ ] Exact BookStack and MariaDB image tags. Pick current stable versions at implementation and record them in D2.
- [ ] Do the drafted integration token names (`ASANA_PAT`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, Gmail names) stay unchanged?
  Carried from phase 0. Resolve when phases 10-12 design their adapters.

---
*Created: 2026-10-08*
