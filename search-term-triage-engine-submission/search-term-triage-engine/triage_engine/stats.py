"""
Statistical Inference and Uncertainty Calculations for Search Term Triage.

Provides:
- Wilson Score Confidence Intervals for binomial conversion proportions.
- Empirical Bayes (Beta-Binomial) posterior shrinkage estimators.
- Explainable uncertainty and evidence strength metrics.
"""

import math
from typing import Tuple, Dict, Any, Optional

def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Computes the asymmetric Wilson score confidence interval for a binomial proportion.
    Accurately handles small sample sizes and extreme values (0 or 100%),
    avoiding the normal approximation failure mode of Wald intervals.

    Returns:
        (lower_bound, upper_bound) bounded in [0.0, 1.0].
    """
    if trials <= 0:
        return 0.0, 0.0
    
    # Standard normal quantile mapping
    z_map = {0.90: 1.644853, 0.95: 1.959964, 0.99: 2.575829}
    z = z_map.get(confidence, 1.959964)
    
    # Clamp successes to valid trial range
    s = max(0, min(int(successes), int(trials)))
    n = float(trials)
    p = s / n
    
    denominator = 1.0 + (z**2) / n
    centre = (p + (z**2) / (2.0 * n)) / denominator
    spread = (z * math.sqrt((p * (1.0 - p) / n) + (z**2 / (4.0 * (n**2))))) / denominator
    
    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return lower, upper


def empirical_bayes_cvr(successes: int, trials: int, prior_alpha: float = 1.2, prior_beta: float = 28.0) -> float:
    """
    Computes Bayesian posterior mean for conversion rate using Beta-Binomial conjugate updating:
    Posterior = Beta(alpha + successes, beta + trials - successes)
    Expected CVR = (alpha + successes) / (alpha + beta + trials)
    
    This shrinks low-volume fluke queries (e.g., 1 conv / 2 clicks) toward account prior (~4%).
    """
    if trials < 0 or successes < 0:
        return 0.0
    s = max(0, int(successes))
    n = max(0, int(trials))
    return (s + prior_alpha) / (n + prior_alpha + prior_beta)


def calculate_derived_metrics(impressions: int, clicks: int, cost: float, 
                              conversions: float, conversion_value: float) -> Dict[str, Optional[float]]:
    """
    Computes standard paid search performance metrics safely without zero-division errors.
    """
    impr = max(0, int(impressions))
    clk = max(0, int(clicks))
    cst = max(0.0, float(cost))
    cnv = max(0.0, float(conversions))
    val = max(0.0, float(conversion_value))
    
    ctr = (clk / impr) if impr > 0 else 0.0
    cpc = (cst / clk) if clk > 0 else 0.0
    cvr = (cnv / clk) if clk > 0 else 0.0
    cpa = (cst / cnv) if cnv > 0 else None
    roas = (val / cst) if cst > 0 else None
    
    return {
        "ctr": round(ctr, 4),
        "cpc": round(cpc, 2),
        "raw_cvr": round(cvr, 4),
        "cpa": round(cpa, 2) if cpa is not None else None,
        "roas": round(roas, 2) if roas is not None else None
    }


def calculate_uncertainty_metrics(clicks: int, conversions: int, cost: float, 
                                  prior_alpha: float = 1.2, prior_beta: float = 28.0,
                                  target_cpa: float = 220.0,
                                  confidence: float = 0.95) -> Dict[str, Any]:
    """
    Calculates statistical uncertainty indicators.
    
    NOTE ON UNCERTAINTY SCORE:
    The uncertainty_score is an explainable heuristic index [0.0 = high certainty, 1.0 = zero evidence]
    derived from the Wilson 95% interval width and sample size. It must not be confused with
    a formal Bayesian credible interval width.
    """
    clk = max(0, int(clicks))
    cnv = max(0, int(conversions))
    cst = max(0.0, float(cost))
    
    ci_lower, ci_upper = wilson_score_interval(cnv, clk, confidence=confidence)
    ci_width = ci_upper - ci_lower
    shrunk_cvr = empirical_bayes_cvr(cnv, clk, prior_alpha, prior_beta)
    
    # Explainable heuristic uncertainty score:
    # 0 clicks -> 1.0 (no sample)
    # < 5 clicks -> dominated by interval width with floor 0.65
    # >= 15 clicks -> interval width directly
    if clk == 0:
        heuristic_uncertainty = 1.0
    elif clk < 5:
        heuristic_uncertainty = round(max(0.65, min(1.0, ci_width)), 2)
    elif clk < 15:
        heuristic_uncertainty = round(max(0.35, min(1.0, ci_width * 1.2)), 2)
    else:
        heuristic_uncertainty = round(min(1.0, ci_width), 2)
        
    return {
        "shrunk_cvr": round(shrunk_cvr, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "ci_width": round(ci_width, 4),
        "uncertainty_score": heuristic_uncertainty,
        "is_underpowered": clk < 10
    }
