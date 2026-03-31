from __future__ import annotations

import asyncio
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import config
from data.wiki_client import MediaWikiClient


SECTION_PATTERN = re.compile(r"\{\{ח:סעיף\|(.*?)\|(.*?)(?:\|.*?)?\}\}")
TEMPLATE_PATTERN = re.compile(r"\{\{ח:[^}]+\}\}")
LINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")
MAAGAR_PATTERN = re.compile(r"\{\{ח:מאגר\|(\d+)\}\}")
MAIN_PAGE_ID = 247


# ---------------------------------------------------------------------------
# In-memory law map — populated from cache at startup or after rebuild
# ---------------------------------------------------------------------------

_law_map: list[dict] = []
_law_id_to_page_id: dict[int, int] = {}
_page_id_to_law_id: dict[int, int] = {}
_page_id_set: set[int] = set()
_normalized_titles: set[str] = set()


def _load_law_map_into_memory(laws: list[dict]) -> None:
    global _law_map, _law_id_to_page_id, _page_id_to_law_id, _page_id_set, _normalized_titles
    _law_map = laws
    _law_id_to_page_id = {}
    _page_id_to_law_id = {}
    _page_id_set = set()
    _normalized_titles = set()
    for law in laws:
        page_id = law.get("page_id")
        law_id = law.get("law_id")
        title = law.get("title", "")
        if page_id:
            _page_id_set.add(page_id)
            _normalized_titles.add(_normalize_title(title))
            if law_id:
                _law_id_to_page_id[law_id] = page_id
                _page_id_to_law_id[page_id] = law_id


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _get_cache_path() -> Path:
    cache_dir = Path(__file__).resolve().parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "law_map.json"


def _load_law_map_cache() -> Dict[str, Any] | None:
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _save_law_map_cache(laws: list[dict]) -> None:
    cache_path = _get_cache_path()
    data = {"timestamp": datetime.now().isoformat(), "laws": laws}
    try:
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Wikitext helpers
# ---------------------------------------------------------------------------

def _fetch_law_wikitext(title: str | None = None, page_id: int | None = None) -> Dict[str, Any]:
    if title is None and page_id is None:
        raise ValueError("title or page_id must be provided")

    params: Dict[str, Any] = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    }
    if title is not None:
        params["titles"] = title
    if page_id is not None:
        params["pageids"] = page_id

    client = MediaWikiClient()
    return client.get(params)


def _extract_wikitext(payload: Dict[str, Any]) -> str:
    pages = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        revisions = page.get("revisions", [])
        if not revisions:
            continue
        content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
        if content:
            return content
    return ""


def _extract_all_from_batch(payload: Dict[str, Any]) -> list[tuple[str, int, str]]:
    """Return (title, page_id, wikitext) for each valid page in a batch response."""
    results = []
    for page in payload.get("query", {}).get("pages", {}).values():
        page_id = page.get("pageid", -1)
        title = page.get("title", "")
        if page_id < 0 or not title:
            continue
        revisions = page.get("revisions", [])
        wikitext = ""
        if revisions:
            wikitext = revisions[0].get("slots", {}).get("main", {}).get("*", "")
        results.append((title, page_id, wikitext))
    return results


def _extract_links(wikitext: str) -> Set[str]:
    titles: Set[str] = set()
    for match in LINK_PATTERN.finditer(wikitext):
        title = match.group(1)
        if "|" in title:
            title = title.split("|", 1)[0]
        cleaned = title.replace("_", " ").strip()
        if cleaned:
            titles.add(cleaned)
    return titles


def _normalize_title(title: str) -> str:
    return " ".join(title.replace("_", " ").split()).strip().lower()


# ---------------------------------------------------------------------------
# Title filtering (used by wide_law_search)
# ---------------------------------------------------------------------------

