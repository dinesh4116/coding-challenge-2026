from __future__ import annotations

import hashlib
import html
import io
import re

import pandas as pd
import streamlit as st

from triage_engine import REQUIRED_COLUMNS, triage_dataframe
from agent_runtime import run_local_agent

# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Kestrel | Search Term Triage",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Stable dark theme and readable, simple styling. No external assets required.
st.markdown(
    """
    <style>
    :root {
      --bg: #0b1220; --panel: #111c2d; --panel2: #18263a;
      --line: #2b3c54; --text: #f1f5fb; --muted: #a8b7cb;
      --blue: #6db5ff; --teal: #53dfc2;
    }
    [data-testid="stAppViewContainer"] { background: var(--bg); }
    [data-testid="stHeader"] { background: rgba(11,18,32,.92); }
    .block-container { max-width: 1560px; padding-top: 1.2rem; padding-bottom: 2.3rem; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#101a2a,#151f30); border-right: 1px solid var(--line); }
    [data-testid="stSidebarContent"] { padding-top: .8rem; }
    [data-testid="stSidebar"] hr { border-color: var(--line); }
    h1,h2,h3 { letter-spacing: -.025em; }
    p,li,label { line-height: 1.5; }
    .hero {
      padding: 26px 28px; border-radius: 20px; margin-bottom: 16px;
      background: linear-gradient(115deg,#111b2b 0%,#1a2d49 60%,#23436c 100%);
      border: 1px solid #2b4568; box-shadow: 0 12px 35px rgba(0,0,0,.15);
    }
    .hero-kicker { color:#9fcaff; font-size:.74rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; margin-bottom:8px; }
    .hero-title { color:#fff; font-size:clamp(1.75rem,3vw,2.45rem); font-weight:850; margin:0; line-height:1.15; }
    .hero-copy { color:#d7e5f8; margin:.65rem 0 0 0; max-width:850px; }
    .hero-pills { display:flex; flex-wrap:wrap; gap:8px; margin-top:17px; }
    .pill { background:rgba(8,16,29,.4); color:#e4efff; border:1px solid #3a5273; border-radius:100px; padding:5px 10px; font-size:.76rem; font-weight:650; }
    .side-brand { display:flex; align-items:center; gap:11px; margin:2px 0 18px; }
    .side-logo { width:42px; height:42px; display:flex; align-items:center; justify-content:center; border-radius:14px; background:linear-gradient(135deg,#367be8,#3bc9b5); font-size:1.3rem; }
    .side-title { color:#f5f8ff; font-weight:850; font-size:1rem; line-height:1.2; }
    .side-sub { color:#9dafc8; font-size:.75rem; margin-top:4px; }
    .section-label { color:#91bdff; text-transform:uppercase; font-size:.72rem; font-weight:800; letter-spacing:.13em; margin-bottom:4px; }
    .muted { color:var(--muted); }
    .agent-card { border:1px solid #355072; border-radius:16px; padding:13px; background:linear-gradient(145deg,#1b304b,#121e30); margin:10px 0 12px; }
    .agent-head { display:flex; align-items:center; gap:10px; }
    .agent-icon { display:flex; align-items:center; justify-content:center; width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg,#367be8,#3bc9b5); font-size:1.2rem; }
    .agent-name { color:#fff; font-weight:800; font-size:.98rem; }
    .agent-status { color:#72e2c5; font-size:.7rem; font-weight:800; letter-spacing:.07em; margin-top:3px; }
    .agent-copy { color:#bdcbe0; font-size:.8rem; line-height:1.45; margin-top:10px; }
    .mini-card { border:1px solid var(--line); border-radius:15px; background:linear-gradient(145deg,#17263a,#111b2b); padding:15px 16px; min-height:100px; }
    .mini-label { color:#9fb2ce; font-size:.78rem; font-weight:700; }
    .mini-value { color:#f5f8ff; font-size:1.7rem; font-weight:850; margin-top:5px; }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#17263a,#111b2b); border:1px solid var(--line); padding:15px 16px; border-radius:15px; min-height:100px; }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color:#aebed4 !important; font-weight:700 !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div { color:#f5f8ff !important; font-weight:850 !important; }
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button { border-radius:11px; font-weight:700; min-height:2.45rem; transition:all .12s ease; }
    div.stButton > button:hover, div.stDownloadButton > button:hover { transform:translateY(-1px); border-color:#6db5ff; }
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background:linear-gradient(100deg,#347de5,#1fa99f); border:0; color:#fff; }
    [data-testid="stFileUploader"] { border:1px dashed #415d80; background:rgba(9,17,30,.55); border-radius:13px; padding:8px; }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stNumberInput"] input { border-radius:10px !important; }
    [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid var(--line); }
    [data-baseweb="tab"] { padding:.65rem .8rem; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    [data-testid="stAlert"] { border-radius:12px; }
    .empty-state { text-align:center; border:1px dashed #3b5678; background:linear-gradient(145deg,#111d30,#14243a); padding:34px 24px; border-radius:20px; }
    .empty-icon { font-size:2.35rem; }
    .empty-title { color:#f3f7ff; font-size:1.4rem; font-weight:850; margin-top:8px; }
    .empty-copy { color:#aebfd7; max-width:680px; margin:8px auto 0; line-height:1.6; }
    .footer { color:#7186a3; border-top:1px solid #25364d; margin-top:25px; padding-top:13px; font-size:.78rem; }
    @media(max-width: 900px) { .block-container { padding-left:1rem; padding-right:1rem; } .hero { padding:20px; } }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session defaults.
for key, value in {
    "agent_messages": [],
    "agent_pending_question": None,
    "agent_export_df": None,
    "agent_export_name": "triage_copilot_export.csv",
    "active_dataset_signature": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

QUICK_PROMPTS = [
    ("📊", "Dataset summary", "Summarize this dataset and the decision counts."),
    ("🏆", "Top campaign", "Which campaign has the highest ROAS?"),
    ("🚫", "High-spend blocked", "Show blocked search terms with spend above ₹10,000."),
    ("🔎", "Explain personal loan", "Why was 'personal loan' blocked?"),
    ("📥", "Export blocked", "Export BLOCK terms with spend above ₹10,000."),
]

# The competition report's money fields are treated as USD internally. Convert
# only for user-facing display; keep the source values unchanged for decisions.
DEFAULT_USD_INR_RATE = 96.50
USD_AMOUNT_PATTERN = re.compile(r"\$\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)")
INR_AMOUNT_PATTERN = re.compile(r"₹\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)")


def format_inr(value: float, decimals: int = 2) -> str:
    """Format a number in rupees with Indian digit grouping."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    sign = "-" if amount < 0 else ""
    fixed = f"{abs(amount):.{decimals}f}"
    whole, dot, fraction = fixed.partition(".")
    if len(whole) > 3:
        last_three, prefix = whole[-3:], whole[:-3]
        groups = []
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(groups + [last_three])
    return f"₹{sign}{whole}{dot}{fraction}"


def inr_prompt_to_source_currency(question: str, rate: float) -> str:
    """Translate rupee thresholds to the source report's dollar units for local tools."""
    def replace(match: re.Match) -> str:
        amount = float(match.group(1).replace(",", ""))
        return f"${amount / rate:.4f}"
    return INR_AMOUNT_PATTERN.sub(replace, question)


def source_currency_text_to_inr(text: str, rate: float) -> str:
    """Convert dollar-formatted amounts in agent text to rupees for display."""
    def replace(match: re.Match) -> str:
        amount = float(match.group(1).replace(",", ""))
        return format_inr(amount * rate)
    return USD_AMOUNT_PATTERN.sub(replace, text)


def add_inr_export_columns(df: pd.DataFrame, rate: float) -> pd.DataFrame:
    """Keep source columns intact and append explicit INR conversions to downloads."""
    out = df.copy()
    for col in ("cost", "conversion_value", "cpa"):
        if col in out.columns:
            out[f"{col}_inr"] = pd.to_numeric(out[col], errors="coerce") * rate
    return out


def money_display_copy(df: pd.DataFrame, rate: float) -> pd.DataFrame:
    """Return a view copy where source USD money fields are shown in INR."""
    out = df.copy()
    for col in ("cost", "conversion_value", "cpa", "spend"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce") * rate
    return out


def queue_question(question: str) -> None:
    st.session_state["agent_pending_question"] = question


def render_hero(upload_name: str | None = None, row_count: int | None = None) -> None:
    pills = ["● Explainable decisions", "✦ Human-in-the-loop", "▦ CSV-powered analysis"]
    if upload_name is not None and row_count is not None:
        pills.insert(0, f"✓ {html.escape(upload_name)} · {row_count:,} rows")
    pill_html = "".join(f'<span class="pill">{p}</span>' for p in pills)
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">DEVSPRINT · PROBLEM STATEMENT 01</div>
          <div class="hero-title">🎯 Search Term Triage Engine</div>
          <p class="hero-copy">Turn raw advertising search terms into explainable recommendations — with confidence, clear reasons, and a human review step.</p>
          <div class="hero-pills">{pill_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Sidebar: data input, settings, and Copilot (no API-key field)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="side-brand">
          <div class="side-logo">🎯</div>
          <div><div class="side-title">Kestrel Triage</div><div class="side-sub">PS-01 · DevSprint workspace</div></div>
        </div>
        <div class="section-label">01 · DATA SOURCE</div>
        <p class="muted" style="font-size:.82rem;margin-top:3px;">Upload a search-term performance report to begin.</p>
        """,
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Upload search-term CSV",
        type=["csv"],
        key="triage_csv_upload",
        help="The CSV must contain the required search-term and performance columns.",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        st.success(f"File selected · {uploaded.name}", icon="✅")
    else:
        st.caption("No dataset loaded yet")

    with st.expander("💱 Currency display", expanded=False):
        usd_inr_rate = st.number_input(
            "USD → INR display rate", min_value=1.0, max_value=200.0,
            value=DEFAULT_USD_INR_RATE, step=0.25, format="%.2f",
            help="Only changes display and rupee filters. The source data and ROAS calculations remain in their original units.",
        )
        st.caption("Indicative conversion rate. Update it if your event or organisation specifies another rate.")

    with st.expander("⚙️ Decision settings", expanded=False):
        st.caption("These are transparent baseline thresholds; tune them to test decision behaviour.")
        min_clicks_promote = st.number_input("Minimum clicks to promote", min_value=1, max_value=1000, value=20, step=5)
        min_conversions_promote = st.number_input("Minimum conversions to promote", min_value=1, max_value=100, value=3)
        min_clicks_evaluate = st.number_input("Clicks for review", min_value=1, max_value=5000, value=30, step=5)
        min_spend_block_inr = st.number_input(
            "Material spend threshold (₹)", min_value=0.0, max_value=10000000.0,
            value=250.0 * DEFAULT_USD_INR_RATE, step=1000.0, format="%.2f",
            help="Entered in INR and converted to the source report's units before triage.",
        )
        min_roas_promote = st.number_input("Minimum ROAS to promote", min_value=0.0, max_value=100.0, value=1.5, step=0.25)

    st.markdown(
        """
        <div class="agent-card">
          <div class="agent-head"><div class="agent-icon">✦</div><div>
            <div class="agent-name">Triage Copilot</div><div class="agent-status">● READY WHEN DATA IS UPLOADED</div>
          </div></div>
          <div class="agent-copy">Ask questions in plain English. Review search terms, compare campaigns, understand a recommendation, or prepare a filtered CSV.</div>
        </div>
        <div class="section-label">02 · QUICK ACTIONS</div>
        """,
        unsafe_allow_html=True,
    )
    if uploaded is None:
        st.info("Upload a CSV above to activate the Copilot.")
    else:
        qcols = st.columns(2)
        for i, (emoji, label, prompt) in enumerate(QUICK_PROMPTS):
            with qcols[i % 2]:
                if st.button(f"{emoji} {label}", key=f"qa_{i}", use_container_width=True):
                    queue_question(prompt)

    with st.form("triage_copilot_form", clear_on_submit=True):
        question = st.text_area(
            "Ask Triage Copilot",
            placeholder="Ask about this dataset…\ne.g. Which campaign has the highest ROAS?",
            height=90,
            label_visibility="collapsed",
            disabled=uploaded is None,
        )
        ask = st.form_submit_button("✦ Ask Copilot", type="primary", use_container_width=True, disabled=uploaded is None)
    if ask and question.strip():
        queue_question(question.strip())

# No dataset is bundled into the active app; user upload is required.
if uploaded is None:
    render_hero()
    st.markdown(
        """
        <div class="empty-state">
          <div class="empty-icon">📂</div>
          <div class="empty-title">Your workspace is ready</div>
          <div class="empty-copy">Upload the CSV using the left panel. Your metrics, recommendation table, campaign insights and Triage Copilot will appear after the file passes validation.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**① Upload**\n\nChoose the provided search-term report.")
    c2.markdown("**② Analyse**\n\nReview decisions, confidence and reasons.")
    c3.markdown("**③ Take action**\n\nFilter results and export a CSV for review.")
    with st.expander("Required CSV columns"):
        st.write("The file must contain the following columns:")
        st.code(", ".join(REQUIRED_COLUMNS))
    st.markdown('<div class="footer">PS-01 · Recommendations support human review; no live advertising account changes are made.</div>', unsafe_allow_html=True)
    st.stop()

# Parse, validate and triage the uploaded CSV.
try:
    upload_bytes = uploaded.getvalue()
    raw = pd.read_csv(io.BytesIO(upload_bytes))
    if raw.empty:
        st.error("This CSV contains no data rows. Please upload a report with search-term records.")
        st.stop()
    missing_cols = [column for column in REQUIRED_COLUMNS if column not in raw.columns]
    if missing_cols:
        st.error("This CSV is missing required columns: " + ", ".join(missing_cols))
        with st.expander("See all required column names"):
            st.code(", ".join(REQUIRED_COLUMNS))
        st.stop()
    with st.spinner("Analysing the uploaded report…"):
        result = triage_dataframe(
            raw,
            int(min_clicks_promote),
            int(min_conversions_promote),
            int(min_clicks_evaluate),
            float(min_spend_block_inr) / float(usd_inr_rate),
            float(min_roas_promote),
        )
except Exception as exc:
    st.error(f"Could not process this CSV: {type(exc).__name__}: {exc}")
    st.stop()

# Clear conversation/export if uploaded contents change.
signature = hashlib.sha256(upload_bytes).hexdigest()
if st.session_state["active_dataset_signature"] != signature:
    st.session_state["active_dataset_signature"] = signature
    st.session_state["agent_messages"] = []
    st.session_state["agent_export_df"] = None
    st.session_state["agent_export_name"] = "triage_copilot_export.csv"

# Run a pending agent question against the just-computed triage result.
pending = st.session_state.pop("agent_pending_question", None)
if pending:
    st.session_state["agent_messages"].append({"role": "user", "content": pending})
    try:
        with st.spinner("Triage Copilot is checking the uploaded records…"):
            local_question = inr_prompt_to_source_currency(pending, float(usd_inr_rate))
            answer, export_df = run_local_agent(local_question, result)
            answer = source_currency_text_to_inr(answer, float(usd_inr_rate))
        st.session_state["agent_messages"].append({"role": "assistant", "content": answer})
        if export_df is not None:
            st.session_state["agent_export_df"] = export_df.copy()
            st.session_state["agent_export_name"] = "triage_copilot_export.csv"
    except Exception as exc:
        st.session_state["agent_messages"].append({"role": "assistant", "content": f"I couldn't complete that request: {type(exc).__name__}: {exc}"})
    st.session_state["agent_messages"] = st.session_state["agent_messages"][-12:]

# Sidebar conversation history + export control.
with st.sidebar:
    msgs = st.session_state["agent_messages"]
    if msgs:
        st.divider()
        st.markdown('<div class="section-label">03 · COPILOT CONVERSATION</div>', unsafe_allow_html=True)
        with st.container():
            for message in msgs[-8:]:
                if message["role"] == "user":
                    st.markdown("**🧑 You**")
                    st.markdown(f"> {message['content']}")
                else:
                    st.markdown("**✦ Copilot**")
                    st.markdown(message["content"])
                st.markdown("---")
        export_df = st.session_state.get("agent_export_df")
        if isinstance(export_df, pd.DataFrame):
            st.download_button(
                f"⬇️ Download prepared CSV · {len(export_df):,} rows",
                data=add_inr_export_columns(export_df, float(usd_inr_rate)).to_csv(index=False).encode("utf-8-sig"),
                file_name=st.session_state["agent_export_name"],
                mime="text/csv",
                use_container_width=True,
                key="copilot_download",
            )
        if st.button("Clear conversation", key="copilot_clear", use_container_width=True):
            st.session_state["agent_messages"] = []
            st.session_state["agent_export_df"] = None
            st.rerun()

# -----------------------------------------------------------------------------
# Main dashboard
# -----------------------------------------------------------------------------
render_hero(uploaded.name, len(result))
spend = pd.to_numeric(result["cost"], errors="coerce").fillna(0).sum()
conversion_value = pd.to_numeric(result["conversion_value"], errors="coerce").fillna(0).sum()
aggregate_roas = conversion_value / spend if spend > 0 else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Rows analysed", f"{len(result):,}")
m2.metric("Promote", f"{int((result.triage_decision == 'PROMOTE').sum()):,}")
m3.metric("Block", f"{int((result.triage_decision == 'BLOCK').sum()):,}")
m4.metric("Ignore", f"{int((result.triage_decision == 'IGNORE').sum()):,}")
m5.metric("Human review", f"{int(result.human_review.sum()):,}")

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"<div class='mini-card'><div class='mini-label'>Total ad spend</div><div class='mini-value'>{format_inr(spend * float(usd_inr_rate))}</div><div class='muted'>Converted from source report</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='mini-card'><div class='mini-label'>Conversion value</div><div class='mini-value'>{format_inr(conversion_value * float(usd_inr_rate))}</div><div class='muted'>Reported value, not verified profit</div></div>", unsafe_allow_html=True)
with k3:
    st.markdown(f"<div class='mini-card'><div class='mini-label'>Aggregate ROAS</div><div class='mini-value'>{aggregate_roas:.2f}×</div><div class='muted'>Conversion value ÷ spend</div></div>", unsafe_allow_html=True)

st.info("Decision support only: BLOCK is a recommendation for negative-keyword review, not an automatic account change. Human-review flags overlap the three decision categories.")
tab_overview, tab_explore, tab_campaigns, tab_method = st.tabs(["✦ Overview", "⌕ Explore decisions", "▥ Campaign insights", "ⓘ How it works"])

with tab_overview:
    a, b = st.columns([0.9, 1.4])
    with a:
        st.subheader("Recommendation mix")
        counts = result["triage_decision"].value_counts().reindex(["PROMOTE", "BLOCK", "IGNORE"], fill_value=0)
        st.bar_chart(counts)
        st.caption("Recommendations generated by the rule-based engine; not ground-truth labels.")
    with b:
        st.subheader("Priority review queue")
        queue = result[result["human_review"]].copy()
        queue["priority_score"] = queue["cost"] + queue["clicks"] * 2 + queue["conversions"] * 10
        columns = [c for c in ["search_term", "triage_decision", "clicks", "cost", "confidence", "reason"] if c in queue.columns]
        if queue.empty:
            st.success("No rows are currently flagged for human review under these settings.")
        else:
            queue_display = money_display_copy(queue.sort_values("priority_score", ascending=False)[columns].head(10), float(usd_inr_rate))
            st.dataframe(
                queue_display,
                use_container_width=True, hide_index=True, height=355,
                column_config={"cost": st.column_config.NumberColumn("Spend (₹)", format="₹%.2f")},
            )
    st.subheader("Decision breakdown by confidence")
    st.dataframe(pd.crosstab(result["triage_decision"], result["confidence"]).reindex(["PROMOTE", "BLOCK", "IGNORE"], fill_value=0), use_container_width=True)

    st.subheader("Campaign money overview (₹)")
    money_by_campaign = result.groupby("campaign", dropna=False).agg(
        spend=("cost", "sum"), conversion_value=("conversion_value", "sum")
    ).reset_index().sort_values("spend", ascending=False).head(8).set_index("campaign")
    money_by_campaign = money_by_campaign * float(usd_inr_rate)
    money_by_campaign.columns = ["Ad spend (₹)", "Conversion value (₹)"]
    st.bar_chart(money_by_campaign)
    st.caption(f"Source amounts are displayed in INR at ₹{float(usd_inr_rate):.2f} per USD. This is a display conversion, not a change to the uploaded data.")

with tab_explore:
    st.subheader("Explore and export search terms")
    st.caption("Filter records, inspect why each recommendation was made, and export the exact rows for analyst review.")
    f1, f2, f3 = st.columns(3)
    with f1:
        decision_filter = st.multiselect("Decision", ["PROMOTE", "BLOCK", "IGNORE"], default=["PROMOTE", "BLOCK", "IGNORE"])
    with f2:
        confidence_filter = st.multiselect("Confidence", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"])
    with f3:
        review_filter = st.selectbox("Human review", ["All rows", "Review needed", "No review flag"])
    term_query = st.text_input("Search term, campaign, ad group or reason", placeholder="Try: working capital, grants, SBA, personal loan")
    view = result[result["triage_decision"].isin(decision_filter) & result["confidence"].isin(confidence_filter)].copy()
    if review_filter == "Review needed":
        view = view[view["human_review"]]
    elif review_filter == "No review flag":
        view = view[~view["human_review"]]
    if term_query.strip():
        q = term_query.strip().lower()
        mask = pd.Series(False, index=view.index)
        for col in ["search_term", "campaign", "ad_group", "reason", "intent_category"]:
            if col in view.columns:
                mask |= view[col].fillna("").astype(str).str.lower().str.contains(q, regex=False, na=False)
        view = view[mask]
    left, right = st.columns([1, 2])
    left.metric("Matching rows", f"{len(view):,}")
    right.caption("Scroll horizontally to inspect every column.")
    display_cols = [c for c in ["row_id", "search_term", "match_type", "campaign", "ad_group", "impressions", "clicks", "cost", "conversions", "conversion_value", "ctr", "conversion_rate", "cpa", "roas", "intent_category", "triage_decision", "confidence", "human_review", "reason"] if c in view.columns]
    view_display = money_display_copy(view[display_cols], float(usd_inr_rate))
    st.dataframe(view_display, use_container_width=True, hide_index=True, height=460, column_config={
        "cost": st.column_config.NumberColumn("Spend (₹)", format="₹%.2f"),
        "conversion_value": st.column_config.NumberColumn("Conversion value (₹)", format="₹%.2f"),
        "cpa": st.column_config.NumberColumn("CPA (₹)", format="₹%.2f"),
        "roas": st.column_config.NumberColumn(format="%.2fx"),
        "ctr": st.column_config.NumberColumn(format="%.2%"),
        "conversion_rate": st.column_config.NumberColumn(format="%.2%"),
        "human_review": st.column_config.CheckboxColumn(),
    })
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "⬇️ Download filtered CSV (with INR)",
        data=add_inr_export_columns(view, float(usd_inr_rate)).to_csv(index=False).encode("utf-8-sig"),
        file_name="search_term_triage_filtered_with_inr.csv", mime="text/csv", use_container_width=True, type="primary",
    )
    dl2.download_button(
        "Download all recommendations (with INR)",
        data=add_inr_export_columns(result, float(usd_inr_rate)).to_csv(index=False).encode("utf-8-sig"),
        file_name="all_search_term_recommendations_with_inr.csv", mime="text/csv", use_container_width=True,
    )
    st.caption("Downloads retain original source amount columns and add cost_inr, conversion_value_inr, and cpa_inr for comparison. Amounts in the dashboard are display-converted.")

with tab_campaigns:
    st.subheader("Campaign performance")
    st.caption("Compare spend, conversion value, ROAS and triage workload across campaigns.")
    camp = result.groupby("campaign", dropna=False).agg(
        rows=("row_id", "count"), impressions=("impressions", "sum"), spend=("cost", "sum"), clicks=("clicks", "sum"),
        conversions=("conversions", "sum"), conversion_value=("conversion_value", "sum"),
        promote=("triage_decision", lambda s: (s == "PROMOTE").sum()),
        block=("triage_decision", lambda s: (s == "BLOCK").sum()),
        review=("human_review", "sum"),
    ).reset_index()
    camp["roas"] = camp["conversion_value"].div(camp["spend"].where(camp["spend"] > 0))
    camp["ctr"] = camp["clicks"].div(camp["impressions"].where(camp["impressions"] > 0))
    camp["conversion_rate"] = camp["conversions"].div(camp["clicks"].where(camp["clicks"] > 0))
    camp_display = money_display_copy(camp, float(usd_inr_rate))
    st.dataframe(camp_display, use_container_width=True, hide_index=True, column_config={
        "spend": st.column_config.NumberColumn("Ad spend (₹)", format="₹%.2f"),
        "conversion_value": st.column_config.NumberColumn("Conversion value (₹)", format="₹%.2f"),
        "roas": st.column_config.NumberColumn(format="%.2fx"),
        "ctr": st.column_config.NumberColumn(format="%.2%"),
        "conversion_rate": st.column_config.NumberColumn(format="%.2%"),
    })
    chart_choice = st.radio("Chart metric", ["Ad spend (₹)", "Conversion value (₹)", "Conversions", "ROAS"], horizontal=True)
    chart_map = {"Ad spend (₹)": "spend", "Conversion value (₹)": "conversion_value", "Conversions": "conversions", "ROAS": "roas"}
    chart_data = camp.copy()
    if chart_map[chart_choice] in ("spend", "conversion_value"):
        chart_data[chart_map[chart_choice]] = chart_data[chart_map[chart_choice]] * float(usd_inr_rate)
    chart = chart_data.set_index("campaign")[[chart_map[chart_choice]]].sort_values(chart_map[chart_choice], ascending=False)
    st.bar_chart(chart)
    st.caption(f"Monetary chart values are shown in INR at ₹{float(usd_inr_rate):.2f} per USD; ROAS remains a ratio.")
    st.caption("ROAS is conversion value divided by spend; it is not profit and does not establish causation.")

with tab_method:
    st.subheader("How recommendations are generated")
    left, right = st.columns(2)
    with left:
        st.markdown("#### ✅ PROMOTE")
        st.write("Supported business-financing intent with sufficient observed performance evidence and ROAS above the configured threshold.")
        st.markdown("#### 🚫 BLOCK")
        st.write("Unsupported product or clearly irrelevant intent. This is a negative-keyword recommendation for human review, not an automatic account change.")
    with right:
        st.markdown("#### ⏸️ IGNORE")
        st.write("No immediate targeting change is recommended, often because evidence or intent is insufficient.")
        st.markdown("#### 🧑‍💼 HUMAN REVIEW")
        st.write("Ambiguous or low-evidence terms should be checked by an analyst before action.")
    with st.expander("Technical method and limitations"):
        st.markdown("""
        - The current engine is a transparent, rule-based baseline, not a trained machine-learning model.
        - Product relevance is checked before performance metrics; unsupported products can be flagged even when conversions are recorded.
        - Small samples are uncertain; confidence labels are categories, not calibrated probabilities.
        - Thresholds and keyword patterns should be validated against the advertiser's policy and reviewed labels.
        - All actions are recommendations; the app does not modify any live advertising account.
        """)
        st.write("Required input columns:")
        st.code(", ".join(REQUIRED_COLUMNS))

st.markdown('<div class="footer">PS-01 · Search Term Triage Engine · INR is a display conversion; recommendations support analyst review and do not change live ad accounts.</div>', unsafe_allow_html=True)
