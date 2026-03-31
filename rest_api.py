from __future__ import annotations

from fastapi import Body, FastAPI, HTTPException, Path, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

import config
from data.citations import build_citations_url
from data.law_get import (
    get_law_sections_text,
    get_law_sections_titles,
    resolve_id_to_page_id,
    wide_law_search,
)
from models import (
    CitationsRequest,
    CitationsResponse,
    HealthResponse,
    SearchResponse,
    SectionsListResponse,
    SectionsRequest,
    SectionsTextResponse,
)
from validators import truncate_text, validate_limit, validate_phrase, validate_sections, validate_title

if config.RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=[config.RATE_LIMIT_PER_IP])
    limit = limiter.limit
else:
    limiter = None

    def limit(_: str):
        def decorator(func):
            return func

        return decorator


api_app = FastAPI(title="Israel Law Data API")


def _resolve_or_404(id: int) -> int:
    """Resolve a law_id or page_id to a page_id, or raise 404."""
    page_id = resolve_id_to_page_id(id)
    if page_id is None:
        raise HTTPException(status_code=404, detail=f"Law not found for id={id}")
    return page_id


@api_app.get("/health", response_model=HealthResponse)
@limit(config.RATE_LIMIT_PER_IP)
def health(request: Request) -> dict:
    return {"status": "ok"}


@api_app.get("/laws/search", response_model=SearchResponse)
@limit(config.RATE_LIMIT_PER_IP)
def search_laws(
    request: Request,
    phrase: str = Query(..., min_length=1, description="Hebrew search phrase"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
) -> dict:
    try:
        phrase = validate_phrase(phrase)
        limit = validate_limit(limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    results = wide_law_search(phrase, limit=limit)
    return {"results": results}


@api_app.get("/laws/{id}/sections", response_model=SectionsListResponse)
@limit(config.RATE_LIMIT_PER_IP)
def list_sections(
    request: Request,
    id: int = Path(..., ge=1, description="Law ID or Wikisource page ID"),
) -> dict:
    page_id = _resolve_or_404(id)
    sections = get_law_sections_titles(page_id)
    if not sections:
        raise HTTPException(status_code=404, detail="No sections found")
    return {"sections": sections}


@api_app.post("/laws/{id}/sections/text", response_model=SectionsTextResponse)
@limit(config.RATE_LIMIT_PER_IP)
def get_sections_text(
    request: Request,
    payload: SectionsRequest = Body(...),
    id: int = Path(..., ge=1, description="Law ID or Wikisource page ID"),
) -> dict:
    page_id = _resolve_or_404(id)
    try:
        sections_numbers = validate_sections(payload.sections)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    sections = get_law_sections_text(page_id, sections_numbers)
    if not sections:
        raise HTTPException(status_code=404, detail="No matching sections found")
    for section in sections:
        section["text"] = truncate_text(section.get("text", ""), payload.full)
    return {"sections": sections}


@api_app.post("/citations", response_model=CitationsResponse)
@limit(config.RATE_LIMIT_PER_IP)
def citations(request: Request, payload: CitationsRequest = Body(...)) -> dict:
    try:
        title = validate_title(payload.title)
        sections_numbers = validate_sections(payload.sections)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    urls = build_citations_url(title, sections_numbers)
    return {"citations": urls}
