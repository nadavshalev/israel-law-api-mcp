#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env()


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000/api")
PAGE_ID = os.getenv("PAGE_ID", "279238")
PHRASE = os.getenv("PHRASE", "איסור עישון")
LAW_TITLE = os.getenv("LAW_TITLE", "חוק למניעת העישון במקומות ציבוריים והחשיפה לעישון")
SECTIONS = [item.strip() for item in os.getenv("SECTIONS", "1,2,3").split(",") if item.strip()]
FULL_TEXT = os.getenv("FULL_TEXT", "false").lower() in {"1", "true", "yes", "on"}
LIMIT = int(os.getenv("LIMIT", "5"))


def section(title: str) -> None:
    print(f"\n== {title} ==")


def pretty(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def get(url: str, **kwargs) -> requests.Response:
    return requests.get(url, timeout=20, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return requests.post(url, timeout=20, **kwargs)


def main() -> None:
    if not SECTIONS:
        print("No sections provided", file=sys.stderr)
        sys.exit(1)

    # Health
    section("Health")
    resp = get(f"{BASE_URL}/health")
    print(f"GET /health -> {resp.status_code}")
    resp.raise_for_status()
    print(pretty(resp.json()))

    # Search
    section("Search")
    params = {"phrase": PHRASE, "limit": LIMIT}
    resp = get(f"{BASE_URL}/laws/search", params=params)
    print(f"GET /laws/search -> {resp.status_code}")
    resp.raise_for_status()
    search_data = resp.json()
    print(pretty(search_data))

    # Use returned page_id if available
    page_id = PAGE_ID
    results = search_data.get("results", [])
    if results and isinstance(results[0], dict):
        page_id = str(results[0].get("page_id", PAGE_ID))

    # Sections list
    section("Sections")
    resp = get(f"{BASE_URL}/laws/{quote(str(page_id))}/sections")
    print(f"GET /laws/{page_id}/sections -> {resp.status_code}")
    resp.raise_for_status()
    sections_data = resp.json()
    print(pretty(sections_data))

    # Section text
    section("Section text")
    payload = {"sections": SECTIONS, "full": FULL_TEXT}
    resp = post(f"{BASE_URL}/laws/{quote(str(page_id))}/sections/text", json=payload)
    print(f"POST /laws/{page_id}/sections/text -> {resp.status_code}")
    resp.raise_for_status()
    print(pretty(resp.json()))

    # Citations
    section("Citations")
    payload = {"title": LAW_TITLE, "sections": SECTIONS}
    resp = post(f"{BASE_URL}/citations", json=payload)
    print(f"POST /citations -> {resp.status_code}")
    resp.raise_for_status()
    print(pretty(resp.json()))


if __name__ == "__main__":
    main()
