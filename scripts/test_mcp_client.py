from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession

from mcp.client.streamable_http import streamable_http_client as http_client


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test MCP HTTP server")
    parser.add_argument(
        "--server",
        type=str,
        default="http://127.0.0.1:8000/mcp/",
        help="MCP server URL",
    )
    parser.add_argument(
        "--phrase",
        type=str,
        default="איסור עישון",
        help="Search phrase for test call",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Limit for search results",
    )
    args = parser.parse_args()

    server_url = args.server
    if server_url.endswith("/mcp"):
        server_url = f"{server_url}/"

    def to_jsonable(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj

    async with http_client(server_url) as streams:
        read, write = streams[:2]
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:")
            print(json.dumps(to_jsonable(tools), ensure_ascii=False, indent=2))

            result = await session.call_tool(
                "mcp_search_laws",
                {"phrase": args.phrase, "limit": args.limit},
            )
            print("\nSearch result:")
            print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
