# Israeli Law MCP Server

This server provides access to Israeli legislation from the **Open Law Book** (ספר החוקים הפתוח) on Hebrew Wikisource. It exposes four tools for searching laws, browsing their structure, reading section text, and generating source citations.

All law titles and legal content are in Hebrew.

## Tools

| Tool | Purpose |
|------|---------|
| `mcp_search_laws` | Search for a law by Hebrew keyword. Returns matching laws with their `page_id`. |
| `mcp_list_sections` | Given a `page_id`, returns the table of contents: all section numbers and titles. |
| `mcp_get_sections_text` | Given a `page_id` and specific section numbers, returns the verbatim legal text. |
| `mcp_build_citations` | Given a law title and section numbers, returns direct Wikisource URLs to those sections. |

## Recommended Workflow

1. **Search** — call `mcp_search_laws` with a Hebrew keyword (e.g. `פיצויי פיטורין`) to find the relevant law and its `page_id`.
2. **Map** — call `mcp_list_sections` with the `page_id` to identify which section numbers are relevant.
3. **Read** — call `mcp_get_sections_text` with the `page_id` and those section numbers to retrieve the full text.
4. **Cite** — call `mcp_build_citations` to generate a verifiable source URL for any legal claim.

Do not skip Step 2 or guess section contents — always fetch the actual text before presenting information to the user.

## Usage Notes

- Up to 10 sections can be fetched per `mcp_get_sections_text` call.
- If a law is not found on the first search, retry with different Hebrew keywords or phrasing.
- If the requested section is not present in the results, report it explicitly rather than inferring the content.
- Always use `mcp_build_citations` to back legal claims with source links rather than citing from memory.
