from __future__ import annotations

import json

from shippy.compose import MockLLM, compose
from shippy.retrieve import SearchResult
from shippy.validate import validate

INTAKE_CHUNK = {
    "text": (
        "SOP - Returns Intake > Receiving a return\n"
        "Scan the return label when the parcel arrives at the returns desk. "
        "Match the scan to an open return in the returns tool. "
        "If no match exists, park the parcel in the unmatched bin and raise a returns query."
    ),
    "metadata": {
        "sop_id": "sop-returns-intake",
        "version": 1,
        "title": "SOP - Returns Intake",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 0.1,
}

RESTOCKING_OLD_CHUNK = {
    "text": (
        "SOP - Restocking Fee > When the fee applies\n"
        "A restocking fee applies to opened items returned without a defect. "
        "The fee is 10 percent of the item price."
    ),
    "metadata": {
        "sop_id": "sop-restocking-fee",
        "version": 1,
        "title": "SOP - Restocking Fee",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 0.2,
}

RESTOCKING_NEW_CHUNK = {
    "text": (
        "SOP - Restocking Fee > When the fee applies\n"
        "There is no restocking fee on any return inside the 14 day window. "
        "The fee was removed for all product lines from the current policy release."
    ),
    "metadata": {
        "sop_id": "sop-restocking-fee",
        "version": 2,
        "title": "SOP - Restocking Fee (Current)",
        "book": "operations-sops",
        "updated_at": "2026-10-14T10:00:00Z",
    },
    "distance": 0.3,
}

VIP_OPS_CHUNK = {
    "text": (
        "SOP - VIP Escalation (Ops) > Escalation target\n"
        "Route the escalation to the Operations Duty Manager. "
        "Post the brief in the VIP Ops channel and tag the duty manager on call."
    ),
    "metadata": {
        "sop_id": "sop-vip-escalation-ops",
        "version": 1,
        "title": "SOP - VIP Escalation (Ops)",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 0.2,
}

VIP_FINANCE_CHUNK = {
    "text": (
        "SOP - VIP Escalation (Finance) > Escalation target\n"
        "Route the escalation to the Finance Controller. "
        "Post the brief in the Billing Escalations channel and tag the controller on call."
    ),
    "metadata": {
        "sop_id": "sop-vip-escalation-finance",
        "version": 1,
        "title": "SOP - VIP Escalation (Finance)",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 0.3,
}

COD_CHUNK = {
    "text": (
        "SOP - COD Remittance Deadlines > What this SOP covers\n"
        "This SOP covers cash on delivery remittances from our carriers to our bank account. "
        "It does not cover customer refunds. It does not cover payout timing for any claim."
    ),
    "metadata": {
        "sop_id": "sop-cod-remittance-deadlines",
        "version": 1,
        "title": "SOP - COD Remittance Deadlines",
        "book": "operations-sops",
        "updated_at": "2026-10-09T05:00:00Z",
    },
    "distance": 0.4,
}


def test_happy_path_passes_validation() -> None:
    result = SearchResult(status="ok", chunks=[INTAKE_CHUNK])
    quote = "Scan the return label when the parcel arrives at the returns desk."
    provider = MockLLM(
        {
            "returns": json.dumps(
                {
                    "answer": "Scan the return label when the parcel arrives.",
                    "quote": quote,
                    "proposed_action": "Follow the returns intake SOP.",
                }
            )
        }
    )

    answer = compose("returns intake procedure", result.chunks, provider)
    vr = validate(result, answer)

    assert vr.ok
    assert vr.status == "ok"


def test_version_conflict_refuses() -> None:
    result = SearchResult(status="ok", chunks=[RESTOCKING_OLD_CHUNK, RESTOCKING_NEW_CHUNK])

    vr = validate(result)

    assert not vr.ok
    assert vr.status == "refused"
    assert "version conflict" in vr.reason


def test_conflicting_pair_refuses_when_quote_not_in_chunks() -> None:
    result = SearchResult(status="ok", chunks=[VIP_OPS_CHUNK, VIP_FINANCE_CHUNK])
    provider = MockLLM(
        {
            "VIP": json.dumps(
                {
                    "answer": "Route to the Finance Controller.",
                    "quote": "This text is not in any chunk.",
                    "proposed_action": "Follow VIP escalation SOP.",
                }
            )
        }
    )

    answer = compose("VIP escalation target", result.chunks, provider)
    vr = validate(result, answer)

    assert not vr.ok
    assert vr.status == "refused"


def test_keyword_decoy_refuses_when_quote_not_in_chunk() -> None:
    result = SearchResult(status="ok", chunks=[COD_CHUNK])
    provider = MockLLM(
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

    answer = compose("refund timing", result.chunks, provider)
    vr = validate(result, answer)

    assert not vr.ok
    assert vr.status == "refused"
    assert "verbatim" in vr.reason


def test_unanswerable_query_refuses() -> None:
    result = SearchResult(status="no_match")

    vr = validate(result)

    assert not vr.ok
    assert vr.status == "refused"
    assert "no matching SOP" in vr.reason
