
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from database import get_connection, initialize_database
from utils.data_loader import load_campaign_data, load_security_data
from modules.anomaly_detector import detect_campaign_anomalies
from modules.cyber_detector import detect_cyber_threats
from modules.alert_correlator import correlate_alerts
from modules.risk_scorer import calculate_risk, get_risk_level
from modules.recommendation_engine import generate_recommendations


# =====================================================
# 1. CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="AdPulse Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PAGES = [
    "Home",
    "Campaign Intelligence",
    "Cyber Play Lab",
    "Incident Center",
    "Analytics",
    "Activity & Reports"
]

ICONS = {
    "Home": "⌂",
    "Campaign Intelligence": "◈",
    "Cyber Play Lab": "⚡",
    "Incident Center": "🛡",
    "Analytics": "▥",
    "Activity & Reports": "▤"
}

SHORT_NAMES = {
    "Home": "Home",
    "Campaign Intelligence": "Campaigns",
    "Cyber Play Lab": "Cyber Lab",
    "Incident Center": "Incidents",
    "Analytics": "Analytics",
    "Activity & Reports": "Reports"
}

# Initialize the existing SQLite database.
initialize_database()

# Refresh the app every five seconds.
st_autorefresh(
    interval=5000,
    limit=None,
    key="adpulse_main_refresh"
)


# =====================================================
# 2. SESSION STATE
# =====================================================

defaults = {
    "authenticated": False,
    "current_page": "Home",
    "sidebar_page": "Home",
    "demo_alerts": [],
    "incident_status": {},
    "activity_log": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def navigate(page):
    st.session_state.current_page = page
    st.session_state.sidebar_page = page


def sidebar_changed():
    st.session_state.current_page = st.session_state.sidebar_page


def logout():
    st.session_state.authenticated = False
    st.session_state.current_page = "Home"
    st.session_state.sidebar_page = "Home"


def record_activity(message):
    st.session_state.activity_log.insert(0, {
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Activity": message
    })


# =====================================================
# 3. CYBER THEME
# =====================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(
            circle at 85% 0%,
            rgba(87, 45, 145, 0.15),
            transparent 32%
        ),
        #080b14;
    color: #edf2ff;
}

[data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #29334d;
}

h1, h2, h3 {
    color: #edf2ff !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #111a2d, #1d1632);
    border: 1px solid #29334d;
    border-radius: 14px;
    padding: 17px;
}

[data-testid="stMetricLabel"] {
    color: #a6b4ce !important;
}

[data-testid="stMetricValue"] {
    color: #67e8f9 !important;
}

div.stButton > button {
    background: #131d31;
    color: #edf2ff;
    border: 1px solid #35456b;
    border-radius: 9px;
    min-height: 40px;
    transition: 0.2s;
}

div.stButton > button:hover {
    border-color: #67e8f9;
    color: #67e8f9;
}

div[data-testid="stForm"] {
    background: #101727;
    border: 1px solid #29334d;
    border-radius: 16px;
    padding: 20px;
}

