import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from server.indexing.text_builder import build_doc_text

with open("data/restaurants.json", "r", encoding="utf-8") as f:
    restaurants = json.load(f)

for r in restaurants[:3]:
    print("ID:", r.get("id"))
    print("NAME:", r.get("name"))
    print("DOC_TEXT:", build_doc_text(r))
    print("-" * 70)