from __future__ import annotations

from dataclasses import dataclass, field

import chromadb

RELEVANCE_FLOOR = 1.0
DEFAULT_K = 5
COLLECTION_NAME = "sops"


@dataclass
class SearchResult:
    status: str
    chunks: list[dict] = field(default_factory=list)


def search_sop(
    query: str,
    collection: chromadb.Collection,
    k: int = DEFAULT_K,
    floor: float = RELEVANCE_FLOOR,
) -> SearchResult:
    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
        if dist <= floor
    ]

    if not chunks:
        return SearchResult(status="no_match")

    return SearchResult(status="ok", chunks=chunks)
