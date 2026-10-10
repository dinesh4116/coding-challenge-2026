"""
AdCreative Intelligence - Recommendations, Explainability & Experiment Planning Engine
- Translates empirical statistical findings into structured, explainable creative recommendations.
- Categorizes recommendations into:
    A. Recommendations based on observed evidence (Supported association)
    B. New hypotheses requiring testing (Preliminary evidence)
    C. Recommendations blocked by insufficient evidence (Underpowered / No association)
- Provides full 6-part Recommendation Explainability:
    1. What was observed
    2. Which data supports it
    3. Why it may matter
    4. What action could be tested
    5. How success should be measured
    6. What uncertainty remains
- Builds structured Experiment Plans for the Experiment Planner.
- Generates downloadable Analytical Reports in Markdown, CSV, and multi-page executive PDF formats.
- Watermarks synthetic datasets prominently so synthetic demo data is never confused with production data.
"""

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from statistical_engine import Finding, compute_aggregate_kpis


def _build_variation_spec(attr: str, metric: str, uplift: float) -> Dict[str, str]:
    """Deterministically builds control, variant, variable changed, and hypothesis descriptions for an attribute."""
    attr_clean = attr.split(":")[0].strip()
    if "Warm" in attr or "dominant_color_tone" in attr:
        return {
            "var_title": "Warm Palette Shift (Coral / Amber / Sunset)",
            "variable_changed": "Dominant Color Tone (Warm vs. Cool/Neutral)",
            "hyp": f"Transitioning hero ad color palettes toward warm hues will replicate the observed {uplift:+.1f}% {metric} difference under controlled split testing.",
            "ctrl": "Current Cool / Monochromatic Palette",
            "variant": "Vibrant Warm Palette with Amber/Coral Accent",
            "why_matters": f"Color temperature shapes immediate feed stopping power and visual salience, directly affecting {metric}.",
        }
    if "Human" in attr or "human_presence_cat" in attr:
        return {
            "var_title": "Human Subject & Facial Expression Integration",
            "variable_changed": "Frontal Human Face Presence (With Human vs. No Human)",
            "hyp": f"Incorporating relatable human facial expressions and lifestyle context will improve {metric} engagement.",
            "ctrl": "Product-Only Still Composition",
            "variant": "Product Featured with Expressive Human Subject",
            "why_matters": f"Human faces anchor viewer gaze patterns and social trust in paid social feeds, influencing {metric}.",
        }
    if "Square" in attr or "aspect_ratio_cat" in attr:
        return {
            "var_title": "1:1 Square vs. Vertical Aspect Ratio Optimization",
            "variable_changed": "Canvas Aspect Ratio & Framing",
            "hyp": f"Deploying native 1:1 Square creative framing will capture higher feed viewport real-estate for {metric} efficiency.",
            "ctrl": "Standard Landscape or Uncropped Story Frame",
            "variant": "Native 1:1 Square Optimized Creative",
            "why_matters": f"Native aspect ratio alignment maximizes viewport coverage across feed placements and impacts {metric}.",
        }
    if "Clean / Minimal" in attr or "visual_complexity" in attr or "edge_density" in attr.lower():
        return {
            "var_title": "Visual De-Cluttering & Minimalist Hierarchy",
            "variable_changed": "Background Edge Density & Visual Clutter",
            "hyp": f"Eliminating secondary graphic clutter and focusing on a single focal element will reduce cognitive friction and improve {metric}.",
            "ctrl": "Multi-Element Dense Banner",
            "variant": "Clean Minimalist Hero Layout (<6% Edge Density)",
            "why_matters": f"Lower visual complexity speeds up message comprehension during rapid feed scrolling, impacting {metric}.",
        }
    if "Minimal Copy" in attr or "text_density" in attr.lower():
        return {
            "var_title": "Copy Reduction & Headline Clarity",
            "variable_changed": "On-Image Text Overlay Density",
            "hyp": f"Limiting on-image copy coverage to a concise headline and bold CTA will improve comprehension and {metric}.",
            "ctrl": "Text-Heavy Multi-Bullet Layout",
            "variant": "High-Contrast Single Value Proposition (<15% Copy Area)",
            "why_matters": f"Concise overlay copy prevents cognitive overload and keeps visual focus on the primary CTA, driving {metric}.",
        }
    if "brightness" in attr.lower() or "contrast" in attr.lower():
        return {
            "var_title": "Luminance & Contrast Calibration",
            "variable_changed": f"Image {attr_clean}",
            "hyp": f"Calibrating luminance and foreground-background contrast into the optimal range will elevate visual salience and improve {metric}.",
            "ctrl": "Subdued Low-Contrast Mid-Tone Frame",
            "variant": "High-Contrast Calibrated Hero Frame",
            "why_matters": f"Strong luminance contrast separates the hero product and headline from the background, improving {metric}.",
        }
    return {
        "var_title": f"Controlled Creative Variation on {attr_clean}",
        "variable_changed": attr_clean,
        "hyp": f"Testing isolated variations in {attr_clean} to verify its relationship with {metric} under randomized split conditions.",
        "ctrl": f"Baseline {attr_clean} Control Asset",
        "variant": f"Optimized {attr_clean} Treatment Asset",
        "why_matters": f"Isolating {attr_clean} clarifies whether observed {metric} differences stem from creative design or campaign confounding.",
    }


