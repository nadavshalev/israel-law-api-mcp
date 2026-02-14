#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000/api}"
PAGE_ID="${PAGE_ID:-279238}"
PHRASE="${PHRASE:-איסור עישון}"
LAW_TITLE="${LAW_TITLE:-חוק למניעת העישון במקומות ציבוריים והחשיפה לעישון}"
SECTIONS_JSON='["1","2","3"]'

echo "Health:"
curl -s "${BASE_URL}/health" | python3 -m json.tool

echo "\nSearch:"
curl -s "${BASE_URL}/laws/search?phrase=$(python3 -c "import urllib.parse,os;print(urllib.parse.quote(os.environ.get('PHRASE','')))")&limit=5" \
  | python3 -m json.tool

echo "\nSections:"
curl -s "${BASE_URL}/laws/${PAGE_ID}/sections" | python3 -m json.tool

echo "\nSection text:"
curl -s -X POST "${BASE_URL}/laws/${PAGE_ID}/sections/text" \
  -H "Content-Type: application/json" \
  -d "{\"sections\": ${SECTIONS_JSON}}" \
  | python3 -m json.tool

echo "\nCitations:"
curl -s -X POST "${BASE_URL}/citations" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"${LAW_TITLE}\", \"sections\": ${SECTIONS_JSON}}" \
  | python3 -m json.tool
