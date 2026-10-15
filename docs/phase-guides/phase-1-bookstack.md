# Phase 1: Self-hosted BookStack

## What problem this solves

Shippy answers questions about procedures.
It needs a source of procedures to read.

Phase 1 builds that source.

We self-host BookStack instead of using anyone else's.
We are the admin of our own instance.
No company system is touched anywhere in this project.

## The one-sentence version

BookStack is our fake company wiki.
MariaDB is its hard drive.
Containers let us start and wipe both in one command.
Shippy will read from that wiki and answer questions with citations.

## The two boxes

A container is a sealed box with a program inside.
It runs the same way on any machine.

We use containers so setup needs no manual install.
One command brings the whole thing up.

| Box | Runs | Job |
|---|---|---|
| `bookstack` | BookStack | The wiki website. Stores pages. |
| `db` | MariaDB | The database. Stores BookStack's data. |

### Why two boxes, and why BookStack is not a database

Think of a database as a spreadsheet that never loses data.
BookStack writes every page edit into it.
It reads every page view back out.

A **database** is the storage room.
**BookStack** is the website on top.

BookStack is not a storage room.
It is a website that uses one.

That is why we need both boxes.

### Host and port

Your computer is the **host**.
A **port** is a numbered door into it.

`8080:80` means:
- Container door is `80`, inside the box.
- Host door is `8080`, outside the box.

You type `localhost:8080` in a browser.
BookStack answers.

MariaDB's door stays closed to the host.
Only BookStack inside the box can reach it.
That keeps the database private.

### Why MariaDB has a healthcheck

First boot, MariaDB builds its tables.
This building step is called **migrations**.
BookStack's API answers errors until it finishes.

The healthcheck asks MariaDB "are you ready?".
BookStack waits for a yes before starting.
Without that wait, the first boot races and fails.

## The use case, as you

You are the operations lead.
You want to ask Shippy a question.

Step 1. You ask Shippy:
"What is our restocking fee?"

Step 2. Shippy needs a source to check.
That source is BookStack, running on your machine.

Step 3. Shippy calls BookStack's API.
It pulls the SOP page.

Step 4. Shippy reads the page.
It answers with a quote and a page link.

Without BookStack, step 2 has nothing.
Shippy would be guessing.

## What each piece does for you

| Piece | Your benefit |
|---|---|
| BookStack | Holds your SOPs as pages you can edit in a browser. |
| MariaDB | BookStack's hard drive. You never touch it directly. |
| Port 8080 | The address you open to see BookStack. |
| The seed script | Fills BookStack with 24 practice pages so you can test Shippy. |
| The token | A password that lets Shippy call the API. Stays in `.env`. |

## The seed script

`scripts/seed_bookstack.py`.
Run it with `uv run python scripts/seed_bookstack.py`.

### What it does, in order

1. Reads `BOOKSTACK_URL` and `BOOKSTACK_TOKEN` from `.env`.
2. Asks the API "are you ready?" for up to 120 seconds.
3. Creates the two books if missing.
4. Lists all existing pages once.
5. Creates any page whose slug is missing. Skips any slug already present.
6. Edits the one page that needs a second version.
7. Prints `created=X skipped=Y failed=Z`.

### What a book is

In BookStack, a **book** is a top-level folder.
Pages live inside books.

We created two:

- `operations-sops` holds the 18 SOP pages.
- `client-profiles` holds the 6 client pages.

`ensure_books` means: check if each book already exists.
Create it if missing. Skip if present.

### Why it waits 120 seconds

On the first boot the database is still building its tables.
The API answers errors while that runs.
The script retries until it gets a `200 OK`.

### Idempotency

Idempotent means: run it twice, get the same result.
Never duplicates.

The key is the page slug.

| Slug state | What the script does |
|---|---|
| Found | Skip it. Do nothing. |
| Missing | Create the page. |

Proof from the real run:

```
Run 1: created=24 skipped=0 failed=0
Run 2: created=0 skipped=24 failed=0
```

24 = 18 SOPs + 6 client profiles.

### The revision trick

A **revision** is one saved version of a page.
BookStack keeps history.
Every edit stores a new revision.

Only one page uses this: `sop-restocking-fee-current`.

Why: we need two versions of the same SOP.
One old with a 10% fee, one current with a 0% fee.

The trick:
1. Create both pages first.
2. Then edit the second one.

The edit makes it revision 2.
It also makes it newer than the first page.

**`updated_at`** is a timestamp field.
It records when a page was last changed.
Format: `2026-10-09T05:04:35Z`.

