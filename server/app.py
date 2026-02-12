import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = None
tfidf_matrix = None
id_to_index = None
restaurants_cache = None

app = FastAPI(title="Project36 Restaurant Recommender", version="0.1.0")


@app.on_event("startup")
def build_tfidf_index():
    global vectorizer, tfidf_matrix, id_to_index, restaurants_cache

    restaurants = load_restaurants("../data/restaurants.json")
    restaurants_cache = restaurants

    corpus = []
    id_to_index = {}

    for idx, r in enumerate(restaurants):
        text = f"{r.get('name','')} {r.get('menu_text','')} {r.get('cuisines','')}"
        corpus.append(text)
        id_to_index[r.get("id")] = idx

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)

    print(f"TF-IDF ready: {tfidf_matrix.shape[0]} documents")


# ----------------------------
# Load restaurant data
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

    # Ensure each entry is an object
    cleaned: List[Dict[str, Any]] = []
    for i, r in enumerate(restaurants):
        if isinstance(r, dict):
            cleaned.append(r)
        else:
            raise RuntimeError(f"restaurants[{i}] is not an object")

    return cleaned


RESTAURANTS: List[Dict[str, Any]] = load_restaurants(DATA_PATH)

# ----------------------------
# API Models
# ----------------------------

class RecommendRequest(BaseModel):
    # Week 1: keep it minimal. Add more fields later (distance, vegan, etc.)
    halal: bool = False
    top_k: int = Field(default=5, ge=1, le=50)
    query: Optional[str] = None


# ----------------------------
# Helpers
# ----------------------------

def get_number(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        # Avoid treating bool as number
        if isinstance(x, bool):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


# ----------------------------
# Routes
# ----------------------------

@app.get("/health")
def health():
    return {"ok": True, "count": len(RESTAURANTS)}


@app.post("/recommend")
def recommend(req: RecommendRequest):

    print("🔥 RECOMMEND CALLED 🔥")
    if not RESTAURANTS:
        raise HTTPException(status_code=500, detail="No restaurant data loaded.")

    results = list(RESTAURANTS)

    # Hard filter: halal requirement (uses your schema key: dietary_tags)
    if req.halal:
        results = [
            r for r in results
            if "halal" in (r.get("dietary_tags") or [])
        ]

    # Stub ranking: rating desc, then review_count desc
    #results.sort(
        #key=lambda r: (
            #get_number(r.get("rating"), 0.0),
            #get_number(r.get("review_count"), 0.0),
        #),
        #reverse=True
    #)

    # Build query string from request
    query_text = req.query or ""

    print("QUERY TEXT:", query_text)

    if req.halal:
        query_text += " halal "

    if query_text.strip() == "":
        query_text = "food"

    if req.halal:
        query_text += " halal "

    # You can expand this later with more features
    # Example: add cuisines if they exist
    # query_text += " " + (req.cuisine or "")

    if query_text.strip() == "":
        query_text = "restaurant"

    # Vectorize query
    query_vec = vectorizer.transform([query_text])

    # Compute cosine similarity
    similarity_scores = (tfidf_matrix @ query_vec.T).toarray().flatten()

    print("QUERY:", query_text)
    print("Similarity scores shape:", similarity_scores.shape)
    print("First 10 similarity scores:", similarity_scores[:10])

    # Attach scores to filtered results
    scored_results = []

    for r in results:
        idx = id_to_index.get(r.get("id"))
        if idx is not None:
            score = float(similarity_scores[idx])
            scored_results.append((score, r))
            print("Restaurant:", r.get("name"), "Score:", score)

    # Sort by TF-IDF similarity
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Replace results list
    results = [r for score, r in scored_results[:req.top_k]]


    output: List[Dict[str, Any]] = []

    for score, r in scored_results[: req.top_k]:

        dietary_tags = r.get("dietary_tags") or []
        rating = get_number(r.get("rating"), 0.0)

        why: List[str] = []

        if req.halal and "halal" in dietary_tags:
            why.append("matches halal")

        if score > 0:
            why.append("text match")

        output.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "dietary_tags": dietary_tags,
            "rating": rating,
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
            "score": round(score, 4),
            "why": why
        })


    return output

@app.post("/refresh")
def refresh():
    """Reload restaurants.json from disk (simple 'refresh' mechanism for your demo)."""
    global RESTAURANTS
    RESTAURANTS = load_restaurants(DATA_PATH)
    return {"ok": True, "count": len(RESTAURANTS), "reloaded_from": str(DATA_PATH)}