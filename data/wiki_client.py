from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import requests

class MediaWikiClient:
    def __init__(self) -> None:
        self.config = {
            "base_url": "https://he.wikisource.org/w/api.php",
            "user_agent": "IsraelLawApiMcp/1.0 (+https://github.com/nadavshalev/israel-law-api-mcp)"
        }
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.config["user_agent"],
                "Accept": "application/json",
            }
        )

    def get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.get(self.config["base_url"], params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 10, namespace: int | None = None) -> Dict[str, Any]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        if namespace is not None:
            params["srnamespace"] = namespace
        return self.get(params)
