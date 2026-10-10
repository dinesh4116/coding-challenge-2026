import io
import re
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="QueryPilot AI", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background:#0b1020; color:#f2f5fb; }
[data-testid="stHeader"] { background:rgba(11,16,32,.96); }
.block-container { max-width:1600px; padding-top:1.3rem; padding-bottom:2.5rem; }
section[data-testid="stSidebar"] { background:#0a0f1e; border-right:1px solid #1b2338; }
section[data-testid="stSidebar"] .block-container { padding-top:1.4rem; padding-left:1.1rem; padding-right:1.1rem; }
h1,h2,h3 { color:#f5f7fc !important; letter-spacing:-.03em; }
h1 { font-size:2rem !important; font-weight:800 !important; }
h2 { font-size:1.35rem !important; font-weight:700 !important; }
p,label { color:#9aa7bd; }
/* Metric strip */
[data-testid="stMetric"] { background:#141b2d; border:1px solid #232c42; border-radius:14px; padding:14px 16px; }
[data-testid="stMetricLabel"] { color:#8b96ad !important; }
[data-testid="stMetricValue"] { color:#f5f7fc !important; font-weight:800 !important; }
/* Cards */
.qp-card { background:#141b2d; border:1px solid #232c42; border-radius:16px; padding:18px 20px; min-height:125px; }
.qp-eyebrow { color:#8b96ad; font-size:.74rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.qp-big { color:#f5f7fc; font-size:2.05rem; font-weight:800; margin:7px 0; }
.qp-sub { color:#8b96ad; font-size:.82rem; }
.qp-hero { min-height:335px; }
.qp-hero-num { color:#f5f7fc; font-size:2.5rem; font-weight:800; line-height:1.05; margin:10px 0 6px; }
.qp-card-head { display:flex; align-items:center; gap:12px; }
.qp-check { width:40px; height:40px; border-radius:99px; background:rgba(56,214,165,.12); border:1px solid rgba(56,214,165,.35); color:#3dd598; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.05rem; flex:0 0 auto; }
.qp-pill { display:inline-block; border-radius:99px; padding:4px 10px; background:#12352d; color:#4fe0b0; font-size:.72rem; font-weight:700; }
.qp-pill-red { background:#3d1620; color:#ff8090; }
.qp-pill-grey { background:#1c2740; color:#9fb0ff; }
.qp-note { background:#101728; border:1px solid #232c42; border-radius:12px; padding:12px 14px; margin-top:16px; }
.qp-note-title { color:#e8edf8; font-size:.82rem; font-weight:700; }
.qp-note p { color:#8b96ad; font-size:.79rem; margin:5px 0 0; line-height:1.5; }
/* Decision-share bars */
.qp-bars { display:flex; flex-direction:column; gap:12px; margin-top:18px; }
.qp-bar-row { display:grid; grid-template-columns:72px 1fr 42px; gap:10px; align-items:center; font-size:.78rem; }
.qp-bar-name { color:#e8edf8; font-weight:600; }
.qp-bar-val { text-align:right; color:#e8edf8; font-weight:700; }
.qp-track { background:#0f1524; border:1px solid #232c42; border-radius:99px; height:9px; overflow:hidden; }
.qp-fill { height:100%; border-radius:99px; }
/* Sub-cards inside the block card */
.qp-subgrid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:16px; }
.qp-subcard { background:#101728; border:1px solid #232c42; border-radius:12px; padding:11px 13px; }
.qp-sub-label { color:#6f7c95; font-size:.67rem; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }
.qp-sub-val { color:#f5f7fc; font-size:1.2rem; font-weight:800; margin-top:5px; }
.qp-sub-note { color:#8b96ad; font-size:.71rem; margin-top:3px; line-height:1.4; }
.qp-subcard.is-red { background:rgba(255,89,109,.07); border-color:rgba(255,89,109,.32); }
.qp-subcard.is-red .qp-sub-label { color:#ff98a4; }
.qp-subcard.is-red .qp-sub-val { color:#ff7a8a; }
.qp-subcard.is-green { background:rgba(56,214,165,.07); border-color:rgba(56,214,165,.3); }
.qp-subcard.is-green .qp-sub-label { color:#5fdcb2; }
.qp-subcard.is-green .qp-sub-val { color:#3dd598; }
/* Sidebar logo + navigation */
.qp-logo { display:flex; align-items:center; gap:10px; margin:2px 0 6px; }
.qp-logo-mark { width:30px; height:30px; border-radius:9px; background:linear-gradient(135deg,#8d9aff,#4f7cf7); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:.95rem; flex:0 0 auto; }
.qp-logo-text { color:#f5f7fc; font-weight:800; font-size:1.02rem; letter-spacing:-.02em; }
.qp-badge-demo { background:#1c2740; color:#9fb0ff; border:1px solid #324070; border-radius:99px; padding:2px 8px; font-size:.63rem; font-weight:800; letter-spacing:.08em; }
.qp-nav-section { color:#66738d; font-size:.68rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:16px 0 8px; }
.qp-nav-item { display:flex; align-items:center; gap:10px; background:#131a2c; border:1px solid #232c42; border-radius:11px; padding:10px 12px; color:#e8edf8; font-weight:600; font-size:.88rem; }
.qp-nav-ico { color:#8d9aff; font-weight:800; }
.qp-nav-live { margin-left:auto; width:8px; height:8px; border-radius:99px; background:#4fe0b0; box-shadow:0 0 0 3px rgba(79,224,176,.15); }
/* Header chips (real threshold state, top-right) */
.qp-head-right { display:flex; justify-content:flex-end; align-items:center; gap:8px; flex-wrap:wrap; padding-top:16px; }
.qp-chip { background:#141b2d; border:1px solid #26314a; color:#8b96ad; border-radius:99px; padding:6px 12px; font-size:.76rem; white-space:nowrap; }
.qp-chip b { color:#f5f7fc; font-weight:700; margin-left:4px; }
.qp-chip-accent { background:#1c2740; border-color:#324070; color:#9fb0ff; }
.qp-chip-accent b, .qp-chip-accent { color:#9fb0ff; }
/* Decision legend badges */
.qp-legend { display:flex; gap:8px; flex-wrap:wrap; margin:4px 0 12px; }
.qp-badge { border-radius:9px; padding:4px 11px; font-size:.74rem; font-weight:700; border:1px solid; background:transparent; }
/* Traffic-source cards */
.qp-source-top { display:flex; align-items:center; gap:12px; }
.qp-icon-tile { width:42px; height:42px; border-radius:12px; background:#1a2136; border:1px solid #26314a; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1rem; flex:0 0 auto; }
.qp-source-name { color:#f3f6fc; font-weight:700; font-size:.95rem; }
.qp-source-foot { margin-top:14px; }
/* Buttons */
.stButton>button,.stDownloadButton>button { border-radius:10px; border:1px solid #324070; background:#1c2740; color:#eef2fa; font-weight:600; }
.stDownloadButton>button { background:#4f7cf7; border-color:#4f7cf7; color:#fff; }
/* Dark data grid frame */
div[data-testid="stDataFrame"] { border:1px solid #26314a; border-radius:12px; overflow:hidden; background:#11182a; }
/* Keep interactive inputs consistent with the dark dashboard. */
div[data-baseweb="select"] > div { background:#141b2d !important; border-color:#324070 !important; color:#f2f5fb !important; }
div[data-baseweb="select"] input { color:#f2f5fb !important; }
div[data-baseweb="tag"] { background:#1c2740 !important; color:#c7d1ea !important; border-color:#324070 !important; }
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
  background:#141b2d !important; color:#f2f5fb !important; border-color:#324070 !important;
}
div[data-testid="stFileUploader"] section { background:#141b2d !important; border:1px dashed #324070 !important; }
div[data-testid="stFileUploader"] section * { color:#dce5f5 !important; }
[data-testid="stTable"] { background:#11182a !important; color:#eaf0fa !important; }
[data-testid="stTable"] th { background:#202a3d !important; color:#f2f5fb !important; }
[data-testid="stTable"] td { background:#11182a !important; color:#dce5f5 !important; }
[data-testid="stDataFrame"] iframe { color-scheme:dark; }
hr { border-color:#232c42; }
/* Equal-height hero columns + responsive tweaks */
[data-testid="stColumn"] { display:flex; flex-direction:column; }
[data-testid="stColumn"] > div { flex:1 1 auto; }
@media (max-width:900px) { .qp-hero { min-height:0; } .qp-subgrid { grid-template-columns:1fr; } }
</style>
""", unsafe_allow_html=True)

REQUIRED = ["query", "campaign", "ad_group", "impressions", "clicks", "cost", "conversions", "conversion_value"]
ALIASES = {
    "search term": "query", "search_term": "query", "search query": "query",
    "campaign name": "campaign", "ad group": "ad_group", "ad_group_name": "ad_group",
    "ad group name": "ad_group",
    "spend": "cost", "amount spent": "cost", "conversion value": "conversion_value",
    "conv. value": "conversion_value", "conv": "conversions"
}

def _norm_key(c):
    """Lowercase and unify separators so 'Ad Group_Name' == 'ad group name'."""
    return re.sub(r"\s+", " ", str(c).strip().lower().replace("-", " ").replace("_", " ")).strip()
IRRELEVANT_HINTS = [
    "free", "jobs", "job", "career", "salary", "meaning", "definition", "wikipedia",
    "torrent", "crack", "login", "customer service", "phone number", "complaint"
]
BUYING_HINTS = [
    "buy", "price", "pricing", "cost", "best", "compare", "review", "quote",
    "near me", "purchase", "discount", "trial", "demo", "software", "service"
]

def normalize_columns(df):
    df = df.copy()
    aliases = {_norm_key(k): v for k, v in ALIASES.items()}
    rename = {c: aliases.get(_norm_key(c), _norm_key(c).replace(" ", "_")) for c in df.columns}
    df = df.rename(columns=rename)
    # Guard against duplicate targets (e.g. both "cost" and "spend" present).
    return df.loc[:, ~df.columns.duplicated()]

def triage_row(r, target_cpa, min_clicks, min_spend, relevance_terms):
    query = str(r["query"]).strip()
    q = query.lower()
    clicks = float(r["clicks"])
    cost = float(r["cost"])
    conv = float(r["conversions"])
    value = float(r["conversion_value"])
    reasons = []
    relevance_terms = [x.strip().lower() for x in relevance_terms if x.strip()]
    relevant = not relevance_terms or any(t in q for t in relevance_terms)
    irrelevant = any(h in q for h in IRRELEVANT_HINTS)
    buying_intent = any(h in q for h in BUYING_HINTS)

    # Do not make a confident performance call on tiny samples.
    if clicks < min_clicks and cost < min_spend:
        return ("Ignore", 0.35,
                f"Low evidence: {clicks:.0f} clicks and {cost:.2f} spend; collect more data before changing bids.",
                "Low sample", relevant)

    if irrelevant:
        return ("Block", 0.78,
                "Query contains a likely irrelevant/support/job/free-intent term; verify against the business before adding a negative.",
                "Likely irrelevant intent", relevant)

    if not relevant:
        return ("Review", 0.40,
                "Query does not match the optional product/service terms provided; human relevance review is needed.",
                "Possible relevance mismatch", relevant)

    if conv >= 2 and clicks >= min_clicks:
        cpa = cost / conv if conv else np.inf
        if cpa <= target_cpa:
            conf = min(0.95, 0.65 + 0.05 * min(conv, 6) + 0.03 * min(clicks / max(min_clicks, 1), 3))
            return ("Promote", conf, f"{conv:.0f} conversions at CPA {cpa:.2f}, within target {target_cpa:.2f}; validate relevance and margin.", "Repeated conversions within target", relevant)
        return ("Review", 0.62, f"{conv:.0f} conversions but CPA {cpa:.2f} exceeds target {target_cpa:.2f}; inspect landing page and intent before changing bids.", "Conversions above target CPA", relevant)

    if clicks >= min_clicks and conv == 0 and cost >= min_spend:
        conf = min(0.88, 0.55 + 0.05 * min(cost / max(min_spend, 1), 5))
        return ("Review", conf, f"No conversions after {clicks:.0f} clicks and {cost:.2f} spend; assess conversion lag, tracking, and query intent before blocking.", "Spend without conversions", relevant)

    if conv > 0:
        return ("Ignore", 0.52, f"Only {conv:.0f} conversion(s) on {clicks:.0f} clicks; evidence is limited, so avoid promoting from a small sample.", "Limited conversion sample", relevant)

    if buying_intent:
        return ("Review", 0.48, "Query shows possible commercial intent, but current performance evidence is insufficient for a reliable promote/block decision.", "Commercial intent, uncertain performance", relevant)

    return ("Ignore", 0.50, "No strong relevance or performance signal; retain for now and reassess with more data.", "No strong signal", relevant)

def run_triage(df, target_cpa, min_clicks, min_spend, relevance_terms):
    out = []
    for _, r in df.iterrows():
        decision, confidence, reason, category, relevant = triage_row(r, target_cpa, min_clicks, min_spend, relevance_terms)
        out.append((decision, round(float(confidence), 2), reason, category, relevant))
    result = df.copy()
    result[["decision", "confidence", "reason", "signal", "keyword_relevance_match"]] = pd.DataFrame(out, index=result.index)
    return result

with st.sidebar:
    st.markdown('<div class="qp-logo"><span class="qp-logo-mark">Q</span><span class="qp-logo-text">QueryPilot AI</span><span class="qp-badge-demo">DEMO</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="qp-nav-section">Marketing &amp; Sales</div>', unsafe_allow_html=True)
    st.markdown('<div class="qp-nav-item"><span class="qp-nav-ico">◧</span><span>Search-term Triage</span><span class="qp-nav-live" title="Active"></span></div>', unsafe_allow_html=True)
    st.markdown('<div class="qp-nav-section">Triage settings</div>', unsafe_allow_html=True)
    target_cpa = st.number_input("Target CPA", min_value=0.01, value=50.0, step=5.0)
    min_clicks = st.number_input("Minimum clicks for performance judgement", min_value=1, value=10, step=1)
    min_spend = st.number_input("Minimum spend for performance judgement", min_value=0.01, value=30.0, step=5.0)
    relevance_raw = st.text_input("Product/service terms (optional)", placeholder="e.g. crm, accounting, project management")
    relevance_terms = relevance_raw.split(",") if relevance_raw.strip() else []
    st.caption("If terms are entered, queries without any matching term are routed to Review.")

head_l, head_r = st.columns([2.6, 1])
with head_l:
    st.title("Marketing Optimization")
    st.caption("Search-term quality, campaign efficiency, and evidence-aware recommendations.")
with head_r:
    st.markdown(
        f'<div class="qp-head-right">'
        f'<span class="qp-chip">Target CPA <b>{target_cpa:,.0f}</b></span>'
        f'<span class="qp-chip">Min clicks <b>{int(min_clicks)}</b></span>'
        f'<span class="qp-chip">Min spend <b>{min_spend:,.0f}</b></span>'
        f'<span class="qp-chip qp-chip-accent">● DEMO</span></div>',
        unsafe_allow_html=True,
    )
st.info("Decision support prototype, not an automatic Google Ads change. Always review recommendations before applying negatives or bids.")

uploaded = st.file_uploader("Upload a search-term CSV", type=["csv"])
sample_path = os.path.join(os.path.dirname(__file__), "sample_search_terms.csv")
if uploaded:
    try:
        raw = pd.read_csv(uploaded)
    except pd.errors.EmptyDataError:
        st.error("The uploaded file is empty. Upload a CSV with a header row and at least one data row.")
        st.stop()
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()
else:
    st.markdown("No file uploaded? Start with the included sample data.")
    if not os.path.exists(sample_path):
        st.error(f"Sample file `{os.path.basename(sample_path)}` not found. Upload a CSV to continue.")
        st.stop()
    try:
        raw = pd.read_csv(sample_path)
    except Exception as e:
        st.error(f"Could not read sample CSV: {e}")
        st.stop()

df = normalize_columns(raw)
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.markdown("Required columns: `query, campaign, ad_group, impressions, clicks, cost, conversions, conversion_value`. Common aliases such as `search term` and `spend` are supported.")
    st.stop()

df = df[REQUIRED].copy()
df["query"] = df["query"].fillna("").astype(str)
METRIC_COLS = ["impressions", "clicks", "cost", "conversions", "conversion_value"]
for c in METRIC_COLS:
    # Tolerate formatting found in real ad exports (e.g. "1,234.50" or "$50").
    df[c] = pd.to_numeric(df[c].astype(str).str.strip().str.replace(r"[,$\s]", "", regex=True), errors="coerce")
finite_mask = np.isfinite(df[METRIC_COLS].to_numpy(dtype="float64")).all(axis=1)
if not finite_mask.all():
    st.warning("Some numeric values are missing, non-numeric, or infinite; rows with invalid metrics are removed.")
    df = df[finite_mask]
if (df[METRIC_COLS] < 0).any().any():
    st.error("Negative metric values found. Fix the input data before analysis.")
    st.stop()
if df.empty:
    st.error("No valid rows found.")
    st.stop()

with st.spinner("Analyzing search terms..."):
    result = run_triage(df, target_cpa, int(min_clicks), float(min_spend), relevance_terms)

total_cost = result["cost"].sum()
total_conv = result["conversions"].sum()
overall_cpa = total_cost / total_conv if total_conv else np.nan
total_clicks = int(result["clicks"].sum())
total_impressions = int(result["impressions"].sum())
blocked_count = int(result["decision"].eq("Block").sum())
conversion_value = float(result["conversion_value"].sum())
roas = conversion_value / total_cost if total_cost else np.nan
quality_score = max(0, min(100, int(100 * (result["decision"].eq("Promote").sum() + .5 * result["decision"].eq("Ignore").sum()) / max(len(result), 1))))
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Search terms analyzed", f"{len(result):,}")
with k2:
    st.metric("Total spend", f"{total_cost:,.2f}")
with k3:
    st.metric("Conversions", f"{total_conv:,.1f}")
with k4:
    st.metric("Blended CPA", f"{overall_cpa:,.2f}" if pd.notna(overall_cpa) else "N/A")

roas_text = f"{roas:.2f}x" if pd.notna(roas) else "N/A"
promote_count = int(result["decision"].eq("Promote").sum())
review_count = int(result["decision"].eq("Review").sum())
block_spend = float(result.loc[result["decision"].eq("Block"), "cost"].sum())
# Decision-mix bars (display-only; same counts as the summary table below).
dec_colors = {"Promote": "#38d6a5", "Review": "#7b8cff", "Ignore": "#f7b955", "Block": "#ff596d"}
bar_parts = []
for _d, _c in dec_colors.items():
    _n = int(result["decision"].eq(_d).sum())
    _pct = round(100 * _n / max(len(result), 1))
    bar_parts.append(f'<div class="qp-bar-row"><span class="qp-bar-name">{_d}</span>'
                     f'<div class="qp-track"><div class="qp-fill" style="width:{_pct}%;background:{_c}"></div></div>'
                     f'<span class="qp-bar-val">{_pct}%</span></div>')
bar_html = "".join(bar_parts)

h1c, h2c, h3c = st.columns([1.05, 1, 1.3])
with h1c:
    st.markdown(f'''<div class="qp-card qp-hero">
      <div class="qp-eyebrow">Search-term quality score</div>
      <div class="qp-hero-num" style="color:#ffa149">{quality_score}%</div>
      <span class="qp-pill">● Analysis ready</span>
      <div class="qp-note">
        <div class="qp-note-title">What\u2019s happening</div>
        <p>Illustrative heuristic indicator built from the decision mix across analyzed search terms. Transparent rules, not a calibrated probability.</p>
      </div>
      <p class="qp-sub" style="margin-top:12px">✦ Tune the rules with the sidebar settings</p>
    </div>''', unsafe_allow_html=True)
with h2c:
    st.markdown(f'''<div class="qp-card qp-hero">
      <div class="qp-eyebrow">Total clicks</div>
      <div class="qp-hero-num" style="color:#8d9aff">{total_clicks:,}</div>
      <p class="qp-sub">{total_impressions:,} impressions</p>
      <div class="qp-bars">{bar_html}</div>
    </div>''', unsafe_allow_html=True)
with h3c:
    st.markdown(f'''<div class="qp-card qp-hero">
      <div class="qp-card-head"><div class="qp-check">✓</div><div class="qp-eyebrow" style="margin:0">Block recommendations</div></div>
      <div class="qp-hero-num">{blocked_count:,}</div>
      <span class="qp-pill qp-pill-red">● Verify before adding negative keywords</span>
      <div class="qp-subgrid">
        <div class="qp-subcard is-red"><div class="qp-sub-label">Spend in block candidates</div><div class="qp-sub-val">{block_spend:,.2f}</div><div class="qp-sub-note">Cost tied in likely-irrelevant terms</div></div>
        <div class="qp-subcard is-green"><div class="qp-sub-label">Conversion value / spend</div><div class="qp-sub-val">{roas_text}</div><div class="qp-sub-note">Value: {conversion_value:,.2f}</div></div>
        <div class="qp-subcard"><div class="qp-sub-label">Review queue</div><div class="qp-sub-val">{review_count:,}</div><div class="qp-sub-note">Human check recommended</div></div>
        <div class="qp-subcard"><div class="qp-sub-label">Promote ready</div><div class="qp-sub-val">{promote_count:,}</div><div class="qp-sub-note">Within target CPA</div></div>
      </div>
    </div>''', unsafe_allow_html=True)

st.subheader("Decision overview")
st.caption("How the engine classifies every analyzed search term.")
counts = result["decision"].value_counts().reindex(["Promote", "Block", "Ignore", "Review"], fill_value=0).rename_axis("Decision").reset_index(name="Terms")
chart_col, table_col = st.columns([1, 1.5])
with chart_col:
    fig = px.pie(counts, names="Decision", values="Terms", hole=0.62, title="Triage distribution", color="Decision", color_discrete_map={"Promote":"#38d6a5","Block":"#ff596d","Ignore":"#f7b955","Review":"#7b8cff"})
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#eaf0fa", margin=dict(l=4,r=4,t=40,b=8), legend=dict(font=dict(size=12, color="#c9d2e4"), bgcolor="rgba(0,0,0,0)"))
    fig.update_traces(marker=dict(line=dict(color="#141b2d", width=3)), textposition="inside", textfont=dict(size=12, color="#0b1020"))
    st.plotly_chart(fig, use_container_width=True)
with table_col:
    st.dataframe(counts, use_container_width=True, hide_index=True)
    st.caption("Confidence is a rule-based evidence score, not a calibrated probability.")

st.markdown("---")
st.subheader("Traffic sources")
st.caption("Platform connections are not configured. These cards are visual placeholders; metrics come only from the uploaded CSV or included sample data.")
source_data = [("Google Ads", "G", "#4c8dff", "CSV analysis available"), ("Microsoft Ads", "▦", "#49a6ff", "Connection not configured"), ("Meta", "f", "#8292ff", "Connection not configured"), ("X", "𝕏", "#d9e1ee", "Connection not configured"), ("LinkedIn", "in", "#55b7e8", "Connection not configured"), ("Other sources", "○", "#8d9aff", "CSV import available")]
source_cols = st.columns(3)
for i, (name, symbol, color, status) in enumerate(source_data):
    is_available = "not configured" not in status.lower()
    pill_cls = "qp-pill" if is_available else "qp-pill-grey"
    pill_txt = "● Available" if is_available else "○ Not configured"
    with source_cols[i % 3]:
        st.markdown(f'''<div class="qp-card" style="margin-bottom:14px;min-height:105px">
          <div class="qp-source-top"><div class="qp-icon-tile" style="color:{color}">{symbol}</div>
          <div><div class="qp-source-name">{name}</div><div class="qp-sub">{status}</div></div></div>
          <div class="qp-source-foot"><span class="{pill_cls}">{pill_txt}</span></div>
        </div>''', unsafe_allow_html=True)

st.subheader("Search-term recommendations")
st.caption("Every row includes a decision, an evidence score and a plain-English reason. Filter, search, then export.")
filters = st.multiselect("Filter decisions", ["Promote", "Block", "Ignore", "Review"], default=["Promote", "Block", "Review"])
filtered = result[result["decision"].isin(filters)].copy()
search = st.text_input("Search query text")
if search:
    # Literal substring match so characters like "(" or "$" cannot crash the filter.
    filtered = filtered[filtered["query"].str.contains(search, case=False, na=False, regex=False)]
display_cols = ["query", "campaign", "ad_group", "clicks", "cost", "conversions", "conversion_value", "decision", "confidence", "signal", "reason"]

DECISION_BADGE = {
    "Promote": ("#123f34", "#4fe0b0"),
    "Block": ("#431b26", "#ff8090"),
    "Ignore": ("#453416", "#ffc46b"),
    "Review": ("#243066", "#9fb0ff"),
}
legend_html = "".join(
    f'<span class="qp-badge" style="color:{fg};border-color:{fg}55;background:{bg}66">{d}</span>'
    for d, (bg, fg) in DECISION_BADGE.items()
)
st.markdown(f'<div class="qp-legend">{legend_html}</div>', unsafe_allow_html=True)

display_df = filtered[display_cols]
# Colored decision badges via pandas Styler (values unchanged); guard on the
# Styler cell limit so very large CSVs still render, unstyled.
if display_df.shape[0] * display_df.shape[1] <= int(pd.options.styler.render.max_elements):
    def _paint_decision(values):
        out = []
        for v in values:
            bg_fg = DECISION_BADGE.get(v)
            out.append(f"background-color: {bg_fg[0]}; color: {bg_fg[1]}; font-weight: 700;" if bg_fg else "")
        return out

    table_data = display_df.style.apply(_paint_decision, subset=["decision"])
else:
    table_data = display_df
st.dataframe(
    table_data,
    filtered[display_cols],
    use_container_width=True,
    hide_index=True,
    height=420,
    column_config={
        "query": st.column_config.TextColumn("Query", width="large"),
        "campaign": st.column_config.TextColumn("Campaign"),
        "ad_group": st.column_config.TextColumn("Ad group"),
        "cost": st.column_config.NumberColumn("Cost", format="%.2f"),
        "conversion_value": st.column_config.NumberColumn("Conv. value", format="%.2f"),
        "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
        "signal": st.column_config.TextColumn("Signal", width="medium"),
        "reason": st.column_config.TextColumn("Reason", width="large"),
    },
)

csv_bytes = result.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download full triage CSV", data=csv_bytes, file_name="querypilot_triage_results.csv", mime="text/csv")

st.subheader("How to explain this result")
st.markdown("""
- **Promote**: repeated conversion evidence at or below the configured target CPA; still check relevance and profitability.
- **Block**: strong likely-irrelevant intent signals; human verification is required before applying a negative keyword.
- **Review**: mixed evidence, possible relevance mismatch, or meaningful spend without conversions.
- **Ignore**: low sample size or no clear positive/negative signal yet.
""")
st.caption("Prototype limitations: intent detection uses transparent keyword heuristics; this is not a trained ML classifier. Validate thresholds on labelled historical data before production use.")
