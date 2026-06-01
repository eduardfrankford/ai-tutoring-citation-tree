"""Resolve a user-provided input (URL, DOI, ArXiv, title, Google Scholar URL)
to a single paper by asking Claude to identify it via web search."""
from __future__ import annotations

import json
from dataclasses import dataclass

from anthropic import APIStatusError

from anthropic_client import (
    MODEL,
    PAPER_SCHEMA,
    WEB_SEARCH_TOOL,
    MissingAPIKeyError,
    extract_text_blocks,
    get_client,
    paper_fingerprint,
)

RESOLVE_SYSTEM = """You are a research-paper identification assistant.

Given a user-supplied reference to a single academic paper, your job is to
identify that exact paper and return its bibliographic metadata.

The input may be:
- A DOI, ArXiv ID, or URL pointing to a paper (arxiv.org, semanticscholar.org, doi.org, publisher sites)
- A Google Scholar URL (https://scholar.google.com/...). For URLs with `?cites=<cluster_id>`,
  the cluster ID identifies the SOURCE paper whose citations the user wants to explore —
  you must identify that source paper. If you cannot resolve the cluster ID directly,
  search Google Scholar for the URL or extract any visible title/author hints.
- A free-text title (possibly with authors)

Use the `web_search` tool when necessary to verify the paper's identity. Prefer
the canonical title and author list as published.

Return ONE paper — the single best match. If you genuinely cannot identify the
paper, return an empty title and put the reason in any free-text response.

Fields:
- title: the paper's full title
- authors: author names in publication order (full names, not initials when known)
- year: publication year (integer) or null
- venue: conference/journal name or null
- doi: DOI string without URL prefix, or null
- arxiv_id: e.g. "2310.06825" or null
- url: a canonical URL for the paper (arxiv abs page, DOI link, publisher page) or null
- citation_count: approximate citation count from Google Scholar / Semantic Scholar if visible, else null
"""


@dataclass
class ResolvedPaper:
    paper_id: str
    title: str
    year: int | None
    authors: list[str]
    citation_count: int | None
    external_ids: dict
    venue: str | None
    url: str | None


class ResolveError(Exception):
    pass


def _user_prompt(query: str) -> str:
    return (
        f"Identify the paper referenced by the following input and return its metadata.\n\n"
        f"<input>\n{query.strip()}\n</input>"
    )


async def resolve(query: str) -> ResolvedPaper:
    if not query or not query.strip():
        raise ResolveError("Empty input.")

    try:
        client = get_client()
    except MissingAPIKeyError as e:
        raise ResolveError(str(e)) from e

    try:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": RESOLVE_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[WEB_SEARCH_TOOL],
            output_config={
                "format": {"type": "json_schema", "schema": PAPER_SCHEMA},
            },
            messages=[{"role": "user", "content": _user_prompt(query)}],
        )
    except APIStatusError as e:
        raise ResolveError(f"Anthropic API error ({e.status_code}): {e.message}") from e

    if message.stop_reason == "refusal":
        raise ResolveError("Claude declined to resolve this paper.")

    text = extract_text_blocks(message)
    if not text.strip():
        raise ResolveError("Empty response from Claude.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ResolveError(f"Could not parse Claude's response as JSON: {e}") from e

    title = (data.get("title") or "").strip()
    if not title:
        raise ResolveError(
            "Claude could not identify a single paper from that input. "
            "Try the paper's DOI, ArXiv ID, or full title."
        )

    authors = [a for a in (data.get("authors") or []) if a]
    year = data.get("year")
    external_ids = {}
    if data.get("doi"):
        external_ids["DOI"] = data["doi"]
    if data.get("arxiv_id"):
        external_ids["ArXiv"] = data["arxiv_id"]

    return ResolvedPaper(
        paper_id=paper_fingerprint(title, authors, year),
        title=title,
        year=year,
        authors=authors,
        citation_count=data.get("citation_count"),
        external_ids=external_ids,
        venue=data.get("venue"),
        url=data.get("url"),
    )
