from parser import normalize_text, parse_html

HTML = """<html><head><title>  Demo   Page </title><style>.a{}</style><script>var x='Secret';</script></head>
<body><header class="hero"><h1>Get approved in minutes</h1><p>Simple online <b>application</b>.</p>
<a class="btn" href="#">Apply Now</a></header>
<main><section class="features"><h2>Features</h2><ul><li>Fast</li><li>Secure</li></ul></section>
<section class="pricing"><h2>Pricing</h2><p>Only $29/month</p></section>
<section id="faq"><h2>FAQ</h2><p>Is it free? No.</p></section></main>
<footer><p>Terms apply.</p><div hidden>Hidden text</div></footer></body></html>"""


def by_text(page, text):
    return next(b for b in page.blocks if b.text == text)


def test_valid_html_extraction_and_cleanup():
    page = parse_html(HTML, url="https://x.test")
    assert page.title == "Demo Page"
    texts = [b.text for b in page.blocks]
    assert "Get approved in minutes" in texts and "Simple online application." in texts
    assert not any("Secret" in t or "Hidden" in t for t in texts)
    assert [b.document_order for b in page.blocks] == list(range(1, len(page.blocks) + 1))
    assert page.blocks[0].block_id == "block_001" and page.blocks[0].source_path.endswith("h1[1]")


def test_no_duplicate_text_from_nested_containers():
    page = parse_html("<div><p>Hello <a href='#'>world</a></p><ul><li>One</li></ul></div>")
    texts = [b.text for b in page.blocks]
    assert texts == ["Hello world", "One"]


def test_section_classification():
    page = parse_html(HTML)
    assert by_text(page, "Get approved in minutes").section == "hero"
    assert by_text(page, "Fast").section == "features"
    assert by_text(page, "Only $29/month").section == "pricing"
    assert by_text(page, "Is it free? No.").section == "faq"
    assert by_text(page, "Terms apply.").section == "footer"
    assert "pricing" in by_text(page, "Only $29/month").labels
    assert by_text(page, "Apply Now").kind == "link"


def test_unknown_section_is_not_guessed():
    page = parse_html("<div><div>Welcome to our shop where we sell lamps</div></div>")
    b = page.blocks[0]
    assert b.section == "unknown" and b.section_confidence == "low"
    assert b.above_the_fold is None          # HTML alone never proves 'above the fold'


def test_original_and_normalized_text_kept_separately():
    page = parse_html("<p>It\u2019s   a \u201cGreat\u201d Deal</p>")
    b = page.blocks[0]
    assert b.text == "It\u2019s a \u201cGreat\u201d Deal"
    assert b.normalized_text == normalize_text("It's a \"great\" deal") == "it's a \"great\" deal"


def test_incomplete_snapshots_detected():
    assert parse_html("").snapshot_complete is False
    shell = parse_html("<html><body><div id='root'></div><script src='a.js'></script></body></html>")
    assert shell.snapshot_complete is False and shell.blocks == []
    assert parse_html(HTML).snapshot_complete is False   # short demo page: <150 chars


def test_layout_metadata_sets_above_the_fold():
    page = parse_html("<main><h1>Top</h1><p>Low</p></main>")
    layout = {"viewport_height": 800, "elements": {page.blocks[0].source_path: {"top": 100},
                                                    page.blocks[1].source_path: {"top": 2000}}}
    page2 = parse_html("<main><h1>Top</h1><p>Low</p></main>", layout=layout)
    assert [b.above_the_fold for b in page2.blocks] == [True, False] and page2.layout_used
