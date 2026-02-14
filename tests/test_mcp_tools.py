from __future__ import annotations

import importlib

import pytest


def build_module(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))

    import config as config_module
    import api as api_module

    importlib.reload(config_module)
    importlib.reload(api_module)

    return api_module


def stub_wide_law_search(_: str, limit: int = 10):
    return [{"title": "Law", "page_id": 1} for _ in range(limit)]


def stub_get_law_sections_titles(_: int):
    return [{"section_id": "1:Title", "number": "1", "title": "Title"}]


def stub_get_law_sections_text(_: int, sections_num: list[str]):
    return [
        {
            "section_id": f"{num}:Title",
            "number": num,
            "title": "Title",
            "text": "X" * 20,
        }
        for num in sections_num
    ]


def with_stubs(api_module) -> None:
    api_module.wide_law_search = stub_wide_law_search
    api_module.get_law_sections_titles = stub_get_law_sections_titles
    api_module.get_law_sections_text = stub_get_law_sections_text


def test_mcp_search_laws(monkeypatch: pytest.MonkeyPatch):
    api_module = build_module(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_LIMIT="2",
        MAX_SEARCH_PHRASE_LEN="120",
    )
    with_stubs(api_module)

    results = api_module.mcp_search_laws("test", limit=10)
    assert len(results) == 2


def test_mcp_get_sections_text_full(monkeypatch: pytest.MonkeyPatch):
    api_module = build_module(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SECTION_TEXT_CHARS="5",
        MAX_SECTIONS_PER_REQUEST="10",
    )
    with_stubs(api_module)

    truncated = api_module.mcp_get_sections_text(1, ["1"])
    assert len(truncated[0]["text"]) == 5

    full = api_module.mcp_get_sections_text(1, ["1"], full=True)
    assert len(full[0]["text"]) == 20
