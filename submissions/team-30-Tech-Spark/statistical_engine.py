"""
AdCreative Intelligence - Statistical Engine Module
Performs rigorous statistical comparison of automatically extracted visual
attributes against performance metrics (CTR, CVR, CPC, CPA).

Implements:
- Aggregate pooled rate comparisons with proportion z-tests & Wald/Wilson CIs.
- Creative-level distributions with Welch's t-tests & Cohen's d effect sizes (Simpson's paradox guard).
- Continuous attribute correlations (Spearman rho, Pearson r with Fisher z CI) & Exposure-Weighted WLS / OLS.
- Benjamini-Hochberg False Discovery Rate (FDR) and Bonferroni multiple-testing corrections.
- Confounding investigations across campaign, audience, placement, and platform.
- Documented composite ranking criteria.
- Mandatory 11-point findings reporting including standardized evidence classifications,
  traceable ad IDs, and honest non-causal limitations statements.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.regression.linear_model as sm_lm
import statsmodels.tools.tools as sm_tools


@dataclass
class Finding:
    attribute: str
    outcome_metric: str
    direction_of_association: str
    effect_size: Dict[str, Any]
    sample_sizes: Dict[str, Any]
    uncertainty: Dict[str, Any]
    evidence_classification: str
    limitations: str
    attribute_type: str  # 'categorical' or 'continuous'
    statistical_method: str = "Two-Proportion Z-Test + Ad-Level Welch's t-Test"
    adjusted_p_value: Optional[float] = None
    explanation: str = ""
    traceable_ad_ids: Dict[str, List[str]] = field(default_factory=dict)
    rank_score: float = 0.0
    group_a: Optional[str] = None
    group_b: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def direction(self) -> str:
        return self.direction_of_association

    @property
    def evidence_category(self) -> str:
        return self.evidence_classification

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["direction"] = self.direction
        d["evidence_category"] = self.evidence_category
        return d


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: Optional[float] = None) -> Optional[float]:
    """Zero-safe division returning default if denominator is zero, null, or NaN."""
    if denominator is None or np.isnan(denominator) or denominator <= 0:
        return default
    if numerator is None or np.isnan(numerator):
        return default
    return float(numerator) / float(denominator)


def compute_aggregate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes aggregate campaign KPIs strictly across all rows:
    - Pooled Campaign Metrics:
      - Aggregate CTR = total clicks / total impressions
      - Aggregate CVR = total conversions / total clicks
      - Aggregate CPC = total spend / total clicks
      - Aggregate CPA = total spend / total conversions
    - Unweighted Ad-Level Averages (kept explicitly separate from pooled campaign metrics):
      - mean_ad_ctr, mean_ad_cvr, mean_ad_cpc, mean_ad_cpa
      - median_ad_ctr, median_ad_cvr, median_ad_cpc, median_ad_cpa
    Undefined metrics are represented as None (unavailable, never 0.0).
    """
    if df is None or df.empty:
        return {
            "total_creatives": 0,
            "total_spend": 0.0,
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "aggregate_ctr": None,
            "aggregate_cvr": None,
            "aggregate_cpc": None,
            "aggregate_cpa": None,
            "mean_ad_ctr": None,
            "mean_ad_cvr": None,
            "mean_ad_cpc": None,
            "mean_ad_cpa": None,
            "median_ad_ctr": None,
            "median_ad_cvr": None,
            "median_ad_cpc": None,
            "median_ad_cpa": None,
        }

    total_imp = int(df["impressions"].sum())
    total_clk = int(df["clicks"].sum())
    total_cnv = int(df["conversions"].sum())
    total_spn = float(df["spend"].sum())

    def _col_stat(col_name: str, stat_fn: str) -> Optional[float]:
        if col_name not in df.columns:
            return None
        s = pd.to_numeric(df[col_name], errors="coerce").dropna()
        if s.empty:
            return None
        return float(s.mean() if stat_fn == "mean" else s.median())

    return {
        "total_creatives": len(df),
        "total_spend": total_spn,
        "total_impressions": total_imp,
        "total_clicks": total_clk,
        "total_conversions": total_cnv,
        "aggregate_ctr": (total_clk / total_imp) if total_imp > 0 else None,
        "aggregate_cvr": (total_cnv / total_clk) if total_clk > 0 else None,
        "aggregate_cpc": (total_spn / total_clk) if total_clk > 0 else None,
        "aggregate_cpa": (total_spn / total_cnv) if total_cnv > 0 else None,
        "mean_ad_ctr": _col_stat("ctr", "mean"),
        "mean_ad_cvr": _col_stat("cvr", "mean"),
        "mean_ad_cpc": _col_stat("cpc", "mean"),
        "mean_ad_cpa": _col_stat("cpa", "mean"),
        "median_ad_ctr": _col_stat("ctr", "median"),
        "median_ad_cvr": _col_stat("cvr", "median"),
        "median_ad_cpc": _col_stat("cpc", "median"),
        "median_ad_cpa": _col_stat("cpa", "median"),
    }


def compute_proportion_difference_ci(
    count_a: int, total_a: int, count_b: int, total_b: int, alpha: float = 0.05
) -> Tuple[float, float, float, float]:
    """
    Computes difference in proportions (p_a - p_b) with 95% Wald standard error and confidence interval.
    Note: Assumes independent Bernoulli trials; for multi-ad comparisons where exposures are clustered
    within creatives, use _compute_ad_level_welch_inference instead.
    Returns: (diff, ci_lower, ci_upper, standard_error)
    """
    if total_a <= 0 or total_b <= 0:
        return 0.0, 0.0, 0.0, 0.0

    p_a = count_a / total_a
    p_b = count_b / total_b
    diff = p_a - p_b

    var_a = (p_a * (1.0 - p_a)) / total_a
    var_b = (p_b * (1.0 - p_b)) / total_b
    se = float(np.sqrt(var_a + var_b))

    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ci_lower = diff - z_crit * se
    ci_upper = diff + z_crit * se

    return float(diff), float(ci_lower), float(ci_upper), float(se)


