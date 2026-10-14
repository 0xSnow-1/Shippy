from __future__ import annotations

import os
import sys
from pathlib import Path

import chromadb
import httpx

from shippy.env import load_env

CHROMA_PATH = Path("data/chroma")
REQUEST_TIMEOUT_SECONDS = 30

BOOKS = {
    "operations-sops": ("sops", "sop_id"),
    "client-profiles": ("clients", "client_id"),
}


class IngestError(Exception):
    pass


def require_env(path: str | Path = ".env") -> tuple[str, str]:
    load_env(path)
    url = os.environ.get("BOOKSTACK_URL", "").rstrip("/")
    token = os.environ.get("BOOKSTACK_TOKEN", "")
    missing = [name for name, value in (("BOOKSTACK_URL", url), ("BOOKSTACK_TOKEN", token)) if not value]
    if missing:
        raise IngestError("missing environment variable: " + ", ".join(missing))
    return url, token


def resolve_books(client: httpx.Client) -> dict[str, int]:
    response = client.get("/api/books", params={"count": 100})
    response.raise_for_status()
    found = {item["slug"]: item["id"] for item in response.json()["data"]}
    missing = [slug for slug in BOOKS if slug not in found]
    if missing:
        raise IngestError("book not found: " + ", ".join(missing))
    return {slug: found[slug] for slug in BOOKS}


def fetch_pages(client: httpx.Client, book_id: int) -> list[dict]:
    collected: list[dict] = []
    page_number = 1
    while True:
        response = client.get("/api/pages", params={"page": page_number, "count": 100})
        response.raise_for_status()
        items = response.json()["data"]
        collected.extend(item for item in items if item.get("book_id") == book_id)
        if len(items) < 100:
            break
        page_number += 1
    collected.sort(key=lambda item: item["slug"])
    return collected


def page_slug(client: httpx.Client, page_id: int) -> str:
    response = client.get(f"/api/pages/{page_id}")
    if response.is_success:
        return str(response.json().get("slug", page_id))
    return str(page_id)


def export_markdown(client: httpx.Client, page_id: int) -> str:
    response = client.get(f"/api/pages/{page_id}/export/markdown")
    if not response.is_success:
        slug = page_slug(client, page_id)
        raise IngestError(f"markdown export for page '{slug}' failed with status {response.status_code}")
    return response.text


def strip_boilerplate(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    expected = f"# {title}"
    if not lines or lines[0] != expected:
        raise IngestError(f"format drift: export does not start with '{expected}'")
    rest = lines[1:]
    index = 0
    while index < len(rest) and not rest[index].strip():
        index += 1
    return "\n".join(rest[index:])


def trim_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def chunk_page(page: dict, book_slug: str, markdown: str, id_key: str) -> list[dict]:
    title = page["name"]
    slug = page["slug"]
    body = strip_boilerplate(markdown, title)

    segments: list[tuple[str | None, list[str]]] = []
    heading: str | None = None
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            segments.append((heading, current))
            heading = line[3:].strip()
            current = []
        else:
            current.append(line)
    segments.append((heading, current))

    if segments[0][0] is None:
        preamble = trim_blank_edges(segments[0][1])
        sections = segments[1:]
    else:
        preamble = []
        sections = segments

    if not sections:
        raise IngestError(f"format drift: page '{slug}' has no section headings")

    metadata = {
        id_key: slug,
        "version": page["revision_count"],
        "updated_at": page["updated_at"],
        "title": title,
        "book": book_slug,
    }

    chunks: list[dict] = []
    if preamble:
        chunks.append(
            {
                "id": f"{slug}#0",
                "text": title + "\n" + "\n".join(preamble),
                "metadata": dict(metadata),
            }
        )
    for heading_text, lines in sections:
        path = f"{title} > {heading_text}" if heading_text else title
        chunks.append(
            {
                "id": f"{slug}#{len(chunks)}",
                "text": path + "\n" + "\n".join(trim_blank_edges(lines)),
                "metadata": dict(metadata),
            }
        )
    return chunks


def write_collection(
    chunks: list[dict], name: str, path: Path, embedding_fn: chromadb.EmbeddingFunction | None = None
) -> None:
    client = chromadb.PersistentClient(path=str(path))
    existing = [item if isinstance(item, str) else item.name for item in client.list_collections()]
    if name in existing:
        client.delete_collection(name)
    if embedding_fn is None:
        collection = client.create_collection(name)
    else:
        collection = client.create_collection(name, embedding_function=embedding_fn)

    if chunks:
        collection.add(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[chunk["metadata"] for chunk in chunks],
        )

    stored = collection.get(include=["metadatas"])
    expected = {chunk["id"]: chunk["metadata"] for chunk in chunks}
    found = dict(zip(stored["ids"], stored["metadatas"]))
    if len(stored["ids"]) != len(chunks) or found != expected:
        raise IngestError(f"round-trip verification failed for collection '{name}'")


def main(
    embedding_fn: chromadb.EmbeddingFunction | None = None, path: Path = CHROMA_PATH
) -> int:
    try:
        url, token = require_env()
        headers = {"Authorization": f"Token {token}"}
        counts: dict[str, tuple[int, int]] = {}
        with httpx.Client(
            base_url=url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        ) as client:
            books = resolve_books(client)
            for slug, book_id in books.items():
                collection_name, id_key = BOOKS[slug]
                pages = fetch_pages(client, book_id)
                chunks: list[dict] = []
                for page in pages:
                    markdown = export_markdown(client, page["id"])
                    chunks.extend(chunk_page(page, slug, markdown, id_key))
                write_collection(chunks, collection_name, path, embedding_fn)
                counts[collection_name] = (len(chunks), len(pages))
    except (IngestError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    total = sum(chunk_count for chunk_count, _ in counts.values())
    print(f"sops: {counts['sops'][0]} chunks from {counts['sops'][1]} pages")
    print(f"clients: {counts['clients'][0]} chunks from {counts['clients'][1]} pages")
    print(f"round-trip: {total} chunks verified with metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
