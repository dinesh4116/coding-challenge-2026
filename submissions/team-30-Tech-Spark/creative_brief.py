"""
AdCreative Intelligence - Creative Brief Module
Generates actionable, data-grounded creative briefs for marketing and design teams.
All insights, recommendations, DOs/DON'Ts, and A/B test blueprints are dynamically
synthesized from the actual statistical findings and extracted features (zero hardcoded results).
Strictly distinguishes statistically supported findings from exploratory hypotheses.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from statistical_engine import Finding, compute_aggregate_kpis, investigate_confounding


def _estimate_required_sample_size(baseline_rate: float, relative_uplift_pct: float) -> str:
    """
    Estimates minimum required sample size (impressions/clicks) per variant for an 80% powered
    two-proportion A/B test at alpha=0.05 using normal approximation:
    n = 16 * p * (1 - p) / (delta^2)
    """
    p = max(min(baseline_rate, 0.95), 0.005)
    rel = max(abs(relative_uplift_pct) / 100.0, 0.10)
    delta = p * rel
    if delta <= 1e-6:
        return "25,000+ impressions per variant"
    n_events = int(np.ceil(16.0 * p * (1.0 - p) / (delta**2)))
    n_events = max(min(n_events, 250000), 1000)
    return f"~{n_events:,} exposures per variant (80% power, α=0.05)"


def generate_creative_brief(
    findings: List[Finding],
    df_metrics: Optional[pd.DataFrame] = None,
    dataset_is_synthetic: bool = False,
) -> Dict[str, Any]:
    """
    Synthesizes observed empirical findings into an executive Creative Brief.
    Separates:
      - Confirmed Evidence (Supported association)
      - Exploratory Hypotheses (Preliminary)
      - Underpowered / Inconclusive Signals (Underpowered)
      - Null / Unsupported Contrasts (No clear association / Unsupported)
      - Dynamic A/B Testing Blueprint derived from top observed findings
      - Grounded Designer Action Checklist (DOs and DON'Ts)
    """
    supported = [f for f in findings if f.evidence_classification == "Supported association"]
    preliminary = [f for f in findings if f.evidence_classification == "Preliminary"]
    underpowered = [f for f in findings if f.evidence_classification == "Underpowered"]
    no_association = [
        f for f in findings if f.evidence_classification in ("No clear association", "Unsupported", "Not estimable")
    ]

    summary_stats = compute_aggregate_kpis(df_metrics) if df_metrics is not None else {}
    confounding_notes = (
        investigate_confounding(df_metrics, findings)
        if df_metrics is not None and not df_metrics.empty and findings
        else []
    )

    actionable_dos: List[str] = []
    actionable_donts: List[str] = []

    # 1. Build DOs strictly from Supported associations (or clearly labeled Preliminary if no Supported exist)
    for f in supported[:6]:
        q_val = f.uncertainty.get("fdr_q_value", 1.0)
        ci_l = f.uncertainty.get("ci_95_lower", 0.0)
        ci_u = f.uncertainty.get("ci_95_upper", 0.0)
        if f.attribute_type == "categorical":
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            n_a = f.sample_sizes.get("creatives_group_a", 0)
            n_b = f.sample_sizes.get("creatives_group_b", 0)
            # For cost metrics (CPC, CPA), negative uplift means lower cost (favorable)
            is_favorable = (uplift < 0) if f.outcome_metric in ("CPC", "CPA") else (uplift > 0)
            preferred_group = f.group_a if is_favorable else f.group_b
            compared_group = f.group_b if is_favorable else f.group_a
            actionable_dos.append(
                f"[Supported Evidence] Favor '{preferred_group}' over '{compared_group}' ({f.attribute.split(':')[0]}): "
                f"{f.direction_of_association} (n={n_a} vs {n_b} creatives, 95% CI [{ci_l:.4f}, {ci_u:.4f}], FDR q={q_val:.4f})."
            )
        else:
            rho = f.effect_size.get("spearman_rho", 0.0)
            n_c = f.sample_sizes.get("creatives_count", 0)
            actionable_dos.append(
                f"[Supported Evidence] Optimize '{f.attribute}' for {f.outcome_metric}: "
                f"{f.direction_of_association} across n={n_c} creatives (95% CI [{ci_l:.3f}, {ci_u:.3f}], FDR q={q_val:.4f})."
            )

    if not actionable_dos and preliminary:
        for f in preliminary[:4]:
            q_val = f.uncertainty.get("fdr_q_value", 1.0)
            p_val = f.uncertainty.get("raw_p_value", 1.0)
            actionable_dos.append(
                f"[Preliminary Hypothesis — Test Before Scaling] {f.attribute} ({f.outcome_metric}): "
                f"{f.direction_of_association} (raw p={p_val:.4f}, FDR q={q_val:.4f})."
            )

    if not actionable_dos:
        actionable_dos.append(
            "Insufficient statistical power in current dataset to confirm positive creative drivers (all tests Underpowered or No clear association). Upload additional creatives or impression volume before committing design changes."
        )

    # 2. Build DON'Ts strictly from No Clear Association / Unsupported / Underpowered findings
    for f in no_association[:4]:
        p_val = f.uncertainty.get("raw_p_value", 1.0)
        q_val = f.uncertainty.get("fdr_q_value", 1.0)
        actionable_donts.append(
            f"[{f.evidence_classification}] Do not assume '{f.attribute}' drives {f.outcome_metric} without further testing: "
            f"{f.direction_of_association} (raw p={p_val:.4f}, FDR q={q_val:.4f}). Note: non-significance does not prove zero effect."
        )

    for f in underpowered[:2]:
        if f.attribute_type == "categorical":
            n_a = f.sample_sizes.get("creatives_group_a", 0)
            n_b = f.sample_sizes.get("creatives_group_b", 0)
            actionable_donts.append(
                f"[Underpowered Sample] Avoid over-indexing on '{f.attribute}' ({f.outcome_metric}): "
                f"Only n={n_a} vs n={n_b} creatives observed; high sampling variance."
            )

    if not actionable_donts:
        actionable_donts.append(
            "Do not treat observational creative correlations as causal proof; always validate via controlled split-testing."
        )

    # 3. Dynamically construct A/B Test Matrix from top findings (Supported, Preliminary, and Underpowered)
    ab_test_matrix: List[Dict[str, Any]] = []
    candidate_findings = (supported + preliminary + underpowered)[:5]

    for idx, f in enumerate(candidate_findings):
        attr_base = f.attribute.split(":")[0].strip()
        if f.attribute_type == "categorical" and f.group_a and f.group_b:
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            rate_a = f.effect_size.get("rate_group_a", 0.025)
            rate_b = f.effect_size.get("rate_group_b", 0.025)
            is_favorable = (uplift < 0) if f.outcome_metric in ("CPC", "CPA") else (uplift > 0)
            variant_grp = f.group_a if is_favorable else f.group_b
            control_grp = f.group_b if is_favorable else f.group_a
            baseline = float(rate_b if is_favorable else rate_a) if f.outcome_metric in ("CTR", "CVR") else 0.03
            sample_req = _estimate_required_sample_size(baseline, uplift)

            ab_test_matrix.append(
                {
                    "test_id": f"EXP-{idx + 1:02d}",
                    "attribute_tested": attr_base,
                    "hypothesis": f"Controlled test of '{variant_grp}' vs '{control_grp}' on {f.outcome_metric} (observed: {f.direction_of_association}).",
                    "control": f"{attr_base}: {control_grp}",
                    "variant": f"{attr_base}: {variant_grp}",
                    "primary_kpi": f.outcome_metric,
                    "observed_evidence": f"{f.evidence_classification} (FDR q={f.uncertainty.get('fdr_q_value', 1.0):.4f})",
                    "min_sample_size_per_variant": sample_req,
                }
            )
        else:
            rho = f.effect_size.get("spearman_rho", 0.0)
            direction = "High" if rho > 0 else "Low"
            opp_dir = "Low" if rho > 0 else "High"
            if f.outcome_metric in ("CPC", "CPA"):
                direction, opp_dir = opp_dir, direction
            sample_req = _estimate_required_sample_size(0.025, abs(rho) * 40.0)

            ab_test_matrix.append(
                {
                    "test_id": f"EXP-{idx + 1:02d}",
                    "attribute_tested": attr_base,
                    "hypothesis": f"Controlled test of {direction} vs {opp_dir} '{attr_base}' on {f.outcome_metric} (observed Spearman ρ={rho:+.2f}).",
                    "control": f"{opp_dir} {attr_base} (Baseline)",
                    "variant": f"{direction} {attr_base} (Treatment)",
                    "primary_kpi": f.outcome_metric,
                    "observed_evidence": f"{f.evidence_classification} (FDR q={f.uncertainty.get('fdr_q_value', 1.0):.4f})",
                    "min_sample_size_per_variant": sample_req,
                }
            )

    # Markdown Document Builder
    md_lines: List[str] = [
        "# EXECUTIVE CREATIVE BRIEF: ADCREATIVE INTELLIGENCE",
        "**Target Audience**: Performance Marketing, Creative Strategy, & Design Teams",
        f"**Dataset Status**: {'⚠️ SYNTHETIC DATASET (Evaluation Mock — Not Real Production Claims)' if dataset_is_synthetic else '📊 EMPIRICAL UPLOADED DATASET'}",
        "",
        "---",
        "## 1. EXECUTIVE SUMMARY & AGGREGATE CAMPAIGN METRICS",
        "*(Both pooled campaign ratios $\\sum\\text{num}/\\sum\\text{denom}$ and unweighted ad-level distributions are reported)*",
        "",
    ]

    if summary_stats and summary_stats.get("total_creatives", 0) > 0:
        ctr_str = f"{summary_stats['aggregate_ctr'] * 100:.2f}%" if summary_stats.get("aggregate_ctr") is not None else "Undefined (0 impressions)"
        cvr_str = f"{summary_stats['aggregate_cvr'] * 100:.2f}%" if summary_stats.get("aggregate_cvr") is not None else "Undefined (0 clicks)"
        cpc_str = f"${summary_stats['aggregate_cpc']:.2f}" if summary_stats.get("aggregate_cpc") is not None else "Undefined (0 clicks)"
        cpa_str = f"${summary_stats['aggregate_cpa']:.2f}" if summary_stats.get("aggregate_cpa") is not None else "Undefined (0 conversions)"

        mean_ctr_str = f"{summary_stats['mean_ad_ctr'] * 100:.2f}%" if summary_stats.get("mean_ad_ctr") is not None else "Undefined"
        med_ctr_str = f"{summary_stats['median_ad_ctr'] * 100:.2f}%" if summary_stats.get("median_ad_ctr") is not None else "Undefined"
        mean_cvr_str = f"{summary_stats['mean_ad_cvr'] * 100:.2f}%" if summary_stats.get("mean_ad_cvr") is not None else "Undefined"
        med_cvr_str = f"{summary_stats['median_ad_cvr'] * 100:.2f}%" if summary_stats.get("median_ad_cvr") is not None else "Undefined"
        mean_cpc_str = f"${summary_stats['mean_ad_cpc']:.2f}" if summary_stats.get("mean_ad_cpc") is not None else "Undefined"
        med_cpc_str = f"${summary_stats['median_ad_cpc']:.2f}" if summary_stats.get("median_ad_cpc") is not None else "Undefined"
        mean_cpa_str = f"${summary_stats['mean_ad_cpa']:.2f}" if summary_stats.get("mean_ad_cpa") is not None else "Undefined"
        med_cpa_str = f"${summary_stats['median_ad_cpa']:.2f}" if summary_stats.get("median_ad_cpa") is not None else "Undefined"

        md_lines.extend(
            [
                f"- **Creatives Analyzed**: {summary_stats['total_creatives']} distinct visual assets",
                f"- **Total Spend Analyzed**: ${summary_stats['total_spend']:,.2f}",
                f"- **Total Impression Volume**: {summary_stats['total_impressions']:,}",
                f"- **Total Clicks Generated**: {summary_stats['total_clicks']:,} (**Pooled CTR**: {ctr_str} | **Ad-Level Mean / Median CTR**: {mean_ctr_str} / {med_ctr_str})",
                f"- **Total Conversions**: {summary_stats['total_conversions']:,} (**Pooled CVR**: {cvr_str} | **Ad-Level Mean / Median CVR**: {mean_cvr_str} / {med_cvr_str})",
                f"- **Cost Efficiency**: **Pooled CPC** = {cpc_str} (Ad Mean/Median: {mean_cpc_str}/{med_cpc_str}) | **Pooled CPA** = {cpa_str} (Ad Mean/Median: {mean_cpa_str}/{med_cpa_str})",
                "",
            ]
        )


    md_lines.extend(
        [
            "### Confirmed Evidence (Supported Association: FDR q < 0.05, Adequate Sample Size)",
            "These associations passed Benjamini-Hochberg multiple-testing correction and sample thresholds:",
        ]
    )

    if supported:
        for f in supported:
            md_lines.append(
                f"- **{f.attribute}** ({f.outcome_metric}): {f.direction_of_association} | "
                f"Method: *{f.statistical_method}* | "
                f"95% CI: [{f.uncertainty['ci_95_lower']:.4f}, {f.uncertainty['ci_95_upper']:.4f}], "
                f"Raw p = {f.uncertainty['raw_p_value']:.4f}, Adjusted FDR q = {f.uncertainty['fdr_q_value']:.4f}. "
                f"*Limitation*: {f.limitations}"
            )
    else:
        md_lines.append(
            "- *No tested visual attribute reached Supported association (FDR q < 0.05 with N >= 4 per group) in the current dataset. "
            "Review preliminary hypotheses below.*"
        )

    md_lines.extend(
        [
            "",
            "### Preliminary Hypotheses & Underpowered Signals (Require Split-Test Validation)",
            "These associations show directional patterns or nominal significance before multiple-testing correction, or have small group sample sizes:",
        ]
    )

    if preliminary or underpowered:
        for f in (preliminary + underpowered)[:6]:
            md_lines.append(
                f"- **[{f.evidence_classification}] {f.attribute}** ({f.outcome_metric}): {f.direction_of_association} "
                f"(Method: {f.statistical_method}, Raw p = {f.uncertainty['raw_p_value']:.4f}, FDR q = {f.uncertainty['fdr_q_value']:.4f})."
            )
    else:
        md_lines.append("- *No preliminary or underpowered hypotheses currently queued.*")

    md_lines.extend(
        [
            "",
            "---",
            "## 2. DATA-GROUNDED DESIGNER GUIDELINES",
            "",
            "### Recommended Creative Explorations (Grounded in Observed Data)",
        ]
    )
    for do in actionable_dos:
        md_lines.append(f"1. {do}")

    md_lines.extend(
        [
            "",
            "### Cautions, Null Associations & Sample Constraints",
        ]
    )
    for dont in actionable_donts:
        md_lines.append(f"1. {dont}")

    if confounding_notes:
        md_lines.extend(
            [
                "",
                "---",
                "## 3. CONFOUNDING & METADATA STRATIFICATION CHECKS",
            ]
        )
        for c_note in confounding_notes[:5]:
            if "confounding_risk" in c_note:
                md_lines.append(
                    f"- **{c_note['attribute']} vs {c_note['confounder_field']}** ({c_note['outcome_metric']}): "
                    f"Risk = **{c_note['confounding_risk']}** — {c_note['assessment']}"
                )
            elif "message" in c_note:
                md_lines.append(f"- {c_note['message']}")

    md_lines.extend(
        [
            "",
            "---",
            "## 4. PRIORITIZED A/B TEST DESIGN MATRIX",
            "Controlled experimental roadmap synthesized directly from observed findings:",
            "",
            "| Test ID | Attribute | Hypothesis | Control | Variant | Primary KPI | Observed Evidence | Est. Sample Size |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for exp in ab_test_matrix:
        md_lines.append(
            f"| **{exp['test_id']}** | {exp['attribute_tested']} | {exp['hypothesis']} | {exp['control']} | {exp['variant']} | **{exp['primary_kpi']}** | {exp['observed_evidence']} | {exp['min_sample_size_per_variant']} |"
        )

    md_lines.extend(
        [
            "",
            "---",
            "## 5. METHODOLOGY & STATISTICAL GOVERNANCE NOTICE",
            "> **Observational Non-Causality**: All associations reported here are observational. Ad performance is jointly influenced by audience targeting, auction competition, placement, and budget allocation. Never claim causation without randomized A/B split testing.",
            "",
            "> **Absence of Evidence**: A non-significant p-value or 'No clear association' classification indicates insufficient statistical evidence in the current sample, not proof that an attribute has zero effect.",
        ]
    )

    full_markdown = "\n".join(md_lines)

    return {
        "summary_stats": summary_stats,
        "supported_findings": supported,
        "preliminary_findings": preliminary,
        "underpowered_findings": underpowered,
        "no_association_findings": no_association,
        "confounding_notes": confounding_notes,
        "actionable_dos": actionable_dos,
        "actionable_donts": actionable_donts,
        "ab_test_matrix": ab_test_matrix,
        "full_markdown": full_markdown,
    }


def _fmt_rate(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"{float(val) * 100.0:.2f}%"


def _fmt_currency(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Undefined (0 denom)"
    return f"${float(val):,.2f}"


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
        f"| **CTR** | {_fmt_rate(kpis.get('aggregate_ctr'))} | {_fmt_rate(kpis.get('mean_ad_ctr'))} | {_fmt_rate(kpis.get('median_ad_ctr'))} |",
        f"| **CVR** | {_fmt_rate(kpis.get('aggregate_cvr'))} | {_fmt_rate(kpis.get('mean_ad_cvr'))} | {_fmt_rate(kpis.get('median_ad_cvr'))} |",
        f"| **CPC** | {_fmt_currency(kpis.get('aggregate_cpc'))} | {_fmt_currency(kpis.get('mean_ad_cpc'))} | {_fmt_currency(kpis.get('median_ad_cpc'))} |",
        f"| **CPA** | {_fmt_currency(kpis.get('aggregate_cpa'))} | {_fmt_currency(kpis.get('mean_ad_cpa'))} | {_fmt_currency(kpis.get('median_ad_cpa'))} |",
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

