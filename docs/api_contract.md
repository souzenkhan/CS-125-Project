# API Contract

## Endpoint: Recommend restaurants
**POST** `/recommend`

Goal: iOS sends preferences + location, server returns ranked restaurant recommendations.

---

## Request (JSON)

### Location rule (required)
Client must send **either**:
- `user_location` (lat/lng), OR
- `use_campus_center: true`

If both are provided, server uses `user_location`.

### Request fields
- `user_location` (object, optional)
  - `lat` (number)
  - `lng` (number)
- `use_campus_center` (boolean, optional; default `false`)
- `dietary_required` (array[string], required) — **hard filters** (restaurant must satisfy all)
- `cuisines_optional` (array[string], optional; default `[]`) — **soft preference**
- `max_distance_miles` (number, required)
- `price_max` (int, required; allowed `1..4`)
- `query_text` (string, optional)
- `top_k` (int, required)

### Price scale
- `1 = $`
- `2 = $$`
- `3 = $$$`
- `4 = $$$$`

### Dietary tags allowed (initial set)
- `halal`, `vegan`, `pescatarian`, `vegetarian`, `gluten_free`

---

## Response (JSON) — 200 OK

### Response fields
- `results` (array, required)

Each result contains:
- `restaurant` (object, required) — restaurant document (snake_case schema)
- `score` (number, required) — higher is better (recommended `0..1`)
- `why` (array[string], required) — short reasons suitable for UI display

### Restaurant object schema (returned inside each result)

Required fields:
- `id` (string) — unique identifier
- `name` (string)
- `dietary_tags` (array[string])
- `rating` (number `0..5`)
- `price_level` (int `1..4`)
- `address` (string)
- `lat` (number)
- `lng` (number)
- `hours_text` (string)
- `source` (string) — allowed: `manual`, `google`, `yelp`

Optional fields (if missing, return `null`):
- `review_count` (int|null)
- `phone` (string|null)
- `menu_text` (string|null)
- `cuisines` (array[string]|null)
- `categories` (array[string]|null)

---

## Error Responses

### 400 Bad Request
```json
{ "error": "bad_request", "message": "top_k is required" }

### 422 Validation Error
{ "error": "validation_error", "message": "Provide user_location or set use_campus_center=true" }

### 500 Server Error
{ "error": "server_error", "message": "Unexpected error" }

---

## Examples

### Example 1: user_location + multiple dietary filters + cuisines preferences

#### Request
{
  "user_location": { "lat": 33.6405, "lng": -117.8443 },
  "use_campus_center": false,
  "dietary_required": ["halal", "vegetarian"],
  "cuisines_optional": ["mexican", "thai"],
  "max_distance_miles": 3.0,
  "price_max": 2,
  "query_text": "quick lunch",
  "top_k": 5
}

#### Response (200)
{
  "results": [
    {
      "restaurant": {
        "id": "moongoat_coffee",
        "name": "MoonGoat Coffee",
        "dietary_tags": ["vegan", "vegetarian"],
        "rating": 4.0,
        "price_level": 2,
        "address": "5171 California Ave unit 100, Irvine, CA, 92617",
        "lat": 33.64252214002005,
        "lng": -117.83871802459163,
        "hours_text": "Mon–Sun 6am–6pm",
        "source": "google",
        "review_count": 1240,
        "phone": "(949) 612-2875",
        "menu_text": null,
        "cuisines": ["American"],
        "categories": ["Cafe", "Fast Food"]
      },
      "score": 0.91,
      "why": [
        "Matches dietary_required: vegetarian",
        "Within max_distance_miles",
        "Price level <= price_max"
      ]
    }
  ]
}

---

### Example 2 : campus center + halal only

#### Request
{
  "use_campus_center": true,
  "dietary_required": ["halal"],
  "cuisines_optional": [],
  "max_distance_miles": 2.0,
  "price_max": 2,
  "top_k": 3
}

#### Response (200)
{
  "results": [
    {
      "restaurant": {
        "id": "example_halal_1",
        "name": "Example Halal Spot",
        "dietary_tags": ["halal"],
        "rating": 4.5,
        "price_level": 2,
        "address": "Irvine, CA",
        "lat": 33.64,
        "lng": -117.84,
        "hours_text": "Mon–Sun 11am–9pm",
        "source": "yelp",
        "review_count": 210,
        "phone": null,
        "menu_text": null,
        "cuisines": ["Mediterranean"],
        "categories": ["Restaurant"]
      },
      "score": 0.93,
      "why": [
        "Matches dietary_required: halal",
        "Within max_distance_miles",
        "Price level <= price_max"
      ]
    }
  ]
}

---

### Example 3: user_location + vegetarian + taiwanese + query_text

#### Request
{
  "user_location": { "lat": 33.641, "lng": -117.844 },
  "use_campus_center": false,
  "dietary_required": ["vegetarian"],
  "cuisines_optional": ["taiwanese"],
  "max_distance_miles": 4.0,
  "price_max": 3,
  "query_text": "boba",
  "top_k": 5
}

#### Response (200)
{
  "results": [
    {
      "restaurant": {
        "id": "example_boba_1",
        "name": "Example Boba Cafe",
        "dietary_tags": ["vegetarian"],
        "rating": 4.2,
        "price_level": 2,
        "address": "Irvine, CA",
        "lat": 33.641,
        "lng": -117.844,
        "hours_text": "Mon–Sun 10am–10pm",
        "source": "google",
        "review_count": 540,
        "phone": null,
        "menu_text": "Milk tea, fruit tea, light snacks",
        "cuisines": ["Taiwanese"],
        "categories": ["Cafe"]
      },
      "score": 0.9,
      "why": [
        "Matches dietary_required: vegetarian",
        "Query matches: boba",
        "Within max_distance_miles"
      ]
    }
  ]
}

---

### Example 4: campus center + gluten_free + mexican preference

#### Request
{
  "use_campus_center": true,
  "dietary_required": ["gluten_free"],
  "cuisines_optional": ["mexican"],
  "max_distance_miles": 1.5,
  "price_max": 2,
  "top_k": 5
}

#### Response (200)
{
  "results": [
    {
      "restaurant": {
        "id": "example_glutenfree_1",
        "name": "Example Tacos",
        "dietary_tags": ["gluten_free"],
        "rating": 4.1,
        "price_level": 2,
        "address": "Irvine, CA",
        "lat": 33.64,
        "lng": -117.842,
        "hours_text": "Mon–Fri 11am–8pm",
        "source": "manual",
        "review_count": null,
        "phone": null,
        "menu_text": null,
        "cuisines": ["Mexican"],
        "categories": ["Fast Food"]
      },
      "score": 0.88,
      "why": [
        "Matches dietary_required: gluten_free",
        "Cuisine preference: mexican",
        "Within max_distance_miles"
      ]
    }
  ]
}

