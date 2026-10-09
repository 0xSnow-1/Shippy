from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
BOOKS = {
    "sops.json": ("operations-sops", "Operations SOPs"),
    "clients.json": ("client-profiles", "Client Profiles"),
}
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
API_READY_TIMEOUT_SECONDS = 120
API_RETRY_SECONDS = 2
LIST_COUNT = 500
REQUEST_TIMEOUT_SECONDS = 30
REVISION_GAP_SECONDS = 1.1


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def require_env() -> tuple[str, str]:
    url = os.environ.get("BOOKSTACK_URL", "").rstrip("/")
    token = os.environ.get("BOOKSTACK_TOKEN", "")
    missing = [name for name, value in (("BOOKSTACK_URL", url), ("BOOKSTACK_TOKEN", token)) if not value]
    if missing:
        raise SystemExit("Missing environment variables: " + ", ".join(missing))
    return url, token


def wait_for_api(client: httpx.Client) -> None:
    deadline = time.monotonic() + API_READY_TIMEOUT_SECONDS
    last = "no response"
    while True:
        try:
            response = client.get("/api/pages", params={"count": 1})
        except httpx.HTTPError as exc:
            last = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code == 200:
                return
            if response.status_code < 500:
                raise SystemExit(f"BookStack API answered HTTP {response.status_code}. Check BOOKSTACK_TOKEN.")
            last = f"HTTP {response.status_code}"
        if time.monotonic() >= deadline:
            raise SystemExit(f"BookStack API not ready after {API_READY_TIMEOUT_SECONDS}s ({last})")
        time.sleep(API_RETRY_SECONDS)


def slug_index(client: httpx.Client, path: str) -> dict[str, int]:
    response = client.get(path, params={"count": LIST_COUNT})
    response.raise_for_status()
    return {item["slug"]: item["id"] for item in response.json()["data"]}


def ensure_books(client: httpx.Client) -> dict[str, int]:
    books = slug_index(client, "/api/books")
    for slug, name in BOOKS.values():
        if slug in books:
            continue
        response = client.post("/api/books", json={"name": name})
        response.raise_for_status()
        book = response.json()
        if book["slug"] != slug:
            raise SystemExit(f"Book title {name!r} gives slug {book['slug']!r}, expected {slug!r}.")
        books[book["slug"]] = book["id"]
    return books


def load_entries() -> list[dict]:
    entries = []
    for filename, (book_slug, _) in BOOKS.items():
        path = CORPUS_DIR / filename
        for entry in json.loads(path.read_text(encoding="utf-8")):
            entries.append({**entry, "book_slug": book_slug})
    return entries


def seed_entry(client: httpx.Client, entry: dict, book_id: int, existing: dict[str, int]) -> dict | None:
    if entry["slug"] in existing:
        return None
    response = client.post(
        "/api/pages",
        json={"name": entry["title"], "markdown": entry["markdown"], "book_id": book_id},
    )
    response.raise_for_status()
    page = response.json()
    if page["slug"] != entry["slug"]:
        raise SystemExit(f"Page title {entry['title']!r} gives slug {page['slug']!r}, expected {entry['slug']!r}.")
    return page


def apply_revisions(client: httpx.Client, pending: list[tuple[int, str]]) -> None:
    if not pending:
        return
    time.sleep(REVISION_GAP_SECONDS)
    for page_id, markdown in pending:
        client.put(f"/api/pages/{page_id}", json={"markdown": markdown}).raise_for_status()


def run_seed(client: httpx.Client, entries: list[dict]) -> tuple[int, int, int]:
    wait_for_api(client)
    books = ensure_books(client)
    existing = slug_index(client, "/api/pages")
    created = 0
    skipped = 0
    failed = 0
    pending: list[tuple[int, str]] = []
    for entry in entries:
        try:
            page = seed_entry(client, entry, books[entry["book_slug"]], existing)
        except (httpx.HTTPError, KeyError) as exc:
            failed += 1
            print(f"failed {entry['slug']}: {exc}", file=sys.stderr)
            continue
        if page is None:
            skipped += 1
            continue
        created += 1
        if "revised_markdown" in entry:
            pending.append((page["id"], entry["revised_markdown"]))
    try:
        apply_revisions(client, pending)
    except httpx.HTTPError as exc:
        failed += 1
        print(f"failed revision pass: {exc}", file=sys.stderr)
    return created, skipped, failed


def main() -> int:
    load_dotenv(ENV_FILE)
    url, token = require_env()
    headers = {"Authorization": f"Token {token}"}
    with httpx.Client(base_url=url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        created, skipped, failed = run_seed(client, load_entries())
    print(f"created={created} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
