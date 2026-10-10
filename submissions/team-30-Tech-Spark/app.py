"""
AdCreative Intelligence - Main Streamlit Web Application
Challenge: PS-02 | AdCreative Intelligence

A professional marketing & creative analytics SaaS workspace:
- Data Ingestion, Schema Validation & Stem-Based Image Matching Audit (zero silent discards)
- Automated Computer Vision Feature Extraction with Explicit Measurement Provenance
- Creative Library Gallery, Single-Creative Detail Inspector & Pairwise Variant Hypothesis Testing
- Cluster-Appropriate Statistical Engine with Benjamini-Hochberg FDR Correction
- Ranked Statistical Findings with Practical vs. Statistical Significance & Forest Plots
- Deterministic, Data-Grounded Creative Brief Generator (10-Section Strategy Workspace + A/B Roadmap)
- Multi-Format Export Center (CSV, JSON, Markdown, and Executive PDF)
"""

import importlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_ingestion as _di_mod
import feature_extraction as _fe_mod
import statistical_engine as _se_mod
import synthetic_data as _sd_mod
import creative_brief as _cb_mod
import recommendations as _rec_mod

if not hasattr(_di_mod, "compute_data_quality_summary") or not hasattr(_di_mod, "apply_column_mapping"):
    importlib.reload(_di_mod)
if not hasattr(_fe_mod, "FEATURE_PROVENANCE_MAP") or not hasattr(_fe_mod, "UNAVAILABLE_CAPABILITIES"):
    importlib.reload(_fe_mod)
if not hasattr(_se_mod, "build_creative_scorecard") or not hasattr(_se_mod, "compare_multiple_creatives"):
    importlib.reload(_se_mod)
if not hasattr(_cb_mod, "build_consolidated_report_markdown"):
    importlib.reload(_cb_mod)
if not hasattr(_rec_mod, "generate_experiment_plan"):
    importlib.reload(_rec_mod)

from data_ingestion import (
    ingest_ad_dataset,
    generate_example_csv_content,
    validate_and_parse_csv,
    match_images_to_records,
    normalize_identifier_candidates,
    ensure_persistent_image,
    suggest_column_mapping,
    apply_column_mapping,
    compute_data_quality_summary,
    SUPPORTED_IMAGE_EXTENSIONS,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
)
from feature_extraction import (
    extract_features_from_image,
    batch_extract_features,
    FEATURE_PROVENANCE_MAP,
    UNAVAILABLE_CAPABILITIES,
)
from statistical_engine import (
    run_full_statistical_analysis,
    compute_aggregate_kpis,
    investigate_confounding,
    compare_creative_variants,
    compare_multiple_creatives,
    build_creative_scorecard,
    rank_creatives,
    Finding,
)
from synthetic_data import (
    get_synthetic_dataset_paths,
    generate_synthetic_dataset,
)
from creative_brief import (
    generate_creative_brief,
    findings_to_export_df,
    build_consolidated_report_markdown,
)
from recommendations import (
    generate_recommendations,
    generate_experiment_plan,
    generate_pdf_report_bytes,
)
from database import get_storage


