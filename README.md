# Israel Law Data API & MCP

REST and MCP services for searching Israeli laws on Hebrew Wikisource, listing sections, fetching section text, and building citation URLs.

---

## Data Source & Licensing

* **Source:** This project is powered by the incredible work of the **[Open Israel Law Book (ספר החוקים הפתוח)](https://he.wikisource.org/wiki/%D7%A1%D7%A4%D7%A8_%D7%94%D7%97%D7%95%D7%A7%D7%99%D7%9D_%D7%94%D7%A4%D7%AA%D7%95%D7%97)** on Hebrew Wikisource.
* **Data License:** Content retrieved from Wikisource is provided under the **[Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/)** license.
* **Code License:** This software (the API and MCP implementation) is released under the **MIT License**.

## Disclaimer

**This is an unofficial, community-driven tool.** It was built to improve accessibility to public legal data, but it is not an official government service.

1.  **Not Legal Advice:** The information provided by this API is for informational purposes only and does not constitute legal advice.
2.  **No Guarantee of Accuracy:** While we strive to provide accurate data, legal texts may be incomplete, unvetted, or outdated.

---
## Run locally

```bash
uvicorn api:app --reload
```

REST base URL: `http://127.0.0.1:8000/api`

## REST endpoints

- `GET /api/health`
- `GET /api/laws/search?phrase=...&limit=10`
- `GET /api/laws/{page_id}/sections`
- `POST /api/laws/{page_id}/sections/text`
- `POST /api/citations`

Search notes:
- Law search results are filtered to titles listed on the main laws page (page_id=247). That page is cached locally under `data/cache/page_247.json`; if it cannot be fetched and no cache exists, searches return an error.

Example:

```bash
curl --get \
  --data-urlencode "phrase=איסור עישון" \
  --data-urlencode "limit=5" \
  "http://127.0.0.1:8000/api/laws/search"
```

To request full section text, pass `full: true` in the JSON body:

```bash
curl -X POST "http://127.0.0.1:8000/api/laws/279238/sections/text" \
  -H "Content-Type: application/json" \
  -d '{"sections":["1","2"],"full":true}'
```

## MCP (HTTP)

MCP endpoint: `http://127.0.0.1:8000/mcp/`

If you deploy behind a public domain, set `MCP_ALLOWED_HOSTS` to include it.
Example:

```
MCP_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,israel-law-api-mcp.sliplane.app:*
```

To allow all hosts (not recommended for public deployments), disable DNS rebinding protection:

```
MCP_DNS_REBINDING_PROTECTION=false
```

Example MCP client config:

```json
{
  "mcpServers": {
    "israel-law": {
      "url": "http://127.0.0.1:8000/mcp/"
    }
  }
}
```

Test MCP client:

```bash
python3 scripts/test_mcp_client.py --server "http://127.0.0.1:8000/mcp/"
```

API check helper:

```bash
BASE_URL=http://127.0.0.1:8000/api python3 scripts/check_api.py
```

## Docker

Build and run (VPS-local access by default):

```bash
docker compose up -d --build
```

The container reads `HOST` and `PORT` from `.env`.

## Limits and safety

Default limits are configured via `.env` and applied per IP. You can adjust:

- `RATE_LIMIT_PER_IP` for request rates
- `MAX_SECTIONS_PER_REQUEST`
- `MAX_SECTION_TEXT_CHARS`
- `MAX_SEARCH_PHRASE_LEN`
- `MAX_SEARCH_LIMIT`
- `CONCURRENT_LIMIT_TOTAL` for concurrency caps
