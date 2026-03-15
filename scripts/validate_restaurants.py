import json
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ALLOWED_DIETARY_TAGS = {"halal", "vegan", "pescatarian", "vegetarian", "gluten_free"}
MIN_MENU_TEXT_LEN = 30

REQUIRED_FIELDS = {
    "id": str,
    "name": str,
    "dietary_tags": list,
    "rating": (int, float),
    "price_level": int,
    "address": str,
    "lat": (int, float),
    "lng": (int, float),
    "distance": (int, float),
    "hours_text": str,
    "source": str,
}

ALLOWED_SOURCES = {"manual", "google", "yelp"}

OPTIONAL_FIELDS = {
    "review_count": int,
    "phone": str,
    "menu_text": str,
    "categories": list,
}

def fail(errors: List[str]) -> None:
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1)

def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def is_non_empty_string(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def validate_lat_lng(lat: Any, lng: Any) -> Optional[str]:
    if not is_number(lat) or not is_number(lng):
        return "lat/lng must be numbers"
    if not (-90.0 <= float(lat) <= 90.0):
        return f"lat out of range (-90..90): {lat}"
    if not (-180.0 <= float(lng) <= 180.0):
        return f"lng out of range (-180..180): {lng}"
    return None

def validate_restaurant(
    obj: Dict[str, Any],
    idx: int,
    seen_ids: Set[str],
    seen_names: Set[str],
) -> List[str]:
    errs: List[str] = []
    prefix = f"restaurants[{idx}]"

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in obj:
            errs.append(f"{prefix}: missing required field '{field}'")
            continue

        val = obj[field]

        # numeric fields handled separately
        if field in ("rating", "lat", "lng", "distance"):
            if not is_number(val):
                errs.append(f"{prefix}.{field}: must be a number")
            continue

        # required string fields must not be empty/whitespace
        if expected_type == str and not is_non_empty_string(val):
            errs.append(f"{prefix}.{field}: cannot be empty")
            continue

        if not isinstance(val, expected_type):
            errs.append(f"{prefix}.{field}: expected {expected_type}, got {type(val).__name__}")


    # id uniqueness (use stripped id so whitespace doesn't create "different" IDs)
    rid = obj.get("id")
    if isinstance(rid, str):
        rid_clean = rid.strip()
        if rid_clean in seen_ids:
            errs.append(f"{prefix}.id: duplicate id '{rid_clean}'")
        elif rid_clean != "":
            seen_ids.add(rid_clean)
    

    # name uniqueness (case-insensitive, whitespace-normalized)
    name = obj.get("name")
    if isinstance(name, str):
        name_clean = " ".join(name.strip().lower().split())
        if name_clean == "":
            errs.append(f"{prefix}.name: cannot be empty")
        elif name_clean in seen_names:
            errs.append(f"{prefix}.name: duplicate name '{name.strip()}'")
        else:
            seen_names.add(name_clean)

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


    # distance bounds 0..50
    distance = obj.get("distance")
    if is_number(distance):
        d = float(distance)
        if d < 0.0 or d > 50.0:
            errs.append(f"{prefix}.distance: must be between 0 and 50, got {distance}")
    elif "distance" in obj:
        errs.append(f"{prefix}.distance: must be a number")

    # dietary_tags allowed values
    tags = obj.get("dietary_tags")

    if not isinstance(tags, list):
        errs.append(f"{prefix}.dietary_tags: must be a list")
    else:
        if len(tags) == 0:
            errs.append(f"{prefix}.dietary_tags: must have at least one tag")
        else:
            seen_tags = set()
            for t in tags:
                if not isinstance(t, str):
                    errs.append(f"{prefix}.dietary_tags: all tags must be strings")
                    break

                tag = t.strip()
                if tag == "":
                    errs.append(f"{prefix}.dietary_tags: tags cannot be empty strings")
                    continue

                if tag not in ALLOWED_DIETARY_TAGS:
                    errs.append(
                        f"{prefix}.dietary_tags: invalid tag '{tag}' (allowed: {sorted(ALLOWED_DIETARY_TAGS)})"
                    )
                if tag in seen_tags:
                    errs.append(f"{prefix}.dietary_tags: duplicate tag '{tag}'")
                else:
                    seen_tags.add(tag)

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
    # cuisines required and must be non-empty
    cuisines = obj.get("cuisines")
    if "cuisines" not in obj:
        errs.append(f"{prefix}.cuisines: missing required field 'cuisines'")
    elif not isinstance(cuisines, list):
        errs.append(f"{prefix}.cuisines: must be a list")
    elif len(cuisines) == 0:
        errs.append(f"{prefix}.cuisines: cannot be empty")
    elif any(not isinstance(x, str) or x.strip() == "" for x in cuisines):
        errs.append(f"{prefix}.cuisines: must be a non-empty list of non-empty strings")

    for field, expected_type in OPTIONAL_FIELDS.items():
        if field in obj:
            val = obj[field]
            if val is None:
                continue

            if field == "categories":
                if not isinstance(val, list):
                    errs.append(f"{prefix}.{field}: must be list or null")
                else:
                    if len(val) == 0:
                        errs.append(f"{prefix}.{field}: cannot be empty")
                    elif any(not isinstance(x, str) or x.strip() == "" for x in val):
                        errs.append(f"{prefix}.{field}: must be a non-empty list of non-empty strings")

            elif field == "menu_text":
                if not isinstance(val, str):
                    errs.append(f"{prefix}.menu_text: must be str or null")
                else:
                    if len(val.strip()) < MIN_MENU_TEXT_LEN:
                        errs.append(
                            f"{prefix}.menu_text: must be at least {MIN_MENU_TEXT_LEN} chars, got {len(val.strip())}"
                        )

            elif field == "review_count":
                if not (isinstance(val, int) and not isinstance(val, bool)):
                    errs.append(f"{prefix}.review_count: must be int or null")

            else:
                # phone, etc.
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
    seen_names: Set[str] = set()

    for i, item in enumerate(restaurants):
        if not isinstance(item, dict):
            errors.append(f"restaurants[{i}]: expected object, got {type(item).__name__}")
            continue
        errors.extend(validate_restaurant(item, i, seen_ids, seen_names))

    if errors:
        fail(errors)

    print(f"OK: {len(restaurants)} restaurants validated successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
