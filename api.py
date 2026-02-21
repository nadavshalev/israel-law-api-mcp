from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, List
import asyncio

from fastapi import Body, FastAPI, HTTPException, Path, Query, Request
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from data.citations import build_citations_url
from data.law_get import get_law_sections_text, get_law_sections_titles, wide_law_search
from config import (
    CONCURRENT_LIMIT_ENABLED,
    CONCURRENT_LIMIT_TOTAL,
    MAX_SEARCH_LIMIT,
    MAX_SEARCH_PHRASE_LEN,
    MAX_SECTION_TEXT_CHARS,
    MAX_SECTIONS_PER_REQUEST,
    MCP_ALLOWED_HOSTS,
    MCP_ALLOWED_ORIGINS,
    MCP_DNS_REBINDING_PROTECTION,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_IP,
)


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=MCP_DNS_REBINDING_PROTECTION,
    allowed_hosts=MCP_ALLOWED_HOSTS,
    allowed_origins=MCP_ALLOWED_ORIGINS,
)

mcp = FastMCP(
    name="Israel Law MCP",
    instructions=(
        "Provides tools for searching and reading Israeli legislation from Hebrew Wikisource. "
        "Typical workflow: "
        "(1) mcp_search_laws to find a law by name and get its page_id, "
        "(2) mcp_list_sections to browse available sections, "
        "(3) mcp_get_sections_text to read the full text of specific sections, "
        "(4) mcp_build_citations to generate source URLs. "
        "All law names and content are in Hebrew."
    ),
    stateless_http=True,
    streamable_http_path="/",
    transport_security=transport_security,
)

mcp_app = mcp.streamable_http_app()

if RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_PER_IP])
    limit = limiter.limit
else:
    limiter = None

    def limit(_: str):
        def decorator(func):
            return func

        return decorator


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


api_app = FastAPI(title="Israel Law Data API")


class SectionsRequest(BaseModel):
    sections: List[str] = Field(..., min_length=1, description="Section numbers")
    full: bool = Field(False, description="Return full section text")


class CitationsRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Law title on Wikisource")
    sections: List[str] = Field(..., min_length=1, description="Section numbers")


def _normalize_sections(sections: List[str]) -> List[str]:
    normalized = [str(section).strip() for section in sections]
    return [section for section in normalized if section]


def _truncate_text(text: str, full: bool) -> str:
    if full or MAX_SECTION_TEXT_CHARS <= 0:
        return text
    if len(text) <= MAX_SECTION_TEXT_CHARS:
        return text
    return text[:MAX_SECTION_TEXT_CHARS]


class ConcurrencyLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.enabled = CONCURRENT_LIMIT_ENABLED
        self.total_semaphore = asyncio.Semaphore(max(CONCURRENT_LIMIT_TOTAL, 1))

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        await self.total_semaphore.acquire()
        try:
            return await call_next(request)
        finally:
            self.total_semaphore.release()


@mcp.tool(
    description=(
        "Search Israeli legislation on Hebrew Wikisource by a Hebrew keyword or phrase. "
        "Use this as the first step to find the page_id of a law before fetching its sections. "
        "The phrase should be in Hebrew (e.g. 'חוק העונשין', 'צו הגנת הצרכן'). "
        "Returns a list of matching laws, each with 'title' (Hebrew law name) and 'page_id' (Wikisource page ID). "
        "Use the returned page_id with mcp_list_sections or mcp_get_sections_text. "
        "If you didn't get the desired law, try modifying the search phrase and searching again. "
    )
)
def mcp_search_laws(
    phrase: Annotated[str, Field(description="Hebrew search phrase for the law name (e.g. 'חוק העונשין')")],
    limit: Annotated[int, Field(description="Maximum number of results to return (default 10, max 20)")] = 10,
) -> List[dict]:
    phrase = phrase.strip()
    if not phrase:
        raise ValueError("phrase must not be empty")
    if len(phrase) > MAX_SEARCH_PHRASE_LEN:
        raise ValueError("phrase is too long")
    if limit > MAX_SEARCH_LIMIT:
        limit = MAX_SEARCH_LIMIT
    return wide_law_search(phrase, limit=limit)


@mcp.tool(
    description=(
        "List all section numbers and titles for a given Israeli law. "
        "Use this after mcp_search_laws to browse the structure of a law before fetching full text. "
        "Returns a list of objects with 'number' (section number, e.g. '1', '2א') and 'title' (Hebrew section heading). "
        "Pass the desired section numbers to mcp_get_sections_text to retrieve their full text. "
        "If you don't see the section you're looking for, you can try different law page_id or "
        "even search again with a modified phrase to find a different law page_id that might have the sections you need."
    )
)
def mcp_list_sections(
    page_id: Annotated[int, Field(description="Wikisource page ID of the law (obtained from mcp_search_laws)")],
) -> List[dict]:
    return get_law_sections_titles(page_id)


