from __future__ import annotations

import json
import os
from pathlib import Path

import uvicorn

from shippy.app import get_app, live_search, open_sops_collection
from shippy.compose import MockLLM
from shippy.ingest import chunk_page, write_collection

CORPUS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "corpus"
BOOKS = {
    "sops.json": ("operations-sops", "sop_id"),
    "clients.json": ("client-profiles", "client_id"),
}

CLAIM_QUOTE = (
    "File the carrier claim within seven days of delivery. "
    "Attach the photographs, the order value, and the tracking record."
)

MOCK_RESPONSES = {
    "carrier claim for a damaged parcel": json.dumps(
        {
            "answer": "File the carrier claim within seven days of delivery.",
            "quote": CLAIM_QUOTE,
            "proposed_action": "Keep the outer box until the claim closes.",
        }
    ),
    "restocking fee": json.dumps(
        {
            "answer": "There is a flat restocking fee of 15 dollars on every return.",
            "quote": "There is a flat restocking fee of 15 dollars on every return.",
            "proposed_action": "Apply the fee in the returns tool.",
        }
    ),
}


def build_index(chroma_path: Path) -> None:
    for filename, (book_slug, id_key) in BOOKS.items():
        chunks: list[dict] = []
        for entry in json.loads((CORPUS_DIR / filename).read_text(encoding="utf-8")):
            title = entry["title"]
            page = {
                "slug": entry["slug"],
                "name": title,
                "revision_count": 1,
                "updated_at": "2026-10-09T05:00:00Z",
            }
            markdown = f"# {title}\n\n{entry['markdown']}"
            chunks.extend(chunk_page(page, book_slug, markdown, id_key))
            if "revised_markdown" not in entry:
                continue
            revised_page = {**page, "revision_count": 2}
            revised_markdown = f"# {title}\n\n{entry['revised_markdown']}"
            revised_chunks = chunk_page(revised_page, book_slug, revised_markdown, id_key)
            for chunk in revised_chunks:
                chunk["id"] = f"{chunk['id']}.rev2"
            chunks.extend(revised_chunks)
        name = "sops" if id_key == "sop_id" else "clients"
        write_collection(chunks, name, chroma_path)


def main() -> int:
    chroma_path = Path(os.environ["SHIPPY_DEMO_CHROMA"])
    db_path = Path(os.environ["SHIPPY_DEMO_DB"])
    api_key = os.environ["SHIPPY_API_KEY"]
    host = os.environ.get("SHIPPY_DEMO_HOST", "127.0.0.1")
    port = int(os.environ.get("SHIPPY_DEMO_PORT", "8000"))

    if os.environ.get("SHIPPY_DEMO_BUILD_INDEX", "1") == "1":
        build_index(chroma_path)

    collection = open_sops_collection(chroma_path)
    provider = None if os.environ.get("SHIPPY_DEMO_LLM") == "bedrock" else MockLLM(MOCK_RESPONSES)
    app = get_app(
        search=live_search(collection),
        provider=provider,
        api_key=api_key,
        db_path=db_path,
    )

    mode = "bedrock" if provider is None else "mock"
    print(
        f"index: sops={collection.count()} chunks at {chroma_path}",
        flush=True,
    )
    print(f"llm: {mode}", flush=True)
    print(f"listening on http://{host}:{port}", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
