"""Recursively crawl citations by asking Claude (with web search) to enumerate
papers that cite a given paper."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from anthropic import APIStatusError

from anthropic_client import (
    CITATIONS_SCHEMA,
    MODEL,
    WEB_SEARCH_TOOL,
    extract_text_blocks,
    get_client,
    paper_fingerprint,
)

log = logging.getLogger("crawler")


CITATIONS_SYSTEM = """You are a research-paper citation discovery assistant.

Given a single source paper, your job is to find OTHER papers that cite it
(i.e. papers in which the source paper appears in the bibliography). Use the
`web_search` tool to query Google Scholar, Semantic Scholar, OpenAlex, ArXiv,
or publisher pages.

Strategies that work well:
- Search Google Scholar for the source paper's title together with "cited by"
- Search Semantic Scholar / OpenAlex for the paper's name and follow citation lists
- For well-known papers, browse recent ArXiv preprints that reference the title

Return up to the requested number of CITING papers (papers that cite the source).
Do NOT include the source paper itself in the results.

For each paper return:
- title, authors, year, venue
- doi / arxiv_id / url if discoverable
- citation_count: approximate citation count if visible, else null

If you cannot find any citing papers (or the source paper is too new / too
obscure for the web to surface citations), return an empty `papers` array and
explain in `notes`. Better to return fewer high-confidence results than to
fabricate citations.
"""


@dataclass
class PaperNode:
    paper_id: str
    title: str
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    citation_count: int | None = None
    external_ids: dict = field(default_factory=dict)
    venue: str | None = None
    url: str | None = None
    depth: int = 0
    parent_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.paper_id,
            "title": self.title,
            "year": self.year,
            "authors": self.authors,
            "citationCount": self.citation_count,
            "externalIds": self.external_ids,
            "venue": self.venue,
            "url": self.url,
            "depth": self.depth,
            "parent": self.parent_id,
        }


def _user_prompt(node: PaperNode, limit: int) -> str:
    bits = [f"Title: {node.title}"]
    if node.authors:
        bits.append("Authors: " + ", ".join(node.authors[:8]))
    if node.year:
        bits.append(f"Year: {node.year}")
    if node.venue:
        bits.append(f"Venue: {node.venue}")
    if node.external_ids.get("DOI"):
        bits.append(f"DOI: {node.external_ids['DOI']}")
    if node.external_ids.get("ArXiv"):
        bits.append(f"ArXiv: {node.external_ids['ArXiv']}")
    if node.url:
        bits.append(f"URL: {node.url}")

    return (
        f"Source paper:\n" + "\n".join(bits) + "\n\n"
        f"Find up to {limit} OTHER papers that cite this source paper. "
        f"Do not include the source paper itself."
    )


async def _fetch_citing_papers(node: PaperNode, limit: int) -> list[dict]:
    try:
        client = get_client()
    except Exception as e:
        log.warning("Anthropic client unavailable: %s", e)
        return []
    try:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=[
                {
                    "type": "text",
                    "text": CITATIONS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[WEB_SEARCH_TOOL],
            output_config={
                "format": {"type": "json_schema", "schema": CITATIONS_SCHEMA},
            },
            messages=[{"role": "user", "content": _user_prompt(node, limit)}],
        )
    except APIStatusError as e:
        log.warning("Anthropic error while fetching citations for %s: %s", node.title[:60], e)
        return []

    # Server-side web search can hit its iteration limit; resume once.
    if message.stop_reason == "pause_turn":
        try:
            message = await client.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=[
                    {
                        "type": "text",
                        "text": CITATIONS_SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[WEB_SEARCH_TOOL],
                output_config={
                    "format": {"type": "json_schema", "schema": CITATIONS_SCHEMA},
                },
                messages=[
                    {"role": "user", "content": _user_prompt(node, limit)},
                    {"role": "assistant", "content": message.content},
                ],
            )
        except APIStatusError as e:
            log.warning("Resume after pause_turn failed: %s", e)

    if message.stop_reason == "refusal":
        log.info("Refusal while fetching citations for %s", node.title[:60])
        return []

    text = extract_text_blocks(message)
    if not text.strip():
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        log.warning("Could not parse citations JSON for %s: %s", node.title[:60], e)
        return []

    return data.get("papers") or []


def _make_child(raw: dict, parent: PaperNode) -> PaperNode | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    authors = [a for a in (raw.get("authors") or []) if a]
    year = raw.get("year")
    ext = {}
    if raw.get("doi"):
        ext["DOI"] = raw["doi"]
    if raw.get("arxiv_id"):
        ext["ArXiv"] = raw["arxiv_id"]
    return PaperNode(
        paper_id=paper_fingerprint(title, authors, year),
        title=title,
        year=year,
        authors=authors,
        citation_count=raw.get("citation_count"),
        external_ids=ext,
        venue=raw.get("venue"),
        url=raw.get("url"),
        depth=parent.depth + 1,
        parent_id=parent.paper_id,
    )


async def crawl_citations(
    root_id: str,
    root_meta: dict,
    *,
    max_depth: int,
    max_per_node: int,
    max_total_nodes: int = 1000,
    concurrency: int = 3,
) -> dict:
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")
    if max_per_node < 1:
        raise ValueError("max_per_node must be >= 1")

    seen: dict[str, PaperNode] = {}
    edges: list[dict] = []
    root = PaperNode(
        paper_id=root_id,
        title=root_meta.get("title") or "(root)",
        year=root_meta.get("year"),
        authors=root_meta.get("authors") or [],
        citation_count=root_meta.get("citationCount"),
        external_ids=root_meta.get("externalIds") or {},
        venue=root_meta.get("venue"),
        url=root_meta.get("url"),
        depth=0,
    )
    seen[root_id] = root

    sem = asyncio.Semaphore(concurrency)
    truncated = False

    async def expand(node: PaperNode) -> list[PaperNode]:
        nonlocal truncated
        if node.depth >= max_depth:
            return []
        async with sem:
            raws = await _fetch_citing_papers(node, max_per_node)
        new_children: list[PaperNode] = []
        for raw in raws[:max_per_node]:
            child = _make_child(raw, node)
            if not child or child.paper_id == node.paper_id:
                continue
            edges.append({"source": node.paper_id, "target": child.paper_id})
            if child.paper_id in seen:
                continue
            if len(seen) >= max_total_nodes:
                truncated = True
                break
            seen[child.paper_id] = child
            new_children.append(child)
        return new_children

    frontier: list[PaperNode] = [root]
    for _ in range(max_depth):
        if not frontier or truncated:
            break
        results = await asyncio.gather(*(expand(n) for n in frontier))
        frontier = [c for batch in results for c in batch]
        if not frontier:
            break

    return {
        "root": root_id,
        "nodes": [n.to_dict() for n in seen.values()],
        "edges": edges,
        "truncated": truncated,
        "rateLimited": False,
        "stats": {
            "totalNodes": len(seen),
            "totalEdges": len(edges),
            "maxDepth": max_depth,
            "maxPerNode": max_per_node,
        },
    }


async def stream_crawl(
    root_id: str,
    root_meta: dict,
    *,
    max_depth: int,
    max_per_node: int,
    max_total_nodes: int = 1000,
    concurrency: int = 3,
) -> AsyncIterator[dict]:
    """Streaming version: yields events as nodes are discovered."""
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    seen: dict[str, PaperNode] = {}
    root = PaperNode(
        paper_id=root_id,
        title=root_meta.get("title") or "(root)",
        year=root_meta.get("year"),
        authors=root_meta.get("authors") or [],
        citation_count=root_meta.get("citationCount"),
        external_ids=root_meta.get("externalIds") or {},
        venue=root_meta.get("venue"),
        url=root_meta.get("url"),
        depth=0,
    )
    seen[root.paper_id] = root
    yield {"type": "root", "node": root.to_dict()}

    sem = asyncio.Semaphore(concurrency)
    truncated = False
    queue: asyncio.Queue = asyncio.Queue()

    async def expand(node: PaperNode):
        nonlocal truncated
        if node.depth >= max_depth:
            return
        async with sem:
            raws = await _fetch_citing_papers(node, max_per_node)
        for raw in raws[:max_per_node]:
            child = _make_child(raw, node)
            if not child or child.paper_id == node.paper_id:
                continue
            edge = {"source": node.paper_id, "target": child.paper_id}
            if child.paper_id in seen:
                await queue.put({"type": "edge", "edge": edge})
                continue
            if len(seen) >= max_total_nodes:
                truncated = True
                break
            seen[child.paper_id] = child
            await queue.put({"type": "node", "node": child.to_dict(), "edge": edge})

    frontier: list[PaperNode] = [root]
    for _ in range(max_depth):
        if not frontier or truncated:
            break
        tasks = [asyncio.create_task(expand(n)) for n in frontier]
        gather_task = asyncio.create_task(asyncio.gather(*tasks))
        next_frontier: list[PaperNode] = []
        while not gather_task.done() or not queue.empty():
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield ev
                if ev["type"] == "node":
                    nid = ev["node"]["id"]
                    if nid in seen:
                        next_frontier.append(seen[nid])
            except asyncio.TimeoutError:
                continue
        await gather_task
        frontier = next_frontier

    yield {
        "type": "done",
        "stats": {
            "totalNodes": len(seen),
            "totalEdges": 0,
            "maxDepth": max_depth,
            "maxPerNode": max_per_node,
        },
        "truncated": truncated,
        "rateLimited": False,
    }