def _get_main_page_titles() -> Set[str]:
    """Return the set of normalized law titles for search result filtering."""
    if _normalized_titles:
        return _normalized_titles

    # Try loading from law_map.json cache
    cached = _load_law_map_cache()
    if cached and "laws" in cached and "timestamp" in cached:
        age = datetime.now() - datetime.fromisoformat(cached["timestamp"])
        if age.days < config.LAW_MAP_TTL_DAYS:
            _load_law_map_into_memory(cached["laws"])
            if _normalized_titles:
                return _normalized_titles

    # Fallback: fetch page_247 synchronously (first startup before map is built)
    print("Law map not ready — fetching page_247 for title filtering...")
    payload = _fetch_law_wikitext(page_id=MAIN_PAGE_ID)
    wikitext = _extract_wikitext(payload)
    if not wikitext:
        raise RuntimeError("Failed to fetch main page wikitext")
    return {_normalize_title(t) for t in _extract_links(wikitext)}


# ---------------------------------------------------------------------------
# Lookup helpers (public)
# ---------------------------------------------------------------------------

def get_page_id_from_law_id(law_id: int) -> int | None:
    return _law_id_to_page_id.get(law_id)


def get_law_id_from_page_id(page_id: int) -> int | None:
    return _page_id_to_law_id.get(page_id)


def resolve_id_to_page_id(id: int) -> int | None:
    """Resolve either a law_id or a page_id to a page_id. Returns None if unknown."""
    page_id = _law_id_to_page_id.get(id)
    if page_id is not None:
        return page_id
    if id in _page_id_set:
        return id
    return None


# ---------------------------------------------------------------------------
# Async background map rebuild
# ---------------------------------------------------------------------------

async def maybe_rebuild_law_map() -> None:
    """Check cache staleness and rebuild the law map if needed."""
    cached = _load_law_map_cache()
    if cached and "timestamp" in cached and "laws" in cached:
        age = datetime.now() - datetime.fromisoformat(cached["timestamp"])
        if age.days < config.LAW_MAP_TTL_DAYS:
            # Cache is fresh — just make sure in-memory map is loaded
            print(f"Law map cache is fresh (age {age.days} days) — loading into memory")
            if not _normalized_titles:
                _load_law_map_into_memory(cached["laws"])
            return
    print("Law map cache is stale or missing — rebuilding...")
    await _rebuild_law_map()


async def _rebuild_law_map() -> None:
    """Fetch page_247, diff against existing cache, batch-fetch new laws only."""
    print("Building law map...")

    # 1. Fetch page_247 to get the current full title set
    payload = await asyncio.to_thread(_fetch_law_wikitext, None, MAIN_PAGE_ID)
    wikitext = _extract_wikitext(payload)
    if not wikitext:
        print("Law map build failed: could not fetch page_247")
        return
    current_titles: Set[str] = _extract_links(wikitext)

    # 2. Load existing cache to compute delta
    cached = _load_law_map_cache()
    existing_laws: list[dict] = cached.get("laws", []) if cached else []
    existing_by_title: dict[str, dict] = {law["title"]: law for law in existing_laws}
    cached_titles: Set[str] = set(existing_by_title.keys())

    new_titles = current_titles - cached_titles
    removed_titles = cached_titles - current_titles
    print(f"  Titles: {len(current_titles)} total, {len(new_titles)} new, {len(removed_titles)} removed")

    # 3. Keep unchanged entries
    kept_laws = [law for law in existing_laws if law["title"] not in removed_titles]

    # 4. Batch-fetch wikitext only for new titles
    new_laws: list[dict] = []
    if new_titles:
        client = MediaWikiClient()
        batch_size = config.LAW_MAP_BATCH_SIZE
        new_titles_list = list(new_titles)
        total = len(new_titles_list)
        batches = [new_titles_list[i:i + batch_size] for i in range(0, total, batch_size)]
        print(f"  Fetching {total} new laws in {len(batches)} batches (concurrency={config.LAW_MAP_CONCURRENCY})...")

        semaphore = asyncio.Semaphore(config.LAW_MAP_CONCURRENCY)

        async def _fetch_batch(batch: list[str]) -> list[tuple[str, int, str]]:
            async with semaphore:
                payload = await asyncio.to_thread(client.get_pages_batch, batch)
                return _extract_all_from_batch(payload)

        batch_results = await asyncio.gather(*[_fetch_batch(b) for b in batches])
        for entries in batch_results:
            for title, page_id, wiki in entries:
                match = MAAGAR_PATTERN.search(wiki)
                entry: dict = {"title": title, "page_id": page_id}
                if match:
                    entry["law_id"] = int(match.group(1))
                new_laws.append(entry)

    # 5. Enrich only new laws with secondary IDs — kept laws are already settled
    if new_laws:
        try:
            from data.secondary_law_matcher import enrich_with_secondary_ids
            enriched = enrich_with_secondary_ids(new_laws)
            print(f"  Secondary law IDs matched: {enriched}")
        except Exception as e:
            print(f"  Secondary law ID enrichment skipped: {e}")

    # 6. Merge, save, reload
    all_laws = kept_laws + new_laws
    _save_law_map_cache(all_laws)
    _load_law_map_into_memory(all_laws)
    print(
        f"Law map ready: {len(all_laws)} laws "
        f"({len(new_laws)} added, {len(removed_titles)} removed)"
    )


