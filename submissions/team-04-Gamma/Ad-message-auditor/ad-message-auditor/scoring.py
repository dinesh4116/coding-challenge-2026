"""Position-aware scoring. All numbers are INITIAL HEURISTICS, not validated values.

Match score (0-100)
    Each of five dimensions starts at 100. Verified discrepancies subtract a penalty:
        penalty = severity_penalty[severity] * status_multiplier[status]
    The overall score is the weighted average of the dimension scores (equivalent to
    "start at 100 and subtract weighted penalties").

    * contradicted / partial findings count ONLY if their evidence quote was verified.
    * missing findings count (absence in a complete snapshot is the evidence).
    * supported and uncertain findings never reduce the score; uncertainty reduces
      *confidence* instead.
    * Prominence dimension: a verified supporting claim that only appears in the footer,
      FAQ or an unclassified section gets a prominence penalty. This is a position concern,
      not a claim that the ad is false.

Audit confidence (0-1) is computed separately and never feeds the match score.
If nothing could be evaluated, the score is ``None`` (shown as "not evaluated").
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from schemas import Finding, ParsedPage

DIMENSIONS = ["main_offer", "features_benefits", "pricing_timing_eligibility", "cta", "prominence"]
TYPE_TO_DIMENSION = {
    "offer": "main_offer", "guarantee": "main_offer", "trial": "main_offer",
    "regulated_claim": "main_offer", "other": "main_offer",
    "feature": "features_benefits",
    "pricing": "pricing_timing_eligibility", "fees": "pricing_timing_eligibility",
    "timing": "pricing_timing_eligibility", "eligibility": "pricing_timing_eligibility",
    "cta": "cta",
}


@dataclass
class ScoringConfig:
    weights: Dict[str, float] = field(default_factory=lambda: {
        "main_offer": 30, "features_benefits": 25, "pricing_timing_eligibility": 20,
        "cta": 15, "prominence": 10})
    severity_penalty: Dict[str, float] = field(default_factory=lambda: {
        "none": 0, "low": 10, "medium": 25, "high": 50})
    status_multiplier: Dict[str, float] = field(default_factory=lambda: {
        "contradicted": 1.0, "missing": 0.8, "partial": 0.5, "supported": 0.0, "uncertain": 0.0})
    prominence_penalty: Dict[str, float] = field(default_factory=lambda: {
        "footer": 60, "faq": 30, "unknown": 20})
    # confidence deductions
    incomplete_snapshot: float = 0.4
    llm_unavailable: float = 0.25
    llm_disabled: float = 0.15
    uncertain_share: float = 0.3
    unverified_quote_each: float = 0.1
    unverified_quote_cap: float = 0.3
    unclassified_majority: float = 0.1
    no_findings: float = 0.3


def finding_penalty(f: Finding, cfg: ScoringConfig) -> float:
    if f.status in ("supported", "uncertain"):
        return 0.0
    if f.status in ("partial", "contradicted") and not f.evidence_verified:
        return 0.0
    return cfg.severity_penalty.get(f.severity, 0) * cfg.status_multiplier.get(f.status, 0)


def is_evaluable(f: Finding) -> bool:
    if f.status == "missing":
        return True
    return f.status in ("supported", "partial", "contradicted") and f.evidence_verified


def compute_score(findings: List[Finding], cfg: Optional[ScoringConfig] = None
                  ) -> Tuple[Optional[float], Dict[str, float]]:
    cfg = cfg or ScoringConfig()
    if not any(is_evaluable(f) for f in findings):
        return None, {}
    penalties = {d: 0.0 for d in DIMENSIONS}
    for f in findings:
        penalties[TYPE_TO_DIMENSION.get(f.mismatch_type, "main_offer")] += finding_penalty(f, cfg)
        if f.evidence_verified and f.position_concern and f.status in ("supported", "partial"):
            penalties["prominence"] += cfg.prominence_penalty.get(f.source_section or "unknown", 0)
    dims = {d: round(max(0.0, 100.0 - penalties[d]), 1) for d in DIMENSIONS}
    total_w = sum(cfg.weights.get(d, 0) for d in DIMENSIONS) or 1
    score = sum(cfg.weights.get(d, 0) * dims[d] for d in DIMENSIONS) / total_w
    return round(max(0.0, min(100.0, score)), 1), dims


def compute_confidence(findings: List[Finding], page: ParsedPage, llm_status: str,
                       cfg: Optional[ScoringConfig] = None, complete: Optional[bool] = None) -> float:
    cfg = cfg or ScoringConfig()
    if not page.blocks:
        return 0.0
    complete = page.snapshot_complete if complete is None else complete
    c = 1.0
    if not complete:
        c -= cfg.incomplete_snapshot
    if llm_status in ("unavailable", "invalid_output"):
        c -= cfg.llm_unavailable
    elif llm_status == "disabled":
        c -= cfg.llm_disabled
    if findings:
        c -= cfg.uncertain_share * sum(f.status == "uncertain" for f in findings) / len(findings)
        c -= min(cfg.unverified_quote_cap,
                 cfg.unverified_quote_each * sum(bool(f.unverified_quote) for f in findings))
    else:
        c -= cfg.no_findings
    content = [b for b in page.blocks if "navigation" not in b.labels]
    if content and sum(b.section == "unknown" for b in content) / len(content) > 0.5:
        c -= cfg.unclassified_majority
    return round(max(0.0, min(1.0, c)), 2)
