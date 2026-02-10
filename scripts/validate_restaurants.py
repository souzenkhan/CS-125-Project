import json
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ALLOWED_DIETARY_TAGS = {"halal", "vegan", "pescatarian", "vegetarian", "gluten_free"}

REQUIRED_FIELDS = {
    "id": str,
    "name": str,
    "dietary_tags": list,
    "rating": (int, float),
    "price_level": int,
    "address": str,
    "lat": (int, float),
    "lng": (int, float),
    "hours_text": str,
    "source": str,
}

ALLOWED_SOURCES = {"manual", "google", "yelp"}

OPTIONAL_FIELDS = {
    "review_count": int,
    "phone": str,
    "menu_text": str,
    "cuisines": list,
    "categories": list,
}

def fail(errors: List[str]) -> None:
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1)

def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def validate_lat_lng(lat: Any, lng: Any) -> Optional[str]:
    if not is_number(lat) or not is_number(lng):
        return "lat/lng must be numbers"
    if not (-90.0 <= float(lat) <= 90.0):
        return f"lat out of range (-90..90): {lat}"
    if not (-180.0 <= float(lng) <= 180.0):
        return f"lng out of range (-180..180): {lng}"
    return None

def validate_restaurant(obj: Dict[str, Any], idx: int, seen_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    prefix = f"restaurants[{idx}]"

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in obj:
            errs.append(f"{prefix}: missing required field '{field}'")
            continue
        val = obj[field]
        if field in ("rating", "lat", "lng"):
            if not is_number(val):
                errs.append(f"{prefix}.{field}: must be a number")
        elif not isinstance(val, expected_type):
            errs.append(f"{prefix}.{field}: expected {expected_type}, got {type(val).__name__}")

    # id uniqueness
    rid = obj.get("id")
    if isinstance(rid, str):
        if rid.strip() == "":
            errs.append(f"{prefix}.id: cannot be empty")
        elif rid in seen_ids:
            errs.append(f"{prefix}.id: duplicate id '{rid}'")
        else:
            seen_ids.add(rid)

    # rating bounds 0..5
    rating = obj.get("rating")
    if is_number(rating):
        r = float(rating)
        if r < 0.0 or r > 5.0:
            errs.append(f"{prefix}.rating: must be between 0 and 5, got {rating}")

    # price_level bounds 1..4
    pl = obj.get("price_level")
    if isinstance(pl, int) and not isinstance(pl, bool):
        if pl < 1 or pl > 4:
            errs.append(f"{prefix}.price_level: must be 1..4, got {pl}")
    elif "price_level" in obj:
        errs.append(f"{prefix}.price_level: must be int 1..4")

    # dietary_tags allowed values
    tags = obj.get("dietary_tags")
    if isinstance(tags, list):
        for t in tags:
            if not isinstance(t, str):
                errs.append(f"{prefix}.dietary_tags: all tags must be strings")
                break
            if t not in ALLOWED_DIETARY_TAGS:
                errs.append(f"{prefix}.dietary_tags: invalid tag '{t}' (allowed: {sorted(ALLOWED_DIETARY_TAGS)})")

    # source allowed values
    src = obj.get("source")
    if isinstance(src, str):
        if src not in ALLOWED_SOURCES:
            errs.append(f"{prefix}.source: must be one of {sorted(ALLOWED_SOURCES)}, got '{src}'")

    # lat/lng range
    if "lat" in obj and "lng" in obj:
        msg = validate_lat_lng(obj.get("lat"), obj.get("lng"))
        if msg:
            errs.append(f"{prefix}: {msg}")

    for field, expected_type in OPTIONAL_FIELDS.items():
        if field in obj:
            val = obj[field]
            if val is None:
                continue
            if field in ("cuisines", "categories"):
                if not isinstance(val, list):
                    errs.append(f"{prefix}.{field}: must be list or null")
                else:
                    if any(not isinstance(x, str) for x in val):
                        errs.append(f"{prefix}.{field}: must be list of strings")
            elif field == "review_count":
                if not (isinstance(val, int) and not isinstance(val, bool)):
                    errs.append(f"{prefix}.review_count: must be int or null")
            else:
                if not isinstance(val, expected_type):
                    errs.append(f"{prefix}.{field}: must be {expected_type.__name__} or null")

    return errs

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_restaurants.py path/to/restaurants.json")
        sys.exit(2)

    path = sys.argv[1]

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        fail([f"File not found: {path}"])
    except json.JSONDecodeError as e:
        fail([f"Invalid JSON in {path}: {e}"])

    # Accept either:
    # 1) list of restaurants
    # 2) { "restaurants": [ ... ] }
    if isinstance(data, dict) and "restaurants" in data:
        restaurants = data["restaurants"]
    else:
        restaurants = data

    if not isinstance(restaurants, list):
        fail([f"Top-level must be a list OR an object with 'restaurants' list. Got {type(restaurants).__name__}"])

    errors: List[str] = []
    seen_ids: Set[str] = set()

    for i, item in enumerate(restaurants):
        if not isinstance(item, dict):
            errors.append(f"restaurants[{i}]: expected object, got {type(item).__name__}")
            continue
        errors.extend(validate_restaurant(item, i, seen_ids))

    if errors:
        fail(errors)

    print(f"OK: {len(restaurants)} restaurants validated successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
