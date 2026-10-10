"""
dashboard.py

Streamlit Web Dashboard for PS-04: Campaign Anomaly Alerting Without Alert Fatigue.
Interactive visualization of 20 campaigns across 180 days with incident detection,
plain-English diagnostics, and episode clustering.

Run with:  streamlit run dashboard.py
"""

import sys
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from detect import run_detection, cluster_incident_episodes
from generate_data import load_and_preprocess_ps04_data

st.set_page_config(
    page_title="PS-04 Campaign Anomaly Monitor",
    page_icon="🛡️",
    layout="wide"
)


@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect("data/campaign_data.db")
        df = pd.read_sql("SELECT * FROM campaign_metrics", conn)
        conn.close()
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        df = load_and_preprocess_ps04_data()
    return df


@st.cache_data
def compute_alerts(df):
    return run_detection(df)


# Header
st.title("🛡️ PS-04: Campaign Anomaly Alerting (Zero Alert Fatigue)")
st.caption(
    "Intelligent marketing performance monitoring across 20 campaigns & 180 days (3,600 campaign-days). "
    "Features B2B weekend seasonality filtering, small-campaign noise suppression, and plain-English root-cause explanations."
)

df = load_data()
alerts = compute_alerts(df)
episodes = cluster_incident_episodes(alerts)

# ---- Sidebar Controls ----
st.sidebar.header("🔍 Filters & Controls")

vertical_filter = st.sidebar.selectbox("Vertical", ["All Verticals", "ecommerce", "b2b"])
if vertical_filter != "All Verticals":
    filtered_df = df[df["vertical"] == vertical_filter]
else:
    filtered_df = df

channels = sorted(filtered_df["channel"].unique())
channel = st.sidebar.selectbox("Channel", ["All Channels"] + channels)
if channel != "All Channels":
    filtered_df = filtered_df[filtered_df["channel"] == channel]

campaigns = sorted(filtered_df["campaign_name"].unique())
campaign = st.sidebar.selectbox("Campaign", campaigns)

metric_options = ["spend", "conversions", "clicks", "impressions", "revenue", "cvr", "ctr", "cpc", "roas"]
metric = st.sidebar.selectbox("Metric to Plot", metric_options, index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("Chart Overlays")
show_baseline = st.sidebar.checkbox("Show 14-Day Trailing Baseline", value=True)
show_anomalies = st.sidebar.checkbox("Overlay Anomaly Markers", value=True)

# ---- Top KPI Summary Cards ----
col1, col2, col3, col4 = st.columns(4)
total_days = len(df)
alert_rate = (len(alerts) / total_days) * 100
col1.metric("Campaign-Days Monitored", f"{total_days:,}")
col2.metric("Total Alerts Fired", f"{len(alerts)} ({alert_rate:.2f}% rate)")
col3.metric("Verified Incident Episodes", f"{len(episodes)} incidents")
col4.metric("Alert Silence Rate", f"{(100.0 - alert_rate):.2f}% (No Fatigue)")

# ---- Visual Time Series ----
st.markdown("---")
st.subheader(f"📈 {campaign} — Metric: `{metric.upper()}`")

sub = df[df["campaign_name"] == campaign].sort_values("date").copy()
sub_alerts = alerts[alerts["campaign_name"] == campaign] if not alerts.empty else pd.DataFrame()

fig = go.Figure()

# Base actual values
fig.add_trace(go.Scatter(
    x=sub["date"], y=sub[metric],
    mode="lines+markers",
    name=f"Actual {metric.upper()}",
    line=dict(color="#1E88E5", width=2),
    marker=dict(size=4)
))

# Trailing baseline (rolling median)
if show_baseline:
    sub["baseline_line"] = sub[metric].rolling(14, min_periods=7).median()
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["baseline_line"],
        mode="lines",
        name="14-Day Baseline",
        line=dict(color="#757575", width=1.5, dash="dash")
    ))

# Overlay incident markers
if show_anomalies and not sub_alerts.empty:
    # Match dates to actual metric values for plotting
    merged_alerts = pd.merge(sub_alerts, sub[["date", metric]], on="date", how="inner")
       # Critical markers
    crit = merged_alerts[merged_alerts["severity"] == "CRITICAL"]
    if not crit.empty:
        fig.add_trace(go.Scatter(
            x=crit["date"], y=crit[metric],
            mode="markers",
            name="CRITICAL Incident",
            marker=dict(color="#D50000", size=14, symbol="x", line=dict(width=2)),
            text=crit["explanation"],
            hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Value:</b> %{y}<br><b>Diagnosis:</b> %{text}<extra></extra>"
        ))

    # High markers
    high = merged_alerts[merged_alerts["severity"] == "HIGH"]
    if not high.empty:
        fig.add_trace(go.Scatter(
            x=high["date"], y=high[metric],
            mode="markers",
            name="HIGH Incident",
            marker=dict(color="#FF6D00", size=13, symbol="diamond-open", line=dict(width=2)),
            text=high["explanation"],
            hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Value:</b> %{y}<br><b>Diagnosis:</b> %{text}<extra></extra>"
        ))

fig.update_layout(
    height=440,
    margin=dict(l=20, r=20, t=30, b=20),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

# ---- Tabs for Incident Episodes & Live Alert Feed ----
tab1, tab2 = st.tabs(["🚨 Verified Incident Episodes Catalog", "📋 Daily Alert Feed & Diagnostics"])

with tab1:
    st.markdown("### Clustered Multi-Day Incident Episodes")
    st.caption("Contiguous days where the same problem persisted are aggregated into unified incidents to prevent spam.")
    
    for idx, ep in episodes.iterrows():
        color_badge = "🔴" if ep["severity"] == "CRITICAL" else "🟠"
        with st.expander(f"{color_badge} [{ep['severity']}] {ep['start_date']} to {ep['end_date']} ({ep['duration_days']} Day{'s' if ep['duration_days']>1 else ''}) — {ep['campaign_name']}"):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Channel:** {ep['channel']}")
            c2.markdown(f"**Incident Type:** {ep['incident_type']}")
            c3.markdown(f"**Duration:** {ep['duration_days']} consecutive days")
            st.markdown(f"**Impact Diagnosis:** {ep['summary']}")
            st.markdown(f"**Recommended Action:** `{ep['recommended_action']}`")

with tab2:
    st.markdown("### Daily Alert Feed")
    if alerts.empty:
        st.info("No anomalies detected.")
    else:
        filter_curr = st.checkbox("Show alerts for currently selected campaign only", value=False)
        display_df = alerts.copy()
        if filter_curr:
            display_df = display_df[display_df["campaign_name"] == campaign]

        view_cols = ["date", "severity", "campaign_name", "incident_type", "change_pct", "actual_value", "normal_baseline", "explanation"]
        st.dataframe(
            display_df[view_cols],
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")
st.caption(
    "PS-04 Campaign Anomaly Alerting Solution | Engineered with B2B weekend seasonality adjustment & alert fatigue suppression."
)
