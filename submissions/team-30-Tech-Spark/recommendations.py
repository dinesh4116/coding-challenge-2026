"""
AdCreative Intelligence - Recommendations & Analytical Reporting Engine
- Translates empirical statistical findings into structured creative experiments.
- Categorizes recommendations into:
    A. Recommendations based on observed evidence (Supported association)
    B. New hypotheses requiring testing (Preliminary evidence)
    C. Recommendations blocked by insufficient evidence (Underpowered / No association)
- Generates downloadable Analytical Reports in Markdown, CSV, and multi-page executive PDF formats.
- Watermarks synthetic datasets prominently so synthetic demo data is never confused with production data.
"""

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from statistical_engine import Finding, compute_aggregate_kpis


def generate_recommendations(
    findings: List[Finding],
    df_metrics: Optional[pd.DataFrame] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Translates statistical findings into actionable creative experiment recommendations.
    Strictly categorizes recommendations into Category A, Category B, and Category C.
    """
    cat_a: List[Dict[str, Any]] = []
    cat_b: List[Dict[str, Any]] = []
    cat_c: List[Dict[str, Any]] = []

    for idx, f in enumerate(findings):
        attr = f.attribute
        metric = f.outcome_metric
        uplift = f.effect_size.get("relative_uplift_pct", 0.0)
        ci_l = f.uncertainty.get("ci_95_lower", 0.0)
        ci_u = f.uncertainty.get("ci_95_upper", 0.0)
        q_val = f.uncertainty.get("fdr_q_value", 1.0)
        raw_p = f.uncertainty.get("raw_p_value", 1.0)
        ev_class = f.evidence_classification

        # Tailored variation and hypothesis generation based on attribute
        if "Warm" in attr or "dominant_color_tone" in attr:
            var_title = "Warm Palette Shift (Coral / Amber / Sunset)"
            hyp = f"Transitioning hero ad color palettes toward warm hues will replicate observed {uplift:+.1f}% {metric} advantage."
            ctrl = "Current Cool / Monochromatic Palette"
            variant = "Vibrant Warm Palette with Amber/Coral Accent"
        elif "Human" in attr or "human_presence_cat" in attr:
            var_title = "Human Subject Integration"
            hyp = f"Incorporating relatable human facial expressions and lifestyle context will improve {metric} engagement."
            ctrl = "Product-Only Still Composition"
            variant = "Product in Hands of Expressive Human Subject"
        elif "Square" in attr or "aspect_ratio_cat" in attr:
            var_title = "1:1 Square Feed Optimization"
            hyp = f"Deploying native 1:1 Square creative framing will capture higher feed viewport real-estate for {metric} uplift."
            ctrl = "Standard Landscape or Story Crop"
            variant = "Native 1:1 Square Optimized Creative"
        elif "Clean / Minimal" in attr or "visual_complexity" in attr:
            var_title = "Visual De-Cluttering & Minimalist Hierarchy"
            hyp = f"Eliminating secondary graphic clutter and focusing on a single focal element will reduce friction and lift {metric}."
            ctrl = "Multi-Element Dense Banner"
            variant = "Clean Minimalist Hero Layout (<6% Edge Density)"
        elif "Minimal Copy" in attr or "text_density_cat" in attr:
            var_title = "Copy Reduction & Headline Clarity"
            hyp = f"Limiting on-image copy coverage to concise headline and bold CTA will improve reader comprehension and {metric}."
            ctrl = "Text-Heavy Multi-Bullet Layout"
            variant = "High-Contrast Single Value Proposition (<15% Copy)"
        elif "brightness" in attr.lower():
            var_title = "Luminance Contrast Calibration"
            hyp = f"Calibrating background brightness into optimal range will elevate visual salience and improve {metric}."
            ctrl = "Subdued Mid-Tone Luminance"
            variant = "High-Luminance Hero Frame (>65 BT.601 Score)"
        else:
            var_title = f"Creative Variation for {attr}"
            hyp = f"Testing variations in {attr} to evaluate its association with {metric}."
            ctrl = f"Baseline {attr} Variant"
            variant = f"Optimized {attr} Variant"

        # Measurement plan estimation
        # Required sample size proxy based on baseline metric rate
        base_rate = f.effect_size.get("rate_group_b", 0.02)
        if base_rate and base_rate > 0:
            req_impressions = max(int(16.0 / (base_rate * max(abs(uplift) / 100.0, 0.05)**2)), 15000)
        else:
            req_impressions = 25000

        rec_entry = {
            "rec_id": f"REC-{idx+1:02d}",
            "attribute": attr,
            "outcome_metric": metric,
            "proposed_creative_variation": var_title,
            "control_asset": ctrl,
            "variant_asset": variant,
            "hypothesis": hyp,
            "success_metric": f"Primary: {metric} | Secondary Guardrail: CPA / CPC",
            "measurement_plan": (
                f"Controlled 50/50 A/B split test with uniform audience targeting and bidding. "
                f"Minimum target: {req_impressions:,} impressions per variant (~7-14 days duration)."
            ),
            "relevant_finding": {
                "attribute": attr,
                "outcome_metric": metric,
                "effect_size": f.effect_size,
                "ci_95": f"[{ci_l:.4f}, {ci_u:.4f}]",
                "raw_p": raw_p,
                "fdr_q": q_val,
                "evidence_classification": ev_class,
                "traceable_ads": f.traceable_ad_ids,
            },
            "important_limitations": (
                f"Non-causal observational observation. "
                f"Untested recommendation: does NOT guarantee performance uplift in future campaigns. "
                f"{f.limitations}"
            ),
        }

        if ev_class == "Supported association":
            cat_a.append({**rec_entry, "category": "A. Recommendations based on observed evidence"})
        elif ev_class in ("Preliminary", "Preliminary evidence"):
            cat_b.append({**rec_entry, "category": "B. New hypotheses requiring testing"})
        else:
            cat_c.append({
                **rec_entry,
                "category": "C. Recommendations blocked by insufficient evidence",
                "blocking_reason": (
                    f"Evidence tier is '{ev_class}' (q={q_val:.4f}). "
                    f"Current sample size or statistical power is inadequate to justify active creative production rollouts without prior exploratory proof."
                ),
            })

    return {
        "category_a_observed_evidence": cat_a,
        "category_b_hypotheses_to_test": cat_b,
        "category_c_blocked_insufficient_evidence": cat_c,
    }


def generate_analytical_report_markdown(
    project_name: str,
    project_id: str,
    df_metrics: pd.DataFrame,
    findings: List[Finding],
    recommendations: Dict[str, List[Dict[str, Any]]],
    confounding_reports: Optional[List[Dict[str, Any]]] = None,
    is_synthetic: bool = False,
) -> str:
    """Generates complete executive analytical report in structured Markdown."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    agg_kpis = compute_aggregate_kpis(df_metrics)

    lines: List[str] = [
        f"# ADCREATIVE INTELLIGENCE: ANALYTICAL PERFORMANCE REPORT",
        f"**Project**: {project_name} (`{project_id}`)",
        f"**Generated**: {now_str}",
        f"**Data Lineage Status**: {'⚠️ SYNTHETIC DEMONSTRATION DATASET (DO NOT USE FOR REAL MEDIA SPEND)' if is_synthetic else '✅ EMPIRICAL PRODUCTION CAMPAIGN DATA'}",
        "",
        "---",
        "## 1. PROJECT & DATASET SUMMARY",
        "",
        f"- **Total Creatives Ingested**: {agg_kpis['total_creatives']}",
        f"- **Total Campaign Spend**: ${agg_kpis['total_spend']:,.2f}",
        f"- **Total Impressions Delivered**: {agg_kpis['total_impressions']:,}",
        f"- **Total Clicks Recorded**: {agg_kpis['total_clicks']:,}",
        f"- **Total Conversions Recorded**: {agg_kpis['total_conversions']:,}",
        f"- **Aggregate CTR**: {(agg_kpis['aggregate_ctr']*100):.2f}%" if agg_kpis["aggregate_ctr"] is not None else "- **Aggregate CTR**: Unavailable (0 impressions)",
        f"- **Aggregate CVR**: {(agg_kpis['aggregate_cvr']*100):.2f}%" if agg_kpis["aggregate_cvr"] is not None else "- **Aggregate CVR**: Unavailable (0 clicks)",
        f"- **Aggregate CPC**: ${agg_kpis['aggregate_cpc']:.2f}" if agg_kpis["aggregate_cpc"] is not None else "- **Aggregate CPC**: Unavailable (0 clicks)",
        f"- **Aggregate CPA**: ${agg_kpis['aggregate_cpa']:.2f}" if agg_kpis["aggregate_cpa"] is not None else "- **Aggregate CPA**: Unavailable (0 conversions)",
        "",
        "---",
        "## 2. STATISTICALLY RANKED CREATIVE FINDINGS",
        "",
        "| Rank | Visual Attribute | Metric | Direction & Uplift | 95% CI | Raw p | FDR q | Evidence Classification |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for idx, f in enumerate(findings[:15]):
        uplift = f.effect_size.get("relative_uplift_pct", 0.0)
        ci_l = f.uncertainty.get("ci_95_lower", 0.0)
        ci_u = f.uncertainty.get("ci_95_upper", 0.0)
        lines.append(
            f"| #{idx+1} | {f.attribute} | **{f.outcome_metric}** | {uplift:+.1f}% | [{ci_l:.4f}, {ci_u:.4f}] | "
            f"{f.uncertainty['raw_p_value']:.4f} | **{f.uncertainty['fdr_q_value']:.4f}** | `{f.evidence_classification}` |"
        )

    lines.extend([
        "",
        "---",
        "## 3. CONFOUNDING INVESTIGATION ACROSS METADATA",
        "",
    ])

    if confounding_reports:
        for cr in confounding_reports:
            lines.append(
                f"- **{cr.get('attribute', 'Attribute')} vs {cr.get('confounder_field', 'Segment')}** ({cr.get('outcome_metric', 'Metric')}): "
                f"Risk = **{cr.get('confounding_risk', 'Unknown')}** ({cr.get('max_segment_concentration_pct', 0)}% max segment concentration). "
                f"{cr.get('assessment', '')}"
            )
    else:
        lines.append("- *No optional campaign, audience, or placement metadata fields were ingested for confounding analysis.*")

    lines.extend([
        "",
        "---",
        "## 4. CREATIVE RECOMMENDATIONS & EXPERIMENT BLUEPRINT",
        "",
        "### Category A: Recommendations Based on Observed Evidence (Supported)",
    ])

    cat_a = recommendations.get("category_a_observed_evidence", [])
    if cat_a:
        for rec in cat_a:
            lines.extend([
                f"#### [{rec['rec_id']}] {rec['proposed_creative_variation']}",
                f"- **Hypothesis**: {rec['hypothesis']}",
                f"- **Control**: {rec['control_asset']}",
                f"- **Variant**: {rec['variant_asset']}",
                f"- **Measurement Plan**: {rec['measurement_plan']}",
                f"- **Success Metric**: {rec['success_metric']}",
                f"- **Limitations**: {rec['important_limitations']}",
                "",
            ])
    else:
        lines.append("- *No findings reached confirmed FDR q < 0.05 evidence status. See Category B below for experimental hypotheses.*")

    lines.extend([
        "",
        "### Category B: New Hypotheses Requiring Structured Testing (Preliminary)",
    ])
    cat_b = recommendations.get("category_b_hypotheses_to_test", [])
    if cat_b:
        for rec in cat_b[:5]:
            lines.extend([
                f"#### [{rec['rec_id']}] {rec['proposed_creative_variation']}",
                f"- **Hypothesis**: {rec['hypothesis']}",
                f"- **Control**: {rec['control_asset']}",
                f"- **Variant**: {rec['variant_asset']}",
                f"- **Measurement Plan**: {rec['measurement_plan']}",
                f"- **Success Metric**: {rec['success_metric']}",
                f"- **Limitations**: {rec['important_limitations']}",
                "",
            ])
    else:
        lines.append("- *No preliminary hypotheses queued.*")

    lines.extend([
        "",
        "### Category C: Recommendations Blocked by Insufficient Evidence",
    ])
    cat_c = recommendations.get("category_c_blocked_insufficient_evidence", [])
    if cat_c:
        for rec in cat_c[:4]:
            lines.append(
                f"- **{rec['attribute']} ({rec['outcome_metric']})**: {rec.get('blocking_reason', '')}"
            )

    lines.extend([
        "",
        "---",
        "## 5. SCIENTIFIC INTEGRITY & METHODOLOGICAL GOVERNANCE",
        "> **Strict Non-Causal Declaration**: All analyses presented in this report reflect observational correlations. "
        "Creative performance is subject to auction dynamics, targeting overlap, bidding pacing, and seasonality. "
        "Do not interpret statistical significance as causal proof of future performance. "
        "A non-significant result does not prove that an attribute has no effect (absence of evidence is not evidence of absence).",
        "",
        f"> **Report Timestamp**: {now_str} | Generated by AdCreative Intelligence System Circuits",
    ])

    return "\n".join(lines)


def generate_analytical_report_csv(
    findings: List[Finding],
    df_metrics: pd.DataFrame,
    is_synthetic: bool = False,
) -> str:
    """Exports all ranked findings and traceable records to clean CSV format."""
    rows: List[Dict[str, Any]] = []
    for idx, f in enumerate(findings):
        uplift = f.effect_size.get("relative_uplift_pct", 0.0)
        ci_l = f.uncertainty.get("ci_95_lower", 0.0)
        ci_u = f.uncertainty.get("ci_95_upper", 0.0)
        rows.append({
            "rank": idx + 1,
            "rank_score": f.rank_score,
            "attribute": f.attribute,
            "outcome_metric": f.outcome_metric,
            "direction": f.direction_of_association,
            "relative_uplift_pct": uplift,
            "ci_95_lower": ci_l,
            "ci_95_upper": ci_u,
            "standard_error": f.uncertainty.get("standard_error", 0.0),
            "raw_p_value": f.uncertainty.get("raw_p_value", 1.0),
            "fdr_q_value": f.uncertainty.get("fdr_q_value", 1.0),
            "evidence_classification": f.evidence_classification,
            "statistical_method": f.statistical_method,
            "sample_sizes_json": str(f.sample_sizes),
            "traceable_ads_json": str(f.traceable_ad_ids),
            "limitations": f.limitations,
            "data_lineage": "SYNTHETIC_DEMO" if is_synthetic else "PRODUCTION_EMPIRICAL",
        })
    export_df = pd.DataFrame(rows)
    return export_df.to_csv(index=False)


def generate_pdf_report_bytes(
    project_name: str,
    project_id: str,
    df_metrics: pd.DataFrame,
    findings: List[Finding],
    recommendations: Dict[str, List[Dict[str, Any]]],
    is_synthetic: bool = False,
) -> bytes:
    """
    Renders a multi-page executive PDF analytical report using matplotlib PdfPages.
    Never exports synthetic demo results as real project results (watermarked clearly).
    """
    buf = io.BytesIO()
    agg_kpis = compute_aggregate_kpis(df_metrics)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with PdfPages(buf) as pdf:
        # PAGE 1: Executive KPI Summary & Overview
        fig1, ax1 = plt.subplots(figsize=(8.5, 11))
        ax1.axis("off")

        # Watermark if synthetic
        if is_synthetic:
            fig1.text(
                0.5, 0.96,
                "⚠️ SYNTHETIC DEMONSTRATION REPORT — NOT REAL CAMPAIGN DATA",
                ha="center", va="top", fontsize=11, fontweight="bold", color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFEBEE", edgecolor="#EF5350")
            )

        fig1.text(0.08, 0.91, "AdCreative Intelligence | PS-02", fontsize=14, color="#1565C0", fontweight="bold")
        fig1.text(0.08, 0.87, f"Executive Analytical Report: {project_name}", fontsize=18, fontweight="bold", color="#212121")
        fig1.text(0.08, 0.84, f"Project ID: {project_id}   |   Date: {now_str}   |   Total Assets: {agg_kpis['total_creatives']}", fontsize=10, color="#616161")

        # Horizontal Rule
        ax1.plot([0.08, 0.92], [0.82, 0.82], color="#BDBDBD", transform=fig1.transFigure, linewidth=1.5)

        # KPI Table Box
        fig1.text(0.08, 0.78, "1. Executive Performance Metrics Summary", fontsize=13, fontweight="bold", color="#1E88E5")
        
        kpi_text = (
            f"• Total Analyzed Spend:        ${agg_kpis['total_spend']:,.2f}\n"
            f"• Total Impressions:           {agg_kpis['total_impressions']:,}\n"
            f"• Total Clicks Delivered:      {agg_kpis['total_clicks']:,}\n"
            f"• Total Conversions Recorded:  {agg_kpis['total_conversions']:,}\n"
            f"• Aggregate CTR:               {(agg_kpis['aggregate_ctr']*100):.2f}%\n" if agg_kpis["aggregate_ctr"] is not None else "• Aggregate CTR:               Unavailable\n"
        ) + (
            f"• Aggregate CVR:               {(agg_kpis['aggregate_cvr']*100):.2f}%\n" if agg_kpis["aggregate_cvr"] is not None else "• Aggregate CVR:               Unavailable\n"
        ) + (
            f"• Aggregate CPC:               ${agg_kpis['aggregate_cpc']:.2f}\n" if agg_kpis["aggregate_cpc"] is not None else "• Aggregate CPC:               Unavailable\n"
        ) + (
            f"• Aggregate CPA:               ${agg_kpis['aggregate_cpa']:.2f}\n" if agg_kpis["aggregate_cpa"] is not None else "• Aggregate CPA:               Unavailable\n"
        )

        fig1.text(
            0.10, 0.61, kpi_text, fontsize=10, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.8", facecolor="#F5F5F5", edgecolor="#E0E0E0")
        )

        # Top Findings Summary
        fig1.text(0.08, 0.56, "2. Key Creative Attribute Findings (Top 5)", fontsize=13, fontweight="bold", color="#1E88E5")

        y_pos = 0.52
        for i, f in enumerate(findings[:5]):
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            q_val = f.uncertainty.get("fdr_q_value", 1.0)
            ci_l = f.uncertainty.get("ci_95_lower", 0.0)
            ci_u = f.uncertainty.get("ci_95_upper", 0.0)

            badge_color = "#2E7D32" if f.evidence_classification == "Supported association" else ("#F57F17" if "Preliminary" in f.evidence_classification else "#616161")
            fig1.text(0.09, y_pos, f"#{i+1} {f.attribute} ({f.outcome_metric})", fontsize=10, fontweight="bold", color="#212121")
            fig1.text(0.68, y_pos, f"[{f.evidence_classification}]", fontsize=9, fontweight="bold", color=badge_color)
            y_pos -= 0.025
            fig1.text(0.11, y_pos, f"• Uplift: {uplift:+.1f}% | 95% CI: [{ci_l:.4f}, {ci_u:.4f}] | FDR q: {q_val:.4f}", fontsize=9, color="#424242")
            y_pos -= 0.02
            fig1.text(0.11, y_pos, f"• Method: {f.statistical_method}", fontsize=8, color="#757575", fontfamily="sans-serif")
            y_pos -= 0.035

        # Footer Governance
        fig1.text(
            0.08, 0.08,
            "Observational Governance: Findings reflect empirical correlations and do not imply causal guarantees.\n"
            "Uncontrolled auction dynamics, targeting differences, and budget pacing may influence performance.",
            fontsize=8, color="#757575", style="italic"
        )
        pdf.savefig(fig1)
        plt.close(fig1)

        # PAGE 2: Creative Recommendations & Experiments
        fig2, ax2 = plt.subplots(figsize=(8.5, 11))
        ax2.axis("off")

        if is_synthetic:
            fig2.text(
                0.5, 0.96,
                "⚠️ SYNTHETIC DEMONSTRATION REPORT — NOT REAL CAMPAIGN DATA",
                ha="center", va="top", fontsize=11, fontweight="bold", color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFEBEE", edgecolor="#EF5350")
            )

        fig2.text(0.08, 0.91, "3. Recommended Creative Experiments (A/B Blueprint)", fontsize=14, fontweight="bold", color="#1565C0")
        fig2.text(0.08, 0.88, "Translating observed evidence into controlled experimental iterations.", fontsize=9, color="#616161")
        ax2.plot([0.08, 0.92], [0.86, 0.86], color="#BDBDBD", transform=fig2.transFigure, linewidth=1.5)

        y_p = 0.82
        all_recs = (
            recommendations.get("category_a_observed_evidence", []) +
            recommendations.get("category_b_hypotheses_to_test", [])
        )[:4]

        if all_recs:
            for rec in all_recs:
                fig2.text(0.08, y_p, f"[{rec['rec_id']}] {rec['proposed_creative_variation']}", fontsize=11, fontweight="bold", color="#212121")
                fig2.text(0.68, y_p, f"{rec['category'][:10]}...", fontsize=8, color="#1E88E5", fontweight="bold")
                y_p -= 0.025
                fig2.text(0.10, y_p, f"Hypothesis: {rec['hypothesis'][:90]}...", fontsize=9, color="#37474F")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Control: {rec['control_asset']}   |   Variant: {rec['variant_asset']}", fontsize=8, color="#546E7A")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Plan: {rec['measurement_plan'][:100]}...", fontsize=8, color="#546E7A")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Limitations: {rec['important_limitations'][:100]}...", fontsize=8, color="#78909C", style="italic")
                y_p -= 0.045
        else:
            fig2.text(0.10, y_p, "No creative recommendations generated. Ingest more creatives to expand power.", fontsize=10, color="#757575")

        fig2.text(
            0.08, 0.08,
            f"AdCreative Intelligence PDF Generator   |   Page 2 of 2   |   {now_str}",
            fontsize=8, color="#9E9E9E"
        )
        pdf.savefig(fig2)
        plt.close(fig2)

    buf.seek(0)
    return buf.getvalue()
