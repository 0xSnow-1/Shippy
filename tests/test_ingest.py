from __future__ import annotations

import hashlib
import re

import chromadb
import httpx
import pytest
import respx
from chromadb.utils.embedding_functions import register_embedding_function

from shippy.ingest import (
    IngestError,
    chunk_page,
    export_markdown,
    fetch_pages,
    main,
    require_env,
    resolve_books,
    strip_boilerplate,
    write_collection,
)

BASE = "http://bookstack.test"

BOOK_LIST = {
    "data": [{"id": 5, "slug": "operations-sops"}, {"id": 6, "slug": "client-profiles"}],
    "total": 2,
}


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={"Authorization": "Token 1:2"})


def page_list(entries: list[dict], total: int) -> dict:
    return {"data": entries, "total": total}


@respx.mock
def test_both_books_resolve() -> None:
    respx.get(f"{BASE}/api/books").mock(return_value=httpx.Response(200, json=BOOK_LIST))

    assert resolve_books(client()) == {"operations-sops": 5, "client-profiles": 6}


@respx.mock
def test_missing_book_raises_with_slug() -> None:
    respx.get(f"{BASE}/api/books").mock(
        return_value=httpx.Response(200, json=page_list([{"id": 5, "slug": "operations-sops"}], 1))
    )

    with pytest.raises(IngestError) as excinfo:
        resolve_books(client())

    assert "client-profiles" in str(excinfo.value)


def test_missing_env_variable_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("BOOKSTACK_URL", raising=False)
    monkeypatch.delenv("BOOKSTACK_TOKEN", raising=False)

    with pytest.raises(IngestError) as excinfo:
        require_env(tmp_path / ".env")

    assert "BOOKSTACK_URL" in str(excinfo.value)
    assert "BOOKSTACK_TOKEN" in str(excinfo.value)


@respx.mock
def test_pagination_stops_after_short_page() -> None:
    first = [{"id": i, "slug": f"p{i:03d}", "book_id": 1} for i in range(99)]
    first.append({"id": 200, "slug": "foreign-page", "book_id": 2})
    second = [{"id": 300, "slug": "zzz-last", "book_id": 1}]
    route = respx.get(f"{BASE}/api/pages").mock(
        side_effect=[
            httpx.Response(200, json=page_list(first, 101)),
            httpx.Response(200, json=page_list(second, 101)),
        ]
    )

    pages = fetch_pages(client(), 1)

    assert route.call_count == 2
    assert route.calls[0].request.url.params["page"] == "1"
    assert route.calls[0].request.url.params["count"] == "100"
    assert route.calls[1].request.url.params["page"] == "2"
    assert len(pages) == 100
    assert all(page["book_id"] == 1 for page in pages)
    assert [page["slug"] for page in pages] == sorted(page["slug"] for page in pages)


@respx.mock
def test_export_returns_markdown() -> None:
    respx.get(f"{BASE}/api/pages/9/export/markdown").mock(
        return_value=httpx.Response(200, text="# SOP - Alpha\nBody text\n")
    )

    assert export_markdown(client(), 9) == "# SOP - Alpha\nBody text\n"


@respx.mock
def test_export_404_raises_with_slug() -> None:
    respx.get(f"{BASE}/api/pages/9/export/markdown").mock(return_value=httpx.Response(404))
    respx.get(f"{BASE}/api/pages/9").mock(
        return_value=httpx.Response(200, json={"id": 9, "slug": "sop-alpha"})
    )

    with pytest.raises(IngestError) as excinfo:
        export_markdown(client(), 9)

    message = str(excinfo.value)
    assert "sop-alpha" in message
    assert "404" in message

PAGE = {
    "slug": "sop-alpha",
    "name": "SOP - Alpha",
    "revision_count": 2,
    "updated_at": "2026-10-09T05:04:35Z",
}

