import json
from fastapi.testclient import TestClient

import server.app as appmod


def test_personalization_clicks_boost_mexican(tmp_path):
    restaurants = [
        {
            "id": "ita1",
            "name": "Italian Place",
            "dietary_tags": ["vegetarian"],
            "rating": 4.0,
            "price_level": 2,
            "address": "A",
            "lat": 33.6405,
            "lng": -117.8443,
            "hours_text": "Mon–Sun 10am–10pm",
            "source": "manual",
            "menu_text": "Same neutral menu text for both restaurants so tfidf ties.",
            "cuisines": ["Italian"],
            "categories": ["Restaurant"],
        },
        {
            "id": "mex1",
            "name": "Mexican Place",
            "dietary_tags": ["vegetarian"],
            "rating": 4.0,
            "price_level": 2,
            "address": "B",
            "lat": 33.6405,
            "lng": -117.8443,
            "hours_text": "Mon–Sun 10am–10pm",
            "source": "manual",
            "menu_text": "Same neutral menu text for both restaurants so tfidf ties.",
            "cuisines": ["Mexican"],
            "categories": ["Restaurant"],
        },
    ]

    data_path = tmp_path / "restaurants.json"
    data_path.write_text(json.dumps(restaurants, indent=2), encoding="utf-8")

    # Point app to temp data and rebuild TF-IDF
    appmod.DATA_PATH = data_path
    client = TestClient(appmod.app)
    appmod.USER_PROFILES.clear()

    refresh = client.post("/refresh")
    assert refresh.status_code == 200

    user_id = "u1"

    # baseline recommendation (no clicks yet) 
    baseline = client.post("/recommend", json={"user_id": user_id, "query": "food", "top_k": 2})
    assert baseline.status_code == 200
    base_list = baseline.json()
    base_ids = [r["id"] for r in base_list]

    # With tied scores, stable sort keeps ita1 first
    assert base_ids[0] == "ita1"
    assert base_ids[1] == "mex1"

    #simulate user clicking Mexican twice 
    for _ in range(2):
        c = client.post("/click", json={"user_id": user_id, "restaurant_id": "mex1"})
        assert c.status_code == 200

    # recommendation after clicks 
    after = client.post("/recommend", json={"user_id": user_id, "query": "food", "top_k": 2})
    assert after.status_code == 200
    after_list = after.json()
    after_ids = [r["id"] for r in after_list]

    assert after_ids[0] == "mex1", "Mexican should be boosted to the top after 2 clicks"