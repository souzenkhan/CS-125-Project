# server/app.py
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
from datetime import datetime

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
# User Profile (single-user prototype)
# ----------------------------
class UserProfile:
    def __init__(self):
        self.dietary_required: List[str] = []
        self.preferred_cuisines: List[str] = []
        self.disliked_cuisines: List[str] = []
        self.price_preference: int = 2
        self.click_history: List[str] = []

    def record_click(self, restaurant_id: str):
        self.click_history.append(restaurant_id)

    def cuisine_click_counts(self, restaurant_lookup: Dict[str, Dict[str, Any]]) -> Counter:
        counter = Counter()
        for rid in self.click_history:
            r = restaurant_lookup.get(rid)
            if not r:
                continue
            for c in r.get("cuisines", []) or []:
                counter[c.lower()] += 1
        return counter


user_profile = UserProfile()

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

def price_score(r: Dict[str, Any]) -> float:
    restaurant_price = r.get("price_level")
    if not isinstance(restaurant_price, int):
        return 0.5  # neutral if unknown

    diff = abs(user_profile.price_preference - restaurant_price)
    return max(0.0, 1.0 - (diff / 4.0))


def miles_away(r: Dict[str, Any]) -> Optional[float]:
    """Actual distance in miles (for explanations)."""
    lat = r.get("lat")
    lng = r.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return haversine_miles(CAMPUS_LAT, CAMPUS_LNG, float(lat), float(lng))
    except Exception:
        return None


def extract_query_terms(query_text: str) -> List[str]:
    """
    Pick 1–2 meaningful terms from the user's query for explanation.
    Keep it simple + deterministic.
    """
    STOP = {
        "food", "restaurant", "restaurants", "near", "nearby", "uc", "uci",
        "campus", "open", "now", "best", "good", "cheap", "in", "out",
        "the", "a", "an", "and", "or", "to", "for"
    }
    tokens = [t.strip().lower() for t in query_text.replace("_", " ").split()]
    tokens = [t for t in tokens if t and t not in STOP and len(t) >= 3]

    seen = set()
    uniq: List[str] = []
    for t in tokens:
        if t not in seen:
            uniq.append(t)
            seen.add(t)

    return uniq[:2]


def term_appears_in_doc(term: str, doc_text: str) -> bool:
    return term in doc_text


def build_why(
    *,
    req: "RecommendRequest",
    r: Dict[str, Any],
    query_text: str,
    tfidf: float,
    dist_miles: Optional[float],
    opn: float,
    rate_norm: float,
) -> List[str]:
    """
    Return 3–5 concise explanation bullets grounded in scoring signals.
    """
    why: List[str] = []

    dietary_tags = r.get("dietary_tags") or []

    # 1) Dietary constraint
    if req.halal and "halal" in dietary_tags:
        why.append("matches halal")

    # 2) Query term match (specific)
    doc = build_doc_text(r)
    terms = extract_query_terms(query_text)
    matched_terms = [t for t in terms if term_appears_in_doc(t, doc)]

    if matched_terms:
        why.append(f"query match: {', '.join(matched_terms)}")
    elif tfidf > 0.0 and query_text.strip():
        why.append("matches search terms")

    # 3) Distance
    if dist_miles is not None:
        why.append(f"{dist_miles:.1f} mi away")
        if dist_miles <= 0.8:
            why.append("walkable distance")

    # 4) Open / closing soon (simple heuristic)
    hours = (r.get("hours_text") or "").lower()
    if "closed" in hours:
        why.append("may be closed")
    else:
        why.append("open now")

    # 5) Rating
    rating_val = get_number(r.get("rating"), 0.0)
    if rate_norm >= 0.8:
        why.append(f"high rating ({rating_val:.1f})")
    elif rating_val > 0:
        why.append(f"rating {rating_val:.1f}")

    # Ensure 3–5 bullets
    return why[:5]


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

