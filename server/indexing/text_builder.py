import re
from typing import Any, Dict, List

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")   # keep letters, numbers, whitespace
_WS_RE = re.compile(r"\s+")

def _as_str_list(x: Any) -> List[str]:
    """Allow list[str] or null. If string is passed by mistake, wrap it."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v) for v in x if v is not None]
    return [str(x)]

def _clean(s: str) -> str:
    s = s.lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

def expand_tags(tags: List[str]) -> List[str]:
    """
    For tags like 'gluten_free', include both:
    - 'gluten_free'
    - 'gluten free'
    """
    expanded = []
    for t in tags:
        expanded.append(t)
        if "_" in t:
            expanded.append(t.replace("_", " "))
    return expanded

def build_doc_text(r: Dict[str, Any]) -> str:
    """
    Build the TF-IDF document text for one restaurant object.

    Uses schema fields:
    - name (str)
    - cuisines (list[str] | null)
    - categories (list[str] | null)
    - menu_text (str | null)
    - dietary_tags (list[str])
    - price_level (int 1..4)
    """
    name = r.get("name", "") or ""
    cuisines = _as_str_list(r.get("cuisines"))
    categories = _as_str_list(r.get("categories"))
    menu_text = r.get("menu_text") or ""

    dietary_tags = _as_str_list(r.get("dietary_tags"))
    expanded_dietary = expand_tags(dietary_tags)

    # Add a price token to help queries like "cheap" map loosely via "$", "$$"
    price_token = ""
    pl = r.get("price_level")
    if isinstance(pl, int) and 1 <= pl <= 4:
        price_token = "$" * pl

    parts: List[str] = []
    parts.append(name)
    parts.extend(cuisines)
    parts.extend(categories)
    parts.append(menu_text)
    parts.append(price_token)

    # Upweight dietary tags by repeating them
    parts.extend(expanded_dietary)
    parts.extend(expanded_dietary)

    # Remove empties and normalize
    return _clean(" ".join(p for p in parts if p))