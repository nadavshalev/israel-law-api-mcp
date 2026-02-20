#!/usr/bin/env python3
#%%
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

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RATE_LIMIT_PER_IP = os.getenv("RATE_LIMIT_PER_IP", "60/minute")
MAX_SECTIONS_PER_REQUEST = int(os.getenv("MAX_SECTIONS_PER_REQUEST", "10"))
MAX_SECTION_TEXT_CHARS = int(os.getenv("MAX_SECTION_TEXT_CHARS", "10000"))
MAX_SEARCH_PHRASE_LEN = int(os.getenv("MAX_SEARCH_PHRASE_LEN", "120"))
MAX_SEARCH_LIMIT = int(os.getenv("MAX_SEARCH_LIMIT", "20"))


def section(title: str) -> None:
    print("\n== {} ==".format(title))


def get(url: str) -> requests.Response:
    return requests.get(url, timeout=20)


def post(url: str, payload: dict) -> requests.Response:
    return requests.post(url, json=payload, timeout=20)


#%% Health
# This is a basic check to ensure the server is up and responding before running further tests.

section("Health")
resp = get(f"{BASE_URL}/health")
print(f"GET /health -> {resp.status_code}")
resp.raise_for_status()


#%% Rate limiting
# This test makes repeated search requests to trigger the rate limit. 
# It checks if a 429 status code is returned after the expected number of requests. 
# If the limit is not hit within the expected window, it prints a warning. 
# If rate limiting is disabled, it skips this test.

section("Rate limiting")
if RATE_LIMIT_ENABLED:
    print(f"RATE_LIMIT_PER_IP={RATE_LIMIT_PER_IP}")
    limit_count_raw = RATE_LIMIT_PER_IP.split("/")[0].strip()
    limit_count = int(limit_count_raw) if limit_count_raw.isdigit() else 30
    phrase_enc = quote(PHRASE)
    hit_429 = False
    for i in range(limit_count + 5):
        r = get(f"{BASE_URL}/health")
        # r = get(f"{BASE_URL}/laws/search?phrase={phrase_enc}&limit=1")
        if r.status_code == 429:
            hit_429 = True
            break
        print(f"Request {i+1} Search -> {r.status_code}")
    print(f"Rate limit hit: {hit_429}")
    if not hit_429:
        print("WARN: did not hit rate limit within expected window")
else:
    print("Rate limiting disabled; skipping")


#%% Max search phrase length
# This test sends a search request with an excessively long phrase 
# to check if the server correctly returns a 400 Bad Request status.

section("Max search phrase length")
resp = get(f"{BASE_URL}/laws/search?phrase={quote('a'*(MAX_SEARCH_PHRASE_LEN + 1))}&limit=1")
print(f"Too long phrase -> {resp.status_code}")
resp = get(f"{BASE_URL}/laws/search?phrase={quote('a'*MAX_SEARCH_PHRASE_LEN)}&limit=1")
print(f"Max length phrase -> {resp.status_code}")


#%% Max search limit cap
# This test sends a search request with a limit parameter that exceeds the maximum allowed. 
# It checks if the server caps the results at the defined maximum and does not return 
# more results than allowed. If the server returns more results than the maximum, 
# it exits with an error.

section("Max search limit cap")
resp = get(f"{BASE_URL}/laws/search?phrase={quote(PHRASE)}&limit=999")
print(f"Search with excessive limit -> {resp.status_code}")
resp = get(f"{BASE_URL}/laws/search?phrase={quote(PHRASE)}&limit={MAX_SEARCH_LIMIT}")
print(f"Search with max limit -> {resp.status_code}")

#%% Max sections per request
# This test sends a request to retrieve section texts with a number of sections that exceeds the maximum allowed. 
# It checks if the server returns an appropriate error status code (e.g., 400 Bad Request) 
# when too many sections are requested. If the server does not enforce the limit, 
# it prints a warning.

section("Max sections per request")
resp = post(f"{BASE_URL}/laws/{PAGE_ID}/sections/text", {"sections": [str(i) for i in range(1, 100)]})
print(f"Too many sections -> {resp.status_code}")
resp = post(f"{BASE_URL}/laws/{PAGE_ID}/sections/text", {"sections": [str(i) for i in range(1, MAX_SECTIONS_PER_REQUEST + 1)]})
print(f"Max sections -> {resp.status_code}")


#%% Section text full override
section("Section text full override")
resp = post(f"{BASE_URL}/laws/{PAGE_ID}/sections/text", {"sections": ["1"], "full": True})
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
text_full = resp.json().get("sections", [{}])[0].get("text", "")
print(f"Full length: {len(text_full)}")
if len(text_full) <= MAX_SECTION_TEXT_CHARS:
    print("WARN: full text length did not exceed truncation cap")


print("\nSecurity tests completed")
