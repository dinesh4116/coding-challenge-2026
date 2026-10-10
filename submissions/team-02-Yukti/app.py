"""Adomaly - PS-04 Campaign Anomaly Alerting Without Alert Fatigue.

Streamlit dashboard over the existing detection pipeline. It only *displays*
pipeline output: detection, scoring, routing and episode logic all live in
src/ and are not modified or re-implemented here.

Run:  streamlit run app.py
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import config as C
from src.data_io import load_ps04_metrics
from src.detector_config import PS04_BASE_METRICS, RATIO_METRICS, DetectorConfig
from src.explain import LABEL
from src.pipeline import run_ps04_detection
from src.scoring import ALERT, NO_ALERT, REVIEW

st.set_page_config(page_title="Adomaly | PS-04", page_icon="📡", layout="wide")

# Streamlit >= 1.46 uses width="stretch"; older versions use use_container_width.
_v = tuple(int(x) for x in st.__version__.split(".")[:2])
FULL = {"width": "stretch"} if _v >= (1, 46) else {"use_container_width": True}

# Same config run_ps04_detection uses by default; read here only to display thresholds.
CFG = DetectorConfig(metrics=PS04_BASE_METRICS + tuple(RATIO_METRICS))
ROUTE_COLORS = {ALERT: "#d64545", REVIEW: "#e0a030", NO_ALERT: "#9aa5b1"}
SEV_ORDER = ["high", "medium", "low"]
FLAG_COLS = ["date", "campaign_id", "campaign_name", "channel", "vertical", "metric",
             "observed", "baseline", "pct_change", "z", "direction", "severity",
             "evidence_score", "route", "episode_id", "notification", "explanation",
             "diagnostic_action"]

st.markdown("""<style>
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:10px 14px}
div[data-testid="stMetricValue"]{font-size:1.5rem}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data ----
@st.cache_data(show_spinner="Loading PS-04 dataset...")
def load_data(path: str):
    return load_ps04_metrics(path)


@st.cache_data(show_spinner="Running Adomaly detection pipeline...")
def run_pipeline(metrics: pd.DataFrame, metadata: pd.DataFrame):
    return run_ps04_detection(metrics, metadata)


def fmt_value(metric: str, v) -> str:
    if pd.isna(v):
        return "n/a"
    if metric in ("ctr", "cvr"):
        return f"{v * 100:.2f}%"
    if metric in ("spend", "revenue"):
        return f"{v:,.2f}"
    return f"{v:,.0f}"


EVAL_DIR = C.ROOT / "reports" / "evaluation"


@st.cache_data(show_spinner=False)
def load_evaluation_report():
    """Read the saved outputs of `python -m scripts.run_evaluation`. Returns
    None if the report hasn't been generated yet; this tab never runs the
    evaluation itself, it only displays what was last saved to disk."""
    needed = ["synthetic_metrics.json", "ps04_metrics.json", "alert_fatigue_comparison.csv",
              "synthetic_incident_results.csv"]
    if not all((EVAL_DIR / f).exists() for f in needed):
        return None
    syn = json.loads((EVAL_DIR / "synthetic_metrics.json").read_text())
    ps04 = json.loads((EVAL_DIR / "ps04_metrics.json").read_text())
    fatigue_cmp = pd.read_csv(EVAL_DIR / "alert_fatigue_comparison.csv")
    incidents = pd.read_csv(EVAL_DIR / "synthetic_incident_results.csv")
    return syn, ps04, fatigue_cmp, incidents


def download(df: pd.DataFrame, name: str, label: str = "Download CSV"):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=name,
                       mime="text/csv", key=f"dl_{name}")


def show_table(df: pd.DataFrame, height: int = 380):
    st.dataframe(
        df, **FULL, hide_index=True, height=height,
        column_config={
            "date": st.column_config.DateColumn("Date"),
            "start_date": st.column_config.DateColumn("Start"),
            "end_date": st.column_config.DateColumn("End"),
            "evidence_score": st.column_config.ProgressColumn(
                "Evidence (heuristic)", min_value=0, max_value=1, format="%.2f"),
            "max_evidence": st.column_config.ProgressColumn(
                "Max evidence (heuristic)", min_value=0, max_value=1, format="%.2f"),
            "pct_change": st.column_config.NumberColumn("% change", format="percent"),
            "z": st.column_config.NumberColumn("Robust z", format="%+.1f"),
            "explanation": st.column_config.TextColumn("Explanation", width="large"),
            "diagnostic_action": st.column_config.TextColumn("First check", width="medium"),
        })


