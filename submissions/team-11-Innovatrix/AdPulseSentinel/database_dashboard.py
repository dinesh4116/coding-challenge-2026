from streamlit_autorefresh import st_autorefresh
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from database import get_connection, initialize_database


# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(
    page_title="AdPulse Sentinel Live Data",
    page_icon="🛡️",
    layout="wide"
)

# -------------------------------
# AUTOMATIC REFRESH EVERY 5 SECONDS
# -------------------------------
st_autorefresh(
    interval=5000,
    limit=None,
    key="adpulse_refresh"
)


# -------------------------------
# LOAD INCIDENTS FROM DATABASE
# -------------------------------
def load_incidents():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT
                id AS 'Incident ID',
                campaign AS Campaign,
                severity AS Severity,
                description AS Description,
                status AS Status,
                event_time AS 'Event Time'
            FROM incidents
            ORDER BY id DESC
        """, conn)


# -------------------------------
# LOAD CAMPAIGN EVENTS
# -------------------------------
def load_campaign_events():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT
                id AS 'Event ID',
                campaign AS Campaign,
                spend AS Spend,
                clicks AS Clicks,
                conversions AS Conversions,
                event_time AS 'Event Time'
            FROM campaign_events
            ORDER BY id DESC
        """, conn)


# -------------------------------
# INITIALIZE DATABASE
# -------------------------------
initialize_database()


# -------------------------------
# DASHBOARD HEADER
# -------------------------------
st.title("🛡️ AdPulse Sentinel")
st.caption(
    "Real-time campaign monitoring and security incident dashboard"
)

st.success("Database connected. Dashboard refreshes every 5 seconds.")


# -------------------------------
# MANUAL REFRESH BUTTON
# -------------------------------
if st.button("🔄 Refresh Now"):
    st.rerun()


# -------------------------------
# READ LATEST DATABASE DATA
# -------------------------------
incidents = load_incidents()
events = load_campaign_events()


# -------------------------------
# CALCULATE METRICS
# -------------------------------
total_events = len(events)
total_incidents = len(incidents)

open_count = 0
high_count = 0
medium_count = 0
resolved_count = 0

if not incidents.empty:
    open_count = int(
        (incidents["Status"] == "Open").sum()
    )

    high_count = int(
        (incidents["Severity"] == "High").sum()
    )

    medium_count = int(
        (incidents["Severity"] == "Medium").sum()
    )

    resolved_count = int(
        (incidents["Status"] == "Resolved").sum()
    )


# -------------------------------
# METRIC CARDS
# -------------------------------
st.subheader("📊 Live Overview")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Saved Campaign Events",
    total_events
)

col2.metric(
    "Total Incidents",
    total_incidents
)

col3.metric(
    "Open Incidents",
    open_count
)

col4, col5, col6 = st.columns(3)

col4.metric(
    "High-Severity Incidents",
    high_count
)

col5.metric(
    "Medium-Severity Incidents",
    medium_count
)

col6.metric(
    "Resolved Incidents",
    resolved_count
)


# -------------------------------
# INCIDENT CENTER
# -------------------------------
st.divider()
st.subheader("🚨 Recent Incidents")

if incidents.empty:
    st.info("No incidents recorded yet.")
else:
    st.dataframe(
        incidents,
        use_container_width=True,
        hide_index=True
    )


# -------------------------------
# CAMPAIGN EVENT TABLE
# -------------------------------
st.divider()
st.subheader("📡 Latest Campaign Events")

if events.empty:
    st.info("No campaign events recorded yet.")
else:
    st.dataframe(
        events.head(20),
        use_container_width=True,
        hide_index=True
    )


# -------------------------------
# CAMPAIGN SPENDING CHART
# -------------------------------
st.divider()
st.subheader("💰 Campaign Spending")

if not events.empty:
    spending = (
        events.groupby("Campaign", as_index=False)["Spend"]
        .sum()
        .sort_values("Spend", ascending=False)
    )

    st.bar_chart(
        spending,
        x="Campaign",
        y="Spend"
    )
else:
    st.info("Spending data will appear when events are generated.")


# -------------------------------
# INCIDENT SEVERITY SUMMARY
# -------------------------------
st.divider()
st.subheader("🛡️ Incident Severity Summary")

if not incidents.empty:
    severity_summary = (
        incidents["Severity"]
        .value_counts()
        .rename_axis("Severity")
        .reset_index(name="Count")
    )

    st.bar_chart(
        severity_summary,
        x="Severity",
        y="Count"
    )
else:
    st.info("No incident severity data available yet.")


# -------------------------------
# DOWNLOAD REPORTS
# -------------------------------
st.divider()
st.subheader("📥 Download Reports")

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="Download Incident Report (CSV)",
        data=incidents.to_csv(index=False).encode("utf-8"),
        file_name="adpulse_incidents.csv",
        mime="text/csv"
    )

with col2:
    st.download_button(
        label="Download Campaign Events (CSV)",
        data=events.to_csv(index=False).encode("utf-8"),
        file_name="adpulse_campaign_events.csv",
        mime="text/csv"
    )


# -------------------------------
# FOOTER
# -------------------------------
st.divider()

st.caption(
    "AdPulse Sentinel | SQLite Database | "
    "Automatic refresh interval: 5 seconds"
)
