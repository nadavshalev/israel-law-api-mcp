# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always activate the virtual environment before running any commands:

```bash
source .venv/bin/activate
```

```bash
# Run the server locally
uvicorn api:app --reload

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_api.py

# Run a specific test
pytest tests/test_api.py::test_health

# Test REST API against a running server
python3 scripts/check_api.py

# Test MCP endpoint against a running server
python3 scripts/check_mcp_client.py --server "http://127.0.0.1:8000/mcp/"

# Build and run with Docker
docker-compose up --build
```

## Architecture

The app is a single `api.py` file that creates three FastAPI apps composed together:
- `api_app` — REST API, mounted at `/api`
- `mcp_app` — MCP server, mounted at `/mcp`
- `app` — root app that mounts both

Both interfaces expose the same four operations: search laws, list sections, get section text, and build citation URLs. The MCP tools and REST endpoints are thin wrappers around shared functions in `data/`.

**Data flow:** Hebrew Wikisource (`he.wikisource.org/w/api.php`) → `data/wiki_client.py` (raw MediaWiki API) → `data/law_get.py` (wikitext parsing, section extraction) → `api.py` (validation, limits, response shaping).

`data/law_get.py` fetches a cached index of valid law titles from Wikisource (stored at `data/cache/page_247.json`, 30-day TTL) to filter search results to actual laws. `data/citations.py` generates Wikisource anchor URLs from law title + section numbers.

**Configuration** (`config.py`): All limits and security settings are env-driven. The file reads from `.env` with a built-in fallback parser (no `python-dotenv` required). Key settings: rate limiting per IP, max concurrent requests, max sections per request, text truncation limit, and MCP allowed hosts for DNS rebinding protection.

**Tests** use `conftest.py` fixtures that reload modules with injected env vars and stub out network calls, so all tests run without hitting Wikisource.