try:
    metrics, metadata = load_data(str(C.PS04_FILE))
except FileNotFoundError:
    st.error(f"Dataset not found at `{C.PS04_FILE.relative_to(C.ROOT)}`. "
             "Place the organizer-supplied `daily_campaign_metrics.csv` there and reload.")
    st.stop()
except ValueError as e:
    st.error(f"Dataset schema check failed: {e}")
    st.stop()

try:
    records, episodes = run_pipeline(metrics, metadata)
except Exception as e:  # show, don't crash the demo
    st.error(f"Detection pipeline failed: {e}")
    st.stop()

episodes = episodes.merge(metadata, on="campaign_id", how="left")

# ------------------------------------------------------------- sidebar ----
st.sidebar.title("📡 Adomaly")
st.sidebar.caption("PS-04 · Campaign anomaly alerting without alert fatigue")


def ms(label, options, key):
    return st.sidebar.multiselect(label, options, default=[], key=key,
                                  placeholder="All")


channels = ms("Channel", sorted(metadata["channel"].dropna().unique()), "f_channel")
verticals = ms("Vertical", sorted(metadata["vertical"].dropna().unique()), "f_vertical")
meta_f = metadata
if channels:
    meta_f = meta_f[meta_f["channel"].isin(channels)]
if verticals:
    meta_f = meta_f[meta_f["vertical"].isin(verticals)]
camps = ms("Campaign", meta_f["campaign_id"].tolist(), "f_campaign")
if camps:
    meta_f = meta_f[meta_f["campaign_id"].isin(camps)]
sel_ids = meta_f["campaign_id"].tolist()

dmin, dmax = metrics["date"].min().date(), metrics["date"].max().date()
dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
d0, d1 = (pd.Timestamp(dr[0]), pd.Timestamp(dr[1])) if len(dr) == 2 else (pd.Timestamp(dmin), pd.Timestamp(dmax))

st.sidebar.divider()
st.sidebar.caption(
    f"Detector: rolling {CFG.window}-day median/MAD per campaign, weekday-adjusted, "
    f"history strictly before each day. Anomaly if |z| ≥ {CFG.z_threshold}; "
    f"Alert if evidence ≥ {CFG.alert_evidence}, else Human Review. "
    "Filters change the view only; detection always runs on the full dataset.")

m_view = metrics[metrics["campaign_id"].isin(sel_ids) & metrics["date"].between(d0, d1)]
r_view = records[records["campaign_id"].isin(sel_ids) & records["date"].between(d0, d1)]
flagged = r_view[r_view["route"] != NO_ALERT]
ep_view = episodes[episodes["campaign_id"].isin(sel_ids)
                   & (episodes["end_date"] >= d0) & (episodes["start_date"] <= d1)]

# -------------------------------------------------------------- header ----
st.title("Adomaly — Campaign Anomaly Monitor")
st.caption(
    "Data: organizer-supplied PS-04 `daily_campaign_metrics.csv`. This dataset has **no ground-truth "
    "labels**, so flags are statistical signals for investigation, not confirmed incidents. "
    "Evidence strength is a heuristic ranking score, **not** a calibrated probability.")

if m_view.empty:
    st.warning("No data matches the current filters. Widen the channel, vertical, campaign or date filters.")
    st.stop()

tabs = st.tabs(["Overview", "Campaign explorer", "Anomalies", "Alert routing",
                "Alert fatigue", "Evaluation", "About & limitations"])

