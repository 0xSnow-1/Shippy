from __future__ import annotations

import json

from fastapi.testclient import TestClient

from shippy.app import get_app
from shippy.compose import MockLLM
from shippy.retrieve import RELEVANCE_FLOOR, SearchResult

API_KEY = "test-key"

CLAIM_CHUNK = {
    "text": (
        "SOP - Damaged Parcel Claims > Filing the claim\n"
        "File the carrier claim within seven days of delivery. "
        "Attach the photographs, the order value, and the tracking record. "
        "Keep the outer box until the claim closes."
    ),
    "metadata": {
        "sop_id": "sop-damaged-parcel-claims",
        "version": 1,
        "title": "SOP - Damaged Parcel Claims",
        "book": "operations-sops",
        "updated_at": "2026-10-14T14:39:02Z",
    },
    "distance": 0.42,
}

CLAIM_QUOTE = (
    "File the carrier claim within seven days of delivery. "
    "Attach the photographs, the order value, and the tracking record."
)

COD_CHUNK = {
    "text": (
        "SOP - COD Remittance Deadlines > What this SOP covers\n"
        "This SOP covers cash on delivery remittances. It does not cover customer refunds."
    ),
    "metadata": {
        "sop_id": "sop-cod-remittance-deadlines",
        "version": 1,
        "title": "SOP - COD Remittance Deadlines",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 1.10,
}

RESTOCKING_OLD_CHUNK = {
    "text": (
        "SOP - Restocking Fee > When the fee applies\n"
        "A restocking fee applies to opened items returned without a defect."
    ),
    "metadata": {"sop_id": "sop-restocking-fee", "version": 1, "title": "SOP - Restocking Fee"},
    "distance": 0.2,
}

RESTOCKING_NEW_CHUNK = {
    "text": (
        "SOP - Restocking Fee > When the fee applies\n"
        "There is no restocking fee on any return inside the 14 day window."
    ),
    "metadata": {"sop_id": "sop-restocking-fee", "version": 2, "title": "SOP - Restocking Fee"},
    "distance": 0.3,
}


class FakeSearch:
    def __init__(self, result: SearchResult, considered: SearchResult | None = None):
        self.result = result
        self.considered = considered or result

    def __call__(self, query: str, floor: float = RELEVANCE_FLOOR) -> SearchResult:
        if floor == float("inf"):
            return self.considered
        return self.result


def make_client(search: FakeSearch, responses: dict[str, str] | None = None) -> TestClient:
    provider = MockLLM(responses or {})
    return TestClient(get_app(search=search, provider=provider, api_key=API_KEY))


def claim_provider() -> MockLLM:
    return MockLLM(
        {
            "carrier claim": json.dumps(
                {
                    "answer": "File the carrier claim within seven days of delivery.",
                    "quote": CLAIM_QUOTE,
                    "proposed_action": "Keep the outer box until the claim closes.",
                }
            )
        }
    )


def test_wrong_key_returns_401() -> None:
    search = FakeSearch(SearchResult(status="ok", chunks=[CLAIM_CHUNK]))
    response = make_client(search).post(
        "/lookup",
        json={"query": "How do we file a carrier claim for a damaged parcel?"},
        headers={"x-api-key": "wrong-key"},
    )

    assert response.status_code == 401


def test_correct_key_returns_cited_answer_with_source_id_and_verbatim_quote() -> None:
    search = FakeSearch(SearchResult(status="ok", chunks=[CLAIM_CHUNK]))
    client = TestClient(get_app(search=search, provider=claim_provider(), api_key=API_KEY))

    response = client.post(
        "/lookup",
        json={"query": "How do we file a carrier claim for a damaged parcel?"},
        headers={"x-api-key": API_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_id"] == "sop-damaged-parcel-claims"
    assert payload["quote"] == CLAIM_QUOTE
    assert payload["quote"] in CLAIM_CHUNK["text"]
    assert payload["answer"]


def test_unanswerable_question_returns_refusal_with_source_links() -> None:
    search = FakeSearch(
        SearchResult(status="no_match", chunks=[]),
        considered=SearchResult(status="ok", chunks=[COD_CHUNK]),
    )
    response = make_client(search).post(
        "/lookup",
        json={"query": "What is the payout limit for the 2026 carrier insurance claim?"},
        headers={"x-api-key": API_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is True
    assert payload["reason"] == "no matching SOP found"
    assert payload["source_links"] == [
        "http://localhost:8080/books/operations-sops/page/sop-cod-remittance-deadlines"
    ]


def test_version_conflict_returns_refusal_with_source_links() -> None:
    search = FakeSearch(
        SearchResult(status="ok", chunks=[RESTOCKING_OLD_CHUNK, RESTOCKING_NEW_CHUNK])
    )
    response = make_client(search).post(
        "/lookup",
        json={"query": "What is the restocking fee?"},
        headers={"x-api-key": API_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is True
    assert "version conflict" in payload["reason"]
    assert payload["source_links"]


def test_health_is_open_without_key() -> None:
    search = FakeSearch(SearchResult(status="no_match", chunks=[]))
    response = make_client(search).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
