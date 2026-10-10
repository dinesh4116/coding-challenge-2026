"""Streamlit dashboard: Ad-to-Landing-Page Message Match Auditor.

Run:  streamlit run app.py
This app only AUDITS and RECOMMENDS. It never changes a Google Ads account.
"""
import logging
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import exports
from auditor import DEFAULT_HOST, DEFAULT_MODEL, OllamaLLM, audit_batch
from data_loader import extract_snapshot_zip, load_pairs, resolve_snapshots
from schemas import STATUSES

BASE = Path(__file__).resolve().parent
(BASE / "outputs").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    handlers=[logging.FileHandler(BASE / "outputs" / "audit.log", encoding="utf-8"),
                              logging.StreamHandler()])

st.set_page_config(page_title="Ad Message Match Auditor", page_icon="🎯", layout="wide")
ss = st.session_state
for key, default in [("results", []), ("reviews", {}), ("pairs", []), ("load_errors", []),
                     ("load_warnings", []), ("snap_dir", str(BASE / "data" / "snapshots"))]:
    ss.setdefault(key, default)

# ------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    use_llm = st.checkbox("Use Ollama AI analysis", value=True,
                          help="Off = rule-based checks only (price, timing, call-to-action).")
    model = st.text_input("Ollama model", DEFAULT_MODEL)
    host = st.text_input("Ollama host", DEFAULT_HOST)
    if st.button("Test Ollama connection"):
        ok, msg = OllamaLLM(model, host).health()
        (st.success if ok else st.error)(msg)
    fetch_live = st.checkbox("Allow live URL fetching (optional)", value=False,
                             help="Only used for pairs with no offline snapshot. Public http/https URLs only.")
    st.caption("Offline snapshots are the default. Live results are labelled 'live_fetch'.")
    st.info("Audit only: this tool never modifies a Google Ads account.")

st.title("🎯 Ad-to-Landing-Page Message Match Auditor")
st.caption("Position-aware auditing: where on the page does the evidence appear?")
tab_over, tab_up, tab_res, tab_rev, tab_exp = st.tabs(
    ["Overview", "Upload & process", "Audit results", "Human review", "Export"])

results = ss.results

# ------------------------------------------------------------------ overview
with tab_over:
    scores = [r.match_score for r in results if r.match_score is not None]
    high = sum(1 for r in results for f in r.findings if f.severity == "high" and f.status != "supported")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pairs processed", len(results))
    c2.metric("Average match score", f"{sum(scores) / len(scores):.1f}" if scores else "-")
    c3.metric("High-severity findings", high)
    c4.metric("Pairs requiring review", sum(r.needs_human_review for r in results))
    if results:
        df = pd.DataFrame({"pair_id": [r.pair_id for r in results],
                           "match_score": [r.match_score or 0 for r in results]}).set_index("pair_id")
        st.bar_chart(df)
        st.caption("Pairs with no score (not evaluated) are drawn as 0 here; see the results tab.")
    else:
        st.info("No results yet. Go to **Upload & process**.")

