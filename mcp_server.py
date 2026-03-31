from __future__ import annotations

from pathlib import Path
from typing import Annotated, List

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

import config
from data.citations import build_citations_url
from data.law_get import (
    get_law_sections_text,
    get_law_sections_titles,
    get_page_id_from_law_id,
    wide_law_search,
)
from models import LawResult, SectionText, SectionTitle
from validators import truncate_text, validate_limit, validate_phrase, validate_sections, validate_title

_description_path = Path(__file__).parent / "mcp_description.md"
_mcp_instructions = _description_path.read_text(encoding="utf-8")

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=config.MCP_DNS_REBINDING_PROTECTION,
    allowed_hosts=config.MCP_ALLOWED_HOSTS,
    allowed_origins=config.MCP_ALLOWED_ORIGINS,
)

mcp = FastMCP(
    name="Israel Law MCP",
    instructions=_mcp_instructions,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=transport_security,
)

mcp_app = mcp.streamable_http_app()


def _resolve_law_id_param(page_id: int | None, law_id: int | None) -> int:
    """Resolve exactly one of page_id / law_id to a page_id."""
    if page_id is not None and law_id is not None:
        raise ValueError("provide either page_id or law_id, not both")
    if page_id is None and law_id is None:
        raise ValueError("provide either page_id or law_id")
    if law_id is not None:
        resolved = get_page_id_from_law_id(law_id)
        if resolved is None:
            raise ValueError(f"law_id={law_id} not found in law map")
        return resolved
    return page_id  # type: ignore[return-value]


@mcp.tool(
    description=(
        "Search Israeli legislation on Hebrew Wikisource by a Hebrew keyword or phrase. "
        "Use this as the first step to find the page_id and law_id of a law. "
        "The phrase should be in Hebrew (e.g. 'חוק העונשין', 'צו הגנת הצרכן'). "
        "Returns a list of matching laws with 'title', 'page_id', and 'law_id' (when available). "
        "Pass either page_id or law_id to mcp_list_sections or mcp_get_sections_text. "
        "If you didn't get the desired law, try modifying the search phrase and searching again. "
    )
)
def mcp_search_laws(
    phrase: Annotated[str, Field(description="Hebrew search phrase for the law name (e.g. 'חוק העונשין')")],
    limit: Annotated[int, Field(description="Maximum number of results to return (default 10, max 20)")] = 10,
) -> List[LawResult]:
    phrase = validate_phrase(phrase)
    limit = validate_limit(limit)
    return [LawResult(**item) for item in wide_law_search(phrase, limit=limit)]


@mcp.tool(
    description=(
        "List all section numbers and titles for a given Israeli law. "
        "Use this after mcp_search_laws to browse the structure of a law before fetching full text. "
        "Returns a list of objects with 'number' (e.g. '1', '2א') and 'title' (Hebrew section heading). "
        "Pass the desired section numbers to mcp_get_sections_text to retrieve their full text. "
        "Provide either page_id (Wikisource page ID) or law_id (Israeli registry ID) — not both."
    )
)
def mcp_list_sections(
    page_id: Annotated[int | None, Field(description="Wikisource page ID (from mcp_search_laws)")] = None,
    law_id: Annotated[int | None, Field(description="Israeli legislation registry ID (from mcp_search_laws)")] = None,
) -> List[SectionTitle]:
    resolved = _resolve_law_id_param(page_id, law_id)
    return [SectionTitle(**item) for item in get_law_sections_titles(resolved)]


@mcp.tool(
    description=(
        "Fetch the full text of specific sections within an Israeli law. "
        "Use this after mcp_list_sections to retrieve the content of one or more sections by their number. "
        "Returns a list of objects with 'number', 'title', and 'text' for each matched section. "
        "By default text is truncated to 10,000 characters per section; set full=true to get the complete text. "
        "Up to 10 sections can be requested at once. "
        "Provide either page_id (Wikisource page ID) or law_id (Israeli registry ID) — not both."
    )
)
def mcp_get_sections_text(
    sections: Annotated[List[str], Field(description="Section numbers to fetch (e.g. ['1', '2', '3א'])")],
    page_id: Annotated[int | None, Field(description="Wikisource page ID (from mcp_search_laws)")] = None,
    law_id: Annotated[int | None, Field(description="Israeli legislation registry ID (from mcp_search_laws)")] = None,
    full: Annotated[bool, Field(description="If true, return complete section text without truncation")] = False,
) -> List[SectionText]:
    resolved = _resolve_law_id_param(page_id, law_id)
    sections_numbers = validate_sections(sections)
    results = get_law_sections_text(resolved, sections_numbers)
    return [
        SectionText(
            number=item["number"],
            title=item["title"],
            text=truncate_text(item.get("text", ""), full),
        )
        for item in results
    ]


@mcp.tool(
    description=(
        "Build direct Hebrew Wikisource citation URLs for specific sections of a law. "
        "Each URL links to the exact section anchor on the law's Wikisource page. "
        "Use this to provide verifiable source links when citing Israeli legislation. "
        "The title must match the exact Hebrew law title on Wikisource (e.g. 'חוק העונשין'). "
        "Returns a list of URLs, one per requested section."
    )
)
def mcp_build_citations(
    title: Annotated[str, Field(description="Exact Hebrew law title as it appears on Wikisource (e.g. 'חוק העונשין')")],
    sections: Annotated[List[str], Field(description="Section numbers to generate citation URLs for (e.g. ['1', '2', '3א'])")],
) -> List[str]:
    title = validate_title(title)
    sections_numbers = validate_sections(sections)
    return build_citations_url(title, sections_numbers)