# ------------------------------------------------------------ overview ----
with tabs[0]:
    c = st.columns(6)
    c[0].metric("Campaigns", m_view["campaign_id"].nunique())
    c[1].metric("Observations", f"{len(m_view):,}", help="Campaign-days in view")
    c[2].metric("Spend", f"{m_view['spend'].sum():,.0f}")
    c[3].metric("Clicks", f"{m_view['clicks'].sum():,.0f}")
    c[4].metric("Conversions", f"{m_view['conversions'].sum():,.0f}")
    rev_ids = meta_f.loc[meta_f["vertical"] != "b2b", "campaign_id"]
    rev_m = m_view[m_view["campaign_id"].isin(rev_ids)]
    if rev_m.empty:
        c[5].metric("Revenue", "n/a", help="B2B campaigns report zero revenue (leads, not sales).")
    else:
        roas = rev_m["revenue"].sum() / rev_m["spend"].sum() if rev_m["spend"].sum() > 0 else float("nan")
        c[5].metric("Revenue (non-B2B)", f"{rev_m['revenue'].sum():,.0f}",
                    f"ROAS {roas:.2f}" if pd.notna(roas) else None, delta_color="off",
                    help="B2B campaigns record zero revenue by design, so revenue and ROAS cover non-B2B campaigns only.")

    c = st.columns(4)
    c[0].metric("Flagged records", f"{len(flagged):,}",
                help="Campaign-day-metric records routed to Alert or Human Review")
    c[1].metric("Alerts", int((flagged["route"] == ALERT).sum()))
    c[2].metric("Human review", int((flagged["route"] == REVIEW).sum()))
    c[3].metric("Episodes", len(ep_view))

    left, right = st.columns(2)
    daily = m_view.groupby("date", as_index=False)[["spend", "conversions"]].sum()
    fig = px.area(daily, x="date", y="spend", title="Total daily spend")
    fig.update_layout(height=320, margin=dict(t=50, b=10), xaxis_title=None)
    left.plotly_chart(fig, **FULL)

    by_c = (m_view.groupby("campaign_id", as_index=False)[["spend", "conversions"]].sum()
            .merge(metadata, on="campaign_id"))
    fig = px.bar(by_c.sort_values("spend"), x="spend", y="campaign_id", color="vertical",
                 orientation="h", title="Spend by campaign", hover_data=["campaign_name", "channel"])
    fig.update_layout(height=320, margin=dict(t=50, b=10), yaxis_title=None)
    right.plotly_chart(fig, **FULL)

    show_table(by_c[["campaign_id", "campaign_name", "channel", "vertical",
                     "landing_page_group", "spend", "conversions"]], height=260)

# ------------------------------------------------------------ explorer ----
with tabs[1]:
    a, b = st.columns([1, 2])
    cid = a.selectbox("Campaign", sel_ids,
                      format_func=lambda x: f"{x} · {metadata.set_index('campaign_id').at[x, 'campaign_name']}")
    metric_opts = list(CFG.metrics)
    mets = b.multiselect("Metrics", metric_opts, default=["spend", "conversions", "ctr"],
                         format_func=lambda m: LABEL.get(m, m))
    meta_row = metadata.set_index("campaign_id").loc[cid]
    st.caption(f"Channel **{meta_row['channel']}** · vertical **{meta_row['vertical']}** · "
               f"landing page group **{meta_row['landing_page_group']}**")
    if not mets:
        st.info("Select at least one metric.")
    for m in mets:
        s = r_view[(r_view["campaign_id"] == cid) & (r_view["metric"] == m)].sort_values("date")
        if s.empty:
            st.info(f"No {LABEL.get(m, m)} data for {cid} in this range.")
            continue
        if m == "revenue" and meta_row["vertical"] == "b2b":
            st.info("Revenue is zero for B2B campaigns by design (lead generation). It is scored "
                    "safely (baseline 0, z = 0) and never flagged.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s["date"], y=s["observed"], name="Observed",
                                 mode="lines", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=s["date"], y=s["baseline"], name="Expected (baseline)",
                                 mode="lines", line=dict(dash="dot", width=1.5)))
        for route in (REVIEW, ALERT):
            f = s[s["route"] == route]
            if not f.empty:
                fig.add_trace(go.Scatter(
                    x=f["date"], y=f["observed"], mode="markers", name=route,
                    marker=dict(size=11, color=ROUTE_COLORS[route], line=dict(width=1, color="white")),
                    customdata=f[["severity", "z", "evidence_score", "notification"]],
                    hovertemplate="%{x|%Y-%m-%d}<br>severity %{customdata[0]}<br>z %{customdata[1]:+.1f}"
                                  "<br>evidence %{customdata[2]:.2f}<br>%{customdata[3]}<extra></extra>"))
        fig.update_layout(title=LABEL.get(m, m), height=300, margin=dict(t=45, b=10),
                          legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                          yaxis_tickformat=".2%" if m in ("ctr", "cvr") else None)
        st.plotly_chart(fig, **FULL)

