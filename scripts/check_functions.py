#%% Imports and setup
from pathlib import Path
from pprint import pprint
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from data.law_get import wide_law_search, get_law_sections_titles, get_law_sections_text
from data.citations import build_citations_url

#%% Wide search

results = wide_law_search("תקנות רישוי עסקים")
pprint({"search_results": results})

if not results:
    raise SystemExit("No results")

#%% Fetch law wikitext
title = str(results[0]["title"])
page_id = int(results[0]["page_id"])

sections = get_law_sections_titles(page_id)
print(f"Found {len(sections)} sections in the law '{title}'.")
pprint({"sections": sections[:5]})  # Print only the first 5 sections for brevity

#%% Fetch section text
if not sections:
    raise SystemExit("No sections found")

sections_numbers = ['16', '27', '3א']  # Example section numbers to fetch

sections_with_text = get_law_sections_text(page_id, sections_numbers)
print(f"Retrieved text for {len(sections_with_text)} sections.")

for section in sections_with_text:
    print(f"Section ID: {section['section_id']}")
    print(f"Number: {section['number']}")
    print(f"Title: {section['title']}")
    print(f"Text: {section['text'][:200]}...")  # Print only the first 200 characters of the text
    print("-" * 40)

#%% Citations

citations = build_citations_url(title, sections_numbers)
print(f"Generated {len(citations)} citations:")
pprint({"citations": citations})