from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import build_app, with_stubs


def test_rate_limit_per_ip(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_PER_IP="5/minute",
        MAX_SEARCH_PHRASE_LEN="120",
        MAX_SEARCH_LIMIT="20",
        MAX_SECTIONS_PER_REQUEST="10",
        MAX_SECTION_TEXT_CHARS="10000",
    )
    with_stubs(rest_mod, mcp_mod)

    client = TestClient(app)
    status_codes = []
    for _ in range(7):
        resp = client.get("/api/laws/search", params={"phrase": "x", "limit": 1})
        status_codes.append(resp.status_code)
        if resp.status_code == 429:
            break

    assert 429 in status_codes


def test_max_search_phrase_length(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_PHRASE_LEN="5",
        MAX_SEARCH_LIMIT="20",
    )
    with_stubs(rest_mod, mcp_mod)

    client = TestClient(app)
    resp_ok = client.get("/api/laws/search", params={"phrase": "12345", "limit": 1})
    resp_bad = client.get("/api/laws/search", params={"phrase": "123456", "limit": 1})

    assert resp_ok.status_code == 200
    assert resp_bad.status_code == 400


def test_search_limit_is_capped(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SEARCH_LIMIT="2",
    )
    with_stubs(rest_mod, mcp_mod)

    client = TestClient(app)
    resp = client.get("/api/laws/search", params={"phrase": "x", "limit": 50})

    assert resp.status_code == 200
    assert len(resp.json().get("results", [])) == 2


def test_max_sections_per_request(monkeypatch: pytest.MonkeyPatch):
    app, rest_mod, mcp_mod = build_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="false",
        MAX_SECTIONS_PER_REQUEST="2",
    )
    with_stubs(rest_mod, mcp_mod)

    client = TestClient(app)
    resp = client.post(
        "/api/laws/1/sections/text",
        json={"sections": ["1", "2", "3"]},
    )

    assert resp.status_code == 400


def test_text_truncation_and_full_override(monkeypatch: pytest.MonkeyPatch):
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
    text = resp.json()["sections"][0]["text"]
    assert len(text) == 5

    resp_full = client.post(
        "/api/laws/1/sections/text",
        json={"sections": ["1"], "full": True},
    )
    assert resp_full.status_code == 200
    text_full = resp_full.json()["sections"][0]["text"]
    assert len(text_full) == 20
