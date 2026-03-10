# server/query_processing.py

SYNONYMS = {
    "boba": "bubble tea",
    "bbq": "barbecue",
    "veg": "vegetarian",
}


def expand_query(query: str) -> str:
    """
    Replace common shorthand with expanded terms
    so TF-IDF can match more documents.
    """
    if not query:
        return ""

    words = query.lower().split()
    expanded = []

    for w in words:
        if w in SYNONYMS:
            expanded.append(SYNONYMS[w])
        expanded.append(w)

    return " ".join(expanded)