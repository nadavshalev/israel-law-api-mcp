from __future__ import annotations

import re
from typing import Any, Dict, List
from data.wiki_client import MediaWikiClient


SECTION_PATTERN = re.compile(r"\{\{ח:סעיף\|(.*?)\|(.*?)(?:\|.*?)?\}\}")
TEMPLATE_PATTERN = re.compile(r"\{\{ח:[^}]+\}\}")


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


def _extract_wikitext(payload: Dict[str, Any]) -> str:
    pages = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        revisions = page.get("revisions", [])
        if not revisions:
            continue
        revision = revisions[0]
        slots = revision.get("slots", {})
        main_slot = slots.get("main", {})
        content = main_slot.get("*", "")
        if content:
            return content
    return ""


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
        section_id = f"{number}:{title}"
        sections.append(
            {
                "section_id": section_id,
                "number": number,
                "title": title,
                "text": text,
            }
        )
    return sections


def wide_law_search(phrase: str, limit: int = 10) -> List[Dict[str, str | int]]:
    ''' Search for laws in the Hebrew Wikipedia using a phrase. 
    The search is limited to the main namespace and looks for the phrase in the title, 
    along with keywords indicating it's a law (חוק, צו, תקנות). 
    Returns a list of dictionaries containing the title and page ID of each matching law.
    '''
    query = f"{phrase} intitle:(חוק OR צו OR תקנות)"
    client = MediaWikiClient()
    payload = client.search(query, limit=limit, namespace=0)
    results = payload.get("query", {}).get("search", [])
    laws: List[Dict[str, str | int]] = []
    for item in results:
        title = item.get("title")
        page_id = item.get("pageid")
        if (title and page_id is not None) and page_id != 247: # Exclude also the main page
            laws.append({"title": title, "page_id": page_id})
    return laws

def get_law_sections_text(page_id: int, sections_num: list[str]) -> List[Dict[str, str]]:
    ''' Retrieve the text of specific sections from a law page given its page ID and a list of section numbers.
    The function fetches the wikitext of the law page, extracts the sections, 
    and returns a list of dictionaries containing the section number, title, and text for each requested section.
    '''
    fetched_data = _fetch_law_wikitext(page_id=page_id)
    wikitext = _extract_wikitext(fetched_data)
    all_sections = _parse_sections_with_text(wikitext)
    sections = [section for section in all_sections if section["number"] in sections_num]
    return sections

def get_law_sections_titles(page_id: int) -> List[Dict[str, str]]:
    ''' Retrieve the titles of all sections from a law page given its page ID.
    The function fetches the wikitext of the law page, extracts the sections, 
    and returns a list of dictionaries containing the section ID and title for each section.
    '''
    fetched_data = _fetch_law_wikitext(page_id=page_id)
    wikitext = _extract_wikitext(fetched_data)
    all_sections = _parse_sections_with_text(wikitext)
    sections = [{"number": section["number"], "title": section["title"]} for section in all_sections]
    return sections
