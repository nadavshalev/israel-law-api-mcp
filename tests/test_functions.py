from __future__ import annotations

from data.citations import build_citations_url
from data.law_get import _clean_section_text, _parse_sections_with_text


def test_build_citations_url():
    urls = build_citations_url("חוק לדוגמה", ["1", "2"])
    assert len(urls) == 2
    assert urls[0].startswith("https://he.wikisource.org/wiki/")
    assert "#" in urls[0]


def test_parse_sections_with_text_basic():
    wikitext = """
{{ח:סעיף|1|כותרת}}
{{ח:ת}} תוכן ראשון.

{{ח:סעיף|2|כותרת שנייה}}
{{ח:ת}} תוכן שני.
"""
    sections = _parse_sections_with_text(wikitext)
    assert len(sections) == 2
    assert sections[0]["number"] == "1"
    assert sections[0]["title"] == "כותרת"
    assert "תוכן ראשון" in sections[0]["text"]


def test_clean_section_text():
    raw = """
{{ח:תיבה|מקור|מקור|http://example.com}}
'''מודגש'''
{{ח:הערה|[הערה]}}
"""
    cleaned = _clean_section_text(raw)
    assert "מקור" in cleaned
    assert "'''" not in cleaned
    assert "הערה" in cleaned
