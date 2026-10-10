"""Rule-based, explainable search-term triage engine for the DevSprint PS-01 dataset.

This is a decision-support prototype: BLOCK means recommend exclusion for review,
not automatically change a live advertising account. Thresholds are transparent
and should be calibrated against event requirements and business goals.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "row_id", "search_term", "match_type", "campaign", "ad_group",
    "impressions", "clicks", "cost", "conversions", "conversion_value"
]

# Unsupported offerings and clearly unrelated intents defined in the supplied README.
UNSUPPORTED_PATTERNS = {
    "personal loans": r"\bpersonal\s+(?:loan|loans|lending|credit)\b",
    "mortgages / home loans": r"\b(?:mortgage|mortgages|home\s+loan|home\s+loans|refinanc(?:e|ing)\s+home)\b",
    "student loans": r"\bstudent\s+(?:loan|loans|lending)\b",
    "grants": r"\b(?:business\s+)?grants?\b",
    "employment": r"\b(?:jobs?|careers?|hiring|salary|resume|vacanc(?:y|ies))\b",
    "payday loans": r"\bpayday\s+loans?\b",
    "consumer auto loans": r"\b(?:car|auto)\s+loans?\b",
}
UNRELATED_PATTERNS = {
    "freebie / entertainment": r"\b(?:wallpaper|screensaver|meme|lyrics|game|clipart)\b",
    "templates / downloadable forms": r"\b(?:invoice|loan)\s+templates?\b|\btemplate\s+for\s+(?:invoice|loan)\b",
}
SUPPORTED_PATTERNS = {
    "business loans": r"\b(?:business|small\s+business|commercial)\s+(?:loans?|lending|financing|funding|credit)\b",
    "working capital": r"\bworking\s+capital\b",
    "equipment finance": r"\b(?:equipment|construction\s+equipment|truck|trucking|commercial\s+vehicle)\s+(?:loans?|finance|financing)\b|\bequipment\s+finance\b",
    "business line of credit": r"\b(?:business\s+)?lines?\s+of\s+credit\b|\bline\s+of\s+credit\b",
    "merchant cash advance": r"\bmerchant\s+cash\s+advances?\b",
    "SBA loans": r"\bsba\s+loans?\b|\bsba\s+financing\b",
    "invoice financing": r"\binvoice\s+(?:financing|factoring|funding)\b",
    "business credit": r"\bbusiness\s+credit\s+(?:line|financing|options?|cards?)\b|\bcredit\s+for\s+(?:small\s+)?business\b",
    "startup financing": r"\b(?:startup|start\s+up)\s+(?:business\s+)?(?:loans?|funding|financing|capital)\b",
}
COMMERCIAL_MODIFIERS = r"\b(?:rates?|rate|requirements?|calculator|approval|apply|application|lender|lenders|providers?|options?|compare|comparison|bad\s+credit|low\s+credit|fast|instant|online|near\s+me|for\s+(?:restaurants?|contractors?|trucking|women|farmers?|small\s+business))\b"


def _contains(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _intent(term: str):
    t = str(term).lower().strip()
    for label, pat in UNSUPPORTED_PATTERNS.items():
        if _contains(pat, t):
            return "unsupported", label, "The query indicates a product or intent the advertiser does not offer."
    for label, pat in UNRELATED_PATTERNS.items():
        if _contains(pat, t):
            return "irrelevant", label, "The query appears to seek a non-financing item rather than a supported business funding product."
    for label, pat in SUPPORTED_PATTERNS.items():
        if _contains(pat, t):
            return "relevant", label, "The query matches a financing product or service offered by the advertiser."
    # Terms like "loan for business" / "funding for small business" may be relevant.
    if _contains(r"\b(?:loan|loans|funding|financing|lender|lending|capital)\b", t) and _contains(r"\b(?:business|company|commercial|contractor|restaurant|trucking|equipment|merchant|sba)\b", t):
        return "relevant", "business financing (possible)", "The query appears related to business financing, but its exact product intent should be reviewed."
    if _contains(r"\b(?:loan|loans|credit|financing|funding|lender|lending|capital)\b", t):
        return "ambiguous", "general financing", "The query mentions financing but does not clearly establish a supported business-loan intent."
    return "irrelevant_or_unclear", "unclear / unrelated", "No clear match to the advertiser's supported business financing products was detected."


def triage_dataframe(df: pd.DataFrame, min_clicks_promote: int = 20, min_conversions_promote: int = 3,
                     min_clicks_evaluate: int = 30, min_spend_block: float = 250.0,
                     min_roas_promote: float = 1.5) -> pd.DataFrame:
    """Return the original rows plus transparent recommendations and computed metrics."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    out = df.copy()
    out["search_term"] = out["search_term"].fillna("").astype(str)
    for c in ["impressions", "clicks", "cost", "conversions", "conversion_value"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).clip(lower=0)
    out["ctr"] = np.where(out["impressions"] > 0, out["clicks"] / out["impressions"], np.nan)
    out["conversion_rate"] = np.where(out["clicks"] > 0, out["conversions"] / out["clicks"], np.nan)
    out["cpa"] = np.where(out["conversions"] > 0, out["cost"] / out["conversions"], np.nan)
    out["roas"] = np.where(out["cost"] > 0, out["conversion_value"] / out["cost"], np.nan)

    intents = out["search_term"].map(_intent)
    out["intent_type"] = intents.map(lambda x: x[0])
    out["intent_category"] = intents.map(lambda x: x[1])
    out["intent_reason"] = intents.map(lambda x: x[2])

    decisions, reasons, confidence, review = [], [], [], []
    for r in out.itertuples(index=False):
        typ = r.intent_type
        clicks = float(r.clicks)
        conv = float(r.conversions)
        cost = float(r.cost)
        value = float(r.conversion_value)
        roas = value / cost if cost > 0 else np.nan

        if typ in ("unsupported", "irrelevant"):
            decisions.append("BLOCK")
            reasons.append(f"{r.intent_reason} Category: {r.intent_category}. Recommend a negative-keyword review regardless of recorded conversions.")
            confidence.append("HIGH")
            review.append(False)
        elif typ == "irrelevant_or_unclear":
            if clicks >= min_clicks_evaluate and cost >= min_spend_block and conv == 0:
                decisions.append("IGNORE")
                reasons.append("Intent is unclear. Spend is material with no recorded conversions, but relevance is not certain enough for an automatic block; review the query.")
                confidence.append("LOW")
                review.append(True)
            else:
                decisions.append("IGNORE")
                reasons.append("No clear supported-product intent was found. Gather context or review manually before taking action.")
                confidence.append("LOW")
                review.append(True)
        elif typ == "ambiguous":
            if clicks < min_clicks_evaluate or conv < 2:
                decisions.append("IGNORE")
                reasons.append("General financing intent is ambiguous and performance evidence is limited; route to human review.")
                confidence.append("LOW")
                review.append(True)
            elif conv >= min_conversions_promote and np.isfinite(roas) and roas >= min_roas_promote:
                decisions.append("PROMOTE")
                reasons.append("Performance meets the configured conversion and return thresholds, but product relevance still needs human confirmation.")
                confidence.append("MEDIUM")
                review.append(True)
            else:
                decisions.append("IGNORE")
                reasons.append("Financing intent is ambiguous or performance does not meet promotion criteria; inspect before changing targeting.")
                confidence.append("LOW")
                review.append(True)
        else:  # relevant
            if clicks >= min_clicks_promote and conv >= min_conversions_promote and np.isfinite(roas) and roas >= min_roas_promote:
                decisions.append("PROMOTE")
                reasons.append("Relevant business-financing intent with sufficient clicks, multiple conversions and return above the configured threshold.")
                confidence.append("HIGH" if clicks >= 50 and conv >= 5 else "MEDIUM")
                review.append(False if clicks >= 50 and conv >= 5 else True)
            elif clicks >= min_clicks_evaluate and cost >= min_spend_block and conv == 0:
                decisions.append("IGNORE")
                reasons.append("Relevant product intent, but the query has spent materially without recorded conversions. Review targeting, conversion lag and landing-page fit before blocking.")
                confidence.append("MEDIUM")
                review.append(True)
            else:
                decisions.append("IGNORE")
                reasons.append("Relevant product intent, but evidence is not strong enough for promotion under the configured thresholds.")
                confidence.append("LOW" if clicks < min_clicks_promote or conv < min_conversions_promote else "MEDIUM")
                review.append(True)

    out["triage_decision"] = decisions
    out["confidence"] = confidence
    out["reason"] = reasons
    out["human_review"] = review
    return out
