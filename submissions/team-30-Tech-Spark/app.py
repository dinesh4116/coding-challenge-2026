"""
AdCreative Intelligence - Main Streamlit Web Application
Challenge: PS-02 | AdCreative Intelligence

A high-performance interactive application for advertising visual intelligence:
- Data Ingestion, Matching Audit & Validation (never silently discards records)
- Automated Computer Vision Feature Extraction with Provenance & Status Reporting
- Side-by-Side Creative Comparison & Interactive Visual Gallery
- Rigorous Statistical Engine with Multiple-Testing Correction (Benjamini-Hochberg FDR)
- Ranked Findings Dashboard with 10-Point Reporting, Explicit Estimands & Confidence Intervals
- Data-Grounded Creative Brief Generator (zero hardcoded analytical results)
"""

import importlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
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

if not hasattr(_fe_mod, "FEATURE_PROVENANCE_MAP") or not hasattr(_fe_mod, "UNAVAILABLE_CAPABILITIES"):
    importlib.reload(_fe_mod)
if not hasattr(_se_mod, "_compute_ad_level_welch_inference"):
    importlib.reload(_se_mod)
if not hasattr(_cb_mod, "build_consolidated_report_markdown"):
    importlib.reload(_cb_mod)

from data_ingestion import (
    ingest_ad_dataset,
    generate_example_csv_content,
    validate_and_parse_csv,
    match_images_to_records,
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
    Finding,
)
from synthetic_data import (
    get_synthetic_dataset_paths,
    generate_synthetic_dataset,
)
from creative_brief import (
    generate_creative_brief,
)


