from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        env_path = Path(__file__).resolve().parent / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


RATE_LIMIT_ENABLED = _get_bool("RATE_LIMIT_ENABLED", True)
RATE_LIMIT_PER_IP = os.getenv("RATE_LIMIT_PER_IP", "60/minute")

MAX_SECTIONS_PER_REQUEST = _get_int("MAX_SECTIONS_PER_REQUEST", 10)
MAX_SECTION_TEXT_CHARS = _get_int("MAX_SECTION_TEXT_CHARS", 10000)
MAX_SEARCH_PHRASE_LEN = _get_int("MAX_SEARCH_PHRASE_LEN", 120)
MAX_SEARCH_LIMIT = _get_int("MAX_SEARCH_LIMIT", 20)

CONCURRENT_LIMIT_ENABLED = _get_bool("CONCURRENT_LIMIT_ENABLED", True)
CONCURRENT_LIMIT_TOTAL = _get_int("CONCURRENT_LIMIT_TOTAL", 10)
