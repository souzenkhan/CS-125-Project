import pytest
from fastapi.testclient import TestClient
from server.app import app   # adjust if your file name is different

client = TestClient(app)

#test 1: Ranking Sorted Descending
def test_results_sorted_by_score_descending():
    response = client.post("/recommend", json={
        "query": "burgers",
        "halal": False,
        "vegan": False
    })

    assert response.status_code == 200
    results = response.json()

    assert len(results) > 1

    scores = [r["score"] for r in results]

    assert scores == sorted(scores, reverse=True)


#test 2: Dietary Filter Removes Invalid Options
def test_halal_filter_removes_non_halal():
    response = client.post("/recommend", json={
        "query": "",
        "halal": True,
        "vegan": False
    })

    assert response.status_code == 200
    results = response.json()

    for r in results:
        assert "halal" in (r.get("dietary_tags") or [])

#test 3: Query Sensitivity Changes Ranking
def test_query_changes_top_result():
    response1 = client.post("/recommend", json={
        "query": "pizza",
        "halal": False,
        "vegan": False
    })

    response2 = client.post("/recommend", json={
        "query": "sushi",
        "halal": False,
        "vegan": False
    })

    assert response1.status_code == 200
    assert response2.status_code == 200

    results1 = response1.json()
    results2 = response2.json()

    assert len(results1) > 0
    assert len(results2) > 0

    top1 = results1[0]["name"]
    top2 = results2[0]["name"]

    assert top1 != top2
