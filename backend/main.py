"""FastAPI server exposing paper resolution and citation tree endpoints."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from crawler import crawl_citations, stream_crawl
from resolver import ResolveError, resolve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("citation_visualizer")

app = FastAPI(title="Citation Visualizer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResolveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="URL, DOI, ArXiv ID, S2 ID, or title")


class TreeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    # Claude + web search is slow (~10-20s per node) and costly (~$0.05-0.15
    # per node). Keep defaults small; users can dial up in the UI.
    max_depth: int = Field(1, ge=0, le=3)
    max_per_node: int = Field(5, ge=1, le=20)
    max_total_nodes: int = Field(50, ge=1, le=500)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/resolve")
async def api_resolve(req: ResolveRequest) -> dict:
    try:
        paper = await resolve(req.query)
    except ResolveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": paper.paper_id,
        "title": paper.title,
        "year": paper.year,
        "authors": paper.authors,
        "citationCount": paper.citation_count,
        "externalIds": paper.external_ids,
        "venue": paper.venue,
        "url": paper.url,
    }


@app.post("/api/tree")
async def api_tree(req: TreeRequest) -> dict:
    try:
        paper = await resolve(req.query)
    except ResolveError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log.info(
        "Crawling citations for %s (depth=%d, per_node=%d, max=%d)",
        paper.paper_id, req.max_depth, req.max_per_node, req.max_total_nodes,
    )

    tree = await crawl_citations(
        root_id=paper.paper_id,
        root_meta={
            "title": paper.title,
            "year": paper.year,
            "authors": paper.authors,
            "citationCount": paper.citation_count,
            "externalIds": paper.external_ids,
            "venue": paper.venue,
            "url": paper.url,
        },
        max_depth=req.max_depth,
        max_per_node=req.max_per_node,
        max_total_nodes=req.max_total_nodes,
    )
    return tree


@app.get("/api/tree/stream")
async def api_tree_stream(
    query: str = Query(..., min_length=1),
    max_depth: int = Query(1, ge=0, le=3),
    max_per_node: int = Query(5, ge=1, le=20),
    max_total_nodes: int = Query(50, ge=1, le=500),
):
    """Server-Sent Events stream of nodes/edges as they are discovered."""
    try:
        paper = await resolve(query)
    except ResolveError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def event_gen():
        # Send the resolved paper info first so the client can show "Found: ..." immediately.
        yield _sse({
            "type": "resolved",
            "paper": {
                "id": paper.paper_id,
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors,
                "citationCount": paper.citation_count,
                "externalIds": paper.external_ids,
                "venue": paper.venue,
                "url": paper.url,
            },
        })
        async for ev in stream_crawl(
            root_id=paper.paper_id,
            root_meta={
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors,
                "citationCount": paper.citation_count,
                "externalIds": paper.external_ids,
            },
            max_depth=max_depth,
            max_per_node=max_per_node,
            max_total_nodes=max_total_nodes,
        ):
            yield _sse(ev)
            # Let the event loop flush.
            await asyncio.sleep(0)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=True)