We use it to decide which page is current.
Newer `updated_at` wins.

| Page | `updated_at` | `revision_count` |
|---|---|---|
| `sop-restocking-fee` | `05:04:35` | 1 |
| `sop-restocking-fee-current` | `05:04:44` | 2 |

The script sleeps 1.1 seconds before editing.
BookStack only stores time to the second.
Without the sleep both pages could show the same second.
Then we could not tell which is newer.

## The corpus

Two JSON files. Data stays separate from code.
A reviewer reads the corpus without reading Python.

- `scripts/corpus/sops.json` holds 18 SOPs.
- `scripts/corpus/clients.json` holds 6 client profiles.

Every entry has three keys:

```json
{
  "slug": "sop-restocking-fee",
  "title": "SOP - Restocking Fee",
  "markdown": "## When it applies\n...\n## How to apply it\n..."
}
```

Bodies use `##` headings.
Phase 2 chunks on headings, so the headings give the chunker structure.

Company names are fictional.
No real personal data. No real company data.

## The four traps

The traps are the reason this corpus is not filler.
Each one is a known bad case with a recorded expected outcome.

| # | Trap | Pages | Why it exists |
|---|---|---|---|
| 1 | Stale SOP | `sop-restocking-fee` (older, 10%) vs `sop-restocking-fee-current` (newer, 0%) | Tests whether the system respects `updated_at`. |
| 2 | Conflicting pair | `sop-vip-escalation-ops` vs `sop-vip-escalation-finance` | Opposite escalation targets, identical text otherwise. No version rule can separate them, so the citation contract must refuse. |
| 3 | Keyword decoy | `sop-cod-remittance-deadlines` | Shares refund keywords but answers another question. Tests whether retrieval is fooled by lexical overlap. |
| 4 | Unanswerable | none | "What is the payout limit for the 2026 carrier insurance claim?" Nothing answers it, so the system must refuse. |

Five slugs come from four traps.
Traps 1 and 2 each need two pages.

## Secrets

`.env.example` is committed. It lists names with empty values.
`.env` holds real values. Git ignores it.

Phase 1 added one line to the example file:

```
BOOKSTACK_DB_PASSWORD=
```

The compose file reads it with a default, so a fresh clone still boots.

The API token is the sensitive value.
Format is `id:secret`.
It lives in `.env` only.

## What the API got wrong

BookStack's docs did not match the pinned version `26.09.1`.

| Assumption | Reality |
|---|---|
| Web installer at `/install` | Returns 404. Use the `bookstack:create-admin` command. |
| `GET /api/users/me` | Does not exist. Use `/api/users/1`. |
| `GET /api/pages/{slug}` | The id is treated as a number, so a slug never resolves. List pages instead. |
| Send `slug` on create | Rejected. The slug comes from the title. |
| "Access System API" checkbox | Not present. API permission follows the user account. |
| Token created via API | No such API. Drive the admin UI over HTTP. |

## The six gates

Gates are proof commands.
All six pass.

| Gate | Command | Result |
|---|---|---|
| 1 | `curl -H "Authorization: Token $BOOKSTACK_TOKEN" localhost:8080/api/pages` | HTTP 200, 24 pages, all trap slugs |
| 2 | `uv run python scripts/seed_bookstack.py` twice | `created=0 skipped=24 failed=0` |
| 3 | `uv run pytest` | 9 passed |
| 4 | `uv run ruff check .` | clean |
| 5 | `git status`, `git check-ignore .env` | `.env` ignored, no token in any file |
| 6 | Cold start from `docker compose down -v` | Full path works from zero |

Gate 6 is the important one.
It wipes the volumes.
It recreates the admin.
It mints a new token.
It seeds twice.
It runs Gate 1.

That proves a new developer can reproduce the state from nothing.

## How to run it yourself

```bash
docker compose up -d
set -a; . ./.env; set +a
uv run python scripts/seed_bookstack.py
uv run python scripts/seed_bookstack.py
curl -s -H "Authorization: Token $BOOKSTACK_TOKEN" localhost:8080/api/pages
uv run pytest
uv run ruff check .
```

The second seed run is the one to watch.
It must print `created=0`.

To rebuild from nothing, add `docker compose down -v` first.
Then you must re-create the admin and mint a new token.

## What you can do now

- Open `http://localhost:8080` in a browser. See the wiki.
- Ask the API for any page and get JSON back.
- Run the seed script twice and prove it does not duplicate.

## What this unlocks

Phase 2 reads these pages.
It pulls them, cuts them into chunks, and stores them for search.

---
*Created: 2026-10-09*
