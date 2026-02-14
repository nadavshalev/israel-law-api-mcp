from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def build_app(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))

    import config as config_module
    import api as api_module

    importlib.reload(config_module)
    importlib.reload(api_module)

    return api_module.app, api_module


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


def test_health(monkeypatch: pytest.MonkeyPatch):
    app, api_module = build_app(monkeypatch, RATE_LIMIT_ENABLED="false")
    with_stubs(api_module)
    client = TestClient(app)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_search_laws(monkeypatch: pytest.MonkeyPatch):
    app, api_module = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_LIMIT="2",
        MAX_SEARCH_PHRASE_LEN="120",
    )
    with_stubs(api_module)
    client = TestClient(app)

    resp = client.get("/api/laws/search", params={"phrase": "test", "limit": 10})
    assert resp.status_code == 200
    assert len(resp.json().get("results", [])) == 2


def test_sections_text_full_override(monkeypatch: pytest.MonkeyPatch):
    app, api_module = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SECTION_TEXT_CHARS="5",
        MAX_SECTIONS_PER_REQUEST="10",
    )
    with_stubs(api_module)
    client = TestClient(app)

    resp = client.post("/api/laws/1/sections/text", json={"sections": ["1"]})
    assert resp.status_code == 200
    assert len(resp.json()["sections"][0]["text"]) == 5

    resp_full = client.post(
        "/api/laws/1/sections/text",
        json={"sections": ["1"], "full": True},
    )
    assert resp_full.status_code == 200
    assert len(resp_full.json()["sections"][0]["text"]) == 20