THREE_SECTIONS = (
    "# SOP - Alpha\n"
    "\n"
    "## One\n"
    "Alpha body one.\n"
    "\n"
    "## Two\n"
    "Alpha body two.\n"
    "\n"
    "## Three\n"
    "Alpha body three."
)


def test_strip_removes_title_line() -> None:
    stripped = strip_boilerplate("# SOP - Alpha\n\n## One\nBody.", "SOP - Alpha")

    assert stripped.splitlines() == ["## One", "Body."]


def test_strip_rejects_wrong_title() -> None:
    with pytest.raises(IngestError) as excinfo:
        strip_boilerplate("# Wrong Title\nBody.", "SOP - Alpha")

    assert "format drift" in str(excinfo.value)


def test_three_sections_make_three_chunks_with_stable_ids() -> None:
    chunks = chunk_page(PAGE, "operations-sops", THREE_SECTIONS, "sop_id")
    again = chunk_page(PAGE, "operations-sops", THREE_SECTIONS, "sop_id")

    assert len(chunks) == 3
    assert [chunk["id"] for chunk in chunks] == ["sop-alpha#0", "sop-alpha#1", "sop-alpha#2"]
    assert [chunk["id"] for chunk in again] == [chunk["id"] for chunk in chunks]


def test_path_line_is_exact_and_body_stays_verbatim() -> None:
    chunks = chunk_page(PAGE, "operations-sops", THREE_SECTIONS, "sop_id")

    assert chunks[0]["text"] == "SOP - Alpha > One\nAlpha body one."
    assert chunks[1]["text"] == "SOP - Alpha > Two\nAlpha body two."
    assert chunks[2]["text"] == "SOP - Alpha > Three\nAlpha body three."


def test_preamble_chunk_exists_when_text_precedes_first_h2() -> None:
    markdown = "# SOP - Alpha\n\nA short intro.\n\n## One\nAlpha body one."

    chunks = chunk_page(PAGE, "operations-sops", markdown, "sop_id")

    assert len(chunks) == 2
    assert chunks[0]["id"] == "sop-alpha#0"
    assert chunks[0]["text"] == "SOP - Alpha\nA short intro."
    assert chunks[1]["id"] == "sop-alpha#1"
    assert chunks[1]["text"] == "SOP - Alpha > One\nAlpha body one."


def test_missing_sections_raise() -> None:
    with pytest.raises(IngestError):
        chunk_page(PAGE, "operations-sops", "# SOP - Alpha\nJust text.", "sop_id")

    with pytest.raises(IngestError):
        chunk_page(PAGE, "operations-sops", "# SOP - Alpha\n", "sop_id")


def test_chunk_metadata_holds_five_keys() -> None:
    chunks = chunk_page(PAGE, "operations-sops", THREE_SECTIONS, "sop_id")
    client_page = {**PAGE, "slug": "client-profile-alpha", "name": "Client Profile - Alpha"}
    client_markdown = THREE_SECTIONS.replace("SOP - Alpha", "Client Profile - Alpha")
    client_chunks = chunk_page(client_page, "client-profiles", client_markdown, "client_id")

    expected = {
        "sop_id": "sop-alpha",
        "version": 2,
        "updated_at": "2026-10-09T05:04:35Z",
        "title": "SOP - Alpha",
        "book": "operations-sops",
    }
    for chunk in chunks:
        assert chunk["metadata"] == expected
    assert client_chunks[0]["metadata"]["client_id"] == "client-profile-alpha"
    assert client_chunks[0]["metadata"]["book"] == "client-profiles"
    assert "sop_id" not in client_chunks[0]["metadata"]

@register_embedding_function
class FakeEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "fake_embeddings"

    @staticmethod
    def build_from_config(config: dict) -> FakeEmbeddingFunction:
        return FakeEmbeddingFunction()

    def get_config(self) -> dict:
        return {}

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in input]

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(byte) for byte in digest[:8]]


