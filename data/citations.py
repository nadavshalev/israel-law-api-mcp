from __future__ import annotations

from urllib.parse import quote
from typing import Any, Dict, List



def _build_law_url(title: str) -> str:
    encoded = quote(title, safe="")
    return f"https://he.wikisource.org/wiki/{encoded}"


def _build_section_anchor(number: str) -> str:
    clean_number = "".join(str(number).split()).strip(".")
    anchor = f"סעיף_{clean_number}"
    return quote(anchor, safe="")


def build_citations_url(title: str, numbers: list) -> list:
    anchors = [_build_section_anchor(n) for n in numbers]
    base_url = _build_law_url(title)
    return [f"{base_url}#{anchor}" for anchor in anchors]
