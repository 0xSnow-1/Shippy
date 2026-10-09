import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "scripts" / "corpus"
REQUIREMENTS = (
    Path(__file__).resolve().parent.parent
    / "specs"
    / "2026-10-08-phase-1-bookstack"
    / "requirements.md"
)
REQUIRED_KEYS = ("slug", "title", "markdown")
TRAP_SLUGS = (
    "sop-restocking-fee",
    "sop-restocking-fee-current",
    "sop-vip-escalation-ops",
    "sop-vip-escalation-finance",
    "sop-cod-remittance-deadlines",
)
UNANSWERABLE_QUESTION = "What is the payout limit for the 2026 carrier insurance claim?"


def load(name: str) -> list[dict]:
    return json.loads((CORPUS / name).read_text(encoding="utf-8"))


def entries() -> list[dict]:
    return load("sops.json") + load("clients.json")


def slugify(title: str) -> str:
    text = title.lower().replace("_", "-").replace("@", "-at-")
    text = re.sub(r"[^a-z0-9\-\s]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def test_counts_are_in_range() -> None:
    assert 15 <= len(load("sops.json")) <= 20
    assert 5 <= len(load("clients.json")) <= 10


def test_every_entry_has_the_required_keys() -> None:
    for entry in entries():
        for key in REQUIRED_KEYS:
            value = entry.get(key)
            assert isinstance(value, str) and value.strip(), f"{entry.get('slug')}: bad {key}"


def test_slugs_are_unique() -> None:
    slugs = [entry["slug"] for entry in entries()]
    assert len(slugs) == len(set(slugs))


def test_slug_matches_title() -> None:
    for entry in entries():
        assert entry["slug"] == slugify(entry["title"])


def test_trap_slugs_exist_in_the_corpus() -> None:
    slugs = {entry["slug"] for entry in load("sops.json")}
    assert set(TRAP_SLUGS) <= slugs


def test_trap_slugs_match_the_requirements_inventory() -> None:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    for slug in TRAP_SLUGS:
        assert f"`{slug}`" in text


def test_unanswerable_question_is_recorded() -> None:
    assert UNANSWERABLE_QUESTION in REQUIREMENTS.read_text(encoding="utf-8")
