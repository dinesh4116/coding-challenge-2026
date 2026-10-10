from schemas import Finding, ParsedPage
from scoring import ScoringConfig, compute_confidence, compute_score


def F(status="contradicted", mt="pricing", sev="high", verified=True, section="main", pos=False):
    return Finding(claim="c", mismatch_type=mt, status=status, severity=sev, evidence_verified=verified,
                   source_section=section, position_concern=pos)


def test_no_discrepancies_scores_100():
    score, dims = compute_score([F("supported", sev="none")])
    assert score == 100.0 and all(v == 100.0 for v in dims.values())


def test_verified_contradiction_penalty_and_weights():
    # pricing dimension 100-50=50, weight 20% -> 100 - 0.2*50 = 90
    score, dims = compute_score([F()])
    assert dims["pricing_timing_eligibility"] == 50.0 and score == 90.0


def test_unverified_contradiction_is_not_penalised():
    score, _ = compute_score([F(verified=False), F("supported", sev="none")])
    assert score == 100.0


def test_missing_penalty_uses_multiplier():
    score, dims = compute_score([F("missing", mt="offer", sev="medium", verified=False)])
    assert dims["main_offer"] == 80.0 and score == 94.0       # 25*0.8=20 -> 30%*20=6


def test_footer_support_scores_lower_than_hero_support():
    hero, _ = compute_score([F("supported", sev="none", section="hero")])
    footer, d = compute_score([F("supported", sev="none", section="footer", pos=True)])
    assert hero == 100.0 and footer == 94.0 and d["prominence"] == 40.0   # 100-60, 10% weight


def test_not_evaluable_returns_none():
    assert compute_score([])[0] is None
    assert compute_score([F("uncertain", verified=False)])[0] is None


def test_custom_weights_normalised():
    cfg = ScoringConfig(weights={"main_offer": 1, "features_benefits": 1, "pricing_timing_eligibility": 1,
                                 "cta": 1, "prominence": 1})
    score, _ = compute_score([F()], cfg)
    assert score == 90.0           # 100 - 50/5


def test_confidence_is_separate_and_penalises_gaps():
    from parser import parse_html
    good = parse_html("<main><h1>Title</h1><p>" + "Real content here. " * 20 + "</p></main>")
    f = [F("supported", sev="none")]
    assert compute_confidence(f, good, "ok") == 1.0
    assert compute_confidence(f, good, "unavailable") == 0.75
    assert compute_confidence(f, ParsedPage(), "ok") == 0.0
    assert compute_confidence([F("uncertain", verified=False)], good, "ok") == 0.7
