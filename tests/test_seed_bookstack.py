import httpx
import respx

from scripts.seed_bookstack import run_seed

BASE = "http://bookstack.test"

ENTRY = {"slug": "sop-alpha", "title": "SOP - Alpha", "markdown": "# Alpha\nBody", "book_slug": "operations-sops"}

BOOKS = {"data": [{"id": 2, "slug": "operations-sops"}, {"id": 3, "slug": "client-profiles"}], "total": 2}


def pages(*entries: dict) -> dict:
    return {"data": list(entries), "total": len(entries)}


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={"Authorization": "Token 1:2"})


@respx.mock
def test_existing_page_is_skipped() -> None:
    respx.get(f"{BASE}/api/pages").mock(return_value=httpx.Response(200, json=pages({"id": 7, "slug": "sop-alpha"})))
    respx.get(f"{BASE}/api/books").mock(return_value=httpx.Response(200, json=BOOKS))
    post = respx.post(f"{BASE}/api/pages").mock(return_value=httpx.Response(201))

    created, skipped, failed = run_seed(client(), [ENTRY])

    assert (created, skipped, failed) == (0, 1, 0)
    assert post.call_count == 0


@respx.mock
def test_missing_page_is_created() -> None:
    respx.get(f"{BASE}/api/pages").mock(return_value=httpx.Response(200, json=pages()))
    respx.get(f"{BASE}/api/books").mock(return_value=httpx.Response(200, json=BOOKS))
    post = respx.post(f"{BASE}/api/pages").mock(
        return_value=httpx.Response(201, json={"id": 9, "slug": "sop-alpha"})
    )

    created, skipped, failed = run_seed(client(), [ENTRY])

    assert (created, skipped, failed) == (1, 0, 0)
    assert post.call_count == 1
    assert post.calls[0].request.url.path == "/api/pages"
