from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import build_app, with_stubs


def test_health(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(monkeypatch, RATE_LIMIT_ENABLED="false")
    with_stubs(rest_mod, mcp_mod)
    client = TestClient(app)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_search_laws(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_LIMIT="2",
        MAX_SEARCH_PHRASE_LEN="120",
    )
    with_stubs(rest_mod, mcp_mod)
    client = TestClient(app)

    resp = client.get("/api/laws/search", params={"phrase": "test", "limit": 10})
    assert resp.status_code == 200
    assert len(resp.json().get("results", [])) == 2


def test_sections_text_full_override(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SECTION_TEXT_CHARS="5",
        MAX_SECTIONS_PER_REQUEST="10",
    )
    with_stubs(rest_mod, mcp_mod)
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