def ensure_index_ready():
    global vectorizer, tfidf_matrix, id_to_index, RESTAURANTS

    if vectorizer is not None and tfidf_matrix is not None:
        return

    # Load data if needed
    if not RESTAURANTS:
        RESTAURANTS = load_restaurants(DATA_PATH)

    corpus = []
    id_to_index = {}

    for idx, r in enumerate(RESTAURANTS):
        corpus.append(build_doc_text(r))
        rid = r.get("id")
        if isinstance(rid, str):
            id_to_index[rid] = idx

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return {"ok": True, "count": len(RESTAURANTS)}

def get_time_of_day():
    hour = datetime.now().hour

    if 5 <= hour < 11:
        return "morning"
    elif 11 <= hour < 16:
        return "lunch"
    else:
        return "dinner"
    
def time_context_boost(restaurant, time_of_day):
    tags = restaurant.get("tags") or []
    cuisines = restaurant.get("cuisines") or []

    boost = 0.0

    if time_of_day == "morning":
        if "cafe" in tags or "coffee" in tags or "breakfast" in cuisines:
            boost = 0.15

    elif time_of_day == "lunch":
        if "fast food" in cuisines or "sandwich" in cuisines:
            boost = 0.12

    elif time_of_day == "dinner":
        if "restaurant" in tags or "dinner" in cuisines:
            boost = 0.10

    return boost

@app.post("/recommend")
def recommend(req: RecommendRequest):
    #if not RESTAURANTS:
        #raise HTTPException(status_code=500, detail="No restaurant data loaded.")
    #if vectorizer is None or tfidf_matrix is None:
        #raise HTTPException(status_code=500, detail="TF-IDF index not initialized.")
    ensure_index_ready()
    time_of_day = get_time_of_day()
    

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
        query_text = (query_text + " halal").strip()
    if query_text == "":
        query_text = "food"

    query_vec = vectorizer.transform([query_text])
    similarity_scores = (tfidf_matrix @ query_vec.T).toarray().flatten()

    restaurant_lookup = {r["id"]: r for r in RESTAURANTS if isinstance(r.get("id"), str)}
    cuisine_counts = user_profile.cuisine_click_counts(restaurant_lookup)

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
        # Price preference score
        price = price_score(r)
        time_boost = time_context_boost(r, time_of_day)

        # Personal boost
        personal_boost = 0.0
        for cuisine in r.get("cuisines", []) or []:
            cuisine_lower = cuisine.lower()

            # Boost clicked cuisines
            if cuisine_lower in cuisine_counts:
                personal_boost += 0.05 * cuisine_counts[cuisine_lower]

            # Boost explicitly preferred cuisines
            if cuisine_lower in user_profile.preferred_cuisines:
                personal_boost += 0.05

            # Penalty for disliked cuisines
            if cuisine_lower in user_profile.disliked_cuisines:
                personal_boost -= 0.05

        # Clamp to safe range
        personal_boost = max(-0.2, min(personal_boost, 0.4))

        final_score = (
            0.40 * tfidf +
            0.15 * dist +
            0.15 * opn +
            0.10 * rate +
            0.10 * price +
            0.10 * personal_boost +
            0.10 * time_boost
        )

        scored_results.append((final_score, tfidf, dist, opn, rate, price, personal_boost, r))

    scored_results.sort(key=lambda x: x[0], reverse=True)

    output: List[Dict[str, Any]] = []

    for final_score, tfidf, dist, opn, rate, price, personal_boost, r in scored_results[: req.top_k]:
        dietary_tags = r.get("dietary_tags") or []
        dist_miles = miles_away(r)

        why = build_why(
            req=req,
            r=r,
            query_text=query_text,
            tfidf=tfidf,
            dist_miles=dist_miles,
            opn=opn,
            rate_norm=rate,
        )

        output.append({
            # Restaurant fields
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
                "price": round(price, 4),
                "personal_boost": round(personal_boost, 4),
                "time_boost": round(time_boost, 4),
            },
            "why": why
        })

    return output

class FeedbackRequest(BaseModel):
    restaurant_id: str


@app.post("/feedback")
def record_feedback(feedback: FeedbackRequest):
    rid = feedback.restaurant_id

    if rid not in [r.get("id") for r in RESTAURANTS]:
        raise HTTPException(status_code=400, detail="Invalid restaurant_id")

    user_profile.record_click(rid)

    return {"status": "recorded", "click_history_count": len(user_profile.click_history)}


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