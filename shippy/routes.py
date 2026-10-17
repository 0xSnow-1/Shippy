from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shippy import store, workflow
from shippy.compose import LLMProvider, compose
from shippy.retrieve import SearchResult
from shippy.validate import validate

SearchFn = Callable[..., SearchResult]


def source_links(chunks: list[dict]) -> list[str]:
    base = os.environ.get("BOOKSTACK_URL", "http://localhost:8080").rstrip("/")
    seen: list[str] = []
    for chunk in chunks:
        sop_id = chunk.get("metadata", {}).get("sop_id", "")
        if not sop_id or sop_id in seen:
            continue
        seen.append(sop_id)
    return [f"{base}/books/operations-sops/page/{sop_id}" for sop_id in seen]


def refusal(reason: str, links: list[str]) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "answer": "",
            "quote": "",
            "proposed_action": "none",
            "refused": True,
            "reason": reason,
            "source_links": links,
        },
    )


def create_router(search: SearchFn, provider: LLMProvider) -> APIRouter:
    router = APIRouter()

    @router.post("/lookup")
    async def lookup(request: Request) -> Any:
        body = await request.json()
        query = body.get("query") or body.get("question") or ""

        result = search(query)
        if result.status == "no_match":
            considered = search(query, floor=float("inf"))
            return refusal("no matching SOP found", source_links(considered.chunks))

        precheck = validate(result, None)
        if not precheck.ok:
            return refusal(precheck.reason, precheck.sources)

        answer = compose(query, result.chunks, provider)
        validation = validate(result, answer)
        if not validation.ok:
            return refusal(validation.reason, validation.sources)

        best = result.chunks[0]["metadata"]
        return {
            "answer": answer.answer,
            "quote": answer.quote,
            "proposed_action": answer.proposed_action,
            "source_id": best.get("sop_id"),
            "source_links": source_links(result.chunks[:1]),
        }

    return router


def create_workflow_router(db_path: str | Path | None = None) -> APIRouter:
    router = APIRouter()

    @router.post("/workflows/run")
    async def start_run(request: Request) -> Any:
        try:
            body = await request.json()
        except ValueError:
            body = None
        action = body.get("action") if isinstance(body, dict) else None
        payload = body.get("payload") if isinstance(body, dict) else None
        if not isinstance(action, str) or not isinstance(payload, dict):
            return JSONResponse(status_code=400, content={"error": "action and payload are required"})

        conn = store.connect(db_path)
        try:
            return workflow.start(conn, action, payload)
        except workflow.UnknownActionError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        finally:
            conn.close()

    @router.post("/workflows/{run_id}/approve")
    async def approve_run(run_id: str) -> Any:
        conn = store.connect(db_path)
        try:
            return workflow.approve(conn, run_id, db_path=db_path)
        except workflow.UnknownRunError as exc:
            return JSONResponse(status_code=404, content={"error": str(exc)})
        except workflow.InvalidStateError as exc:
            return JSONResponse(status_code=409, content={"error": str(exc)})
        except workflow.TaskFailedError as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})
        finally:
            conn.close()

    @router.post("/workflows/{run_id}/reject")
    async def reject_run(run_id: str) -> Any:
        conn = store.connect(db_path)
        try:
            return workflow.reject(conn, run_id)
        except workflow.UnknownRunError as exc:
            return JSONResponse(status_code=404, content={"error": str(exc)})
        except workflow.InvalidStateError as exc:
            return JSONResponse(status_code=409, content={"error": str(exc)})
        finally:
            conn.close()

    @router.get("/runs/{run_id}")
    async def read_run(run_id: str) -> Any:
        conn = store.connect(db_path)
        try:
            return workflow.replay(conn, run_id)
        except workflow.UnknownRunError as exc:
            return JSONResponse(status_code=404, content={"error": str(exc)})
        finally:
            conn.close()

    return router
