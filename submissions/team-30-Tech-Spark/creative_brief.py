"""
AdCreative Intelligence - Creative Brief Module
Generates actionable, data-grounded creative briefs for marketing and design teams.
All insights, recommendations, DOs/DON'Ts, and A/B test blueprints are dynamically
synthesized from the actual statistical findings and extracted features (zero hardcoded results).
Strictly distinguishes statistically supported findings from exploratory hypotheses, and clearly
states when a brief is based on general creative suggestions rather than performance findings.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from statistical_engine import Finding, compute_aggregate_kpis, investigate_confounding, rank_creatives
from recommendations import generate_recommendations, generate_experiment_plan


def _estimate_required_sample_size(
    baseline_rate: float,
    relative_uplift_pct: float,
    outcome_metric: str = "CTR",
    pooled_ctr: Optional[float] = None,
    pooled_cvr: Optional[float] = None,
    pooled_cpm: Optional[float] = None,
    pooled_cpc: Optional[float] = None,
) -> str:
    """
    Estimates minimum required sample size per variant for an 80% powered
    A/B test at alpha=0.05:
      - CTR: two-proportion z-test directly on impressions.
      - CVR: two-proportion z-test on clicks, converted to required impressions via pooled CTR.
      - CPC / CPA / ROAS: continuous two-sample approximation converted to impressions & budget.
    """
    rel = max(abs(relative_uplift_pct) / 100.0, 0.10)
    eff_ctr = float(pooled_ctr) if (pooled_ctr is not None and pooled_ctr > 0) else 0.02
    eff_cvr = float(pooled_cvr) if (pooled_cvr is not None and pooled_cvr > 0) else 0.05

    if outcome_metric == "CTR":
        p = max(min(float(baseline_rate) if baseline_rate else eff_ctr, 0.95), 0.002)
        delta = p * rel
        if delta <= 1e-6:
            return "25,000+ impressions per variant"
        n_impr = int(np.ceil(16.0 * p * (1.0 - p) / (delta**2)))
        n_impr = max(min(n_impr, 250000), 1000)
        budget_str = ""
        if pooled_cpm is not None and pooled_cpm > 0:
            est_cost = (n_impr / 1000.0) * pooled_cpm
            budget_str = f"; est. ~${est_cost:,.0f}/variant"
        return f"~{n_impr:,} impressions per variant (80% power, α=0.05{budget_str})"

    if outcome_metric == "CVR":
        p = max(min(float(baseline_rate) if baseline_rate else eff_cvr, 0.95), 0.005)
        delta = p * rel
        if delta <= 1e-6:
            return "2,500+ clicks (~125,000 impressions) per variant"
        n_clicks = int(np.ceil(16.0 * p * (1.0 - p) / (delta**2)))
        n_clicks = max(min(n_clicks, 100000), 200)
        n_impr = int(np.ceil(n_clicks / max(eff_ctr, 0.002)))
        budget_str = ""
        if pooled_cpc is not None and pooled_cpc > 0:
            est_cost = n_clicks * pooled_cpc
            budget_str = f"; est. ~${est_cost:,.0f}/variant"
        return (
            f"~{n_clicks:,} clicks (~{n_impr:,} impressions at {eff_ctr*100:.2f}% CTR) "
            f"per variant (80% power, α=0.05{budget_str})"
        )

    # Continuous cost/value metrics (CPC, CPA, ROAS): approximate standardized effect d
    d = max(min(rel, 1.0), 0.15)
    n_events = max(min(int(np.ceil(16.0 / (d**2))), 5000), 30)
    if outcome_metric == "CPC":
        n_impr = int(np.ceil(n_events / max(eff_ctr, 0.002)))
        budget_str = f"; est. ~${n_events * pooled_cpc:,.0f}/variant" if (pooled_cpc and pooled_cpc > 0) else ""
        return f"~{n_events:,} clicks (~{n_impr:,} impressions) per variant (80% power, α=0.05{budget_str})"
    else:
        # CPA or ROAS requires conversion events to stabilize variance
        n_clicks = int(np.ceil(n_events / max(eff_cvr, 0.005)))
        n_impr = int(np.ceil(n_clicks / max(eff_ctr, 0.002)))
        budget_str = f"; est. ~${n_clicks * pooled_cpc:,.0f}/variant" if (pooled_cpc and pooled_cpc > 0) else ""
        return (
            f"~{n_events:,} conversions (~{n_clicks:,} clicks / ~{n_impr:,} impressions) "
            f"per variant (80% power, α=0.05{budget_str})"
        )


def _select_exemplar_ads(f: Finding, df_metrics: Optional[pd.DataFrame] = None, max_ads: int = 3) -> List[str]:
    """Selects up to `max_ads` traceable exemplar ad_ids for a Finding, sorted by target metric when possible."""
    if not f.traceable_ad_ids:
        return []

    candidate_ids: List[str] = []
    if isinstance(f.traceable_ad_ids, dict):
        if f.attribute_type == "categorical" and f.group_a and f.group_b:
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            is_favorable = (uplift < 0) if f.outcome_metric in ("CPC", "CPA") else (uplift > 0)
            pref_grp = f.group_a if is_favorable else f.group_b
            if pref_grp in f.traceable_ad_ids:
                candidate_ids.extend([str(x) for x in f.traceable_ad_ids[pref_grp]])
        if not candidate_ids:
            for ids_list in f.traceable_ad_ids.values():
                if isinstance(ids_list, list):
                    candidate_ids.extend([str(x) for x in ids_list])
    elif isinstance(f.traceable_ad_ids, (list, tuple)):
        candidate_ids = [str(x) for x in f.traceable_ad_ids]

    if not candidate_ids:
        return []

    if df_metrics is None or df_metrics.empty or "ad_id" not in df_metrics.columns:
        return candidate_ids[:max_ads]

    sub = df_metrics[df_metrics["ad_id"].astype(str).isin(candidate_ids)].copy()
    if sub.empty:
        return candidate_ids[:max_ads]

    metric_col_map = {"CTR": "ctr", "CVR": "cvr", "CPC": "cpc", "CPA": "cpa", "ROAS": "roas"}
    col = metric_col_map.get(f.outcome_metric)
    if col and col in sub.columns:
        ascending = f.outcome_metric in ("CPC", "CPA")
        sub_valid = sub.dropna(subset=[col])
        if not sub_valid.empty:
            sub_sorted = sub_valid.sort_values(by=col, ascending=ascending)
            return [str(x) for x in sub_sorted["ad_id"].head(max_ads).tolist()]
    return [str(x) for x in sub["ad_id"].head(max_ads).tolist()]


def _guardrail_for_metric(outcome_metric: str, has_roas: bool = False) -> str:
    if outcome_metric == "CTR":
        return "CPA & CVR (verify clicks convert efficiently)"
    if outcome_metric == "CVR":
        return "CPA & ROAS" if has_roas else "CPA & CPC"
    if outcome_metric in ("CPC", "CPA"):
        return "Conversion Volume & CTR"
    if outcome_metric == "ROAS":
        return "CPA & Total Conversion Volume"
    return "CPA & CTR"


def generate_creative_brief(
    findings: List[Finding],
    df_metrics: Optional[pd.DataFrame] = None,
    dataset_is_synthetic: bool = False,
    campaign_objective: str = "Direct Response & Conversion Efficiency Optimization",
    target_audience: Optional[str] = None,
    creative_format: str = "1:1 Square Feed & 9:16 Vertical Story / Reel",
) -> Dict[str, Any]:
    """
    Synthesizes observed empirical findings into an executive Creative Brief using
    deterministic, rule-based synthesis grounded strictly in computed statistical findings.
    Separates:
      - Confirmed Evidence (Supported association)
      - Exploratory Hypotheses (Preliminary)
      - Underpowered / Inconclusive Signals (Underpowered)
      - Null / Unsupported Contrasts (No clear association / Unsupported)
      - Dynamic A/B Testing Blueprint derived from top observed findings
      - Grounded Designer Action Checklist (DOs and DON'Ts)
      - 14-Field Structured Strategy Brief (compatible with 10-Section legacy keys)
    """
    supported = [f for f in findings if f.evidence_classification == "Supported association"]
    preliminary = [f for f in findings if f.evidence_classification in ("Preliminary", "Preliminary evidence")]
    underpowered = [f for f in findings if f.evidence_classification == "Underpowered"]
    no_association = [
        f for f in findings if f.evidence_classification in ("No clear association", "Unsupported", "Not estimable")
    ]

    has_sufficient_evidence = bool(supported or preliminary)

    summary_stats = compute_aggregate_kpis(df_metrics) if df_metrics is not None else {}
    confounding_notes = (
        investigate_confounding(df_metrics, findings)
        if df_metrics is not None and not df_metrics.empty and findings
        else []
    )
    ranked_df = (
        rank_creatives(df_metrics)
        if df_metrics is not None and not df_metrics.empty
        else pd.DataFrame()
    )
    structured_recs = generate_recommendations(findings, df_metrics=df_metrics)
    experiment_plan = generate_experiment_plan(findings, df_metrics=df_metrics)

    pooled_ctr = summary_stats.get("aggregate_ctr")
    pooled_cvr = summary_stats.get("aggregate_cvr")
    pooled_cpc = summary_stats.get("aggregate_cpc")
    total_impr = summary_stats.get("total_impressions", 0)
    total_spend = summary_stats.get("total_spend", 0.0)
    pooled_cpm = (total_spend / total_impr * 1000.0) if (total_impr and total_impr > 0 and total_spend > 0) else None
    has_roas = summary_stats.get("aggregate_roas") is not None

    actionable_dos: List[str] = []
    actionable_donts: List[str] = []

    # 1. Build DOs strictly from Supported associations (or clearly labeled Preliminary if no Supported exist)
    for f in supported[:6]:
        q_val = f.uncertainty.get("fdr_q_value", 1.0)
        ci_l = f.uncertainty.get("ci_95_lower", 0.0)
        ci_u = f.uncertainty.get("ci_95_upper", 0.0)
        exemplars = _select_exemplar_ads(f, df_metrics, max_ads=3)
        exemplar_str = f" [Exemplar ads: {', '.join(exemplars)}]" if exemplars else ""
        if f.attribute_type == "categorical":
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            n_a = f.sample_sizes.get("creatives_group_a", 0)
            n_b = f.sample_sizes.get("creatives_group_b", 0)
            is_favorable = (uplift < 0) if f.outcome_metric in ("CPC", "CPA") else (uplift > 0)
            preferred_group = f.group_a if is_favorable else f.group_b
            compared_group = f.group_b if is_favorable else f.group_a
            actionable_dos.append(
                f"[Supported Evidence] Favor '{preferred_group}' over '{compared_group}' ({f.attribute.split(':')[0]}): "
                f"{f.direction_of_association} (n={n_a} vs {n_b} creatives, 95% CI [{ci_l:.4f}, {ci_u:.4f}], FDR q={q_val:.4f}).{exemplar_str}"
            )
        else:
            n_c = f.sample_sizes.get("creatives_count", 0)
            actionable_dos.append(
                f"[Supported Evidence] Optimize '{f.attribute}' for {f.outcome_metric}: "
                f"{f.direction_of_association} across n={n_c} creatives (95% CI [{ci_l:.3f}, {ci_u:.3f}], FDR q={q_val:.4f}).{exemplar_str}"
            )

    if not actionable_dos and preliminary:
        for f in preliminary[:4]:
            q_val = f.uncertainty.get("fdr_q_value", 1.0)
            p_val = f.uncertainty.get("raw_p_value", 1.0)
            exemplars = _select_exemplar_ads(f, df_metrics, max_ads=3)
            exemplar_str = f" [Exemplar ads: {', '.join(exemplars)}]" if exemplars else ""
            actionable_dos.append(
                f"[Preliminary Hypothesis — Test Before Scaling] {f.attribute} ({f.outcome_metric}): "
                f"{f.direction_of_association} (raw p={p_val:.4f}, FDR q={q_val:.4f}).{exemplar_str}"
            )

    if not actionable_dos:
        actionable_dos.append(
            "Insufficient statistical evidence in the current dataset to confirm performance drivers — "
            "this brief is based on general creative suggestions rather than confirmed performance findings. "
            "Upload additional creatives or impression volume before committing major design changes."
        )

    # 2. Build DON'Ts strictly from No Clear Association / Unsupported / Underpowered findings + High Confounding Warnings
    for c_note in confounding_notes:
        if c_note.get("confounding_risk") == "High" or c_note.get("stratified_consistency") == "Mixed / Reversed":
            actionable_donts.append(
                f"[Confounding Warning — {c_note.get('confounding_risk', 'High')} Risk] Do not attribute '{c_note.get('attribute')}' "
                f"({c_note.get('outcome_metric')}) purely to creative design: {c_note.get('assessment')}"
            )

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
        else:
            n_c = f.sample_sizes.get("creatives_count", 0)
            actionable_donts.append(
                f"[Underpowered Sample] Avoid over-indexing on '{f.attribute}' ({f.outcome_metric}): "
                f"Only n={n_c} creatives observed (minimum N >= 4 required for correlation inference)."
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
        exemplars = _select_exemplar_ads(f, df_metrics, max_ads=3)
        guardrail = _guardrail_for_metric(f.outcome_metric, has_roas=has_roas)

        flagged_confounders = [
            str(c.get("confounder_field"))
            for c in confounding_notes
            if c.get("attribute") == attr_base and c.get("confounding_risk") in ("High", "Moderate")
        ]
        conf_control_str = (
            f"Hold {', '.join(flagged_confounders)} constant across split cells"
            if flagged_confounders
            else "Lock audience, placement, and bidding strategy across 50/50 split cells"
        )

        if f.attribute_type == "categorical" and f.group_a and f.group_b:
            uplift = f.effect_size.get("relative_uplift_pct", 0.0)
            rate_a = f.effect_size.get("rate_group_a", 0.025)
            rate_b = f.effect_size.get("rate_group_b", 0.025)
            is_favorable = (uplift < 0) if f.outcome_metric in ("CPC", "CPA") else (uplift > 0)
            variant_grp = f.group_a if is_favorable else f.group_b
            control_grp = f.group_b if is_favorable else f.group_a
            baseline = float(rate_b if is_favorable else rate_a) if f.outcome_metric in ("CTR", "CVR") else 0.03
            sample_req = _estimate_required_sample_size(
                baseline,
                uplift,
                outcome_metric=f.outcome_metric,
                pooled_ctr=pooled_ctr,
                pooled_cvr=pooled_cvr,
                pooled_cpm=pooled_cpm,
                pooled_cpc=pooled_cpc,
            )

            ab_test_matrix.append(
                {
                    "test_id": f"EXP-{idx + 1:02d}",
                    "attribute_tested": attr_base,
                    "hypothesis": f"Controlled test of '{variant_grp}' vs '{control_grp}' on {f.outcome_metric} (observed: {f.direction_of_association}).",
                    "control": f"{attr_base}: {control_grp}",
                    "variant": f"{attr_base}: {variant_grp}",
                    "primary_kpi": f.outcome_metric,
                    "guardrail_kpi": guardrail,
                    "observed_evidence": f"{f.evidence_classification} (FDR q={f.uncertainty.get('fdr_q_value', 1.0):.4f})",
                    "min_sample_size_per_variant": sample_req,
                    "exemplar_ad_ids": exemplars,
                    "confounding_controls": conf_control_str,
                }
            )
        else:
            rho = f.effect_size.get("spearman_rho", 0.0)
            direction = "High" if rho > 0 else "Low"
            opp_dir = "Low" if rho > 0 else "High"
            if f.outcome_metric in ("CPC", "CPA"):
                direction, opp_dir = opp_dir, direction
            sample_req = _estimate_required_sample_size(
                0.025,
                abs(rho) * 40.0,
                outcome_metric=f.outcome_metric,
                pooled_ctr=pooled_ctr,
                pooled_cvr=pooled_cvr,
                pooled_cpm=pooled_cpm,
                pooled_cpc=pooled_cpc,
            )

            ab_test_matrix.append(
                {
                    "test_id": f"EXP-{idx + 1:02d}",
                    "attribute_tested": attr_base,
                    "hypothesis": f"Controlled test of {direction} vs {opp_dir} '{attr_base}' on {f.outcome_metric} (observed Spearman ρ={rho:+.2f}).",
                    "control": f"{opp_dir} {attr_base} (Baseline)",
                    "variant": f"{direction} {attr_base} (Treatment)",
                    "primary_kpi": f.outcome_metric,
                    "guardrail_kpi": guardrail,
                    "observed_evidence": f"{f.evidence_classification} (FDR q={f.uncertainty.get('fdr_q_value', 1.0):.4f})",
                    "min_sample_size_per_variant": sample_req,
                    "exemplar_ad_ids": exemplars,
                    "confounding_controls": conf_control_str,
                }
            )

    # Markdown Document Builder
    md_lines: List[str] = [
        "# EXECUTIVE CREATIVE BRIEF: ADCREATIVE INTELLIGENCE",
        "**Target Audience**: Performance Marketing, Creative Strategy, & Design Teams",
        f"**Dataset Status**: {'⚠️ DEMO DATA — SYNTHETIC EXAMPLE (SYNTHETIC DATASET — Not Real Production Claims)' if dataset_is_synthetic else '📊 EMPIRICAL UPLOADED DATASET'}",
        f"**Evidence Basis**: {'Grounded in Empirical Statistical Findings' if has_sufficient_evidence else '⚠️ Exploratory Creative Suggestions (Dataset Lacks Statistically Supported Findings)'}",
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
                f"- **Creatives Analyzed**: {summary_stats['total_creatives']} distinct assets",
                f"- **Total Spend Analyzed**: ${summary_stats['total_spend']:,.2f}",
                f"- **Total Impression Volume**: {summary_stats['total_impressions']:,}",
                f"- **Total Clicks Generated**: {summary_stats['total_clicks']:,} (**Pooled CTR**: {ctr_str} | **Ad-Level Mean / Median CTR**: {mean_ctr_str} / {med_ctr_str})",
                f"- **Total Conversions**: {summary_stats['total_conversions']:,} (**Pooled CVR**: {cvr_str} | **Ad-Level Mean / Median CVR**: {mean_cvr_str} / {med_cvr_str})",
                f"- **Cost Efficiency**: **Pooled CPC** = {cpc_str} (Ad Mean/Median: {mean_cpc_str}/{med_cpc_str}) | **Pooled CPA** = {cpa_str} (Ad Mean/Median: {mean_cpa_str}/{med_cpa_str})",
            ]
        )
        if summary_stats.get("aggregate_roas") is not None:
            roas_str = f"{summary_stats['aggregate_roas']:.2f}x"
            mean_roas_str = f"{summary_stats['mean_ad_roas']:.2f}x" if summary_stats.get("mean_ad_roas") is not None else "Undefined"
            med_roas_str = f"{summary_stats['median_ad_roas']:.2f}x" if summary_stats.get("median_ad_roas") is not None else "Undefined"
            rev_val = summary_stats.get("total_revenue") or 0.0
            md_lines.append(
                f"- **Revenue & Return on Ad Spend**: **Total Revenue** = ${rev_val:,.2f} | **Pooled ROAS** = {roas_str} (Ad Mean/Median: {mean_roas_str}/{med_roas_str})"
            )
        md_lines.append("")

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
            "| Test ID | Attribute | Hypothesis | Control | Variant | Primary KPI | Guardrail KPI | Observed Evidence | Est. Sample Size & Budget |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for exp in ab_test_matrix:
        md_lines.append(
            f"| **{exp['test_id']}** | {exp['attribute_tested']} | {exp['hypothesis']} | {exp['control']} | {exp['variant']} | **{exp['primary_kpi']}** | {exp.get('guardrail_kpi', 'CPA')} | {exp['observed_evidence']} | {exp['min_sample_size_per_variant']} |"
        )

    # Build 14-Field + 10-Section Structured Strategy Brief
    lead_finding = (supported + preliminary + underpowered + findings)[0] if findings else None
    audience_vals: List[str] = []
    platform_vals: List[str] = []
    if df_metrics is not None and not df_metrics.empty:
        if "audience" in df_metrics.columns:
            audience_vals = [str(x) for x in df_metrics["audience"].dropna().unique() if str(x) != "Unknown"]
        if "platform" in df_metrics.columns:
            platform_vals = [str(x) for x in df_metrics["platform"].dropna().unique() if str(x) != "Unknown"]

    resolved_audience = (
        target_audience.strip()
        if (target_audience and target_audience.strip())
        else (
            f"Active campaign segments ({', '.join(audience_vals[:4])})"
            if audience_vals
            else "Performance Marketing & Paid Social Acquisition Audiences (No explicit audience column in CSV)"
        )
    )
    platform_context = f" across {', '.join(platform_vals[:3])}" if platform_vals else ""

    if lead_finding is not None and has_sufficient_evidence:
        lead_exemplars = _select_exemplar_ads(lead_finding, df_metrics, max_ads=3)
        ex_note = f" (Exemplar creative IDs: {', '.join(lead_exemplars)})" if lead_exemplars else ""
        lead_attr_base = lead_finding.attribute.split(":")[0].strip()
        brief_title_text = f"Data-Backed Creative Brief: {lead_attr_base} Optimization for {lead_finding.outcome_metric}"
        key_insight_text = (
            f"[{lead_finding.evidence_classification}] {lead_finding.attribute} on {lead_finding.outcome_metric}: "
            f"{lead_finding.direction_of_association} "
            f"(Method: {lead_finding.statistical_method}, 95% CI [{lead_finding.uncertainty.get('ci_95_lower', 0):.4f}, "
            f"{lead_finding.uncertainty.get('ci_95_upper', 0):.4f}], raw p={lead_finding.uncertainty.get('raw_p_value', 1):.4f}, "
            f"BH-FDR q={lead_finding.uncertainty.get('fdr_q_value', 1):.4f}).{ex_note}"
        )
        supporting_evidence_text = (
            f"{len(supported)} statistically supported association(s) (FDR q < 0.05) and "
            f"{len(preliminary)} preliminary signal(s) across {summary_stats.get('total_creatives', 0)} creatives "
            f"({summary_stats.get('total_impressions', 0):,} impressions). Lead evidence: {key_insight_text}"
        )
        creative_concept_text = (
            f"Data-grounded creative iteration isolating '{lead_attr_base}'{platform_context} while holding copy offer, "
            f"landing page, and audience targeting constant to validate the observed {lead_finding.outcome_metric} signal."
        )
        hook_text = (
            f"Immediate first-impression visual salience anchored on the top-performing '{lead_attr_base}' treatment, "
            f"paired with a high-contrast focal subject and concise value proposition in the upper/center viewport."
        )
        main_message_text = (
            f"Deliver a single, uncluttered core value proposition so visual hierarchy reinforces the tested "
            f"'{lead_attr_base}' treatment without competing secondary copy blocks."
        )
        primary_metric_str = lead_finding.outcome_metric
        secondary_metrics_str = _guardrail_for_metric(lead_finding.outcome_metric, has_roas=has_roas)
        evidence_status_note = (
            f"Grounded in {len(supported)} statistically supported association(s) (FDR q < 0.05) "
            f"and {len(preliminary)} preliminary signal(s) from the active dataset."
        )
    else:
        brief_title_text = f"Exploratory Creative Brief: Baseline Testing for {campaign_objective}"
        key_insight_text = (
            "Dataset lacks statistically supported findings (no attributes reached Supported or Preliminary evidence thresholds). "
            "This brief is based on general creative testing suggestions rather than confirmed performance findings."
        )
        supporting_evidence_text = (
            f"Current dataset ({summary_stats.get('total_creatives', 0)} creatives, {summary_stats.get('total_impressions', 0):,} impressions) "
            "is underpowered or inconclusive. Additional creative variations and exposure volume are required."
        )
        creative_concept_text = (
            "Establish a clean baseline creative control vs. a structured single-variable visual variation "
            "(based on creative suggestions rather than performance findings) to collect benchmark data."
        )
        hook_text = "Clear focal subject with high luminance contrast against background."
        main_message_text = "Single primary benefit statement paired with direct call to action."
        primary_metric_str = "CTR & CVR"
        secondary_metrics_str = "CPA & CPC"
        evidence_status_note = (
            "No statistically supported or preliminary findings were detected in the current dataset — "
            "this brief is based on general creative suggestions rather than confirmed performance findings."
        )

    headline_direction_text = f"Hook: {hook_text} | Core Copy: {main_message_text} Keep headline concise (<8 words) and identical between Control and Variant cells when testing visual variables."

    visual_direction_text = (
        "DOs:\n" + "\n".join(f"• {d}" for d in actionable_dos[:4])
        + "\n\nCAUTIONS / DON'Ts:\n" + "\n".join(f"• {d}" for d in actionable_donts[:3])
    )
    cta_text = (
        "Use a single, high-contrast Call-to-Action button/badge aligned with post-click landing page intent; "
        "keep CTA phrasing identical between Control and Variant cells during split testing."
    )
    if ab_test_matrix:
        top_exp = ab_test_matrix[0]
        testable_hyp_text = top_exp["hypothesis"]
        rec_exp_text = (
            f"[{top_exp['test_id']}] {top_exp['hypothesis']} | Control: {top_exp['control']} vs. Variant: {top_exp['variant']} | "
            f"Sample Requirement: {top_exp['min_sample_size_per_variant']} | Controls: {top_exp.get('confounding_controls', '')}"
        )
    else:
        testable_hyp_text = "Testing a clean, single-focal-point hero layout against the current baseline creative will establish a reliable CTR and CVR benchmark."
        rec_exp_text = "Run a 50/50 split test with at least 4 distinct creatives per group and >=10,000 impressions per variant."

    variant_ideas_list: List[str] = []
    for exp_row in ab_test_matrix[:3]:
        variant_ideas_list.append(
            f"{exp_row['test_id']} ({exp_row['attribute_tested']}): Test '{exp_row['variant']}' against '{exp_row['control']}' on {exp_row['primary_kpi']}."
        )
    if not variant_ideas_list:
        variant_ideas_list.append(
            "Variant A vs. Control: Isolate a single visual variable (e.g., Warm vs. Cool color tone or Human vs. Product focus) while keeping headline and CTA identical."
        )

    assumptions_text = (
        "Observational correlations do not establish causation. All brief recommendations assume audience targeting, "
        "placement, bidding strategy, and landing page experience are held constant during split-test validation."
    )

    pooled_ctr_lbl = _fmt_rate(summary_stats.get("aggregate_ctr"))
    pooled_cvr_lbl = _fmt_rate(summary_stats.get("aggregate_cvr"))
    pooled_cpa_lbl = _fmt_currency(summary_stats.get("aggregate_cpa"))
    roas_lbl = f" | Pooled ROAS Baseline: {summary_stats['aggregate_roas']:.2f}x" if summary_stats.get("aggregate_roas") is not None else ""
    success_metrics_text = (
        f"Primary KPIs: CTR (Campaign Baseline: {pooled_ctr_lbl}) & CVR (Campaign Baseline: {pooled_cvr_lbl}) | "
        f"Guardrail KPI: CPA (Campaign Baseline: {pooled_cpa_lbl}){roas_lbl}. "
        f"Require Benjamini-Hochberg FDR q < 0.05 across N >= 4 creatives per variant before full budget scaling."
    )

    structured_sections = {
        # 14 Required Brief Fields (Section 9)
        "brief_title": brief_title_text,
        "objective": campaign_objective,
        "campaign_objective": campaign_objective,
        "target_audience": resolved_audience,
        "creative_format": creative_format,
        "format_and_aspect_ratio": creative_format,
        "key_insight": key_insight_text,
        "core_insight": key_insight_text,
        "supporting_evidence": supporting_evidence_text,
        "creative_concept": creative_concept_text,
        "visual_direction": visual_direction_text,
        "headline_direction": headline_direction_text,
        "copy_angle": headline_direction_text,
        "cta_direction": cta_text,
        "call_to_action": cta_text,
        "testable_hypothesis": testable_hyp_text,
        "primary_success_metric": f"{primary_metric_str} (Campaign Pooled CTR: {pooled_ctr_lbl}, CVR: {pooled_cvr_lbl})",
        "secondary_metrics": f"{secondary_metrics_str} (Campaign Pooled CPA: {pooled_cpa_lbl}{roas_lbl})",
        "experimental_considerations": rec_exp_text,
        "suggested_test_plan": rec_exp_text,
        "recommended_experiment": rec_exp_text,
        "success_metrics": success_metrics_text,
        "hook": hook_text,
        "recommended_hook": hook_text,
        "main_message": main_message_text,
        "creative_do_list": "\n".join(actionable_dos),
        "creative_avoid_list": "\n".join(actionable_donts),
        "variant_ideas": "\n".join(variant_ideas_list),
        "assumptions_and_limitations": assumptions_text,
    }

    md_lines.extend(
        [
            "",
            "---",
            "## 5. METHODOLOGY & STATISTICAL GOVERNANCE NOTICE",
            "> **Deterministic Rule-Based Synthesis**: This brief is deterministically synthesized from empirical statistical tests computed on the active dataset (not black-box generative AI). Recommendations do not guarantee future campaign uplift and must be validated via randomized split testing.",
            "",
            "> **Observational Non-Causality**: All associations reported here are observational. Ad performance is jointly influenced by audience targeting, auction competition, placement, and budget allocation. Never claim causation without randomized A/B split testing.",
            "",
            "> **Absence of Evidence**: A non-significant p-value or 'No clear association' classification indicates insufficient statistical evidence in the current sample, not proof that an attribute has zero effect.",
        ]
    )

    full_markdown = "\n".join(md_lines)

    return {
        "brief_title": brief_title_text,
        "has_sufficient_evidence": has_sufficient_evidence,
        "is_low_evidence_fallback": not has_sufficient_evidence,
        "evidence_status_note": evidence_status_note,
        "variant_ideas": variant_ideas_list,
        "summary_stats": summary_stats,
        "supported_findings": supported,
        "preliminary_findings": preliminary,
        "underpowered_findings": underpowered,
        "no_association_findings": no_association,
        "confounding_notes": confounding_notes,
        "actionable_dos": actionable_dos,
        "actionable_donts": actionable_donts,
        "ab_test_matrix": ab_test_matrix,
        "experiment_plan": experiment_plan,
        "top_ranked_creatives": ranked_df.to_dict(orient="records") if not ranked_df.empty else [],
        "structured_recommendations": structured_recs,
        "structured_sections": structured_sections,
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


def _fmt_roas(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Unavailable"
    return f"{float(val):.2f}x"


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
        f"**Dataset Mode**: {'DEMO DATA — SYNTHETIC EXAMPLE' if is_synthetic else 'Uploaded Empirical Campaign Dataset'}",
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
    ]
    if kpis.get("aggregate_roas") is not None:
        lines.append(
            f"| **ROAS** | {_fmt_roas(kpis.get('aggregate_roas'))} | {_fmt_roas(kpis.get('mean_ad_roas'))} | {_fmt_roas(kpis.get('median_ad_roas'))} |"
        )
    lines.extend([
        "",
        "## 3. TOP RANKED STATISTICAL FINDINGS",
    ])
    for idx, f in enumerate(findings[:10]):
        lines.append(
            f"{idx + 1}. **[{f.evidence_classification}] {f.attribute} -> {f.outcome_metric}**: {f.direction_of_association} "
            f"(Method: {f.statistical_method}, 95% CI [{f.uncertainty.get('ci_95_lower', 0):.4f}, {f.uncertainty.get('ci_95_upper', 0):.4f}], "
            f"Raw p={f.uncertainty.get('raw_p_value', 1):.4f}, FDR q={f.uncertainty.get('fdr_q_value', 1):.4f})"
        )
    lines.extend(["", "---", "", brief["full_markdown"]])
    return "\n".join(lines)
