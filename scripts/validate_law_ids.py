#!/usr/bin/env python3
"""
Phase 0 validation: verify that {{ח:מאגר|ID}} extraction produces
real law IDs that exist in the Knesset OData API.

Run once manually before building the full law map:
    python3 scripts/validate_law_ids.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 — triggers load_dotenv()

from data.law_get import MAAGAR_PATTERN, _extract_wikitext, _fetch_law_wikitext

KNESSET_LAW_URL = "https://knesset.gov.il/OdataV4/ParliamentInfo/KNS_IsraelLaw"

# Known laws with their expected law_ids (page_id, title, expected_law_id)
KNOWN_LAWS = [
    (183646, "חוק העונשין", 2000479),
    (1219,   "חוק-יסוד: כבוד האדם וחירותו", 2000046),
    (378333, "חוק התכנית לסיוע כלכלי (קורונה)", 2143999),
]


def fetch_law_id_from_wikisource(page_id: int) -> int | None:
    payload = _fetch_law_wikitext(page_id=page_id)
    wikitext = _extract_wikitext(payload)
    match = MAAGAR_PATTERN.search(wikitext)
    return int(match.group(1)) if match else None


def verify_law_id_in_knesset(law_id: int) -> bool:
    url = f"{KNESSET_LAW_URL}?$filter=Id eq {law_id}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return len(data.get("value", [])) > 0


def main() -> None:
    ok = 0
    fail = 0

    for page_id, title, expected_law_id in KNOWN_LAWS:
        print(f"\n--- {title} (page_id={page_id}) ---")

        extracted = fetch_law_id_from_wikisource(page_id)
        if extracted is None:
            print(f"  FAIL: no {{{{ח:מאגר}}}} template found in wikitext")
            fail += 1
            continue
        print(f"  Extracted law_id: {extracted}")

        if extracted != expected_law_id:
            print(f"  WARN: expected {expected_law_id}, got {extracted}")

        exists = verify_law_id_in_knesset(extracted)
        if exists:
            print(f"  OK: law_id={extracted} confirmed in Knesset API")
            ok += 1
        else:
            print(f"  FAIL: law_id={extracted} not found in Knesset API")
            fail += 1

    print(f"\nResult: {ok} passed, {fail} failed")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