# ----------------------------------------------------------- anomalies ----
with tabs[2]:
    if flagged.empty:
        st.success("No anomalies flagged for the current filters.")
    else:
        a, b, c = st.columns(3)
        f_metric = a.multiselect("Metric", sorted(flagged["metric"].unique()),
                                 format_func=lambda m: LABEL.get(m, m), placeholder="All")
        f_sev = b.multiselect("Severity", [s for s in SEV_ORDER if s in set(flagged["severity"])],
                              placeholder="All")
        f_route = c.multiselect("Route", [ALERT, REVIEW], placeholder="All")
        f = flagged
        if f_metric:
            f = f[f["metric"].isin(f_metric)]
        if f_sev:
            f = f[f["severity"].isin(f_sev)]
        if f_route:
            f = f[f["route"].isin(f_route)]
        f = f.sort_values(["evidence_score", "date"], ascending=[False, False])

        left, right = st.columns(2)
        cnt = f.groupby(["metric", "severity"]).size().reset_index(name="count")
        cnt["metric"] = cnt["metric"].map(lambda m: LABEL.get(m, m))
        fig = px.bar(cnt, x="metric", y="count", color="severity", title="Flags by metric and severity",
                     category_orders={"severity": SEV_ORDER},
                     color_discrete_map={"high": "#d64545", "medium": "#e0a030", "low": "#6b8fd6"})
        fig.update_layout(height=300, margin=dict(t=50, b=10), xaxis_title=None)
        left.plotly_chart(fig, **FULL)
        fig = px.scatter(f, x="date", y="campaign_id", color="route", symbol="metric",
                         color_discrete_map=ROUTE_COLORS, title="When and where flags occurred",
                         hover_data=["metric", "severity", "evidence_score"])
        fig.update_layout(height=300, margin=dict(t=50, b=10), yaxis_title=None, xaxis_title=None)
        right.plotly_chart(fig, **FULL)

        st.subheader(f"{len(f):,} flagged records")
        out = f[FLAG_COLS].copy()
        out["observed"] = [fmt_value(m, v) for m, v in zip(out["metric"], out["observed"])]
        out["baseline"] = [fmt_value(m, v) for m, v in zip(out["metric"], out["baseline"])]
        show_table(out)
        download(f[FLAG_COLS], "adomaly_flagged_records.csv")

# ------------------------------------------------------------- routing ----
with tabs[3]:
    scored = r_view[r_view["status"] == "scored"]
    counts = r_view["route"].value_counts().reindex([ALERT, REVIEW, NO_ALERT], fill_value=0)
    c = st.columns(4)
    c[0].metric("🔴 Alert", int(counts[ALERT]))
    c[1].metric("🟠 Human review", int(counts[REVIEW]))
    c[2].metric("⚪ No alert", f"{int(counts[NO_ALERT]):,}")
    c[3].metric("Not scored", f"{int((r_view['status'] != 'scored').sum()):,}",
                help="Insufficient history or missing value; routed to No Alert by the pipeline.")
    st.caption(
        f"Routing rule (src/scoring.py): a scored record is anomalous if |robust z| ≥ {CFG.z_threshold}. "
        f"Anomalous records with evidence ≥ {CFG.alert_evidence} go to **Alert**; others go to **Human Review**. "
        "Evidence = magnitude × history sufficiency × data quality, each in [0, 1].")

    left, right = st.columns([1, 2])
    fig = px.bar(x=counts.index[:2], y=counts.values[:2], color=counts.index[:2],
                 color_discrete_map=ROUTE_COLORS, title="Flagged records by route")
    fig.update_layout(height=320, showlegend=False, margin=dict(t=50, b=10),
                      xaxis_title=None, yaxis_title="records")
    left.plotly_chart(fig, **FULL)
    anom = scored[scored["is_anomaly"]]
    if anom.empty:
        right.info("No anomalous scored records in view.")
    else:
        fig = px.scatter(anom, x=anom["z"].abs(), y="evidence_score", color="route",
                         color_discrete_map=ROUTE_COLORS, hover_data=["campaign_id", "metric", "date"],
                         title="Why each case was routed: |z| vs evidence strength",
                         labels={"x": "|robust z|", "evidence_score": "evidence (heuristic)"})
        fig.add_hline(y=CFG.alert_evidence, line_dash="dash", annotation_text="Alert threshold")
        fig.update_layout(height=320, margin=dict(t=50, b=10))
        right.plotly_chart(fig, **FULL)

    for route, title in ((ALERT, "🔴 Alerts"), (REVIEW, "🟠 Human review queue")):
        sub = r_view[r_view["route"] == route].sort_values("evidence_score", ascending=False)
        st.subheader(f"{title} ({len(sub)})")
        if sub.empty:
            st.caption("None in the current view.")
            continue
        cols = ["date", "campaign_id", "metric", "severity", "z", "evidence_score",
                "magnitude_score", "history_score", "quality_score", "explanation", "diagnostic_action"]
        show_table(sub[cols], height=300)
        download(sub[cols], f"adomaly_{route.lower().replace(' ', '_')}.csv")

