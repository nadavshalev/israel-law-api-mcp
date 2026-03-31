from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional


def _strip_year_only(name: str) -> str:
    """Strip year suffix only — preserves (תיקון) so we can identify base laws."""
    name = re.sub(r"^הצעת\s+", "", name)
    name = re.sub(r",?\s*ה?תש[א-ת\"״׳]+[\s\-–]*\d{0,4}.*$", "", name)
    name = name.replace("–", "-").replace("—", "-").replace("׳", "'").replace("״", '"')
    return re.sub(r"\s+", " ", name).strip().lower()


def _strip_full(name: str) -> str:
    """Strip year + amendments + temporary provisions."""
    name = re.sub(r"^הצעת\s+", "", name)
    name = re.sub(r",?\s*\(תיקון.*$", "", name)
    name = re.sub(r",?\s*\(הוראת שעה.*$", "", name)
    name = re.sub(r",?\s*ה?תש[א-ת\"״׳]+[\s\-–]*\d{0,4}.*$", "", name)
    name = name.replace("–", "-").replace("—", "-").replace("׳", "'").replace("״", '"')
    return re.sub(r"\s+", " ", name).strip().lower()


def _extract_year(title: str) -> Optional[int]:
    m = re.search(r"\b(19\d\d|20\d\d)\b", title)
    return int(m.group(1)) if m else None


def build_secondary_lookup() -> tuple[dict, dict]:
    """
    Load secondary_law_raw from DB and return two lookup dicts:
      db_full:  strip_full(name)      → list of {id, year, name}
      db_year:  strip_year_only(name) → list of {id, year, name}  (base laws only)
    Returns empty dicts if DB is unavailable.
    """
    try:
        from data.db import connect_readonly
        conn = connect_readonly()
    except Exception as e:
        print(f"  Secondary law matcher: DB unavailable ({e})")
        return {}, {}

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, publicationdate FROM secondary_law_raw")
        rows = cur.fetchall()
    finally:
        conn.close()

    db_full: Dict[str, list] = defaultdict(list)
    db_year: Dict[str, list] = defaultdict(list)

    for r in rows:
        pub_year = None
        if r["publicationdate"]:
            m = re.search(r"(\d{4})", str(r["publicationdate"]))
            pub_year = int(m.group(1)) if m else None
        entry = {"id": r["id"], "year": pub_year, "name": r["name"]}
        db_full[_strip_full(r["name"])].append(entry)
        db_year[_strip_year_only(r["name"])].append(entry)

    return db_full, db_year


def match_id(title: str, db_full: dict, db_year: dict) -> Optional[int]:
    """
    Return the best-matching secondary_law_raw id for a Wikisource title, or None.

    Strategy:
    1. Exact match after stripping year + amendments.
    2. Among candidates, prefer base-law entries (no amendment suffix).
    3. Among remaining ties, prefer the year-matching entry; fall back to lowest id.
    """
    norm = _strip_full(title)
    candidates = db_full.get(norm)
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]["id"]

    # Prefer base-law entries (year-only strip yields the same key)
    base_candidates = db_year.get(norm, [])
    pool = base_candidates if base_candidates else candidates

    wiki_year = _extract_year(title)
    if wiki_year:
        year_match = [c for c in pool if c["year"] and abs(wiki_year - c["year"]) <= 1]
        if len(year_match) == 1:
            return year_match[0]["id"]
        if year_match:
            pool = year_match

    return min(pool, key=lambda c: c["id"])["id"]


def enrich_with_secondary_ids(laws: List[dict]) -> int:
    """
    For each law entry without a law_id, attempt to match against secondary_law_raw.
    Modifies the list in-place.  Returns the number of laws enriched.
    """
    db_full, db_year = build_secondary_lookup()
    if not db_full:
        return 0

    enriched = 0
    for law in laws:
        if law.get("law_id"):
            continue
        matched_id = match_id(law["title"], db_full, db_year)
        if matched_id is not None:
            law["law_id"] = matched_id
            enriched += 1

    return enriched
