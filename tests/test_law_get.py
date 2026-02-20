from __future__ import annotations

import json

import pytest

from data import law_get
from data.law_get import MAIN_PAGE_ID


def test_get_main_page_titles_from_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "page_247.json"
    monkeypatch.setattr(law_get, "_get_cache_path", lambda: cache_path)
    data = {"wikitext": "[[חוק ראשון]] [[חוק_שני|חוק שני]]"}
    cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    titles = law_get._get_main_page_titles()

    assert "חוק ראשון" in titles
    assert "חוק שני" in titles


def test_get_main_page_titles_fetch_and_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "page_247.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(law_get, "_get_cache_path", lambda: cache_path)
    monkeypatch.setattr(law_get, "_save_main_page_cache", lambda data: captured.update(data))

    def fake_fetch(page_id=None, title=None):
        return {
            "query": {
                "pages": {
                    str(MAIN_PAGE_ID): {
                        "revisions": [
                            {"slots": {"main": {"*": "[[Law A]]"}}}
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(law_get, "_fetch_law_wikitext", fake_fetch)

    titles = law_get._get_main_page_titles()

    assert "law a" in titles
    assert captured["titles"] == ["Law A"]


def test_get_main_page_titles_fetch_failure(monkeypatch, tmp_path):
    cache_path = tmp_path / "page_247.json"
    monkeypatch.setattr(law_get, "_get_cache_path", lambda: cache_path)
    monkeypatch.setattr(law_get, "_fetch_law_wikitext", lambda page_id=None, title=None: {"query": {"pages": {}}})

    with pytest.raises(RuntimeError):
        law_get._get_main_page_titles()


def test_wide_law_search_filters(monkeypatch):
    class DummyClient:
        def search(self, query, limit=10, namespace=None):
            return {
                "query": {
                    "search": [
                        {"title": "Law One", "pageid": 1},
                        {"title": "Law Two", "pageid": 2},
                        {"title": "Main Page", "pageid": MAIN_PAGE_ID},
                        {"title": "Other", "pageid": 3},
                    ]
                }
            }

    monkeypatch.setattr(law_get, "MediaWikiClient", lambda: DummyClient())
    monkeypatch.setattr(law_get, "_get_main_page_titles", lambda: {"law one", "law two"})

    laws = law_get.wide_law_search("Law")

    assert {item["title"] for item in laws} == {"Law One", "Law Two"}


def test_wide_law_search_main_titles_error(monkeypatch):
    class DummyClient:
        def search(self, query, limit=10, namespace=None):
            return {"query": {"search": []}}

    monkeypatch.setattr(law_get, "MediaWikiClient", lambda: DummyClient())
    monkeypatch.setattr(law_get, "_get_main_page_titles", lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    with pytest.raises(RuntimeError):
        law_get.wide_law_search("Law")
