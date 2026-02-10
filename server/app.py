import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Project36 Restaurant Recommender", version="0.1.0")

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
    results.sort(
        key=lambda r: (
            get_number(r.get("rating"), 0.0),
            get_number(r.get("review_count"), 0.0),
        ),
        reverse=True
    )

    output: List[Dict[str, Any]] = []
    for r in results[: req.top_k]:
        dietary_tags = r.get("dietary_tags") or []
        rating = get_number(r.get("rating"), 0.0)

        why: List[str] = []
        if req.halal and "halal" in dietary_tags:
            why.append("matches halal")
        if rating >= 4.5:
            why.append("high rating")

        output.append({
            # keep core fields consistent with your dataset schema
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

            # optional fields (may be None)
            "review_count": r.get("review_count"),
            "phone": r.get("phone"),
            "menu_text": r.get("menu_text"),
            "cuisines": r.get("cuisines"),
            "categories": r.get("categories"),

            # recommendation extras
            "score": round(rating * 10.0, 2),  # placeholder numeric score
            "why": why
        })

    return output


@app.post("/refresh")
def refresh():
    """Reload restaurants.json from disk (simple 'refresh' mechanism for your demo)."""
    global RESTAURANTS
    RESTAURANTS = load_restaurants(DATA_PATH)
    return {"ok": True, "count": len(RESTAURANTS), "reloaded_from": str(DATA_PATH)}