# ------------------------------------------------------- alert fatigue ----
with tabs[4]:
    st.caption(
        "Episodes (src/episodes.py): consecutive flagged days for the same campaign, metric and direction, "
        f"allowing up to {CFG.max_gap_days} quiet day(s). Only the first day notifies; later days are "
        "suppressed unless severity rises or the route upgrades Human Review → Alert (escalation).")
    notes = flagged["notification"].value_counts()
    n_new, n_esc, n_sup = int(notes.get("new", 0)), int(notes.get("escalation", 0)), int(notes.get("suppressed", 0))
    sent = n_new + n_esc
    c = st.columns(5)
    c[0].metric("Flagged days", len(flagged), help="What naive per-day alerting would send")
    c[1].metric("Notifications sent", sent)
    c[2].metric("New episodes", n_new)
    c[3].metric("Escalations", n_esc)
    c[4].metric("Suppressed repeats", n_sup,
                f"-{n_sup / len(flagged):.0%} notifications" if len(flagged) else None, delta_color="inverse")
    if flagged.empty:
        st.success("No flagged records, so no episodes in the current view.")
    else:
        left, right = st.columns(2)
        fun = pd.DataFrame({"stage": ["Flagged days", "Notifications sent"], "count": [len(flagged), sent]})
        fig = px.bar(fun, x="stage", y="count", text="count", title="Notification burden: per-day vs episodes")
        fig.update_layout(height=320, margin=dict(t=50, b=10), xaxis_title=None)
        left.plotly_chart(fig, **FULL)
        if not ep_view.empty:
            g = ep_view.copy()
            g["end_plot"] = g["end_date"] + pd.Timedelta(days=1)
            g["label"] = g["campaign_id"] + " · " + g["metric"]
            fig = px.timeline(g, x_start="start_date", x_end="end_plot", y="label", color="top_route",
                              color_discrete_map=ROUTE_COLORS, title="Episode timeline",
                              hover_data=["episode_id", "flagged_days", "peak_severity", "notifications", "suppressed"])
            fig.update_layout(height=max(320, 22 * g["label"].nunique()), margin=dict(t=50, b=10), yaxis_title=None)
            right.plotly_chart(fig, **FULL)
        st.caption("Note: suppression counts are what the episode logic *would* withhold; this prototype "
                   "does not send real notifications.")
        st.subheader(f"Episodes ({len(ep_view)})")
        ep_cols = ["episode_id", "campaign_id", "campaign_name", "metric", "direction", "start_date",
                   "end_date", "flagged_days", "peak_severity", "peak_abs_z", "max_evidence",
                   "top_route", "notifications", "suppressed"]
        show_table(ep_view.sort_values("start_date")[ep_cols], height=320)
        download(ep_view[ep_cols], "adomaly_episodes.csv")

        eid = st.selectbox("Inspect episode", ep_view.sort_values("start_date")["episode_id"])
        det = r_view[r_view["episode_id"] == eid].sort_values("date")
        show_table(det[["date", "metric", "severity", "route", "notification", "evidence_score",
                        "explanation"]], height=220)

