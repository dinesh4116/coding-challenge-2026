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
      - Aggregate ROAS = total revenue / total spend (only when revenue or conversion_value is present)
    - Unweighted Ad-Level Averages (kept explicitly separate from pooled campaign metrics):
      - mean_ad_ctr, mean_ad_cvr, mean_ad_cpc, mean_ad_cpa, mean_ad_roas
      - median_ad_ctr, median_ad_cvr, median_ad_cpc, median_ad_cpa, median_ad_roas
    Undefined metrics are represented as None (unavailable, never 0.0).
    """
    if df is None or df.empty:
        return {
            "total_creatives": 0,
            "total_spend": 0.0,
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "total_revenue": None,
            "aggregate_ctr": None,
            "aggregate_cvr": None,
            "aggregate_cpc": None,
            "aggregate_cpa": None,
            "aggregate_roas": None,
            "mean_ad_ctr": None,
            "mean_ad_cvr": None,
            "mean_ad_cpc": None,
            "mean_ad_cpa": None,
            "mean_ad_roas": None,
            "median_ad_ctr": None,
            "median_ad_cvr": None,
            "median_ad_cpc": None,
            "median_ad_cpa": None,
            "median_ad_roas": None,
        }

    total_imp = int(df["impressions"].sum())
    total_clk = int(df["clicks"].sum())
    total_cnv = int(df["conversions"].sum())
    total_spn = float(df["spend"].sum())

    rev_col = "revenue" if "revenue" in df.columns else ("conversion_value" if "conversion_value" in df.columns else None)
    total_rev: Optional[float] = None
    if rev_col is not None:
        rev_series = pd.to_numeric(df[rev_col], errors="coerce").dropna()
        if not rev_series.empty:
            total_rev = float(rev_series.sum())

    def _col_stat(col_name: str, stat_fn: str) -> Optional[float]:
        if col_name not in df.columns:
            return None
        s = pd.to_numeric(df[col_name], errors="coerce").dropna()
        if s.empty:
            return None
        return float(s.mean() if stat_fn == "mean" else s.median())

    mean_roas = _col_stat("roas", "mean")
    median_roas = _col_stat("roas", "median")
    if mean_roas is None and rev_col is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            spn_s = pd.to_numeric(df["spend"], errors="coerce")
            rev_s = pd.to_numeric(df[rev_col], errors="coerce")
            roas_s = pd.Series(np.where((spn_s > 0) & (~np.isnan(rev_s)), rev_s / spn_s, np.nan)).dropna()
            if not roas_s.empty:
                mean_roas = float(roas_s.mean())
                median_roas = float(roas_s.median())

    return {
        "total_creatives": len(df),
        "total_spend": total_spn,
        "total_impressions": total_imp,
        "total_clicks": total_clk,
        "total_conversions": total_cnv,
        "total_revenue": total_rev,
        "aggregate_ctr": (total_clk / total_imp) if total_imp > 0 else None,
        "aggregate_cvr": (total_cnv / total_clk) if total_clk > 0 else None,
        "aggregate_cpc": (total_spn / total_clk) if total_clk > 0 else None,
        "aggregate_cpa": (total_spn / total_cnv) if total_cnv > 0 else None,
        "aggregate_roas": (total_rev / total_spn) if (total_rev is not None and total_spn > 0) else None,
        "mean_ad_ctr": _col_stat("ctr", "mean"),
        "mean_ad_cvr": _col_stat("cvr", "mean"),
        "mean_ad_cpc": _col_stat("cpc", "mean"),
        "mean_ad_cpa": _col_stat("cpa", "mean"),
        "mean_ad_roas": mean_roas,
        "median_ad_ctr": _col_stat("ctr", "median"),
        "median_ad_cvr": _col_stat("cvr", "median"),
        "median_ad_cpc": _col_stat("cpc", "median"),
        "median_ad_cpa": _col_stat("cpa", "median"),
        "median_ad_roas": median_roas,
    }


def compute_wilson_ci(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Computes the Wilson score 95% confidence interval for a binomial proportion (successes / trials).
    Returns (0.0, 0.0) when trials <= 0.
    """
    if trials <= 0:
        return 0.0, 0.0
    n = float(trials)
    p = float(np.clip(successes / n, 0.0, 1.0))
    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half_width = (z * np.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)) / denom
    return float(max(0.0, center - half_width)), float(min(1.0, center + half_width))


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


