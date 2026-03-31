from __future__ import annotations

from data.secondary_law_matcher import match_id, enrich_with_secondary_ids


def _make_db(entries: list[dict]) -> tuple[dict, dict]:
    """Build (db_full, db_year) from raw test entries."""
    from collections import defaultdict
    from data.secondary_law_matcher import _strip_full, _strip_year_only

    db_full: dict = defaultdict(list)
    db_year: dict = defaultdict(list)
    for e in entries:
        entry = {"id": e["id"], "year": e.get("year"), "name": e["name"]}
        db_full[_strip_full(e["name"])].append(entry)
        db_year[_strip_year_only(e["name"])].append(entry)
    return db_full, db_year


def test_exact_single_match():
    db_full, db_year = _make_db([
        {"id": 2126983, "year": 1997, "name": 'תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות), התשנ"ז-1997'},
    ])
    assert match_id("תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות)", db_full, db_year) == 2126983


def test_prefers_base_law_over_amendment():
    db_full, db_year = _make_db([
        {"id": 2128702, "year": 2000, "name": 'תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות) (תיקון), התש"ס-2000'},
        {"id": 2126983, "year": 1997, "name": 'תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות), התשנ"ז-1997'},
    ])
    # Should pick the base law (no תיקון), not the amendment
    assert match_id("תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות)", db_full, db_year) == 2126983


def test_year_disambiguates_multiple_base_laws():
    db_full, db_year = _make_db([
        {"id": 2100001, "year": 2005, "name": "תקנות הדוגמא (כללים), התשס\"ה-2005"},
        {"id": 2100002, "year": 2015, "name": "תקנות הדוגמא (כללים), התשע\"ה-2015"},
    ])
    assert match_id("תקנות הדוגמא (כללים), התשע\"ה-2015", db_full, db_year) == 2100002
    assert match_id("תקנות הדוגמא (כללים), התשס\"ה-2005", db_full, db_year) == 2100001


def test_strips_hatzaat_prefix():
    db_full, db_year = _make_db([
        {"id": 2208350, "year": 2022, "name": 'הצעת תקנות הגז הפחמימני המעובה (אמות מידה לשירות), התשפ"ב-2022'},
    ])
    assert match_id("תקנות הגז הפחמימני המעובה (אמות מידה לשירות)", db_full, db_year) == 2208350


def test_no_match_returns_none():
    db_full, db_year = _make_db([
        {"id": 2100001, "year": 2005, "name": "תקנות אחרות (כללים), התשס\"ה-2005"},
    ])
    assert match_id("תקנות שאין להן התאמה", db_full, db_year) is None


def test_enrich_with_secondary_ids(monkeypatch):
    db_full, db_year = _make_db([
        {"id": 2126983, "year": 1997, "name": 'תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות), התשנ"ז-1997'},
        {"id": 2135415, "year": 2010, "name": 'צו הגז (בטיחות ורישוי) (גז טבעי דחוס), התש"ע-2010'},
    ])
    import data.secondary_law_matcher as mod
    monkeypatch.setattr(mod, "build_secondary_lookup", lambda: (db_full, db_year))

    laws = [
        {"title": "תקנות בתי קברות צבאיים (כללים לכיתוב על מצבות)", "page_id": 1},
        {"title": 'צו הגז (בטיחות ורישוי) (גז טבעי דחוס)', "page_id": 2},
        {"title": "תקנות שאין להן התאמה", "page_id": 3},
        {"title": "חוק העונשין", "page_id": 4, "law_id": 2000479},  # already has law_id
    ]
    count = enrich_with_secondary_ids(laws)
    assert count == 2
    assert laws[0]["law_id"] == 2126983
    assert laws[1]["law_id"] == 2135415
    assert "law_id" not in laws[2]
    assert laws[3]["law_id"] == 2000479  # unchanged