# ----------------------------------------------------------- evaluation ----
with tabs[5]:
    report = load_evaluation_report()
    if report is None:
        st.info("No saved evaluation report yet. Generate one with:\n\n"
                "```\npython -m scripts.run_evaluation\n```\n\n"
                "This writes `reports/evaluation/` and this tab reads it from there — "
                "it never re-runs the evaluation itself.")
    else:
        syn, ps04, fatigue_cmp, incidents = report
        rl = syn["record_level"]
        inc_level = syn["incident_level"]

        st.markdown("#### 🔬 Synthetic benchmark — *designed scenarios, not real incidents*")
        st.caption(
            "Precision/recall/F1 and detection rate are measured **only** on this labelled "
            "synthetic benchmark's held-out EVAL split, and only over metrics a label targets "
            "(spend, conversions, ctr). They say nothing about real-world accuracy.")
        c = st.columns(5)
        c[0].metric("Precision", f"{rl['precision']*100:.0f}%" if rl["precision"] == rl["precision"] else "n/a")
        c[1].metric("Recall", f"{rl['recall']*100:.0f}%" if rl["recall"] == rl["recall"] else "n/a")
        c[2].metric("F1", f"{rl['f1']:.2f}" if rl["f1"] == rl["f1"] else "n/a")
        c[3].metric("Incident detection rate",
                    f"{inc_level['detection_rate_eval']*100:.0f}%",
                    help="Share of EVAL-split incidents with >=1 flagged record on the mapped "
                         "metric inside their window (Alert or Human Review both count).")
        c[4].metric("Median detection delay",
                    f"{inc_level['median_delay_days_eval']:.0f} d" if inc_level['median_delay_days_eval'] == inc_level['median_delay_days_eval'] else "n/a",
                    help="Days from an incident's documented start to its first flag.")
        st.caption(f"TP={rl['tp']} · FP={rl['fp']} · FN={rl['fn']} · TN={rl['tn']} "
                   f"(evaluated on {rl['n_evaluated']} campaign-day-metric records, "
                   f"{rl['n_unmapped_metric_flags']} unmapped-metric flags excluded from scoring)")

        show_table(incidents[["incident_id", "campaign_id", "incident_type", "mapped_metric",
                              "severity", "period", "detected", "delay_days"]], height=240)

        st.divider()
        st.markdown("#### 🚨 Alert fatigue — synthetic vs **official PS-04 dataset**")
        st.caption(
            "Volume behaviour only (no accuracy claim for PS-04, which has no ground-truth "
            "labels). Shows how many raw per-day flags collapse into actual notifications.")
        disp = fatigue_cmp.copy()
        disp["notification_reduction_pct"] = disp["notification_reduction_pct"].map(
            lambda v: f"{v:.0f}%" if pd.notna(v) else "n/a")
        show_table(disp[["dataset", "raw_flagged_records", "notifications_sent",
                         "suppressed_repeats", "notification_reduction_pct"]], height=160)
        fig = px.bar(fatigue_cmp, x="dataset", y=["raw_flagged_records", "notifications_sent"],
                     barmode="group", title="Raw flags vs notifications sent, by dataset")
        fig.update_layout(height=300, margin=dict(t=50, b=10), xaxis_title=None, yaxis_title="records")
        st.plotly_chart(fig, **FULL)

        st.caption(
            "Full metric definitions, assumptions and limitations: `reports/evaluation/report.md` "
            "(regenerate with `python -m scripts.run_evaluation`).")

# --------------------------------------------------------------- about ----
with tabs[6]:
    st.markdown(f"""
**What Adomaly does on this dataset**
- Builds a campaign-specific baseline for each metric (spend, impressions, clicks, conversions, revenue,
  CTR, CVR) from the previous {CFG.window} days only, using median and MAD with a weekday/weekend adjustment.
- Scores each day with a robust z-score, an explainable evidence-strength score, and routes it to
  Alert, Human Review or No Alert.
- Groups repeated flags into episodes and suppresses duplicate notifications, escalating only when an
  episode gets worse.

**Limitations**
- The PS-04 dataset has **no ground-truth labels**. Flags are not confirmed incidents, and precision/recall
  cannot be measured on it. Quantitative evaluation exists only on the separate synthetic benchmark,
  which shows behaviour on designed scenarios, not real-world performance.
- Evidence strength is a transparent heuristic for ordering and routing, **not** a probability.
- The first {CFG.min_history} days of each campaign have insufficient history and are not scored.
- Thresholds were chosen on the synthetic benchmark's development period and were not re-tuned for
  this dataset.
- B2B campaigns report zero revenue by design; revenue is scored safely but carries no signal for them.
""")
    download(records, "adomaly_all_records.csv", "Download all scored records (CSV)")
