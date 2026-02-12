# server/app.py
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="Project36 Restaurant Recommender", version="0.1.0")

# ----------------------------
# Paths / Data loading
# ----------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "restaurants.json"

def load_restaurants(path: Path) -> List[Dict[str, Any]]:
    """Loads restaurant data from JSON.
    Accepts either:
      1) [ {restaurant}, ... ]
      2) { "restaurants": [ {restaurant}, ... ] }
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"restaurants.json not found at: {path}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in: {path} ({e})") from e

    if isinstance(data, dict) and "restaurants" in data:
        restaurants = data["restaurants"]
    else:
        restaurants = data

    if not isinstance(restaurants, list):
        raise RuntimeError(
            "restaurants.json must be a list OR an object with a 'restaurants' list."
        )

    cleaned: List[Dict[str, Any]] = []
    for i, r in enumerate(restaurants):
        if isinstance(r, dict):
            cleaned.append(r)
        else:
            raise RuntimeError(f"restaurants[{i}] is not an object")

    return cleaned

# Global cache (reloaded on refresh)
RESTAURANTS: List[Dict[str, Any]] = load_restaurants(DATA_PATH)

# ----------------------------
# TF-IDF index globals
# ----------------------------
vectorizer: Optional[TfidfVectorizer] = None
tfidf_matrix = None  # scipy sparse matrix
id_to_index: Dict[str, int] = {}

# ----------------------------
# TF-IDF document text builder
# ----------------------------
_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")

def _as_str_list(x: Any) -> List[str]:
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

def _expand_tags(tags: List[str]) -> List[str]:
    """Include both underscore and space forms, e.g., gluten_free + gluten free."""
    expanded: List[str] = []
    for t in tags:
        expanded.append(t)
        if "_" in t:
            expanded.append(t.replace("_", " "))
    return expanded

def build_doc_text(r: Dict[str, Any]) -> str:
    name = r.get("name", "") or ""
    cuisines = _as_str_list(r.get("cuisines"))
    categories = _as_str_list(r.get("categories"))
    menu_text = r.get("menu_text") or ""
    dietary_tags = _as_str_list(r.get("dietary_tags"))
    dietary_expanded = _expand_tags(dietary_tags)

    # Price token helps "cheap" vibes indirectly ($, $$, $$$, $$$$)
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

    # Upweight dietary tags by repeating (expanded)
    parts.extend(dietary_expanded)
    parts.extend(dietary_expanded)

    return _clean(" ".join(p for p in parts if p))

# ----------------------------
# Helpers (numbers, distance, etc.)
# ----------------------------
def get_number(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default

# Campus center (approx) - simple demo reference point
CAMPUS_LAT = 33.6405
CAMPUS_LNG = -117.8443
MAX_DISTANCE_MILES = 2.0  # beyond this distance_score becomes 0

def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2))
    return 2 * R * math.asin(math.sqrt(a))

def distance_score(r: Dict[str, Any]) -> float:
    lat = get_number(r.get("lat"), None)  # type: ignore[arg-type]
    lng = get_number(r.get("lng"), None)  # type: ignore[arg-type]
    if lat is None or lng is None:
        return 0.0

    d = haversine_miles(CAMPUS_LAT, CAMPUS_LNG, float(lat), float(lng))
    if d >= MAX_DISTANCE_MILES:
        return 0.0

    return max(0.0, 1.0 - (d / MAX_DISTANCE_MILES))

def open_score(r: Dict[str, Any]) -> float:
    """
    Simple heuristic:
    - if hours_text contains 'closed' => 0
    - if it contains am/pm => 1
    - otherwise => 0.5
    """
    hours = (r.get("hours_text") or "").lower()
    if "closed" in hours:
        return 0.0
    if "am" in hours or "pm" in hours:
        return 1.0
    return 0.5

def rating_score(r: Dict[str, Any]) -> float:
    rating = get_number(r.get("rating"), 0.0)
    return min(max(rating / 5.0, 0.0), 1.0)

# ----------------------------
# API Models
# ----------------------------
class RecommendRequest(BaseModel):
    halal: bool = False
    top_k: int = Field(default=5, ge=1, le=50)
    query: Optional[str] = None

# ----------------------------
# Build TF-IDF at startup
# ----------------------------
@app.on_event("startup")
def build_tfidf_index() -> None:
    global vectorizer, tfidf_matrix, id_to_index, RESTAURANTS

    # Load fresh in case file changed before startup
    RESTAURANTS = load_restaurants(DATA_PATH)

    corpus: List[str] = []
    id_to_index = {}

    for idx, r in enumerate(RESTAURANTS):
        corpus.append(build_doc_text(r))
        rid = r.get("id")
        if isinstance(rid, str):
            id_to_index[rid] = idx

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)

    print(f"TF-IDF ready: {tfidf_matrix.shape[0]} documents")

# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return {"ok": True, "count": len(RESTAURANTS)}

@app.post("/recommend")
def recommend(req: RecommendRequest):
    if not RESTAURANTS:
        raise HTTPException(status_code=500, detail="No restaurant data loaded.")
    if vectorizer is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF index not initialized.")

    # Start from full set
    candidates = list(RESTAURANTS)

    # Hard filter: halal
    if req.halal:
        candidates = [
            r for r in candidates
            if "halal" in (r.get("dietary_tags") or [])
        ]

    # Build query text
    query_text = (req.query or "").strip()
    if req.halal:
        # reinforce importance (also helps explanations)
        query_text = (query_text + " halal").strip()

    if query_text == "":
        query_text = "food"

    # TF-IDF query vector
    query_vec = vectorizer.transform([query_text])

    # Cosine similarity with TF-IDF vectors (since sklearn TF-IDF vectors are L2-normalized)
    similarity_scores = (tfidf_matrix @ query_vec.T).toarray().flatten()

    scored_results: List[tuple] = []

    for r in candidates:
        rid = r.get("id")
        if not isinstance(rid, str):
            continue
        idx = id_to_index.get(rid)
        if idx is None:
            continue

        tfidf = float(similarity_scores[idx])
        dist = distance_score(r)
        opn = open_score(r)
        rate = rating_score(r)

        final_score = (
            0.50 * tfidf +
            0.20 * dist +
            0.20 * opn +
            0.10 * rate
        )

        scored_results.append((final_score, tfidf, dist, opn, rate, r))

    scored_results.sort(key=lambda x: x[0], reverse=True)

    output: List[Dict[str, Any]] = []

    for final_score, tfidf, dist, opn, rate, r in scored_results[: req.top_k]:
        dietary_tags = r.get("dietary_tags") or []

        why: List[str] = []

        # Dietary
        if req.halal and "halal" in dietary_tags:
            why.append("matches halal requirement")

        # Text
        if tfidf > 0.0:
            why.append("matches search terms")

        # Distance
        if dist > 0.7:
            why.append("very close to campus")
        elif dist > 0.4:
            why.append("near campus")

        # Open
        if opn == 1.0:
            why.append("open now")
        elif opn == 0.0:
            why.append("may be closed")

        # Rating
        if rate >= 0.8:
            why.append(f"high rating ({r.get('rating')})")

        output.append({
            # Restaurant fields (unchanged)
            "id": r.get("id"),
            "name": r.get("name"),
            "dietary_tags": dietary_tags,
            "rating": get_number(r.get("rating"), 0.0),
            "price_level": r.get("price_level"),
            "address": r.get("address"),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "hours_text": r.get("hours_text"),
            "source": r.get("source"),
            "review_count": r.get("review_count"),
            "phone": r.get("phone"),
            "menu_text": r.get("menu_text"),
            "cuisines": r.get("cuisines"),
            "categories": r.get("categories"),

            # Scoring outputs
            "score": round(final_score, 4),
            "score_components": {
                "tfidf": round(tfidf, 4),
                "distance": round(dist, 4),
                "open": round(opn, 4),
                "rating": round(rate, 4),
            },
            "why": why
        })

    return output

@app.post("/refresh")
def refresh():
    """Reload restaurants.json and rebuild TF-IDF index (simple refresh mechanism for demo)."""
    global RESTAURANTS, vectorizer, tfidf_matrix, id_to_index

    RESTAURANTS = load_restaurants(DATA_PATH)

    corpus: List[str] = []
    id_to_index = {}

    for idx, r in enumerate(RESTAURANTS):
        corpus.append(build_doc_text(r))
        rid = r.get("id")
        if isinstance(rid, str):
            id_to_index[rid] = idx

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)

    return {"ok": True, "count": len(RESTAURANTS), "reloaded_from": str(DATA_PATH)}