def generate_recommendations(
    findings: List[Finding],
    df_metrics: Optional[pd.DataFrame] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Translates statistical findings into actionable, explainable creative experiment recommendations.
    Strictly categorizes recommendations into Category A, Category B, and Category C, and includes
    the 6 required explainability dimensions on every recommendation.
    """
    cat_a: List[Dict[str, Any]] = []
    cat_b: List[Dict[str, Any]] = []
    cat_c: List[Dict[str, Any]] = []

    for idx, f in enumerate(findings):
        attr = f.attribute
        metric = f.outcome_metric
        uplift = float(f.effect_size.get("relative_uplift_pct", 0.0) or 0.0)
        ci_l = float(f.uncertainty.get("ci_95_lower", 0.0) or 0.0)
        ci_u = float(f.uncertainty.get("ci_95_upper", 0.0) or 0.0)
        q_val = float(f.uncertainty.get("fdr_q_value", 1.0) or 1.0)
        raw_p = float(f.uncertainty.get("raw_p_value", 1.0) or 1.0)
        ev_class = f.evidence_classification

        spec = _build_variation_spec(attr, metric, uplift)
        var_title = spec["var_title"]
        hyp = spec["hyp"]
        ctrl = spec["ctrl"]
        variant = spec["variant"]

        # Measurement plan estimation
        base_rate = float(f.effect_size.get("rate_group_b", 0.02) or 0.02)
        if base_rate > 0:
            req_impressions = max(int(16.0 / (base_rate * max(abs(uplift) / 100.0, 0.05) ** 2)), 15000)
        else:
            req_impressions = 25000
        req_impressions = min(req_impressions, 250000)

        # Sample summary string
        if f.attribute_type == "categorical":
            n_a = f.sample_sizes.get("creatives_group_a", 0)
            n_b = f.sample_sizes.get("creatives_group_b", 0)
            imp_a = f.sample_sizes.get("impressions_group_a", 0)
            imp_b = f.sample_sizes.get("impressions_group_b", 0)
            supporting_data_str = (
                f"Group A ({f.group_a}): n={n_a} creatives ({imp_a:,} impressions) vs. "
                f"Group B ({f.group_b}): n={n_b} creatives ({imp_b:,} impressions). "
                f"Method: {f.statistical_method} | 95% CI: [{ci_l:.4f}, {ci_u:.4f}] | Raw p={raw_p:.4f} | BH-FDR q={q_val:.4f}."
            )
        else:
            n_c = f.sample_sizes.get("creatives_count", 0)
            imp_t = f.sample_sizes.get("total_impressions", 0)
            rho = float(f.effect_size.get("spearman_rho", 0.0) or 0.0)
            supporting_data_str = (
                f"Analyzed across n={n_c} creatives ({imp_t:,} total impressions). "
                f"Spearman ρ={rho:+.3f} | 95% CI: [{ci_l:.4f}, {ci_u:.4f}] | Raw p={raw_p:.4f} | BH-FDR q={q_val:.4f}."
            )

        measurement_plan_str = (
            f"Controlled 50/50 A/B split test holding audience, placement, and bidding constant. "
            f"Minimum target: {req_impressions:,} impressions per variant (~7–14 days duration)."
        )
        success_metric_str = f"Primary: {metric} | Secondary Guardrail: CPA & CVR"
        limitations_str = (
            f"Observational correlation only — does NOT guarantee future causal uplift. "
            f"{f.limitations}"
        )

        rec_entry = {
            "rec_id": f"REC-{idx+1:02d}",
            "attribute": attr,
            "outcome_metric": metric,
            "proposed_creative_variation": var_title,
            "variable_changed": spec["variable_changed"],
            "control_asset": ctrl,
            "variant_asset": variant,
            "hypothesis": hyp,
            "success_metric": success_metric_str,
            "measurement_plan": measurement_plan_str,
            # 6 Explicit Explainability Fields (Section 14)
            "what_was_observed": f.direction_of_association,
            "supporting_data": supporting_data_str,
            "why_it_matters": spec["why_matters"],
            "action_to_test": f"Test '{variant}' (Treatment) against '{ctrl}' (Control) isolating {spec['variable_changed']}.",
            "how_to_measure_success": f"{success_metric_str}. {measurement_plan_str}",
            "remaining_uncertainty": limitations_str,
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
            "important_limitations": limitations_str,
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
                    f"Evidence tier is '{ev_class}' (FDR q={q_val:.4f}). "
                    f"Current sample size or statistical power is insufficient to justify production rollouts without prior exploratory proof."
                ),
            })

    return {
        "category_a_observed_evidence": cat_a,
        "category_b_hypotheses_to_test": cat_b,
        "category_c_blocked_insufficient_evidence": cat_c,
    }


def generate_experiment_plan(
    findings: List[Finding],
    df_metrics: Optional[pd.DataFrame] = None,
    max_experiments: int = 8,
) -> List[Dict[str, Any]]:
    """
    Builds structured experiment plans from statistical findings for the Experiment Planner:
    Includes:
      - experiment_id
      - experiment_name
      - hypothesis
      - control_concept
      - variant_concept
      - variable_changed
      - primary_metric
      - secondary_metrics
      - target_audience_or_placement
      - minimum_data_considerations
      - measurement_period_guidance
      - decision_criteria
      - risks_and_limitations
      - evidence_tier
      - status ('Planned')
    """
    if not findings:
        return []

    # Determine available audience / placement context from dataset
    aud_str = "Primary Acquisition Audience"
    plc_str = "Primary Feed & Story Placements"
    if df_metrics is not None and not df_metrics.empty:
        if "audience" in df_metrics.columns:
            auds = [str(x) for x in df_metrics["audience"].dropna().unique() if str(x) not in ("", "Unknown", "nan")]
            if auds:
                aud_str = ", ".join(auds[:2])
        if "placement" in df_metrics.columns:
            plcs = [str(x) for x in df_metrics["placement"].dropna().unique() if str(x) not in ("", "Unknown", "nan")]
            if plcs:
                plc_str = ", ".join(plcs[:2])

    # Prioritize Supported -> Preliminary -> Underpowered -> others
    supported = [f for f in findings if f.evidence_classification == "Supported association"]
    prelim = [f for f in findings if f.evidence_classification in ("Preliminary", "Preliminary evidence")]
    under = [f for f in findings if f.evidence_classification == "Underpowered"]
    others = [f for f in findings if f not in supported and f not in prelim and f not in under]
    ordered = (supported + prelim + under + others)[:max_experiments]

    plans: List[Dict[str, Any]] = []
    for idx, f in enumerate(ordered):
        uplift = float(f.effect_size.get("relative_uplift_pct", 0.0) or 0.0)
        spec = _build_variation_spec(f.attribute, f.outcome_metric, uplift)
        q_val = float(f.uncertainty.get("fdr_q_value", 1.0) or 1.0)
        raw_p = float(f.uncertainty.get("raw_p_value", 1.0) or 1.0)

        if f.outcome_metric == "CTR":
            sec_metrics = "CPA, CVR, CPC"
            min_data = "At least N >= 4 distinct creative executions per arm and >= 15,000 impressions per variant (80% power at α=0.05)."
        elif f.outcome_metric == "CVR":
            sec_metrics = "CPA, CTR, Conversion Volume"
            min_data = "At least N >= 4 distinct creative executions per arm and >= 600 clicks (~25,000+ impressions) per variant."
        elif f.outcome_metric in ("CPC", "CPA"):
            sec_metrics = "Conversion Volume, CTR, CVR"
            min_data = "At least N >= 4 distinct creative executions per arm and >= 50 conversion events per cell to stabilize cost variance."
        else:
            sec_metrics = "CPA, Conversion Volume, CTR"
            min_data = "At least N >= 4 distinct creative executions per arm and >= 50 conversion events per cell."

        plans.append({
            "experiment_id": f"EXP-{idx+1:02d}",
            "experiment_name": f"{spec['var_title']} ({f.outcome_metric} Test)",
            "hypothesis": spec["hyp"],
            "control_concept": spec["ctrl"],
            "variant_concept": spec["variant"],
            "variable_changed": spec["variable_changed"],
            "primary_metric": f.outcome_metric,
            "secondary_metrics": sec_metrics,
            "target_audience_or_placement": f"Audience: {aud_str} | Placement: {plc_str}",
            "minimum_data_considerations": min_data,
            "measurement_period_guidance": "Run 7 to 14 consecutive days (minimum 1 full weekly cycle to neutralize day-of-week auction seasonality; avoid mid-flight budget edits).",
            "decision_criteria": (
                f"Ship Variant if {f.outcome_metric} improves with two-sided p < 0.05 (BH-FDR q < 0.05) across N >= 4 creatives/cell "
                f"and guardrail {sec_metrics.split(',')[0]} does not degrade by > 10%."
            ),
            "risks_and_limitations": (
                f"Source finding is observational ({f.evidence_classification}, raw p={raw_p:.4f}, FDR q={q_val:.4f}). "
                f"{f.limitations}"
            ),
            "evidence_tier": f.evidence_classification,
            "status": "Planned",
        })

    return plans


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
        f"**Data Lineage Status**: {'⚠️ DEMO DATA — SYNTHETIC EXAMPLE (DO NOT USE FOR REAL MEDIA SPEND)' if is_synthetic else '✅ EMPIRICAL PRODUCTION CAMPAIGN DATA'}",
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
                f"- **What Was Observed**: {rec.get('what_was_observed', '')}",
                f"- **Supporting Data**: {rec.get('supporting_data', '')}",
                f"- **Why It Matters**: {rec.get('why_it_matters', '')}",
                f"- **Action to Test**: {rec.get('action_to_test', '')}",
                f"- **How to Measure Success**: {rec.get('how_to_measure_success', '')}",
                f"- **Remaining Uncertainty**: {rec.get('remaining_uncertainty', '')}",
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
                f"- **What Was Observed**: {rec.get('what_was_observed', '')}",
                f"- **Supporting Data**: {rec.get('supporting_data', '')}",
                f"- **Why It Matters**: {rec.get('why_it_matters', '')}",
                f"- **Action to Test**: {rec.get('action_to_test', '')}",
                f"- **How to Measure Success**: {rec.get('how_to_measure_success', '')}",
                f"- **Remaining Uncertainty**: {rec.get('remaining_uncertainty', '')}",
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
        f"> **Report Timestamp**: {now_str} | Generated by AdCreative Intelligence",
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
                "DEMO DATA — SYNTHETIC EXAMPLE — NOT REAL CAMPAIGN DATA",
                ha="center", va="top", fontsize=11, fontweight="bold", color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFEBEE", edgecolor="#EF5350")
            )

        fig1.text(0.08, 0.91, "AdCreative Intelligence", fontsize=14, color="#4F46E5", fontweight="bold")
        fig1.text(0.08, 0.87, f"Executive Analytical Report: {project_name}", fontsize=18, fontweight="bold", color="#0F172A")
        fig1.text(0.08, 0.84, f"Workspace ID: {project_id}   |   Date: {now_str}   |   Total Assets: {agg_kpis['total_creatives']}", fontsize=10, color="#475569")

        # Horizontal Rule
        ax1.plot([0.08, 0.92], [0.82, 0.82], color="#CBD5E1", transform=fig1.transFigure, linewidth=1.5)

        # KPI Table Box
        fig1.text(0.08, 0.78, "1. Executive Performance Metrics Summary", fontsize=13, fontweight="bold", color="#4F46E5")

        kpi_text = (
            f"• Total Analyzed Spend:        ${agg_kpis['total_spend']:,.2f}\n"
            f"• Total Impressions:           {agg_kpis['total_impressions']:,}\n"
            f"• Total Clicks Delivered:      {agg_kpis['total_clicks']:,}\n"
            f"• Total Conversions Recorded:  {agg_kpis['total_conversions']:,}\n"
            + (f"• Aggregate CTR:               {(agg_kpis['aggregate_ctr']*100):.2f}%\n" if agg_kpis["aggregate_ctr"] is not None else "• Aggregate CTR:               Unavailable\n")
            + (f"• Aggregate CVR:               {(agg_kpis['aggregate_cvr']*100):.2f}%\n" if agg_kpis["aggregate_cvr"] is not None else "• Aggregate CVR:               Unavailable\n")
            + (f"• Aggregate CPC:               ${agg_kpis['aggregate_cpc']:.2f}\n" if agg_kpis["aggregate_cpc"] is not None else "• Aggregate CPC:               Unavailable\n")
            + (f"• Aggregate CPA:               ${agg_kpis['aggregate_cpa']:.2f}\n" if agg_kpis["aggregate_cpa"] is not None else "• Aggregate CPA:               Unavailable\n")
        )

        fig1.text(
            0.10, 0.61, kpi_text, fontsize=10, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.8", facecolor="#F8FAFC", edgecolor="#E2E8F0")
        )

        # Top Findings Summary
        fig1.text(0.08, 0.56, "2. Key Creative Attribute Findings (Top 5)", fontsize=13, fontweight="bold", color="#4F46E5")

        y_pos = 0.52
        for i, f in enumerate(findings[:5]):
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            q_val = f.uncertainty.get("fdr_q_value", 1.0)
            ci_l = f.uncertainty.get("ci_95_lower", 0.0)
            ci_u = f.uncertainty.get("ci_95_upper", 0.0)

            badge_color = "#047857" if f.evidence_classification == "Supported association" else ("#B45309" if "Preliminary" in f.evidence_classification else "#475569")
            fig1.text(0.09, y_pos, f"#{i+1} {f.attribute} ({f.outcome_metric})", fontsize=10, fontweight="bold", color="#0F172A")
            fig1.text(0.68, y_pos, f"[{f.evidence_classification}]", fontsize=9, fontweight="bold", color=badge_color)
            y_pos -= 0.025
            fig1.text(0.11, y_pos, f"• Uplift: {uplift:+.1f}% | 95% CI: [{ci_l:.4f}, {ci_u:.4f}] | FDR q: {q_val:.4f}", fontsize=9, color="#334155")
            y_pos -= 0.02
            fig1.text(0.11, y_pos, f"• Method: {f.statistical_method}", fontsize=8, color="#64748B", fontfamily="sans-serif")
            y_pos -= 0.035

        # Footer Governance
        fig1.text(
            0.08, 0.08,
            "Observational Governance: Findings reflect empirical correlations and do not imply causal guarantees.\n"
            "Uncontrolled auction dynamics, targeting differences, and budget pacing may influence performance.",
            fontsize=8, color="#64748B", style="italic"
        )
        pdf.savefig(fig1)
        plt.close(fig1)

        # PAGE 2: Creative Recommendations & Experiments
        fig2, ax2 = plt.subplots(figsize=(8.5, 11))
        ax2.axis("off")

        if is_synthetic:
            fig2.text(
                0.5, 0.96,
                "DEMO DATA — SYNTHETIC EXAMPLE — NOT REAL CAMPAIGN DATA",
                ha="center", va="top", fontsize=11, fontweight="bold", color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFEBEE", edgecolor="#EF5350")
            )

        fig2.text(0.08, 0.91, "3. Recommended Creative Experiments (A/B Blueprint)", fontsize=14, fontweight="bold", color="#4F46E5")
        fig2.text(0.08, 0.88, "Translating observed evidence into controlled experimental iterations.", fontsize=9, color="#475569")
        ax2.plot([0.08, 0.92], [0.86, 0.86], color="#CBD5E1", transform=fig2.transFigure, linewidth=1.5)

        y_p = 0.82
        all_recs = (
            recommendations.get("category_a_observed_evidence", []) +
            recommendations.get("category_b_hypotheses_to_test", [])
        )[:4]

        if all_recs:
            for rec in all_recs:
                fig2.text(0.08, y_p, f"[{rec['rec_id']}] {rec['proposed_creative_variation']}", fontsize=11, fontweight="bold", color="#0F172A")
                fig2.text(0.68, y_p, f"{rec['category'][:10]}...", fontsize=8, color="#4F46E5", fontweight="bold")
                y_p -= 0.025
                fig2.text(0.10, y_p, f"Hypothesis: {rec['hypothesis'][:90]}...", fontsize=9, color="#334155")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Control: {rec['control_asset']}   |   Variant: {rec['variant_asset']}", fontsize=8, color="#475569")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Plan: {rec['measurement_plan'][:100]}...", fontsize=8, color="#475569")
                y_p -= 0.02
                fig2.text(0.10, y_p, f"Limitations: {rec['important_limitations'][:100]}...", fontsize=8, color="#64748B", style="italic")
                y_p -= 0.045
        else:
            fig2.text(0.10, y_p, "No creative recommendations generated. Ingest more creatives to expand power.", fontsize=10, color="#64748B")

        fig2.text(
            0.08, 0.08,
            f"AdCreative Intelligence PDF Generator   |   Page 2 of 2   |   {now_str}",
            fontsize=8, color="#94A3B8"
        )
        pdf.savefig(fig2)
        plt.close(fig2)

    buf.seek(0)
    return buf.getvalue()