def compare_creative_variants(
    row_a: Union[pd.Series, Dict[str, Any]],
    row_b: Union[pd.Series, Dict[str, Any]],
    alpha: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Performs rigorous statistical comparisons between two individual creative variants (Creative A vs Creative B)
    across CTR (Two-Proportion Z-Test + 95% Wald CI), CVR (Two-Proportion Z-Test / Fisher's Exact Test + 95% CI),
    CPC, CPA, and ROAS (when revenue is available).
    Explicitly handles zero denominators and underpowered exposure volumes without fabricating significance.
    """
    ad_a = str(row_a.get("ad_id", "Creative A"))
    ad_b = str(row_b.get("ad_id", "Creative B"))

    imp_a = int(float(row_a.get("impressions", 0) or 0))
    clk_a = int(float(row_a.get("clicks", 0) or 0))
    cnv_a = int(float(row_a.get("conversions", 0) or 0))
    spn_a = float(row_a.get("spend", 0.0) or 0.0)

    imp_b = int(float(row_b.get("impressions", 0) or 0))
    clk_b = int(float(row_b.get("clicks", 0) or 0))
    cnv_b = int(float(row_b.get("conversions", 0) or 0))
    spn_b = float(row_b.get("spend", 0.0) or 0.0)

    results: List[Dict[str, Any]] = []

    # 1. CTR Comparison (clicks / impressions)
    if imp_a > 0 and imp_b > 0:
        ctr_a = clk_a / imp_a
        ctr_b = clk_b / imp_b
        diff, ci_low, ci_upp, se = compute_proportion_difference_ci(clk_a, imp_a, clk_b, imp_b, alpha=alpha)
        rel_uplift = ((ctr_a - ctr_b) / ctr_b * 100.0) if ctr_b > 0 else 0.0

        p_pool = (clk_a + clk_b) / float(imp_a + imp_b)
        se_pool = float(np.sqrt(max(p_pool * (1.0 - p_pool) * (1.0 / imp_a + 1.0 / imp_b), 0.0)))
        if se_pool > 1e-12:
            z_stat = diff / se_pool
            p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(z_stat))))
        else:
            z_stat = 0.0
            p_val = 1.0

        if imp_a < 100 or imp_b < 100 or (clk_a + clk_b) < 10:
            verdict = "Underpowered Exposure Volume"
        elif p_val < alpha and ((ci_low > 0 and ci_upp > 0) or (ci_low < 0 and ci_upp > 0)):
            verdict = "Statistically Significant Difference (p < 0.05)"
        else:
            verdict = "No Statistically Significant Difference"

        results.append({
            "metric": "CTR",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": round(ctr_a, 6),
            "value_b": round(ctr_b, 6),
            "absolute_difference": round(diff, 6),
            "relative_uplift_pct": round(rel_uplift, 2),
            "ci_95_lower": round(ci_low, 6),
            "ci_95_upper": round(ci_upp, 6),
            "p_value": round(float(np.clip(p_val, 1e-12, 1.0)), 6),
            "statistical_method": "Two-Proportion Z-Test (Clicks / Impressions)",
            "verdict": verdict,
            "limitations": "Observational comparison between two creatives; exposure volume and targeting differences may confound CTR.",
        })
    else:
        results.append({
            "metric": "CTR",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": None,
            "value_b": None,
            "absolute_difference": None,
            "relative_uplift_pct": None,
            "ci_95_lower": None,
            "ci_95_upper": None,
            "p_value": None,
            "statistical_method": "Not Estimable (0 Impressions)",
            "verdict": "Not estimable",
            "limitations": "One or both creatives have 0 impressions; CTR cannot be calculated.",
        })

    # 2. CVR Comparison (conversions / clicks)
    if clk_a > 0 and clk_b > 0:
        cvr_a = cnv_a / clk_a
        cvr_b = cnv_b / clk_b
        diff_cvr, ci_low_cvr, ci_upp_cvr, se_cvr = compute_proportion_difference_ci(cnv_a, clk_a, cnv_b, clk_b, alpha=alpha)
        rel_uplift_cvr = ((cvr_a - cvr_b) / cvr_b * 100.0) if cvr_b > 0 else 0.0

        non_cnv_a = max(clk_a - cnv_a, 0)
        non_cnv_b = max(clk_b - cnv_b, 0)
        if min(cnv_a, cnv_b, non_cnv_a, non_cnv_b) < 5:
            try:
                _, p_val_cvr = stats.fisher_exact([[cnv_a, non_cnv_a], [cnv_b, non_cnv_b]], alternative="two-sided")
                p_val_cvr = float(p_val_cvr)
                method_cvr = "Fisher's Exact Test (Small Conversion Counts)"
            except Exception:
                p_val_cvr = 1.0
                method_cvr = "Two-Proportion Z-Test (Clicks / Conversions)"
        else:
            p_pool_cvr = (cnv_a + cnv_b) / float(clk_a + clk_b)
            se_pool_cvr = float(np.sqrt(max(p_pool_cvr * (1.0 - p_pool_cvr) * (1.0 / clk_a + 1.0 / clk_b), 0.0)))
            p_val_cvr = float(2.0 * (1.0 - stats.norm.cdf(abs(diff_cvr / se_pool_cvr)))) if se_pool_cvr > 1e-12 else 1.0
            method_cvr = "Two-Proportion Z-Test (Conversions / Clicks)"

        if clk_a < 20 or clk_b < 20 or (cnv_a + cnv_b) < 5:
            verdict_cvr = "Underpowered Exposure Volume"
        elif p_val_cvr < alpha and ((ci_low_cvr > 0 and ci_upp_cvr > 0) or (ci_low_cvr < 0 and ci_upp_cvr > 0)):
            verdict_cvr = "Statistically Significant Difference (p < 0.05)"
        else:
            verdict_cvr = "No Statistically Significant Difference"

        results.append({
            "metric": "CVR",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": round(cvr_a, 6),
            "value_b": round(cvr_b, 6),
            "absolute_difference": round(diff_cvr, 6),
            "relative_uplift_pct": round(rel_uplift_cvr, 2),
            "ci_95_lower": round(ci_low_cvr, 6),
            "ci_95_upper": round(ci_upp_cvr, 6),
            "p_value": round(float(np.clip(p_val_cvr, 1e-12, 1.0)), 6),
            "statistical_method": method_cvr,
            "verdict": verdict_cvr,
            "limitations": "Observational post-click conversion comparison; landing page and audience intent may confound CVR.",
        })
    else:
        results.append({
            "metric": "CVR",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": None,
            "value_b": None,
            "absolute_difference": None,
            "relative_uplift_pct": None,
            "ci_95_lower": None,
            "ci_95_upper": None,
            "p_value": None,
            "statistical_method": "Not Estimable (0 Clicks)",
            "verdict": "Not estimable",
            "limitations": "One or both creatives have 0 clicks; CVR cannot be calculated.",
        })

    # 3. CPA Comparison (spend / conversions)
    if cnv_a > 0 and cnv_b > 0:
        cpa_a = spn_a / cnv_a
        cpa_b = spn_b / cnv_b
        diff_cpa = cpa_a - cpa_b
        rel_cpa = ((cpa_a - cpa_b) / cpa_b * 100.0) if cpa_b > 0 else 0.0
        results.append({
            "metric": "CPA",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": round(cpa_a, 2),
            "value_b": round(cpa_b, 2),
            "absolute_difference": round(diff_cpa, 2),
            "relative_uplift_pct": round(rel_cpa, 2),
            "ci_95_lower": None,
            "ci_95_upper": None,
            "p_value": None,
            "statistical_method": "Descriptive Cost Ratio Comparison (n=1 vs n=1 Creative)",
            "verdict": "Descriptive Only (Single-Ad Cost Ratio)",
            "limitations": "Single-record spend/conversion ratios lack within-creative variance; use CVR test or multi-ad cohort Welch's t-test for significance.",
        })

    # 4. ROAS Comparison (revenue / spend, only when revenue is available)
    rev_a_raw = row_a.get("revenue", None)
    rev_b_raw = row_b.get("revenue", None)
    if rev_a_raw is not None and rev_b_raw is not None and not pd.isna(rev_a_raw) and not pd.isna(rev_b_raw) and spn_a > 0 and spn_b > 0:
        roas_a = float(rev_a_raw) / spn_a
        roas_b = float(rev_b_raw) / spn_b
        diff_roas = roas_a - roas_b
        rel_roas = ((roas_a - roas_b) / roas_b * 100.0) if roas_b > 0 else 0.0
        results.append({
            "metric": "ROAS",
            "creative_a": ad_a,
            "creative_b": ad_b,
            "value_a": round(roas_a, 3),
            "value_b": round(roas_b, 3),
            "absolute_difference": round(diff_roas, 3),
            "relative_uplift_pct": round(rel_roas, 2),
            "ci_95_lower": None,
            "ci_95_upper": None,
            "p_value": None,
            "statistical_method": "Descriptive Return on Ad Spend Comparison (n=1 vs n=1 Creative)",
            "verdict": "Descriptive Only (Single-Ad ROAS Ratio)",
            "limitations": "Single-record revenue/spend ratios lack within-creative variance; evaluate multi-ad cohorts for inferential ROAS testing.",
        })

    return results


def rank_creatives(
    df: pd.DataFrame,
    primary_metric: str = "composite",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Ranks individual creatives with statistical rigor:
    - Computes 95% Wilson confidence intervals for CTR and CVR.
    - Benchmarks each creative's CTR against the rest-of-campaign pooled baseline using a Two-Proportion Z-Test
      with Benjamini-Hochberg FDR multiple-testing correction.
    - Flags low-exposure creatives ('Low Volume / High Variance', 'Moderate Exposure', 'High Reliability').
    - Computes a volume-regularized Composite Rank Score (0-100) using Empirical Bayes shrinkage toward
      the campaign pooled mean so noisy low-denominator creatives do not falsely outrank proven winners.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    work_df = df.copy()
    kpis = compute_aggregate_kpis(work_df)
    total_imp = kpis["total_impressions"]
    total_clk = kpis["total_clicks"]
    total_cnv = kpis["total_conversions"]
    total_spn = kpis["total_spend"]
    pooled_ctr = kpis["aggregate_ctr"] or 0.0
    pooled_cvr = kpis["aggregate_cvr"] or 0.0
    pooled_cpa = kpis["aggregate_cpa"]
    pooled_cpc = kpis["aggregate_cpc"]
    pooled_roas = kpis["aggregate_roas"]

    rows_meta: List[Dict[str, Any]] = []
    raw_p_list: List[float] = []

    for _, row in work_df.iterrows():
        imp = int(float(row.get("impressions", 0) or 0))
        clk = int(float(row.get("clicks", 0) or 0))
        cnv = int(float(row.get("conversions", 0) or 0))
        spn = float(row.get("spend", 0.0) or 0.0)

        ctr_val = (clk / imp) if imp > 0 else np.nan
        cvr_val = (cnv / clk) if clk > 0 else np.nan
        cpc_val = (spn / clk) if clk > 0 else np.nan
        cpa_val = (spn / cnv) if cnv > 0 else np.nan
        roas_val = row.get("roas", np.nan)
        if pd.isna(roas_val) and "revenue" in work_df.columns and pd.notna(row.get("revenue")) and spn > 0:
            roas_val = float(row["revenue"]) / spn

        ctr_low, ctr_upp = compute_wilson_ci(clk, imp, alpha=alpha)
        cvr_low, cvr_upp = compute_wilson_ci(cnv, clk, alpha=alpha)

        # Two-proportion Z-test of this creative's CTR vs Rest of Campaign
        rest_imp = max(total_imp - imp, 0)
        rest_clk = max(total_clk - clk, 0)
        if imp > 0 and rest_imp > 0 and total_clk > 0:
            p_pool = total_clk / float(total_imp)
            se_pool = float(np.sqrt(max(p_pool * (1.0 - p_pool) * (1.0 / imp + 1.0 / rest_imp), 0.0)))
            diff_vs_rest = (clk / imp) - (rest_clk / rest_imp)
            z_val = (diff_vs_rest / se_pool) if se_pool > 1e-12 else 0.0
            p_vs_rest = float(2.0 * (1.0 - stats.norm.cdf(abs(z_val))))
        else:
            p_vs_rest = 1.0

        raw_p_list.append(float(np.clip(p_vs_rest, 1e-12, 1.0)))

        # Exposure reliability tier
        if imp >= 5000 and clk >= 50:
            rel_tier = "High Reliability"
            rel_weight = 1.0
        elif imp >= 1000 and clk >= 20:
            rel_tier = "Moderate Exposure"
            rel_weight = 0.80
        else:
            rel_tier = "Low Volume / High Variance"
            rel_weight = 0.45

        # Empirical Bayes shrunk CTR & CVR (prior weight = 2,000 impressions / 50 clicks)
        eb_ctr = ((clk + 2000.0 * pooled_ctr) / (imp + 2000.0)) if (imp > 0 and pooled_ctr > 0) else 0.0
        eb_cvr = ((cnv + 50.0 * pooled_cvr) / (clk + 50.0)) if (clk > 0 and pooled_cvr > 0) else 0.0

        ctr_ratio = (eb_ctr / pooled_ctr) if pooled_ctr > 0 else 1.0
        cvr_ratio = (eb_cvr / pooled_cvr) if pooled_cvr > 0 else 1.0
        cpa_eff_ratio = (pooled_cpa / cpa_val) if (pooled_cpa and not np.isnan(cpa_val) and cpa_val > 0) else 0.8
        roas_ratio = (float(roas_val) / pooled_roas) if (pooled_roas and not pd.isna(roas_val) and pooled_roas > 0) else 1.0

        if pooled_roas is not None and not pd.isna(roas_val):
            raw_composite = (0.35 * ctr_ratio + 0.30 * cvr_ratio + 0.20 * cpa_eff_ratio + 0.15 * roas_ratio) * 50.0 * rel_weight
        else:
            raw_composite = (0.45 * ctr_ratio + 0.35 * cvr_ratio + 0.20 * cpa_eff_ratio) * 50.0 * rel_weight

        composite_score = round(float(np.clip(raw_composite, 0.0, 100.0)), 2)

        # Lift vs campaign pooled baseline on requested metric
        m_key = primary_metric.lower()
        if m_key == "cvr":
            lift_pct = ((cvr_val - pooled_cvr) / pooled_cvr * 100.0) if (not np.isnan(cvr_val) and pooled_cvr > 0) else np.nan
        elif m_key == "cpc":
            lift_pct = ((cpc_val - pooled_cpc) / pooled_cpc * 100.0) if (not np.isnan(cpc_val) and pooled_cpc and pooled_cpc > 0) else np.nan
        elif m_key == "cpa":
            lift_pct = ((cpa_val - pooled_cpa) / pooled_cpa * 100.0) if (not np.isnan(cpa_val) and pooled_cpa and pooled_cpa > 0) else np.nan
        elif m_key == "roas":
            lift_pct = ((float(roas_val) - pooled_roas) / pooled_roas * 100.0) if (not pd.isna(roas_val) and pooled_roas and pooled_roas > 0) else np.nan
        else:
            lift_pct = ((ctr_val - pooled_ctr) / pooled_ctr * 100.0) if (not np.isnan(ctr_val) and pooled_ctr > 0) else np.nan

        rows_meta.append({
            "ctr_ci_lower": round(ctr_low, 6),
            "ctr_ci_upper": round(ctr_upp, 6),
            "ctr_ci_95": f"[{ctr_low*100:.2f}%, {ctr_upp*100:.2f}%]" if imp > 0 else "Unavailable",
            "cvr_ci_lower": round(cvr_low, 6),
            "cvr_ci_upper": round(cvr_upp, 6),
            "cvr_ci_95": f"[{cvr_low*100:.2f}%, {cvr_upp*100:.2f}%]" if clk > 0 else "Unavailable",
            "reliability_tier": rel_tier,
            "composite_rank_score": composite_score,
            "lift_vs_campaign_pct": round(float(lift_pct), 2) if not pd.isna(lift_pct) else np.nan,
            "vs_campaign_p_value": round(float(np.clip(p_vs_rest, 1e-12, 1.0)), 6),
        })

    # Benjamini-Hochberg FDR across creatives
    m_tests = len(raw_p_list)
    q_vals = np.ones(m_tests)
    if m_tests > 0:
        order = np.argsort(raw_p_list)
        run_min = 1.0
        for r_idx in range(m_tests, 0, -1):
            orig_i = order[r_idx - 1]
            q_raw = (raw_p_list[orig_i] * m_tests) / float(r_idx)
            run_min = min(run_min, q_raw)
            q_vals[orig_i] = min(run_min, 1.0)

    for i, meta in enumerate(rows_meta):
        q_v = float(q_vals[i])
        meta["vs_campaign_fdr_q"] = round(q_v, 6)
        if meta["reliability_tier"] == "Low Volume / High Variance":
            meta["significance_vs_baseline"] = "Underpowered (Low Exposure)"
        elif q_v < alpha:
            meta["significance_vs_baseline"] = "Significant vs. Campaign (FDR q < 0.05)"
        elif meta["vs_campaign_p_value"] < alpha:
            meta["significance_vs_baseline"] = "Nominal Signal (p < 0.05, q >= 0.05)"
        else:
            meta["significance_vs_baseline"] = "Within Campaign Baseline Variance"

    meta_df = pd.DataFrame(rows_meta, index=work_df.index)
    for col in meta_df.columns:
        work_df[col] = meta_df[col]

    m_sort = primary_metric.lower()
    if m_sort in ("ctr", "cvr", "roas") and m_sort in work_df.columns:
        work_df = work_df.sort_values([m_sort, "composite_rank_score"], ascending=[False, False], na_position="last")
    elif m_sort in ("cpc", "cpa") and m_sort in work_df.columns:
        work_df = work_df.sort_values([m_sort, "composite_rank_score"], ascending=[True, False], na_position="last")
    else:
        work_df = work_df.sort_values("composite_rank_score", ascending=False, na_position="last")

    work_df = work_df.reset_index(drop=True)
    work_df.insert(0, "rank", range(1, len(work_df) + 1))
    return work_df


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

    # 5. ROAS = revenue / spend (only when revenue/roas column is available)
    if "roas" in df.columns and spn_a > 0 and spn_b > 0:
        vals_roas_a = pd.to_numeric(sub_a["roas"], errors="coerce").dropna().values
        vals_roas_b = pd.to_numeric(sub_b["roas"], errors="coerce").dropna().values
        if len(vals_roas_a) >= 1 and len(vals_roas_b) >= 1:
            rev_a = float(pd.to_numeric(sub_a["revenue"], errors="coerce").dropna().sum()) if "revenue" in sub_a.columns else float(np.mean(vals_roas_a) * spn_a)
            rev_b = float(pd.to_numeric(sub_b["revenue"], errors="coerce").dropna().sum()) if "revenue" in sub_b.columns else float(np.mean(vals_roas_b) * spn_b)
            roas_a = rev_a / spn_a
            roas_b = rev_b / spn_b
            diff_roas = roas_a - roas_b
            uplift_roas = ((roas_a - roas_b) / roas_b * 100.0) if roas_b > 0 else 0.0

            cohen_d_roas = compute_cohens_d(vals_roas_a, vals_roas_b)
            inf_roas = _compute_ad_level_welch_inference(vals_roas_a, vals_roas_b, center_diff=diff_roas)
            p_val_roas = inf_roas["p_welch"]
            ci_low_roas = inf_roas["ci_lower"]
            ci_upp_roas = inf_roas["ci_upper"]
            se_roas = inf_roas["se_welch"]
            method_roas = (
                f"Ad-Level Welch's t-Test on Return on Ad Spend (df={inf_roas['df_welch']})"
                if inf_roas["inferential_valid"]
                else "Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"
            )

            dir_str_roas = (
                f"'{group_a}' associated with {uplift_roas:+.1f}% {'higher' if uplift_roas >= 0 else 'lower'} pooled ROAS than '{group_b}' "
                f"({roas_a:.2f}x vs {roas_b:.2f}x pooled; Ad-level mean: {inf_roas['mean_a']:.2f}x vs {inf_roas['mean_b']:.2f}x)"
            )

            findings.append(
                Finding(
                    attribute=f"{attribute_col}: {group_a} vs {group_b}",
                    outcome_metric="ROAS",
                    direction_of_association=dir_str_roas,
                    effect_size={
                        "relative_uplift_pct": round(uplift_roas, 2),
                        "absolute_difference": round(diff_roas, 4),
                        "ad_level_mean_difference": round(inf_roas["ad_mean_diff"], 4),
                        "roas_group_a": round(roas_a, 3),
                        "roas_group_b": round(roas_b, 3),
                        "ad_mean_group_a": round(inf_roas["mean_a"], 3),
                        "ad_mean_group_b": round(inf_roas["mean_b"], 3),
                        "cohens_d": round(cohen_d_roas, 3),
                    },
                    sample_sizes={
                        "creatives_group_a": n_a,
                        "creatives_group_b": n_b,
                        "impressions_group_a": imp_a,
                        "impressions_group_b": imp_b,
                        "spend_group_a": round(spn_a, 2),
                        "spend_group_b": round(spn_b, 2),
                        "revenue_group_a": round(rev_a, 2),
                        "revenue_group_b": round(rev_b, 2),
                    },
                    uncertainty={
                        "estimand": "ROAS Difference (Revenue/Spend, Group A - Group B, Ad-Level Welch t 95% CI)",
                        "point_estimate": round(diff_roas, 4),
                        "ci_95_lower": round(ci_low_roas, 4),
                        "ci_95_upper": round(ci_upp_roas, 4),
                        "standard_error": round(se_roas, 4),
                        "raw_p_value": float(np.clip(p_val_roas, 1e-12, 1.0)),
                        "fdr_q_value": float(np.clip(p_val_roas, 1e-12, 1.0)),
                    },
                    evidence_classification="Pending",
                    limitations=generate_limitations_statement(n_a, n_b, total_imp, attribute_col, "ROAS"),
                    attribute_type="categorical",
                    statistical_method=method_roas,
                    adjusted_p_value=float(np.clip(p_val_roas, 1e-12, 1.0)),
                    explanation=f"Group '{group_a}' generated {roas_a:.2f}x pooled ROAS (${rev_a:,.2f} revenue / ${spn_a:,.2f} spend) versus {roas_b:.2f}x pooled ROAS in '{group_b}'.",
                    traceable_ad_ids=traceable,
                    group_a=group_a,
                    group_b=group_b,
                    details={"welch_p_test": p_val_roas, "mann_whitney_p": inf_roas["p_mwu"], "df_welch": inf_roas["df_welch"]},
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
    Explicitly reports Underpowered findings when 2 <= n < 4 instead of silently dropping them.
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
    if n < 2:
        return None

    x = valid_data[attribute_col].astype(float).values
    y = valid_data[metric_col].astype(float).values
    weights = valid_data["impressions"].astype(float).values
    ad_ids = valid_data["ad_id"].astype(str).tolist()

    if np.std(x) == 0 or np.std(y) == 0:
        return None

    # Explicit Underpowered handling for very small sample sizes (2 <= n < 4)
    if n < 4:
        spearman_res = stats.spearmanr(x, y)
        rho = float(spearman_res.statistic) if not np.isnan(spearman_res.statistic) else 0.0
        direction_verb = "positively associated with" if rho >= 0 else "negatively associated with"
        return Finding(
            attribute=attribute_col,
            outcome_metric=outcome_metric,
            direction_of_association=f"Continuous '{attribute_col}' is {direction_verb} {outcome_metric} (Descriptive Spearman ρ = {rho:+.2f}; Underpowered n={n})",
            effect_size={
                "spearman_rho": round(rho, 3),
                "pearson_r": round(rho, 3),
                "ols_slope": 0.0,
                "wls_slope_exposure_weighted": 0.0,
                "r_squared": round(rho * rho, 4),
                "relative_uplift_pct": round(rho * 50.0, 2),
            },
            sample_sizes={
                "creatives_count": n,
                "total_impressions": int(valid_data["impressions"].sum()),
                "total_clicks": int(valid_data["clicks"].sum()) if "clicks" in valid_data.columns else 0,
                "total_conversions": int(valid_data["conversions"].sum()) if "conversions" in valid_data.columns else 0,
            },
            uncertainty={
                "estimand": "Descriptive Rank Correlation (Underpowered n < 4; Fisher z CI Not Estimable)",
                "point_estimate": round(rho, 3),
                "ci_95_lower": 0.0,
                "ci_95_upper": 0.0,
                "standard_error": 0.0,
                "raw_p_value": 1.0,
                "fdr_q_value": 1.0,
            },
            evidence_classification="Underpowered",
            limitations=(
                f"Underpowered sample size (only {n} creatives; minimum n >= 4 required for Fisher z CI and n >= 6 for supported inference). "
                "Observational correlation only; does not establish causation. "
                "A non-significant result does not prove that an attribute has no effect (absence of evidence is not evidence of absence)."
            ),
            attribute_type="continuous",
            statistical_method="Descriptive Rank Correlation Only (Underpowered Sample n < 4)",
            adjusted_p_value=1.0,
            explanation=f"Only {n} valid creatives available for '{attribute_col}' vs {outcome_metric}; sample is underpowered for inferential testing.",
            traceable_ad_ids={"analyzed_ads": ad_ids},
            details={"ci_slope_low": 0.0, "ci_slope_upp": 0.0, "pearson_p": 1.0, "spearman_p": 1.0},
        )

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
    Checks if attributes are disproportionately clustered in specific campaigns or audiences,
    and verifies within-stratum directional consistency where overlapping strata exist.
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
            if attr not in df.columns or attr == conf_col or finding.outcome_metric.lower() not in df.columns:
                continue

            metric = finding.outcome_metric.lower()
            sub_df = df[[attr, conf_col, metric, "spend", "impressions"]].dropna()
            if len(sub_df) < 4:
                continue

            # Stratification check: contingency / cross-tab distribution
            ctab = pd.crosstab(sub_df[attr], sub_df[conf_col])
            row_props = ctab.div(ctab.sum(axis=1), axis=0)
            max_cluster = float(row_props.max().max())

            # Within-stratum directional verification for categorical contrasts
            stratified_consistency = "Not Applicable (Continuous)"
            overlapping_strata = 0
            if finding.attribute_type == "categorical" and finding.group_a and finding.group_b:
                overall_diff = float(finding.effect_size.get("ad_level_mean_difference", finding.effect_size.get("absolute_difference", 0.0)))
                consistent_strata = 0
                for seg in unique_segments:
                    seg_df = sub_df[sub_df[conf_col] == seg]
                    vals_a = seg_df[seg_df[attr] == finding.group_a][metric].dropna()
                    vals_b = seg_df[seg_df[attr] == finding.group_b][metric].dropna()
                    if len(vals_a) >= 1 and len(vals_b) >= 1:
                        overlapping_strata += 1
                        stratum_diff = float(vals_a.mean() - vals_b.mean())
                        if overall_diff == 0 or (stratum_diff * overall_diff >= 0):
                            consistent_strata += 1
                if overlapping_strata == 0:
                    stratified_consistency = "Unverifiable (100% Collinear / Zero Overlapping Strata)"
                elif consistent_strata == overlapping_strata:
                    stratified_consistency = f"Consistent Within All {overlapping_strata} Overlapping Strata"
                else:
                    stratified_consistency = f"Mixed / Reversal ({consistent_strata}/{overlapping_strata} Overlapping Strata Agree)"

            confounded_risk = "Low"
            risk_desc = f"Attribute '{attr}' is reasonably balanced across {conf_col} segments ({stratified_consistency})."
            if max_cluster >= 0.75 or overlapping_strata == 0 and finding.attribute_type == "categorical":
                confounded_risk = "High"
                risk_desc = (
                    f"Warning: Up to {max_cluster*100:.0f}% of creatives with specific '{attr}' "
                    f"are concentrated in a single '{conf_col}' segment ({stratified_consistency}). "
                    f"The observed {finding.outcome_metric} difference may be driven by '{conf_col}' targeting/allocation rather than the creative attribute alone."
                )
            elif max_cluster >= 0.50:
                confounded_risk = "Moderate"
                risk_desc = f"Moderate clustering ({max_cluster*100:.0f}%) of '{attr}' within specific '{conf_col}' segments ({stratified_consistency})."

            confounding_reports.append({
                "attribute": attr,
                "confounder_field": conf_col,
                "outcome_metric": finding.outcome_metric,
                "confounding_risk": confounded_risk,
                "stratified_consistency": stratified_consistency,
                "assessment": risk_desc,
                "max_segment_concentration_pct": round(max_cluster * 100.0, 1),
                "segments_analyzed": unique_segments[:5],
            })

    return confounding_reports


def _generate_csv_creative_variant_findings(df: pd.DataFrame) -> List[Finding]:
    """
    When a dataset has no extracted visual features (e.g., CSV uploaded prior to image matching)
    and no multi-group metadata segments, performs statistical comparisons across creative variants:
    1. Top vs. Bottom Median-Split Cohort comparison (High-CTR / High-Spend vs Low-CTR / Low-Spend cohorts).
    2. Pairwise Two-Proportion Z-Tests comparing top and bottom creative variants on CTR and CVR.
    Ensures valid multi-row CSV uploads never return 0 statistical comparisons while strictly
    labeling sample size and observational limitations.
    """
    variant_findings: List[Finding] = []
    if df is None or len(df) < 2:
        return variant_findings

    work = df.copy()

    # 1. If N >= 4 creatives, compare Above-Median Spend vs Below-Median Spend creative cohorts
    if "spend" in work.columns and len(work) >= 4 and work["spend"].nunique() >= 2:
        med_spend = float(work["spend"].median())
        work["spend_allocation_tier"] = np.where(
            work["spend"] >= med_spend,
            f"Higher Spend (>=${med_spend:.0f})",
            f"Lower Spend (<${med_spend:.0f})",
        )
        tiers = work["spend_allocation_tier"].unique().tolist()
        if len(tiers) == 2:
            variant_findings.extend(
                analyze_categorical_attribute(
                    work,
                    "spend_allocation_tier",
                    f"Higher Spend (>=${med_spend:.0f})",
                    f"Lower Spend (<${med_spend:.0f})",
                )
            )

    # 2. Pairwise Two-Proportion Z-Test between Top-Performing and Lowest-Performing Creative Variants on CTR and CVR
    valid_ctr = work.dropna(subset=["ctr"]).sort_values("ctr", ascending=False)
    if len(valid_ctr) >= 2:
        top_row = valid_ctr.iloc[0]
        bot_row = valid_ctr.iloc[-1]
        ad_top = str(top_row["ad_id"])
        ad_bot = str(bot_row["ad_id"])
        if ad_top != ad_bot:
            pw_results = compare_creative_variants(top_row, bot_row)
            for pw in pw_results:
                if pw["metric"] in ("CTR", "CVR") and pw["p_value"] is not None:
                    m_name = pw["metric"]
                    imp_top = int(float(top_row.get("impressions", 0) or 0))
                    imp_bot = int(float(bot_row.get("impressions", 0) or 0))
                    clk_top = int(float(top_row.get("clicks", 0) or 0))
                    clk_bot = int(float(bot_row.get("clicks", 0) or 0))
                    cnv_top = int(float(top_row.get("conversions", 0) or 0))
                    cnv_bot = int(float(bot_row.get("conversions", 0) or 0))
                    uplift = float(pw["relative_uplift_pct"] or 0.0)
                    p_raw = float(pw["p_value"])

                    variant_findings.append(
                        Finding(
                            attribute=f"creative_variant: {ad_top} vs {ad_bot}",
                            outcome_metric=m_name,
                            direction_of_association=(
                                f"Creative '{ad_top}' achieved {uplift:+.1f}% {'higher' if uplift >= 0 else 'lower'} {m_name} "
                                f"({pw['value_a']*100:.2f}%) than '{ad_bot}' ({pw['value_b']*100:.2f}%)"
                            ),
                            effect_size={
                                "relative_uplift_pct": round(uplift, 2),
                                "absolute_difference": pw["absolute_difference"],
                                "rate_group_a": pw["value_a"],
                                "rate_group_b": pw["value_b"],
                            },
                            sample_sizes={
                                "creatives_group_a": 1,
                                "creatives_group_b": 1,
                                "impressions_group_a": imp_top,
                                "impressions_group_b": imp_bot,
                                "clicks_group_a": clk_top,
                                "clicks_group_b": clk_bot,
                                "conversions_group_a": cnv_top,
                                "conversions_group_b": cnv_bot,
                            },
                            uncertainty={
                                "estimand": f"{m_name} Proportion Difference ({ad_top} - {ad_bot}, 95% Wald CI)",
                                "point_estimate": pw["absolute_difference"],
                                "ci_95_lower": pw["ci_95_lower"],
                                "ci_95_upper": pw["ci_95_upper"],
                                "standard_error": round((pw["ci_95_upper"] - pw["ci_95_lower"]) / 3.92, 6),
                                "raw_p_value": p_raw,
                                "fdr_q_value": p_raw,
                            },
                            evidence_classification="Underpowered",
                            limitations=generate_limitations_statement(1, 1, imp_top + imp_bot, "creative_variant", m_name),
                            attribute_type="categorical",
                            statistical_method=pw["statistical_method"],
                            adjusted_p_value=p_raw,
                            explanation=(
                                f"Direct variant comparison between '{ad_top}' and '{ad_bot}' using CSV exposure counts. "
                                "Upload matching creative images to unlock visual attribute cohort inference."
                            ),
                            traceable_ad_ids={"group_a_ads": [ad_top], "group_b_ads": [ad_bot]},
                            group_a=ad_top,
                            group_b=ad_bot,
                        )
                    )

    return variant_findings


def run_full_statistical_analysis(
    df_with_features: pd.DataFrame,
) -> List[Finding]:
    """
    Orchestrates complete automated statistical analysis across all extracted
    categorical, composition, and continuous visual attributes, plus CSV segment/variant
    contrasts when visual features are absent or supplementary.
    Strictly excludes corrupted records (extraction_status == 'error') and excludes
    unmatched records from visual attribute comparisons.
    """
    if df_with_features is None or df_with_features.empty:
        return []

    has_status_col = "extraction_status" in df_with_features.columns
    if has_status_col:
        visual_df = df_with_features[df_with_features["extraction_status"] == "success"].copy()
        csv_valid_df = df_with_features[df_with_features["extraction_status"] != "error"].copy()
    else:
        visual_df = df_with_features.copy()
        csv_valid_df = df_with_features.copy()

    findings: List[Finding] = []
    invalid_labels = {"Unknown", "Unavailable", "None", "nan", ""}

    if not visual_df.empty:
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

        tested_pairs = set()
        tested_cols = set()
        for col, grp_a, grp_b in categorical_tests:
            if col in visual_df.columns:
                unique_vals = [
                    v for v in visual_df[col].dropna().unique().tolist()
                    if str(v).strip() not in invalid_labels
                ]
                if grp_a in unique_vals and grp_b in unique_vals:
                    cat_findings = analyze_categorical_attribute(visual_df, col, grp_a, grp_b)
                    findings.extend(cat_findings)
                    tested_cols.add(col)
                    tested_pairs.add((col, grp_a, grp_b))
                    tested_pairs.add((col, grp_b, grp_a))

        # Fallback for custom uploaded datasets where different category buckets are populated
        all_cat_cols = [
            "dominant_color_tone", "human_presence_cat", "brightness_cat", "contrast_cat",
            "aspect_ratio_cat", "visual_complexity", "text_density_cat", "colorfulness_cat",
            "composition_style", "object_presence_cat", "scene_category",
        ]
        for col in all_cat_cols:
            if col not in tested_cols and col in visual_df.columns:
                valid_series = visual_df[col].dropna()
                valid_series = valid_series[~valid_series.astype(str).str.strip().isin(invalid_labels)]
                val_counts = valid_series.value_counts()
                top_cats = [str(c) for c in val_counts.index[:3]]
                for i in range(len(top_cats)):
                    for j in range(i + 1, len(top_cats)):
                        grp_a, grp_b = top_cats[i], top_cats[j]
                        if (col, grp_a, grp_b) not in tested_pairs:
                            cat_findings = analyze_categorical_attribute(visual_df, col, grp_a, grp_b)
                            findings.extend(cat_findings)
                            tested_pairs.add((col, grp_a, grp_b))
                            tested_pairs.add((col, grp_b, grp_a))

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
        if "roas" in visual_df.columns and pd.to_numeric(visual_df["roas"], errors="coerce").notna().sum() >= 2:
            outcome_metrics.append("ROAS")

        for col in continuous_cols:
            if col in visual_df.columns:
                for metric in outcome_metrics:
                    cont_finding = analyze_continuous_attribute(visual_df, col, metric)
                    if cont_finding is not None:
                        findings.append(cont_finding)

    # Fallback when 0 visual findings were generated (e.g., CSV uploaded with 0 matched images):
    # Evaluate CSV segment/variant attributes and pairwise creative variant contrasts
    if not findings and not csv_valid_df.empty:
        csv_segment_cols = ["variant", "placement", "audience", "campaign_name", "platform"]
        for seg_col in csv_segment_cols:
            if seg_col in csv_valid_df.columns:
                valid_s = csv_valid_df[seg_col].dropna()
                valid_s = valid_s[~valid_s.astype(str).str.strip().isin(invalid_labels)]
                vc = valid_s.value_counts()
                top_segs = [str(c) for c in vc.index[:3]]
                for i in range(len(top_segs)):
                    for j in range(i + 1, len(top_segs)):
                        seg_findings = analyze_categorical_attribute(csv_valid_df, seg_col, top_segs[i], top_segs[j])
                        findings.extend(seg_findings)

        if not findings:
            findings.extend(_generate_csv_creative_variant_findings(csv_valid_df))

    # Apply Multiple Testing Correction (FDR Benjamini-Hochberg & Bonferroni)
    findings = apply_multiple_testing_correction(findings)

    # Rank Findings using transparent criteria
    findings = rank_findings(findings)

    return findings


def build_creative_scorecard(
    df: pd.DataFrame,
    primary_metric: str = "composite",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Constructs a comprehensive Creative Scorecard for all creatives in `df`:
    - Summarizes CTR, CPC, CVR, CPA, ROAS (when available), Spend, Sample Size (impressions, clicks, conversions),
      and relative performance vs. comparison group (`lift_vs_campaign_pct`).
    - Explicitly documents the Empirical Bayes composite scoring formula, weights, and limitations.
    - Detects and warns when ranking creatives across heterogeneous / incompatible comparison groups
      (e.g., multiple platforms, placements, or campaigns with different auction dynamics).
    """
    if df is None or df.empty:
        return {
            "scorecard_df": pd.DataFrame(),
            "comparison_group_warnings": [],
            "formula_documentation": "",
            "weights_summary": {},
            "limitations": "No creatives available to score.",
        }

    ranked_df = rank_creatives(df, primary_metric=primary_metric, alpha=alpha)
    kpis = compute_aggregate_kpis(df)
    has_roas = kpis.get("aggregate_roas") is not None

    # Check for incompatible comparison groups (multiple platforms, placements, or campaigns)
    group_warnings: List[str] = []
    for seg_col, seg_label in [
        ("platform", "Platform"),
        ("placement", "Placement"),
        ("campaign_name", "Campaign"),
        ("audience", "Audience"),
    ]:
        if seg_col in df.columns:
            valid_vals = [
                str(x).strip()
                for x in df[seg_col].dropna().unique()
                if str(x).strip() not in ("", "Unknown", "nan", "None")
            ]
            if len(valid_vals) > 1:
                group_warnings.append(
                    f"Heterogeneous {seg_label}s Detected ({len(valid_vals)}: {', '.join(valid_vals[:4])}): "
                    f"Ranking creatives across different {seg_label.lower()}s mixes distinct auction environments and baseline rates. "
                    f"Filter by {seg_label} before making direct winner/loser budget decisions."
                )

    if has_roas:
        weights_summary = {
            "EB_Shrunk_CTR_Ratio": 0.35,
            "EB_Shrunk_CVR_Ratio": 0.30,
            "CPA_Efficiency_Ratio": 0.20,
            "ROAS_Ratio": 0.15,
            "Exposure_Reliability_Multiplier": "1.00 (High: >=5k imp & >=50 clicks), 0.80 (Moderate: >=1k imp & >=20 clicks), 0.45 (Low Volume)",
        }
        formula_doc = (
            "Score = clip((0.35 * [EB_CTR / Pooled_CTR] + 0.30 * [EB_CVR / Pooled_CVR] "
            "+ 0.20 * [Pooled_CPA / Ad_CPA] + 0.15 * [Ad_ROAS / Pooled_ROAS]) * 50 * Reliability_Multiplier, 0, 100), "
            "where EB_CTR = (Clicks + 2000 * Pooled_CTR) / (Impressions + 2000) and "
            "EB_CVR = (Conversions + 50 * Pooled_CVR) / (Clicks + 50)."
        )
    else:
        weights_summary = {
            "EB_Shrunk_CTR_Ratio": 0.45,
            "EB_Shrunk_CVR_Ratio": 0.35,
            "CPA_Efficiency_Ratio": 0.20,
            "Exposure_Reliability_Multiplier": "1.00 (High: >=5k imp & >=50 clicks), 0.80 (Moderate: >=1k imp & >=20 clicks), 0.45 (Low Volume)",
        }
        formula_doc = (
            "Score = clip((0.45 * [EB_CTR / Pooled_CTR] + 0.35 * [EB_CVR / Pooled_CVR] "
            "+ 0.20 * [Pooled_CPA / Ad_CPA]) * 50 * Reliability_Multiplier, 0, 100), "
            "where EB_CTR = (Clicks + 2000 * Pooled_CTR) / (Impressions + 2000) and "
            "EB_CVR = (Conversions + 50 * Pooled_CVR) / (Clicks + 50)."
        )

    limitations = (
        "Composite scores are observational summaries regularized via Empirical Bayes shrinkage toward the active "
        "comparison group's pooled baseline. They do not adjust for non-random budget allocation, audience fatigue, "
        "or cross-platform auction differences."
    )

    return {
        "scorecard_df": ranked_df,
        "comparison_group_warnings": group_warnings,
        "formula_documentation": formula_doc,
        "weights": weights_summary,
        "weights_summary": weights_summary,
        "limitations": limitations,
    }


def compare_multiple_creatives(
    df: pd.DataFrame,
    ad_ids: List[str],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Compares two or more selected creatives side-by-side:
    - Summarizes key metrics (Spend, Impressions, Clicks, Conversions, CTR, CVR, CPC, CPA, ROAS)
      and visual features for each selected creative.
    - Computes absolute and relative differences vs. the first selected creative (Reference Baseline).
    - Flags sample-size warnings (low exposure or >3x exposure imbalance) and incompatible comparison groups.
    - Runs pairwise statistical hypothesis tests (`compare_creative_variants`) between the reference creative
      and each comparison creative.
    """
    if df is None or df.empty or not ad_ids or len(ad_ids) < 2:
        return {
            "reference_ad_id": ad_ids[0] if ad_ids else None,
            "creatives_summary": [],
            "pairwise_tests": [],
            "sample_size_warnings": ["Select at least 2 creatives to run a side-by-side comparison."],
            "comparison_group_warnings": [],
        }

    clean_ids = [str(x).strip() for x in ad_ids if str(x).strip()]
    sub_df = df[df["ad_id"].astype(str).isin(clean_ids)].copy()
    if len(sub_df) < 2:
        return {
            "reference_ad_id": clean_ids[0] if clean_ids else None,
            "creatives_summary": [],
            "pairwise_tests": [],
            "sample_size_warnings": ["Fewer than 2 selected creative IDs were found in the active dataset."],
            "comparison_group_warnings": [],
        }

    # Preserve user selection order
    id_to_row = {str(r["ad_id"]): r for _, r in sub_df.iterrows()}
    ordered_rows = [id_to_row[cid] for cid in clean_ids if cid in id_to_row]
    ref_row = ordered_rows[0]
    ref_id = str(ref_row["ad_id"])

    ref_ctr = float(ref_row["ctr"]) if pd.notna(ref_row.get("ctr")) else None
    ref_cvr = float(ref_row["cvr"]) if pd.notna(ref_row.get("cvr")) else None
    ref_cpc = float(ref_row["cpc"]) if pd.notna(ref_row.get("cpc")) else None
    ref_cpa = float(ref_row["cpa"]) if pd.notna(ref_row.get("cpa")) else None
    ref_roas = float(ref_row["roas"]) if pd.notna(ref_row.get("roas")) else None

    creatives_summary: List[Dict[str, Any]] = []
    sample_warnings: List[str] = []
    impressions_list: List[int] = []

    for idx, row in enumerate(ordered_rows):
        cid = str(row["ad_id"])
        imp = int(float(row.get("impressions", 0) or 0))
        clk = int(float(row.get("clicks", 0) or 0))
        cnv = int(float(row.get("conversions", 0) or 0))
        spn = float(row.get("spend", 0.0) or 0.0)
        impressions_list.append(imp)

        if imp < 1000 or clk < 20:
            sample_warnings.append(
                f"Creative '{cid}' has low exposure volume ({imp:,} impressions, {clk:,} clicks); "
                "rate estimates have wide confidence intervals."
            )

        ctr_v = float(row["ctr"]) if pd.notna(row.get("ctr")) else None
        cvr_v = float(row["cvr"]) if pd.notna(row.get("cvr")) else None
        cpc_v = float(row["cpc"]) if pd.notna(row.get("cpc")) else None
        cpa_v = float(row["cpa"]) if pd.notna(row.get("cpa")) else None
        roas_v = float(row["roas"]) if pd.notna(row.get("roas")) else None

        ctr_ci_l, ctr_ci_u = compute_wilson_ci(clk, imp, alpha=alpha)
        cvr_ci_l, cvr_ci_u = compute_wilson_ci(cnv, clk, alpha=alpha)

        def _rel_diff(val: Optional[float], base: Optional[float]) -> Optional[float]:
            if idx == 0:
                return 0.0
            if val is None or base is None or base == 0:
                return None
            return round((val - base) / base * 100.0, 2)

        def _abs_diff(val: Optional[float], base: Optional[float]) -> Optional[float]:
            if idx == 0:
                return 0.0
            if val is None or base is None:
                return None
            return round(val - base, 6)

        creatives_summary.append({
            "ad_id": cid,
            "role": "Baseline (Reference)" if idx == 0 else f"Variant {idx}",
            "campaign_name": str(row.get("campaign_name", "N/A")),
            "platform": str(row.get("platform", "N/A")),
            "placement": str(row.get("placement", "N/A")),
            "audience": str(row.get("audience", "N/A")),
            "spend": spn,
            "impressions": imp,
            "clicks": clk,
            "conversions": cnv,
            "ctr": ctr_v,
            "ctr_ci_95": f"[{ctr_ci_l*100:.2f}%, {ctr_ci_u*100:.2f}%]" if imp > 0 else "Unavailable",
            "ctr_abs_diff_vs_ref": _abs_diff(ctr_v, ref_ctr),
            "ctr_rel_diff_vs_ref_pct": _rel_diff(ctr_v, ref_ctr),
            "cvr": cvr_v,
            "cvr_ci_95": f"[{cvr_ci_l*100:.2f}%, {cvr_ci_u*100:.2f}%]" if clk > 0 else "Unavailable",
            "cvr_abs_diff_vs_ref": _abs_diff(cvr_v, ref_cvr),
            "cvr_rel_diff_vs_ref_pct": _rel_diff(cvr_v, ref_cvr),
            "cpc": cpc_v,
            "cpc_rel_diff_vs_ref_pct": _rel_diff(cpc_v, ref_cpc),
            "cpa": cpa_v,
            "cpa_rel_diff_vs_ref_pct": _rel_diff(cpa_v, ref_cpa),
            "roas": roas_v,
            "roas_rel_diff_vs_ref_pct": _rel_diff(roas_v, ref_roas),
            "dominant_color_tone": str(row.get("dominant_color_tone", "N/A")),
            "human_presence_cat": str(row.get("human_presence_cat", "N/A")),
            "aspect_ratio_cat": str(row.get("aspect_ratio_cat", "N/A")),
            "composition_style": str(row.get("composition_style", "N/A")),
            "visual_complexity": str(row.get("visual_complexity", "N/A")),
            "text_density_cat": str(row.get("text_density_cat", "N/A")),
        })

    if impressions_list and min(impressions_list) > 0:
        imbalance_ratio = max(impressions_list) / float(min(impressions_list))
        if imbalance_ratio >= 3.0:
            sample_warnings.append(
                f"Exposure Imbalance Warning: Max/min impression ratio across selected creatives is {imbalance_ratio:.1f}x "
                f"({max(impressions_list):,} vs {min(impressions_list):,} impressions). Delivery pacing and auction saturation may bias direct comparisons."
            )

    comp_group_warnings: List[str] = []
    for meta_col, label in [("platform", "Platform"), ("campaign_name", "Campaign"), ("placement", "Placement")]:
        if meta_col in sub_df.columns:
            vals = [str(v) for v in sub_df[meta_col].dropna().unique() if str(v) not in ("", "Unknown", "nan")]
            if len(vals) > 1:
                comp_group_warnings.append(
                    f"Selected creatives span multiple {label}s ({', '.join(vals)}). Differences may reflect {label.lower()} baselines rather than creative design."
                )

    pairwise_tests: List[Dict[str, Any]] = []
    for comp_row in ordered_rows[1:]:
        comp_id = str(comp_row["ad_id"])
        pw = compare_creative_variants(comp_row, ref_row, alpha=alpha)
        for item in pw:
            item["reference_ad_id"] = ref_id
            item["challenger_ad_id"] = comp_id
        pairwise_tests.extend(pw)

    return {
        "reference_ad_id": ref_id,
        "creatives_summary": creatives_summary,
        "comparison_table": pd.DataFrame(creatives_summary),
        "pairwise_tests": pairwise_tests,
        "sample_size_warnings": sample_warnings,
        "comparison_group_warnings": comp_group_warnings,
    }