@mcp.tool(
    description=(
        "Fetch the full text of specific sections within an Israeli law. "
        "Use this after mcp_list_sections to retrieve the content of one or more sections by their number. "
        "Returns a list of objects with 'number', 'title', and 'text' for each matched section. "
        "By default text is truncated to 10,000 characters per section; set full=true to get the complete text. "
        "Up to 10 sections can be requested at once."
    )
)
def mcp_get_sections_text(
    page_id: Annotated[int, Field(description="Wikisource page ID of the law (obtained from mcp_search_laws)")],
    sections: Annotated[List[str], Field(description="Section numbers to fetch (e.g. ['1', '2', '3א'])")],
    full: Annotated[bool, Field(description="If true, return complete section text without truncation")] = False,
) -> List[dict]:
    sections_numbers = _normalize_sections(sections)
    if not sections_numbers:
        raise ValueError("sections must not be empty")
    if len(sections_numbers) > MAX_SECTIONS_PER_REQUEST:
        raise ValueError("too many sections requested")
    results = get_law_sections_text(page_id, sections_numbers)
    for section in results:
        section["text"] = _truncate_text(section.get("text", ""), full)
    return results


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
    title = title.strip()
    if not title:
        raise ValueError("title must not be empty")
    sections_numbers = _normalize_sections(sections)
    if not sections_numbers:
        raise ValueError("sections must not be empty")
    return build_citations_url(title, sections_numbers)


@api_app.get("/health")
@limit(RATE_LIMIT_PER_IP)
def health(request: Request) -> dict:
    return {"status": "ok"}


@api_app.get("/laws/search")
@limit(RATE_LIMIT_PER_IP)
def search_laws(
    request: Request,
    phrase: str = Query(..., min_length=1, description="Search phrase"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
) -> dict:
    phrase = phrase.strip()
    if not phrase:
        raise HTTPException(status_code=400, detail="phrase must not be empty")
    if len(phrase) > MAX_SEARCH_PHRASE_LEN:
        raise HTTPException(status_code=400, detail="phrase is too long")
    if limit > MAX_SEARCH_LIMIT:
        limit = MAX_SEARCH_LIMIT
    results = wide_law_search(phrase, limit=limit)
    return {"results": results}


@api_app.get("/laws/{page_id}/sections")
@limit(RATE_LIMIT_PER_IP)
def list_sections(
    request: Request,
    page_id: int = Path(..., ge=1, description="Wikisource page id"),
) -> dict:
    sections = get_law_sections_titles(page_id)
    if not sections:
        raise HTTPException(status_code=404, detail="No sections found")
    return {"sections": sections}


@api_app.post("/laws/{page_id}/sections/text")
@limit(RATE_LIMIT_PER_IP)
def get_sections_text(
    request: Request,
    payload: SectionsRequest = Body(...),
    page_id: int = Path(..., ge=1, description="Wikisource page id"),
) -> dict:
    sections_numbers = _normalize_sections(payload.sections)
    if not sections_numbers:
        raise HTTPException(status_code=400, detail="sections must not be empty")
    if len(sections_numbers) > MAX_SECTIONS_PER_REQUEST:
        raise HTTPException(status_code=400, detail="too many sections requested")
    sections = get_law_sections_text(page_id, sections_numbers)
    if not sections:
        raise HTTPException(status_code=404, detail="No matching sections found")
    for section in sections:
        section["text"] = _truncate_text(section.get("text", ""), payload.full)
    return {"sections": sections}


@api_app.post("/citations")
@limit(RATE_LIMIT_PER_IP)
def citations(request: Request, payload: CitationsRequest = Body(...)) -> dict:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title must not be empty")
    sections_numbers = _normalize_sections(payload.sections)
    if not sections_numbers:
        raise HTTPException(status_code=400, detail="sections must not be empty")
    urls = build_citations_url(title, sections_numbers)
    return {"citations": urls}


app = FastAPI(lifespan=lifespan)
app.mount("/api", api_app)
app.mount("/mcp", mcp_app)

if RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    api_app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    api_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    api_app.add_middleware(SlowAPIMiddleware)

app.add_middleware(ConcurrencyLimiterMiddleware)
