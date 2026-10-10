from parser import parse_html
from schemas import RawFinding
from verifier import verify_findings, verify_quote

LONG = " ".join(["Filler sentence to make the snapshot look complete."] * 5)
HTML = f"""<body><header class="hero"><h1>Fast Loans</h1><p>{LONG}</p></header>
<main><p>Rates start at 5.9% APR for qualified borrowers.</p></main>
<footer><p>Same-day approval is available for eligible applicants.</p></footer></body>"""


def page():
    return parse_html(HTML)


def raw(status, quote, **kw):
    return RawFinding(claim="c", status=status, evidence_quote=quote, mismatch_type="timing", **kw)


def test_exact_quotation_verified_with_location():
    p = page()
    f = verify_findings([raw("supported", "Rates start at 5.9% APR")], p)[0]
    assert f.evidence_verified and f.status == "supported"
    assert f.evidence_quote == "Rates start at 5.9% APR"        # original preserved
    assert f.source_section == "main" and f.document_order == 3 and f.source_block_id == "block_003"


def test_unicode_and_case_normalised_but_quote_not_rewritten():
    p = parse_html("<main><p>It\u2019s the \u201cBest\u201d plan available today, honestly.</p></main>")
    q = "it's the \"best\" plan"
    f = verify_findings([raw("supported", q)], p)[0]
    assert f.evidence_verified and f.evidence_quote == q


def test_fabricated_quotation_rejected():
    f = verify_findings([raw("contradicted", "Approval takes 30 business days")], page())[0]
    assert not f.evidence_verified and f.evidence_quote is None
    assert f.status == "uncertain" and f.needs_human_review
    assert f.unverified_quote == "Approval takes 30 business days"


def test_quote_spanning_two_blocks_rejected():
    p = page()
    assert not verify_quote("Fast Loans " + LONG[:20], p.blocks).verified


def test_missing_claim_has_no_invented_quote():
    f = verify_findings([raw("missing", "Some invented proof")], page())[0]
    assert f.status == "missing" and f.evidence_quote is None and not f.evidence_verified
    assert "not found in the inspected page content" in f.explanation
    assert f.unverified_quote == "Some invented proof"


def test_supported_without_quote_becomes_uncertain():
    f = verify_findings([raw("supported", None)], page())[0]
    assert f.status == "uncertain" and f.needs_human_review


def test_footer_vs_hero_position_concern():
    p = page()
    foot = verify_findings([raw("supported", "Same-day approval is available")], p)[0]
    hero = verify_findings([raw("supported", "Fast Loans")], p)[0]
    assert foot.source_section == "footer" and foot.position_concern
    assert hero.source_section == "hero" and not hero.position_concern


def test_incomplete_snapshot_makes_missing_uncertain():
    p = parse_html("<p>Tiny page</p>")
    assert not p.snapshot_complete
    f = verify_findings([raw("missing", None)], p)[0]
    assert f.status == "uncertain" and f.needs_human_review
