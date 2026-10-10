import pytest
from decision_engine import DecisionEngine


@pytest.fixture
def engine():
    return DecisionEngine({
        "business_name": "Test Laptop Store",
        "product_description": "Selling laptops and accessories",
        "relevant_intents": ["buy laptop", "laptop price"],
        "irrelevant_intents": ["free laptop wallpaper", "repair manual"],
        "negative_keywords": ["free", "torrent", "repair manual"],
        "min_clicks_threshold": 10,
        "min_cost_threshold": 15.0
    })

def test_clear_irrelevant_block(engine):
    row = {
        "query_text": "download free laptop wallpaper",
        "campaign": "Laptop Sales",
        "ad_group": "Gaming Laptops",
        "clicks": 15,
        "cost": 12.50,
        "conversions": 0
    }
    res = engine.evaluate_row(row)
    assert res["decision"] == "BLOCK"
    assert res["confidence"] == "HIGH"
    assert "free" in res["explanation"].lower()

def test_high_performance_promote(engine):
    row = {
        "query_text": "buy dell laptop online",
        "campaign": "Laptop Sales",
        "ad_group": "Gaming Laptops",
        "clicks": 25,
        "cost": 45.00,
        "conversions": 3,
        "conversion_value": 450.00
    }
    res = engine.evaluate_row(row)
    assert res["decision"] == "PROMOTE"
    assert res["confidence"] == "HIGH"
    assert "conversions" in res["explanation"].lower()

def test_ambiguous_low_volume_ignore(engine):
    row = {
        "query_text": "laptop screen resolution specs",
        "campaign": "Laptop Sales",
        "ad_group": "Gaming Laptops",
        "clicks": 0,
        "cost": 0.0,
        "conversions": 0
    }
    res = engine.evaluate_row(row)
    assert res["decision"] == "IGNORE"

def test_ambiguous_human_review(engine):
    row = {
        "query_text": "dell laptop vs hp comparison",
        "campaign": "Laptop Sales",
        "ad_group": "Gaming Laptops",
        "clicks": 5,
        "cost": 10.00,
        "conversions": 0
    }
    res = engine.evaluate_row(row)
    assert res["decision"] == "HUMAN REVIEW"
    assert res["review_required"] is True


def test_empty_query_text(engine):
    row = {
        "query_text": "",
        "clicks": 5,
        "cost": 10.0
    }
    res = engine.evaluate_row(row)
    assert res["decision"] == "HUMAN REVIEW"
    assert res["review_required"] is True

def test_zero_conversions_never_blindly_blocked(engine):
    # Relevant search with low clicks and 0 conversions should NOT be blindly blocked
    row = {
        "query_text": "buy high end gaming laptop",
        "campaign": "Laptop Sales",
        "ad_group": "Gaming Laptops",
        "clicks": 2,
        "cost": 5.00,
        "conversions": 0
    }
    res = engine.evaluate_row(row)
    assert res["decision"] != "BLOCK"

def test_batch_processing(engine):
    data = [
        {"query_text": "buy lenovo laptop", "clicks": 10, "cost": 20.0, "conversions": 1},
        {"query_text": "free crack laptop software", "clicks": 5, "cost": 5.0, "conversions": 0},
    ]
    out = engine.process_records(data)
    assert len(out) == 2
    assert "decision" in out[0]
    assert "explanation" in out[0]