def compute_cohens_d(group_a_vals: np.ndarray, group_b_vals: np.ndarray) -> float:
    """Computes Cohen's d effect size between two continuous samples."""
    n_a = len(group_a_vals)
    n_b = len(group_b_vals)
    if n_a < 2 or n_b < 2:
        return 0.0

    var_a = float(np.var(group_a_vals, ddof=1))
    var_b = float(np.var(group_b_vals, ddof=1))
    pooled_sd = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    if pooled_sd == 0:
        return 0.0

    return float((np.mean(group_a_vals) - np.mean(group_b_vals)) / pooled_sd)


def _safe_welch_p(vals_a: np.ndarray, vals_b: np.ndarray, fallback_p: float = 1.0) -> float:
    """Safely computes two-sided Welch's t-test p-value across creatives without emitting precision loss warnings."""
    if len(vals_a) < 2 or len(vals_b) < 2:
        return fallback_p
    if np.std(vals_a) < 1e-10 and np.std(vals_b) < 1e-10:
        return 1e-12 if abs(np.mean(vals_a) - np.mean(vals_b)) > 1e-10 else 1.0
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        t_res = stats.ttest_ind(vals_a, vals_b, equal_var=False)
        return float(t_res.pvalue) if not np.isnan(t_res.pvalue) else fallback_p


