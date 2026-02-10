import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# ---------- Load restaurant data at startup ----------

DATA_PATH = Path(__file__).parent.parent / "data" / "restaurants.json"

with open(DATA_PATH, "r") as f:
    RESTAURANTS = json.load(f)

# ---------- Models ----------

class RecommendRequest(BaseModel):
    halal: Optional[bool] = False
    top_k: int = 5


class RecommendResult(BaseModel):
    id: int
    name: str
    rating: float
    review_count: Optional[int]
    tags: List[str]
    score: float
    why: List[str]

# ---------- Routes ----------

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    results = RESTAURANTS.copy()

    # Hard filter: halal requirement
    if req.halal:
        results = [
            r for r in results
            if "halal" in r.get("tags", [])
        ]

    # Stub ranking: rating desc, then review_count desc
    results.sort(
        key=lambda r: (
            r.get("rating", 0),
            r.get("review_count", 0)
        ),
        reverse=True
    )

    output = []
    for r in results[:req.top_k]:
        why = []

        if req.halal and "halal" in r.get("tags", []):
            why.append("matches halal")
        if r.get("rating", 0) >= 4.5:
            why.append("high rating")

        output.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "rating": r.get("rating"),
            "review_count": r.get("review_count"),
            "tags": r.get("tags", []),
            "score": round(r.get("rating", 0) * 10, 2),  # fake numeric score
            "why": why
        })

    return output