# ------------------------------------------------------------ upload & process
with tab_up:
    st.subheader("1. Ad/page pairs")
    up = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xls"])
    cA, cB = st.columns(2)
    if up is not None and cA.button("Load uploaded file", type="primary"):
        res = load_pairs(up.getvalue(), up.name)
        ss.pairs, ss.load_errors, ss.load_warnings = res.pairs, res.errors, res.warnings
    if cB.button("Load bundled sample data"):
        res = load_pairs(BASE / "data" / "sample_ads.csv")
        ss.pairs, ss.load_errors, ss.load_warnings = res.pairs, res.errors, res.warnings
        ss.snap_dir = str(BASE / "data" / "snapshots")
    for e in ss.load_errors:
        st.error(e)
    for w in ss.load_warnings:
        st.warning(w)

    st.subheader("2. Offline snapshots")
    zup = st.file_uploader("Snapshot bundle (.zip of .html files) - optional", type=["zip"])
    if zup is not None and st.button("Use uploaded bundle"):
        dest = tempfile.mkdtemp(prefix="snapshots_")
        names = extract_snapshot_zip(zup.getvalue(), dest)
        ss.snap_dir = dest
        st.success(f"Extracted {len(names)} file(s).")
    ss.snap_dir = st.text_input("Snapshot folder", ss.snap_dir)

    if ss.pairs:
        paths, errs, unused = resolve_snapshots(ss.pairs, ss.snap_dir)
        table = pd.DataFrame([{"pair_id": p.pair_id, "headlines": " | ".join(p.ad_headlines),
                               "snapshot": paths[p.pair_id].name if paths[p.pair_id] else "NOT FOUND",
                               "problem": errs.get(p.pair_id, "")} for p in ss.pairs])
        st.dataframe(table, use_container_width=True, hide_index=True)
        if errs:
            st.warning(f"{len(errs)} pair(s) have no matching snapshot"
                       + (" (live fetching is enabled and will be tried)." if fetch_live else
                          " and will be reported as failed."))
        if unused:
            st.info("Snapshot files not used by any pair: " + ", ".join(unused))

        st.subheader("3. Run")
        if st.button("Run audit", type="primary"):
            llm = OllamaLLM(model, host) if use_llm else None
            bar = st.progress(0.0, text="Starting...")
            ss.results = audit_batch(
                ss.pairs, ss.snap_dir, llm=llm, fetch_live=fetch_live,
                progress=lambda i, n, pid: bar.progress(i / n, text=f"Audited {pid} ({i}/{n})"))
            ss.reviews = {}
            bar.empty()
            st.success(f"Audited {len(ss.results)} pair(s). Open the results tab.")
            st.rerun()

# ------------------------------------------------------------------- results
with tab_res:
    if not results:
        st.info("Run an audit first.")
    else:
        st.subheader("Audited pairs")
        pair_df = pd.DataFrame([{
            "pair_id": r.pair_id, "match_score": r.match_score, "audit_confidence": r.audit_confidence,
            "status": r.audit_status, "needs_review": r.needs_human_review, "findings": len(r.findings),
            "source": r.source_type, "summary": r.summary} for r in results])
        st.dataframe(pair_df, use_container_width=True, hide_index=True)

        st.subheader("Findings")
        rows = [x for x in exports.results_to_rows(results, ss.reviews) if x.get("claim")]
        fdf = pd.DataFrame(rows)
        if not fdf.empty:
            f1, f2, f3, f4 = st.columns(4)
            sev = f1.multiselect("Severity", ["high", "medium", "low", "none"])
            mt = f2.multiselect("Mismatch type", sorted(fdf["mismatch_type"].unique()))
            stt = f3.multiselect("Status", STATUSES)
            rev = f4.selectbox("Human review", ["all", "needs review", "no review needed"])
            view = fdf
            if sev:
                view = view[view["severity"].isin(sev)]
            if mt:
                view = view[view["mismatch_type"].isin(mt)]
            if stt:
                view = view[view["status"].isin(stt)]
            if rev != "all":
                view = view[view["needs_human_review"] == (rev == "needs review")]
            st.dataframe(view[["pair_id", "status", "severity", "mismatch_type", "claim", "source_section",
                               "evidence_verified", "needs_human_review"]],
                         use_container_width=True, hide_index=True)

        st.subheader("Pair details")
        pid = st.selectbox("Pair", [r.pair_id for r in results], key="detail_pair")
        r = next(x for x in results if x.pair_id == pid)
        left, right = st.columns(2)
        with left:
            st.markdown("**Ad copy**")
            for h in r.ad_headlines:
                st.markdown(f"- 📰 **{h}**")
            for d in r.ad_descriptions:
                st.markdown(f"- {d}")
            if r.landing_page_url:
                st.caption(f"Landing page URL: {r.landing_page_url}")
        with right:
            st.markdown("**Audit**")
            st.write(f"Match score: **{r.match_score if r.match_score is not None else 'not evaluated'}** | "
                     f"Audit confidence: **{r.audit_confidence:.0%}** | Source: {r.source_type}")
            st.write(r.summary)
            for reason in r.review_reasons:
                st.warning(reason)
            if r.dimension_scores:
                st.caption("Dimension scores: " + ", ".join(f"{k}={v}" for k, v in r.dimension_scores.items()))
        for i, f in enumerate(r.findings):
            icon = {"supported": "✅", "partial": "🟡", "missing": "⚪", "contradicted": "🔴", "uncertain": "❔"}[f.status]
            with st.expander(f"{icon} {f.status.upper()} | {f.severity} | {f.mismatch_type} | {f.claim}"):
                if f.evidence_verified:
                    st.markdown("**Verified evidence quotation (exact text from the page):**")
                    st.code(f.evidence_quote, language=None)
                    st.caption(f"Section: {f.source_section} | block {f.source_block_id} | document order {f.document_order}")
                elif f.unverified_quote:
                    st.error("Rejected: the model's quotation was NOT found in the page text.")
                    st.code(f.unverified_quote, language=None)
                else:
                    st.caption("No quotation (claim not found in the inspected content, or no evidence).")
                st.write(f.explanation)
                if f.position_concern:
                    st.warning(f.position_note)
                st.markdown(f"**Recommended fix:** {f.recommended_fix}")
                if f.needs_human_review:
                    st.info("Needs human review: " + "; ".join(f.review_reasons))

