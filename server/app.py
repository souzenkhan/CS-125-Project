from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "restaurants.json"


def load_restaurants() -> List[Dict[str, Any]]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {DATA_PATH}: {e}") from e

    if isinstance(data, dict) and "restaurants" in data:
        return data["restaurants"]
    if isinstance(data, list):
        return data
    return []


class Location(BaseModel):
    lat: float
    lng: float


class RecommendRequest(BaseModel):
    user_location: Optional[Location] = None
    use_campus_center: bool = False
    dietary_required: List[str] = Field(default_factory=list)
    cuisines_optional: List[str] = Field(default_factory=list)
    max_distance_miles: float
    price_max: int
    query_text: Optional[str] = None
    top_k: int


@app.get("/health")
def health():
   
    return {"ok": True}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    if req.user_location is None and not req.use_campus_center:
        raise HTTPException(
            status_code=422,
            detail="Provide user_location or set use_campus_center=true",
        )

    restaurants = load_restaurants()

    results = []
    for r in restaurants:
        tags = r.get("dietary_tags") or []
        if any(tag not in tags for tag in req.dietary_required):
            continue

        price_level = r.get("price_level")
        if isinstance(price_level, int) and price_level > req.price_max:
            continue

        rating = r.get("rating")
        try:
            score = float(rating) / 5.0 if rating is not None else 0.0
        except Exception:
            score = 0.0

        why = []
        for tag in req.dietary_required:
            why.append(f"Matches dietary_required: {tag}")
        why.append("Price level <= price_max")

        results.append({"restaurant": r, "score": score, "why": why})

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results[: max(req.top_k, 0)]}
