from __future__ import annotations

import pytest

from conftest import build_mcp_module, with_stubs


def test_mcp_search_laws(monkeypatch: pytest.MonkeyPatch):
    mcp_mod = build_mcp_module(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_LIMIT="2",
        MAX_SEARCH_PHRASE_LEN="120",
    )
    with_stubs(mcp_mod)

    results = mcp_mod.mcp_search_laws("test", limit=10)
    assert len(results) == 2


def test_mcp_get_sections_text_full(monkeypatch: pytest.MonkeyPatch):
    mcp_mod = build_mcp_module(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SECTION_TEXT_CHARS="5",
        MAX_SECTIONS_PER_REQUEST="10",
    )
    with_stubs(mcp_mod)

    truncated = mcp_mod.mcp_get_sections_text(["1"], page_id=1)
    assert len(truncated[0].text) == 5

    full = mcp_mod.mcp_get_sections_text(["1"], page_id=1, full=True)
    assert len(full[0].text) == 20