CHUNK_A = {
    "id": "sop-alpha#0",
    "text": "SOP - Alpha > One\nAlpha body one.",
    "metadata": {
        "sop_id": "sop-alpha",
        "version": 2,
        "updated_at": "2026-10-09T05:04:35Z",
        "title": "SOP - Alpha",
        "book": "operations-sops",
    },
}

CHUNK_B = {
    "id": "sop-alpha#1",
    "text": "SOP - Alpha > Two\nAlpha body two.",
    "metadata": {
        "sop_id": "sop-alpha",
        "version": 2,
        "updated_at": "2026-10-09T05:04:35Z",
        "title": "SOP - Alpha",
        "book": "operations-sops",
    },
}


def test_write_collection_round_trip_with_second_client(tmp_path) -> None:
    path = tmp_path / "chroma"

    write_collection([CHUNK_A, CHUNK_B], "sops", path, FakeEmbeddingFunction())

    second = chromadb.PersistentClient(path=str(path))
    stored = second.get_collection("sops").get(include=["metadatas"])
    found = dict(zip(stored["ids"], stored["metadatas"]))

    assert found == {CHUNK_A["id"]: CHUNK_A["metadata"], CHUNK_B["id"]: CHUNK_B["metadata"]}


def test_write_collection_drop_rule_keeps_second_write(tmp_path) -> None:
    path = tmp_path / "chroma"

    write_collection([CHUNK_A, CHUNK_B], "sops", path, FakeEmbeddingFunction())
    write_collection([CHUNK_B], "sops", path, FakeEmbeddingFunction())

    stored = chromadb.PersistentClient(path=str(path)).get_collection("sops").get()

    assert stored["ids"] == [CHUNK_B["id"]]

MAIN_PAGES = [
    {
        "id": 11,
        "slug": "sop-alpha",
        "book_id": 5,
        "name": "SOP - Alpha",
        "revision_count": 1,
        "updated_at": "2026-10-09T05:04:35Z",
    },
    {
        "id": 12,
        "slug": "sop-beta",
        "book_id": 5,
        "name": "SOP - Beta",
        "revision_count": 3,
        "updated_at": "2026-10-09T05:05:00Z",
    },
    {
        "id": 21,
        "slug": "client-profile-gamma",
        "book_id": 6,
        "name": "Client Profile - Gamma",
        "revision_count": 1,
        "updated_at": "2026-10-09T05:06:00Z",
    },
]

MAIN_EXPORTS = {
    11: "# SOP - Alpha\n\n## One\nAlpha body one.\n\n## Two\nAlpha body two.",
    12: "# SOP - Beta\n\n## One\nBeta body one.",
    21: "# Client Profile - Gamma\n\n## Account\nGamma account text.",
}


@respx.mock
def test_main_runs_offline_and_reports_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOOKSTACK_URL", BASE)
    monkeypatch.setenv("BOOKSTACK_TOKEN", "1:fake-token")

    respx.get(f"{BASE}/api/books").mock(return_value=httpx.Response(200, json=BOOK_LIST))
    respx.get(f"{BASE}/api/pages").mock(
        side_effect=lambda request: httpx.Response(200, json=page_list(MAIN_PAGES, 3))
    )
    respx.get(url__regex=rf"{re.escape(BASE)}/api/pages/\d+/export/markdown").mock(
        side_effect=lambda request: httpx.Response(
            200, text=MAIN_EXPORTS[int(request.url.path.split("/")[3])]
        )
    )

    exit_code = main(FakeEmbeddingFunction(), tmp_path / "chroma")
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "sops: 3 chunks from 2 pages",
        "clients: 1 chunks from 1 pages",
        "round-trip: 4 chunks verified with metadata",
    ]

    stored = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    assert stored.get_collection("sops").count() == 3
    assert stored.get_collection("clients").count() == 1


def test_main_reports_missing_env_on_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOOKSTACK_URL", raising=False)
    monkeypatch.delenv("BOOKSTACK_TOKEN", raising=False)

    exit_code = main(FakeEmbeddingFunction(), tmp_path / "chroma")
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert "BOOKSTACK_URL" in captured.err
