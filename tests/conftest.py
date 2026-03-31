from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def stub_wide_law_search(_: str, limit: int = 10):
    return [{"title": "Law", "page_id": 1} for _ in range(limit)]


def stub_get_law_sections_titles(_: int):
    return [{"section_id": "1:Title", "number": "1", "title": "Title"}]


def stub_get_law_sections_text(_: int, sections_num: list[str]):
    return [
        {
            "section_id": f"{num}:Title",
            "number": num,
            "title": "Title",
            "text": "X" * 20,
        }
        for num in sections_num
    ]


def stub_resolve_id_to_page_id(id: int) -> int:
    return id  # treat any id as a valid page_id in tests


def with_stubs(*modules) -> None:
    for mod in modules:
        mod.wide_law_search = stub_wide_law_search
        mod.get_law_sections_titles = stub_get_law_sections_titles
        mod.get_law_sections_text = stub_get_law_sections_text
        mod.resolve_id_to_page_id = stub_resolve_id_to_page_id


def build_app(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))

    import config as config_module
    import rest_api as rest_module
    import mcp_server as mcp_module
    import main as main_module

    importlib.reload(config_module)
    importlib.reload(rest_module)
    importlib.reload(mcp_module)
    importlib.reload(main_module)

    return main_module.app, rest_module, mcp_module


def build_mcp_module(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))

    import config as config_module
    import mcp_server as mcp_module

    importlib.reload(config_module)
    importlib.reload(mcp_module)

    return mcp_module
