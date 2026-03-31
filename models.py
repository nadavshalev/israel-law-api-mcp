from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


# --- Request models ---

class SectionsRequest(BaseModel):
    sections: List[str] = Field(..., min_length=1, description="Section numbers to fetch (e.g. ['1', '2', '3א'])")
    full: bool = Field(False, description="Return full section text without truncation")


class CitationsRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Exact Hebrew law title as it appears on Wikisource")
    sections: List[str] = Field(..., min_length=1, description="Section numbers to generate citation URLs for")


# --- Shared output models ---

class LawResult(BaseModel):
    """A law matching the search query."""
    title: str = Field(description="Hebrew law name as it appears on Wikisource")
    page_id: int = Field(description="Wikisource page ID — pass this to mcp_list_sections or mcp_get_sections_text")
    law_id: int | None = Field(None, description="Israeli legislation registry ID (from {{ח:מאגר}} template), if present")


class SectionTitle(BaseModel):
    """A section entry from a law's table of contents."""
    number: str = Field(description="Section number (e.g. '1', '2א', '3(ב)')")
    title: str = Field(description="Hebrew section heading")


class SectionText(BaseModel):
    """A section with its full or truncated text."""
    number: str = Field(description="Section number (e.g. '1', '2א', '3(ב)')")
    title: str = Field(description="Hebrew section heading")
    text: str = Field(description="Cleaned section text; truncated to MAX_SECTION_TEXT_CHARS unless full=true")


# --- REST response wrappers ---

class HealthResponse(BaseModel):
    status: str = Field(description="Always 'ok' when the server is running")


class SearchResponse(BaseModel):
    results: List[LawResult]


class SectionsListResponse(BaseModel):
    sections: List[SectionTitle]


class SectionsTextResponse(BaseModel):
    sections: List[SectionText]


class CitationsResponse(BaseModel):
    citations: List[str] = Field(description="Direct Wikisource URLs linking to each requested section anchor")
