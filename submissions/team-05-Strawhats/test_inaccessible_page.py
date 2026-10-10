
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_404_page_is_not_scored():
    response = client.post(
        "/analyze",
        json={
            "ad_text": "Get approved on the same day.",
            "destination_url": "https://example.com/offer",
            "http_status": 404,
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["page_status"] == "inaccessible"
    assert result["http_status"] == 404
    assert result["score"] is None
    assert result["score_status"] == "unavailable"
    assert result["findings"] == []
    assert result["evidence_quotes"] == []
    assert result["destination_url"] == (
        "https://example.com/offer"
    )
    assert result["message"] == (
        "Landing page inaccessible — "
        "unable to assess message match."
    )