.hero {
    background: linear-gradient(120deg, #102b43, #2a194b);
    border: 1px solid #35456b;
    border-radius: 18px;
    padding: 30px;
    margin-bottom: 20px;
}

.card {
    background: #101727;
    border: 1px solid #29334d;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
}

.eyebrow {
    color: #67e8f9;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
}

.muted {
    color: #a6b4ce;
}

.status-pill {
    display: inline-block;
    padding: 5px 12px;
    border: 1px solid #247b73;
    border-radius: 20px;
    background: rgba(16, 185, 129, 0.08);
    color: #6ee7b7;
    font-size: 12px;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# 4. LOAD LIVE DATA FROM SQLITE
# =====================================================

def load_data():
    with get_connection() as conn:
        campaign_events = pd.read_sql_query("""
            SELECT id, campaign, spend, clicks,
                   conversions, event_time
            FROM campaign_events
            ORDER BY id DESC
        """, conn)

        security_events = pd.read_sql_query("""
            SELECT id, campaign, clicks_per_minute,
                   repeated_requests, event_time
            FROM security_events
            ORDER BY id DESC
        """, conn)

        db_incidents = pd.read_sql_query("""
            SELECT id, campaign, severity, description,
                   status, event_time
            FROM incidents
            ORDER BY id DESC
        """, conn)

    # Keep the CSV files as a fallback when the database
    # has no events yet.
    if campaign_events.empty:
        campaigns = load_campaign_data()
        campaigns["event_time"] = "CSV sample data"
        campaign_events = campaigns.copy()

    if security_events.empty:
        security_events = load_security_data().copy()
        security_events["event_time"] = "CSV sample data"

    # Apply demonstration thresholds for the existing
    # campaign anomaly detection module.
    if "spend_limit" not in campaign_events.columns:
        campaign_events["spend_limit"] = 5000

    if "click_limit" not in campaign_events.columns:
        campaign_events["click_limit"] = 1000

    if "conversion_min" not in campaign_events.columns:
        campaign_events["conversion_min"] = 10

    # Use the latest record for each campaign on the main
    # overview screens. Keep all records for event reports.
    latest_campaigns = (
        campaign_events
        .drop_duplicates(subset=["campaign"], keep="first")
        .copy()
    )

    latest_security = (
        security_events
        .drop_duplicates(subset=["campaign"], keep="first")
        .copy()
    )

    return (
        latest_campaigns,
        latest_security,
        campaign_events,
        security_events,
        db_incidents
    )


# =====================================================
# 5. DETECTION AND INCIDENT DATA
# =====================================================

def build_incidents(campaign_data, security_data):
    campaign_alerts = detect_campaign_anomalies(campaign_data)
    cyber_alerts = detect_cyber_threats(security_data)

    all_alerts = campaign_alerts + cyber_alerts
    all_alerts += st.session_state.demo_alerts

    grouped_incidents = correlate_alerts(all_alerts)
    results = []

    for incident in grouped_incidents:
        incident["risk_score"] = calculate_risk(incident)
        incident["risk_level"] = get_risk_level(
            incident["risk_score"]
        )
        incident["recommendations"] = generate_recommendations(
            incident
        )

        incident["status"] = st.session_state.incident_status.get(
            incident["campaign"], "Open"
        )

        results.append(incident)

    results.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    return all_alerts, results


def make_incident_dataframe(incidents):
    rows = []

    for incident in incidents:
        rows.append({
            "Campaign": incident["campaign"],
            "Signals": ", ".join(incident["alerts"]),
            "Severity": incident["severity"],
            "Risk Score": incident["risk_score"],
            "Risk Level": incident["risk_level"],
            "Status": incident["status"],
            "Evidence": " | ".join(incident["evidence"]),
            "Recommendations": " | ".join(
                incident["recommendations"]
            )
        })

    return pd.DataFrame(rows)


def severity_label(severity):
    if severity == "High":
        return "🔴 HIGH"
    if severity == "Medium":
        return "🟠 MEDIUM"
    return "🟢 LOW"


# =====================================================
# 6. SCREEN 1 — LOGIN
# =====================================================

def show_login():
    st.markdown("<br><br>", unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown("""
        <div class="hero" style="min-height:390px;">
            <div class="eyebrow">CAMPAIGN SECURITY PLATFORM</div>
            <br>
            <h1 style="font-size:43px;">
                🛡️ AdPulse<br>Sentinel
            </h1>
            <p style="font-size:18px; color:#c0cce5;">
                Detect the unusual.<br>
                Understand the risk.<br>
                Reduce alert fatigue.
            </p>
            <br>
            <span class="status-pill">● DEMO ENVIRONMENT</span>
            <br><br>
            <p class="muted">
                Cybersecurity-aware campaign monitoring
                with correlated alerts and risk-based
                investigation.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="eyebrow">SECURE ACCESS</div>',
            unsafe_allow_html=True
        )
        st.title("Welcome Back")
        st.write("Sign in to open your monitoring console.")

        st.info(
            "Demo username: admin\n\n"
            "Demo password: sentinel123"
        )

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            submitted = st.form_submit_button(
                "🛡️ Secure Login",
                use_container_width=True
            )

        if submitted:
            if username == "admin" and password == "sentinel123":
                st.session_state.authenticated = True
                st.session_state.current_page = "Home"
                st.session_state.sidebar_page = "Home"
                record_activity("Demo user signed in")
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.caption(
            "Demo authentication only. Not production security."
        )


# =====================================================
# 7. TOP NAVIGATION AND SIDEBAR
# =====================================================

def show_navigation():
    with st.sidebar:
        st.markdown(
            '<div class="eyebrow">ADPULSE</div>',
            unsafe_allow_html=True
        )
        st.markdown("## 🛡️ Sentinel")
        st.caption("CAMPAIGN SECURITY PLATFORM")
        st.divider()

        st.radio(
            "Main navigation",
            options=PAGES,
            key="sidebar_page",
            format_func=lambda page: ICONS[page] + "   " + page,
            label_visibility="collapsed",
            on_change=sidebar_changed
        )

        st.divider()

        st.markdown(
            '<span class="status-pill">● Database mode</span>',
            unsafe_allow_html=True
        )

        st.caption("Prototype v2.0")

        st.button(
            "↪ Logout",
            key="logout_button",
            use_container_width=True,
            on_click=logout
        )

    st.markdown(
        '<div class="eyebrow">'
        'ADPULSE SENTINEL / MONITORING CONSOLE'
        '</div>',
        unsafe_allow_html=True
    )

    columns = st.columns(6)

    for index, page in enumerate(PAGES):
        with columns[index]:
            st.button(
                ICONS[page] + " " + SHORT_NAMES[page],
                key="top_" + page,
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.current_page == page
                    else "secondary"
                ),
                on_click=navigate,
                args=(page,)
            )

    st.divider()


# =====================================================
# 8. SHARED DASHBOARD METRICS
# =====================================================

def show_metrics(
    incidents,
    all_alerts,
    campaign_data,
    all_events,
    db_incidents
):
    open_items = [
        item for item in incidents
        if item["status"] == "Open"
    ]

    high_items = [
        item for item in open_items
        if item["risk_level"] == "High"
    ]

    grouped_signals = sum(
        max(0, len(item["alerts"]) - 1)
        for item in incidents
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Campaigns Monitored",
        campaign_data["campaign"].nunique()
    )
    c2.metric("Saved Events", len(all_events))
    c3.metric("Open Incidents", len(open_items))
    c4.metric("High-Risk Groups", len(high_items))

    st.caption(
        f"Saved database incident records: {len(db_incidents)} "
        "| Refresh interval: 5 seconds"
    )


def page_heading(title, description):
    st.title(title)
    st.markdown(
        f'<p class="muted">{description}</p>',
        unsafe_allow_html=True
    )


# =====================================================
# 9. SCREEN 2 — HOME
# =====================================================

def show_home(
    incidents,
    all_alerts,
    campaign_data,
    all_events,
    db_incidents
):
    st.markdown("""
    <div class="hero">
        <div class="eyebrow">CAMPAIGN SECURITY OVERVIEW</div>
        <h1 style="font-size:36px;">
            Welcome to AdPulse Sentinel
        </h1>
        <p style="color:#c0cce5; font-size:16px;">
            Identify unusual campaign activity, correlate
            cybersecurity signals, and prioritize incidents.
        </p>
        <span class="status-pill">● Automatic refresh enabled</span>
    </div>
    """, unsafe_allow_html=True)

    show_metrics(
        incidents, all_alerts, campaign_data,
        all_events, db_incidents
    )

    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("Latest Campaign Spending")

        spend_df = (
            campaign_data.groupby("campaign", as_index=False)["spend"]
            .sum()
        )

        fig = px.bar(
            spend_df,
            x="campaign",
            y="spend",
            color="campaign",
            labels={"campaign": "Campaign", "spend": "Spend (₹)"},
            template="plotly_dark"
        )
        fig.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("System Status")
        st.markdown(f"""
        <div class="card">
            <span class="status-pill">● SQLITE CONNECTED</span>
            <br><br>
            <b>Campaign event records</b>
            <p class="muted">{len(all_events)} loaded records</p>
            <b>Security event records</b>
            <p class="muted">Live database query enabled</p>
            <b>Detection engine</b>
            <p class="muted">Existing Python detection modules</p>
            <b>Refresh interval</b>
            <p class="muted">5 seconds</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Priority Incidents")

    open_items = [
        item for item in incidents
        if item["status"] == "Open"
    ]

    if not open_items:
        st.success("No open detected incident groups.")
    else:
        for incident in open_items[:3]:
            st.markdown(
                f"""
                <div class="card">
                    <b>{incident['campaign']}</b>
                    &nbsp; {severity_label(incident['severity'])}
                    <br><br>
                    <span class="muted">
                        {", ".join(incident['alerts'])}
                    </span>
                    <br><br>
                    Risk score: <b>{incident['risk_score']}/100</b>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.subheader("Quick Access")
    a, b, c = st.columns(3)

    with a:
        st.button(
            "◈ Campaign Intelligence",
            use_container_width=True,
            on_click=navigate,
            args=("Campaign Intelligence",)
        )
    with b:
        st.button(
            "⚡ Cyber Play Lab",
            use_container_width=True,
            on_click=navigate,
            args=("Cyber Play Lab",)
        )
    with c:
        st.button(
            "🛡 Incident Center",
            use_container_width=True,
            on_click=navigate,
            args=("Incident Center",)
        )


# =====================================================
# 10. SCREEN 3 — CAMPAIGN INTELLIGENCE
# =====================================================

def show_campaign_intelligence(
    incidents, all_alerts, campaign_data,
    all_events, db_incidents
):
    page_heading(
        "Campaign Intelligence",
        "Explore the latest campaign spending, clicks, "
        "conversions, and detected anomalies."
    )

    show_metrics(
        incidents, all_alerts, campaign_data,
        all_events, db_incidents
    )

    st.subheader("Spend vs Spending Limit")

    fig = px.bar(
        campaign_data,
        x="campaign",
        y=["spend", "spend_limit"],
        barmode="group",
        labels={
            "campaign": "Campaign",
            "value": "Amount (₹)",
            "variable": "Metric"
        },
        template="plotly_dark"
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest Campaign Records")
    st.dataframe(
        campaign_data,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Recent Generated Events")
    st.dataframe(
        all_events.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Detected Campaign Anomalies")
    campaign_alerts = detect_campaign_anomalies(campaign_data)

    if campaign_alerts:
        for alert in campaign_alerts:
            st.warning(
                f"**{alert['campaign']} — {alert['type']}**\n\n"
                f"{alert['evidence']}"
            )
    else:
        st.success("No campaign anomalies detected.")


# =====================================================
# 11. SCREEN 4 — CYBER PLAY LAB
# =====================================================

def show_cyber_play_lab(security_data):
    page_heading(
        "Cyber Play Lab",
        "Explore how unusual traffic patterns trigger "
        "cybersecurity-aware campaign alerts."
    )

    st.info(
        "These simulations use synthetic data. They do not "
        "send network traffic or attack real systems."
    )

    left, right = st.columns(2)

    with left:
        st.markdown("""
        <div class="card">
            <h3>⚡ Click-Burst Simulation</h3>
            <p class="muted">
                Simulate a sudden increase in clicks per minute.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "Run Click-Burst Simulation",
            use_container_width=True
        ):
            st.session_state.demo_alerts.append({
                "campaign": "Sandbox Campaign",
                "type": "Suspicious Click Burst",
                "severity": "High",
                "evidence": (
                    "SIMULATED: 250 clicks per minute exceeded "
                    "the demonstration threshold of 100."
                )
            })
            record_activity("Click-burst simulation executed")
            st.rerun()

    with right:
        st.markdown("""
        <div class="card">
            <h3>🔁 Repeated-Request Simulation</h3>
            <p class="muted">
                Simulate repeated requests requiring investigation.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "Run Repeated-Request Simulation",
            use_container_width=True
        ):
            st.session_state.demo_alerts.append({
                "campaign": "Sandbox Campaign",
                "type": "Repeated Request Pattern",
                "severity": "Medium",
                "evidence": (
                    "SIMULATED: 75 repeated requests exceeded "
                    "the demonstration threshold of 50."
                )
            })
            record_activity("Repeated-request simulation executed")
            st.rerun()

    st.subheader("Latest Database Security Events")
    st.dataframe(
        security_data.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Detected Cyber Signals")
    security_alerts = detect_cyber_threats(security_data)

    if security_alerts:
        st.dataframe(
            pd.DataFrame(security_alerts),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No cyber signals detected.")

    st.subheader("Simulation History")
    demo_df = pd.DataFrame(st.session_state.demo_alerts)

    if not demo_df.empty:
        st.dataframe(
            demo_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("No synthetic scenarios have been run yet.")

    if st.button("Clear Simulated Alerts"):
        st.session_state.demo_alerts = []
        record_activity("Simulated alerts cleared")
        st.rerun()


# =====================================================
# 12. SCREEN 5 — INCIDENT CENTER
# =====================================================

def show_incident_center(
    incidents, all_alerts, campaign_data,
    all_events, db_incidents
):
    page_heading(
        "Incident Center",
        "Investigate detected signals and review persisted "
        "incident records from SQLite."
    )

    show_metrics(
        incidents, all_alerts, campaign_data,
        all_events, db_incidents
    )

    st.subheader("Detected Incident Groups")

    if not incidents:
        st.info("No detected incident groups.")
    else:
        selected = st.selectbox(
            "Choose a detected incident group",
            options=[item["campaign"] for item in incidents]
        )

        incident = next(
            item for item in incidents
            if item["campaign"] == selected
        )

        a, b, c = st.columns(3)
        a.metric("Risk Score", f"{incident['risk_score']}/100")
        b.metric("Risk Level", incident["risk_level"])
        c.metric("Severity", incident["severity"])

        st.subheader(incident["campaign"])

        st.write("**Correlated Signals**")
        for signal in incident["alerts"]:
            st.write(f"• {signal}")

        st.write("**Supporting Evidence**")
        for evidence in incident["evidence"]:
            st.info(evidence)

        st.write("**Recommended Investigation Steps**")
        for recommendation in incident["recommendations"]:
            st.write(f"✓ {recommendation}")

        st.write(f"**Group status:** {incident['status']}")

        if incident["status"] == "Open":
            if st.button("✓ Resolve Incident Group"):
                st.session_state.incident_status[
                    incident["campaign"]
                ] = "Resolved"
                record_activity(
                    f"Incident group resolved: {incident['campaign']}"
                )
                st.rerun()
        else:
            if st.button("↺ Reopen Incident Group"):
                st.session_state.incident_status[
                    incident["campaign"]
                ] = "Open"
                record_activity(
                    f"Incident group reopened: {incident['campaign']}"
                )
                st.rerun()

        st.dataframe(
            make_incident_dataframe(incidents),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    st.subheader("Persisted SQLite Incident Records")

    if db_incidents.empty:
        st.info(
            "No persisted incident records yet. "
            "Start auto_detector.py to process new events."
        )
    else:
        st.dataframe(
            db_incidents,
            use_container_width=True,
            hide_index=True
        )

        selected_id = st.selectbox(
            "Select a saved incident ID to update its status",
            options=db_incidents["id"].astype(int).tolist(),
            key="saved_incident_id"
        )

        current_row = db_incidents[
            db_incidents["id"] == selected_id
        ].iloc[0]

        st.write(f"Current status: **{current_row['status']}**")

        left, right = st.columns(2)

        with left:
            if st.button("Mark Saved Incident Resolved"):
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE incidents SET status = 'Resolved' WHERE id = ?",
                        (int(selected_id),)
                    )
                record_activity(
                    f"Saved database incident {selected_id} resolved"
                )
                st.rerun()

        with right:
            if st.button("Reopen Saved Incident"):
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE incidents SET status = 'Open' WHERE id = ?",
                        (int(selected_id),)
                    )
                record_activity(
                    f"Saved database incident {selected_id} reopened"
                )
                st.rerun()


# =====================================================
# 13. SCREEN 6 — ANALYTICS
# =====================================================

def show_analytics(
    incidents, all_alerts, campaign_data,
    all_events, db_incidents
):
    page_heading(
        "Analytics",
        "Understand signal types, incident risk, and event trends."
    )

    show_metrics(
        incidents, all_alerts, campaign_data,
        all_events, db_incidents
    )

    left, right = st.columns(2)

    with left:
        signal_counts = {}

        for alert in all_alerts:
            name = alert["type"]
            signal_counts[name] = signal_counts.get(name, 0) + 1

        if signal_counts:
            signal_df = pd.DataFrame({
                "Signal": list(signal_counts.keys()),
                "Count": list(signal_counts.values())
            })

            fig = px.pie(
                signal_df,
                names="Signal",
                values="Count",
                hole=0.55,
                title="Signal Type Distribution",
                template="plotly_dark"
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        if incidents:
            risk_df = pd.DataFrame(incidents)

            fig = px.bar(
                risk_df,
                x="campaign",
                y="risk_score",
                color="risk_level",
                title="Incident Risk Scores",
                labels={
                    "campaign": "Campaign",
                    "risk_score": "Risk Score",
                    "risk_level": "Risk Level"
                },
                template="plotly_dark"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_range=[0, 100]
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Event Volume by Campaign")

    if not all_events.empty:
        event_counts = (
            all_events.groupby("campaign")
            .size()
            .reset_index(name="Events")
        )
        event_counts.columns = ["Campaign", "Events"]
        st.bar_chart(event_counts, x="Campaign", y="Events")

    st.subheader("Incident Severity in Database")

    if not db_incidents.empty:
        severity_counts = (
            db_incidents.groupby("severity")
            .size()
            .reset_index(name="Count")
        )
        st.bar_chart(
            severity_counts,
            x="severity",
            y="Count"
        )

    st.subheader("Alert Grouping Summary")

    raw_count = len(all_alerts)
    incident_count = len(incidents)
    grouped_count = sum(
        max(0, len(item["alerts"]) - 1)
        for item in incidents
    )

    a, b, c = st.columns(3)
    a.metric("Current Raw Signals", raw_count)
    b.metric("Grouped Incident Groups", incident_count)
    c.metric("Additional Signals in Groups", grouped_count)

    st.caption(
        "These are prototype metrics, not a measured production "
        "reduction in alert fatigue."
    )


# =====================================================
# 14. SCREEN 7 — ACTIVITY & REPORTS
# =====================================================

def show_activity_reports(
    incidents, campaign_data, security_data,
    all_events, db_incidents
):
    page_heading(
        "Activity & Reports",
        "Review saved incidents and export campaign and "
        "security reports."
    )

    report_df = make_incident_dataframe(incidents)

    st.subheader("Detected Incident Group Report")

    if report_df.empty:
        st.info("No detected incident groups available.")
    else:
        st.dataframe(
            report_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇ Download Incident Group Report",
            data=report_df.to_csv(index=False).encode("utf-8"),
            file_name="adpulse_incident_groups.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.subheader("Saved Database Incident Report")

    st.dataframe(
        db_incidents,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇ Download Saved Incidents",
        data=db_incidents.to_csv(index=False).encode("utf-8"),
        file_name="adpulse_saved_incidents.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.subheader("Campaign Event Export")

    st.download_button(
        "⬇ Download All Campaign Events",
        data=all_events.to_csv(index=False).encode("utf-8"),
        file_name="adpulse_campaign_events.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.subheader("Security Event Export")

    st.download_button(
        "⬇ Download Security Events",
        data=security_data.to_csv(index=False).encode("utf-8"),
        file_name="adpulse_security_events.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.subheader("Session Activity History")

    if st.session_state.activity_log:
        activity_df = pd.DataFrame(
            st.session_state.activity_log
        )
        st.dataframe(
            activity_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇ Download Activity History",
            data=activity_df.to_csv(index=False).encode("utf-8"),
            file_name="adpulse_activity_history.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No session activity recorded yet.")

    st.caption(
        "Session activity is temporary. Saved campaign events "
        "and database incidents persist in SQLite."
    )


# =====================================================
# 15. MAIN APPLICATION ROUTER
# =====================================================

try:
    (
        campaign_data,
        security_data,
        all_events,
        all_security_events,
        db_incidents
    ) = load_data()

except Exception as error:
    st.error("Could not load AdPulse Sentinel database data.")
    st.code(str(error))
    st.stop()


if not st.session_state.authenticated:
    show_login()

else:
    all_alerts, incidents = build_incidents(
        campaign_data,
        security_data
    )

    show_navigation()

    current_page = st.session_state.current_page

    if current_page == "Home":
        show_home(
            incidents, all_alerts, campaign_data,
            all_events, db_incidents
        )

    elif current_page == "Campaign Intelligence":
        show_campaign_intelligence(
            incidents, all_alerts, campaign_data,
            all_events, db_incidents
        )

    elif current_page == "Cyber Play Lab":
        show_cyber_play_lab(security_data)

    elif current_page == "Incident Center":
        show_incident_center(
            incidents, all_alerts, campaign_data,
            all_events, db_incidents
        )

    elif current_page == "Analytics":
        show_analytics(
            incidents, all_alerts, campaign_data,
            all_events, db_incidents
        )

    elif current_page == "Activity & Reports":
        show_activity_reports(
            incidents, campaign_data, security_data,
            all_events, db_incidents
        )

    st.divider()

    st.caption(
        "AdPulse Sentinel | Campaign Anomaly Alerting Without Alert Fatigue "
        "| SQLite-backed prototype | Simulated campaign events"
    )
