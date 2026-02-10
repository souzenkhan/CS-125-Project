from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert ("status" in body and str(body["status"]).lower() == "ok") or ("ok" in body)

def test_recommend_returns_list():
    payload = {
        "use_campus_center": True,
        "dietary_required": ["vegetarian"],
        "cuisines_optional": [],
        "max_distance_miles": 3.0,
        "price_max": 4,
        "top_k": 5,
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)

def test_dietary_filter_works():
    payload = {
        "use_campus_center": True,
        "dietary_required": ["vegetarian"],
        "cuisines_optional": [],
        "max_distance_miles": 10.0,
        "price_max": 4,
        "top_k": 10,
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 200
    results = r.json().get("results", [])
    for item in results:
        tags = item["restaurant"].get("dietary_tags", [])
        assert "vegetarian" in tags