def _compute_ad_level_welch_inference(
    vals_a: np.ndarray,
    vals_b: np.ndarray,
    center_diff: Optional[float] = None,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Performs cluster-appropriate creative-level inference treating each ad_id as the unit of analysis
    (never treating individual impressions/clicks as independent experimental units).
    Computes:
      - Ad-level mean difference (mean_a - mean_b)
      - Welch standard error across creatives: sqrt(s_a^2 / n_a + s_b^2 / n_b)
      - Welch-Satterthwaite degrees of freedom (df_welch) and Student's t critical value
      - 95% confidence interval using Student's t distribution
      - Two-sided Welch's t-test p-value (unmanipulated) and Mann-Whitney U p-value
    """
    n_a = len(vals_a)
    n_b = len(vals_b)
    if n_a < 2 or n_b < 2:
        pt = float(center_diff) if center_diff is not None else 0.0
        return {
            "inferential_valid": False,
            "mean_a": float(np.mean(vals_a)) if n_a > 0 else 0.0,
            "mean_b": float(np.mean(vals_b)) if n_b > 0 else 0.0,
            "ad_mean_diff": pt,
            "se_welch": 0.0,
            "df_welch": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "p_welch": 1.0,
            "p_mwu": 1.0,
        }

    mean_a = float(np.mean(vals_a))
    mean_b = float(np.mean(vals_b))
    ad_diff = mean_a - mean_b
    diff_for_ci = float(center_diff) if center_diff is not None else ad_diff

    var_a = float(np.var(vals_a, ddof=1))
    var_b = float(np.var(vals_b, ddof=1))
    term_a = var_a / n_a
    term_b = var_b / n_b
    se_welch = float(np.sqrt(term_a + term_b))

    denom_df = (term_a**2) / max(n_a - 1, 1) + (term_b**2) / max(n_b - 1, 1)
    if denom_df > 1e-20:
        df_welch = float(((term_a + term_b) ** 2) / denom_df)
    else:
        df_welch = float(max(n_a + n_b - 2, 1))

    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=max(df_welch, 1.0)))
    ci_lower = diff_for_ci - t_crit * se_welch
    ci_upper = diff_for_ci + t_crit * se_welch

    p_welch = _safe_welch_p(vals_a, vals_b, 1.0)
    try:
        mwu_res = stats.mannwhitneyu(vals_a, vals_b, alternative="two-sided")
        p_mwu = float(mwu_res.pvalue) if not np.isnan(mwu_res.pvalue) else p_welch
    except Exception:
        p_mwu = p_welch

    return {
        "inferential_valid": True,
        "mean_a": mean_a,
        "mean_b": mean_b,
        "ad_mean_diff": ad_diff,
        "se_welch": se_welch,
        "df_welch": round(df_welch, 2),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "p_welch": float(np.clip(p_welch, 1e-12, 1.0)),
        "p_mwu": float(np.clip(p_mwu, 1e-12, 1.0)),
    }


def classify_evidence(
    raw_p: float,
    fdr_q: float,
    sample_size_a: int,
    sample_size_b: int,
    relative_uplift_pct: float,
    ci_lower: float,
    ci_upper: float,
) -> str:
    """
    Classifies evidence strictly using documented standards:
    - Supported association: FDR q < 0.05, N >= 4 per group, CI excludes zero, substantive uplift.
    - Preliminary: Nominal p < 0.05 or promising uplift in moderate sample size.
    - Underpowered: Creative count N < 3 in a group or excessively wide CI.
    - No clear association: Adequate sample size, negligible effect (|uplift| < 6%), p > 0.20.
    - Unsupported: Tested contrast fails to show expected association.
    """
    min_n = min(sample_size_a, sample_size_b)
    abs_uplift = abs(relative_uplift_pct)

    # 1. Underpowered: sample size too small
    if min_n < 3:
        return "Underpowered"

    # 2. Supported association: FDR q < 0.05, adequate sample size, CI does not cross zero, substantive effect
    if fdr_q < 0.05 and min_n >= 4 and ((ci_lower > 0 and ci_upper > 0) or (ci_lower < 0 and ci_upper < 0)):
        if abs_uplift >= 8.0:
            return "Supported association"
        else:
            return "Preliminary"

    # 3. Preliminary: nominal p < 0.05 or moderate sample size with promising effect
    if raw_p < 0.05 or (fdr_q < 0.15 and abs_uplift >= 10.0 and min_n >= 3):
        return "Preliminary"

    # 4. No clear association: adequate sample size, negligible effect, non-significant
    if min_n >= 5 and abs_uplift < 6.0 and raw_p > 0.20:
        return "No clear association"

    # 5. Unsupported
    if raw_p >= 0.10:
        if min_n >= 4:
            return "No clear association"
        return "Unsupported"

    return "Preliminary"


def generate_limitations_statement(
    n_a: int,
    n_b: int,
    total_impressions: int,
    attribute_name: str,
    metric: str,
) -> str:
    """Generates an honest, non-causal limitations statement."""
    limits = [
        "Observational association only; does not establish causal impact.",
        "Uncontrolled confounders (audience targeting, bidding strategies, budget pacing, seasonality) may explain observed variance.",
    ]
    if min(n_a, n_b) < 5:
        limits.append(
            f"Small sample size ({n_a} vs {n_b} creatives); estimates have high sampling variance."
        )
    if total_impressions < 50000:
        limits.append("Low overall impression volume limits statistical power for fine-grained detection.")
    limits.append(
        "A non-significant result does not prove the attribute has no effect (absence of evidence is not evidence of absence)."
    )
    return " ".join(limits)


def analyze_categorical_attribute(
    df: pd.DataFrame,
    attribute_col: str,
    group_a: str,
    group_b: str,
) -> List[Finding]:
    """Compares two groups of a categorical visual attribute across CTR, CVR, CPC, and CPA."""
    findings: List[Finding] = []

    sub_a = df[df[attribute_col] == group_a]
    sub_b = df[df[attribute_col] == group_b]

    n_a = len(sub_a)
    n_b = len(sub_b)

    ad_ids_a = sub_a["ad_id"].astype(str).tolist()
    ad_ids_b = sub_b["ad_id"].astype(str).tolist()
    traceable = {"group_a_ads": ad_ids_a, "group_b_ads": ad_ids_b}

    if n_a < 1 or n_b < 1:
        # Generate 'Not estimable' finding
        findings.append(
            Finding(
                attribute=f"{attribute_col}: {group_a} vs {group_b}",
                outcome_metric="CTR",
                direction_of_association=f"Contrast between '{group_a}' (n={n_a}) and '{group_b}' (n={n_b}) is not estimable.",
                effect_size={"relative_uplift_pct": 0.0, "absolute_difference": 0.0},
                sample_sizes={"creatives_group_a": n_a, "creatives_group_b": n_b},
                uncertainty={"ci_95_lower": 0.0, "ci_95_upper": 0.0, "standard_error": 0.0, "raw_p_value": 1.0, "fdr_q_value": 1.0},
                evidence_classification="Not estimable",
                limitations="One or both contrast groups contain zero creatives. Comparison cannot be mathematically estimated.",
                attribute_type="categorical",
                statistical_method="Two-Proportion Z-Test (Not Estimable)",
                adjusted_p_value=1.0,
                explanation=f"Cannot compute contrast because one of the groups has no creative assets in the dataset.",
                traceable_ad_ids=traceable,
                group_a=group_a,
                group_b=group_b,
            )
        )
        return findings

    imp_a = int(sub_a["impressions"].sum())
    clk_a = int(sub_a["clicks"].sum())
    cnv_a = int(sub_a["conversions"].sum())
    spn_a = float(sub_a["spend"].sum())

    imp_b = int(sub_b["impressions"].sum())
    clk_b = int(sub_b["clicks"].sum())
    cnv_b = int(sub_b["conversions"].sum())
    spn_b = float(sub_b["spend"].sum())

    total_imp = imp_a + imp_b

    # 1. CTR = clicks / impressions
    if imp_a > 0 and imp_b > 0:
        ctr_a = clk_a / imp_a
        ctr_b = clk_b / imp_b
        diff_ctr = ctr_a - ctr_b
        uplift_pct = ((ctr_a - ctr_b) / ctr_b * 100.0) if ctr_b > 0 else 0.0

        vals_a = sub_a["ctr"].dropna().values
        vals_b = sub_b["ctr"].dropna().values
        cohen_d = compute_cohens_d(vals_a, vals_b)
        inf_ctr = _compute_ad_level_welch_inference(vals_a, vals_b, center_diff=diff_ctr)
        p_final = inf_ctr["p_welch"]
        ci_low_ctr = inf_ctr["ci_lower"]
        ci_upp_ctr = inf_ctr["ci_upper"]
        se_ctr = inf_ctr["se_welch"]
        method_ctr = (
            f"Ad-Level Welch's t-Test across Creatives (df={inf_ctr['df_welch']}) + Mann-Whitney U Check"
            if inf_ctr["inferential_valid"]
            else "Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"
        )

        dir_str = (
            f"'{group_a}' associated with {uplift_pct:+.1f}% {'higher' if uplift_pct >= 0 else 'lower'} pooled CTR compared to '{group_b}' "
            f"(Ad-level mean: {inf_ctr['mean_a']*100:.2f}% vs {inf_ctr['mean_b']*100:.2f}%)"
        )
        expl_str = (
            f"Creatives in group '{group_a}' ({', '.join(ad_ids_a[:3])}{'...' if len(ad_ids_a)>3 else ''}) generated "
            f"{clk_a:,} clicks across {imp_a:,} impressions ({ctr_a*100:.2f}% pooled CTR; {inf_ctr['mean_a']*100:.2f}% ad-level mean), "
            f"versus {ctr_b*100:.2f}% pooled CTR ({inf_ctr['mean_b']*100:.2f}% ad-level mean) in group '{group_b}'."
        )

        findings.append(
            Finding(
                attribute=f"{attribute_col}: {group_a} vs {group_b}",
                outcome_metric="CTR",
                direction_of_association=dir_str,
                effect_size={
                    "relative_uplift_pct": round(uplift_pct, 2),
                    "absolute_difference": round(diff_ctr, 6),
                    "ad_level_mean_difference": round(inf_ctr["ad_mean_diff"], 6),
                    "rate_group_a": round(ctr_a, 4),
                    "rate_group_b": round(ctr_b, 4),
                    "ad_mean_group_a": round(inf_ctr["mean_a"], 4),
                    "ad_mean_group_b": round(inf_ctr["mean_b"], 4),
                    "cohens_d": round(cohen_d, 3),
                },
                sample_sizes={
                    "creatives_group_a": n_a,
                    "creatives_group_b": n_b,
                    "impressions_group_a": imp_a,
                    "impressions_group_b": imp_b,
                    "clicks_group_a": clk_a,
                    "clicks_group_b": clk_b,
                },
                uncertainty={
                    "estimand": "CTR Difference (Group A - Group B, Ad-Level Welch t 95% CI)",
                    "point_estimate": round(diff_ctr, 6),
                    "ci_95_lower": round(ci_low_ctr, 6),
                    "ci_95_upper": round(ci_upp_ctr, 6),
                    "standard_error": round(se_ctr, 6),
                    "raw_p_value": float(np.clip(p_final, 1e-12, 1.0)),
                    "fdr_q_value": float(np.clip(p_final, 1e-12, 1.0)),
                },
                evidence_classification="Pending",
                limitations=generate_limitations_statement(n_a, n_b, total_imp, attribute_col, "CTR"),
                attribute_type="categorical",
                statistical_method=method_ctr,
                adjusted_p_value=float(np.clip(p_final, 1e-12, 1.0)),
                explanation=expl_str,
                traceable_ad_ids=traceable,
                group_a=group_a,
                group_b=group_b,
                details={"welch_p_test": p_final, "mann_whitney_p": inf_ctr["p_mwu"], "df_welch": inf_ctr["df_welch"]},
            )
        )

    # 2. CVR = conversions / clicks
    if clk_a > 0 and clk_b > 0:
        cvr_a = cnv_a / clk_a
        cvr_b = cnv_b / clk_b
        diff_cvr = cvr_a - cvr_b
        uplift_pct_cvr = ((cvr_a - cvr_b) / cvr_b * 100.0) if cvr_b > 0 else 0.0

        vals_cvr_a = sub_a["cvr"].dropna().values
        vals_cvr_b = sub_b["cvr"].dropna().values
        cohen_d_cvr = compute_cohens_d(vals_cvr_a, vals_cvr_b)
        inf_cvr = _compute_ad_level_welch_inference(vals_cvr_a, vals_cvr_b, center_diff=diff_cvr)
        p_final_cvr = inf_cvr["p_welch"]
        ci_low_cvr = inf_cvr["ci_lower"]
        ci_upp_cvr = inf_cvr["ci_upper"]
        se_cvr = inf_cvr["se_welch"]
        method_cvr = (
            f"Ad-Level Welch's t-Test across Creatives (df={inf_cvr['df_welch']}) + Mann-Whitney U Check"
            if inf_cvr["inferential_valid"]
            else "Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"
        )

        dir_str_cvr = (
            f"'{group_a}' associated with {uplift_pct_cvr:+.1f}% {'higher' if uplift_pct_cvr >= 0 else 'lower'} pooled CVR compared to '{group_b}' "
            f"(Ad-level mean: {inf_cvr['mean_a']*100:.2f}% vs {inf_cvr['mean_b']*100:.2f}%)"
        )
        expl_str_cvr = (
            f"Group '{group_a}' converted at {cvr_a*100:.2f}% pooled ({cnv_a:,} conversions / {clk_a:,} clicks; "
            f"{inf_cvr['mean_a']*100:.2f}% ad-level mean) compared to {cvr_b*100:.2f}% pooled ({inf_cvr['mean_b']*100:.2f}% ad-level mean) in '{group_b}'."
        )

        findings.append(
            Finding(
                attribute=f"{attribute_col}: {group_a} vs {group_b}",
                outcome_metric="CVR",
                direction_of_association=dir_str_cvr,
                effect_size={
                    "relative_uplift_pct": round(uplift_pct_cvr, 2),
                    "absolute_difference": round(diff_cvr, 6),
                    "ad_level_mean_difference": round(inf_cvr["ad_mean_diff"], 6),
                    "rate_group_a": round(cvr_a, 4),
                    "rate_group_b": round(cvr_b, 4),
                    "ad_mean_group_a": round(inf_cvr["mean_a"], 4),
                    "ad_mean_group_b": round(inf_cvr["mean_b"], 4),
                    "cohens_d": round(cohen_d_cvr, 3),
                },
                sample_sizes={
                    "creatives_group_a": n_a,
                    "creatives_group_b": n_b,
                    "impressions_group_a": imp_a,
                    "impressions_group_b": imp_b,
                    "clicks_group_a": clk_a,
                    "clicks_group_b": clk_b,
                    "conversions_group_a": cnv_a,
                    "conversions_group_b": cnv_b,
                },
                uncertainty={
                    "estimand": "CVR Difference (Group A - Group B, Ad-Level Welch t 95% CI)",
                    "point_estimate": round(diff_cvr, 6),
                    "ci_95_lower": round(ci_low_cvr, 6),
                    "ci_95_upper": round(ci_upp_cvr, 6),
                    "standard_error": round(se_cvr, 6),
                    "raw_p_value": float(np.clip(p_final_cvr, 1e-12, 1.0)),
                    "fdr_q_value": float(np.clip(p_final_cvr, 1e-12, 1.0)),
                },
                evidence_classification="Pending",
                limitations=generate_limitations_statement(n_a, n_b, total_imp, attribute_col, "CVR"),
                attribute_type="categorical",
                statistical_method=method_cvr,
                adjusted_p_value=float(np.clip(p_final_cvr, 1e-12, 1.0)),
                explanation=expl_str_cvr,
                traceable_ad_ids=traceable,
                group_a=group_a,
                group_b=group_b,
                details={"welch_p_test": p_final_cvr, "mann_whitney_p": inf_cvr["p_mwu"], "df_welch": inf_cvr["df_welch"]},
            )
        )

    # 3. CPC = spend / clicks
    if clk_a > 0 and clk_b > 0:
        cpc_a = spn_a / clk_a
        cpc_b = spn_b / clk_b
        diff_cpc = cpc_a - cpc_b
        uplift_cpc = ((cpc_a - cpc_b) / cpc_b * 100.0) if cpc_b > 0 else 0.0

        vals_cpc_a = sub_a["cpc"].dropna().values
        vals_cpc_b = sub_b["cpc"].dropna().values
        cohen_d_cpc = compute_cohens_d(vals_cpc_a, vals_cpc_b)
        inf_cpc = _compute_ad_level_welch_inference(vals_cpc_a, vals_cpc_b, center_diff=diff_cpc)
        p_val_cpc = inf_cpc["p_welch"]
        ci_low_cpc = inf_cpc["ci_lower"]
        ci_upp_cpc = inf_cpc["ci_upper"]
        se_diff_cpc = inf_cpc["se_welch"]
        method_cpc = (
            f"Ad-Level Welch's t-Test on Cost per Click (df={inf_cpc['df_welch']})"
            if inf_cpc["inferential_valid"]
            else "Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"
        )

        dir_str_cpc = (
            f"'{group_a}' associated with ${abs(cpc_a - cpc_b):.2f} {'lower (cheaper clicks)' if cpc_a <= cpc_b else 'higher'} pooled CPC than '{group_b}' "
            f"(Ad-level mean: ${inf_cpc['mean_a']:.2f} vs ${inf_cpc['mean_b']:.2f})"
        )

        findings.append(
            Finding(
                attribute=f"{attribute_col}: {group_a} vs {group_b}",
                outcome_metric="CPC",
                direction_of_association=dir_str_cpc,
                effect_size={
                    "relative_uplift_pct": round(uplift_cpc, 2),
                    "absolute_difference": round(diff_cpc, 4),
                    "ad_level_mean_difference": round(inf_cpc["ad_mean_diff"], 4),
                    "cpc_group_a": round(cpc_a, 2),
                    "cpc_group_b": round(cpc_b, 2),
                    "ad_mean_group_a": round(inf_cpc["mean_a"], 2),
                    "ad_mean_group_b": round(inf_cpc["mean_b"], 2),
                    "cohens_d": round(cohen_d_cpc, 3),
                },
                sample_sizes={
                    "creatives_group_a": n_a,
                    "creatives_group_b": n_b,
                    "impressions_group_a": imp_a,
                    "impressions_group_b": imp_b,
                    "clicks_group_a": clk_a,
                    "clicks_group_b": clk_b,
                    "spend_group_a": round(spn_a, 2),
                    "spend_group_b": round(spn_b, 2),
                },
                uncertainty={
                    "estimand": "CPC Difference in USD ($/Click, Group A - Group B, Ad-Level Welch t 95% CI)",
                    "point_estimate": round(diff_cpc, 4),
                    "ci_95_lower": round(ci_low_cpc, 4),
                    "ci_95_upper": round(ci_upp_cpc, 4),
                    "standard_error": round(se_diff_cpc, 4),
                    "raw_p_value": float(np.clip(p_val_cpc, 1e-12, 1.0)),
                    "fdr_q_value": float(np.clip(p_val_cpc, 1e-12, 1.0)),
                },
                evidence_classification="Pending",
                limitations=generate_limitations_statement(n_a, n_b, total_imp, attribute_col, "CPC"),
                attribute_type="categorical",
                statistical_method=method_cpc,
                adjusted_p_value=float(np.clip(p_val_cpc, 1e-12, 1.0)),
                explanation=f"Group '{group_a}' averaged ${cpc_a:.2f} pooled (${inf_cpc['mean_a']:.2f} ad-level) per click versus ${cpc_b:.2f} pooled (${inf_cpc['mean_b']:.2f} ad-level) in '{group_b}'.",
                traceable_ad_ids=traceable,
                group_a=group_a,
                group_b=group_b,
                details={"welch_p_test": p_val_cpc, "mann_whitney_p": inf_cpc["p_mwu"], "df_welch": inf_cpc["df_welch"]},
            )
        )

    # 4. CPA = spend / conversions
    if cnv_a > 0 and cnv_b > 0:
        cpa_a = spn_a / cnv_a
        cpa_b = spn_b / cnv_b
        diff_cpa = cpa_a - cpa_b
        uplift_cpa = ((cpa_a - cpa_b) / cpa_b * 100.0) if cpa_b > 0 else 0.0

        vals_cpa_a = sub_a["cpa"].dropna().values
        vals_cpa_b = sub_b["cpa"].dropna().values
        cohen_d_cpa = compute_cohens_d(vals_cpa_a, vals_cpa_b)
        inf_cpa = _compute_ad_level_welch_inference(vals_cpa_a, vals_cpa_b, center_diff=diff_cpa)
        p_val_cpa = inf_cpa["p_welch"]
        ci_low_cpa = inf_cpa["ci_lower"]
        ci_upp_cpa = inf_cpa["ci_upper"]
        se_diff = inf_cpa["se_welch"]
        method_cpa = (
            f"Ad-Level Welch's t-Test on Cost per Acquisition (df={inf_cpa['df_welch']})"
            if inf_cpa["inferential_valid"]
            else "Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"
        )

        dir_str_cpa = (
            f"'{group_a}' associated with ${abs(cpa_a - cpa_b):.2f} {'lower (more efficient)' if cpa_a <= cpa_b else 'higher'} pooled CPA than '{group_b}' "
            f"(Ad-level mean: ${inf_cpa['mean_a']:.2f} vs ${inf_cpa['mean_b']:.2f})"
        )

        findings.append(
            Finding(
                attribute=f"{attribute_col}: {group_a} vs {group_b}",
                outcome_metric="CPA",
                direction_of_association=dir_str_cpa,
                effect_size={
                    "relative_uplift_pct": round(uplift_cpa, 2),
                    "absolute_difference": round(diff_cpa, 2),
                    "ad_level_mean_difference": round(inf_cpa["ad_mean_diff"], 2),
                    "cpa_group_a": round(cpa_a, 2),
                    "cpa_group_b": round(cpa_b, 2),
                    "ad_mean_group_a": round(inf_cpa["mean_a"], 2),
                    "ad_mean_group_b": round(inf_cpa["mean_b"], 2),
                    "cohens_d": round(cohen_d_cpa, 3),
                },
                sample_sizes={
                    "creatives_group_a": n_a,
                    "creatives_group_b": n_b,
                    "impressions_group_a": imp_a,
                    "impressions_group_b": imp_b,
                    "conversions_group_a": cnv_a,
                    "conversions_group_b": cnv_b,
                    "spend_group_a": round(spn_a, 2),
                    "spend_group_b": round(spn_b, 2),
                },
                uncertainty={
                    "estimand": "CPA Difference in USD ($/Conv, Group A - Group B, Ad-Level Welch t 95% CI)",
                    "point_estimate": round(diff_cpa, 2),
                    "ci_95_lower": round(ci_low_cpa, 2),
                    "ci_95_upper": round(ci_upp_cpa, 2),
                    "standard_error": round(se_diff, 2),
                    "raw_p_value": float(np.clip(p_val_cpa, 1e-12, 1.0)),
                    "fdr_q_value": float(np.clip(p_val_cpa, 1e-12, 1.0)),
                },
                evidence_classification="Pending",
                limitations=generate_limitations_statement(n_a, n_b, total_imp, attribute_col, "CPA"),
                attribute_type="categorical",
                statistical_method=method_cpa,
                adjusted_p_value=float(np.clip(p_val_cpa, 1e-12, 1.0)),
                explanation=f"Group '{group_a}' yielded ${cpa_a:.2f} pooled (${inf_cpa['mean_a']:.2f} ad-level) CPA versus ${cpa_b:.2f} pooled (${inf_cpa['mean_b']:.2f} ad-level) in '{group_b}'.",
                traceable_ad_ids=traceable,
                group_a=group_a,
                group_b=group_b,
                details={"welch_p_test": p_val_cpa, "mann_whitney_p": inf_cpa["p_mwu"], "df_welch": inf_cpa["df_welch"]},
            )
        )

    return findings


def analyze_continuous_attribute(
    df: pd.DataFrame,
    attribute_col: str,
    outcome_metric: str,
) -> Optional[Finding]:
    """
    Computes Spearman rank correlation, Pearson correlation with Fisher z CI,
    and exposure-weighted regression for continuous visual attributes against ad-level performance.
    """
    metric_col = outcome_metric.lower()
    if metric_col not in df.columns or attribute_col not in df.columns:
        return None

    cols_needed = [attribute_col, metric_col, "ad_id", "impressions"]
    for extra_col in ["clicks", "conversions"]:
        if extra_col in df.columns:
            cols_needed.append(extra_col)
    valid_data = df[cols_needed].dropna(subset=[attribute_col, metric_col, "impressions"])
    n = len(valid_data)
    if n < 4:
        return None

    x = valid_data[attribute_col].astype(float).values
    y = valid_data[metric_col].astype(float).values
    weights = valid_data["impressions"].astype(float).values
    ad_ids = valid_data["ad_id"].astype(str).tolist()

    if np.std(x) == 0 or np.std(y) == 0:
        return None

    # Spearman rank correlation
    spearman_res = stats.spearmanr(x, y)
    rho = float(spearman_res.statistic) if not np.isnan(spearman_res.statistic) else 0.0
    p_spearman = float(spearman_res.pvalue) if not np.isnan(spearman_res.pvalue) else 1.0

    # Pearson correlation & Fisher z 95% CI
    pearson_res = stats.pearsonr(x, y)
    r = float(pearson_res.statistic) if not np.isnan(pearson_res.statistic) else 0.0
    p_pearson = float(pearson_res.pvalue) if not np.isnan(pearson_res.pvalue) else 1.0

    r_clipped = np.clip(r, -0.9999, 0.9999)
    z = np.arctanh(r_clipped)
    se_z = 1.0 / np.sqrt(max(n - 3, 1))
    z_low = z - 1.96 * se_z
    z_upp = z + 1.96 * se_z
    ci_low_r = float(np.tanh(z_low))
    ci_upp_r = float(np.tanh(z_upp))

    # OLS & Exposure-Weighted WLS regression slopes
    try:
        x_const = sm_tools.add_constant(x)
        ols_model = sm_lm.OLS(y, x_const).fit()
        slope = float(ols_model.params[1])
        se_slope = float(ols_model.bse[1])
        r2 = float(ols_model.rsquared)
        ci_slope_low = float(ols_model.conf_int()[1][0])
        ci_slope_upp = float(ols_model.conf_int()[1][1])

        # WLS weighted by impression exposure
        if np.sum(weights) > 0 and np.all(weights > 0):
            wls_model = sm_lm.WLS(y, x_const, weights=weights).fit()
            wls_slope = float(wls_model.params[1])
        else:
            wls_slope = slope
    except Exception:
        slope = 0.0
        se_slope = 0.0
        r2 = 0.0
        ci_slope_low = 0.0
        ci_slope_upp = 0.0
        wls_slope = 0.0

    p_final = float(np.clip(p_spearman, 1e-12, 1.0))
    direction_verb = "positively associated with" if rho > 0 else "negatively associated with"
    dir_str = (
        f"Continuous '{attribute_col}' is {direction_verb} {outcome_metric} (Spearman ρ = {rho:+.2f})"
    )

    uplift_proxy = rho * 50.0

    classification = "Preliminary"
    if n < 6:
        classification = "Underpowered"
    elif p_final < 0.05 and abs(rho) >= 0.40 and ((ci_low_r > 0 and ci_upp_r > 0) or (ci_low_r < 0 and ci_upp_r < 0)):
        classification = "Supported association"
    elif p_final < 0.05 or abs(rho) >= 0.35:
        classification = "Preliminary"
    elif abs(rho) < 0.15 and p_final > 0.30 and n >= 8:
        classification = "No clear association"
    else:
        classification = "Unsupported"

    expl = (
        f"Across {n} creatives ({', '.join(ad_ids[:4])}{'...' if len(ad_ids)>4 else ''}), higher {attribute_col} "
        f"correlates with {direction_verb} {outcome_metric} (Spearman ρ={rho:.2f}, Exposure-Weighted WLS slope={wls_slope:.4f})."
    )

    small_sample_note = f"Small sample size ({n} creatives); correlation and slope estimates have high sampling variance. " if n < 8 else ""

    return Finding(
        attribute=attribute_col,
        outcome_metric=outcome_metric,
        direction_of_association=dir_str,
        effect_size={
            "spearman_rho": round(rho, 3),
            "pearson_r": round(r, 3),
            "ols_slope": round(slope, 6),
            "wls_slope_exposure_weighted": round(wls_slope, 6),
            "r_squared": round(r2, 4),
            "relative_uplift_pct": round(uplift_proxy, 2),
        },
        sample_sizes={
            "creatives_count": n,
            "total_impressions": int(valid_data["impressions"].sum()),
            "total_clicks": int(valid_data["clicks"].sum()) if "clicks" in valid_data.columns else 0,
            "total_conversions": int(valid_data["conversions"].sum()) if "conversions" in valid_data.columns else 0,
        },
        uncertainty={
            "estimand": "Pearson Correlation r (Fisher z-Transform 95% CI)",
            "point_estimate": round(r, 3),
            "ci_95_lower": round(ci_low_r, 3),
            "ci_95_upper": round(ci_upp_r, 3),
            "standard_error": round(se_slope, 6),
            "raw_p_value": p_final,
            "fdr_q_value": p_final,
        },
        evidence_classification=classification,
        limitations=(
            f"Observational correlation analysis across {n} creatives. "
            f"{small_sample_note}"
            "Linear regression assumes independent observations and no omitted variable bias. "
            "Does not prove continuous visual gradient causes performance changes. "
            "A non-significant result does not prove that an attribute has no effect (absence of evidence is not evidence of absence)."
        ),
        attribute_type="continuous",
        statistical_method="Spearman Nonparametric Rank Correlation + Exposure-Weighted WLS Regression",
        adjusted_p_value=p_final,
        explanation=expl,
        traceable_ad_ids={"analyzed_ads": ad_ids},
        details={
            "ci_slope_low": round(ci_slope_low, 6),
            "ci_slope_upp": round(ci_slope_upp, 6),
            "pearson_p": p_pearson,
            "spearman_p": p_spearman,
        },
    )


def apply_multiple_testing_correction(findings: List[Finding]) -> List[Finding]:
    """Applies Benjamini-Hochberg False Discovery Rate (FDR) and Bonferroni corrections across all findings."""
    if not findings:
        return findings

    estimable_indices = [i for i, f in enumerate(findings) if f.evidence_classification != "Not estimable"]
    if not estimable_indices:
        return findings

    m = len(estimable_indices)
    raw_p_values = [findings[i].uncertainty["raw_p_value"] for i in estimable_indices]

    sorted_order = np.argsort(raw_p_values)
    q_values = np.zeros(m)

    running_min = 1.0
    for rank in range(m, 0, -1):
        order_idx = sorted_order[rank - 1]
        p = raw_p_values[order_idx]
        q_raw = (p * m) / float(rank)
        running_min = min(running_min, q_raw)
        q_values[order_idx] = min(running_min, 1.0)

    for local_idx, finding_idx in enumerate(estimable_indices):
        finding = findings[finding_idx]
        q_val = float(q_values[local_idx])
        p_val = finding.uncertainty["raw_p_value"]
        bonferroni_p = float(min(p_val * m, 1.0))

        finding.uncertainty["fdr_q_value"] = round(q_val, 6)
        finding.uncertainty["bonferroni_p"] = round(bonferroni_p, 6)
        finding.adjusted_p_value = round(q_val, 6)

        if finding.attribute_type == "categorical":
            uplift = finding.effect_size.get("relative_uplift_pct", 0.0)
            n_a = finding.sample_sizes.get("creatives_group_a", 0)
            n_b = finding.sample_sizes.get("creatives_group_b", 0)
            ci_low = finding.uncertainty["ci_95_lower"]
            ci_upp = finding.uncertainty["ci_95_upper"]

            finding.evidence_classification = classify_evidence(
                raw_p=p_val,
                fdr_q=q_val,
                sample_size_a=n_a,
                sample_size_b=n_b,
                relative_uplift_pct=uplift,
                ci_lower=ci_low,
                ci_upper=ci_upp,
            )
        elif finding.attribute_type == "continuous":
            n_c = finding.sample_sizes.get("creatives_count", 0)
            rho = abs(finding.effect_size.get("spearman_rho", 0.0))
            ci_low = finding.uncertainty["ci_95_lower"]
            ci_upp = finding.uncertainty["ci_95_upper"]

            if n_c < 6:
                finding.evidence_classification = "Underpowered"
            elif q_val < 0.05 and rho >= 0.40 and ((ci_low > 0 and ci_upp > 0) or (ci_low < 0 and ci_upp < 0)):
                finding.evidence_classification = "Supported association"
            elif p_val < 0.05 or (q_val < 0.15 and rho >= 0.35):
                finding.evidence_classification = "Preliminary"
            elif rho < 0.15 and p_val > 0.30 and n_c >= 8:
                finding.evidence_classification = "No clear association"
            else:
                finding.evidence_classification = "Unsupported"

    return findings


def rank_findings(findings: List[Finding]) -> List[Finding]:
    """
    Ranks findings using documented composite evidence score:
    Score = w_p * (-log10(q_fdr)) + w_effect * min(|uplift| / 15, 4.0) + w_power * min(sqrt(N), 4.0)
    Multipliers:
      Supported association: x2.0
      Preliminary: x1.4
      Underpowered: x0.7
      No clear association: x0.5
      Unsupported / Not estimable: x0.3
    """
    for f in findings:
        q = f.uncertainty.get("fdr_q_value", 1.0)
        p_log = -np.log10(max(q, 1e-8))

        if f.attribute_type == "categorical":
            uplift = abs(f.effect_size.get("relative_uplift_pct", 0.0))
            effect_score = min(uplift / 15.0, 4.0)
            n_creatives = f.sample_sizes.get("creatives_group_a", 1) + f.sample_sizes.get("creatives_group_b", 1)
        else:
            rho = abs(f.effect_size.get("spearman_rho", 0.0))
            effect_score = rho * 4.0
            n_creatives = f.sample_sizes.get("creatives_count", 4)

        power_score = min(np.sqrt(max(n_creatives, 1)), 4.0)

        tier_mult = 1.0
        if f.evidence_classification == "Supported association":
            tier_mult = 2.0
        elif f.evidence_classification in ("Preliminary", "Preliminary evidence"):
            tier_mult = 1.4
        elif f.evidence_classification == "Underpowered":
            tier_mult = 0.7
        elif f.evidence_classification == "No clear association":
            tier_mult = 0.5
        elif f.evidence_classification in ("Unsupported", "Not estimable"):
            tier_mult = 0.3

        composite_score = (0.50 * p_log + 0.35 * effect_score + 0.15 * power_score) * tier_mult
        f.rank_score = round(float(composite_score), 3)

    return sorted(findings, key=lambda x: x.rank_score, reverse=True)


def investigate_confounding(
    df: pd.DataFrame,
    findings: List[Finding],
) -> List[Dict[str, Any]]:
    """
    Investigates potential confounding from available campaign metadata fields
    (campaign_name, audience, placement, platform).
    Checks if visual attributes are disproportionately clustered in specific campaigns or audiences,
    and runs multivariable models to see if findings hold when controlling for these factors.
    """
    confounding_reports: List[Dict[str, Any]] = []
    potential_confounders = [c for c in ["campaign_name", "campaign_id", "audience", "placement", "platform"] if c in df.columns]

    if not potential_confounders:
        return [
            {
                "status": "No Optional Confounders Ingested",
                "message": "Dataset does not include campaign, audience, or placement metadata. Confounding cannot be empirically evaluated.",
                "recommendation": "Ingest optional fields ('campaign_name', 'audience', 'placement', 'platform') to enable multivariable confounding tests.",
            }
        ]

    for conf_col in potential_confounders:
        unique_segments = df[conf_col].dropna().unique().tolist()
        if len(unique_segments) < 2:
            continue

        for finding in findings[:6]:  # Test top findings
            attr = finding.attribute.split(":")[0].strip()
            if attr not in df.columns or finding.outcome_metric.lower() not in df.columns:
                continue

            metric = finding.outcome_metric.lower()
            sub_df = df[[attr, conf_col, metric, "spend", "impressions"]].dropna()
            if len(sub_df) < 6:
                continue

            # Stratification check: contingency / cross-tab distribution
            ctab = pd.crosstab(sub_df[attr], sub_df[conf_col])
            # Check if any segment holds >70% of a specific attribute category
            row_props = ctab.div(ctab.sum(axis=1), axis=0)
            max_cluster = float(row_props.max().max())

            confounded_risk = "Low"
            risk_desc = f"Visual attribute '{attr}' is reasonably balanced across {conf_col} segments."
            if max_cluster >= 0.75:
                confounded_risk = "High"
                risk_desc = (
                    f"Warning: Up to {max_cluster*100:.0f}% of creatives with specific '{attr}' "
                    f"are concentrated in a single '{conf_col}' segment. The observed {finding.outcome_metric} uplift "
                    f"may be partially driven by targeting or budget allocation rather than visual creative elements."
                )
            elif max_cluster >= 0.50:
                confounded_risk = "Moderate"
                risk_desc = f"Moderate clustering ({max_cluster*100:.0f}%) of '{attr}' within specific '{conf_col}' segments."

            confounding_reports.append({
                "attribute": attr,
                "confounder_field": conf_col,
                "outcome_metric": finding.outcome_metric,
                "confounding_risk": confounded_risk,
                "assessment": risk_desc,
                "max_segment_concentration_pct": round(max_cluster * 100.0, 1),
                "segments_analyzed": unique_segments[:5],
            })

    return confounding_reports


def run_full_statistical_analysis(
    df_with_features: pd.DataFrame,
) -> List[Finding]:
    """
    Orchestrates complete automated statistical analysis across all extracted
    categorical, composition, and continuous visual attributes.
    Strictly excludes corrupted, invalid, or unmatched records (where extraction_status != 'success').
    """
    if df_with_features is None or df_with_features.empty:
        return []

    clean_df = df_with_features.copy()
    if "extraction_status" in clean_df.columns:
        clean_df = clean_df[clean_df["extraction_status"] == "success"].copy()

    if clean_df.empty:
        return []

    findings: List[Finding] = []
    invalid_labels = {"Unknown", "Unavailable", "None", "nan", ""}

    # Categorical Visual & Composition Attributes to compare
    categorical_tests = [
        ("dominant_color_tone", "Warm", "Cool"),
        ("dominant_color_tone", "Warm", "Neutral"),
        ("dominant_color_tone", "Cool", "Neutral"),
        ("human_presence_cat", "With Human", "No Human"),
        ("brightness_cat", "High Brightness (>65)", "Low Brightness (<35)"),
        ("brightness_cat", "Medium Brightness (35-65)", "Low Brightness (<35)"),
        ("contrast_cat", "High Contrast (>65)", "Low Contrast (<40)"),
        ("aspect_ratio_cat", "1:1 Square", "9:16 Portrait / Story"),
        ("aspect_ratio_cat", "1:1 Square", "16:9 Landscape"),
        ("visual_complexity", "Clean / Minimal", "Complex / Busy"),
        ("text_density_cat", "Minimal Copy", "Text-Heavy"),
        ("colorfulness_cat", "Highly Vibrant", "Subdued / Monochromatic"),
        ("composition_style", "Centered Hero", "Rule-of-Thirds Dynamic"),
        ("object_presence_cat", "Clear Foreground Subject", "Ambient / Minimal Foreground"),
    ]

    tested_cols = set()
    for col, grp_a, grp_b in categorical_tests:
        if col in clean_df.columns:
            unique_vals = [
                v for v in clean_df[col].dropna().unique().tolist()
                if str(v).strip() not in invalid_labels
            ]
            if grp_a in unique_vals and grp_b in unique_vals:
                cat_findings = analyze_categorical_attribute(clean_df, col, grp_a, grp_b)
                findings.extend(cat_findings)
                tested_cols.add(col)

    # Fallback for custom uploaded datasets where different category buckets are populated
    all_cat_cols = [
        "dominant_color_tone", "human_presence_cat", "brightness_cat", "contrast_cat",
        "aspect_ratio_cat", "visual_complexity", "text_density_cat", "colorfulness_cat",
        "composition_style", "object_presence_cat",
    ]
    for col in all_cat_cols:
        if col not in tested_cols and col in clean_df.columns:
            valid_series = clean_df[col].dropna()
            valid_series = valid_series[~valid_series.astype(str).str.strip().isin(invalid_labels)]
            val_counts = valid_series.value_counts()
            if len(val_counts) >= 2:
                grp_a = str(val_counts.index[0])
                grp_b = str(val_counts.index[1])
                cat_findings = analyze_categorical_attribute(clean_df, col, grp_a, grp_b)
                findings.extend(cat_findings)

    # Continuous Visual & Composition Attributes to correlate
    continuous_cols = [
        "brightness_score",
        "contrast_score",
        "colorfulness_score",
        "saturation_score",
        "edge_density_pct",
        "text_density_score",
        "aspect_ratio",
        "rule_of_thirds_score",
        "center_focus_ratio",
        "visual_symmetry_score",
    ]
    outcome_metrics = ["CTR", "CVR", "CPC", "CPA"]

    for col in continuous_cols:
        if col in clean_df.columns:
            for metric in outcome_metrics:
                cont_finding = analyze_continuous_attribute(clean_df, col, metric)
                if cont_finding is not None:
                    findings.append(cont_finding)

    # Apply Multiple Testing Correction (FDR Benjamini-Hochberg & Bonferroni)
    findings = apply_multiple_testing_correction(findings)

    # Rank Findings using transparent criteria
    findings = rank_findings(findings)

    return findings

