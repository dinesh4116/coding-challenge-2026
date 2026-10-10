import io
import zipfile
from pathlib import Path

import pandas as pd

from data_loader import extract_snapshot_zip, load_pairs, resolve_snapshots, split_multi
from schemas import AdPair

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_ads.csv"


def test_sample_csv_loads():
    res = load_pairs(SAMPLE)
    assert not res.errors and len(res.pairs) == 7
    assert res.pairs[0].ad_headlines == ["Same-Day Approval", "Personal Loans from Northwind Credit"]


def test_alias_columns_and_numbered_columns():
    csv = "ID,Headline 1,Headline 2,Description,Final URL\nA1,One,Two,Desc here,https://x.test\n"
    res = load_pairs(csv.encode(), "t.csv")
    assert not res.errors
    p = res.pairs[0]
    assert (p.pair_id, p.ad_headlines, p.ad_descriptions, p.landing_page_url) == \
        ("A1", ["One", "Two"], ["Desc here"], "https://x.test")


def test_validation_errors_are_row_specific():
    csv = ("pair_id,ad_headlines,landing_page_url\n"
           "A,Good,https://x.test\n"
           "A,Dup,https://x.test\n"
           "B,,https://x.test\n"
           "C,Bad url,ftp://x.test\n")
    res = load_pairs(csv.encode(), "t.csv")
    assert [p.pair_id for p in res.pairs] == ["A"]
    joined = " ".join(res.errors)
    assert "Row 3" in joined and "duplicate" in joined and "Row 4" in joined and "no ad headline" in joined
    assert "Row 5" in joined and "http" in joined


def test_missing_required_column():
    res = load_pairs(b"pair_id,landing_page_url\nA,https://x.test\n", "t.csv")
    assert not res.pairs and "headlines" in res.errors[0]


def test_unsupported_and_corrupt_files():
    assert load_pairs(b"x", "t.pdf").errors
    assert load_pairs(b"not an excel file", "t.xlsx").errors


def test_excel_input(tmp_path):
    p = tmp_path / "ads.xlsx"
    pd.DataFrame({"pair_id": ["A"], "ad_headlines": ["H1 | H2"], "snapshot_file": ["a.html"]}).to_excel(p, index=False)
    res = load_pairs(p)
    assert not res.errors and res.pairs[0].ad_headlines == ["H1", "H2"]


def test_split_multi():
    assert split_multi("a | b\nc") == ["a", "b", "c"] and split_multi(None) == [] and split_multi(float("nan")) == []


def test_snapshot_matching(tmp_path):
    (tmp_path / "A.html").write_text("<p>a</p>")
    (tmp_path / "custom.htm").write_text("<p>c</p>")
    (tmp_path / "unused.html").write_text("<p>u</p>")
    pairs = [AdPair(pair_id="A", ad_headlines=["x"]),
             AdPair(pair_id="B", ad_headlines=["x"], snapshot_file="custom.htm"),
             AdPair(pair_id="C", ad_headlines=["x"]),
             AdPair(pair_id="D", ad_headlines=["x"], snapshot_file="../secret.html")]
    paths, errors, unused = resolve_snapshots(pairs, tmp_path)
    assert paths["A"].name == "A.html" and paths["B"].name == "custom.htm"
    assert paths["C"] is None and "No snapshot found" in errors["C"]
    assert paths["D"] is None and "outside" in errors["D"]
    assert unused == ["unused.html"]


def test_zip_bundle_extraction_blocks_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ok.html", "<p>fine</p>")
        z.writestr("../evil.html", "<p>bad</p>")
        z.writestr("run.exe", "nope")
    dest = tmp_path / "bundle"
    names = extract_snapshot_zip(buf.getvalue(), dest)
    assert names == ["ok.html"] and not (tmp_path / "evil.html").exists()
