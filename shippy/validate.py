from __future__ import annotations

import os
from dataclasses import dataclass, field

from shippy.compose import Answer
from shippy.retrieve import SearchResult


@dataclass
class ValidationResult:
    ok: bool
    status: str
    reason: str = ""
    sources: list[str] = field(default_factory=list)


def _source_links(chunks: list[dict]) -> list[str]:
    base = os.environ.get("BOOKSTACK_URL", "").rstrip("/")
    seen: list[str] = []
    for chunk in chunks:
        sop_id = chunk["metadata"].get("sop_id", "")
        if not sop_id or sop_id in seen:
            continue
        seen.append(sop_id)
    if base:
        return [f"{base}/books/operations-sops/page/{sop_id}" for sop_id in seen]
    return [f"/books/operations-sops/page/{sop_id}" for sop_id in seen]


def _has_version_conflict(chunks: list[dict]) -> bool:
    by_sop: dict[str, set[int]] = {}
    for chunk in chunks:
        sop_id = chunk["metadata"].get("sop_id", "")
        version = chunk["metadata"].get("version", 0)
        by_sop.setdefault(sop_id, set()).add(version)
    return any(len(versions) > 1 for versions in by_sop.values())


def validate(result: SearchResult, answer: Answer | None = None) -> ValidationResult:
    if result.status == "no_match":
        return ValidationResult(
            ok=False,
            status="refused",
            reason="no matching SOP found",
            sources=[],
        )

    chunks = result.chunks

    if _has_version_conflict(chunks):
        return ValidationResult(
            ok=False,
            status="refused",
            reason="version conflict: multiple SOP versions retrieved",
            sources=_source_links(chunks),
        )

    if answer is not None:
        quote_found = any(answer.quote in chunk["text"] for chunk in chunks)
        if not quote_found:
            return ValidationResult(
                ok=False,
                status="refused",
                reason="quote is not a verbatim substring of any retrieved chunk",
                sources=_source_links(chunks),
            )

    return ValidationResult(ok=True, status="ok")
