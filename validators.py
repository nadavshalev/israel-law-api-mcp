from __future__ import annotations

from typing import List

import config


def validate_phrase(phrase: str) -> str:
    phrase = phrase.strip()
    if not phrase:
        raise ValueError("phrase must not be empty")
    if len(phrase) > config.MAX_SEARCH_PHRASE_LEN:
        raise ValueError("phrase is too long")
    return phrase


def validate_limit(limit: int) -> int:
    return min(limit, config.MAX_SEARCH_LIMIT)


def normalize_sections(sections: List[str]) -> List[str]:
    normalized = [str(s).strip() for s in sections]
    return [s for s in normalized if s]


def validate_sections(sections: List[str]) -> List[str]:
    sections = normalize_sections(sections)
    if not sections:
        raise ValueError("sections must not be empty")
    if len(sections) > config.MAX_SECTIONS_PER_REQUEST:
        raise ValueError("too many sections requested")
    return sections


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValueError("title must not be empty")
    return title


def truncate_text(text: str, full: bool) -> str:
    if full or config.MAX_SECTION_TEXT_CHARS <= 0:
        return text
    if len(text) <= config.MAX_SECTION_TEXT_CHARS:
        return text
    return text[:config.MAX_SECTION_TEXT_CHARS]