# ---------------------------------------------------------------------------
# Section text cleaning
# ---------------------------------------------------------------------------

def _clean_section_text(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\{\{ח:תתת\|\((.)\)\}\}", r"(\1)", cleaned)
    cleaned = re.sub(r"\{\{ח:תת\|\((.)\)\}\}", r"(\1)", cleaned)
    cleaned = re.sub(r"\{\{ח:ת(?:\|.*?)?\}\}", "", cleaned)
    cleaned = re.sub(r"\{\{ח:(?:חיצוני|פנימי)\|.*?\|(.*?)\}\}", r"\1", cleaned)
    cleaned = re.sub(r"\{\{ח:תיבה\|.*?\|(.*?)\|.*?\}\}", r"[\1]", cleaned)
    cleaned = re.sub(r"\{\{ח:הערה\|\[(.*?)\]\}\}", r" (\1)", cleaned)
    cleaned = TEMPLATE_PATTERN.sub("", cleaned)
    cleaned = cleaned.replace("'''", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _parse_sections_with_text(wikitext: str) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []
    matches = list(SECTION_PATTERN.finditer(wikitext))
    for index, match in enumerate(matches):
        number = match.group(1).strip()
        title = match.group(2).strip()
        if not number or not title:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(wikitext)
        text = _clean_section_text(wikitext[start:end])
        sections.append({
            "section_id": f"{number}:{title}",
            "number": number,
            "title": title,
            "text": text,
        })
    return sections


# ---------------------------------------------------------------------------
# Public data functions
# ---------------------------------------------------------------------------

def wide_law_search(phrase: str, limit: int = 10) -> List[Dict[str, str | int]]:
    """Search for laws by phrase. Returns list of {title, page_id, law_id?}."""
    query = f"{phrase} intitle:(חוק OR צו OR תקנות)"
    client = MediaWikiClient()
    payload = client.search(query, limit=limit, namespace=0)
    results = payload.get("query", {}).get("search", [])

    main_titles = _get_main_page_titles()
    if not main_titles:
        raise RuntimeError("Main page titles unavailable")

    laws: List[Dict[str, str | int]] = []
    for item in results:
        title = item.get("title")
        page_id = item.get("pageid")
        if not (title and page_id is not None) or \
                page_id == MAIN_PAGE_ID or \
                _normalize_title(title) not in main_titles:
            continue
        entry: Dict[str, str | int] = {"title": title, "page_id": page_id}
        law_id = get_law_id_from_page_id(page_id)
        if law_id is not None:
            entry["law_id"] = law_id
        laws.append(entry)
    return laws


def get_law_sections_text(page_id: int, sections_num: list[str]) -> List[Dict[str, str]]:
    """Retrieve the text of specific sections from a law page."""
    fetched_data = _fetch_law_wikitext(page_id=page_id)
    wikitext = _extract_wikitext(fetched_data)
    all_sections = _parse_sections_with_text(wikitext)
    return [s for s in all_sections if s["number"] in sections_num]


def get_law_sections_titles(page_id: int) -> List[Dict[str, str]]:
    """Retrieve the section numbers and titles from a law page."""
    fetched_data = _fetch_law_wikitext(page_id=page_id)
    wikitext = _extract_wikitext(fetched_data)
    all_sections = _parse_sections_with_text(wikitext)
    return [{"number": s["number"], "title": s["title"]} for s in all_sections]
