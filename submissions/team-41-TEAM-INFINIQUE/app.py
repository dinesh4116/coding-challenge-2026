"""Streamlit UI for QueryPilot: Deterministic Search Term Triage Engine.

DevSprint PS-01 Full-Stack MVP.
Launch locally with:
    streamlit run app.py
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from triage.config import ColumnMapping, TriageConfig
from triage.engine import run_triage_engine
from triage.export import EXPORT_COLUMNS, filter_and_sort_results, results_to_csv_string
from triage.loader import load_csv_flexible, suggest_column_mapping

SYNTHETIC_CSV_PATH = Path(__file__).resolve().parent / "data" / "sample_synthetic.csv"


def inject_custom_css() -> None:
    """Inject clean, professional enterprise styling into Streamlit."""
    st.markdown(
        """
        <style>
        /* Base typography and clean white canvas */
        .stApp {
            background-color: #f8fafc;
            color: #0f172a;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        }
        /* Top Navigation Header */
        .querypilot-header-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0 18px 0;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 20px;
        }
        .querypilot-title {
            font-size: 1.85rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
            line-height: 1.2;
            letter-spacing: -0.02em;
        }
        .querypilot-subtitle {
            font-size: 0.9rem;
            color: #64748b;
            margin-top: 3px;
            font-weight: 500;
        }
        .querypilot-badge-prod {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background-color: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
        }
        /* Metric cards */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 16px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.8rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
            font-weight: 700;
            color: #0f172a;
        }
        /* Primary button styling */
        div.stButton > button:first-child, div.stDownloadButton > button:first-child {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            padding: 6px 14px;
            transition: all 0.15s ease-in-out;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            background-color: #1d4ed8 !important;
            box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }
        /* Secondary action buttons */
        button[kind="secondary"] {
            background-color: #ffffff !important;
            color: #334155 !important;
            border: 1px solid #cbd5e1 !important;
        }
        /* Evidence Inspector Card */
        .inspector-panel {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 18px;
            margin-top: 14px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }
        .inspector-panel h4 {
            margin-top: 0;
            margin-bottom: 12px;
            color: #0f172a;
            font-size: 1.1rem;
            font-weight: 700;
        }
        /* Decision Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 0.02em;
        }
        .badge-PROMOTE {
            background-color: #ecfdf5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        .badge-BLOCK {
            background-color: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        .badge-IGNORE {
            background-color: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
        }
        .badge-REVIEW {
            background-color: #fffbeb;
            color: #92400e;
            border: 1px solid #fde68a;
        }
        /* Callout banners */
        .synthetic-banner {
            background-color: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 6px;
            padding: 10px 14px;
            color: #1e40af;
            font-size: 0.85rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    """Ensure all required session state variables exist."""
    if "dataset_source" not in st.session_state:
        st.session_state["dataset_source"] = "synthetic"
    if "uploaded_filename" not in st.session_state:
        st.session_state["uploaded_filename"] = ""
    if "raw_df" not in st.session_state:
        st.session_state["raw_df"] = None
    if "upload_error" not in st.session_state:
        st.session_state["upload_error"] = None
    if "selected_term_override" not in st.session_state:
        st.session_state["selected_term_override"] = None


def load_dataset() -> Optional[pd.DataFrame]:
    """Load dataset based on active source with error handling."""
    source = st.session_state["dataset_source"]

    if source == "synthetic":
        if not SYNTHETIC_CSV_PATH.exists():
            st.error(f"Synthetic demo file missing at: {SYNTHETIC_CSV_PATH}")
            return None
        try:
            df = load_csv_flexible(SYNTHETIC_CSV_PATH)
            st.session_state["raw_df"] = df
            st.session_state["uploaded_filename"] = "sample_synthetic.csv"
            st.session_state["upload_error"] = None
            return df
        except Exception as e:
            st.error(f"Failed to load synthetic dataset: {e}")
            return None

    elif source == "uploaded":
        return st.session_state.get("raw_df")

    return None


def main() -> None:
    st.set_page_config(
        page_title="QueryPilot | Search Term Triage Engine",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()
    initialize_session_state()

    # =========================================================================
    # SIDEBAR: Dataset Source & Upload
    # =========================================================================
    st.sidebar.markdown("### 📁 Dataset Source")

    source_choice = st.sidebar.radio(
        "Choose Data Source:",
        options=["SYNTHETIC Demo Dataset (24 rows)", "Upload Custom / Official CSV"],
        index=0 if st.session_state["dataset_source"] == "synthetic" else 1,
        help="Select synthetic benchmark or upload any Google Ads / Bing search term CSV report.",
    )

    if source_choice == "SYNTHETIC Demo Dataset (24 rows)":
        if st.session_state["dataset_source"] != "synthetic":
            st.session_state["dataset_source"] = "synthetic"
            st.session_state["selected_term_override"] = None
            st.rerun()
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Search Term Report (.csv)",
            type=["csv"],
            help="Upload a standard search term report with Search term, Clicks, Cost, and Conversions.",
        )
        if uploaded_file is not None:
            # Check if this is a newly uploaded file
            if (
                st.session_state["dataset_source"] != "uploaded"
                or st.session_state.get("uploaded_filename") != uploaded_file.name
            ):
                try:
                    df = load_csv_flexible(uploaded_file)
                    if df.empty:
                        st.session_state["upload_error"] = "Uploaded CSV file is completely empty."
                        st.session_state["raw_df"] = None
                    else:
                        st.session_state["dataset_source"] = "uploaded"
                        st.session_state["uploaded_filename"] = uploaded_file.name
                        st.session_state["raw_df"] = df
                        st.session_state["upload_error"] = None
                        st.session_state["selected_term_override"] = None
                        st.rerun()
                except pd.errors.EmptyDataError:
                    st.session_state["upload_error"] = "Uploaded file contains no data (empty file)."
                    st.session_state["raw_df"] = None
                except Exception as exc:
                    st.session_state["upload_error"] = f"Failed to parse CSV file: {exc}"
                    st.session_state["raw_df"] = None
        else:
            if st.session_state["dataset_source"] == "uploaded" and st.session_state["raw_df"] is None:
                st.sidebar.info("Please select a `.csv` file above to begin analysis.")

    # =========================================================================
    # SIDEBAR: Analysis Configuration & Thresholds
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Analysis Settings")

    with st.sidebar.expander("Statistical Parameters", expanded=True):
        alpha = st.number_input(
            "Significance Level (alpha)",
            min_value=0.001,
            max_value=0.200,
            value=0.050,
            step=0.005,
            format="%.3f",
            help="Type-I error rate for binomial hypothesis tests (default: 0.05).",
        )
        shrinkage_k = st.number_input(
            "Empirical Bayes Shrinkage (k clicks)",
            min_value=0.0,
            max_value=1000.0,
            value=100.0,
            step=10.0,
            help="Credibility weight for shrinking campaign baseline to account baseline.",
        )
        min_test_clicks = st.number_input(
            "Minimum Test Clicks",
            min_value=1,
            max_value=200,
            value=10,
            step=1,
            help="Minimum observed traffic required before statistical significance is tested.",
        )
        min_promote_conversions = st.number_input(
            "Min. Promote Conversions",
            min_value=2.0,
            max_value=20.0,
            value=2.0,
            step=1.0,
            help="Hard floor: 1-conversion terms are never promoted to avoid low-sample fluke traps.",
        )
        block_cost_cpa_multiplier = st.number_input(
            "Block Cost Gate (x Account CPA)",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Multiplier applied to account CPA to set minimum spend required to BLOCK.",
        )
        strict_fdr_gate = st.checkbox(
            "Strict BH FDR Multiple-Testing Gate",
            value=False,
            help="Require Benjamini-Hochberg adjusted q <= alpha instead of unadjusted p-value.",
        )

        if st.button("Reset Settings to Defaults", use_container_width=True):
            st.rerun()

    # System Diagnostics footer in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="font-size: 0.75rem; color: #64748b; line-height: 1.4;">
            <strong>QueryPilot Engine:</strong><br>
            • Deterministic SciPy Binomial<br>
            • Wilson 95% Credible Intervals<br>
            • Benjamini-Hochberg FDR Step-Up<br>
            • 100% Local &amp; Private (No API Keys)
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================================
    # MAIN WORKSPACE HEADER
    # =========================================================================
    raw_df = load_dataset()

    # Show upload error if any
    if st.session_state.get("upload_error"):
        st.error(f"❌ **Upload Error:** {st.session_state['upload_error']}")
        st.info("Upload a valid search term CSV report or switch back to the SYNTHETIC demo dataset.")
        return

    if raw_df is None:
        st.info(
            "👋 **Welcome to QueryPilot.** Upload a search term report `.csv` via the sidebar, "
            "or select **SYNTHETIC Demo Dataset** to inspect the triage engine."
        )
        return

    is_synthetic = st.session_state["dataset_source"] == "synthetic"
    active_filename = st.session_state.get("uploaded_filename", "dataset.csv")

    st.markdown(
        f"""
        <div class="querypilot-header-bar">
            <div>
                <p class="querypilot-title">QueryPilot</p>
                <p class="querypilot-subtitle">Search Term Triage Engine · DevSprint PS-01</p>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span class="querypilot-badge-prod">
                    ● PROD DETERMINISTIC
                </span>
                <span style="font-size: 0.8rem; font-family: monospace; background: #f1f5f9; padding: 4px 8px; border-radius: 4px; border: 1px solid #cbd5e1;">
                    {active_filename} ({len(raw_df):,} rows)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <span>🧪</span>
                <div>
                    <strong>SYNTHETIC DATASET ACTIVE:</strong> Using <code>data/sample_synthetic.csv</code>.
                    All rows are clearly labeled test cases designed to verify edge cases (2-click/1-conv trap,
                    costly zero-conversion losers, fractional conversions, and duplicates).
                    Not official hackathon results.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =========================================================================
    # SCHEMA MAPPING & COLUMN VERIFICATION
    # =========================================================================
    available_cols = list(raw_df.columns)
    suggested = suggest_column_mapping(available_cols)

    with st.expander("⚙️ Dataset Schema & Column Mapping", expanded=False):
        st.markdown(
            "<span style='font-size: 0.85rem; color: #475569;'>"
            "Columns detected automatically. Verify or adjust canonical mappings below if needed:</span>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)

        def _get_col_idx(col_name: Optional[str], opts: List[str]) -> int:
            if col_name and col_name in opts:
                return opts.index(col_name)
            return 0

        with c1:
            st.markdown("**Required Metrics:**")
            map_search_term = st.selectbox(
                "Search Term *",
                options=available_cols,
                index=_get_col_idx(suggested.get("search_term"), available_cols),
            )
            map_clicks = st.selectbox(
                "Clicks *",
                options=available_cols,
                index=_get_col_idx(suggested.get("clicks"), available_cols),
            )
            map_cost = st.selectbox(
                "Cost *",
                options=available_cols,
                index=_get_col_idx(suggested.get("cost"), available_cols),
            )
            map_conversions = st.selectbox(
                "Conversions *",
                options=available_cols,
                index=_get_col_idx(suggested.get("conversions"), available_cols),
            )

        with c2:
            st.markdown("**Campaign Hierarchy:**")
            opt_cols = ["(Not Mapped)"] + available_cols
            map_campaign = st.selectbox(
                "Campaign",
                options=opt_cols,
                index=_get_col_idx(suggested.get("campaign"), opt_cols),
            )
            map_ad_group = st.selectbox(
                "Ad Group",
                options=opt_cols,
                index=_get_col_idx(suggested.get("ad_group"), opt_cols),
            )

        with c3:
            st.markdown("**Optional Dimensions:**")
            map_match_type = st.selectbox(
                "Match Type",
                options=opt_cols,
                index=_get_col_idx(suggested.get("match_type"), opt_cols),
            )
            map_impressions = st.selectbox(
                "Impressions",
                options=opt_cols,
                index=_get_col_idx(suggested.get("impressions"), opt_cols),
            )
            map_conv_val = st.selectbox(
                "Conversion Value",
                options=opt_cols,
                index=_get_col_idx(suggested.get("conversion_value"), opt_cols),
            )

    mapping = ColumnMapping(
        search_term=map_search_term,
        clicks=map_clicks,
        cost=map_cost,
        conversions=map_conversions,
        campaign=None if map_campaign == "(Not Mapped)" else map_campaign,
        ad_group=None if map_ad_group == "(Not Mapped)" else map_ad_group,
        match_type=None if map_match_type == "(Not Mapped)" else map_match_type,
        impressions=None if map_impressions == "(Not Mapped)" else map_impressions,
        conversion_value=None if map_conv_val == "(Not Mapped)" else map_conv_val,
    )

    config = TriageConfig(
        alpha=float(alpha),
        shrinkage_k=float(shrinkage_k),
        min_test_clicks=int(min_test_clicks),
        min_promote_conversions=float(min_promote_conversions),
        block_cost_cpa_multiplier=float(block_cost_cpa_multiplier),
        strict_fdr_gate=bool(strict_fdr_gate),
    )

    # =========================================================================
    # EXECUTE TRIAGE ENGINE
    # =========================================================================
    try:
        results_df, summary, quality_report = run_triage_engine(raw_df, mapping, config)
    except ValueError as ve:
        st.error(f"❌ **Schema Validation Failed:** {ve}")
        st.info("Check the column mappings above and make sure the required fields match your CSV.")
        return
    except Exception as exc:
        st.error(f"❌ **Engine Execution Error:** {exc}")
        return

    # =========================================================================
    # DATA QUALITY REPORT
    # =========================================================================
    total_anomalies = (
        quality_report.missing_required_row_count
        + quality_report.negative_metric_row_count
        + quality_report.conversions_exceed_clicks_row_count
        + quality_report.fractional_conversion_row_count
        + quality_report.zero_click_row_count
        + quality_report.duplicate_query_row_count
    )

    if total_anomalies > 0:
        with st.expander(
            f"🔍 Data Quality Audit ({total_anomalies} issues detected)",
            expanded=False,
        ):
            q_col1, q_col2 = st.columns(2)
            with q_col1:
                st.markdown("**Integrity Verification:**")
                st.markdown(
                    f"""
                    - **Total Rows Ingested:** `{quality_report.total_rows:,}`
                    - **Unique Search Terms:** `{quality_report.unique_search_terms:,}`
                    - **Missing Required Metrics:** `{quality_report.missing_required_row_count}`
                    - **Zero-Click Rows:** `{quality_report.zero_click_row_count}`
                    - **Negative Metric Rows:** `{quality_report.negative_metric_row_count}`
                    """
                )
            with q_col2:
                st.markdown("**Behavioral Flags:**")
                st.markdown(
                    f"""
                    - **Conversions Exceed Clicks:** `{quality_report.conversions_exceed_clicks_row_count}`
                    - **Fractional Conversions (Attribution):** `{quality_report.fractional_conversion_row_count}`
                    - **Duplicate Queries in Campaign:** `{quality_report.duplicate_campaign_query_row_count}`
                    - **Duplicate Queries Across Campaigns:** `{quality_report.duplicate_query_row_count}`
                    - **Cost Incurred Without Clicks:** `{quality_report.cost_without_clicks_row_count}`
                    """
                )
            st.info(
                "💡 **Conservative Anomaly Handling:** Rows with fatal anomalies (missing values, negative numbers, "
                "or conv > clicks) are safely assigned to `IGNORE` and flagged for review. They are excluded from the "
                "baseline conversion pool so corrupt rows never distort account-level benchmarks."
            )

    # =========================================================================
    # KPI SUMMARY METRICS
    # =========================================================================
    st.markdown("### 📊 Performance Summary")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    promote_pct = (summary.promote_count / summary.total_rows * 100) if summary.total_rows > 0 else 0
    block_pct = (summary.block_count / summary.total_rows * 100) if summary.total_rows > 0 else 0
    ignore_pct = (summary.ignore_count / summary.total_rows * 100) if summary.total_rows > 0 else 0

    kpi1.metric("Total Analyzed", f"{summary.total_rows:,}", help="Total search terms evaluated by engine")
    kpi2.metric(
        "PROMOTE",
        f"{summary.promote_count:,}",
        delta=f"{promote_pct:.1f}% of terms",
        delta_color="normal",
        help="High-confidence outperforming search terms recommended for dedicated exact match ad groups",
    )
    kpi3.metric(
        "BLOCK",
        f"{summary.block_count:,}",
        delta=f"{block_pct:.1f}% of terms",
        delta_color="inverse",
        help="Statistically significant budget-bleed terms recommended for negative keyword lists",
    )
    kpi4.metric(
        "IGNORE / HOLD",
        f"{summary.ignore_count:,}",
        delta=f"{ignore_pct:.1f}% of terms",
        delta_color="off",
        help="Terms within normal baseline variation or insufficient click sample",
    )
    kpi5.metric(
        "REVIEW QUEUE",
        f"{summary.review_flagged_count:,}",
        delta=f"{summary.review_flagged_count / summary.total_rows * 100:.1f}% flagged",
        delta_color="off",
        help="Terms requiring human review due to borderline signals, anomalies, or attribution flags",
    )

    # Account baseline and cost gate sub-strip
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(
            f"<div style='font-size:0.8rem; color:#475569;'><strong>Account Baseline CVR:</strong> "
            f"<code>{summary.account_baseline_cvr * 100:.2f}%</code></div>",
            unsafe_allow_html=True,
        )
    with b2:
        cpa_str = f"${summary.account_cpa:.2f}" if summary.account_cpa is not None else "N/A"
        st.markdown(
            f"<div style='font-size:0.8rem; color:#475569;'><strong>Account Avg CPA:</strong> "
            f"<code>{cpa_str}</code></div>",
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f"<div style='font-size:0.8rem; color:#475569;'><strong>Effective Block Cost Gate:</strong> "
            f"<code>${summary.effective_block_cost_gate:.2f}</code></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # =========================================================================
    # DECISION CHARTS (Altair)
    # =========================================================================
    st.markdown("### 📈 Visual Distribution")
    c_chart1, c_chart2 = st.columns([1, 2])

    with c_chart1:
        decision_counts = (
            results_df["decision"]
            .value_counts()
            .reindex(["PROMOTE", "BLOCK", "IGNORE"], fill_value=0)
            .reset_index()
        )
        decision_counts.columns = ["Decision", "Count"]

        bar = (
            alt.Chart(decision_counts)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Decision:N", title=None, sort=["PROMOTE", "BLOCK", "IGNORE"]),
                y=alt.Y("Count:Q", title="Search Terms"),
                color=alt.Color(
                    "Decision:N",
                    scale=alt.Scale(
                        domain=["PROMOTE", "BLOCK", "IGNORE"],
                        range=["#10b981", "#ef4444", "#94a3b8"],
                    ),
                    legend=None,
                ),
                tooltip=["Decision", "Count"],
            )
            .properties(height=260)
        )
        st.altair_chart(bar, use_container_width=True)

    with c_chart2:
        scatter_data = results_df[results_df["clicks"] > 0]
        if not scatter_data.empty:
            scatter = (
                alt.Chart(scatter_data)
                .mark_circle(size=65, opacity=0.8)
                .encode(
                    x=alt.X("clicks:Q", title="Clicks (Log Scale)", scale=alt.Scale(type="log")),
                    y=alt.Y("observed_cvr:Q", title="Observed CVR", axis=alt.Axis(format="%")),
                    color=alt.Color(
                        "decision:N",
                        scale=alt.Scale(
                            domain=["PROMOTE", "BLOCK", "IGNORE"],
                            range=["#10b981", "#ef4444", "#94a3b8"],
                        ),
                        legend=alt.Legend(title="Decision", orient="top"),
                    ),
                    tooltip=[
                        "search_term",
                        "clicks",
                        "conversions",
                        alt.Tooltip("cost:Q", format="$.2f"),
                        alt.Tooltip("observed_cvr:Q", format=".2%"),
                        alt.Tooltip("shrunk_baseline_cvr:Q", format=".2%"),
                        "decision",
                    ],
                )
                .properties(height=260)
            )
            st.altair_chart(scatter, use_container_width=True)
        else:
            st.info("No rows with clicks > 0 available for scatter analysis.")

    st.markdown("---")

    # =========================================================================
    # SEARCH & MULTI-FILTER TOOLBAR
    # =========================================================================
    st.markdown("### 🔎 Search & Filter Results")

    all_campaigns = sorted([c for c in results_df["campaign"].dropna().unique() if str(c).strip()])
    all_match_types = sorted([m for m in results_df["match_type"].dropna().unique() if str(m).strip()])

    f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.2, 2])

    with f_col1:
        filter_decisions = st.multiselect(
            "Filter by Decision:",
            options=["PROMOTE", "BLOCK", "IGNORE"],
            default=["PROMOTE", "BLOCK", "IGNORE"],
        )

    with f_col2:
        filter_campaigns = st.multiselect(
            "Filter by Campaign:",
            options=all_campaigns,
            default=[],
            help="Leave empty to include all campaigns.",
        )

    with f_col3:
        filter_match_types = st.multiselect(
            "Match Type:",
            options=all_match_types,
            default=[],
            help="Leave empty to include all match types.",
        )

    with f_col4:
        search_query = st.text_input(
            "Search Query / Keyword / Reason:",
            value="",
            placeholder="Search query text, ad group, or reason...",
        )

    f_sub1, f_sub2 = st.columns([2, 1])
    with f_sub1:
        review_only = st.checkbox("🚩 Show Only Flagged for Human Review", value=False)
    with f_sub2:
        if st.button("Reset All Filters", use_container_width=True):
            st.session_state["selected_term_override"] = None
            st.rerun()

    # Apply filters using export utility
    displayed_df = filter_and_sort_results(
        results_df=results_df,
        decisions=filter_decisions if filter_decisions else ["PROMOTE", "BLOCK", "IGNORE"],
        campaigns=filter_campaigns if filter_campaigns else None,
        match_types=filter_match_types if filter_match_types else None,
        review_only=review_only,
        search_query=search_query,
        sort_by="row_id",
        ascending=True,
    )

    st.markdown(
        f"<span style='font-size: 0.85rem; color: #64748b; font-weight: 500;'>"
        f"Showing <strong>{len(displayed_df):,}</strong> of <strong>{len(results_df):,}</strong> evaluated search terms</span>",
        unsafe_allow_html=True,
    )

    # =========================================================================
    # RESULTS DATA TABLE
    # =========================================================================
    if displayed_df.empty:
        st.warning("No search terms match your current filter criteria. Try clearing filters or widening search.")
        selected_row_data = None
    else:
        # Streamlit interactive dataframe
        table_event = st.dataframe(
            displayed_df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            height=380,
            column_config={
                "row_id": st.column_config.NumberColumn("ID", width="small"),
                "search_term": st.column_config.TextColumn("Search Term", width="medium"),
                "campaign": st.column_config.TextColumn("Campaign", width="medium"),
                "match_type": st.column_config.TextColumn("Match", width="small"),
                "clicks": st.column_config.NumberColumn("Clicks", format="%d"),
                "conversions": st.column_config.NumberColumn("Conv", format="%.1f"),
                "cost": st.column_config.NumberColumn("Cost", format="$%.2f"),
                "observed_cvr": st.column_config.NumberColumn("CVR", format="%.2%"),
                "observed_cpa": st.column_config.NumberColumn("CPA", format="$%.2f"),
                "decision": st.column_config.TextColumn("Decision", width="small"),
                "confidence_tier": st.column_config.TextColumn("Confidence Tier", width="medium"),
                "review_flag": st.column_config.CheckboxColumn("Review?"),
                "reason": st.column_config.TextColumn("Decision Reason", width="large"),
            },
        )

        # Determine selected row
        selected_row_data = None
        # Check if table row was clicked
        if table_event and table_event.selection and table_event.selection.rows:
            sel_idx = table_event.selection.rows[0]
            if sel_idx < len(displayed_df):
                selected_row_data = displayed_df.iloc[sel_idx]
                st.session_state["selected_term_override"] = str(selected_row_data["search_term"])

        # Fallback to dropdown or session state override
        term_options = displayed_df["search_term"].tolist()
        if selected_row_data is None and st.session_state.get("selected_term_override") in term_options:
            matched = displayed_df[displayed_df["search_term"] == st.session_state["selected_term_override"]]
            if not matched.empty:
                selected_row_data = matched.iloc[0]

        if selected_row_data is None and not displayed_df.empty:
            selected_row_data = displayed_df.iloc[0]

    # =========================================================================
    # SELECTED-TERM EVIDENCE INSPECTOR
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🔬 Evidence Inspector")

    if selected_row_data is not None:
        term_name = str(selected_row_data["search_term"])
        term_options = displayed_df["search_term"].tolist()
        term_idx = term_options.index(term_name) if term_name in term_options else 0

        # Dedicated dropdown selector to ensure 100% reliable inspection
        pick_term = st.selectbox(
            "Select Search Term to Inspect:",
            options=term_options,
            index=term_idx,
            help="Choose a term from the filtered results to inspect its complete statistical evidence.",
        )
        if pick_term != term_name:
            matched = displayed_df[displayed_df["search_term"] == pick_term]
            if not matched.empty:
                selected_row_data = matched.iloc[0]
                st.session_state["selected_term_override"] = pick_term

        row = selected_row_data
        decision_label = str(row["decision"])
        review_required = bool(row["review_flag"])

        badge_html = f'<span class="badge badge-{decision_label}">{decision_label}</span>'
        review_html = '<span class="badge badge-REVIEW">🚩 REVIEW REQUIRED</span>' if review_required else ""

        st.markdown(
            f"""
            <div class="inspector-panel">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <div>{badge_html} {review_html}</div>
                    <span style="font-family: monospace; font-size: 0.8rem; color: #64748b;">
                        Row ID #{row['row_id']} · Campaign: {row['campaign']} · Match: {row['match_type']}
                    </span>
                </div>
                <h4 style="font-family: monospace; font-size: 1.15rem; color: #0f172a; margin-top: 6px; word-break: break-all;">
                    {row['search_term']}
                </h4>
                <div style="background-color: #f8fafc; border-left: 3px solid #2563eb; padding: 10px 14px; margin-bottom: 16px; border-radius: 4px;">
                    <strong style="color: #1e40af; font-size: 0.85rem;">Deterministic Engine Rationale:</strong>
                    <p style="margin: 4px 0 0 0; font-family: monospace; font-size: 0.82rem; color: #334155; line-height: 1.45;">
                        {row['reason']}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Metric Cards for Selected Term
        i1, i2, i3, i4 = st.columns(4)
        clicks_val = float(row["clicks"])
        conv_val = float(row["conversions"])
        cost_val = float(row["cost"])
        cpa_val = float(row["observed_cpa"]) if pd.notna(row["observed_cpa"]) else None

        i1.metric("Observed Clicks", f"{clicks_val:g}")
        i2.metric("Conversions", f"{conv_val:g}")
        i3.metric("Total Spend", f"${cost_val:.2f}")
        i4.metric("Observed CPA", f"${cpa_val:.2f}" if cpa_val is not None else "No Conv")

        # Statistical Details Sub-grid
        st.markdown("##### Statistical Test Breakdown & Credible Intervals")
        s1, s2, s3 = st.columns(3)

        with s1:
            st.markdown(
                f"""
                - **Observed CVR:** `{row['observed_cvr'] * 100:.2f}%`
                - **Shrunk Baseline CVR (P₀):** `{row['shrunk_baseline_cvr'] * 100:.2f}%`
                - **Campaign LOO CVR:** `{row['campaign_loo_cvr'] * 100:.2f}%`
                - **Account LOO CVR:** `{row['account_loo_cvr'] * 100:.2f}%`
                """
            )

        with s2:
            st.markdown(
                f"""
                - **Wilson 95% Credible Interval:** `[{row['wilson_ci_lower'] * 100:.2f}%, {row['wilson_ci_upper'] * 100:.2f}%]`
                - **Lower Tail p-value (p_low):** `{row['p_value_lower']:.4f}`
                - **Upper Tail p-value (p_up):** `{row['p_value_upper']:.4f}`
                - **FDR Adjusted q_up:** `{row['q_value_upper']:.4f}`
                """
            )

        with s3:
            st.markdown(
                f"""
                - **Confidence Tier:** `{row['confidence_tier']}`
                - **Data Quality Flags:** `{row['quality_flags']}`
                - **Sample Size Gate:** `{'PASS (>= ' + str(config.min_test_clicks) + ' clicks)' if clicks_val >= config.min_test_clicks else 'FAIL (< ' + str(config.min_test_clicks) + ' clicks)'}`
                - **Conversion Floor Gate:** `{'PASS (>= 2 conv)' if conv_val >= 2.0 else 'HOLD (< 2 conv)'}`
                """
            )

        # Operational Tactical Directive
        st.markdown("##### Prescribed Operational Directive")
        if decision_label == "PROMOTE":
            st.success(
                f"✅ **Promote to Exact Match Keyword:** Search term exhibits statistically significant positive conversion lift "
                f"({conv_val:g} conv / {clicks_val:g} clicks, CVR {row['observed_cvr'] * 100:.2f}% vs baseline {row['shrunk_baseline_cvr'] * 100:.2f}%). "
                f"Recommendation: Add as Exact Match in a dedicated ad group inside `{row['campaign']}` with targeted CPA."
            )
        elif decision_label == "BLOCK":
            st.error(
                f"🛑 **Add as Negative Keyword:** Search term has burned ${cost_val:.2f} (exceeding the block cost gate "
                f"${summary.effective_block_cost_gate:.2f}) with zero or non-viable conversions. "
                f"Recommendation: Add to Campaign Negative Keyword list immediately to halt budget bleed."
            )
        else:
            st.info(
                f"⏸️ **Maintain Passive Observation:** Term is currently within expected baseline variation or below minimum "
                f"click threshold ({clicks_val:g} clicks). No automated account changes recommended."
            )

    # =========================================================================
    # EXPORT FUNCTIONALITY (Multiple Scopes)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 💾 Export Decision CSVs")
    st.markdown(
        "<span style='font-size: 0.85rem; color: #64748b;'>"
        "Download deterministic decision reports in CSV format for Google Ads bulk uploads, negative lists, or offline audit:</span>",
        unsafe_allow_html=True,
    )

    prefix = "synthetic" if is_synthetic else "official"
    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

    with exp_col1:
        st.download_button(
            label=f"📥 Download Current View ({len(displayed_df):,} rows)",
            data=results_to_csv_string(displayed_df),
            file_name=f"querypilot_{prefix}_filtered_{len(displayed_df)}_terms.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download rows matching active search and filter settings.",
        )

    with exp_col2:
        promote_df = results_df[results_df["decision"] == "PROMOTE"]
        st.download_button(
            label=f"🚀 Download PROMOTE List ({len(promote_df):,} terms)",
            data=results_to_csv_string(promote_df),
            file_name=f"querypilot_{prefix}_promote_{len(promote_df)}_terms.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=len(promote_df) == 0,
            help="Download high-performing terms ready for keyword expansion.",
        )

    with exp_col3:
        block_df = results_df[results_df["decision"] == "BLOCK"]
        st.download_button(
            label=f"🛑 Download BLOCK List ({len(block_df):,} terms)",
            data=results_to_csv_string(block_df),
            file_name=f"querypilot_{prefix}_block_{len(block_df)}_terms.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=len(block_df) == 0,
            help="Download wasted spend terms ready for negative keyword lists.",
        )

    with exp_col4:
        review_df = results_df[results_df["review_flag"] == True]  # noqa: E712
        st.download_button(
            label=f"🚩 Download REVIEW Queue ({len(review_df):,} terms)",
            data=results_to_csv_string(review_df),
            file_name=f"querypilot_{prefix}_review_{len(review_df)}_terms.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=len(review_df) == 0,
            help="Download flagged rows needing manual verification.",
        )


if __name__ == "__main__":
    main()