st.set_page_config(
    page_title="AdCreative Intelligence | Creative Analytics Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# SAAS DESIGN SYSTEM CSS (Motion / GoMarble Inspired Clean Light Theme)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Base Application Surface & Charcoal Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #0F172A;
    }
    .stApp {
        background-color: #F8FAFC;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1440px !important;
    }

    /* Clean SaaS Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B !important;
    }
    [data-testid="stSidebar"] * {
        color: #F1F5F9 !important;
    }
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
        color: #94A3B8 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
        margin: 0.85rem 0 !important;
    }

    /* Sidebar Navigation Items */
    [data-testid="stSidebar"] [role="radiogroup"] > label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        padding: 9px 12px !important;
        margin-bottom: 4px !important;
        transition: background-color 0.12s ease, border-color 0.12s ease !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.10) !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
        background: #4F46E5 !important;
        border-color: #6366F1 !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
    }

    /* Sidebar Buttons */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        border: 1px solid #6366F1 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
        padding: 0.5rem 0.85rem !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4338CA !important;
        border-color: #818CF8 !important;
    }

    /* Main Workspace Buttons */
    .stButton > button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        border: 1px solid #4338CA !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #4338CA !important;
    }
    .stButton > button[kind="secondary"], .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    }
    .stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover {
        border-color: #4F46E5 !important;
        color: #4F46E5 !important;
        background-color: #F5F7FF !important;
    }

    /* Native Metric Cards */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        color: #64748B !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* SaaS Page Header */
    .saas-page-header {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .saas-page-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin: 0 0 4px 0;
    }
    .saas-page-subtitle {
        font-size: 0.88rem;
        color: #475569;
        margin: 0;
    }

    /* Status Badges */
    .saas-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 11px;
        border-radius: 8px;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .pill-indigo {
        background-color: #EEF2FF;
        color: #3730A3;
        border: 1px solid #C7D2FE;
    }
    .pill-amber {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .pill-emerald {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .pill-red {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }
    .pill-slate {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }

    /* Custom KPI Card Component */
    .saas-kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        margin-bottom: 12px;
        height: 100%;
    }
    .saas-kpi-label {
        font-size: 0.73rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 6px;
    }
    .saas-kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #0F172A;
        font-variant-numeric: tabular-nums;
        line-height: 1.2;
    }
    .saas-kpi-sub {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 6px;
        font-variant-numeric: tabular-nums;
    }

    /* Section Header */
    .saas-section-header {
        font-size: 1.02rem;
        font-weight: 700;
        color: #0F172A;
        margin: 18px 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #E2E8F0;
        letter-spacing: -0.01em;
    }

    /* Evidence Classification Badges */
    .badge-supported {
        background-color: #ECFDF5;
        color: #047857;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.76rem;
        border: 1px solid #A7F3D0;
    }
    .badge-preliminary {
        background-color: #FFFBEB;
        color: #B45309;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.76rem;
        border: 1px solid #FDE68A;
    }
    .badge-underpowered {
        background-color: #F5F3FF;
        color: #6D28D9;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.76rem;
        border: 1px solid #DDD6FE;
    }
    .badge-neutral {
        background-color: #F1F5F9;
        color: #475569;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.76rem;
        border: 1px solid #CBD5E1;
    }
    .badge-unsupported {
        background-color: #FEF2F2;
        color: #B91C1C;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.76rem;
        border: 1px solid #FECACA;
    }

    /* Finding Card */
    .finding-box {
        border: 1px solid #E2E8F0;
        border-left: 4px solid #4F46E5;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
        background-color: #FFFFFF;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* Synthetic Notice Banner */
    .synthetic-banner {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 4px solid #D97706;
        color: #92400E;
        padding: 10px 16px;
        border-radius: 10px;
        font-size: 0.85rem;
        margin-bottom: 16px;
    }

    /* Creative Gallery Card & Missing Image Placeholder */
    .creative-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8px 0 6px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #F1F5F9;
    }
    .creative-id-label {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.86rem;
        color: #0F172A;
        background: #F1F5F9;
        padding: 2px 8px;
        border-radius: 6px;
    }
    .creative-kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 8px 0;
        font-variant-numeric: tabular-nums;
    }
    .creative-kpi-item {
        font-size: 0.79rem;
        color: #334155;
    }
    .creative-kpi-item strong {
        color: #0F172A;
    }
    .missing-image-placeholder {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 10px;
        padding: 24px 14px;
        text-align: center;
        color: #64748B;
        margin-bottom: 8px;
    }

    /* Workflow Stepper */
    .workflow-stepper {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px;
        margin-bottom: 16px;
    }
    .workflow-step {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 14px;
    }
    .workflow-step-num {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #4F46E5;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }
    .workflow-step-title {
        font-size: 0.86rem;
        font-weight: 600;
        color: #0F172A;
    }
    .workflow-step-desc {
        font-size: 0.76rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* Empty State Card */
    .saas-empty-state {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 28px 24px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        margin: 10px 0 18px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Support both clean SaaS page names and legacy numbered page names
PAGES = [
    "1. Overview",
    "2. Upload Creatives",
    "3. Creative Library",
    "4. Ranked Findings",
    "5. Creative Brief",
    "6. Export Center",
]

PAGE_DISPLAY_LABELS = {
    "1. Overview": "Overview",
    "2. Upload Creatives": "Upload Creatives",
    "3. Creative Library": "Creative Library",
    "4. Ranked Findings": "Ranked Findings",
    "5. Creative Brief": "Creative Brief Generator",
    "6. Export Center": "Export Center",
}

PAGE_ALIASES = {
    "Overview": "1. Overview",
    "1. Overview": "1. Overview",
    "Upload Creatives": "2. Upload Creatives",
    "2. Upload Creatives": "2. Upload Creatives",
    "Creative Library": "3. Creative Library",
    "3. Creative Library": "3. Creative Library",
    "Ranked Findings": "4. Ranked Findings",
    "4. Ranked Findings": "4. Ranked Findings",
    "Creative Brief Generator": "5. Creative Brief",
    "Creative Brief": "5. Creative Brief",
    "5. Creative Brief": "5. Creative Brief",
    "Export Center": "6. Export Center",
    "6. Export Center": "6. Export Center",
}


# ---------------------------------------------------------------------------
# REUSABLE UI & FORMATTING COMPONENTS
# ---------------------------------------------------------------------------
def _apply_saas_chart_theme(fig: go.Figure, height: int = 320) -> go.Figure:
    """Applies a consistent, readable SaaS analytics theme to Plotly charts."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color="#0F172A", size=12),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=18, r=18, t=34, b=18),
        height=height,
        title_font=dict(size=13, color="#0F172A", family="Inter, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.85)",
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9", zerolinecolor="#E2E8F0", linecolor="#CBD5E1")
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", zerolinecolor="#E2E8F0", linecolor="#CBD5E1")
    return fig


def _render_kpi_card(label: str, value: str, subtext: str = "", border_color: str = "#4F46E5") -> None:
    """Renders a white SaaS KPI card with top accent bar and tabular numerals."""
    st.markdown(
        f"""
        <div class="saas-kpi-card" style="border-top: 3px solid {border_color};">
            <div class="saas-kpi-label">{label}</div>
            <div class="saas-kpi-value">{value}</div>
            <div class="saas-kpi-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_status_badge(label: str, variant: str = "slate") -> str:
    """Returns HTML for a semantic status pill (indigo, emerald, amber, red, slate)."""
    css_cls = f"pill-{variant}" if variant in ("indigo", "emerald", "amber", "red", "slate") else "pill-slate"
    return f'<span class="saas-status-pill {css_cls}">{label}</span>'


def _render_page_header(title: str, subtitle: str) -> None:
    """Renders a consistent SaaS page header with active dataset status badge."""
    if st.session_state.df_ads is None or st.session_state.df_ads.empty:
        pill_html = _render_status_badge("No Dataset Loaded", "slate")
    elif st.session_state.is_synthetic:
        pill_html = _render_status_badge(
            f"DEMO DATA — SYNTHETIC EXAMPLE ({len(st.session_state.df_ads)} Creatives)", "amber"
        )
    else:
        pill_html = _render_status_badge(f"Empirical Dataset ({len(st.session_state.df_ads)} Creatives)", "indigo")

    st.markdown(
        f"""
        <div class="saas-page-header">
            <div>
                <h1 class="saas-page-title">{title}</h1>
                <p class="saas-page-subtitle">{subtitle}</p>
            </div>
            <div>{pill_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_finding_badge_info(evidence_classification: str) -> Tuple[str, str, str]:
    """
    Maps backend evidence_classification to defensible SaaS badge labels:
      - Supported association -> Statistically Significant
      - Preliminary -> Promising
      - Underpowered / Not estimable -> Insufficient Data
      - No clear association / Unsupported -> Inconclusive
    """
    if evidence_classification == "Supported association":
        return ("Statistically Significant", "badge-supported", "Supported association (FDR q < 0.05)")
    if evidence_classification in ("Preliminary", "Preliminary evidence"):
        return ("Promising", "badge-preliminary", "Preliminary signal (p < 0.05 or q < 0.15)")
    if evidence_classification in ("Underpowered", "Not estimable"):
        return ("Insufficient Data", "badge-underpowered", f"{evidence_classification} (Sample below threshold)")
    if evidence_classification == "No clear association":
        return ("Inconclusive", "badge-neutral", "No clear association (Negligible effect, p > 0.20)")
    return ("Inconclusive", "badge-unsupported", f"{evidence_classification} (Non-significant)")


def _assess_practical_significance(f: Finding) -> str:
    """
    Distinguishes practical (business) importance from statistical significance
    based on observed effect magnitude (relative uplift %, Cohen's d, or Spearman rho).
    """
    if f.attribute_type == "categorical":
        uplift = abs(float(f.effect_size.get("relative_uplift_pct", 0.0) or 0.0))
        cohen_d = abs(float(f.effect_size.get("cohens_d", 0.0) or 0.0))
        if uplift >= 25.0 or cohen_d >= 0.80:
            mag = f"Large practical magnitude ({uplift:.1f}% relative difference, |d|={cohen_d:.2f})"
        elif uplift >= 10.0 or cohen_d >= 0.40:
            mag = f"Moderate practical magnitude ({uplift:.1f}% relative difference, |d|={cohen_d:.2f})"
        else:
            mag = f"Small / marginal practical magnitude ({uplift:.1f}% relative difference, |d|={cohen_d:.2f})"
    else:
        rho = abs(float(f.effect_size.get("spearman_rho", 0.0) or 0.0))
        if rho >= 0.50:
            mag = f"Strong rank association (|Spearman ρ|={rho:.2f})"
        elif rho >= 0.25:
            mag = f"Moderate rank association (|Spearman ρ|={rho:.2f})"
        else:
            mag = f"Weak rank association (|Spearman ρ|={rho:.2f})"

    if f.evidence_classification == "Supported association":
        return f"{mag} — Statistically supported after FDR correction; strong candidate for production split testing."
    if f.evidence_classification in ("Preliminary", "Preliminary evidence"):
        return f"{mag} — Promising directional magnitude, but requires a controlled A/B test to confirm."
    if f.evidence_classification == "Underpowered":
        n_a = f.sample_sizes.get("creatives_group_a", f.sample_sizes.get("creatives_count", 0))
        n_b = f.sample_sizes.get("creatives_group_b", 0)
        sample_str = f"n={n_a} vs n={n_b}" if f.attribute_type == "categorical" else f"n={n_a}"
        return f"{mag} — Observed in an underpowered sample ({sample_str}); high variance prevents reliable practical conclusions."
    return f"{mag} — Insufficient statistical evidence to confirm a repeatable practical effect."


def _recommended_next_step_for_finding(f: Finding) -> str:
    """Generates a defensible next-step action for a statistical finding."""
    if f.evidence_classification == "Supported association":
        return (
            f"Run a controlled 50/50 split test isolating '{f.attribute.split(':')[0].strip()}' on {f.outcome_metric} "
            "while locking audience, placement, and bidding strategy."
        )
    if f.evidence_classification in ("Preliminary", "Preliminary evidence"):
        return (
            f"Treat as an exploratory hypothesis: test in a dedicated A/B cell before scaling budget toward '{f.attribute}'."
        )
    if f.evidence_classification in ("Underpowered", "Not estimable"):
        if f.attribute_type == "categorical":
            n_a = int(f.sample_sizes.get("creatives_group_a", 0))
            n_b = int(f.sample_sizes.get("creatives_group_b", 0))
            add_a = max(0, 4 - n_a)
            add_b = max(0, 4 - n_b)
            return (
                f"Collect additional observations: add at least {add_a} more creative(s) in '{f.group_a}' and {add_b} more in '{f.group_b}' "
                "(target N >= 4 creatives per group and >= 5,000 impressions per creative) before re-evaluating."
            )
        else:
            n_c = int(f.sample_sizes.get("creatives_count", 0))
            add_c = max(0, 6 - n_c)
            return (
                f"Collect additional observations: ingest at least {add_c} more matched creative(s) (target N >= 6 total creatives) "
                "to enable continuous correlation inference."
            )
    return (
        f"Deprioritize design changes on '{f.attribute.split(':')[0].strip()}' for {f.outcome_metric}; focus creative testing on higher-ranked drivers."
    )


# ---------------------------------------------------------------------------
# SESSION STATE & IMAGE PERSISTENCE
# ---------------------------------------------------------------------------
def init_session_state():
    if "df_ads" not in st.session_state:
        st.session_state.df_ads = None
    if "images_dict" not in st.session_state:
        st.session_state.images_dict = {}
    if "uploaded_image_store" not in st.session_state:
        st.session_state.uploaded_image_store = {}
    if "features_df" not in st.session_state:
        st.session_state.features_df = None
    if "findings" not in st.session_state:
        st.session_state.findings = []
    if "is_synthetic" not in st.session_state:
        st.session_state.is_synthetic = False
    if "ingestion_result" not in st.session_state:
        st.session_state.ingestion_result = None
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = PAGES[0]
    if "selected_library_ad_id" not in st.session_state:
        st.session_state.selected_library_ad_id = None
    if "edited_brief_markdown" not in st.session_state:
        st.session_state.edited_brief_markdown = None
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = "default_workspace"


init_session_state()


def store_uploaded_images_in_session(uploaded_files: Any) -> Dict[str, Any]:
    """
    Converts uploaded image files (PNG, JPG, JPEG, WEBP, or ZIP bundles of images)
    into durable in-memory PIL.Image.Image objects stored in st.session_state.uploaded_image_store
    so images remain accessible across page navigation.
    """
    if not uploaded_files:
        return st.session_state.uploaded_image_store

    files_list = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
    for f_obj in files_list:
        fname = getattr(f_obj, "name", str(f_obj))
        ext = Path(fname).suffix.lower()
        if ext == ".zip":
            try:
                if hasattr(f_obj, "seek"):
                    f_obj.seek(0)
                raw_zip = f_obj.read() if hasattr(f_obj, "read") else Path(f_obj).read_bytes()
                if hasattr(f_obj, "seek"):
                    f_obj.seek(0)
                with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        member_name = Path(member.filename).name
                        if not member_name or member_name.startswith("."):
                            continue
                        if Path(member_name).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                            img_bytes = zf.read(member.filename)
                            st.session_state.uploaded_image_store[member_name] = ensure_persistent_image(img_bytes)
            except Exception:
                pass
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            st.session_state.uploaded_image_store[Path(fname).name] = ensure_persistent_image(f_obj)

    return st.session_state.uploaded_image_store


def resolve_creative_image(ad_id: str, images_dict: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    Resolves the image object for a given CSV ad_id across st.session_state.images_dict
    and st.session_state.uploaded_image_store, checking exact match and normalized candidates.
    """
    active_dict = images_dict if images_dict is not None else st.session_state.get("images_dict", {})
    ad_id_str = str(ad_id).strip()

    if ad_id_str in active_dict and active_dict[ad_id_str] is not None:
        return ensure_persistent_image(active_dict[ad_id_str])

    ad_candidates = set(normalize_identifier_candidates(ad_id_str))
    for source_dict in (active_dict, st.session_state.get("uploaded_image_store", {})):
        if not source_dict:
            continue
        for key, img_val in source_dict.items():
            if img_val is None:
                continue
            key_candidates = set(normalize_identifier_candidates(str(key)))
            if ad_candidates & key_candidates:
                persisted = ensure_persistent_image(img_val)
                active_dict[ad_id_str] = persisted
                return persisted

    return None


def get_session_uploaded_filenames() -> List[str]:
    """Returns a deduplicated list of uploaded image filenames in the current session."""
    names: List[str] = []
    ing_res = st.session_state.get("ingestion_result")
    if ing_res is not None and getattr(ing_res, "uploaded_filenames", None):
        for n in ing_res.uploaded_filenames:
            if n not in names:
                names.append(n)
    for n in st.session_state.get("uploaded_image_store", {}).keys():
        if n not in names:
            names.append(n)
    return names


def sync_active_dataset_with_image_store(image_lookup: Optional[Dict[str, Any]] = None) -> bool:
    """
    Re-matches the active CSV dataset against available images in session state,
    re-runs feature extraction and statistical analysis, and updates session state.
    Preserves all required and optional CSV columns.
    """
    if st.session_state.df_ads is None or st.session_state.df_ads.empty:
        return False

    source_images = image_lookup if image_lookup is not None else st.session_state.uploaded_image_store
    if not source_images:
        return False

    keep_candidates = list(REQUIRED_COLUMNS) + list(OPTIONAL_COLUMNS) + ["ctr", "cvr", "cpc", "cpa", "roas"]
    base_cols = list(dict.fromkeys([c for c in keep_candidates if c in st.session_state.df_ads.columns]))
    base_df = st.session_state.df_ads[base_cols].copy()

    res = ingest_ad_dataset(base_df, source_images, allow_view_through_conversions=True)
    if not res.is_valid:
        return False

    feat_dict = batch_extract_features(res.matched_images)
    feat_records = [{"ad_id": aid, **f} for aid, f in feat_dict.items()]
    f_df = pd.DataFrame(feat_records) if feat_records else pd.DataFrame(columns=["ad_id"])
    merged_df = pd.merge(res.df, f_df, on="ad_id", how="left")
    findings = run_full_statistical_analysis(merged_df)

    st.session_state.df_ads = merged_df
    st.session_state.images_dict = res.matched_images
    st.session_state.features_df = f_df
    st.session_state.findings = findings
    st.session_state.ingestion_result = res
    st.session_state.edited_brief_markdown = None
    return True


def navigate_to(page_name: str):
    """Programmatically switches the active navigation page."""
    st.session_state.nav_page = PAGE_ALIASES.get(page_name, page_name)


def select_creative_for_detail(ad_id: str):
    """Selects a creative ID for inspection in the Creative Library Detail View."""
    st.session_state.selected_library_ad_id = str(ad_id)


def select_creative_and_navigate(ad_id: str):
    """Selects a creative ID and navigates directly to the Creative Library Detail Inspector."""
    st.session_state.selected_library_ad_id = str(ad_id)
    st.session_state.nav_page = "3. Creative Library"


def _format_rate(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"{float(val) * 100.0:.2f}%"


def _format_currency(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"${float(val):,.2f}"


def _format_roas(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Unavailable"
    return f"{float(val):.2f}x"


@st.cache_data(show_spinner=False)
def build_sample_upload_zip_bytes() -> bytes:
    """Builds a downloadable ZIP containing sample creative PNGs and matching CSV for live upload testing."""
    csv_path, img_dir = get_synthetic_dataset_paths()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if csv_path.exists():
            zf.write(csv_path, arcname="ad_performance_sample.csv")
        for img_p in sorted(img_dir.glob("*.png")):
            zf.write(img_p, arcname=f"images/{img_p.name}")
    return buf.getvalue()


def load_demo_dataset():
    """Loads pre-generated synthetic dataset into session state."""
    with st.spinner("Loading and analyzing 18-creative demonstration dataset..."):
        csv_path, img_dir = get_synthetic_dataset_paths()

        images = {}
        for p in sorted(img_dir.glob("*.png")):
            images[p.name] = ensure_persistent_image(p)

        res = ingest_ad_dataset(csv_path, images)
        if res.is_valid:
            feat_dict = batch_extract_features(res.matched_images)
            feat_records = [{"ad_id": ad_id, **f} for ad_id, f in feat_dict.items()]
            f_df = pd.DataFrame(feat_records) if feat_records else pd.DataFrame(columns=["ad_id"])
            merged_df = pd.merge(res.df, f_df, on="ad_id", how="left")
            findings = run_full_statistical_analysis(merged_df)

            st.session_state.df_ads = merged_df
            st.session_state.images_dict = res.matched_images
            st.session_state.uploaded_image_store = dict(images)
            st.session_state.features_df = f_df
            st.session_state.findings = findings
            st.session_state.is_synthetic = True
            st.session_state.ingestion_result = res
            st.session_state.selected_library_ad_id = str(merged_df["ad_id"].iloc[0]) if not merged_df.empty else None
            st.session_state.edited_brief_markdown = None
            st.success("Loaded synthetic demonstration dataset (18 creatives).")


def reset_active_session():
    """Resets active dataset state cleanly without crashing."""
    st.session_state.df_ads = None
    st.session_state.images_dict = {}
    st.session_state.uploaded_image_store = {}
    st.session_state.features_df = None
    st.session_state.findings = []
    st.session_state.is_synthetic = False
    st.session_state.ingestion_result = None
    st.session_state.selected_library_ad_id = None
    st.session_state.edited_brief_markdown = None


# ---------------------------------------------------------------------------
# LEFT SIDEBAR SHELL
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    """
    <div style="padding: 4px 0 12px 0;">
        <div style="display:flex; align-items:center; gap:10px;">
            <div style="width:34px; height:34px; border-radius:9px; background:#4F46E5; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:0.95rem; color:#FFFFFF; letter-spacing:-0.03em; box-shadow:0 2px 6px rgba(79,70,229,0.35);">
                AC
            </div>
            <div>
                <div style="font-weight:700; font-size:0.98rem; letter-spacing:-0.01em; color:#F8FAFC;">AdCreative Intelligence</div>
                <div style="font-size:0.74rem; color:#94A3B8;">Creative Analytics Workspace</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_choice = st.sidebar.radio(
    "NAVIGATION",
    PAGES,
    format_func=lambda p: PAGE_DISPLAY_LABELS.get(p, p),
    key="nav_page",
)

st.sidebar.markdown("---")
if st.sidebar.button("Load Synthetic Demo (18 Ads)", use_container_width=True):
    load_demo_dataset()
    st.rerun()

if st.session_state.df_ads is not None and not st.session_state.df_ads.empty:
    if st.sidebar.button("Reset Active Dataset", use_container_width=True):
        reset_active_session()
        st.rerun()

# Sidebar Bottom: Dataset Status, Creatives Loaded, and Compact Documentation
if st.session_state.df_ads is not None and not st.session_state.df_ads.empty:
    dataset_status_str = (
        "DEMO DATA — SYNTHETIC EXAMPLE" if st.session_state.is_synthetic else "Empirical Campaign Dataset"
    )
    supp_count = sum(1 for f in st.session_state.findings if f.evidence_classification == "Supported association")
    st.sidebar.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.10); border-radius:10px; padding:12px 14px; margin-top:10px; font-size:0.80rem;">
            <div style="font-weight:700; color:#E2E8F0; margin-bottom:6px; font-size:0.73rem; text-transform:uppercase; letter-spacing:0.04em;">Dataset Status</div>
            <div style="color:#CBD5E1; margin-bottom:4px;">Status: <strong>{dataset_status_str}</strong></div>
            <div style="color:#CBD5E1; margin-bottom:4px;">Creatives Loaded: <strong>{len(st.session_state.df_ads)}</strong></div>
            <div style="color:#CBD5E1; margin-bottom:4px;">Matched Images: <strong>{len(st.session_state.images_dict)} / {len(st.session_state.df_ads)}</strong></div>
            <div style="color:#CBD5E1;">Significant Findings: <strong>{supp_count} / {len(st.session_state.findings)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        """
        <div style="background:rgba(255,255,255,0.03); border:1px dashed rgba(255,255,255,0.14); border-radius:10px; padding:12px 14px; margin-top:10px; font-size:0.79rem; color:#94A3B8;">
            <div style="font-weight:700; color:#E2E8F0; margin-bottom:4px; font-size:0.73rem; text-transform:uppercase;">Dataset Status</div>
            Status: <strong>No Dataset Loaded</strong><br>
            Creatives Loaded: <strong>0</strong><br>
            Load the 18-ad demo above or upload CSV &amp; images in <strong>Upload Creatives</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
with st.sidebar.expander("Help & Metric Definitions", expanded=False):
    st.markdown(
        """
        **Core Performance Ratios**:
        - **CTR**: `Clicks / Impressions`
        - **CVR**: `Conversions / Clicks`
        - **CPC**: `Spend / Clicks`
        - **CPA**: `Spend / Conversions`
        - **ROAS**: `Revenue / Spend` *(when revenue is available)*

        **Statistical Governance**:
        - **Pooled vs. Ad-Level**: Pooled ratios sum numerators and denominators (`ΣNum / ΣDenom`); ad-level means weight each creative equally.
        - **BH-FDR q-value**: Controls false discovery rate across simultaneous hypothesis tests.
        - **Observational Notice**: Correlation does not prove causation; validate findings via randomized A/B split testing.
        """
    )


# ===========================================================================
# PAGE 1: OVERVIEW DASHBOARD
# ===========================================================================
if nav_choice == "1. Overview":
    _render_page_header(
        "Creative Performance Overview",
        "Summarize campaign performance, identify top-performing creatives, and uncover statistically grounded testing opportunities.",
    )

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <strong>DEMO DATA — SYNTHETIC EXAMPLE</strong>: Analyzing 18 synthetic benchmark creatives generated for demonstration and pipeline verification. Upload your own campaign CSV and creative images in <strong>Upload Creatives</strong> for empirical production analysis.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.df_ads is None or st.session_state.df_ads.empty:
        st.markdown(
            """
            <div class="saas-empty-state">
                <h2 style="margin:0 0 8px 0; font-size:1.25rem; font-weight:700; color:#0F172A;">No Campaign Dataset Loaded</h2>
                <p style="color:#475569; max-width:640px; margin:0 auto 20px auto; font-size:0.90rem; line-height:1.55;">
                    Upload a performance CSV and creative image files to compute aggregate KPIs, extract visual features,
                    rank creatives, and run Benjamini-Hochberg FDR statistical comparisons — or load the 18-creative demonstration dataset to explore all capabilities immediately.
                </p>
                <div class="workflow-stepper" style="max-width:840px; margin:0 auto 10px auto; text-align:left;">
                    <div class="workflow-step">
                        <div class="workflow-step-num">Step 1 &bull; Ingest &amp; Audit</div>
                        <div class="workflow-step-title">Validate CSV &amp; Match Images</div>
                        <div class="workflow-step-desc">Verify required schema columns and match image filename stems across PNG, JPG, JPEG, and WEBP.</div>
                    </div>
                    <div class="workflow-step">
                        <div class="workflow-step-num">Step 2 &bull; Extract Signals</div>
                        <div class="workflow-step-title">Computer Vision Attributes</div>
                        <div class="workflow-step-desc">Measure color tone, luminance, contrast, composition, saliency, and frontal face presence.</div>
                    </div>
                    <div class="workflow-step">
                        <div class="workflow-step-num">Step 3 &bull; Statistical Brief</div>
                        <div class="workflow-step-title">Evidence-Based Roadmap</div>
                        <div class="workflow-step-desc">Rank hypotheses with FDR multiple-testing correction and build a prioritized A/B test plan.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, _ = st.columns([1.3, 1.3, 1.8])
        with c1:
            if st.button("Load Synthetic Demo Dataset", type="primary", use_container_width=True):
                load_demo_dataset()
                st.rerun()
        with c2:
            st.button("Go to Upload Creatives", on_click=navigate_to, args=("2. Upload Creatives",), use_container_width=True)
    else:
        df = st.session_state.df_ads
        kpis = compute_aggregate_kpis(df)
        has_roas = kpis.get("aggregate_roas") is not None

        # Primary KPI Row (5 core executive metrics — never fabricating percentage deltas)
        primary_cols = st.columns(5)
        with primary_cols[0]:
            _render_kpi_card(
                "Total Ad Spend",
                _format_currency(kpis["total_spend"]),
                f"Across {kpis['total_creatives']:,} active creatives",
                border_color="#4F46E5",
            )
        with primary_cols[1]:
            avg_imp = int(round(kpis["total_impressions"] / max(kpis["total_creatives"], 1)))
            _render_kpi_card(
                "Total Impressions",
                f"{kpis['total_impressions']:,}",
                f"Avg {avg_imp:,} impressions / creative",
                border_color="#6366F1",
            )
        with primary_cols[2]:
            _render_kpi_card(
                "Total Clicks",
                f"{kpis['total_clicks']:,}",
                f"Ad-Level Mean CTR: {_format_rate(kpis['mean_ad_ctr'])}",
                border_color="#0EA5E9",
            )
        with primary_cols[3]:
            _render_kpi_card(
                "Total Conversions",
                f"{kpis['total_conversions']:,}",
                f"Pooled CVR: {_format_rate(kpis['aggregate_cvr'])}",
                border_color="#10B981",
            )
        with primary_cols[4]:
            _render_kpi_card(
                "Average (Pooled) CTR",
                _format_rate(kpis["aggregate_ctr"]),
                f"Median Ad CTR: {_format_rate(kpis['median_ad_ctr'])}",
                border_color="#059669",
            )

        # Secondary Supporting Efficiency Metrics Row (CPC, CPA, CVR, Creatives, and ROAS when revenue exists)
        sec_cols = st.columns(5 if has_roas else 4)
        with sec_cols[0]:
            _render_kpi_card(
                "Average (Pooled) CPC",
                _format_currency(kpis["aggregate_cpc"]),
                f"Ad Mean CPC: {_format_currency(kpis['mean_ad_cpc'])}",
                border_color="#64748B",
            )
        with sec_cols[1]:
            _render_kpi_card(
                "Average (Pooled) CPA",
                _format_currency(kpis["aggregate_cpa"]),
                f"Ad Mean CPA: {_format_currency(kpis['mean_ad_cpa'])}",
                border_color="#64748B",
            )
        with sec_cols[2]:
            _render_kpi_card(
                "Average (Pooled) CVR",
                _format_rate(kpis["aggregate_cvr"]),
                f"Ad Mean CVR: {_format_rate(kpis['mean_ad_cvr'])}",
                border_color="#64748B",
            )
        with sec_cols[3]:
            _render_kpi_card(
                "Matched Creative Assets",
                f"{len(st.session_state.images_dict)} / {kpis['total_creatives']}",
                "Visual CV pipeline coverage",
                border_color="#64748B",
            )
        if has_roas:
            with sec_cols[4]:
                _render_kpi_card(
                    "Pooled ROAS",
                    _format_roas(kpis["aggregate_roas"]),
                    f"Total Revenue: {_format_currency(kpis.get('total_revenue'))}",
                    border_color="#8B5CF6",
                )

        with st.expander("Campaign-Level Pooled Metrics vs. Unweighted Ad-Level Distribution (Mean & Median)", expanded=False):
            st.caption(
                "Campaign-level pooled metrics weight each creative by its exposure volume (ΣNumerator / ΣDenominator), "
                "whereas unweighted ad-level averages treat each creative equally regardless of budget or impressions."
            )
            agg_rows = [
                {
                    "Performance Metric": "CTR (Click-Through Rate)",
                    "Campaign-Level Pooled (ΣNum / ΣDenom)": _format_rate(kpis["aggregate_ctr"]),
                    "Unweighted Ad-Level Mean": _format_rate(kpis["mean_ad_ctr"]),
                    "Unweighted Ad-Level Median": _format_rate(kpis["median_ad_ctr"]),
                },
                {
                    "Performance Metric": "CVR (Conversion Rate)",
                    "Campaign-Level Pooled (ΣNum / ΣDenom)": _format_rate(kpis["aggregate_cvr"]),
                    "Unweighted Ad-Level Mean": _format_rate(kpis["mean_ad_cvr"]),
                    "Unweighted Ad-Level Median": _format_rate(kpis["median_ad_cvr"]),
                },
                {
                    "Performance Metric": "CPC (Cost Per Click)",
                    "Campaign-Level Pooled (ΣNum / ΣDenom)": _format_currency(kpis["aggregate_cpc"]),
                    "Unweighted Ad-Level Mean": _format_currency(kpis["mean_ad_cpc"]),
                    "Unweighted Ad-Level Median": _format_currency(kpis["median_ad_cpc"]),
                },
                {
                    "Performance Metric": "CPA (Cost Per Acquisition)",
                    "Campaign-Level Pooled (ΣNum / ΣDenom)": _format_currency(kpis["aggregate_cpa"]),
                    "Unweighted Ad-Level Mean": _format_currency(kpis["mean_ad_cpa"]),
                    "Unweighted Ad-Level Median": _format_currency(kpis["median_ad_cpa"]),
                },
            ]
            if has_roas:
                agg_rows.append(
                    {
                        "Performance Metric": "ROAS (Return on Ad Spend)",
                        "Campaign-Level Pooled (ΣNum / ΣDenom)": _format_roas(kpis["aggregate_roas"]),
                        "Unweighted Ad-Level Mean": _format_roas(kpis["mean_ad_roas"]),
                        "Unweighted Ad-Level Median": _format_roas(kpis["median_ad_roas"]),
                    }
                )
            st.dataframe(pd.DataFrame(agg_rows), use_container_width=True, hide_index=True)

        # -------------------------------------------------------------------
        # PERFORMANCE TRENDS & DISTRIBUTION CHARTS
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Performance Trends &amp; Creative Distributions</div>', unsafe_allow_html=True)

        has_valid_dates = False
        parsed_dates_df = pd.DataFrame()
        if "date" in df.columns:
            temp_dates = pd.to_datetime(df["date"].replace("Unknown", np.nan), errors="coerce")
            if temp_dates.notna().sum() >= 2 and temp_dates.nunique() >= 2:
                has_valid_dates = True
                parsed_dates_df = df.copy()
                parsed_dates_df["_parsed_date"] = temp_dates
                parsed_dates_df = parsed_dates_df.dropna(subset=["_parsed_date"]).sort_values("_parsed_date")

        ch_row1_left, ch_row1_right = st.columns(2)

        with ch_row1_left:
            with st.container(border=True):
                if has_valid_dates:
                    tr_top1, tr_top2 = st.columns([1.3, 1.3])
                    with tr_top1:
                        trend_metric_opts = ["Spend ($)", "Conversions", "Pooled CTR (%)"] + (["Pooled ROAS (x)"] if has_roas else [])
                        selected_trend_metric = st.selectbox(
                            "Time-Series Metric",
                            trend_metric_opts,
                            key="overview_trend_metric_sel",
                        )
                    with tr_top2:
                        camp_opts = ["All Campaigns"]
                        if "campaign_name" in parsed_dates_df.columns:
                            camp_opts.extend(sorted([str(x) for x in parsed_dates_df["campaign_name"].dropna().unique() if str(x) != "Unknown"]))
                        selected_trend_camp = st.selectbox("Filter Trend by Campaign", camp_opts, key="overview_trend_camp_sel")

                    t_df = parsed_dates_df.copy()
                    if selected_trend_camp != "All Campaigns" and "campaign_name" in t_df.columns:
                        t_df = t_df[t_df["campaign_name"].astype(str) == selected_trend_camp]

                    agg_spec: Dict[str, str] = {"impressions": "sum", "clicks": "sum", "conversions": "sum", "spend": "sum"}
                    if "revenue" in t_df.columns:
                        agg_spec["revenue"] = "sum"
                    daily = t_df.groupby("_parsed_date", as_index=False).agg(agg_spec)
                    daily["Pooled CTR (%)"] = np.where(daily["impressions"] > 0, (daily["clicks"] / daily["impressions"]) * 100.0, np.nan)
                    daily["Spend ($)"] = daily["spend"]
                    daily["Conversions"] = daily["conversions"]
                    if "revenue" in daily.columns:
                        daily["Pooled ROAS (x)"] = np.where(daily["spend"] > 0, daily["revenue"] / daily["spend"], np.nan)

                    trend_fig = px.line(
                        daily,
                        x="_parsed_date",
                        y=selected_trend_metric,
                        markers=True,
                        title=f"{selected_trend_metric} Over Time",
                        labels={"_parsed_date": "Date", selected_trend_metric: selected_trend_metric},
                    )
                    trend_fig.update_traces(line_color="#4F46E5", line_width=2.5)
                    _apply_saas_chart_theme(trend_fig, height=280)
                    st.plotly_chart(trend_fig, use_container_width=True)
                else:
                    st.markdown("**CTR Comparison Across Creatives**")
                    st.caption("Time-series chart omitted (no valid `date` column in dataset) — showing CTR by creative vs. campaign baseline.")
                    ctr_plot_df = df.dropna(subset=["ctr"]).copy()
                    if not ctr_plot_df.empty:
                        ctr_plot_df["ctr_pct"] = ctr_plot_df["ctr"] * 100.0
                        ctr_plot_df = ctr_plot_df.sort_values("ctr_pct", ascending=False).head(18)
                        has_tone = "dominant_color_tone" in ctr_plot_df.columns and ctr_plot_df["dominant_color_tone"].notna().any()
                        ctr_fig = px.bar(
                            ctr_plot_df,
                            x="ad_id",
                            y="ctr_pct",
                            color="dominant_color_tone" if has_tone else None,
                            labels={"ad_id": "Creative ID", "ctr_pct": "CTR (%)", "dominant_color_tone": "Color Tone"},
                            color_discrete_map={"Warm": "#F97316", "Cool": "#4F46E5", "Neutral": "#64748B"},
                        )
                        if kpis.get("aggregate_ctr") is not None:
                            ctr_fig.add_hline(
                                y=kpis["aggregate_ctr"] * 100.0,
                                line_dash="dash",
                                line_color="#0F172A",
                                annotation_text=f"Pooled CTR ({kpis['aggregate_ctr']*100:.2f}%)",
                            )
                        _apply_saas_chart_theme(ctr_fig, height=310)
                        st.plotly_chart(ctr_fig, use_container_width=True)
                    else:
                        st.info("CTR comparison unavailable (all records have 0 impressions).")

        with ch_row1_right:
            with st.container(border=True):
                st.markdown("**Conversion Comparison Across Creatives**")
                st.caption("Total conversions and post-click conversion efficiency across active creatives.")
                conv_plot_df = df.sort_values("conversions", ascending=False).head(18).copy()
                has_human_col = "human_presence_cat" in conv_plot_df.columns and conv_plot_df["human_presence_cat"].notna().any()
                conv_fig = px.bar(
                    conv_plot_df,
                    x="ad_id",
                    y="conversions",
                    color="human_presence_cat" if has_human_col else None,
                    labels={"ad_id": "Creative ID", "conversions": "Conversions", "human_presence_cat": "Face Presence"},
                    color_discrete_map={"With Human": "#10B981", "No Human": "#4F46E5"},
                )
                _apply_saas_chart_theme(conv_fig, height=310)
                st.plotly_chart(conv_fig, use_container_width=True)

        ch_row2_left, ch_row2_right = st.columns(2)

        with ch_row2_left:
            with st.container(border=True):
                st.markdown("**Spend vs. Conversions per Creative**")
                st.caption("Bubble size reflects impression volume; hover to inspect creative ID and efficiency.")
                has_tone = "dominant_color_tone" in df.columns and df["dominant_color_tone"].notna().any()
                scatter_fig = px.scatter(
                    df,
                    x="spend",
                    y="conversions",
                    size=df["impressions"].clip(lower=100) if "impressions" in df.columns else None,
                    color="dominant_color_tone" if has_tone else None,
                    hover_name="ad_id",
                    labels={"spend": "Spend ($)", "conversions": "Conversions", "dominant_color_tone": "Color Tone"},
                    color_discrete_map={"Warm": "#F97316", "Cool": "#4F46E5", "Neutral": "#64748B", "Unknown": "#CBD5E1"},
                )
                _apply_saas_chart_theme(scatter_fig, height=310)
                st.plotly_chart(scatter_fig, use_container_width=True)

        with ch_row2_right:
            with st.container(border=True):
                seg_candidates = [
                    c for c in ["campaign_name", "platform", "placement", "audience", "dominant_color_tone", "human_presence_cat", "composition_style"]
                    if c in df.columns and df[c].dropna().nunique() >= 2
                ]
                if seg_candidates:
                    chosen_seg = st.selectbox(
                        "Compare Performance Distribution By Segment",
                        seg_candidates,
                        format_func=lambda c: c.replace("_cat", "").replace("_", " ").title(),
                        key="overview_segment_dist_sel",
                    )
                    seg_label = chosen_seg.replace("_cat", "").replace("_", " ").title()
                    seg_grp = (
                        df.dropna(subset=[chosen_seg])
                        .groupby(chosen_seg, as_index=False)
                        .agg({"impressions": "sum", "clicks": "sum", "conversions": "sum", "spend": "sum", "ad_id": "count"})
                    )
                    seg_grp["Pooled CTR (%)"] = np.where(seg_grp["impressions"] > 0, seg_grp["clicks"] / seg_grp["impressions"] * 100.0, 0.0)
                    seg_grp["Pooled CVR (%)"] = np.where(seg_grp["clicks"] > 0, seg_grp["conversions"] / seg_grp["clicks"] * 100.0, 0.0)
                    seg_melt = seg_grp.melt(
                        id_vars=[chosen_seg],
                        value_vars=["Pooled CTR (%)", "Pooled CVR (%)"],
                        var_name="Metric",
                        value_name="Rate (%)",
                    )
                    seg_fig = px.bar(
                        seg_melt,
                        x=chosen_seg,
                        y="Rate (%)",
                        color="Metric",
                        barmode="group",
                        labels={chosen_seg: seg_label, "Rate (%)": "Pooled Rate (%)"},
                        color_discrete_map={"Pooled CTR (%)": "#4F46E5", "Pooled CVR (%)": "#10B981"},
                    )
                    _apply_saas_chart_theme(seg_fig, height=275)
                    st.plotly_chart(seg_fig, use_container_width=True)
                else:
                    st.markdown("**Aggregate Conversion Funnel**")
                    st.caption("Total campaign progression from impressions to clicks and conversions.")
                    funnel_fig = go.Figure(
                        go.Funnel(
                            y=["Impressions", "Clicks", "Conversions"],
                            x=[kpis["total_impressions"], kpis["total_clicks"], kpis["total_conversions"]],
                            textinfo="value+percent initial",
                            marker={"color": ["#4F46E5", "#6366F1", "#10B981"]},
                        )
                    )
                    _apply_saas_chart_theme(funnel_fig, height=310)
                    st.plotly_chart(funnel_fig, use_container_width=True)

        # -------------------------------------------------------------------
        # TOP-PERFORMING CREATIVES GALLERY SECTION
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Top-Performing Creatives</div>', unsafe_allow_html=True)
        top_ctrl_c1, top_ctrl_c2 = st.columns([1.6, 2.4])
        with top_ctrl_c1:
            overview_sort_opts = ["composite", "ctr", "conversions", "cvr", "cpa", "spend"] + (["roas"] if has_roas else [])
            overview_sort_labels = {
                "composite": "Composite Efficiency Score (Empirical Bayes Shrinkage)",
                "ctr": "CTR (Click-Through Rate — High to Low)",
                "conversions": "Conversions (Volume — High to Low)",
                "cvr": "CVR (Conversion Rate — High to Low)",
                "cpa": "CPA (Cost Per Acquisition — Low to High)",
                "spend": "Spend (Total Spend — High to Low)",
                "roas": "ROAS (Return on Ad Spend — High to Low)",
            }
            overview_rank_by = st.selectbox(
                "Sort Top Creatives By",
                overview_sort_opts,
                format_func=lambda m: overview_sort_labels.get(m, m.upper()),
                key="overview_top_creatives_sort",
            )
        with top_ctrl_c2:
            st.caption(
                "**Ranking Governance**: Single-creative rankings are observational. Creatives with zero denominators (e.g., 0 conversions for CPA) are excluded from ratio-specific sorting rather than fabricated. Composite ranking uses Empirical Bayes shrinkage toward the campaign mean to prevent low-impression outliers from outranking high-volume winners."
            )

        if overview_rank_by in ("conversions", "spend"):
            ranked_overview_df = rank_creatives(df, primary_metric="composite")
            ranked_overview_df = ranked_overview_df.sort_values(overview_rank_by, ascending=False, na_position="last").reset_index(drop=True)
            ranked_overview_df["rank"] = range(1, len(ranked_overview_df) + 1)
        else:
            ranked_overview_df = rank_creatives(df, primary_metric=overview_rank_by)

        top_cards_df = ranked_overview_df.head(4)
        if not top_cards_df.empty:
            lead_cols = st.columns(len(top_cards_df))
            for idx, (_, c_row) in enumerate(top_cards_df.iterrows()):
                cid = str(c_row["ad_id"])
                with lead_cols[idx]:
                    with st.container(border=True):
                        thumb = resolve_creative_image(cid, st.session_state.images_dict)
                        if thumb is not None:
                            st.image(thumb, use_container_width=True)
                        else:
                            st.markdown(
                                f"""
                                <div class="missing-image-placeholder">
                                    <div style="font-weight:600; font-size:0.84rem; color:#475569;">Missing Image</div>
                                    <div style="font-size:0.74rem; margin-top:2px;"><code>{cid}</code></div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        sig_vs_base = str(c_row.get("significance_vs_baseline", ""))
                        rel_tier = str(c_row.get("reliability_tier", "Moderate Exposure"))
                        if "Significant" in sig_vs_base and c_row.get("lift_vs_campaign_pct", 0) > 0:
                            perf_badge = _render_status_badge("Outperforming Baseline", "emerald")
                        elif "Underpowered" in sig_vs_base or "Low Volume" in rel_tier:
                            perf_badge = _render_status_badge("Low Volume", "amber")
                        else:
                            perf_badge = _render_status_badge("Baseline Range", "indigo")

                        roas_item_html = (
                            f'<div class="creative-kpi-item"><strong>ROAS:</strong> {_format_roas(c_row.get("roas"))}</div>'
                            if has_roas
                            else f'<div class="creative-kpi-item"><strong>Impr:</strong> {int(c_row.get("impressions", 0)):,}</div>'
                        )
                        st.markdown(
                            f"""
                            <div class="creative-card-header">
                                <span class="creative-id-label">#{int(c_row.get('rank', idx+1))} {cid}</span>
                                {perf_badge}
                            </div>
                            <div class="creative-kpi-grid">
                                <div class="creative-kpi-item"><strong>Spend:</strong> {_format_currency(c_row.get('spend'))}</div>
                                {roas_item_html}
                                <div class="creative-kpi-item"><strong>CTR:</strong> {_format_rate(c_row.get('ctr'))}</div>
                                <div class="creative-kpi-item"><strong>Conv:</strong> {int(c_row.get('conversions', 0)):,}</div>
                                <div class="creative-kpi-item"><strong>CPA:</strong> {_format_currency(c_row.get('cpa'))}</div>
                                <div class="creative-kpi-item"><strong>Score:</strong> {c_row.get('composite_rank_score', 0):.1f}/100</div>
                            </div>
                            <div style="font-size:0.73rem; color:#64748B; margin-bottom:6px;">
                                95% CTR CI: {c_row.get('ctr_ci_95', 'N/A')}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.button(
                            f"View Creative Detail ({cid})",
                            key=f"overview_nav_detail_{cid}",
                            on_click=select_creative_and_navigate,
                            args=(cid,),
                            use_container_width=True,
                        )

        # -------------------------------------------------------------------
        # SECTION 5.F: DATA QUALITY & LINEAGE AUDIT
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Dataset Quality, Coverage &amp; Lineage Summary</div>', unsafe_allow_html=True)
        dq = compute_data_quality_summary(df, st.session_state.ingestion_result, is_synthetic=st.session_state.is_synthetic)
        with st.container(border=True):
            dq_c1, dq_c2, dq_c3, dq_c4 = st.columns(4)
            dq_c1.metric("Distinct Creatives", f"{dq['creative_count']:,}", f"{dq['record_count']:,} performance records")
            dq_c2.metric("Matched Images", f"{dq['matched_image_count']} / {dq['creative_count']}", f"{dq['missing_image_count']} missing image(s)")
            dq_c3.metric("Date Coverage", f"{dq['distinct_dates']} day(s)" if dq["has_dates"] else "No Dates", dq["date_coverage_label"][:36])
            dq_c4.metric("Dataset Origin", "Synthetic Demo" if dq["is_synthetic"] else "Imported User Data", dq["dataset_origin"])

            present_opt_str = ", ".join(f"`{c}`" for c in dq["present_optional_fields"]) if dq["present_optional_fields"] else "None"
            missing_opt_str = ", ".join(f"`{c}`" for c in dq["missing_optional_fields"]) if dq["missing_optional_fields"] else "None (All optional fields present)"
            st.markdown(
                f"""
                - **Data Freshness & Coverage**: {dq['date_coverage_label']} — *{dq['data_freshness']}*
                - **Collected Optional Fields**: {present_opt_str}
                - **Uncollected / Missing Optional Fields** *(never fabricated)*: {missing_opt_str}
                - **Zero-Denominator Records**: `{dq['zero_impressions_count']}` with 0 impressions, `{dq['zero_clicks_count']}` with 0 clicks, `{dq['zero_conversions_count']}` with 0 conversions, `{dq['zero_spend_count']}` with $0 spend.
                """
            )


# ===========================================================================
# PAGE 2: UPLOAD CREATIVES
# ===========================================================================
elif nav_choice == "2. Upload Creatives":
    _render_page_header(
        "Data Import & Creative Asset Management",
        "Guided 7-step ingestion workflow: upload performance CSV, map columns if needed, match creative images, and audit data quality.",
    )

    # 7-Step Guided Upload Workflow
    st.markdown(
        """
        <div class="workflow-stepper" style="grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));">
            <div class="workflow-step">
                <div class="workflow-step-num">Step 1</div>
                <div class="workflow-step-title">Upload CSV</div>
                <div class="workflow-step-desc">Select campaign performance CSV file.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 2</div>
                <div class="workflow-step-title">Validate File</div>
                <div class="workflow-step-desc">Check numeric types, nulls, and bounds.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 3</div>
                <div class="workflow-step-title">Preview &amp; Map</div>
                <div class="workflow-step-desc">Preview rows and map custom headers.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 4</div>
                <div class="workflow-step-title">Upload Images</div>
                <div class="workflow-step-desc">Attach PNG, JPG, JPEG, WEBP, or ZIP.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 5</div>
                <div class="workflow-step-title">Match IDs</div>
                <div class="workflow-step-desc">Link image stems to CSV <code>ad_id</code>s.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 6</div>
                <div class="workflow-step-title">Review Audit</div>
                <div class="workflow-step-desc">Inspect warnings &amp; unmatched items.</div>
            </div>
            <div class="workflow-step">
                <div class="workflow-step-num">Step 7</div>
                <div class="workflow-step-title">Confirm Import</div>
                <div class="workflow-step-desc">Run CV &amp; statistical engine + save.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("CSV Schema Reference & Starter Templates", expanded=False):
        st.markdown(
            """
            **Required Columns (`REQUIRED_COLUMNS`)**:
            - `ad_id` *(string)*: Unique creative identifier (must match image filename stem, e.g., `ad_warm_01` $\\leftrightarrow$ `ad_warm_01.png`).
            - `spend` *(float $\\ge 0$)*: Total media spend in USD.
            - `impressions` *(integer/float $\\ge 0$)*: Total impressions delivered.
            - `clicks` *(integer/float $\\ge 0$)*: Total clicks recorded (must satisfy $\\text{clicks} \\le \\text{impressions}$).
            - `conversions` *(integer/float $\\ge 0$)*: Total conversions recorded (must satisfy $\\text{conversions} \\le \\text{clicks}$ unless View-Through Conversions are enabled).

            **Optional Columns (`OPTIONAL_COLUMNS`)**:
            - `campaign_id`, `campaign_name` (or `campaign`), `audience`, `placement`, `platform`, `date`, `variant` *(for segment & confounding checks)*.
            - `revenue`, `conversion_value` *(numeric $\\ge 0$, enables ad-level and pooled ROAS calculation)*.
            """
        )
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="Download Example CSV Template",
                data=generate_example_csv_content(),
                file_name="ad_creative_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dl_col2:
            st.download_button(
                label="Download Sample Images + CSV Bundle (.zip)",
                data=build_sample_upload_zip_bytes(),
                file_name="adcreative_sample_upload_bundle.zip",
                mime="application/zip",
                use_container_width=True,
            )

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        with st.container(border=True):
            st.markdown("#### STEP 1 & 2: Upload Performance CSV & Configure Validation")
            st.caption(f"Required fields: `{', '.join(REQUIRED_COLUMNS)}`")
            uploaded_csv = st.file_uploader(
                "1. Upload Ad Performance CSV (Required: ad_id, spend, impressions, clicks, conversions)",
                type=["csv"],
            )
            allow_vtc = st.checkbox(
                "Allow View-Through Conversions (permit conversions > clicks with warning)",
                value=False,
            )

    with u_col2:
        with st.container(border=True):
            st.markdown("#### STEP 4 & 5: Upload & Match Creative Images")
            st.caption(
                f"Supported formats: `PNG`, `JPG`, `JPEG`, `WEBP`, or `.ZIP` — Session cache: `{len(st.session_state.uploaded_image_store)}` file(s)"
            )
            uploaded_images = st.file_uploader(
                "2. Upload Creative Images (PNG, JPG, JPEG, WEBP, or ZIP — filename stem matched to ad_id)",
                type=["png", "jpg", "jpeg", "webp", "zip"],
                accept_multiple_files=True,
            )

    # Step 3: Interactive CSV Preview & Column Mapping when a CSV is selected
    user_column_map: Dict[str, str] = {}
    if uploaded_csv is not None:
        try:
            if hasattr(uploaded_csv, "seek"):
                uploaded_csv.seek(0)
            raw_preview_df = pd.read_csv(uploaded_csv)
            if hasattr(uploaded_csv, "seek"):
                uploaded_csv.seek(0)
        except Exception:
            raw_preview_df = pd.DataFrame()

        if not raw_preview_df.empty:
            raw_cols = [str(c) for c in raw_preview_df.columns]
            norm_cols = [c.strip().lower() for c in raw_cols]
            missing_std_req = [req for req in REQUIRED_COLUMNS if req not in norm_cols]
            with st.expander(
                f"STEP 3: Preview Uploaded CSV ({len(raw_preview_df)} rows) & Map Custom Column Names",
                expanded=bool(missing_std_req),
            ):
                st.dataframe(raw_preview_df.head(8), use_container_width=True, hide_index=True)
                suggestions = suggest_column_mapping(raw_cols)
                st.caption("If your CSV uses custom header names (e.g. `Cost` instead of `spend`), map them below before confirming import:")
                map_cols = st.columns(5)
                col_options = ["(None / Not Present)"] + raw_cols
                for idx, req_col in enumerate(REQUIRED_COLUMNS):
                    suggested = suggestions.get(req_col)
                    default_idx = col_options.index(suggested) if suggested in col_options else 0
                    chosen_src = map_cols[idx].selectbox(
                        f"Map `{req_col}` *",
                        col_options,
                        index=default_idx,
                        key=f"col_map_req_{req_col}",
                    )
                    if chosen_src != "(None / Not Present)":
                        user_column_map[req_col] = chosen_src

                opt_targets = ["campaign_name", "audience", "placement", "platform", "date", "revenue"]
                opt_map_cols = st.columns(6)
                for idx, opt_col in enumerate(opt_targets):
                    suggested_opt = suggestions.get(opt_col)
                    default_opt_idx = col_options.index(suggested_opt) if suggested_opt in col_options else 0
                    chosen_opt_src = opt_map_cols[idx].selectbox(
                        f"Map `{opt_col}`",
                        col_options,
                        index=default_opt_idx,
                        key=f"col_map_opt_{opt_col}",
                    )
                    if chosen_opt_src != "(None / Not Present)":
                        user_column_map[opt_col] = chosen_opt_src

    if uploaded_images:
        prev_store_keys = set(st.session_state.uploaded_image_store.keys())
        store_uploaded_images_in_session(uploaded_images)
        new_store_keys = set(st.session_state.uploaded_image_store.keys())
        if st.session_state.df_ads is not None and (
            new_store_keys != prev_store_keys
            or (st.session_state.ingestion_result and st.session_state.ingestion_result.unmatched_records)
        ):
            sync_active_dataset_with_image_store(st.session_state.uploaded_image_store)

        with st.expander(f"Preview Uploaded Image Files ({len(uploaded_images)} selected)", expanded=False):
            prev_cols = st.columns(min(len(uploaded_images), 6))
            for idx, img_file in enumerate(uploaded_images[:12]):
                with prev_cols[idx % len(prev_cols)]:
                    try:
                        fname = getattr(img_file, "name", f"image_{idx}")
                        if Path(fname).suffix.lower() == ".zip":
                            st.info(f"ZIP archive `{fname}` unpacked into session image store.")
                        else:
                            pil_preview = ensure_persistent_image(img_file)
                            if isinstance(pil_preview, Image.Image):
                                st.image(pil_preview, caption=f"{fname} ({pil_preview.width}x{pil_preview.height})", use_container_width=True)
                    except Exception as exc:
                        st.error(f"Corrupt image `{getattr(img_file, 'name', img_file)}`: {exc}")

    if uploaded_csv is not None:
        st.markdown("#### STEP 6 & 7: Validate & Confirm Import")
        persist_to_sqlite = st.checkbox(
            "Persist imported dataset and findings to local SQLite workspace (`adcreative_workspace.db`)",
            value=True,
            key="persist_sqlite_checkbox",
        )
        if st.button("Validate CSV, Match Images & Confirm Import", type="primary", use_container_width=True):
            with st.spinner("Validating CSV schema, checking logical ratios, and matching creative images..."):
                if uploaded_images:
                    st.session_state.uploaded_image_store = {}
                    store_uploaded_images_in_session(uploaded_images)
                images_input: Any = (
                    dict(st.session_state.uploaded_image_store)
                    if st.session_state.uploaded_image_store
                    else (uploaded_images if uploaded_images else [])
                )
                res = ingest_ad_dataset(
                    uploaded_csv,
                    images_input,
                    allow_view_through_conversions=allow_vtc,
                    column_mapping=user_column_map if user_column_map else None,
                )
                st.session_state.ingestion_result = res

                if not res.is_valid:
                    st.error("CSV Validation Failed — No records were silently discarded. Please correct the errors below:")
                    for e in res.errors:
                        st.markdown(f"- **{e}**")
                else:
                    st.success(f"CSV Validated Successfully: {len(res.df)} creative record(s) imported.")

                    if res.warnings:
                        st.warning("Validation & Matching Warnings:")
                        for w in res.warnings:
                            st.markdown(f"- {w}")

                    with st.spinner("Extracting computer vision features and running statistical comparisons..."):
                        feat_dict = batch_extract_features(res.matched_images)
                        feat_records = []
                        extraction_errors = []
                        for ad_id, f in feat_dict.items():
                            f_row = {"ad_id": ad_id, **f}
                            feat_records.append(f_row)
                            if f.get("extraction_status") == "error":
                                extraction_errors.append(f"{ad_id}: {f.get('extraction_error')}")

                        if extraction_errors:
                            st.error("Image Feature Extraction Errors:")
                            for err in extraction_errors:
                                st.markdown(f"- {err}")

                        f_df = pd.DataFrame(feat_records) if feat_records else pd.DataFrame(columns=["ad_id"])
                        merged_df = pd.merge(res.df, f_df, on="ad_id", how="left")
                        findings = run_full_statistical_analysis(merged_df)

                        st.session_state.df_ads = merged_df
                        st.session_state.images_dict = res.matched_images
                        st.session_state.features_df = f_df
                        st.session_state.findings = findings
                        st.session_state.is_synthetic = False
                        st.session_state.selected_library_ad_id = str(merged_df["ad_id"].iloc[0]) if not merged_df.empty else None
                        st.session_state.edited_brief_markdown = None

                        if persist_to_sqlite:
                            try:
                                storage = get_storage()
                                proj_id = st.session_state.get("active_project_id", "default_workspace")
                                storage.save_performance_df(proj_id, res.df, is_synthetic=False)
                                storage.save_extracted_features(proj_id, feat_dict)
                                storage.save_findings(proj_id, [f.to_dict() for f in findings])
                            except Exception:
                                pass

                    st.success(
                        f"Import Confirmed: Matched {len(res.matched_images)}/{len(res.df)} images and evaluated {len(findings)} statistical comparisons."
                    )

    if st.session_state.ingestion_result is not None:
        res = st.session_state.ingestion_result
        st.markdown('<div class="saas-section-header">STEP 6 &amp; 7: Import Summary &amp; Validation Audit</div>', unsafe_allow_html=True)

        # Compute Invalid records & Duplicate IDs counts from validation errors
        valid_count = len(res.df) if res.is_valid else 0
        invalid_count = len(res.errors) if not res.is_valid else 0
        dup_errors = [e for e in res.errors if "duplicate" in e.lower()]
        dup_count = len(dup_errors)

        status_badges_html = []
        if res.is_valid:
            status_badges_html.append(_render_status_badge("CSV Schema Valid", "emerald"))
        else:
            status_badges_html.append(_render_status_badge("CSV Validation Error", "red"))
        if res.is_valid and not res.unmatched_records:
            status_badges_html.append(_render_status_badge("100% Images Matched", "emerald"))
        elif res.unmatched_records:
            status_badges_html.append(_render_status_badge(f"{len(res.unmatched_records)} Missing Images", "amber"))
        if res.warnings:
            status_badges_html.append(_render_status_badge(f"{len(res.warnings)} Warning(s)", "amber"))

        st.markdown(" ".join(status_badges_html), unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        a1, a2, a3, a4, a5, a6 = st.columns(6)
        a1.metric("Valid Records", f"{valid_count}")
        a2.metric("Invalid Issues", f"{invalid_count}")
        a3.metric("Matched Images", f"{len(res.matched_images)}")
        a4.metric("Missing Images", f"{len(res.unmatched_records)}")
        a5.metric("Unmatched Files", f"{len(res.unmatched_images)}")
        a6.metric("Duplicate IDs", f"{dup_count}")

        if res.unmatched_records:
            uploaded_fnames = get_session_uploaded_filenames()
            uploaded_list_str = ", ".join(uploaded_fnames) if uploaded_fnames else "None (0 image files uploaded)"
            st.warning(
                f"**CSV Records Missing Image Files ({len(res.unmatched_records)})**: `{', '.join(res.unmatched_records)}`\n\n"
                f"**Uploaded Filenames in Session ({len(uploaded_fnames)})**: `{uploaded_list_str}`\n\n"
                "To resolve: Upload `.png`, `.jpg`, `.jpeg`, or `.webp` files whose filename stem matches each `ad_id`."
            )
            if getattr(res, "matching_diagnostics", None):
                with st.expander("View Detailed Ad ID to Image Filename Stem Matching Diagnostics", expanded=False):
                    st.dataframe(pd.DataFrame(res.matching_diagnostics), use_container_width=True, hide_index=True)

        if res.unmatched_images:
            st.warning(
                f"**Unmatched Image Files ({len(res.unmatched_images)})**: `{', '.join(res.unmatched_images)}` "
                "(These image files do not match any `ad_id` in the uploaded CSV)."
            )

        if not res.df.empty:
            st.markdown('<div class="saas-section-header">Imported Records &amp; Feature Extraction Preview</div>', unsafe_allow_html=True)
            audit_df = st.session_state.df_ads if st.session_state.df_ads is not None else res.df.copy()
            audit_cols = [c for c in ["ad_id", "spend", "impressions", "clicks", "conversions", "ctr", "cvr", "cpc", "cpa", "roas"] if c in audit_df.columns]
            for extra_c in ["campaign_name", "platform", "extraction_status", "dominant_color_tone", "human_presence_cat", "aspect_ratio_cat", "composition_style"]:
                if extra_c in audit_df.columns and extra_c not in audit_cols:
                    audit_cols.append(extra_c)
            st.dataframe(audit_df[audit_cols], use_container_width=True, hide_index=True)

            act1, act2 = st.columns(2)
            with act1:
                st.button("Inspect in Creative Library", on_click=navigate_to, args=("3. Creative Library",), use_container_width=True)
            with act2:
                st.button("View Ranked Findings", on_click=navigate_to, args=("4. Ranked Findings",), use_container_width=True)



# ===========================================================================
# PAGE 3: CREATIVE LIBRARY
# ===========================================================================
elif nav_choice == "3. Creative Library":
    _render_page_header(
        "Creative Library & Asset Inspector",
        "Browse creative thumbnails, switch between Visual Grid and Compact Table views, inspect the Empirical Bayes Creative Scorecard, and compare 2+ creatives side-by-side.",
    )

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <strong>DEMO DATA — SYNTHETIC EXAMPLE</strong>: Displaying extracted computer vision attributes and metrics from synthetic benchmark creatives.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.df_ads is None or st.session_state.df_ads.empty:
        st.markdown(
            """
            <div class="saas-empty-state">
                <h3 style="margin:0 0 6px 0; color:#0F172A;">No Creative Assets Loaded</h3>
                <p style="color:#475569; margin:0 auto 16px auto; max-width:560px;">
                    Load the 18-ad demonstration dataset or upload your campaign CSV and creative images in <strong>Upload Creatives</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        df = st.session_state.df_ads
        images_dict = st.session_state.images_dict
        uploaded_fnames = get_session_uploaded_filenames()
        uploaded_list_str = ", ".join(uploaded_fnames) if uploaded_fnames else "None (0 image files uploaded)"

        unmatched_ad_ids = [
            str(aid) for aid in df["ad_id"].astype(str).tolist()
            if resolve_creative_image(str(aid), images_dict) is None
        ]

        if unmatched_ad_ids:
            with st.expander(
                f"Missing Image Diagnostics: {len(unmatched_ad_ids)} of {len(df)} CSV Record(s) Missing Matching Images",
                expanded=True,
            ):
                st.warning(
                    f"**Missing Image Matches ({len(unmatched_ad_ids)})**: CSV `ad_id` values `{', '.join(unmatched_ad_ids)}` "
                    f"do not match any uploaded image filename stem (`.png`, `.jpg`, `.jpeg`, `.webp`).\n\n"
                    f"- **CSV `ad_id` values missing images**: `{', '.join(unmatched_ad_ids)}`\n"
                    f"- **Uploaded image filenames in session ({len(uploaded_fnames)})**: `{uploaded_list_str}`"
                )
                ing_res = st.session_state.get("ingestion_result")
                if ing_res is not None and getattr(ing_res, "matching_diagnostics", None):
                    st.dataframe(pd.DataFrame(ing_res.matching_diagnostics), use_container_width=True, hide_index=True)

                rec_col1, rec_col2 = st.columns([2, 1.2])
                with rec_col1:
                    supp_images = st.file_uploader(
                        "Upload Missing Creative Images Here (PNG, JPG, JPEG, WEBP, or ZIP — stem matched to ad_id)",
                        type=["png", "jpg", "jpeg", "webp", "zip"],
                        accept_multiple_files=True,
                        key="creative_lib_supplementary_uploader",
                    )
                    if supp_images:
                        store_uploaded_images_in_session(supp_images)
                        if sync_active_dataset_with_image_store(st.session_state.uploaded_image_store):
                            st.rerun()
                with rec_col2:
                    _, demo_img_dir = get_synthetic_dataset_paths()
                    available_demo_matches = [
                        p for p in sorted(demo_img_dir.glob("*.png"))
                        if any(
                            set(normalize_identifier_candidates(p.name)) & set(normalize_identifier_candidates(uid))
                            for uid in unmatched_ad_ids
                        )
                    ]
                    if available_demo_matches:
                        st.caption(
                            f"Found **{len(available_demo_matches)}** matching demo image(s) on disk "
                            f"(e.g. `{available_demo_matches[0].name}`) for your CSV `ad_id`s."
                        )
                        if st.button("Attach Matching Demo Images", use_container_width=True):
                            for p in available_demo_matches:
                                st.session_state.uploaded_image_store[p.name] = ensure_persistent_image(p)
                            sync_active_dataset_with_image_store(st.session_state.uploaded_image_store)
                            st.rerun()

        # -------------------------------------------------------------------
        # SEARCH, FILTER, VIEW MODE & SORT CONTROLS
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Search, Filter &amp; Sort Creative Inventory</div>', unsafe_allow_html=True)

        def _reset_library_filters() -> None:
            for k in (
                "lib_search_ad_id", "lib_sort_by", "lib_tone_filter",
                "lib_human_filter", "lib_aspect_filter", "lib_comp_filter",
                "lib_camp_filter", "lib_plat_filter", "lib_place_filter", "lib_aud_filter",
            ):
                if k in st.session_state:
                    del st.session_state[k]

        with st.container(border=True):
            top_ctrl1, top_ctrl2, top_ctrl3, top_ctrl4 = st.columns([1.6, 1.3, 1.1, 0.7])
            with top_ctrl1:
                search_query = st.text_input(
                    "Search by Creative ID",
                    value="",
                    placeholder="Type ad_id substring (e.g. ad_warm_01)...",
                    key="lib_search_ad_id",
                )
            with top_ctrl2:
                sort_options = [
                    "Default Order",
                    "CTR (High → Low)",
                    "Conversions (High → Low)",
                    "CPA (Low → High)",
                    "Spend (High → Low)",
                    "CVR (High → Low)",
                    "ROAS (High → Low)",
                    "Brightness (High → Low)",
                ]
                sort_by = st.selectbox("Sort Gallery By", sort_options, key="lib_sort_by")
            with top_ctrl3:
                view_mode = st.radio(
                    "Display Mode",
                    ["Visual Grid View", "Compact Table View"],
                    horizontal=True,
                    key="lib_view_mode_radio",
                )
            with top_ctrl4:
                st.write("")
                st.button("Clear Filters", on_click=_reset_library_filters, use_container_width=True)

            # Metadata filters: Campaign, Platform, Placement, Audience
            meta_cols = st.columns(4)
            camp_opts = ["All"] + sorted([str(x) for x in df["campaign_name"].dropna().unique()]) if "campaign_name" in df.columns else ["All"]
            plat_opts = ["All"] + sorted([str(x) for x in df["platform"].dropna().unique()]) if "platform" in df.columns else ["All"]
            place_opts = ["All"] + sorted([str(x) for x in df["placement"].dropna().unique()]) if "placement" in df.columns else ["All"]
            aud_opts = ["All"] + sorted([str(x) for x in df["audience"].dropna().unique()]) if "audience" in df.columns else ["All"]

            campaign_filter = meta_cols[0].selectbox("Campaign Filter", camp_opts, key="lib_camp_filter")
            platform_filter = meta_cols[1].selectbox("Platform Filter", plat_opts, key="lib_plat_filter")
            placement_filter = meta_cols[2].selectbox("Placement Filter", place_opts, key="lib_place_filter")
            audience_filter = meta_cols[3].selectbox("Audience Filter", aud_opts, key="lib_aud_filter")

            # Visual feature filters
            f_cols = st.columns(4)
            tones = ["All"] + sorted([str(x) for x in df["dominant_color_tone"].dropna().unique()]) if "dominant_color_tone" in df.columns else ["All"]
            humans = ["All"] + sorted([str(x) for x in df["human_presence_cat"].dropna().unique()]) if "human_presence_cat" in df.columns else ["All"]
            aspects = ["All"] + sorted([str(x) for x in df["aspect_ratio_cat"].dropna().unique()]) if "aspect_ratio_cat" in df.columns else ["All"]
            comps = ["All"] + sorted([str(x) for x in df["composition_style"].dropna().unique()]) if "composition_style" in df.columns else ["All"]

            tone_filter = f_cols[0].selectbox("Color Tone", tones, key="lib_tone_filter")
            human_filter = f_cols[1].selectbox("Human Presence", humans, key="lib_human_filter")
            aspect_filter = f_cols[2].selectbox("Aspect Ratio", aspects, key="lib_aspect_filter")
            comp_filter = f_cols[3].selectbox("Composition Style", comps, key="lib_comp_filter")

        filtered_df = df.copy()
        if search_query.strip():
            q_str = search_query.strip().lower()
            filtered_df = filtered_df[filtered_df["ad_id"].astype(str).str.lower().str.contains(q_str, na=False)]
        if campaign_filter != "All" and "campaign_name" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["campaign_name"].astype(str) == campaign_filter]
        if platform_filter != "All" and "platform" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["platform"].astype(str) == platform_filter]
        if placement_filter != "All" and "placement" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["placement"].astype(str) == placement_filter]
        if audience_filter != "All" and "audience" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["audience"].astype(str) == audience_filter]
        if tone_filter != "All" and "dominant_color_tone" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["dominant_color_tone"] == tone_filter]
        if human_filter != "All" and "human_presence_cat" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["human_presence_cat"] == human_filter]
        if aspect_filter != "All" and "aspect_ratio_cat" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["aspect_ratio_cat"] == aspect_filter]
        if comp_filter != "All" and "composition_style" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["composition_style"] == comp_filter]

        if sort_by == "CTR (High → Low)" and "ctr" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("ctr", ascending=False, na_position="last")
        elif sort_by == "Conversions (High → Low)" and "conversions" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("conversions", ascending=False, na_position="last")
        elif sort_by == "CPA (Low → High)" and "cpa" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("cpa", ascending=True, na_position="last")
        elif sort_by == "Spend (High → Low)" and "spend" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("spend", ascending=False, na_position="last")
        elif sort_by == "CVR (High → Low)" and "cvr" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("cvr", ascending=False, na_position="last")
        elif sort_by == "ROAS (High → Low)" and "roas" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("roas", ascending=False, na_position="last")
        elif sort_by == "Brightness (High → Low)" and "brightness_score" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("brightness_score", ascending=False, na_position="last")

        st.caption(
            f"Showing **{len(filtered_df)}** of **{len(df)}** creative record(s) — Matched Images: **{len(df) - len(unmatched_ad_ids)}/{len(df)}** — Mode: **{view_mode}**"
        )

        # -------------------------------------------------------------------
        # CREATIVE GALLERY: VISUAL GRID VIEW OR COMPACT TABLE VIEW
        # -------------------------------------------------------------------
        if filtered_df.empty:
            st.warning("No creatives match the current search or filter criteria. Click 'Clear Filters' above to reset.")
        elif view_mode == "Compact Table View":
            compact_rows = []
            has_roas_col = "roas" in filtered_df.columns and filtered_df["roas"].notna().any()
            for _, ad in filtered_df.iterrows():
                aid = str(ad["ad_id"])
                matched_img = resolve_creative_image(aid, images_dict)
                row_entry = {
                    "Creative ID": aid,
                    "Image Status": "Matched" if matched_img is not None else "Missing Image",
                    "Campaign": str(ad.get("campaign_name", "—")) if pd.notna(ad.get("campaign_name")) else "—",
                    "Platform": str(ad.get("platform", "—")) if pd.notna(ad.get("platform")) else "—",
                    "Placement": str(ad.get("placement", "—")) if pd.notna(ad.get("placement")) else "—",
                    "Audience": str(ad.get("audience", "—")) if pd.notna(ad.get("audience")) else "—",
                    "Spend": _format_currency(ad.get("spend")),
                    "Impressions": f"{int(ad.get('impressions', 0)):,}",
                    "Clicks": f"{int(ad.get('clicks', 0)):,}",
                    "CTR": _format_rate(ad.get("ctr")),
                    "Conversions": f"{int(ad.get('conversions', 0)):,}",
                    "CVR": _format_rate(ad.get("cvr")),
                    "CPC": _format_currency(ad.get("cpc")),
                    "CPA": _format_currency(ad.get("cpa")),
                    "Color Tone": str(ad.get("dominant_color_tone", "Unavailable")) if pd.notna(ad.get("dominant_color_tone")) else "Unavailable",
                    "Human Presence": str(ad.get("human_presence_cat", "Unavailable")) if pd.notna(ad.get("human_presence_cat")) else "Unavailable",
                }
                if has_roas_col:
                    r_val = ad.get("roas")
                    row_entry["ROAS"] = f"{float(r_val):.2f}x" if (pd.notna(r_val) and np.isfinite(r_val)) else "Unavailable"
                compact_rows.append(row_entry)
            st.dataframe(pd.DataFrame(compact_rows), use_container_width=True, hide_index=True)
        else:
            cols_per_row = 3
            rows = [filtered_df.iloc[i : i + cols_per_row] for i in range(0, len(filtered_df), cols_per_row)]

            for row in rows:
                grid_cols = st.columns(cols_per_row)
                for idx, (_, ad) in enumerate(row.iterrows()):
                    ad_id = str(ad["ad_id"])
                    with grid_cols[idx]:
                        with st.container(border=True):
                            matched_img = resolve_creative_image(ad_id, images_dict)
                            if matched_img is not None:
                                st.image(matched_img, use_container_width=True)
                            else:
                                st.markdown(
                                    f"""
                                    <div class="missing-image-placeholder">
                                        <div style="font-weight:700; font-size:0.88rem; color:#475569;">Missing Image</div>
                                        <div style="font-size:0.75rem; margin-top:2px;">Expected: <code>{ad_id}.png/.jpg/.jpeg/.webp</code></div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                st.warning(f"Missing Image (`{ad_id}`)")
                                st.caption(
                                    f"**Diagnostic**: CSV `ad_id` = `{ad_id}` | Uploaded filenames: `{uploaded_list_str}`"
                                )

                            ext_status = ad.get("extraction_status", "unmatched")
                            if matched_img is not None and (pd.isna(ext_status) or ext_status == "unmatched"):
                                status_badge = _render_status_badge("Matched Image", "emerald")
                            elif ext_status == "success":
                                status_badge = _render_status_badge("Extracted", "emerald")
                            elif ext_status == "error":
                                status_badge = _render_status_badge(f"Error: {ad.get('extraction_error')}", "red")
                            else:
                                status_badge = _render_status_badge("Missing Image", "amber")

                            st.markdown(
                                f"""
                                <div class="creative-card-header">
                                    <span class="creative-id-label">{ad_id}</span>
                                    {status_badge}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            meta_badges: List[str] = []
                            for m_col in ("campaign_name", "platform", "placement"):
                                if m_col in ad and pd.notna(ad[m_col]) and str(ad[m_col]) not in ("", "Unknown"):
                                    meta_badges.append(
                                        f'<span style="background:#F1F5F9; color:#334155; padding:2px 7px; border-radius:6px; font-weight:600;">{ad[m_col]}</span>'
                                    )

                            hex_c = ad.get("dominant_color_hex", "#94A3B8")
                            if pd.isna(hex_c) or not str(hex_c).startswith("#"):
                                hex_c = "#94A3B8"
                            color_name = ad.get("dominant_color_name", "N/A") if pd.notna(ad.get("dominant_color_name")) else "N/A"
                            tone = ad.get("dominant_color_tone", "N/A") if pd.notna(ad.get("dominant_color_tone")) else "N/A"
                            human = ad.get("human_presence_cat", "N/A") if pd.notna(ad.get("human_presence_cat")) else "N/A"
                            aspect = ad.get("aspect_ratio_cat", "N/A") if pd.notna(ad.get("aspect_ratio_cat")) else "N/A"

                            st.markdown(
                                f"""
                                <div style="font-size:0.78rem; color:#475569; margin-bottom:6px; display:flex; align-items:center; flex-wrap:wrap; gap:5px;">
                                    {''.join(meta_badges)}
                                    <span style="display:inline-flex; align-items:center; gap:4px; background:#F8FAFC; border:1px solid #E2E8F0; padding:2px 7px; border-radius:6px;">
                                        <span style="display:inline-block; width:9px; height:9px; background-color:{hex_c}; border-radius:50%; border:1px solid #CBD5E1;"></span>
                                        <strong>{color_name}</strong> ({tone})
                                    </span>
                                    <span style="background:#EEF2FF; color:#3730A3; padding:2px 7px; border-radius:6px; font-weight:500;">{human}</span>
                                    <span style="background:#F8FAFC; border:1px solid #E2E8F0; padding:2px 7px; border-radius:6px;">{aspect}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            ctr_txt = _format_rate(ad.get("ctr"))
                            cvr_txt = _format_rate(ad.get("cvr"))
                            cpc_txt = _format_currency(ad.get("cpc"))
                            cpa_txt = _format_currency(ad.get("cpa"))
                            spend_txt = _format_currency(ad.get("spend"))
                            imp_val = ad.get("impressions", 0)
                            imp_txt = f"{int(imp_val):,}" if pd.notna(imp_val) else "0"
                            roas_val = ad.get("roas")
                            roas_line = f" &bull; ROAS: <strong>{float(roas_val):.2f}x</strong>" if (pd.notna(roas_val) and np.isfinite(roas_val)) else ""

                            st.markdown(
                                f"""
                                <div class="creative-kpi-grid">
                                    <div class="creative-kpi-item"><strong>Spend:</strong> {spend_txt}</div>
                                    <div class="creative-kpi-item"><strong>CTR:</strong> {ctr_txt}</div>
                                    <div class="creative-kpi-item"><strong>Conv:</strong> {int(ad.get('conversions', 0)):,} ({cvr_txt})</div>
                                    <div class="creative-kpi-item"><strong>CPA:</strong> {cpa_txt}</div>
                                </div>
                                <div style="font-size:0.74rem; color:#64748B; margin-bottom:6px; font-variant-numeric:tabular-nums;">
                                    Impressions: <strong>{imp_txt}</strong> &bull; Clicks: <strong>{int(ad.get('clicks', 0)):,}</strong> &bull; CPC: <strong>{cpc_txt}</strong>{roas_line}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            st.button(
                                f"Inspect Details ({ad_id})",
                                key=f"btn_detail_{ad_id}",
                                on_click=select_creative_for_detail,
                                args=(ad_id,),
                                use_container_width=True,
                            )

        # -------------------------------------------------------------------
        # CREATIVE DETAIL VIEW (Connected to Selected Creative ID)
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Creative Detail Inspector</div>', unsafe_allow_html=True)
        all_ad_ids = df["ad_id"].astype(str).tolist()
        default_detail_idx = 0
        if st.session_state.selected_library_ad_id in all_ad_ids:
            default_detail_idx = all_ad_ids.index(st.session_state.selected_library_ad_id)

        selected_detail_id = st.selectbox(
            "Select Creative ID to Inspect Full Details, Extracted Features, Historical Trends & Findings",
            all_ad_ids,
            index=default_detail_idx,
            key="detail_inspector_ad_selectbox",
        )
        st.session_state.selected_library_ad_id = selected_detail_id

        ranked_all = rank_creatives(df, primary_metric="composite")
        detail_row = (
            ranked_all[ranked_all["ad_id"].astype(str) == selected_detail_id].iloc[0]
            if not ranked_all.empty
            else df[df["ad_id"].astype(str) == selected_detail_id].iloc[0]
        )

        with st.container(border=True):
            det_col_img, det_col_info = st.columns([1.15, 1.85])
            with det_col_img:
                st.markdown(f"#### Creative `{selected_detail_id}`")
                det_img = resolve_creative_image(selected_detail_id, images_dict)
                if det_img is not None:
                    st.image(det_img, use_container_width=True)
                else:
                    st.markdown(
                        f"""
                        <div class="missing-image-placeholder">
                            <div style="font-weight:700; font-size:0.9rem;">Missing Image for <code>{selected_detail_id}</code></div>
                            <div style="font-size:0.78rem; margin-top:4px;">Upload <code>{selected_detail_id}.png/.jpg/.jpeg/.webp</code> in Upload Creatives</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Available Metadata
                meta_items = []
                for m_lbl, m_col in [("Campaign", "campaign_name"), ("Platform", "platform"), ("Placement", "placement"), ("Audience", "audience")]:
                    if m_col in detail_row and pd.notna(detail_row[m_col]) and str(detail_row[m_col]).strip() not in ("", "Unknown"):
                        meta_items.append(f"**{m_lbl}**: `{detail_row[m_col]}`")
                if meta_items:
                    st.markdown(" &bull; ".join(meta_items))

                palette = detail_row.get("color_palette_distribution")
                if isinstance(palette, list) and palette:
                    st.markdown("**Dominant RGB K-Means Color Palette**")
                    swatches_html = []
                    for p in palette:
                        swatches_html.append(
                            f'<span style="display:inline-flex; align-items:center; gap:5px; background:#F8FAFC; border:1px solid #E2E8F0; padding:3px 8px; border-radius:6px; font-size:0.76rem; margin-right:5px;">'
                            f'<span style="width:11px; height:11px; border-radius:3px; background:{p.get("hex_code", "#ccc")}; display:inline-block; border:1px solid #CBD5E1;"></span>'
                            f'{p.get("color_name", "")} ({p.get("percentage", 0)}%)</span>'
                        )
                    st.markdown("".join(swatches_html), unsafe_allow_html=True)

            with det_col_info:
                st.markdown("#### Performance Metrics & Statistical Reliability")
                dm1, dm2, dm3, dm4 = st.columns(4)
                dm1.metric("Spend", _format_currency(detail_row.get("spend")))
                dm2.metric("Impressions", f"{int(detail_row.get('impressions', 0)):,}")
                dm3.metric("Clicks", f"{int(detail_row.get('clicks', 0)):,}")
                dm4.metric("Conversions", f"{int(detail_row.get('conversions', 0)):,}")

                has_roas_detail = "roas" in detail_row and pd.notna(detail_row.get("roas")) and np.isfinite(detail_row.get("roas"))
                if has_roas_detail:
                    dm5, dm6, dm7, dm8, dm9 = st.columns(5)
                    dm5.metric("CTR", _format_rate(detail_row.get("ctr")))
                    dm6.metric("CVR", _format_rate(detail_row.get("cvr")))
                    dm7.metric("CPC", _format_currency(detail_row.get("cpc")))
                    dm8.metric("CPA", _format_currency(detail_row.get("cpa")))
                    dm9.metric("ROAS", f"{float(detail_row['roas']):.2f}x")
                else:
                    dm5, dm6, dm7, dm8 = st.columns(4)
                    dm5.metric("CTR", _format_rate(detail_row.get("ctr")))
                    dm6.metric("CVR", _format_rate(detail_row.get("cvr")))
                    dm7.metric("CPC", _format_currency(detail_row.get("cpc")))
                    dm8.metric("CPA", _format_currency(detail_row.get("cpa")))

                st.caption(
                    f"**95% Wilson CTR CI**: `{detail_row.get('ctr_ci_95', 'N/A')}` | "
                    f"**95% Wilson CVR CI**: `{detail_row.get('cvr_ci_95', 'N/A')}` | "
                    f"**Reliability Tier**: `{detail_row.get('reliability_tier', 'N/A')}` | "
                    f"**Composite Score**: `{detail_row.get('composite_rank_score', 0):.1f}/100` "
                    f"({detail_row.get('significance_vs_baseline', '')})"
                )

                st.markdown("#### Extracted Visual Features (Direct vs. Heuristic Proxies)")
                feat_summary_rows = [
                    {"Feature": "Dimensions & Aspect Ratio", "Value": f"{detail_row.get('width', 'Unavailable')}×{detail_row.get('height', 'Unavailable')} px ({detail_row.get('aspect_ratio_cat', 'Unavailable')})", "Provenance": "Direct Pixel Geometry"},
                    {"Feature": "Dominant Color Tone", "Value": f"{detail_row.get('dominant_color_name', 'Unavailable')} ({detail_row.get('dominant_color_hex', 'Unavailable')} — {detail_row.get('dominant_color_tone', 'Unavailable')})", "Provenance": "Direct HSV Hue/Sat + K-Means"},
                    {"Feature": "Luminance & Contrast", "Value": f"Brightness: {detail_row.get('brightness_score', 'Unavailable')} ({detail_row.get('brightness_cat', 'Unavailable')}) | Contrast: {detail_row.get('contrast_score', 'Unavailable')} ({detail_row.get('contrast_cat', 'Unavailable')})", "Provenance": "Direct ITU-R BT.601"},
                    {"Feature": "Visual Composition & Saliency", "Value": f"{detail_row.get('composition_style', 'Unavailable')} (Center Focus: {detail_row.get('center_focus_ratio', 'Unavailable')}%, Symmetry: {detail_row.get('visual_symmetry_score', 'Unavailable')}%)", "Provenance": "Heuristic Sobel / Otsu Proxy"},
                    {"Feature": "Edge Complexity & Copy Proxy", "Value": f"{detail_row.get('visual_complexity', 'Unavailable')} ({detail_row.get('edge_density_pct', 'Unavailable')}% edges) | {detail_row.get('text_density_cat', 'Unavailable')} ({detail_row.get('text_density_score', 'Unavailable')}% area)", "Provenance": "Heuristic Canny / Stroke Filter"},
                    {"Feature": "Frontal Face Detection", "Value": f"{detail_row.get('human_presence_cat', 'Unavailable')} ({detail_row.get('face_count', 0)} face(s), Area ratio: {detail_row.get('face_area_ratio', 0.0)})", "Provenance": "OpenCV Haar Frontal Face Cascade"},
                ]
                st.dataframe(pd.DataFrame(feat_summary_rows), use_container_width=True, hide_index=True)

            # Historical trend for this specific creative when date rows exist in raw_df
            ing_res_detail = st.session_state.get("ingestion_result")
            if ing_res_detail is not None and getattr(ing_res_detail, "raw_df", None) is not None and not ing_res_detail.raw_df.empty:
                raw_sub = ing_res_detail.raw_df[ing_res_detail.raw_df["ad_id"].astype(str) == selected_detail_id].copy()
                if "date" in raw_sub.columns and raw_sub["date"].notna().sum() >= 2:
                    raw_sub["_dt"] = pd.to_datetime(raw_sub["date"], errors="coerce")
                    raw_sub = raw_sub.dropna(subset=["_dt"]).sort_values("_dt")
                    if len(raw_sub) >= 2:
                        st.markdown(f"#### Historical Performance Trend for `{selected_detail_id}`")
                        raw_sub["ctr_pct"] = np.where(raw_sub["impressions"] > 0, (raw_sub["clicks"] / raw_sub["impressions"]) * 100.0, np.nan)
                        hist_fig = px.line(
                            raw_sub,
                            x="_dt",
                            y=["spend", "conversions"],
                            markers=True,
                            labels={"_dt": "Date", "value": "Value", "variable": "Metric"},
                        )
                        _apply_saas_chart_theme(hist_fig, height=220)
                        st.plotly_chart(hist_fig, use_container_width=True)

            # Relevant Statistical Findings & Related Recommendations for selected_detail_id
            rel_findings: List[Finding] = []
            for f in st.session_state.findings:
                if isinstance(f.traceable_ad_ids, dict):
                    for grp_ads in f.traceable_ad_ids.values():
                        if isinstance(grp_ads, list) and selected_detail_id in [str(x) for x in grp_ads]:
                            rel_findings.append(f)
                            break

            det_f_col, det_r_col = st.columns(2)
            with det_f_col:
                st.markdown(f"#### Relevant Statistical Findings for `{selected_detail_id}`")
                if rel_findings:
                    for rf in rel_findings[:4]:
                        b_lbl, _, _ = _get_finding_badge_info(rf.evidence_classification)
                        st.markdown(
                            f"- **[{b_lbl}] {rf.attribute} &rarr; {rf.outcome_metric}**: {rf.direction_of_association} "
                            f"(95% CI `[{rf.uncertainty.get('ci_95_lower', 0):.4f}, {rf.uncertainty.get('ci_95_upper', 0):.4f}]`, "
                            f"FDR q=`{rf.uncertainty.get('fdr_q_value', 1):.4f}`)"
                        )
                else:
                    st.caption("No cohort statistical findings directly reference this creative ID.")

            with det_r_col:
                st.markdown(f"#### Related Recommendations for `{selected_detail_id}`")
                if rel_findings:
                    recs_for_ad = generate_recommendations(rel_findings[:4], df_metrics=df)
                    combined_recs = (
                        recs_for_ad.get("category_a_observed_evidence", [])
                        + recs_for_ad.get("category_b_hypotheses_to_test", [])
                        + recs_for_ad.get("category_c_blocked_insufficient_evidence", [])
                    )
                    for rc in combined_recs[:3]:
                        st.markdown(
                            f"- **{rc['proposed_creative_variation']}** ({rc['outcome_metric']}): {rc['hypothesis']} "
                            f"*Plan*: {rc['measurement_plan']}"
                        )
                else:
                    st.caption("Upload matching creative images and run statistical analysis to generate linked recommendations.")

        # -------------------------------------------------------------------
        # SECTION 11: CREATIVE SCORECARD & EMPIRICAL BAYES RANKING
        # -------------------------------------------------------------------
        with st.expander("Creative Scorecard & Empirical Bayes Relative Performance View (Section 11)", expanded=False):
            rank_options = ["composite", "ctr", "cvr", "cpc", "cpa"] + (["roas"] if "roas" in df.columns and df["roas"].notna().any() else [])
            rank_labels = {
                "composite": "Composite Efficiency Score (Empirical Bayes Shrinkage, 0–100)",
                "ctr": "CTR (Higher is better)",
                "cvr": "CVR (Higher is better)",
                "cpc": "CPC (Lower is better)",
                "cpa": "CPA (Lower is better)",
                "roas": "ROAS (Higher is better)",
            }
            perf_metric_col = st.selectbox(
                "Rank Creatives By Metric",
                rank_options,
                format_func=lambda m: rank_labels.get(m, m.upper()),
                key="top_bottom_metric_sel",
            )
            scorecard_data = build_creative_scorecard(df, primary_metric=perf_metric_col)
            st.info(
                f"**Documented Scoring Methodology**: {scorecard_data.get('formula_documentation', '')}\n\n"
                f"**Limitations**: {scorecard_data.get('limitations', '')}"
            )
            for cw in scorecard_data.get("comparison_group_warnings", []):
                st.warning(f"**Comparison Context Warning**: {cw}")

            ranked_creatives_df = scorecard_data.get("scorecard_df", pd.DataFrame())
            if not ranked_creatives_df.empty:
                tb_c1, tb_c2 = st.columns(2)
                disp_cols = [
                    c for c in [
                        "rank", "ad_id", "composite_rank_score", "reliability_tier",
                        "spend", "impressions", "clicks", "conversions",
                        "ctr", "ctr_ci_95", "cvr", "cvr_ci_95", "cpc", "cpa", "roas",
                        "vs_campaign_fdr_q", "significance_vs_baseline",
                    ]
                    if c in ranked_creatives_df.columns
                ]
                with tb_c1:
                    st.markdown("**Top 5 Performing Creatives**")
                    st.dataframe(ranked_creatives_df.head(5)[disp_cols], use_container_width=True, hide_index=True)
                with tb_c2:
                    st.markdown("**Bottom 5 Performing Creatives**")
                    st.dataframe(ranked_creatives_df.tail(5).iloc[::-1][disp_cols], use_container_width=True, hide_index=True)

                st.markdown("**Full Creative Scorecard Table**")
                st.dataframe(ranked_creatives_df[disp_cols], use_container_width=True, hide_index=True)

        # -------------------------------------------------------------------
        # SECTION 12: MULTI-CREATIVE SIDE-BY-SIDE COMPARISON (2+ CREATIVES)
        # -------------------------------------------------------------------
        if len(df) >= 2:
            with st.expander("Multi-Creative Side-by-Side Comparison & Pairwise Statistical Tests (Section 12)", expanded=False):
                ad_id_list = df["ad_id"].astype(str).tolist()
                default_multi = ad_id_list[: min(3, len(ad_id_list))]
                selected_cmp_ids = st.multiselect(
                    "Select 2 or More Creatives to Compare Side-by-Side (First selected creative is used as Reference Baseline)",
                    options=ad_id_list,
                    default=default_multi,
                    key="multi_creative_cmp_selector",
                )

                if len(selected_cmp_ids) < 2:
                    st.info("Select at least 2 creatives above to compare metrics, visual features, and statistical differences.")
                else:
                    multi_cmp = compare_multiple_creatives(df, selected_cmp_ids)
                    ref_id = multi_cmp.get("reference_ad_id", selected_cmp_ids[0])

                    for w_msg in multi_cmp.get("comparison_group_warnings", []) + multi_cmp.get("sample_size_warnings", []):
                        st.warning(f"**Comparison Advisory**: {w_msg}")

                    # Display thumbnails side-by-side (up to 4 per row)
                    thumb_cols = st.columns(min(4, len(selected_cmp_ids)))
                    for idx_c, cid in enumerate(selected_cmp_ids):
                        with thumb_cols[idx_c % len(thumb_cols)]:
                            role_tag = " (Reference Baseline)" if cid == ref_id else ""
                            st.markdown(f"**`{cid}`{role_tag}**")
                            resolved_c = resolve_creative_image(cid, images_dict)
                            if resolved_c is not None:
                                st.image(resolved_c, use_container_width=True)
                            else:
                                st.warning(f"Missing Image (`{cid}`)")

                    st.markdown(f"##### Side-by-Side Performance & Visual Attributes (Baseline: `{ref_id}`)")
                    cmp_table = multi_cmp.get("comparison_table", pd.DataFrame())
                    if not cmp_table.empty:
                        st.dataframe(cmp_table, use_container_width=True, hide_index=True)

                    pw_tests = multi_cmp.get("pairwise_tests", [])
                    if pw_tests:
                        st.markdown(f"##### Pairwise Statistical Tests vs. Reference Creative (`{ref_id}`)")
                        stat_cmp_rows = []
                        for m_res in pw_tests:
                            p_val = m_res.get("p_value")
                            ci_l = m_res.get("ci_95_lower")
                            ci_u = m_res.get("ci_95_upper")
                            uplift = m_res.get("relative_uplift_pct")
                            stat_cmp_rows.append({
                                "Comparison": f"{m_res.get('reference_ad_id', ref_id)} vs. {m_res.get('challenger_ad_id', '')}",
                                "Metric": m_res.get("metric", ""),
                                "Method": m_res.get("statistical_method", ""),
                                "Relative Diff (Ref vs Challenger)": f"{uplift:+.1f}%" if uplift is not None else "N/A",
                                "95% CI": f"[{ci_l:+.4f}, {ci_u:+.4f}]" if (ci_l is not None and ci_u is not None) else "Descriptive Only (N=1 ad/side)",
                                "Two-Sided p-value": f"{p_val:.4f}" if p_val is not None else "N/A",
                                "Verdict": m_res.get("verdict", ""),
                            })
                        st.dataframe(pd.DataFrame(stat_cmp_rows), use_container_width=True, hide_index=True)
                        st.caption(f"*{pw_tests[0].get('limitations', '')}*")


# ===========================================================================
# PAGE 4: RANKED FINDINGS
# ===========================================================================
elif nav_choice == "4. Ranked Findings":
    _render_page_header(
        "Ranked Statistical Findings & Evidence Workspace",
        "Evaluate visual and campaign attribute hypotheses with Benjamini-Hochberg FDR correction, 95% confidence intervals, plain-English explanations, and practical significance.",
    )

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <strong>DEMO DATA — SYNTHETIC EXAMPLE</strong>: Statistical findings below are computed live on the 18-ad synthetic demonstration dataset.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not st.session_state.findings:
        st.markdown(
            """
            <div class="saas-empty-state">
                <h3 style="margin:0 0 6px 0; color:#0F172A;">No Statistical Findings Available</h3>
                <p style="color:#475569; margin:0 auto 16px auto; max-width:560px;">
                    Load the synthetic demonstration dataset or upload your campaign CSV and creative images in <strong>Upload Creatives</strong> to run hypothesis testing.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        findings: List[Finding] = st.session_state.findings

        n_supp = sum(1 for f in findings if f.evidence_classification == "Supported association")
        n_prelim = sum(1 for f in findings if f.evidence_classification == "Preliminary")
        n_under = sum(1 for f in findings if f.evidence_classification == "Underpowered")
        n_null_unsupp = sum(1 for f in findings if f.evidence_classification in ("No clear association", "Unsupported"))

        fk1, fk2, fk3, fk4 = st.columns(4)
        fk1.metric("Total Hypotheses Tested", f"{len(findings)}")
        fk2.metric("Statistically Significant (FDR q < 0.05)", f"{n_supp}")
        fk3.metric("Promising Signals (Preliminary)", f"{n_prelim}")
        fk4.metric("Inconclusive / Insufficient Data", f"{n_under + n_null_unsupp}")

        st.info(
            "**Analytical Rigor & Causal Guardrail**: Observational creative analytics distinguishes between: "
            "**(1) Descriptive Observations** (sample means/rates), **(2) Correlations** (continuous associations), "
            "**(3) Statistical Evidence** (hypothesis tests surviving Benjamini-Hochberg FDR correction), and "
            "**(4) Causal Conclusions** (which require a controlled split-test experiment isolating a single variable)."
        )

        with st.expander("Defensible Evidence Badge Rules & Statistical Methodology", expanded=False):
            st.markdown(
                """
                ### Evidence Classification Criteria
                - **Statistically Significant (`Supported association`)**: Benjamini-Hochberg adjusted $q_{\\text{FDR}} < 0.05$, minimum group sample size $N \\ge 4$ creatives per group (or $N \\ge 6$ for continuous), 95% confidence interval excludes zero, and relative effect $\\ge 8\\%$ (or $|\\rho| \\ge 0.40$).
                - **Promising (`Preliminary`)**: Nominal $p < 0.05$ before multiple-testing correction, OR $q_{\\text{FDR}} < 0.15$ with relative effect $\\ge 10\\%$ and $N \\ge 3$ per group. Warrants controlled A/B testing.
                - **Insufficient Data (`Underpowered`)**: Group sample size $N < 3$ creatives in at least one group (or $N < 6$ total for continuous). Sampling variance is too high for reliable inference.
                - **Inconclusive (`No clear association` / `Unsupported`)**: Non-significant ($p \\ge 0.10$). *Absence of statistical significance is not proof of zero effect.*
                """
            )

        # -------------------------------------------------------------------
        # WORKING FILTERS & SORTING (Metric, Evidence Strength, Min Sample Size, Campaign, Platform)
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Filter &amp; Sort Statistical Findings</div>', unsafe_allow_html=True)
        with st.container(border=True):
            fc1, fc2, fc3, fc4 = st.columns(4)
            metric_opts = ["All", "CTR", "CVR", "CPC", "CPA"] + (["ROAS"] if any(f.outcome_metric == "ROAS" for f in findings) else [])
            metric_filter = fc1.selectbox("Performance Metric", metric_opts, key="rf_metric_filter")

            sig_filter = fc2.selectbox(
                "Evidence Strength",
                [
                    "All",
                    "Statistically Significant (Supported association)",
                    "Promising (Preliminary)",
                    "Insufficient Data (Underpowered)",
                    "Inconclusive (No clear association / Unsupported)",
                ],
                key="rf_sig_filter",
            )

            min_sample_filter = fc3.number_input(
                "Minimum Sample Size (Creatives)",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
                key="rf_min_sample_input",
            )

            sort_findings_by = fc4.selectbox(
                "Sort Findings By",
                [
                    "Composite Rank Score (Default)",
                    "Statistical Significance (Lowest FDR q)",
                    "Effect Size Magnitude (|Uplift %| / |ρ|)",
                ],
                key="rf_sort_order",
            )

            sub_fc1, sub_fc2, sub_fc3 = st.columns(3)
            creative_filter_opts = ["All Creatives"]
            camp_filter_opts = ["All Campaigns"]
            plat_filter_opts = ["All Platforms"]
            if st.session_state.df_ads is not None:
                df_f_ref = st.session_state.df_ads
                if "ad_id" in df_f_ref.columns:
                    creative_filter_opts.extend(sorted(df_f_ref["ad_id"].astype(str).unique().tolist()))
                if "campaign_name" in df_f_ref.columns:
                    camp_filter_opts.extend(sorted([str(x) for x in df_f_ref["campaign_name"].dropna().unique() if str(x) != "Unknown"]))
                if "platform" in df_f_ref.columns:
                    plat_filter_opts.extend(sorted([str(x) for x in df_f_ref["platform"].dropna().unique() if str(x) != "Unknown"]))

            creative_filter = sub_fc1.selectbox("Filter by Creative ID", creative_filter_opts, key="rf_creative_filter")
            rf_camp_filter = sub_fc2.selectbox("Filter by Campaign", camp_filter_opts, key="rf_camp_filter")
            rf_plat_filter = sub_fc3.selectbox("Filter by Platform", plat_filter_opts, key="rf_plat_filter")

        filtered_findings = list(findings)
        if metric_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.outcome_metric == metric_filter]
        if sig_filter == "Statistically Significant (Supported association)":
            filtered_findings = [f for f in filtered_findings if f.evidence_classification == "Supported association"]
        elif sig_filter == "Promising (Preliminary)":
            filtered_findings = [f for f in filtered_findings if f.evidence_classification in ("Preliminary", "Preliminary evidence")]
        elif sig_filter == "Insufficient Data (Underpowered)":
            filtered_findings = [f for f in filtered_findings if f.evidence_classification in ("Underpowered", "Not estimable")]
        elif sig_filter == "Inconclusive (No clear association / Unsupported)":
            filtered_findings = [f for f in filtered_findings if f.evidence_classification in ("No clear association", "Unsupported")]

        if min_sample_filter > 1:
            def _finding_total_n(f_obj: Finding) -> int:
                if f_obj.attribute_type == "categorical":
                    return int(f_obj.sample_sizes.get("creatives_group_a", 0)) + int(f_obj.sample_sizes.get("creatives_group_b", 0))
                return int(f_obj.sample_sizes.get("creatives_count", 0))
            filtered_findings = [f for f in filtered_findings if _finding_total_n(f) >= int(min_sample_filter)]

        if creative_filter != "All Creatives":
            filtered_findings = [
                f for f in filtered_findings
                if isinstance(f.traceable_ad_ids, dict)
                and any(creative_filter in [str(x) for x in ids] for ids in f.traceable_ad_ids.values() if isinstance(ids, list))
            ]

        if (rf_camp_filter != "All Campaigns" or rf_plat_filter != "All Platforms") and st.session_state.df_ads is not None:
            sub_ads_df = st.session_state.df_ads.copy()
            if rf_camp_filter != "All Campaigns" and "campaign_name" in sub_ads_df.columns:
                sub_ads_df = sub_ads_df[sub_ads_df["campaign_name"].astype(str) == rf_camp_filter]
            if rf_plat_filter != "All Platforms" and "platform" in sub_ads_df.columns:
                sub_ads_df = sub_ads_df[sub_ads_df["platform"].astype(str) == rf_plat_filter]
            allowed_ad_ids = set(sub_ads_df["ad_id"].astype(str).tolist())
            filtered_findings = [
                f for f in filtered_findings
                if isinstance(f.traceable_ad_ids, dict)
                and any(bool(allowed_ad_ids & set(str(x) for x in ids)) for ids in f.traceable_ad_ids.values() if isinstance(ids, list))
            ]

        if sort_findings_by == "Statistical Significance (Lowest FDR q)":
            filtered_findings = sorted(filtered_findings, key=lambda x: float(x.uncertainty.get("fdr_q_value", 1.0)))
        elif sort_findings_by == "Effect Size Magnitude (|Uplift %| / |ρ|)":
            filtered_findings = sorted(
                filtered_findings,
                key=lambda x: abs(float(x.effect_size.get("relative_uplift_pct", x.effect_size.get("spearman_rho", 0.0) * 100.0) or 0.0)),
                reverse=True,
            )

        st.caption(f"Displaying **{len(filtered_findings)}** of **{len(findings)}** tested hypotheses")

        if filtered_findings:
            with st.container(border=True):
                st.markdown("#### 95% Confidence Interval Forest Plot (Matched by Estimand)")
                fp_col1, _ = st.columns([2.2, 1.8])
                with fp_col1:
                    fp_estimand_mode = st.selectbox(
                        "Select Estimand for Forest Plot",
                        [
                            "Categorical Rate Differences — CTR (Group A - Group B)",
                            "Categorical Rate Differences — CVR (Group A - Group B)",
                            "Categorical Cost Differences — CPC ($/Click)",
                            "Categorical Cost Differences — CPA ($/Conversion)",
                            "Continuous Correlations — Pearson r (Fisher z 95% CI)",
                        ],
                    )
                if "CTR" in fp_estimand_mode:
                    plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CTR"][:10]
                    x_axis_label = "Ad-Level Mean CTR Difference (Group A - Group B) with 95% Welch t CI"
                elif "CVR" in fp_estimand_mode:
                    plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CVR"][:10]
                    x_axis_label = "Ad-Level Mean CVR Difference (Group A - Group B) with 95% Welch t CI"
                elif "CPC" in fp_estimand_mode:
                    plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CPC"][:10]
                    x_axis_label = "Ad-Level Mean CPC Difference ($/Click, Group A - Group B) with 95% Welch t CI"
                elif "CPA" in fp_estimand_mode:
                    plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CPA"][:10]
                    x_axis_label = "Ad-Level Mean CPA Difference ($/Conv, Group A - Group B) with 95% Welch t CI"
                else:
                    plot_findings = [f for f in filtered_findings if f.attribute_type == "continuous"][:10]
                    x_axis_label = "Pearson Correlation r with 95% Fisher z Confidence Interval"

                if plot_findings:
                    labels = [f"{f.attribute} ({f.outcome_metric})" for f in plot_findings]
                    means = [f.uncertainty.get("point_estimate", (f.uncertainty["ci_95_lower"] + f.uncertainty["ci_95_upper"]) / 2.0) for f in plot_findings]
                    err_high = [(f.uncertainty["ci_95_upper"] - m) for f, m in zip(plot_findings, means)]
                    err_low = [(m - f.uncertainty["ci_95_lower"]) for f, m in zip(plot_findings, means)]

                    forest_fig = go.Figure()
                    forest_fig.add_trace(
                        go.Scatter(
                            x=means,
                            y=labels,
                            mode="markers",
                            error_x=dict(type="data", array=err_high, arrayminus=err_low, color="#6366F1", thickness=2.2, width=6),
                            marker=dict(size=10, color="#4F46E5"),
                        )
                    )
                    forest_fig.add_vline(x=0, line_dash="dash", line_color="#94A3B8", annotation_text="Null Effect (0)")
                    _apply_saas_chart_theme(forest_fig, height=320)
                    forest_fig.update_layout(xaxis_title=x_axis_label, yaxis_title="Hypothesis")
                    st.plotly_chart(forest_fig, use_container_width=True)
                else:
                    st.caption("No findings in the current filter view match the selected Forest Plot estimand.")

        # -------------------------------------------------------------------
        # RANKED EVIDENCE CARDS
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Evidence-Based Finding Cards</div>', unsafe_allow_html=True)

        for rank_idx, f in enumerate(filtered_findings):
            badge_label, badge_class, tech_tier = _get_finding_badge_info(f.evidence_classification)
            practical_sig = _assess_practical_significance(f)
            next_step_str = _recommended_next_step_for_finding(f)
            relevant_group_str = (
                f"Group A: `{f.group_a}` vs. Group B: `{f.group_b}`"
                if f.attribute_type == "categorical" and f.group_a and f.group_b
                else "Continuous Attribute across Analyzed Creatives"
            )

            with st.container():
                st.markdown(
                    f"""
                    <div class="finding-box">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                            <span style="font-size:1.04rem; font-weight:700; color:#0F172A;">
                                <span style="background:#EEF2FF; color:#4F46E5; padding:2px 8px; border-radius:6px; font-family:'JetBrains Mono',monospace; font-size:0.84rem; margin-right:6px;">#{rank_idx + 1}</span>
                                {f.attribute} &rarr; <span style="color:#4F46E5;">{f.outcome_metric}</span>
                            </span>
                            <span>
                                <span class="{badge_class}">{badge_label}</span>
                                <span style="font-size:0.78rem; color:#64748B; margin-left:6px;">({f.evidence_classification} &bull; Score: <strong>{f.rank_score:.2f}</strong>)</span>
                            </span>
                        </div>
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:10px;">
                            <div style="font-size:0.90rem; color:#0F172A; margin-bottom:4px;">
                                <strong>Plain-English Marketer Explanation:</strong> {f.direction_of_association}
                            </div>
                            <div style="font-size:0.82rem; color:#475569; margin-bottom:2px;">
                                <strong>Relevant Comparison Group:</strong> {relevant_group_str}
                            </div>
                            <div style="font-size:0.82rem; color:#475569;">
                                <strong>Practical Significance:</strong> {practical_sig}
                            </div>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown("**Effect Size**")
                    if f.attribute_type == "categorical":
                        uplift = f.effect_size.get("relative_uplift_pct", 0.0)
                        abs_diff = f.effect_size.get("absolute_difference", 0.0)
                        st.write(f"- Relative Uplift: **{uplift:+.1f}%**")
                        st.write(f"- Absolute Diff: `{abs_diff:+.4f}`")
                        if "cohens_d" in f.effect_size:
                            st.write(f"- Ad-Level Cohen's d: `{f.effect_size['cohens_d']:.2f}`")
                    else:
                        st.write(f"- Spearman ρ: **{f.effect_size.get('spearman_rho', 0.0):+.3f}**")
                        st.write(f"- Pearson r: `{f.effect_size.get('pearson_r', 0.0):+.3f}`")
                        st.write(f"- OLS / WLS Slope: `{f.effect_size.get('ols_slope', 0.0):.5f}`")

                with c2:
                    st.markdown("**Supporting Data & Sample**")
                    if f.attribute_type == "categorical":
                        st.write(f"- **Group A (`{f.group_a}`)**: **{f.sample_sizes.get('creatives_group_a', 0)}** ads")
                        st.write(f"- **Group B (`{f.group_b}`)**: **{f.sample_sizes.get('creatives_group_b', 0)}** ads")
                        if "impressions_group_a" in f.sample_sizes:
                            st.write(f"- Impressions: `{f.sample_sizes['impressions_group_a']:,}` vs `{f.sample_sizes['impressions_group_b']:,}`")
                    else:
                        st.write(f"- **Analyzed Creatives**: **{f.sample_sizes.get('creatives_count', 0)}** ads")
                        st.write(f"- Impressions: `{f.sample_sizes.get('total_impressions', 0):,}`")

                with c3:
                    st.markdown("**Confidence Interval**")
                    estimand_lbl = f.uncertainty.get("estimand", "Point Estimate Difference")
                    ci_l = f.uncertainty.get("ci_95_lower", 0.0)
                    ci_u = f.uncertainty.get("ci_95_upper", 0.0)
                    st.write(f"- **95% CI**: `[{ci_l:.4f}, {ci_u:.4f}]`")
                    st.write(f"- Standard Error: `{f.uncertainty.get('standard_error', 0.0):.4f}`")
                    st.caption(f"Estimand: {estimand_lbl}")

                with c4:
                    st.markdown("**Statistical Evidence**")
                    st.write(f"- Raw p-value: `{f.uncertainty.get('raw_p_value', 1.0):.4f}`")
                    st.write(f"- **Adjusted FDR q**: **{f.uncertainty.get('fdr_q_value', 1.0):.4f}**")
                    st.caption(f"Method: {f.statistical_method}")

                if f.traceable_ad_ids:
                    with st.expander("View Supporting Creative IDs in Each Group"):
                        for grp_key, ids_list in f.traceable_ad_ids.items():
                            st.write(f"**{grp_key}** ({len(ids_list)} ads): `{', '.join(ids_list)}`")

                st.markdown(
                    f"""
                        <div style="font-size:0.82rem; color:#0F172A; background:#EEF2FF; border:1px solid #C7D2FE; border-radius:8px; padding:8px 12px; margin-top:8px;">
                            <strong>Recommended Next Step:</strong> {next_step_str}
                        </div>
                        <div style="font-size:0.79rem; color:#64748B; margin-top:8px; border-top:1px dashed #E2E8F0; padding-top:6px;">
                            <strong>Important Limitations</strong>: {f.limitations}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.session_state.df_ads is not None:
            st.markdown('<div class="saas-section-header">Confounding &amp; Metadata Stratification Check</div>', unsafe_allow_html=True)
            conf_reports = investigate_confounding(st.session_state.df_ads, findings)
            if conf_reports:
                st.dataframe(pd.DataFrame(conf_reports), use_container_width=True, hide_index=True)


# ===========================================================================
# PAGE 5: CREATIVE BRIEF GENERATOR & EXPERIMENT PLANNER
# ===========================================================================
elif nav_choice == "5. Creative Brief":
    _render_page_header(
        "Creative Brief Generator & Experiment Planner",
        "Turn analytical findings into a 14-section production creative brief, structured experiment roadmap, and 6-part explainable recommendations.",
    )

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <strong>DEMO DATA — SYNTHETIC EXAMPLE</strong>: Recommendations, creative briefs, and A/B test plans below are deterministically synthesized from the synthetic benchmark findings.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not st.session_state.findings:
        st.markdown(
            """
            <div class="saas-empty-state">
                <h3 style="margin:0 0 6px 0; color:#0F172A;">Creative Brief Generator Awaiting Findings</h3>
                <p style="color:#475569; margin:0 auto 16px auto; max-width:560px;">
                    Load the synthetic demonstration dataset or upload your campaign CSV and creative images in <strong>Upload Creatives</strong> to synthesize an evidence-backed creative brief.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        all_findings: List[Finding] = st.session_state.findings

        # Guided 5-Step Brief Workflow Configuration
        st.markdown('<div class="saas-section-header">Guided Creative Brief Workflow (Steps 1–4)</div>', unsafe_allow_html=True)
        with st.container(border=True):
            cfg_c1, cfg_c2, cfg_c3 = st.columns([1.4, 1.4, 1.2])
            with cfg_c1:
                brief_objective = st.text_input(
                    "Step 1: Select Campaign Objective",
                    value="Direct Response & Conversion Efficiency Optimization",
                    key="brief_obj_input",
                )
            with cfg_c2:
                default_aud = "Performance Marketing & Paid Social Acquisition Audiences"
                if st.session_state.df_ads is not None and "audience" in st.session_state.df_ads.columns:
                    aud_vals = [str(x) for x in st.session_state.df_ads["audience"].dropna().unique() if str(x) != "Unknown"]
                    if aud_vals:
                        default_aud = ", ".join(aud_vals[:4])
                brief_audience = st.text_input(
                    "Step 2: Choose Target Audience or Segment",
                    value=default_aud,
                    key="brief_aud_input",
                )
            with cfg_c3:
                brief_format = st.selectbox(
                    "Step 3: Choose Creative Format",
                    [
                        "Multi-Format Campaign (1:1 Square Feed + 9:16 Vertical Story/Reel)",
                        "1:1 Square Feed (1080×1080 px)",
                        "9:16 Vertical Story / Reel (1080×1920 px)",
                        "4:5 Portrait Feed (1080×1350 px)",
                        "16:9 Landscape Video / Display (1920×1080 px)",
                    ],
                    key="brief_format_select",
                )

            finding_label_map = {
                f"#{idx+1} [{f.evidence_classification}] {f.attribute} -> {f.outcome_metric} (FDR q={f.uncertainty.get('fdr_q_value', 1.0):.4f})": f
                for idx, f in enumerate(all_findings)
            }
            all_labels = list(finding_label_map.keys())
            default_selected_labels = all_labels[: min(8, len(all_labels))]
            selected_labels = st.multiselect(
                "Step 4: Select Supporting Analytical Findings to Ground the Brief",
                options=all_labels,
                default=default_selected_labels,
                key="brief_selected_findings_multi",
            )
            active_brief_findings = [finding_label_map[lbl] for lbl in selected_labels] if selected_labels else all_findings

            st.caption(
                "**Methodology Note**: Brief generation uses deterministic, rule-based synthesis grounded strictly in the selected statistical findings and active dataset metrics (never fabricated or black-box LLM claims). No recommendation guarantees future advertising performance."
            )

        brief = generate_creative_brief(
            findings=active_brief_findings,
            df_metrics=st.session_state.df_ads,
            dataset_is_synthetic=st.session_state.is_synthetic,
            campaign_objective=brief_objective,
            target_audience=brief_audience,
            creative_format=brief_format,
        )
        sections = brief.get("structured_sections", {})

        if brief.get("is_low_evidence_fallback"):
            st.warning(f"**Evidence Strength Disclosure**: {brief.get('evidence_status_note', '')}")
        else:
            st.success(f"**Evidence Strength Disclosure**: {brief.get('evidence_status_note', '')}")

        bk1, bk2, bk3, bk4 = st.columns(4)
        bk1.metric("Statistically Significant Drivers", f"{len(brief['supported_findings'])}")
        bk2.metric("Promising Hypotheses", f"{len(brief['preliminary_findings'])}")
        bk3.metric("Grounded DO Guidelines", f"{len(brief['actionable_dos'])}")
        bk4.metric("Structured Experiments", f"{len(brief.get('experiment_plan', []))}")

        # -------------------------------------------------------------------
        # STEP 5: 14-SECTION STRUCTURED CREATIVE BRIEF WORKSPACE
        # -------------------------------------------------------------------
        st.markdown('<div class="saas-section-header">Step 5: Structured 14-Section Creative Strategy Brief</div>', unsafe_allow_html=True)

        s_col1, s_col2 = st.columns(2)
        with s_col1:
            with st.container(border=True):
                st.markdown("##### 1. Brief Title")
                st.write(sections.get("brief_title", ""))
                st.markdown("##### 2. Target Audience")
                st.write(sections.get("target_audience", brief_audience))
                st.markdown("##### 3. Campaign Objective")
                st.write(sections.get("campaign_objective", brief_objective))
                st.markdown("##### 4. Creative Format")
                st.write(sections.get("creative_format", brief_format))
                st.markdown("##### 5. Core Insight (Backed by Observed Evidence)")
                st.info(sections.get("core_insight", sections.get("key_insight", "")))
                st.markdown("##### 6. Recommended Hook")
                st.write(sections.get("recommended_hook", sections.get("hook", "")))
                st.markdown("##### 7. Visual Direction")
                st.write(sections.get("visual_direction", ""))

        with s_col2:
            with st.container(border=True):
                st.markdown("##### 8. Copy Angle")
                st.write(sections.get("copy_angle", sections.get("main_message", "")))
                st.markdown("##### 9. Call to Action")
                st.write(sections.get("call_to_action", ""))
                st.markdown("##### 10. Creative DO List & 11. Creative AVOID List")
                for do_item in brief["actionable_dos"][:3]:
                    st.markdown(f"- **DO**: {do_item}")
                for dont_item in brief["actionable_donts"][:2]:
                    st.markdown(f"- **AVOID / CAUTION**: {dont_item}")
                st.markdown("##### 12. Variant Ideas")
                for v_idea in brief.get("variant_ideas", [])[:3]:
                    st.markdown(f"- {v_idea}")
                st.markdown("##### 13. Suggested Test Plan & 14. Success Metrics")
                st.write(sections.get("suggested_test_plan", sections.get("recommended_experiment", "")))
                st.write(sections.get("success_metrics", ""))
                st.caption(f"**Assumptions & Limitations**: {sections.get('assumptions_and_limitations', '')}")

        b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs(
            [
                "Experiment Planner (Section 13)",
                "Explainable Recommendations (Section 14)",
                "Supporting Evidence Breakdown",
                "Edit, Copy & Export Brief",
            ]
        )

        with b_tab1:
            st.markdown("#### Structured Creative Experiment Planner")
            st.caption("Turn analytical findings into controlled A/B split-test designs with clear control vs. variant concepts, sample-size guidance, and decision criteria.")
            exp_plan_list = brief.get("experiment_plan", [])
            if exp_plan_list:
                for exp_item in exp_plan_list:
                    with st.container(border=True):
                        st.markdown(
                            f"##### `{exp_item['experiment_id']}` — {exp_item['experiment_name']} "
                            f"(`{exp_item['evidence_tier']}` &bull; Status: `{exp_item['status']}`)"
                        )
                        st.markdown(f"- **Hypothesis**: {exp_item['hypothesis']}")
                        ec_a, ec_b = st.columns(2)
                        with ec_a:
                            st.markdown(f"- **Control Concept**: {exp_item['control_concept']}")
                            st.markdown(f"- **Variant Concept**: {exp_item['variant_concept']}")
                            st.markdown(f"- **Single Variable Changed**: {exp_item['variable_changed']}")
                            st.markdown(f"- **Target Audience / Placement**: {exp_item['target_audience_or_placement']}")
                        with ec_b:
                            st.markdown(f"- **Primary Metric**: `{exp_item['primary_metric']}` (Secondary: `{exp_item['secondary_metrics']}`)")
                            st.markdown(f"- **Minimum Data Considerations**: {exp_item['minimum_data_considerations']}")
                            st.markdown(f"- **Measurement Period Guidance**: {exp_item['measurement_period_guidance']}")
                            st.markdown(f"- **Decision Criteria**: {exp_item['decision_criteria']}")
                        st.caption(f"**Risks & Limitations**: {exp_item['risks_and_limitations']}")

                st.markdown("##### Tabular Experiment Plan Matrix")
                st.dataframe(pd.DataFrame(exp_plan_list), use_container_width=True, hide_index=True)
            else:
                st.info("Select at least one statistical finding above to populate the Experiment Planner.")

        with b_tab2:
            st.markdown("#### Explainable Recommendations (6-Part Evidence Chain)")
            st.caption("Every recommendation explicitly states what was observed, supporting data, why it matters, the action to test, how to measure success, and remaining uncertainty.")
            recs_bundle = generate_recommendations(active_brief_findings, df_metrics=st.session_state.df_ads)
            all_rec_cards = (
                recs_bundle.get("category_a_observed_evidence", [])
                + recs_bundle.get("category_b_hypotheses_to_test", [])
                + recs_bundle.get("category_c_blocked_insufficient_evidence", [])
            )
            if all_rec_cards:
                for idx_r, rec_item in enumerate(all_rec_cards[:8]):
                    with st.container(border=True):
                        st.markdown(
                            f"##### #{idx_r + 1}: {rec_item.get('attribute', '')} &rarr; `{rec_item.get('outcome_metric', '')}` "
                            f"({rec_item.get('recommendation_category', '')})"
                        )
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            st.markdown(f"1. **What Was Observed**: {rec_item.get('what_was_observed', '')}")
                            st.markdown(f"2. **Supporting Data**: `{rec_item.get('supporting_data', '')}`")
                            st.markdown(f"3. **Why It Matters**: {rec_item.get('why_it_matters', '')}")
                        with rc2:
                            st.markdown(f"4. **Action to Test**: {rec_item.get('action_to_test', '')}")
                            st.markdown(f"5. **How to Measure Success**: {rec_item.get('how_to_measure_success', '')}")
                            st.markdown(f"6. **Remaining Uncertainty**: {rec_item.get('remaining_uncertainty', '')}")
            else:
                st.info("No recommendations available for the current finding selection.")

        with b_tab3:
            st.markdown("#### Confirmed Statistical Associations (`Supported association`: FDR q < 0.05)")
            if brief["supported_findings"]:
                for f in brief["supported_findings"]:
                    st.success(
                        f"**{f.attribute} &rarr; {f.outcome_metric}**: {f.direction_of_association}\n\n"
                        f"- **Method**: `{f.statistical_method}` | **95% CI**: `[{f.uncertainty['ci_95_lower']:.4f}, {f.uncertainty['ci_95_upper']:.4f}]` | **Adjusted FDR q**: `{f.uncertainty['fdr_q_value']:.4f}`\n"
                        f"- **Limitations**: {f.limitations}"
                    )
            else:
                st.info("No selected attributes reached Supported association (FDR q < 0.05 with N >= 4 per group) in the current dataset.")

            st.markdown("#### Promising & Underpowered Hypotheses (Require Split-Test Verification)")
            prelim_and_under = brief["preliminary_findings"] + brief["underpowered_findings"]
            if prelim_and_under:
                for f in prelim_and_under[:6]:
                    st.warning(
                        f"**[{f.evidence_classification}] {f.attribute} &rarr; {f.outcome_metric}**: {f.direction_of_association} "
                        f"(Method: `{f.statistical_method}`, Raw p = `{f.uncertainty['raw_p_value']:.4f}`, Adjusted FDR q = `{f.uncertainty['fdr_q_value']:.4f}`)"
                    )
            else:
                st.write("No preliminary or underpowered hypotheses queued.")

        with b_tab4:
            st.markdown("#### Interactive Brief Editor, One-Click Copy & Export")
            st.caption("Edit the synthesized Markdown brief below; your edits are preserved for copying and downloading as Markdown or Plain Text.")
            current_md = st.session_state.edited_brief_markdown if st.session_state.edited_brief_markdown is not None else brief["full_markdown"]
            edited_md = st.text_area(
                "Edit Creative Brief Markdown",
                value=current_md,
                height=360,
                key="brief_markdown_editor_area",
            )
            st.session_state.edited_brief_markdown = edited_md

            ed_c1, ed_c2, ed_c3, ed_c4 = st.columns(4)
            with ed_c1:
                st.download_button(
                    label="Download Brief (.md)",
                    data=edited_md,
                    file_name="executive_creative_brief.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with ed_c2:
                st.download_button(
                    label="Download Brief (.txt)",
                    data=edited_md,
                    file_name="executive_creative_brief.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with ed_c3:
                if brief.get("experiment_plan"):
                    st.download_button(
                        label="Download Experiment Plan (CSV)",
                        data=pd.DataFrame(brief["experiment_plan"]).to_csv(index=False),
                        file_name="creative_experiment_plan.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
            with ed_c4:
                if st.button("Reset Brief to Default", use_container_width=True):
                    st.session_state.edited_brief_markdown = None
                    st.rerun()

            with st.expander("Copy Brief Source (Click Copy Icon in Top-Right of Code Block)", expanded=False):
                st.code(edited_md, language="markdown")


# ===========================================================================
# PAGE 6: EXPORT CENTER
# ===========================================================================
elif nav_choice == "6. Export Center":
    _render_page_header(
        "Export & Reporting Center",
        "Download validated performance datasets, Empirical Bayes creative scorecards, statistical findings, creative briefs, experiment plans, and data quality summaries.",
    )

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                <strong>DEMO DATA — SYNTHETIC EXAMPLE</strong>: All exports generated below are clearly labeled as synthetic demonstration data and must not be presented as empirical production results.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.df_ads is None or st.session_state.df_ads.empty:
        st.markdown(
            """
            <div class="saas-empty-state">
                <h3 style="margin:0 0 6px 0; color:#0F172A;">No Active Campaign Dataset to Export</h3>
                <p style="color:#475569; margin:0 auto 16px auto; max-width:580px;">
                    Load the synthetic demonstration dataset or upload your campaign CSV and creative images in <strong>Upload Creatives</strong> to enable full analytical exports.
                    Starter templates remain available below.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            if st.button("Load Synthetic Demo Dataset", type="primary", use_container_width=True):
                load_demo_dataset()
                st.rerun()
        with ec2:
            st.download_button(
                "Download Example CSV Template",
                data=generate_example_csv_content(),
                file_name="ad_creative_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with ec3:
            st.download_button(
                "Download Sample Upload Bundle (.zip)",
                data=build_sample_upload_zip_bytes(),
                file_name="adcreative_sample_upload_bundle.zip",
                mime="application/zip",
                use_container_width=True,
            )
    else:
        df_exp = st.session_state.df_ads
        findings_exp: List[Finding] = st.session_state.findings
        ing_exp = st.session_state.ingestion_result
        brief_exp = generate_creative_brief(
            findings=findings_exp,
            df_metrics=df_exp,
            dataset_is_synthetic=st.session_state.is_synthetic,
        )
        consolidated_md = build_consolidated_report_markdown(
            df_exp, findings_exp, ing_exp, st.session_state.is_synthetic
        )
        recs_exp = generate_recommendations(findings_exp, df_metrics=df_exp)
        exp_plan_exp = generate_experiment_plan(findings_exp, df_metrics=df_exp)
        scorecard_exp = build_creative_scorecard(df_exp, primary_metric="composite")
        dq_exp = compute_data_quality_summary(df_exp, ing_exp, is_synthetic=st.session_state.is_synthetic)

        pdf_bytes = generate_pdf_report_bytes(
            project_name="Active Campaign Analysis",
            project_id="session_active",
            df_metrics=df_exp,
            findings=findings_exp,
            recommendations=recs_exp,
            is_synthetic=st.session_state.is_synthetic,
        )

        st.success(
            f"Export Pipeline Ready: {len(df_exp)} validated creative records, "
            f"{len(st.session_state.images_dict)} matched creative images, "
            f"{len(findings_exp)} statistical findings, and {len(exp_plan_exp)} experiment plans available for download."
        )

        st.markdown('<div class="saas-section-header">1. Core Analytical &amp; Strategy Exports</div>', unsafe_allow_html=True)
        row1_c1, row1_c2 = st.columns(2)

        with row1_c1:
            with st.container(border=True):
                st.markdown("#### Creative Performance & Scorecard CSV")
                st.write("Download validated ad-level campaign metrics or the full Empirical Bayes Creative Scorecard.")
                perf_cols = [c for c in ["ad_id", "spend", "impressions", "clicks", "conversions", "revenue", "ctr", "cvr", "cpc", "cpa", "roas"] if c in df_exp.columns]
                st.caption(f"**Included Information**: `{', '.join(perf_cols)}` ({len(df_exp)} rows) + Empirical Bayes Rank Scorecard.")
                dl_p1, dl_p2 = st.columns(2)
                with dl_p1:
                    st.download_button(
                        "Performance Summary (CSV)",
                        data=df_exp[perf_cols].to_csv(index=False),
                        file_name="validated_performance_metrics.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with dl_p2:
                    sc_df = scorecard_exp.get("scorecard_df", pd.DataFrame())
                    st.download_button(
                        "Creative Scorecard (CSV)",
                        data=sc_df.to_csv(index=False) if not sc_df.empty else df_exp[perf_cols].to_csv(index=False),
                        file_name="creative_ranking_scorecard.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

        with row1_c2:
            with st.container(border=True):
                st.markdown("#### Ranked Statistical Findings (CSV & JSON)")
                st.write("Ranked hypothesis tests with effect sizes, 95% confidence intervals, raw p-values, and BH-FDR q-values.")
                st.caption(f"**Included Information**: {len(findings_exp)} tested hypotheses, estimands, sample sizes, and limitations.")
                f_exp_df = findings_to_export_df(findings_exp)
                dl_f1, dl_f2 = st.columns(2)
                with dl_f1:
                    st.download_button(
                        "Download Findings (CSV)",
                        data=f_exp_df.to_csv(index=False),
                        file_name="ranked_statistical_findings.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with dl_f2:
                    st.download_button(
                        "Download Findings (JSON)",
                        data=json.dumps([f.to_dict() for f in findings_exp], indent=2),
                        file_name="ranked_statistical_findings.json",
                        mime="application/json",
                        use_container_width=True,
                    )

        row2_c1, row2_c2 = st.columns(2)

        with row2_c1:
            with st.container(border=True):
                st.markdown("#### Creative Analysis Report (Markdown & PDF)")
                st.write("End-to-end analytical report combining ingestion audit, pooled vs. ad-level KPIs, top findings, and experiment recommendations.")
                st.caption("**Included Information**: Data audit, KPI comparison table, top statistical findings, and governance watermark.")
                dl_r1, dl_r2 = st.columns(2)
                with dl_r1:
                    st.download_button(
                        "Download Analysis Report (MD)",
                        data=consolidated_md,
                        file_name="consolidated_adcreative_report.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with dl_r2:
                    st.download_button(
                        "Download Executive Report (PDF)",
                        data=pdf_bytes,
                        file_name="executive_analytical_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

        with row2_c2:
            with st.container(border=True):
                st.markdown("#### Creative Brief (.md / .txt) & Experiment Plan (CSV)")
                st.write("Deterministic 14-section creative strategy brief, designer DO/AVOID checklist, and structured experiment plan.")
                st.caption(f"**Included Information**: 14-section brief, {len(brief_exp['actionable_dos'])} DOs, and {len(exp_plan_exp)} experiment plans.")
                brief_md_to_export = st.session_state.edited_brief_markdown if st.session_state.edited_brief_markdown is not None else brief_exp["full_markdown"]
                dl_b1, dl_b2, dl_b3 = st.columns(3)
                with dl_b1:
                    st.download_button(
                        "Brief (.md)",
                        data=brief_md_to_export,
                        file_name="executive_creative_brief.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with dl_b2:
                    st.download_button(
                        "Brief (.txt)",
                        data=brief_md_to_export,
                        file_name="executive_creative_brief.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with dl_b3:
                    st.download_button(
                        "Experiment Plan (CSV)",
                        data=pd.DataFrame(exp_plan_exp).to_csv(index=False) if exp_plan_exp else pd.DataFrame().to_csv(index=False),
                        file_name="creative_experiment_plan.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

        st.markdown('<div class="saas-section-header">2. Data Quality Summary &amp; Computer Vision Feature Tables</div>', unsafe_allow_html=True)
        row3_c1, row3_c2, row3_c3 = st.columns(3)

        with row3_c1:
            with st.container(border=True):
                st.markdown("#### Data Quality Summary (CSV & MD)")
                st.write("Dataset provenance, creative & row counts, date coverage, missing optional fields, and zero-denominator counts.")
                st.caption(f"**Origin**: `{dq_exp.get('dataset_origin_label', '')}`")
                dq_flat_df = pd.DataFrame([{
                    "dataset_origin": dq_exp.get("dataset_origin_label", ""),
                    "creative_count": dq_exp.get("creative_count", 0),
                    "performance_record_count": dq_exp.get("performance_record_count", 0),
                    "date_coverage": dq_exp.get("date_coverage", "Not provided"),
                    "data_freshness": dq_exp.get("data_freshness", "Static snapshot"),
                    "present_optional_fields": ", ".join(dq_exp.get("present_optional_fields", [])),
                    "missing_optional_fields": ", ".join(dq_exp.get("missing_optional_fields", [])),
                    "zero_click_creatives": dq_exp.get("zero_click_creatives", 0),
                    "zero_conversion_creatives": dq_exp.get("zero_conversion_creatives", 0),
                }])
                st.download_button(
                    "Download Data Quality Summary (CSV)",
                    data=dq_flat_df.to_csv(index=False),
                    file_name="data_quality_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        with row3_c2:
            with st.container(border=True):
                st.markdown("#### Extracted Visual Features CSV")
                feat_count = len(st.session_state.features_df) if st.session_state.features_df is not None else 0
                st.write("Computer vision measurements, color tone, luminance, composition, and frontal face cascade telemetry.")
                st.caption(f"**Included Information**: {feat_count} matched creative feature rows.")
                if st.session_state.features_df is not None and not st.session_state.features_df.empty:
                    feat_csv_str = st.session_state.features_df.drop(
                        columns=["color_palette_distribution", "feature_sources", "unavailable_features"], errors="ignore"
                    ).to_csv(index=False)
                else:
                    feat_csv_str = pd.DataFrame(columns=["ad_id"]).to_csv(index=False)
                st.download_button(
                    "Download Extracted Features (CSV)",
                    data=feat_csv_str,
                    file_name="extracted_creative_features.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        with row3_c3:
            with st.container(border=True):
                st.markdown("#### Enriched Performance + Features CSV")
                st.write("Merged campaign performance telemetry and extracted computer vision attributes in a single flat table.")
                st.caption(f"**Included Information**: All {len(df_exp)} creative records merged with CV feature columns.")
                enriched_csv_str = df_exp.drop(
                    columns=["color_palette_distribution", "feature_sources", "unavailable_features"], errors="ignore"
                ).to_csv(index=False)
                st.download_button(
                    "Download Enriched Dataset (CSV)",
                    data=enriched_csv_str,
                    file_name="enriched_ad_performance_and_features.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

