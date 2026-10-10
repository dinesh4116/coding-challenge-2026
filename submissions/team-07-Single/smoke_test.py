"""Smoke tests for QueryPilot AI (hackathon demo safety net).

Run from the project folder:

    .venv\\Scripts\\python smoke_test.py

Covers:
1. End-to-end app execution via streamlit.testing.v1.AppTest (sample data).
2. CSV upload paths: valid file, missing columns, negative values, invalid
   numerics, empty file.
3. Search box with special characters, decision filtering, relevance terms.
4. Core pipeline logic (column normalization, aliases, triage rules,
   confidence bounds, relevance routing, low-evidence guardrails).
"""

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def load_core():
    """Import the pure functions from app.py without executing the UI."""
    with open(os.path.join(HERE, "app.py"), encoding="utf-8") as f:
        src = f.read()
    marker = "head_l, head_r = st.columns"
    core_src = src[: src.index(marker)]
    ns = {"__file__": os.path.join(HERE, "app.py"), "__name__": "qp_core"}
    exec(compile(core_src, os.path.join(HERE, "app_core"), "exec"), ns)
    return ns


def new_app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=90)


def errors(at):
    return " | ".join(str(e.value) for e in at.error)


def warnings_(at):
    return " | ".join(str(w.value) for w in at.warning)


def get_elem(at, kind, label):
    """Find a widget by label in main or sidebar."""
    pools = [getattr(at, kind, [])]
    try:
        pools.append(getattr(at.sidebar, kind, []))
    except Exception:
        pass
    for pool in pools:
        for el in pool:
            if getattr(el, "label", None) == label:
                return el
    available = [getattr(e, "label", "?") for p in pools for e in p]
    raise AssertionError(f"{kind} {label!r} not found; available: {available}")


def recommendations_table(at):
    for df_el in at.dataframe:
        value = df_el.value
        if isinstance(value, pd.DataFrame) and "decision" in value.columns:
            return value
    raise AssertionError("recommendations table not found")


def test_app_renders():
    at = new_app().run()
    assert not at.exception, f"app raised an exception: {at.exception}"
    assert len(at.dataframe) >= 2, "expected decision summary + recommendations tables"
    assert len(at.metric) >= 4, "expected KPI metric cards"
    assert len(at.download_button) >= 1, "expected a download button"
    assert errors(at) == "", f"unexpected error with sample data: {errors(at)}"
    # The sample must demonstrate all four statuses with default thresholds.
    for df_el in at.dataframe:
        value = df_el.value
        if isinstance(value, pd.DataFrame) and "Decision" in value.columns:
            counts = dict(zip(value["Decision"], value["Terms"]))
            assert counts.get("Promote", 0) >= 1, f"sample should yield a Promote example: {counts}"
            assert all(counts.get(d, 0) >= 1 for d in ("Block", "Ignore", "Review")), counts
            break
    else:
        raise AssertionError("decision summary table not found")
    print(f"[ok] sample data renders: {len(at.dataframe)} tables, {len(at.metric)} metric cards, all 4 statuses")


def test_upload_valid_csv():
    csv = (
        "search term,campaign name,ad group name,impressions,clicks,spend,conv,conv. value\n"
        '"buy crm software",Brand,Core,"1,200","80","$420.00",8,2400\n'
        "free crm template,Brand,Core,800,40,80,0,0\n"
    )
    at = new_app().run()
    at.file_uploader[0].upload("upload.csv", csv.encode("utf-8"), "text/csv").run()
    assert not at.exception, f"exception after upload: {at.exception}"
    assert errors(at) == "", f"unexpected errors: {errors(at)}"
    rec = recommendations_table(at)
    assert set(rec["query"]) == {"buy crm software", "free crm template"}, rec["query"].tolist()
    # Alias + currency normalization worked; rows triaged with reasons.
    assert rec["cost"].iloc[0] == 420.0 and rec["clicks"].iloc[0] == 80, rec.head()
    assert rec["reason"].str.len().gt(10).all()
    print("[ok] CSV upload: aliases, currency/commas, triage and reasons")


def test_upload_missing_column():
    at = new_app().run()
    at.file_uploader[0].upload(
        "bad.csv", b"query,clicks,conversions\nfoo,10,1\n", "text/csv"
    ).run()
    assert not at.exception, f"exception: {at.exception}"
    assert "Missing required columns" in errors(at), errors(at)
    print("[ok] missing-column CSV shows a helpful error")


def test_upload_negative_values():
    csv = (
        "query,campaign,ad_group,impressions,clicks,cost,conversions,conversion_value\n"
        "buy crm software,Brand,Core,100,10,-50,1,100\n"
    )
    at = new_app().run()
    at.file_uploader[0].upload("neg.csv", csv.encode("utf-8"), "text/csv").run()
    assert not at.exception, f"exception: {at.exception}"
    assert "Negative metric values" in errors(at), errors(at)
    print("[ok] negative metrics rejected with clear error")


def test_upload_invalid_numbers():
    csv = (
        "query,campaign,ad_group,impressions,clicks,cost,conversions,conversion_value\n"
        "buy crm software,Brand,Core,100,ten,fifty,1,100\n"      # invalid -> row dropped
        "free crm template,Brand,Core,800,40,80,0,0\n"           # valid -> kept
    )
    at = new_app().run()
    at.file_uploader[0].upload("junk.csv", csv.encode("utf-8"), "text/csv").run()
    assert not at.exception, f"exception: {at.exception}"
    assert "invalid metrics are removed" in warnings_(at), warnings_(at)
    rec = recommendations_table(at)
    assert list(rec["query"]) == ["free crm template"], rec["query"].tolist()
    print("[ok] invalid numeric rows warned and dropped, valid rows kept")


