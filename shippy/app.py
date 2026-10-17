from __future__ import annotations

import os
from pathlib import Path

import chromadb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shippy.compose import BedrockLLM, LLMProvider
from shippy.retrieve import COLLECTION_NAME, RELEVANCE_FLOOR, SearchResult, search_sop
from shippy.routes import SearchFn, create_router, create_workflow_router

CHROMA_PATH = Path("data/chroma")
PROTECTED_PREFIXES = ("/lookup", "/workflows", "/runs")
DEFAULT_DEV_KEY = "test-key"


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(PROTECTED_PREFIXES) and request.headers.get("x-api-key") != self.api_key:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        return await call_next(request)


def live_search(collection: chromadb.Collection) -> SearchFn:
    def search(query: str, floor: float = RELEVANCE_FLOOR) -> SearchResult:
        return search_sop(query, collection, floor=floor)

    return search


def open_sops_collection(path: Path = CHROMA_PATH) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(path))
    return client.get_collection(COLLECTION_NAME)


def get_app(
    search: SearchFn | None = None,
    provider: LLMProvider | None = None,
    api_key: str | None = None,
    db_path: str | Path | None = None,
) -> FastAPI:
    search = search or live_search(open_sops_collection())
    provider = provider or BedrockLLM()
    api_key = api_key if api_key is not None else os.environ.get("SHIPPY_API_KEY", DEFAULT_DEV_KEY)

    app = FastAPI(title="Shippy")
    app.add_middleware(APIKeyMiddleware, api_key=api_key)
    app.include_router(create_router(search, provider))
    app.include_router(create_workflow_router(db_path))

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