st.set_page_config(
    page_title="AdCreative Intelligence | PS-02",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1E88E5;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .badge-supported {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        border: 1px solid #A5D6A7;
    }
    .badge-preliminary {
        background-color: #FFF8E1;
        color: #F57F17;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        border: 1px solid #FFE082;
    }
    .badge-underpowered {
        background-color: #EDE7F6;
        color: #5E35B1;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        border: 1px solid #D1C4E9;
    }
    .badge-neutral {
        background-color: #ECEFF1;
        color: #455A64;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        border: 1px solid #CFD8DC;
    }
    .badge-unsupported {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        border: 1px solid #FFCDD2;
    }
    .finding-box {
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        background-color: #FFFFFF;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .synthetic-banner {
        background-color: #FFF3E0;
        border: 1px solid #FFE0B2;
        color: #E65100;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 0.9em;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = [
    "1. Overview",
    "2. Upload Creatives",
    "3. Creative Library",
    "4. Ranked Findings",
    "5. Creative Brief",
]


def init_session_state():
    if "df_ads" not in st.session_state:
        st.session_state.df_ads = None
    if "images_dict" not in st.session_state:
        st.session_state.images_dict = {}
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


init_session_state()


def navigate_to(page_name: str):
    """Programmatically switches the active navigation page."""
    st.session_state.nav_page = page_name


def _format_rate(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"{float(val) * 100.0:.2f}%"


def _format_currency(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"${float(val):,.2f}"


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


def findings_to_export_df(findings: List[Finding]) -> pd.DataFrame:
    """Converts Finding objects into a clean tabular DataFrame for CSV export."""
    rows = []
    for idx, f in enumerate(findings):
        rows.append({
            "rank": idx + 1,
            "rank_score": f.rank_score,
            "attribute": f.attribute,
            "attribute_type": f.attribute_type,
            "outcome_metric": f.outcome_metric,
            "evidence_classification": f.evidence_classification,
            "direction_of_association": f.direction_of_association,
            "statistical_method": f.statistical_method,
            "estimand": f.uncertainty.get("estimand", ""),
            "point_estimate": f.uncertainty.get("point_estimate", ""),
            "ci_95_lower": f.uncertainty.get("ci_95_lower", ""),
            "ci_95_upper": f.uncertainty.get("ci_95_upper", ""),
            "standard_error": f.uncertainty.get("standard_error", ""),
            "raw_p_value": f.uncertainty.get("raw_p_value", ""),
            "adjusted_fdr_q_value": f.uncertainty.get("fdr_q_value", ""),
            "bonferroni_p_value": f.uncertainty.get("bonferroni_p", ""),
            "relative_uplift_pct": f.effect_size.get("relative_uplift_pct", ""),
            "creatives_group_a": f.sample_sizes.get("creatives_group_a", f.sample_sizes.get("creatives_count", "")),
            "creatives_group_b": f.sample_sizes.get("creatives_group_b", ""),
            "impressions_group_a": f.sample_sizes.get("impressions_group_a", f.sample_sizes.get("total_impressions", "")),
            "impressions_group_b": f.sample_sizes.get("impressions_group_b", ""),
            "limitations": f.limitations,
        })
    return pd.DataFrame(rows)


def build_consolidated_report_markdown(
    df_ads: pd.DataFrame,
    findings: List[Finding],
    ingestion_res: Any = None,
    is_synthetic: bool = False,
) -> str:
    """Builds a single consolidated Markdown report combining ingestion audit, metrics, features, findings, and brief."""
    brief = generate_creative_brief(findings, df_metrics=df_ads, dataset_is_synthetic=is_synthetic)
    kpis = compute_aggregate_kpis(df_ads)

    lines = [
        "# CONSOLIDATED ADCREATIVE INTELLIGENCE REPORT",
        f"**Dataset Mode**: {'Synthetic Demonstration Dataset' if is_synthetic else 'Uploaded Empirical Campaign Dataset'}",
        "",
        "## 1. DATA INGESTION & MATCHING AUDIT",
        f"- **Valid CSV Records**: {len(df_ads)}",
        f"- **Matched Creative Images**: {len(ingestion_res.matched_images) if ingestion_res else len(df_ads)}",
        f"- **CSV Records Missing Images**: {len(ingestion_res.unmatched_records) if ingestion_res else 0}",
        f"- **Orphan Images Missing CSV Records**: {len(ingestion_res.unmatched_images) if ingestion_res else 0}",
        "",
        "## 2. CAMPAIGN-LEVEL POOLED METRICS VS. AD-LEVEL DISTRIBUTION",
        "| Metric | Campaign-Level Pooled (ΣNum / ΣDenom) | Unweighted Ad-Level Mean | Unweighted Ad-Level Median |",
        "| :--- | :--- | :--- | :--- |",
        f"| **CTR** | {_format_rate(kpis.get('aggregate_ctr'))} | {_format_rate(kpis.get('mean_ad_ctr'))} | {_format_rate(kpis.get('median_ad_ctr'))} |",
        f"| **CVR** | {_format_rate(kpis.get('aggregate_cvr'))} | {_format_rate(kpis.get('mean_ad_cvr'))} | {_format_rate(kpis.get('median_ad_cvr'))} |",
        f"| **CPC** | {_format_currency(kpis.get('aggregate_cpc'))} | {_format_currency(kpis.get('mean_ad_cpc'))} | {_format_currency(kpis.get('median_ad_cpc'))} |",
        f"| **CPA** | {_format_currency(kpis.get('aggregate_cpa'))} | {_format_currency(kpis.get('mean_ad_cpa'))} | {_format_currency(kpis.get('median_ad_cpa'))} |",
        "",
        "## 3. TOP RANKED STATISTICAL FINDINGS",
    ]
    for idx, f in enumerate(findings[:10]):
        lines.append(
            f"{idx + 1}. **[{f.evidence_classification}] {f.attribute} -> {f.outcome_metric}**: {f.direction_of_association} "
            f"(Method: {f.statistical_method}, 95% CI [{f.uncertainty.get('ci_95_lower', 0):.4f}, {f.uncertainty.get('ci_95_upper', 0):.4f}], "
            f"Raw p={f.uncertainty.get('raw_p_value', 1):.4f}, FDR q={f.uncertainty.get('fdr_q_value', 1):.4f})"
        )
    lines.extend(["", "---", "", brief["full_markdown"]])
    return "\n".join(lines)


def load_demo_dataset():
    """Loads pre-generated synthetic dataset into session state."""
    with st.spinner("Generating and analyzing synthetic demonstration creatives..."):
        csv_path, img_dir = get_synthetic_dataset_paths()

        images = {}
        for p in sorted(img_dir.glob("*.png")):
            with Image.open(p) as im:
                images[p.name] = im.copy()

        res = ingest_ad_dataset(csv_path, images)
        if res.is_valid:
            feat_dict = batch_extract_features(res.matched_images)
            feat_records = []
            for ad_id, f in feat_dict.items():
                f_row = {"ad_id": ad_id, **f}
                feat_records.append(f_row)

            f_df = pd.DataFrame(feat_records) if feat_records else pd.DataFrame(columns=["ad_id"])
            merged_df = pd.merge(res.df, f_df, on="ad_id", how="left")
            findings = run_full_statistical_analysis(merged_df)

            st.session_state.df_ads = merged_df
            st.session_state.images_dict = res.matched_images
            st.session_state.features_df = f_df
            st.session_state.findings = findings
            st.session_state.is_synthetic = True
            st.session_state.ingestion_result = res
            st.success("Successfully loaded synthetic demonstration dataset (18 creatives)!")


# Sidebar Navigation
st.sidebar.title("🎨 AdCreative Intelligence")
st.sidebar.caption("Evidence-Based Visual Ad Intelligence | PS-02")

nav_choice = st.sidebar.radio(
    "Navigation",
    PAGES,
    key="nav_page",
)

st.sidebar.markdown("---")
if st.sidebar.button("⚡ Load Synthetic Demo Dataset (18 Ads)", use_container_width=True):
    load_demo_dataset()
    st.rerun()

if st.session_state.df_ads is not None:
    dataset_badge = "🧪 Synthetic Demo (18 Ads)" if st.session_state.is_synthetic else f"📂 Custom Upload ({len(st.session_state.df_ads)} Ads)"
    st.sidebar.info(f"**Active Dataset**: {dataset_badge}\n\n- Matched Images: **{len(st.session_state.images_dict)}**\n- Tested Hypotheses: **{len(st.session_state.findings)}**")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Statistical Governance**:
    - Pooled Numerator/Denominator KPIs + Ad-Level Mean & Median
    - FDR Benjamini-Hochberg Multiple-Testing Correction
    - Creative-Level Welch-Satterthwaite t-Test & Mann-Whitney U
    - 95% Confidence Intervals Matched to Estimands
    - Observational Non-Causal Reporting
    """
)

# -------------------------------------------------------------
# PAGE 1: OVERVIEW
# -------------------------------------------------------------
if nav_choice == "1. Overview":
    st.title("🎨 AdCreative Intelligence — Executive Campaign Overview")
    st.caption("Automated Visual Feature Extraction, Statistical Hypothesis Testing & Evidence-Grounded Creative Briefs")

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                ⚠️ <strong>SYNTHETIC DEMO DATASET ACTIVE</strong>: Currently analyzing synthetic demonstration creatives generated for pipeline verification. Upload your own CSV and images in <em>2. Upload Creatives</em> for production analysis.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.df_ads is None:
        st.info("👋 **Welcome to AdCreative Intelligence!** No creatives are loaded yet. Load the 18-ad synthetic demonstration dataset with 1 click or go to **2. Upload Creatives** to upload your own CSV and ad images.")
        c1, c2, _ = st.columns([1.2, 1.2, 2])
        with c1:
            if st.button("🚀 Load Synthetic Demo Dataset Now", type="primary", use_container_width=True):
                load_demo_dataset()
                st.rerun()
        with c2:
            st.button("📂 Go to 2. Upload Creatives", on_click=navigate_to, args=("2. Upload Creatives",), use_container_width=True)
    else:
        df = st.session_state.df_ads
        kpis = compute_aggregate_kpis(df)
        ing_res = st.session_state.ingestion_result
        total_uploaded_imgs = (
            len(ing_res.matched_images) + len(ing_res.unmatched_images)
            if ing_res is not None
            else len(st.session_state.images_dict)
        )

        # Workspace & Pipeline Status Row
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Uploaded Images", f"{total_uploaded_imgs}")
        s2.metric("Valid CSV Records", f"{kpis['total_creatives']}")
        s3.metric("Matched Creatives", f"{len(st.session_state.images_dict)}")
        s4.metric("Statistical Findings", f"{len(st.session_state.findings)}")

        # Top Metric Row (8 KPIs)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Spend", f"${kpis['total_spend']:,.2f}")
        m2.metric("Total Impressions", f"{kpis['total_impressions']:,}")
        m3.metric("Total Clicks", f"{kpis['total_clicks']:,}")
        m4.metric("Total Conversions", f"{kpis['total_conversions']:,}")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Pooled CTR (ΣClicks / ΣImp)", _format_rate(kpis["aggregate_ctr"]))
        m6.metric("Pooled CVR (ΣConv / ΣClicks)", _format_rate(kpis["aggregate_cvr"]))
        m7.metric("Pooled CPC (ΣSpend / ΣClicks)", _format_currency(kpis["aggregate_cpc"]))
        m8.metric("Pooled CPA (ΣSpend / ΣConv)", _format_currency(kpis["aggregate_cpa"]))

        with st.expander("📊 Campaign-Level Pooled Metrics vs. Unweighted Ad-Level Distribution (Mean & Median)", expanded=True):
            st.caption(
                "Campaign-level pooled metrics weight each creative by its exposure volume (ΣNumerator / ΣDenominator), "
                "whereas unweighted ad-level averages treat each creative equally regardless of budget/impressions. Both are presented below:"
            )
            agg_comparison_df = pd.DataFrame([
                {
                    "Performance Metric": "CTR (Click-Through Rate)",
                    "Campaign-Level Pooled (ΣClicks / ΣImpressions)": _format_rate(kpis["aggregate_ctr"]),
                    "Unweighted Ad-Level Mean": _format_rate(kpis["mean_ad_ctr"]),
                    "Unweighted Ad-Level Median": _format_rate(kpis["median_ad_ctr"]),
                },
                {
                    "Performance Metric": "CVR (Conversion Rate)",
                    "Campaign-Level Pooled (ΣConversions / ΣClicks)": _format_rate(kpis["aggregate_cvr"]),
                    "Unweighted Ad-Level Mean": _format_rate(kpis["mean_ad_cvr"]),
                    "Unweighted Ad-Level Median": _format_rate(kpis["median_ad_cvr"]),
                },
                {
                    "Performance Metric": "CPC (Cost Per Click)",
                    "Campaign-Level Pooled (ΣSpend / ΣClicks)": _format_currency(kpis["aggregate_cpc"]),
                    "Unweighted Ad-Level Mean": _format_currency(kpis["mean_ad_cpc"]),
                    "Unweighted Ad-Level Median": _format_currency(kpis["median_ad_cpc"]),
                },
                {
                    "Performance Metric": "CPA (Cost Per Acquisition)",
                    "Campaign-Level Pooled (ΣSpend / ΣConversions)": _format_currency(kpis["aggregate_cpa"]),
                    "Unweighted Ad-Level Mean": _format_currency(kpis["mean_ad_cpa"]),
                    "Unweighted Ad-Level Median": _format_currency(kpis["median_ad_cpa"]),
                },
            ])
            st.dataframe(agg_comparison_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Aggregate Conversion Funnel")
            funnel_fig = go.Figure(
                go.Funnel(
                    y=["Impressions", "Clicks", "Conversions"],
                    x=[kpis["total_impressions"], kpis["total_clicks"], kpis["total_conversions"]],
                    textinfo="value+percent initial",
                    marker={"color": ["#1976D2", "#42A5F5", "#66BB6A"]},
                )
            )
            funnel_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320)
            st.plotly_chart(funnel_fig, use_container_width=True)

        with col_right:
            st.subheader("Spend vs. Conversions per Creative")
            scatter_fig = px.scatter(
                df,
                x="spend",
                y="conversions",
                size=df["impressions"].clip(lower=100),
                color="dominant_color_tone" if "dominant_color_tone" in df.columns else None,
                hover_name="ad_id",
                labels={"spend": "Spend ($)", "conversions": "Conversions", "dominant_color_tone": "Color Tone"},
                color_discrete_map={"Warm": "#FF5722", "Cool": "#2196F3", "Neutral": "#9E9E9E", "Unknown": "#BDBDBD"},
            )
            scatter_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320)
            st.plotly_chart(scatter_fig, use_container_width=True)

        st.subheader("Extracted Visual Inventory Breakdown")
        c_a, c_b, c_c = st.columns(3)
        if "dominant_color_tone" in df.columns and df["dominant_color_tone"].notna().any():
            with c_a:
                fig_tone = px.pie(
                    df,
                    names="dominant_color_tone",
                    title="Dominant Color Tone",
                    hole=0.4,
                    color="dominant_color_tone",
                    color_discrete_map={"Warm": "#FF7043", "Cool": "#42A5F5", "Neutral": "#B0BEC5"},
                )
                fig_tone.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
                st.plotly_chart(fig_tone, use_container_width=True)

        if "human_presence_cat" in df.columns and df["human_presence_cat"].notna().any():
            with c_b:
                fig_human = px.pie(
                    df,
                    names="human_presence_cat",
                    title="Frontal Face Presence (Haar Cascade)",
                    hole=0.4,
                    color="human_presence_cat",
                    color_discrete_map={"With Human": "#66BB6A", "No Human": "#FFA726"},
                )
                fig_human.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
                st.plotly_chart(fig_human, use_container_width=True)

        if "composition_style" in df.columns and df["composition_style"].notna().any():
            with c_c:
                fig_comp = px.pie(df, names="composition_style", title="Visual Composition Style", hole=0.4)
                fig_comp.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
                st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("---")
        st.subheader("Quick Workflow Navigation & Consolidated Export")
        q1, q2, q3, q4, q5 = st.columns(5)
        with q1:
            st.button("📂 2. Upload Creatives", on_click=navigate_to, args=("2. Upload Creatives",), use_container_width=True)
        with q2:
            st.button("🖼️ 3. Creative Library", on_click=navigate_to, args=("3. Creative Library",), use_container_width=True)
        with q3:
            st.button("📊 4. Ranked Findings", on_click=navigate_to, args=("4. Ranked Findings",), use_container_width=True)
        with q4:
            st.button("📝 5. Creative Brief", on_click=navigate_to, args=("5. Creative Brief",), use_container_width=True)
        with q5:
            consolidated_md = build_consolidated_report_markdown(
                df, st.session_state.findings, st.session_state.ingestion_result, st.session_state.is_synthetic
            )
            st.download_button(
                "📥 Consolidated Report (MD)",
                data=consolidated_md,
                file_name="consolidated_adcreative_report.md",
                mime="text/markdown",
                use_container_width=True,
            )



# -------------------------------------------------------------
# PAGE 2: UPLOAD CREATIVES
# -------------------------------------------------------------
elif nav_choice == "2. Upload Creatives":
    st.title("📂 Upload Creatives, Match Ad IDs & Validate Data")
    st.markdown(
        "Upload your campaign performance CSV (`ad_id, spend, impressions, clicks, conversions`) and ad creative image files. "
        "Every record and image is audited; invalid or unmatched entries are explicitly reported and never silently discarded."
    )

    dl_col1, dl_col2, _ = st.columns([1.2, 1.5, 1.5])
    with dl_col1:
        example_csv_str = generate_example_csv_content()
        st.download_button(
            label="📥 Download Example CSV Template",
            data=example_csv_str,
            file_name="ad_creative_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dl_col2:
        st.download_button(
            label="📦 Download Sample Images + CSV Bundle (.zip)",
            data=build_sample_upload_zip_bytes(),
            file_name="adcreative_sample_upload_bundle.zip",
            mime="application/zip",
            use_container_width=True,
        )

    st.markdown("---")

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        uploaded_csv = st.file_uploader(
            "1. Upload Ad Performance CSV (Required: ad_id, spend, impressions, clicks, conversions)",
            type=["csv"],
        )
        allow_vtc = st.checkbox(
            "Allow View-Through Conversions (permit conversions > clicks with warning)",
            value=False,
        )

    with u_col2:
        uploaded_images = st.file_uploader(
            "2. Upload Creative Images (PNG, JPG, JPEG, WEBP — filename stem matched to ad_id)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
        )

    # Immediate preview of newly staged uploaded image files
    if uploaded_images:
        with st.expander(f"🖼️ Preview Selected Image Files ({len(uploaded_images)} uploaded)", expanded=True):
            prev_cols = st.columns(min(len(uploaded_images), 6))
            for idx, img_file in enumerate(uploaded_images[:12]):
                with prev_cols[idx % len(prev_cols)]:
                    try:
                        img_file.seek(0)
                        pil_preview = Image.open(img_file)
                        st.image(pil_preview, caption=f"{img_file.name} ({pil_preview.width}×{pil_preview.height})", use_container_width=True)
                        img_file.seek(0)
                    except Exception as exc:
                        st.error(f"Corrupt image `{img_file.name}`: {exc}")
            if len(uploaded_images) > 12:
                st.caption(f"Showing first 12 of {len(uploaded_images)} uploaded images.")

    if uploaded_csv is not None:
        if st.button("🔍 Validate CSV, Match Images & Run Statistical Pipeline", type="primary"):
            with st.spinner("Validating CSV records and matching uploaded images..."):
                images_input = uploaded_images if uploaded_images else []
                res = ingest_ad_dataset(
                    uploaded_csv,
                    images_input,
                    allow_view_through_conversions=allow_vtc,
                )
                st.session_state.ingestion_result = res

                if not res.is_valid:
                    st.error("CSV Validation Failed — No records were discarded silently. Please fix the following errors:")
                    for e in res.errors:
                        st.markdown(f"- ❌ **{e}**")
                else:
                    st.success(f"CSV Validated: {len(res.df)} ad record(s) parsed.")

                    if res.warnings:
                        st.warning("Validation & Matching Warnings:")
                        for w in res.warnings:
                            st.markdown(f"- ⚠️ {w}")

                    with st.spinner("Running automated image feature extraction on matched creatives..."):
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
                                st.markdown(f"- ❌ {err}")

                        f_df = pd.DataFrame(feat_records) if feat_records else pd.DataFrame(columns=["ad_id"])
                        merged_df = pd.merge(res.df, f_df, on="ad_id", how="left")
                        findings = run_full_statistical_analysis(merged_df)

                        st.session_state.df_ads = merged_df
                        st.session_state.images_dict = res.matched_images
                        st.session_state.features_df = f_df
                        st.session_state.findings = findings
                        st.session_state.is_synthetic = False

                    st.success(
                        f"Pipeline Complete! Matched {len(res.matched_images)}/{len(res.df)} images and computed {len(findings)} statistical comparisons."
                    )

    if st.session_state.ingestion_result is not None:
        res = st.session_state.ingestion_result
        st.markdown("---")
        st.subheader("Data Ingestion & Matching Audit Report")

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("CSV Records", len(res.df))
        a2.metric("Matched Images", len(res.matched_images))
        a3.metric("CSV Records Missing Images", len(res.unmatched_records))
        a4.metric("Orphan Images (Not in CSV)", len(res.unmatched_images))

        if res.unmatched_records:
            st.warning(f"**CSV Records Missing Image Files ({len(res.unmatched_records)})**: `{', '.join(res.unmatched_records)}`")
        if res.unmatched_images:
            st.warning(f"**Uploaded Images Missing CSV Records ({len(res.unmatched_images)})**: `{', '.join(res.unmatched_images)}`")

        if not res.df.empty:
            st.markdown("#### Complete Ingested Record & Extraction Status Table")
            audit_df = st.session_state.df_ads if st.session_state.df_ads is not None else res.df.copy()
            audit_cols = ["ad_id", "spend", "impressions", "clicks", "conversions", "ctr", "cvr", "cpc", "cpa"]
            for extra_c in ["extraction_status", "extraction_error", "dominant_color_tone", "human_presence_cat", "aspect_ratio_cat", "composition_style"]:
                if extra_c in audit_df.columns:
                    audit_cols.append(extra_c)
            st.dataframe(audit_df[audit_cols], use_container_width=True, hide_index=True)

            st.markdown("#### Export & Download Center")
            ex1, ex2, ex3, ex4 = st.columns(4)
            with ex1:
                perf_only_cols = [c for c in ["ad_id", "spend", "impressions", "clicks", "conversions", "ctr", "cvr", "cpc", "cpa"] if c in res.df.columns]
                st.download_button(
                    "📥 Validated Performance CSV",
                    data=res.df[perf_only_cols].to_csv(index=False),
                    file_name="validated_performance_metrics.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with ex2:
                if st.session_state.features_df is not None and not st.session_state.features_df.empty:
                    feat_csv = st.session_state.features_df.drop(
                        columns=["color_palette_distribution", "feature_sources", "unavailable_features"], errors="ignore"
                    ).to_csv(index=False)
                else:
                    feat_csv = pd.DataFrame(columns=["ad_id"]).to_csv(index=False)
                st.download_button(
                    "📥 Extracted Features CSV",
                    data=feat_csv,
                    file_name="extracted_creative_features.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with ex3:
                export_csv = audit_df.drop(
                    columns=["color_palette_distribution", "feature_sources", "unavailable_features"], errors="ignore"
                ).to_csv(index=False)
                st.download_button(
                    "📥 Enriched Dataset CSV",
                    data=export_csv,
                    file_name="enriched_ad_performance_and_features.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with ex4:
                rep_md = build_consolidated_report_markdown(
                    audit_df, st.session_state.findings, res, st.session_state.is_synthetic
                )
                st.download_button(
                    "📥 Consolidated Report (MD)",
                    data=rep_md,
                    file_name="consolidated_adcreative_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            act1, act2 = st.columns(2)
            with act1:
                st.button("🖼️ Inspect & Compare in 3. Creative Library →", on_click=navigate_to, args=("3. Creative Library",), use_container_width=True)
            with act2:
                st.button("📊 View 4. Ranked Statistical Findings →", on_click=navigate_to, args=("4. Ranked Findings",), use_container_width=True)


# -------------------------------------------------------------
# PAGE 3: CREATIVE LIBRARY
# -------------------------------------------------------------
elif nav_choice == "3. Creative Library":
    st.title("🖼️ Creative Library, Attribute Inspector & Side-by-Side Comparison")

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                ⚠️ <strong>SYNTHETIC DEMO DATASET ACTIVE</strong>: Displaying automatically extracted features from synthetic test creatives.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.df_ads is None:
        st.info("No creatives loaded yet. Click '⚡ Load Synthetic Demo Dataset' in the sidebar or upload your own data in '2. Upload Creatives'.")
        if st.button("🚀 Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        df = st.session_state.df_ads
        images_dict = st.session_state.images_dict

        with st.expander("🔬 Feature Extraction Provenance & Methodology Notice (Direct vs. Heuristic vs. Frontal Face Cascade)", expanded=False):
            st.markdown(
                """
                **Strict Provenance & Transparency Guarantee**: Every extracted attribute is explicitly classified by its measurement provenance. We never claim semantic AI understanding when pixel measurements or heuristics are used:
                1. **Direct Image Measurements**:
                   - **Dimensions & Aspect Ratio** (`width`, `height`, `aspect_ratio`, `aspect_ratio_cat`, `format_suitability`): Exact pixel geometry from image headers.
                   - **Color & Tone Distribution** (`dominant_color_hex`, `dominant_color_name`, `dominant_color_tone`, `pct_warm_pixels`, `pct_cool_pixels`, `pct_neutral_pixels`, `color_palette_distribution`): Direct HSV pixel hue/saturation classification and deterministic K-Means ($k=3$) RGB clustering.
                   - **Brightness, Contrast & Colorfulness** (`brightness_score`, `contrast_score`, `colorfulness_score`, `saturation_score`): Exact ITU-R BT.601 luminance mean/RMS std-dev and Hasler-Süsstrunk opponent-color dispersion.
                2. **Heuristic Estimates (Not OCR / Not Semantic Object Detection)**:
                   - **Visual Complexity & Edge Density** (`edge_density_pct`, `visual_complexity`): Canny edge-pixel density proxy.
                   - **Text / Copy Density Proxy** (`text_density_score`, `text_density_cat`): Morphological horizontal Sobel stroke-width filter estimating text-like character regions *(Heuristic Estimate — Not Optical Character Recognition / OCR)*.
                   - **Visual Composition & Saliency Contours** (`composition_style`, `rule_of_thirds_score`, `center_focus_ratio`, `visual_symmetry_score`, `detected_object_regions`, `primary_subject_coverage_pct`): Sobel gradient energy distribution and Otsu saliency contours *(Heuristic Estimate — Not Semantic Object Detection)*.
                3. **Pretrained Frontal Face Cascade Detection (Frontal Faces Only)**:
                   - **Frontal Face Presence** (`face_count`, `has_human_presence`, `face_area_ratio`, `human_presence_cat`): OpenCV Pretrained Haar Frontal Face Cascade (`haarcascade_frontalface_default.xml` & `haarcascade_frontalface_alt2.xml`). *Note: Detects frontal human faces only; does not detect full-body poses, hands, or non-frontal profiles.*
                4. **Explicitly Unavailable Capabilities**:
                   - `ocr_text_extraction`, `semantic_object_detection`, `comprehensive_human_body_detection`, `brand_logo_recognition` (marked `unavailable` without external OCR/VLM dependencies).
                """
            )
            prov_c1, prov_c2 = st.columns([2, 1.3])
            with prov_c1:
                st.markdown("**Extracted Feature Provenance Map (`FEATURE_PROVENANCE_MAP`)**")
                prov_df = pd.DataFrame(
                    [{"Feature Name": k, "Measurement Provenance": v} for k, v in FEATURE_PROVENANCE_MAP.items()]
                )
                st.dataframe(prov_df, use_container_width=True, hide_index=True, height=220)
            with prov_c2:
                st.markdown("**Unavailable Capabilities (`UNAVAILABLE_CAPABILITIES`)**")
                unavail_df = pd.DataFrame(
                    [{"Capability": k, "Status & Fallback": v} for k, v in UNAVAILABLE_CAPABILITIES.items()]
                )
                st.dataframe(unavail_df, use_container_width=True, hide_index=True, height=220)


        with st.expander("🏆 Top & Bottom Performing Creatives by Metric (Observational Ad-Level Ranking)", expanded=False):
            st.caption(
                "Observational ranking of individual creatives. High or low performance on a single creative may reflect audience targeting, placement, or low denominator volume rather than visual attributes alone."
            )
            perf_metric_col = st.selectbox(
                "Rank Creatives By Metric",
                ["ctr", "cvr", "cpc", "cpa"],
                format_func=lambda m: {"ctr": "CTR (Higher is better)", "cvr": "CVR (Higher is better)", "cpc": "CPC (Lower is better)", "cpa": "CPA (Lower is better)"}[m],
                key="top_bottom_metric_sel",
            )
            valid_perf_df = df.dropna(subset=[perf_metric_col]).copy()
            if not valid_perf_df.empty:
                asc_order = perf_metric_col in ("cpc", "cpa")
                sorted_perf = valid_perf_df.sort_values(perf_metric_col, ascending=asc_order)
                tb_c1, tb_c2 = st.columns(2)
                disp_cols = [c for c in ["ad_id", "spend", "impressions", "clicks", "conversions", "ctr", "cvr", "cpc", "cpa", "dominant_color_tone", "human_presence_cat"] if c in sorted_perf.columns]
                with tb_c1:
                    st.markdown("**Top 5 Performing Creatives**")
                    st.dataframe(sorted_perf.head(5)[disp_cols], use_container_width=True, hide_index=True)
                with tb_c2:
                    st.markdown("**Bottom 5 Performing Creatives**")
                    st.dataframe(sorted_perf.tail(5).iloc[::-1][disp_cols], use_container_width=True, hide_index=True)


        # Side-by-Side Creative Comparison Tool
        if len(df) >= 2:
            with st.expander("⚖️ Side-by-Side Creative Comparison (Compare Visual Attributes & Performance)", expanded=False):
                ad_id_list = df["ad_id"].astype(str).tolist()
                cmp_col1, cmp_col2 = st.columns(2)
                with cmp_col1:
                    sel_a = st.selectbox("Select Creative A", ad_id_list, index=0, key="cmp_ad_a")
                with cmp_col2:
                    default_b_idx = min(1, len(ad_id_list) - 1)
                    sel_b = st.selectbox("Select Creative B", ad_id_list, index=default_b_idx, key="cmp_ad_b")

                row_a = df[df["ad_id"].astype(str) == sel_a].iloc[0]
                row_b = df[df["ad_id"].astype(str) == sel_b].iloc[0]

                img_c1, img_c2 = st.columns(2)
                with img_c1:
                    st.markdown(f"#### Creative A: `{sel_a}`")
                    if sel_a in images_dict:
                        st.image(images_dict[sel_a], use_container_width=True)
                    else:
                        st.warning(f"No image matched for `{sel_a}`")
                with img_c2:
                    st.markdown(f"#### Creative B: `{sel_b}`")
                    if sel_b in images_dict:
                        st.image(images_dict[sel_b], use_container_width=True)
                    else:
                        st.warning(f"No image matched for `{sel_b}`")

                comparison_rows = [
                    {"Dimension / Metric": "Spend ($)", f"Creative A ({sel_a})": _format_currency(row_a.get("spend")), f"Creative B ({sel_b})": _format_currency(row_b.get("spend"))},
                    {"Dimension / Metric": "Impressions", f"Creative A ({sel_a})": f"{int(row_a.get('impressions', 0)):,}", f"Creative B ({sel_b})": f"{int(row_b.get('impressions', 0)):,}"},
                    {"Dimension / Metric": "Clicks", f"Creative A ({sel_a})": f"{int(row_a.get('clicks', 0)):,}", f"Creative B ({sel_b})": f"{int(row_b.get('clicks', 0)):,}"},
                    {"Dimension / Metric": "Conversions", f"Creative A ({sel_a})": f"{int(row_a.get('conversions', 0)):,}", f"Creative B ({sel_b})": f"{int(row_b.get('conversions', 0)):,}"},
                    {"Dimension / Metric": "CTR (Clicks / Imp)", f"Creative A ({sel_a})": _format_rate(row_a.get("ctr")), f"Creative B ({sel_b})": _format_rate(row_b.get("ctr"))},
                    {"Dimension / Metric": "CVR (Conv / Clicks)", f"Creative A ({sel_a})": _format_rate(row_a.get("cvr")), f"Creative B ({sel_b})": _format_rate(row_b.get("cvr"))},
                    {"Dimension / Metric": "CPC ($ / Click)", f"Creative A ({sel_a})": _format_currency(row_a.get("cpc")), f"Creative B ({sel_b})": _format_currency(row_b.get("cpc"))},
                    {"Dimension / Metric": "CPA ($ / Conv)", f"Creative A ({sel_a})": _format_currency(row_a.get("cpa")), f"Creative B ({sel_b})": _format_currency(row_b.get("cpa"))},
                    {"Dimension / Metric": "Dominant Color & Tone", f"Creative A ({sel_a})": f"{row_a.get('dominant_color_name', 'N/A')} ({row_a.get('dominant_color_hex', '')} - {row_a.get('dominant_color_tone', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('dominant_color_name', 'N/A')} ({row_b.get('dominant_color_hex', '')} - {row_b.get('dominant_color_tone', 'N/A')})"},
                    {"Dimension / Metric": "Human Presence (Haar Cascade)", f"Creative A ({sel_a})": f"{row_a.get('human_presence_cat', 'N/A')} (Faces: {row_a.get('face_count', 0)})", f"Creative B ({sel_b})": f"{row_b.get('human_presence_cat', 'N/A')} (Faces: {row_b.get('face_count', 0)})"},
                    {"Dimension / Metric": "Dimensions & Aspect Ratio", f"Creative A ({sel_a})": f"{row_a.get('width', 'N/A')}×{row_a.get('height', 'N/A')} ({row_a.get('aspect_ratio_cat', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('width', 'N/A')}×{row_b.get('height', 'N/A')} ({row_b.get('aspect_ratio_cat', 'N/A')})"},
                    {"Dimension / Metric": "Brightness Score (BT.601)", f"Creative A ({sel_a})": f"{row_a.get('brightness_score', 'N/A')} ({row_a.get('brightness_cat', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('brightness_score', 'N/A')} ({row_b.get('brightness_cat', 'N/A')})"},
                    {"Dimension / Metric": "Contrast Score (RMS)", f"Creative A ({sel_a})": f"{row_a.get('contrast_score', 'N/A')} ({row_a.get('contrast_cat', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('contrast_score', 'N/A')} ({row_b.get('contrast_cat', 'N/A')})"},
                    {"Dimension / Metric": "Colorfulness & Saturation", f"Creative A ({sel_a})": f"{row_a.get('colorfulness_score', 'N/A')} ({row_a.get('colorfulness_cat', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('colorfulness_score', 'N/A')} ({row_b.get('colorfulness_cat', 'N/A')})"},
                    {"Dimension / Metric": "Composition Style", f"Creative A ({sel_a})": f"{row_a.get('composition_style', 'N/A')} (Center: {row_a.get('center_focus_ratio', 'N/A')}%, RoT: {row_a.get('rule_of_thirds_score', 'N/A')})", f"Creative B ({sel_b})": f"{row_b.get('composition_style', 'N/A')} (Center: {row_b.get('center_focus_ratio', 'N/A')}%, RoT: {row_b.get('rule_of_thirds_score', 'N/A')})"},
                    {"Dimension / Metric": "Visual Complexity & Text Proxy", f"Creative A ({sel_a})": f"{row_a.get('visual_complexity', 'N/A')} | {row_a.get('text_density_cat', 'N/A')} ({row_a.get('text_density_score', 'N/A')}%)", f"Creative B ({sel_b})": f"{row_b.get('visual_complexity', 'N/A')} | {row_b.get('text_density_cat', 'N/A')} ({row_b.get('text_density_score', 'N/A')}%)"},
                ]
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

        f1, f2, f3, f4, f5 = st.columns(5)
        tones = ["All"] + sorted([str(x) for x in df["dominant_color_tone"].dropna().unique()]) if "dominant_color_tone" in df.columns else ["All"]
        humans = ["All"] + sorted([str(x) for x in df["human_presence_cat"].dropna().unique()]) if "human_presence_cat" in df.columns else ["All"]
        aspects = ["All"] + sorted([str(x) for x in df["aspect_ratio_cat"].dropna().unique()]) if "aspect_ratio_cat" in df.columns else ["All"]
        comps = ["All"] + sorted([str(x) for x in df["composition_style"].dropna().unique()]) if "composition_style" in df.columns else ["All"]
        sort_options = ["Default Order", "CTR (High → Low)", "CVR (High → Low)", "CPA (Low → High)", "Spend (High → Low)", "Brightness (High → Low)"]

        tone_filter = f1.selectbox("Color Tone", tones)
        human_filter = f2.selectbox("Human Presence", humans)
        aspect_filter = f3.selectbox("Aspect Ratio", aspects)
        comp_filter = f4.selectbox("Composition Style", comps)
        sort_by = f5.selectbox("Sort Gallery By", sort_options)

        filtered_df = df.copy()
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
        elif sort_by == "CVR (High → Low)" and "cvr" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("cvr", ascending=False, na_position="last")
        elif sort_by == "CPA (Low → High)" and "cpa" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("cpa", ascending=True, na_position="last")
        elif sort_by == "Spend (High → Low)" and "spend" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("spend", ascending=False, na_position="last")
        elif sort_by == "Brightness (High → Low)" and "brightness_score" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("brightness_score", ascending=False, na_position="last")

        st.caption(f"Showing {len(filtered_df)} of {len(df)} creative record(s)")

        if filtered_df.empty:
            st.warning("No creatives match the currently selected filters. Try resetting one or more filter dropdowns to 'All'.")
        else:
            cols_per_row = 3
            rows = [filtered_df.iloc[i : i + cols_per_row] for i in range(0, len(filtered_df), cols_per_row)]

            for row in rows:
                grid_cols = st.columns(cols_per_row)
                for idx, (_, ad) in enumerate(row.iterrows()):
                    ad_id = str(ad["ad_id"])
                    with grid_cols[idx]:
                        with st.container():
                            if ad_id in images_dict:
                                st.image(images_dict[ad_id], use_container_width=True)
                            else:
                                st.warning(f"⚠️ Missing Image File for `{ad_id}`")

                            ext_status = ad.get("extraction_status", "unmatched")
                            status_badge = "✅ Extracted" if ext_status == "success" else (f"❌ Error: {ad.get('extraction_error')}" if ext_status == "error" else "⚠️ No Image")
                            st.markdown(f"**{ad_id}** &bull; <small>{status_badge}</small>", unsafe_allow_html=True)

                            hex_c = ad.get("dominant_color_hex", "#888888")
                            if pd.isna(hex_c):
                                hex_c = "#888888"
                            color_name = ad.get("dominant_color_name", "N/A")
                            tone = ad.get("dominant_color_tone", "N/A")
                            human = ad.get("human_presence_cat", "N/A")
                            aspect = ad.get("aspect_ratio_cat", "N/A")

                            st.markdown(
                                f"""
                                <div style="font-size:0.85em; margin-bottom:8px;">
                                    <span style="display:inline-block; width:12px; height:12px; background-color:{hex_c}; border-radius:50%; margin-right:4px; border:1px solid #ccc;"></span>
                                    <strong>{color_name}</strong> ({tone}) | <strong>{human}</strong> | {aspect}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            ctr_txt = _format_rate(ad.get("ctr"))
                            cvr_txt = _format_rate(ad.get("cvr"))
                            cpc_txt = _format_currency(ad.get("cpc"))
                            cpa_txt = _format_currency(ad.get("cpa"))
                            st.markdown(
                                f"📊 **CTR**: {ctr_txt} | **CVR**: {cvr_txt}<br>💰 **CPC**: {cpc_txt} | **CPA**: {cpa_txt}",
                                unsafe_allow_html=True,
                            )

                            with st.expander("🔍 Inspect All Extracted Features"):
                                st.write(f"- **Dimensions**: {ad.get('width', 'N/A')}×{ad.get('height', 'N/A')} px ({ad.get('megapixels', 'N/A')} MP, AR={ad.get('aspect_ratio', 'N/A')})")
                                palette = ad.get("color_palette_distribution")
                                if isinstance(palette, list) and palette:
                                    pal_str = ", ".join([f"{p['color_name']} ({p['hex_code']}: {p['percentage']}%)" for p in palette])
                                    st.write(f"- **Color Distribution Palette**: {pal_str}")
                                st.write(f"- **Brightness**: {ad.get('brightness_score', 'N/A')} / 100 ({ad.get('brightness_cat', 'N/A')})")
                                st.write(f"- **Contrast**: {ad.get('contrast_score', 'N/A')} / 100 ({ad.get('contrast_cat', 'N/A')})")
                                st.write(f"- **Colorfulness & Saturation**: {ad.get('colorfulness_score', 'N/A')} ({ad.get('colorfulness_cat', 'N/A')}), Sat={ad.get('saturation_score', 'N/A')}%")
                                st.write(f"- **Visual Composition**: {ad.get('composition_style', 'N/A')} (Rule-of-Thirds={ad.get('rule_of_thirds_score', 'N/A')}, Center Focus={ad.get('center_focus_ratio', 'N/A')}%, Symmetry={ad.get('visual_symmetry_score', 'N/A')}%)")
                                st.write(f"- **Edge Complexity & Saliency**: {ad.get('edge_density_pct', 'N/A')}% edges ({ad.get('visual_complexity', 'N/A')}), Salient Regions={ad.get('detected_object_regions', 'N/A')} ({ad.get('primary_subject_coverage_pct', 'N/A')}% area)")
                                st.write(f"- **Pretrained Face Detection**: {ad.get('face_count', 0)} face(s) ({ad.get('human_presence_cat', 'N/A')}, Area Ratio={ad.get('face_area_ratio', 0.0)})")
                                st.write(f"- **Typography / Copy Proxy**: {ad.get('text_density_score', 'N/A')}% coverage ({ad.get('text_density_cat', 'N/A')})")
                                st.caption(f"Method: {ad.get('feature_extraction_method', 'N/A')}")
                            st.markdown("---")

        nav_b1, nav_b2 = st.columns(2)
        with nav_b1:
            export_lib_csv = df.drop(columns=["color_palette_distribution", "feature_sources"], errors="ignore").to_csv(index=False)
            st.download_button(
                "📥 Export Creative Feature Table (CSV)",
                data=export_lib_csv,
                file_name="creative_feature_library.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with nav_b2:
            st.button("📊 Analyze Attribute Associations in 4. Ranked Findings →", on_click=navigate_to, args=("4. Ranked Findings",), use_container_width=True)


# -------------------------------------------------------------
# PAGE 4: RANKED FINDINGS
# -------------------------------------------------------------
elif nav_choice == "4. Ranked Findings":
    st.title("📊 Ranked Statistical Findings & Evidence Engine")

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                ⚠️ <strong>SYNTHETIC DEMO DATASET ACTIVE</strong>: Statistical findings below are computed live on the synthetic demonstration dataset.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        Every visual attribute is evaluated against **CTR, CVR, CPC, and CPA**.
        Multiple comparisons are corrected using the **Benjamini-Hochberg False Discovery Rate (FDR)** procedure.
        No finding is labeled *Supported association* without meeting strict adjusted $q$-value, confidence interval, and sample size criteria.
        """
    )

    if not st.session_state.findings:
        st.info("No findings available. Load the synthetic demo dataset in the sidebar or upload your own data in '2. Upload Creatives'.")
        if st.button("🚀 Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        findings: List[Finding] = st.session_state.findings

        with st.expander("ℹ️ Transparent Evidence Classification Rules & Composite Ranking Formula", expanded=False):
            st.markdown(
                """
                ### 1. Transparent Evidence Classification Rules
                - 🟢 **Supported association**: Benjamini-Hochberg adjusted $q_{\\text{FDR}} < 0.05$, minimum group sample size $N \\ge 4$ creatives per group (or $N \\ge 6$ for continuous), 95% confidence interval excludes zero, and relative effect $\\ge 8\\%$ (or $|\\rho| \\ge 0.40$).
                - 🟡 **Preliminary**: Nominal $p < 0.05$ before multiple-testing correction, OR $q_{\\text{FDR}} < 0.15$ with relative effect $\\ge 10\\%$ and $N \\ge 3$ per group. Warrants controlled A/B testing.
                - 🟣 **Underpowered**: Group sample size $N < 3$ creatives in at least one group (or $N < 6$ total for continuous). Sampling variance is too high to draw reliable conclusions.
                - ⚪ **No clear association**: Adequate sample size ($N \\ge 5$ per group), negligible effect size ($|\\text{Uplift}| < 6\\%$ or $|\\rho| < 0.15$), and $p > 0.20$. *(Note: Absence of evidence is not evidence of absence).*
                - 🔴 **Unsupported**: Non-significant ($p \\ge 0.10$) with insufficient evidence or counter-directional noise.

                ### 2. Composite Ranking Score
                $$\\text{Rank Score} = \\left(0.50 \\cdot \\min(-\\log_{10}(q_{\\text{FDR}} + 10^{-8}), 6.0) + 0.35 \\cdot \\min\\left(\\frac{|\\text{Uplift}\\%|}{15.0}, 4.0\\right) + 0.15 \\cdot \\min(\\sqrt{N}, 4.0)\\right) \\times M_{\\text{tier}}$$
                where $M_{\\text{tier}}$ weights Supported ($2.0\\times$), Preliminary ($1.4\\times$), Underpowered ($0.7\\times$), No clear association ($0.5\\times$), and Unsupported ($0.3\\times$).
                """
            )

        # Export & Navigation Row
        exp_c1, exp_c2, exp_c3 = st.columns(3)
        with exp_c1:
            export_df = findings_to_export_df(findings)
            st.download_button(
                "📥 Export Ranked Findings (CSV)",
                data=export_df.to_csv(index=False),
                file_name="ranked_statistical_findings.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with exp_c2:
            findings_json = json.dumps([f.to_dict() for f in findings], indent=2)
            st.download_button(
                "📥 Export Ranked Findings (JSON)",
                data=findings_json,
                file_name="ranked_statistical_findings.json",
                mime="application/json",
                use_container_width=True,
            )
        with exp_c3:
            st.button("📝 Synthesize 5. Creative Brief from Findings →", on_click=navigate_to, args=("5. Creative Brief",), use_container_width=True)

        st.markdown("---")

        c_m, c_e, c_t = st.columns(3)
        metric_filter = c_m.selectbox("Filter by Outcome Metric", ["All", "CTR", "CVR", "CPC", "CPA"])
        evidence_filter = c_e.selectbox(
            "Filter by Evidence Classification",
            ["All", "Supported association", "Preliminary", "Underpowered", "No clear association", "Unsupported"],
        )
        attr_type_filter = c_t.selectbox("Filter by Attribute Type", ["All", "categorical", "continuous"])

        filtered_findings = findings
        if metric_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.outcome_metric == metric_filter]
        if evidence_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.evidence_classification == evidence_filter]
        if attr_type_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.attribute_type == attr_type_filter]

        st.caption(f"Displaying {len(filtered_findings)} of {len(findings)} tested attribute-metric hypotheses")

        if filtered_findings:
            st.subheader("95% Confidence Interval Forest Plot (Matched by Estimand)")
            fp_col1, fp_col2 = st.columns([2, 2])
            with fp_col1:
                fp_estimand_mode = st.selectbox(
                    "Select Estimand for Forest Plot (ensures commensurate x-axis units)",
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
                x_axis_label = "Ad-Level Mean CTR Difference (Group A - Group B) with 95% Welch-Satterthwaite t CI"
            elif "CVR" in fp_estimand_mode:
                plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CVR"][:10]
                x_axis_label = "Ad-Level Mean CVR Difference (Group A - Group B) with 95% Welch-Satterthwaite t CI"
            elif "CPC" in fp_estimand_mode:
                plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CPC"][:10]
                x_axis_label = "Ad-Level Mean CPC Difference ($/Click, Group A - Group B) with 95% Welch-Satterthwaite t CI"
            elif "CPA" in fp_estimand_mode:
                plot_findings = [f for f in filtered_findings if f.attribute_type == "categorical" and f.outcome_metric == "CPA"][:10]
                x_axis_label = "Ad-Level Mean CPA Difference ($/Conv, Group A - Group B) with 95% Welch-Satterthwaite t CI"
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
                        error_x=dict(type="data", array=err_high, arrayminus=err_low, color="#1E88E5", thickness=2, width=6),
                        marker=dict(size=10, color="#1565C0"),
                    )
                )
                forest_fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="Null Effect (0)")
                forest_fig.update_layout(
                    xaxis_title=x_axis_label,
                    yaxis_title="Tested Visual Hypothesis",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=340,
                )
                st.plotly_chart(forest_fig, use_container_width=True)
            else:
                st.caption("No findings match both the current filters and the selected Forest Plot estimand.")

        st.markdown("---")

        for rank_idx, f in enumerate(filtered_findings):
            badge_class = "badge-neutral"
            if f.evidence_classification == "Supported association":
                badge_class = "badge-supported"
            elif f.evidence_classification == "Preliminary":
                badge_class = "badge-preliminary"
            elif f.evidence_classification == "Underpowered":
                badge_class = "badge-underpowered"
            elif f.evidence_classification == "Unsupported":
                badge_class = "badge-unsupported"

            with st.container():
                st.markdown(
                    f"""
                    <div class="finding-box">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-size:1.1em; font-weight:700;">#{rank_idx + 1} &bull; {f.attribute} &rarr; <span style="color:#1E88E5;">{f.outcome_metric}</span></span>
                            <span>
                                <span class="{badge_class}">{f.evidence_classification}</span>
                                <span style="font-size:0.85em; color:#757575; margin-left:8px;">Rank Score: {f.rank_score:.2f}</span>
                            </span>
                        </div>
                        <p style="font-size:1.02em; margin-bottom:6px; color:#212121;">
                            <strong>Direction of Association</strong>: {f.direction_of_association}
                        </p>
                        <p style="font-size:0.9em; margin-bottom:12px; color:#424242;">
                            <strong>Statistical Method</strong>: <code>{f.statistical_method}</code>
                        </p>
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
                        st.write(f"- OLS / WLS Slope: `{f.effect_size.get('ols_slope', 0.0):.5f}` / `{f.effect_size.get('wls_slope_exposure_weighted', 0.0):.5f}`")

                with c2:
                    st.markdown("**Sample Size & Exposure**")
                    if f.attribute_type == "categorical":
                        st.write(f"- **Creatives (Group A `{f.group_a}`)**: **{f.sample_sizes.get('creatives_group_a', 0)}** ads")
                        st.write(f"- **Creatives (Group B `{f.group_b}`)**: **{f.sample_sizes.get('creatives_group_b', 0)}** ads")
                        if "impressions_group_a" in f.sample_sizes:
                            st.write(f"- Exposure (Impressions): `{f.sample_sizes['impressions_group_a']:,}` vs `{f.sample_sizes['impressions_group_b']:,}`")
                        if "clicks_group_a" in f.sample_sizes:
                            st.write(f"- Exposure (Clicks): `{f.sample_sizes['clicks_group_a']:,}` vs `{f.sample_sizes['clicks_group_b']:,}`")
                        if "conversions_group_a" in f.sample_sizes:
                            st.write(f"- Exposure (Conversions): `{f.sample_sizes['conversions_group_a']:,}` vs `{f.sample_sizes['conversions_group_b']:,}`")
                    else:
                        st.write(f"- **Analyzed Creatives**: **{f.sample_sizes.get('creatives_count', 0)}** ads")
                        st.write(f"- Exposure (Impressions): `{f.sample_sizes.get('total_impressions', 0):,}`")
                        if f.sample_sizes.get("total_clicks", 0) > 0:
                            st.write(f"- Exposure (Clicks): `{f.sample_sizes.get('total_clicks', 0):,}`")

                with c3:
                    st.markdown("**Confidence Interval & Estimand**")
                    estimand_lbl = f.uncertainty.get("estimand", "Point Estimate Difference")
                    ci_l = f.uncertainty.get("ci_95_lower", 0.0)
                    ci_u = f.uncertainty.get("ci_95_upper", 0.0)
                    st.write(f"- **Estimand**: {estimand_lbl}")
                    st.write(f"- **95% CI**: `[{ci_l:.4f}, {ci_u:.4f}]`")
                    st.write(f"- Standard Error: `{f.uncertainty.get('standard_error', 0.0):.4f}`")

                with c4:
                    st.markdown("**Multiple-Testing P-Values**")
                    st.write(f"- Raw p-value: `{f.uncertainty.get('raw_p_value', 1.0):.4f}`")
                    st.write(f"- **Adjusted FDR q**: **{f.uncertainty.get('fdr_q_value', 1.0):.4f}**")
                    if "bonferroni_p" in f.uncertainty:
                        st.write(f"- Bonferroni p: `{f.uncertainty.get('bonferroni_p', 1.0):.4f}`")

                if f.traceable_ad_ids:
                    with st.expander("🔗 View Traceable Ad IDs in Each Group"):
                        for grp_key, ids_list in f.traceable_ad_ids.items():
                            st.write(f"**{grp_key}** ({len(ids_list)} ads): `{', '.join(ids_list)}`")

                st.markdown(
                    f"""
                        <div style="font-size:0.85em; color:#616161; margin-top:8px; border-top:1px dashed #E0E0E0; padding-top:6px;">
                            <strong>Limitations & Governance</strong>: {f.limitations}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.session_state.df_ads is not None:
            st.markdown("---")
            st.subheader("Confounding & Metadata Stratification Check")
            conf_reports = investigate_confounding(st.session_state.df_ads, findings)
            if conf_reports:
                st.dataframe(pd.DataFrame(conf_reports), use_container_width=True, hide_index=True)


# -------------------------------------------------------------
# PAGE 5: CREATIVE BRIEF
# -------------------------------------------------------------
elif nav_choice == "5. Creative Brief":
    st.title("📝 Data-Grounded Creative Brief & Experimental Roadmap")

    if st.session_state.is_synthetic:
        st.markdown(
            """
            <div class="synthetic-banner">
                ⚠️ <strong>SYNTHETIC DEMO DATASET ACTIVE</strong>: Recommendations below are synthesized dynamically from the synthetic dataset findings.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        Synthesizes empirical statistical findings into a structured creative brief.
        **Zero hardcoded results**: Every recommendation and A/B test row below is dynamically constructed from the active dataset's statistical engine output.
        """
    )

    if not st.session_state.findings:
        st.info("No findings available. Load the synthetic demo dataset in the sidebar or upload your own data in '2. Upload Creatives'.")
        if st.button("🚀 Load Synthetic Demo Dataset", type="primary"):
            load_demo_dataset()
            st.rerun()
    else:
        brief = generate_creative_brief(
            findings=st.session_state.findings,
            df_metrics=st.session_state.df_ads,
            dataset_is_synthetic=st.session_state.is_synthetic,
        )

        cb_col1, cb_col2, cb_col3 = st.columns(3)
        with cb_col1:
            st.download_button(
                label="📥 Export Grounded Creative Brief (Markdown)",
                data=brief["full_markdown"],
                file_name="executive_creative_brief.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with cb_col2:
            if brief["ab_test_matrix"]:
                ab_csv = pd.DataFrame(brief["ab_test_matrix"]).to_csv(index=False)
                st.download_button(
                    label="📥 Export A/B Test Roadmap (CSV)",
                    data=ab_csv,
                    file_name="ab_test_experimental_matrix.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        with cb_col3:
            st.button("⬅️ Back to 4. Ranked Statistical Findings", on_click=navigate_to, args=("4. Ranked Findings",), use_container_width=True)

        st.markdown("---")

        b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs(
            ["📋 Supported vs. Preliminary Evidence", "✅ Grounded DOs & Cautions", "🧪 Dynamic A/B Test Matrix", "📄 Full Markdown Brief"]
        )

        with b_tab1:
            st.subheader("Confirmed Statistical Associations (Supported: FDR q < 0.05)")
            if brief["supported_findings"]:
                for f in brief["supported_findings"]:
                    st.success(
                        f"**{f.attribute} &rarr; {f.outcome_metric}**: {f.direction_of_association}\n\n"
                        f"- **Method**: {f.statistical_method} | **Estimand**: {f.uncertainty.get('estimand', '')} | **95% CI**: [{f.uncertainty['ci_95_lower']:.4f}, {f.uncertainty['ci_95_upper']:.4f}] | **Adjusted FDR q**: {f.uncertainty['fdr_q_value']:.4f}\n"
                        f"- **Limitations**: {f.limitations}"
                    )
            else:
                st.info("No tested attributes reached Supported association (FDR q < 0.05 with N >= 4 per group) in the current dataset.")

            st.subheader("Preliminary & Underpowered Hypotheses (Require Split-Test Verification)")
            prelim_and_under = brief["preliminary_findings"] + brief["underpowered_findings"]
            if prelim_and_under:
                for f in prelim_and_under[:6]:
                    st.warning(
                        f"**[{f.evidence_classification}] {f.attribute} &rarr; {f.outcome_metric}**: {f.direction_of_association} "
                        f"(Method: {f.statistical_method}, Raw p = {f.uncertainty['raw_p_value']:.4f}, Adjusted FDR q = {f.uncertainty['fdr_q_value']:.4f})"
                    )
            else:
                st.write("No preliminary or underpowered hypotheses queued.")

        with b_tab2:
            st.subheader("Data-Grounded Guidelines")
            c_do, c_dont = st.columns(2)

            with c_do:
                st.markdown("### ✅ Recommended Explorations (DOs)")
                for item in brief["actionable_dos"]:
                    st.markdown(f"- {item}")

            with c_dont:
                st.markdown("### ⚠️ Cautions & Null Findings (DON'Ts)")
                for item in brief["actionable_donts"]:
                    st.markdown(f"- {item}")

        with b_tab3:
            st.subheader("Prioritized A/B Test Matrix (Synthesized from Active Findings)")
            if brief["ab_test_matrix"]:
                exp_df = pd.DataFrame(brief["ab_test_matrix"])
                st.dataframe(exp_df, use_container_width=True, hide_index=True)
            else:
                st.info("Insufficient findings to populate A/B test matrix.")

        with b_tab4:
            st.subheader("Complete Markdown Creative Brief")
            st.text_area("Markdown Source", brief["full_markdown"], height=420)