def test_upload_empty_file():
    at = new_app().run()
    at.file_uploader[0].upload("empty.csv", b"", "text/csv").run()
    assert not at.exception, f"exception: {at.exception}"
    assert "empty" in errors(at).lower(), errors(at)
    print("[ok] empty CSV handled without a traceback")


def test_search_and_filters():
    at = new_app().run()
    # Special characters must not crash the search (literal substring match).
    get_elem(at, "text_input", "Search query text").set_value("( free $").run()
    assert not at.exception, f"exception on special-char search: {at.exception}"
    get_elem(at, "text_input", "Search query text").set_value("project").run()
    assert not at.exception
    rec = recommendations_table(at)
    assert rec["query"].str.contains("project", case=False).all()

    get_elem(at, "multiselect", "Filter decisions").set_value(["Block"]).run()
    assert not at.exception, f"exception on filter: {at.exception}"
    rec = recommendations_table(at)
    assert set(rec["decision"]) == {"Block"}, rec["decision"].unique().tolist()
    print("[ok] search (incl. special chars) and decision filter")


def test_relevance_terms():
    at = new_app().run()
    get_elem(at, "text_input", "Product/service terms (optional)").set_value("crm").run()
    assert not at.exception, f"exception with relevance terms: {at.exception}"
    rec = recommendations_table(at)
    assert "Possible relevance mismatch" in set(rec["signal"]), rec["signal"].unique().tolist()
    print("[ok] relevance terms route non-matching queries to Review")


def test_numeric_coercion_pattern():
    # Same cleaning expression app.py uses: commas/currency/spaces tolerated, junk -> NaN.
    s = pd.Series(["1,234.50", "$50", " 12 ", "abc", ""])
    cleaned = pd.to_numeric(s.str.strip().str.replace(r"[,$\s]", "", regex=True), errors="coerce")
    assert cleaned.iloc[0] == 1234.5 and cleaned.iloc[1] == 50.0 and cleaned.iloc[2] == 12
    assert np.isnan(cleaned.iloc[3]) and np.isnan(cleaned.iloc[4])
    print("[ok] numeric coercion handles currency/commas and rejects junk")


def test_normalization_and_aliases(ns):
    normalize_columns, REQUIRED = ns["normalize_columns"], ns["REQUIRED"]
    raw = pd.DataFrame(
        {
            "Search Term": ["buy crm software"],
            "Campaign Name": ["Brand"],
            "Ad Group_Name": ["Core"],
            "Impressions": [1200],
            "Clicks": [80],
            "Spend": [420],
            "Conv": [8],
            "Conv. Value": [2400],
        }
    )
    df = normalize_columns(raw)
    missing = [c for c in REQUIRED if c not in df.columns]
    assert not missing, f"aliases should satisfy required columns, missing: {missing}"

    # Duplicate columns that normalize to the same target must not crash later steps.
    dup = pd.DataFrame({"cost": [1], "spend": [2], "query": ["a"], "search term": ["b"]})
    out = normalize_columns(dup)
    assert list(out.columns).count("cost") == 1
    assert list(out.columns).count("query") == 1
    print("[ok] column normalization + aliases + duplicate handling")


def test_triage_rules(ns):
    run_triage, normalize_columns = ns["run_triage"], ns["normalize_columns"]
    rows = [
        # strong converters within target CPA -> Promote
        dict(query="buy crm software", campaign="C", ad_group="G",
             impressions=1200, clicks=80, cost=380, conversions=8, conversion_value=2400),
        # likely irrelevant intent -> Block
        dict(query="free project management template", campaign="C", ad_group="G",
             impressions=800, clicks=40, cost=80, conversions=0, conversion_value=0),
        # low evidence -> Ignore (never a confident call)
        dict(query="team planning software", campaign="C", ad_group="G",
             impressions=50, clicks=2, cost=1.5, conversions=0, conversion_value=0),
        # spend without conversions -> Review
        dict(query="cheap project tracker", campaign="C", ad_group="G",
             impressions=700, clicks=18, cost=90, conversions=0, conversion_value=0),
    ]
    df = normalize_columns(pd.DataFrame(rows))
    result = run_triage(df, target_cpa=50.0, min_clicks=10, min_spend=30.0, relevance_terms=[])

    decisions = dict(zip(result["query"], result["decision"]))
    assert decisions["buy crm software"] == "Promote", decisions
    assert decisions["free project management template"] == "Block", decisions
    assert decisions["team planning software"] == "Ignore", decisions
    assert decisions["cheap project tracker"] == "Review", decisions
    signals = dict(zip(result["query"], result["signal"]))
    assert signals["cheap project tracker"] == "Spend without conversions", signals

    assert result["confidence"].between(0.0, 1.0).all(), "confidence must stay within [0, 1]"
    assert result["reason"].str.len().gt(10).all(), "every row needs a human-readable reason"
    assert result["signal"].notna().all()

    # Relevance terms must route non-matching queries to Review, not a confident call.
    rel = run_triage(df, 50.0, 10, 30.0, ["crm"])
    rel_signals = dict(zip(rel["query"], rel["signal"]))
    assert rel_signals["buy crm software"] and dict(zip(rel["query"], rel["decision"]))["buy crm software"] == "Promote"
    assert rel_signals["cheap project tracker"] == "Possible relevance mismatch", rel_signals
    print("[ok] triage rules: Promote/Block/Ignore/Review + confidence bounds + relevance routing")


def main():
    ns = load_core()
    test_numeric_coercion_pattern()
    test_normalization_and_aliases(ns)
    test_triage_rules(ns)
    test_app_renders()
    test_upload_valid_csv()
    test_upload_missing_column()
    test_upload_negative_values()
    test_upload_invalid_numbers()
    test_upload_empty_file()
    test_search_and_filters()
    test_relevance_terms()
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
