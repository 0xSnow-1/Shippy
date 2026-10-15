from __future__ import annotations

import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import register_embedding_function

from shippy.compose import Answer, MockLLM, compose
from shippy.retrieve import SearchResult
from shippy.validate import validate

CORPUS_PATH = Path(__file__).resolve().parent.parent / "scripts" / "corpus" / "sops.json"


@register_embedding_function
class _HashEmbedding(chromadb.EmbeddingFunction):
    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "hash_embedding_eval"

    @staticmethod
    def build_from_config(config: dict) -> _HashEmbedding:
        return _HashEmbedding()

    def get_config(self) -> dict:
        return {}

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in input]

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(byte) for byte in digest[:8]]


def _load_corpus() -> list[dict]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _make_chunk(sop: dict, section_heading: str, section_text: str, version: int = 1) -> dict:
    title = sop["title"]
    slug = sop["slug"]
    path = f"{title} > {section_heading}"
    text = f"{path}\n{section_text}"
    return {
        "text": text,
        "metadata": {
            "sop_id": slug,
            "version": version,
            "title": title,
            "book": "operations-sops",
            "updated_at": "2026-10-09T05:00:00Z",
        },
    }


def _first_section(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()
    heading = ""
    body_lines: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            heading = line[3:].strip()
            in_section = True
        elif in_section:
            body_lines.append(line)
    return heading, "\n".join(body_lines).strip()


def _run_case(
    name: str,
    query: str,
    result: SearchResult,
    provider: MockLLM | None,
    expect_refused: bool,
) -> bool:
    if result.status == "no_match":
        vr = validate(result)
        passed = (not vr.ok) if expect_refused else vr.ok
        label = "PASS" if passed else "FAIL"
        print(f"{label} {name}")
        return passed

    answer: Answer | None = None
    if provider is not None:
        answer = compose(query, result.chunks, provider)

    vr = validate(result, answer)
    passed = (not vr.ok) if expect_refused else vr.ok
    label = "PASS" if passed else "FAIL"
    print(f"{label} {name}")
    return passed


def main() -> int:
    corpus = _load_corpus()
    by_slug = {p["slug"]: p for p in corpus}

    results: list[bool] = []

    # Happy path: returns intake question with a verbatim quote from the chunk
    intake = by_slug["sop-returns-intake"]
    heading, body = _first_section(intake["markdown"])
    happy_chunk = _make_chunk(intake, heading, body)
    quote = body.split(".")[0] + "."
    happy_provider = MockLLM(
        {
            "returns": json.dumps(
                {
                    "answer": "Scan the return label when the parcel arrives.",
                    "quote": quote,
                    "proposed_action": "Follow returns intake SOP.",
                }
            )
        }
    )
    happy_result = SearchResult(status="ok", chunks=[happy_chunk])
    results.append(_run_case("happy_path", "returns intake", happy_result, happy_provider, expect_refused=False))

    # Trap 1: version conflict — same sop_id, two different version numbers
    old = by_slug["sop-restocking-fee"]
    new = by_slug["sop-restocking-fee-current"]
    old_h, old_b = _first_section(old["markdown"])
    new_h, new_b = _first_section(new["markdown"])
    old_chunk = _make_chunk(old, old_h, old_b, version=1)
    new_chunk = _make_chunk(new, new_h, new_b, version=2)
    old_chunk["metadata"]["sop_id"] = "sop-restocking-fee"
    new_chunk["metadata"]["sop_id"] = "sop-restocking-fee"
    conflict_result = SearchResult(status="ok", chunks=[old_chunk, new_chunk])
    results.append(_run_case("version_conflict", "restocking fee", conflict_result, None, expect_refused=True))

    # Trap 2: conflicting pair — VIP escalation routes to two different targets; fabricated quote fails
    ops = by_slug["sop-vip-escalation-ops"]
    fin = by_slug["sop-vip-escalation-finance"]
    ops_h, ops_b = _first_section(ops["markdown"])
    fin_h, fin_b = _first_section(fin["markdown"])
    ops_chunk = _make_chunk(ops, ops_h, ops_b)
    fin_chunk = _make_chunk(fin, fin_h, fin_b)
    pair_provider = MockLLM(
        {
            "VIP": json.dumps(
                {
                    "answer": "Route to the duty manager.",
                    "quote": "This text does not appear in either chunk.",
                    "proposed_action": "Follow VIP escalation SOP.",
                }
            )
        }
    )
    pair_result = SearchResult(status="ok", chunks=[ops_chunk, fin_chunk])
    results.append(_run_case("conflicting_pair", "VIP escalation target", pair_result, pair_provider, expect_refused=True))

    # Trap 3: keyword decoy — COD chunk retrieved; LLM fabricates a refund quote not in that chunk
    cod = by_slug["sop-cod-remittance-deadlines"]
    cod_h, cod_b = _first_section(cod["markdown"])
    cod_chunk = _make_chunk(cod, cod_h, cod_b)
    decoy_provider = MockLLM(
        {
            "refund": json.dumps(
                {
                    "answer": "Refunds are issued within two working days.",
                    "quote": "Refunds are issued within two working days.",
                    "proposed_action": "Check refund issuance SOP.",
                }
            )
        }
    )
    decoy_result = SearchResult(status="ok", chunks=[cod_chunk])
    results.append(_run_case("keyword_decoy", "refund timing", decoy_result, decoy_provider, expect_refused=True))

    # Trap 4: unanswerable — no SOP found for this topic
    unanswerable_result = SearchResult(status="no_match")
    results.append(_run_case("unanswerable", "sick leave policy", unanswerable_result, None, expect_refused=True))

    total = len(results)
    passed_count = sum(results)
    print(f"pass rate: {passed_count}/{total}")
    return 0 if passed_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
