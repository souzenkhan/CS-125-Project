CS 125 Project

Restaurant Recommendation System for UCI Students

Data Schema (Restaurant)

Naming convention: snake_case
Resource type: restaurant (one JSON object = one restaurant document)

Required fields:

- id (string) : unique identifier
- name (string)
- dietary_tags (array[string]) -- allowed: halal, vegan, pescatarian, vegetarian, gluten free (can modify later)
- rating (number 0-5)
- price_level (integer 1-4)
- address (string)
- lat (number)
- lng (number)
- hours_text (string)
- source (string) - allowed: manual, google, yelp
  (note about manual, could be a submitted entry from user, lets keep the main focus on google and yelp for now)

Optional fields:

- review_count (integer)
- phone (string)
- menu_text (string) - short summary (don't need full menu here)
- cuisines (array[string])
- categories (array[string]) -- ex: ["Cafe", "Fast Food"]

Example JSON object
{
"id": "moongoat_coffee",
"name": "MoonGoat Coffee",
"cuisines": ["American"],
"categories": ["Cafe", "Fast Food"],
"dietary_tags": ["vegan", "vegetarian"],
"rating": 4,
"price_level": 2,
"review_count": 1240,
"address": "5171 California Ave unit 100, Irvine, CA, 92617",
"lat": 33.64252214002005,
"lng": -117.83871802459163,
"hours_text": "Mon–Sun 6am–6pm",
"phone": "(949) 612-2875",
"source": "google"
}

Computed (not stored in JSON):

- distance_to_campus
- is_open_now

All restaurants must have a unique id

Missing optional fields should be set to null
