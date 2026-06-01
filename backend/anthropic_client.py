"""Shared Anthropic client and JSON schemas for paper extraction."""
from __future__ import annotations

import hashlib
import os
import re

from anthropic import AsyncAnthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

# Cap web-search invocations per Claude call to control cost. Each search
# is roughly $0.01; a typical citation lookup needs 2-4 searches.
MAX_WEB_SEARCHES = int(os.environ.get("ANTHROPIC_MAX_WEB_SEARCHES", "4"))


class MissingAPIKeyError(RuntimeError):
    pass


if not os.environ.get("ANTHROPIC_API_KEY"):
    # Defer the error to first call so the server still boots and the /api/health
    # probe passes; clients see a clear 500 when they try to actually use it.
    client = None  # type: ignore[assignment]
else:
    client = AsyncAnthropic()


def get_client() -> AsyncAnthropic:
    if client is None:
        raise MissingAPIKeyError(
            "ANTHROPIC_API_KEY is not set. Add it to your environment or "
            "docker-compose .env file and restart the backend."
        )
    return client


# ---------------------------------------------------------------------------
# JSON schemas (Anthropic structured outputs require additionalProperties:false
# and use anyOf for nullable fields).
# ---------------------------------------------------------------------------

_PAPER_PROPS = {
    "title": {"type": "string"},
    "authors": {"type": "array", "items": {"type": "string"}},
    "year": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
    "venue": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "doi": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "arxiv_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "url": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "citation_count": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
}

PAPER_SCHEMA = {
    "type": "object",
    "properties": _PAPER_PROPS,
    "required": list(_PAPER_PROPS.keys()),
    "additionalProperties": False,
}

CITATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "papers": {"type": "array", "items": PAPER_SCHEMA},
        "notes": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["papers", "notes"],
    "additionalProperties": False,
}


WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": MAX_WEB_SEARCHES,
}


def paper_fingerprint(title: str, authors: list[str], year: int | None) -> str:
    """Deterministic identifier so the same paper found via different queries
    deduplicates to one node in the tree."""
    norm_title = re.sub(r"\s+", " ", (title or "").strip().lower())
    norm_title = re.sub(r"[^\w\s]", "", norm_title)
    first_author = (authors[0] if authors else "").strip().lower()
    first_author = re.sub(r"[^\w]", "", first_author)
    seed = f"{norm_title}|{first_author}|{year or ''}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def extract_text_blocks(message) -> str:
    """Concatenate any text blocks in a Claude response — useful for the
    structured-output text payload."""
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)
