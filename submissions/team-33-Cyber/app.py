import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import io
import time

from csv_processor import CSVProcessor
from decision_engine import DecisionEngine
from data_generator import generate_synthetic_dataset

# ----------------------------------------------------
# 1. PAGE & THEME CONFIGURATION
# ----------------------------------------------------
st.set_page_config(
    page_title="SearchSense AI — Search Term Triage Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Cybersecurity / Modern Analytics Design System CSS
CUSTOM_CSS = """
<style>
    /* Global Deep Midnight Navy Background */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }

    /* Cards & Containers */
    div.css-1r6slb0, div.stCard, div[data-testid="stMetricValue"] {
        background-color: #1e293b;
        border-radius: 10px;
        border: 1px solid #334155;
    }

    .stat-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .stat-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stat-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .stat-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .badge-promote { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; }
    .badge-block { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; }
    .badge-ignore { background-color: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid #94a3b8; }
    .badge-review { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b; }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #06b6d4;
        background: linear-gradient(135deg, #0891b2 0%, #0284c7 100%);
        color: #ffffff;
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.5);
        border-color: #38bdf8;
    }

    /* Workflow Banner */
    .workflow-bar {
        display: flex;
        justify-content: space-between;
        background-color: #0f172a;
        padding: 12px 20px;
        border-radius: 10px;
        border: 1px solid #1e293b;
        margin-bottom: 25px;
    }
    .wf-step {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
    }
    .wf-step.active {
        color: #38bdf8;
        font-weight: 700;
        border-bottom: 2px solid #38bdf8;
    }
    .wf-step.completed {
        color: #10b981;
    }

    /* Synthetic Data Alert Banner */
    .synthetic-banner {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid #f59e0b;
        color: #fbbf24;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 15px;
    }

    .official-banner {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        color: #34d399;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 15px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------
# 2. SESSION STATE INITIALIZATION
# ----------------------------------------------------
if "df_raw" not in st.session_state:
    st.session_state.df_raw = None
if "df_processed" not in st.session_state:
    st.session_state.df_processed = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = "None"
if "is_synthetic" not in st.session_state:
    st.session_state.is_synthetic = False
if "csv_summary" not in st.session_state:
    st.session_state.csv_summary = None
if "human_reviews" not in st.session_state:
    st.session_state.human_reviews = {}
if "context_config" not in st.session_state:
    st.session_state.context_config = {
        "business_name": "Ecommerce Laptop & Tech Store",
        "product_description": "Direct sales of high-performance laptops and accessories",
        "relevant_intents": ["buy laptop", "laptop deals", "price", "store near me", "order online"],
        "irrelevant_intents": ["free wallpaper", "teardown", "repair manual", "salary", "jobs"],
        "negative_keywords": ["free", "torrent", "crack", "hack", "teardown", "repair manual", "salary", "jobs", "wikipedia", "cardboard", "diy", "schematic"],
        "min_clicks_threshold": 10,
        "min_cost_threshold": 15.0,
        "target_cpa_threshold": 50.0,
        "roas_threshold": 1.0
    }

# ----------------------------------------------------
# 3. SIDEBAR NAVIGATION
# ----------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8; margin-bottom: 0;'>🔍 SearchSense AI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem;'>Search Term Intelligence & Triage Engine</p>", unsafe_allow_html=True)
    st.divider()

    nav_page = st.radio(
        "Navigation",
        [
            "1. Overview",
            "2. Data Studio",
            "3. Triage Analysis",
            "4. Human Review Queue",
            "5. Insights & Evaluation",
            "6. Export Centre",
            "7. About & Methodology"
        ],
        index=0
    )

    st.divider()
    st.markdown("### 📊 Active Session Status")
    st.markdown(f"**Dataset:** `{st.session_state.dataset_name}`")
    records_cnt = len(st.session_state.df_raw) if st.session_state.df_raw is not None else 0
    st.markdown(f"**Loaded Records:** `{records_cnt:,}`")
    
    if st.session_state.df_processed is not None:
        st.markdown("**Analysis:** <span style='color: #10b981;'>Completed</span>", unsafe_allow_html=True)
    else:
        st.markdown("**Analysis:** <span style='color: #f59e0b;'>Pending</span>", unsafe_allow_html=True)

    if st.session_state.is_synthetic:
        st.markdown("<div class='synthetic-banner'>DEMO SYNTHETIC DATA ACTIVE</div>", unsafe_allow_html=True)

    st.markdown("<br><p style='font-size: 0.75rem; color: #64748b;'>Antigravity Hackathon Submission — PS-01</p>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. WORKFLOW STEP INDICATOR
# ----------------------------------------------------
def render_workflow_bar():
    step1 = "completed" if st.session_state.df_raw is not None else "active"
    step2 = "completed" if st.session_state.df_raw is not None else ""
    step3 = "completed" if st.session_state.df_raw is not None else ""
    step4 = "completed" if st.session_state.df_processed is not None else ("active" if st.session_state.df_raw is not None else "")
    step5 = "completed" if st.session_state.df_processed is not None else ""
    step6 = "completed" if st.session_state.df_processed is not None else ""

    st.markdown(f"""
    <div class='workflow-bar'>
        <span class='wf-step {step1}'>STEP 1 — CHOOSE DATA</span>
        <span class='wf-step {step2}'>STEP 2 — CONFIGURE CONTEXT</span>
        <span class='wf-step {step3}'>STEP 3 — VALIDATE</span>
        <span class='wf-step {step4}'>STEP 4 — ANALYSE</span>
        <span class='wf-step {step5}'>STEP 5 — REVIEW</span>
        <span class='wf-step {step6}'>STEP 6 — EXPORT</span>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 1: OVERVIEW DASHBOARD
# ----------------------------------------------------
if nav_page == "1. Overview":
    render_workflow_bar()
    
    st.markdown("<h1 style='color: #f8fafc;'>Search Intelligence, Made Explainable</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #94a3b8;'>Turn raw Google Ads search-term data into evidence-backed, explainable triage decisions.</p>", unsafe_allow_html=True)
    
    st.write("")

    # Primary Action Cards
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
        st.markdown("### ⚡ Quick Demo")
        st.write("Generate reproducible 25,000 synthetic rows instantly to test the full pipeline.")
        if st.button("Generate Demo Dataset (25k)", use_container_width=True):
            with st.spinner("Generating 25,000 synthetic records..."):
                sample_file = generate_synthetic_dataset()
                df_std, summary = CSVProcessor.load_and_standardize_csv(sample_file)
                st.session_state.df_raw = df_std
                st.session_state.dataset_name = "sample_search_terms_25000.csv"
                st.session_state.is_synthetic = True
                st.session_state.csv_summary = summary
                st.session_state.df_processed = None
                st.success("Successfully loaded 25,000 synthetic search terms!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
        st.markdown("### 📂 Custom / Hackathon CSV")
        st.write("Upload official hackathon CSV or any Google Ads Search Term report.")
        if st.button("Go to Data Studio Upload", use_container_width=True):
            st.info("Please navigate to '2. Data Studio' using the sidebar to upload your file.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c:
        st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
        st.markdown("### 🚀 Run Triage Analysis")
        st.write("Execute decision engine on loaded dataset using configurable rules.")
        if st.session_state.df_raw is not None:
            if st.button("Launch Analysis Engine", use_container_width=True):
                st.info("Navigate to '3. Triage Analysis' to start evaluation.")
        else:
            st.button("Launch Analysis Engine (Load Data First)", disabled=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.divider()

    # Summary Metrics Section
    st.markdown("### 📊 Dataset Overview & Triage Summary")
    
    if st.session_state.df_processed is not None:
        df_p = st.session_state.df_processed
        m1, m2, m3, m4, m5 = st.columns(5)
        
        with m1:
            st.markdown(f"<div class='stat-card'><div class='stat-title'>Total Records</div><div class='stat-value'>{len(df_p):,}</div></div>", unsafe_allow_html=True)
        with m2:
            cnt = (df_p['decision'] == 'PROMOTE').sum()
            st.markdown(f"<div class='stat-card'><div class='stat-title'>Promote</div><div class='stat-value' style='color:#10b981;'>{cnt:,}</div><span class='stat-badge badge-promote'>TARGET KEYWORDS</span></div>", unsafe_allow_html=True)
        with m3:
            cnt = (df_p['decision'] == 'BLOCK').sum()
            st.markdown(f"<div class='stat-card'><div class='stat-title'>Block</div><div class='stat-value' style='color:#ef4444;'>{cnt:,}</div><span class='stat-badge badge-block'>NEGATIVE KEYWORDS</span></div>", unsafe_allow_html=True)
        with m4:
            cnt = (df_p['decision'] == 'IGNORE').sum()
            st.markdown(f"<div class='stat-card'><div class='stat-title'>Ignore</div><div class='stat-value' style='color:#94a3b8;'>{cnt:,}</div><span class='stat-badge badge-ignore'>LOW TRAFFIC</span></div>", unsafe_allow_html=True)
        with m5:
            cnt = (df_p['decision'] == 'HUMAN REVIEW').sum()
            st.markdown(f"<div class='stat-card'><div class='stat-title'>Human Review</div><div class='stat-value' style='color:#f59e0b;'>{cnt:,}</div><span class='stat-badge badge-review'>UNCERTAIN</span></div>", unsafe_allow_html=True)

    elif st.session_state.df_raw is not None:
        st.info(f"Dataset `{st.session_state.dataset_name}` ({len(st.session_state.df_raw):,} records) is loaded. Run analysis in Step 4 to see metrics.")
    else:
        st.warning("No dataset loaded yet. Generate the 25,000-row demo dataset above or upload a CSV in Data Studio.")

# ----------------------------------------------------
# PAGE 2: DATA STUDIO & COLUMN MAPPING
# ----------------------------------------------------
elif nav_page == "2. Data Studio":
    render_workflow_bar()
    st.markdown("<h2>📂 Data Studio — Flexible CSV Upload & Inspection</h2>", unsafe_allow_html=True)
    st.write("Upload official hackathon CSVs or custom Google Ads search term reports.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Upload Search Term CSV")
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is not None:
            try:
                df_std, summary = CSVProcessor.load_and_standardize_csv(uploaded_file)
                st.session_state.df_raw = df_std
                st.session_state.dataset_name = uploaded_file.name
                st.session_state.is_synthetic = False
                st.session_state.csv_summary = summary
                st.session_state.df_processed = None
                st.success(f"Successfully processed CSV '{uploaded_file.name}' with {len(df_std):,} records.")
            except Exception as e:
                st.error(f"Error loading CSV file: {str(e)}")

    with col2:
        st.markdown("### Quick Demo Generator")
        st.write("Need sample data to test high-volume performance?")
        if st.button("Generate & Load 25,000 Row Demo Dataset", use_container_width=True):
            with st.spinner("Generating 25,000 synthetic records..."):
                sample_file = generate_synthetic_dataset()
                df_std, summary = CSVProcessor.load_and_standardize_csv(sample_file)
                st.session_state.df_raw = df_std
                st.session_state.dataset_name = "sample_search_terms_25000.csv"
                st.session_state.is_synthetic = True
                st.session_state.csv_summary = summary
                st.session_state.df_processed = None
                st.success("Loaded 25,000 synthetic records into workspace.")
                st.rerun()

    st.divider()

    if st.session_state.df_raw is not None:
        if st.session_state.is_synthetic:
            st.markdown("<div class='synthetic-banner'>SYNTHETIC DEMONSTRATION DATA — NOT OFFICIAL HACKATHON DATA</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='official-banner'>OFFICIAL / USER SUPPLIED DATASET LOADED</div>", unsafe_allow_html=True)

        st.markdown("### 📋 Dataset Inspection & Schema Mapping")
        
        summary = st.session_state.csv_summary
        if summary:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Rows", f"{summary['total_rows']:,}")
            c2.metric("Valid Search Queries", f"{summary['valid_rows']:,}")
            c3.metric("Available Optional Metrics", len(summary['available_optional']))
            c4.metric("Missing Optional Metrics", len(summary['missing_optional']))

            with st.expander("🔍 View Auto-Detected Column Mapping", expanded=False):
                st.json(summary['mapped_columns'])

        st.markdown("#### Preview Data Records (First 50 Rows)")
        st.dataframe(pd.DataFrame(st.session_state.df_raw[:50]), use_container_width=True)


# ----------------------------------------------------
# PAGE 3: TRIAGE ANALYSIS & CONFIGURATION
# ----------------------------------------------------
elif nav_page == "3. Triage Analysis":
    render_workflow_bar()
    st.markdown("<h2>⚙️ Triage Analysis & Decision Engine</h2>", unsafe_allow_html=True)

    if st.session_state.df_raw is None:
        st.warning("Please load a dataset in Data Studio before running triage analysis.")
    else:
        st.markdown("### 1. Configure Business Context & Rules")
        with st.form("context_form"):
            c1, c2 = st.columns(2)
            with c1:
                b_name = st.text_input("Business / Product Name", value=st.session_state.context_config["business_name"])
                b_desc = st.text_area("Product / Service Description", value=st.session_state.context_config["product_description"])
                rel_intents = st.text_input("Relevant Target Intents (comma separated)", value=", ".join(st.session_state.context_config["relevant_intents"]))
                irr_intents = st.text_input("Irrelevant Intent Phrases (comma separated)", value=", ".join(st.session_state.context_config["irrelevant_intents"]))
            
            with c2:
                neg_kws = st.text_area("Negative Keyword List (comma separated)", value=", ".join(st.session_state.context_config["negative_keywords"]))
                min_clicks = st.number_input("Minimum Clicks Threshold for High-Volume", value=st.session_state.context_config["min_clicks_threshold"], min_value=1)
                min_cost = st.number_input("Minimum Cost Threshold ($)", value=float(st.session_state.context_config["min_cost_threshold"]), min_value=0.0)
            
            submitted = st.form_submit_button("Save Configuration")
            if submitted:
                st.session_state.context_config = {
                    "business_name": b_name,
                    "product_description": b_desc,
                    "relevant_intents": [x.strip() for x in rel_intents.split(",") if x.strip()],
                    "irrelevant_intents": [x.strip() for x in irr_intents.split(",") if x.strip()],
                    "negative_keywords": [x.strip() for x in neg_kws.split(",") if x.strip()],
                    "min_clicks_threshold": min_clicks,
                    "min_cost_threshold": min_cost
                }
                st.success("Business context updated!")

        st.divider()

        st.markdown("### 2. Run Decision Engine")
        st.write(f"Ready to triage **{len(st.session_state.df_raw):,}** search terms for `{st.session_state.context_config['business_name']}`.")
        
        if st.button("🚀 ANALYSE SEARCH TERMS NOW", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("Initializing explainable decision engine rules...")
            progress_bar.progress(20)

            engine = DecisionEngine(st.session_state.context_config)
            
            status_text.text("Processing queries, evaluating relevance & performance evidence...")
            progress_bar.progress(60)

            start_t = time.time()
            records_out = engine.process_records(st.session_state.df_raw)
            duration = time.time() - start_t

            progress_bar.progress(100)
            status_text.text(f"Analysis completed in {duration:.2f} seconds!")
            
            st.session_state.df_processed = pd.DataFrame(records_out)
            st.success(f"Successfully evaluated {len(records_out):,} rows in {duration:.2f} seconds!")


        if st.session_state.df_processed is not None:
            st.divider()
            st.markdown("### 📊 Analysis Results Explorer")
            df_p = st.session_state.df_processed

            # Interactive Filters
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                search_q = st.text_input("Search Query Text", "")
            with f_col2:
                sel_decision = st.multiselect("Filter Decision", ["PROMOTE", "BLOCK", "IGNORE", "HUMAN REVIEW"], default=["PROMOTE", "BLOCK", "IGNORE", "HUMAN REVIEW"])
            with f_col3:
                sel_campaign = st.multiselect("Filter Campaign", options=list(df_p["campaign"].unique()), default=list(df_p["campaign"].unique()))
            with f_col4:
                sel_confidence = st.multiselect("Filter Confidence", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"])

            # Filter data
            filtered_df = df_p[
                (df_p["decision"].isin(sel_decision)) &
                (df_p["campaign"].isin(sel_campaign)) &
                (df_p["confidence"].isin(sel_confidence))
            ]

            if search_q:
                filtered_df = filtered_df[filtered_df["query_text"].str.contains(search_q, case=False, na=False)]

            st.write(f"Displaying **{len(filtered_df):,}** of **{len(df_p):,}** records")

            display_cols = ["source_row_id", "query_text", "campaign", "ad_group", "clicks", "cost", "conversions", "decision", "confidence", "explanation"]
            st.dataframe(filtered_df[display_cols].head(100), use_container_width=True)

            # Detailed Record Inspector
            st.markdown("#### 🔬 Detailed Record Inspector")
            if not filtered_df.empty:
                selected_row_id = st.selectbox("Select Row ID to inspect", options=filtered_df["source_row_id"].head(50))
                rec = filtered_df[filtered_df["source_row_id"] == selected_row_id].iloc[0]

                st.json({
                    "Source Row ID": rec["source_row_id"],
                    "Query Text": rec["query_text"],
                    "Campaign": rec["campaign"],
                    "Decision": rec["decision"],
                    "Confidence": rec["confidence"],
                    "Explanation": rec["explanation"],
                    "Recommended Action": rec["recommended_action"],
                    "Review Required": bool(rec["review_required"]),
                    "Performance": {
                        "Clicks": rec.get("clicks"),
                        "Cost ($)": rec.get("cost"),
                        "Conversions": rec.get("conversions"),
                        "Conversion Value ($)": rec.get("conversion_value")
                    }
                })

# ----------------------------------------------------
# PAGE 4: HUMAN REVIEW WORKSPACE
# ----------------------------------------------------
elif nav_page == "4. Human Review Queue":
    render_workflow_bar()
    st.markdown("<h2>🙋 Human Review Workspace</h2>", unsafe_allow_html=True)
    st.write("Inspect ambiguous, conflicting, or low-confidence search terms that require human verification.")

    if st.session_state.df_processed is None:
        st.warning("Please execute Triage Analysis first.")
    else:
        df_p = st.session_state.df_processed
        review_df = df_p[df_p["decision"] == "HUMAN REVIEW"].copy()

        st.markdown(f"### 📋 Review Queue ({len(review_df):,} items needing review)")

        if review_df.empty:
            st.success("No records currently flagged for Human Review!")
        else:
            sel_row_id = st.selectbox("Select Record from Queue", options=review_df["source_row_id"])
            row_data = review_df[review_df["source_row_id"] == sel_row_id].iloc[0]

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
                st.markdown(f"### Query: `{row_data['query_text']}`")
                st.markdown(f"**Campaign:** {row_data['campaign']} | **Ad Group:** {row_data['ad_group']}")
                st.markdown(f"**System Decision:** `<span class='stat-badge badge-review'>{row_data['decision']}</span>`", unsafe_allow_html=True)
                st.markdown(f"**Confidence:** `{row_data['confidence']}`")
                st.markdown(f"**System Explanation:** {row_data['explanation']}")
                st.markdown(f"**Recommended Action:** {row_data['recommended_action']}")
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
                st.markdown("### ✍️ Human Decision Override")
                
                existing_rev = st.session_state.human_reviews.get(sel_row_id, {})
                default_choice = existing_rev.get("reviewer_decision", "HUMAN REVIEW")
                default_note = existing_rev.get("reviewer_note", "")

                reviewer_dec = st.selectbox(
                    "Reviewer Action",
                    ["HUMAN REVIEW", "PROMOTE (Override)", "BLOCK (Override)", "IGNORE (Override)"],
                    index=["HUMAN REVIEW", "PROMOTE (Override)", "BLOCK (Override)", "IGNORE (Override)"].index(default_choice)
                )
                
                reviewer_note = st.text_area("Reviewer Rationale & Notes", value=default_note)

                if st.button("Save Human Review Decision"):
                    st.session_state.human_reviews[sel_row_id] = {
                        "reviewer_decision": reviewer_dec,
                        "reviewer_note": reviewer_note,
                        "reviewed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.success(f"Review saved for {sel_row_id}!")
                st.markdown("</div>", unsafe_allow_html=True)

            st.divider()
            st.markdown("### Current Human Review Log")
            if st.session_state.human_reviews:
                st.json(st.session_state.human_reviews)
            else:
                st.info("No human override notes logged yet in this session.")

# ----------------------------------------------------
# PAGE 5: INSIGHTS & EVALUATION
# ----------------------------------------------------
elif nav_page == "5. Insights & Evaluation":
    render_workflow_bar()
    st.markdown("<h2>📈 Insights & Ground-Truth Evaluation</h2>", unsafe_allow_html=True)

    if st.session_state.df_processed is None:
        st.warning("Run Triage Analysis to view insights.")
    else:
        df_p = st.session_state.df_processed

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Triage Decisions Distribution")
            fig_pie = px.pie(
                df_p, names="decision", 
                color="decision",
                color_discrete_map={
                    "PROMOTE": "#10b981",
                    "BLOCK": "#ef4444",
                    "IGNORE": "#94a3b8",
                    "HUMAN REVIEW": "#f59e0b"
                },
                hole=0.4
            )
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("### Decisions by Campaign")
            fig_bar = px.histogram(
                df_p, x="campaign", color="decision",
                barmode="group",
                color_discrete_map={
                    "PROMOTE": "#10b981",
                    "BLOCK": "#ef4444",
                    "IGNORE": "#94a3b8",
                    "HUMAN REVIEW": "#f59e0b"
                }
            )
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # Benchmark Ground Truth Evaluation
        st.markdown("### 🎯 Benchmark Evaluation (Synthetic Ground Truth)")
        if "_synthetic_ground_truth" in df_p.columns:
            st.markdown("<div class='synthetic-banner'>EVALUATING AGAINST SYNTHETIC GROUND TRUTH — NOT ACCESSED BY DECISION ENGINE</div>", unsafe_allow_html=True)
            
            # Compute classification match
            eval_df = df_p[df_p["_synthetic_ground_truth"].notna()].copy()
            match_cnt = (eval_df["decision"] == eval_df["_synthetic_ground_truth"]).sum()
            acc = (match_cnt / len(eval_df)) * 100

            e1, e2, e3 = st.columns(3)
            e1.metric("Evaluated Benchmark Records", f"{len(eval_df):,}")
            e2.metric("Exact Rule Match Count", f"{match_cnt:,}")
            e3.metric("Rule Benchmark Accuracy", f"{acc:.2f}%")

            with st.expander("View Confusion Matrix Breakdown", expanded=True):
                ctable = pd.crosstab(eval_df["_synthetic_ground_truth"], eval_df["decision"], rownames=["Synthetic Ground Truth"], colnames=["Engine Decision"])
                st.dataframe(ctable, use_container_width=True)
        else:
            st.info("User-supplied dataset does not contain synthetic ground truth labels. Real accuracy cannot be measured without verified historical ground truth.")

# ----------------------------------------------------
# PAGE 6: EXPORT CENTRE
# ----------------------------------------------------
elif nav_page == "6. Export Centre":
    render_workflow_bar()
    st.markdown("<h2>📥 Export Centre</h2>", unsafe_allow_html=True)
    st.write("Download full triage analysis, negative keyword blocks, promotion targets, or human review queues.")

    if st.session_state.df_processed is None:
        st.warning("Run Triage Analysis first to export results.")
    else:
        df_p = st.session_state.df_processed.copy()

        # Merge human review overrides if present
        if st.session_state.human_reviews:
            df_p["reviewer_decision"] = df_p["source_row_id"].map(lambda x: st.session_state.human_reviews.get(x, {}).get("reviewer_decision", ""))
            df_p["reviewer_note"] = df_p["source_row_id"].map(lambda x: st.session_state.human_reviews.get(x, {}).get("reviewer_note", ""))

        st.markdown("### Available CSV Downloads")
        
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 1. Complete Triage Analysis CSV")
            st.write("Includes all original columns, decision labels, explanations, and row IDs.")
            csv_full = df_p.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Complete Triage CSV",
                data=csv_full,
                file_name=f"searchsense_triage_full_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.write("")
            st.markdown("#### 2. Negative Keyword Blocklist (BLOCK)")
            st.write("Ready to import directly into Google Ads as negative keywords.")
            df_block = df_p[df_p["decision"] == "BLOCK"]
            csv_block = df_block.to_csv(index=False).encode('utf-8')
            st.download_button(
                f"Download Blocklist ({len(df_block):,} rows)",
                data=csv_block,
                file_name="searchsense_blocklist.csv",
                mime="text/csv",
                use_container_width=True
            )

        with c2:
            st.markdown("#### 3. High Potential Promotion Targets (PROMOTE)")
            st.write("Target terms with positive ROI or strong buying intent.")
            df_promote = df_p[df_p["decision"] == "PROMOTE"]
            csv_promote = df_promote.to_csv(index=False).encode('utf-8')
            st.download_button(
                f"Download Target Keywords ({len(df_promote):,} rows)",
                data=csv_promote,
                file_name="searchsense_promote_list.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.write("")
            st.markdown("#### 4. Human Review Queue CSV")
            st.write("Queue of uncertain queries for manual specialist audit.")
            df_review = df_p[df_p["decision"] == "HUMAN REVIEW"]
            csv_review = df_review.to_csv(index=False).encode('utf-8')
            st.download_button(
                f"Download Review Queue ({len(df_review):,} rows)",
                data=csv_review,
                file_name="searchsense_human_review_queue.csv",
                mime="text/csv",
                use_container_width=True
            )

# ----------------------------------------------------
# PAGE 7: ABOUT & METHODOLOGY
# ----------------------------------------------------
elif nav_page == "7. About & Methodology":
    render_workflow_bar()
    st.markdown("<h2>📖 About SearchSense AI & Methodology</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    ### Problem Statement — PS-01: Search Term Triage Engine

    Google Ads accounts generate large volumes of search-term queries. Marketers struggle to manually triage thousands of terms into actionable targets, waste blocks, or uncertain queries.

    ### Architectural Principles
    1. **Transparent & Cautious:** Every decision is backed by explicit text relevance and empirical metric evidence.
    2. **Zero Black-Box Guessing:** We do not claim trained AI when using explainable rule-based decision trees.
    3. **Human-in-the-Loop:** Uncertain, low-volume, or conflicting records are safely routed to **HUMAN REVIEW**.
    4. **Privacy & Local Execution:** 100% offline local processing without requiring external API keys.

    ### Decision Rules Rationale
    - **PROMOTE:** Requires commercial search intent AND positive conversion/ROAS metric evidence.
    - **BLOCK:** Requires explicit non-commercial / negative keywords OR proven wasteful ad spend ($15+ spend with 0 conversions on non-brand queries).
    - **IGNORE:** Applied to low-volume searches (<10 clicks) where statistical evidence is premature.
    - **HUMAN REVIEW:** Applied when text intent is ambiguous, performance metrics conflict, or required columns are missing.
    """)