# -------------------------------------------------------------- human review
with tab_rev:
    if not results:
        st.info("Run an audit first.")
    else:
        with_f = [r for r in results if r.findings]
        pid = st.selectbox("Pair", [r.pair_id for r in with_f], key="rev_pair") if with_f else None
        if pid:
            r = next(x for x in with_f if x.pair_id == pid)
            idx = st.selectbox("Finding", range(len(r.findings)), key="rev_idx",
                               format_func=lambda i: f"{i}: {r.findings[i].status} - {r.findings[i].claim}")
            f = r.findings[idx]
            st.write(f"**Claim:** {f.claim}")
            if f.evidence_quote:
                st.code(f.evidence_quote, language=None)
            st.write(f.explanation)
            key = exports.review_key(pid, idx)
            cur = ss.reviews.get(key, {})
            decision = st.radio("Decision", ["pending", "accepted", "rejected"], horizontal=True,
                                index=["pending", "accepted", "rejected"].index(cur.get("decision", "pending")),
                                key=f"dec_{key}")
            opts = ["(keep)"] + STATUSES
            corrected = st.selectbox("Correct the status", opts, key=f"st_{key}",
                                     index=opts.index(cur.get("corrected_status") or "(keep)"))
            notes = st.text_area("Reviewer notes", cur.get("notes", ""), key=f"nt_{key}")
            if st.button("Save review"):
                ss.reviews[key] = {"decision": decision, "notes": notes,
                                   "corrected_status": "" if corrected == "(keep)" else corrected}
                st.success("Review saved.")
        if ss.reviews:
            st.subheader("Saved reviews")
            st.dataframe(pd.DataFrame([{"key": k, **v} for k, v in ss.reviews.items()]),
                         use_container_width=True, hide_index=True)

# -------------------------------------------------------------------- export
with tab_exp:
    if not results:
        st.info("Run an audit first.")
    else:
        st.write("Exports include any human review decisions you saved.")
        st.download_button("⬇ All results (CSV)", exports.to_csv_bytes(results, ss.reviews),
                           "audit_results.csv", "text/csv")
        st.download_button("⬇ Structured results (JSON)", exports.to_json_bytes(results, ss.reviews),
                           "audit_results.json", "application/json")
        fl = exports.fix_list(results, ss.reviews)
        st.download_button("⬇ Prioritised fix list (CSV)", fl.to_csv(index=False).encode("utf-8-sig"),
                           "fix_list.csv", "text/csv")
        st.dataframe(fl, use_container_width=True, hide_index=True)
        st.caption("These are recommendations only. Nothing has been changed in any Google Ads account.")
