"""
Context-Aware Negative Keyword Suggestions Engine (TriageIQ).
Generates precise negative keyword candidates from:
1. Explicit business-scope exclusions (e.g., consumer loans, auto loans, grants, jobs, templates).
2. Statistically supported poor-performance cases (spend bleeders exceeding target CPA with zero conversions).

Adheres strictly to the Narrowest Appropriate Scope Rule:
- Only recommends Campaign scope for universally off-target terms.
- Restricts ad-group specific bleeders to Ad Group scope.
- Populates explicit over-exclusion risk warnings to protect converting B2B search queries.
"""

import re
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from triage_engine.rules import AdvertiserProfile

# High-value commercial tokens that should trigger over-exclusion warnings if used in phrase match
COMMERCIAL_TOKENS = {
    "business", "commercial", "equipment", "loan", "loans", "financing", "finance", 
    "funding", "capital", "lender", "lending", "credit", "line", "cash", "advance"
}

def analyze_over_exclusion_risk(keyword_text: str, match_type: str, scope: str) -> Tuple[str, str]:
    """
    Evaluates whether adding this negative keyword carries risk of over-blocking legitimate B2B queries.
    Returns (risk_level, risk_warning).
    """
    tokens = set(re.sub(r"[^a-zA-Z0-9\s]", " ", keyword_text.lower()).split())
    colliding_tokens = tokens.intersection(COMMERCIAL_TOKENS)
    
    if match_type == "Negative Exact":
        return (
            "LOW",
            "🟢 Low Risk: Exact match strictly restricts blocking to this specific query string, protecting all related search variations."
        )
        
    # For Negative Phrase:
    if len(tokens) == 1:
        single_token = list(tokens)[0]
        if single_token in colliding_tokens:
            return (
                "CRITICAL",
                f"🚨 Critical Over-Exclusion Risk: Single-word phrase '{single_token}' will block ALL business queries containing '{single_token}'. Highly recommend switching to Negative Exact or specific phrase."
            )
        elif single_token in {"bad", "poor", "instant", "fast", "apply", "free", "rates"}:
            return (
                "HIGH",
                f"⚠️ High Over-Exclusion Risk: Broad qualifier '{single_token}' could block valid B2B searchers (e.g. 'instant business financing'). Switch to multi-token phrase."
            )
            
    if colliding_tokens:
        tok_str = ", ".join(f"'{t}'" for t in sorted(colliding_tokens))
        return (
            "MEDIUM",
            f"⚠️ Moderate Risk: Phrase contains core term(s) {tok_str}. Verify that legitimate B2B variations are not suppressed."
        )
        
    return (
        "LOW",
        "🟢 Low Risk: Negative phrase targets specific off-target pattern with zero overlap with core commercial lending vocabulary."
    )


def generate_context_aware_negative_suggestions(
    res_df: pd.DataFrame,
    advertiser_profile: AdvertiserProfile,
    target_cpa: float = 220.0
) -> List[Dict[str, Any]]:
    """
    Generates structured, audited negative keyword candidates from the active dataset.
    """
    suggestions = []
    seen_negatives = set()
    candidate_id = 1
    
    # 1. EXPLICIT BUSINESS SCOPE EXCLUSIONS
    # Scan blocked rows that match known negative triggers
    blocked_df = res_df[res_df["decision"] == "BLOCK"].copy()
    
    # Also evaluate queries across the account with 0 conversions matching exclusion triggers
    for _, row in blocked_df.iterrows():
        query = str(row.get("query_text", "")).strip()
        campaign = str(row.get("campaign", "Default Campaign")).strip()
        ad_group = str(row.get("ad_group", "Default Ad Group")).strip()
        clicks = int(row.get("clicks", 0))
        cost = float(row.get("cost", 0.0))
        conversions = float(row.get("conversions", 0.0))
        ci_upper = float(row.get("ci_upper", 0.0))
        reason = str(row.get("reason", ""))
        
        # Determine trigger match
        matched_trigger = None
        triggers = getattr(advertiser_profile, "off_target_triggers", []) or getattr(advertiser_profile, "negative_triggers", [])
        for trig in triggers:
            if re.search(r'\b' + re.escape(trig) + r'\b', query.lower()):
                matched_trigger = trig
                break
                
        if matched_trigger:
            # Explicit off-target business scope
            # Determine narrowest appropriate scope:
            # Universally toxic across all business products (jobs, grants, consumer personal loans) -> Campaign scope
            universal_triggers = {
                "personal loan", "personal loans", "car loan", "car financing", "auto loan", 
                "student loan", "mortgage", "grant", "grants", "government grants", 
                "jobs", "job", "salary", "hiring", "resume", "internship", "templates", "sample"
            }
            
            is_universal = any(u in matched_trigger for u in universal_triggers)
            scope = "Campaign" if is_universal else "Ad Group"
            
            # Match type selection:
            # If trigger is a clean multi-word concept like "personal loans", recommend Negative Phrase
            # If query is long/specific or contains commercial root, recommend Negative Exact
            if len(matched_trigger.split()) >= 2 and is_universal:
                match_type = "Negative Phrase"
                neg_text = f'"{matched_trigger}"'
                clean_kw = matched_trigger
            else:
                match_type = "Negative Exact"
                neg_text = f"[{query}]"
                clean_kw = query
                
            risk_level, risk_warning = analyze_over_exclusion_risk(clean_kw, match_type, scope)
            
            dedup_key = (campaign, scope if scope == "Campaign" else ad_group, neg_text, match_type)
            if dedup_key not in seen_negatives:
                seen_negatives.add(dedup_key)
                explanation = (
                    f"Violates {advertiser_profile.name} commercial scope. "
                    f"Selected {scope} {match_type} to eliminate off-target ad spend while protecting related products."
                )
                evidence = f"Matches exclusion trigger '{matched_trigger}'; ${cost:.2f} historical spend across {clicks} clicks with 0 conversions."
                
                suggestions.append({
                    "suggestion_id": f"NEG-{candidate_id:04d}",
                    "negative_keyword": neg_text,
                    "clean_keyword": clean_kw,
                    "query_text": query,
                    "campaign": campaign,
                    "ad_group": ad_group if scope == "Ad Group" else "[All Ad Groups in Campaign]",
                    "recommended_scope": scope,
                    "recommended_match_type": match_type,
                    "trigger_type": "EXPLICIT_BUSINESS_EXCLUSION",
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": int(conversions),
                    "ci_upper": ci_upper,
                    "evidence": evidence,
                    "explanation": explanation,
                    "over_exclusion_warning": risk_warning,
                    "risk_level": risk_level,
                    "analyst_status": "Pending Analyst Approval"
                })
                candidate_id += 1
                
        else:
            # 2. STATISTICALLY SUPPORTED POOR-PERFORMANCE BLEEDERS
            # Clicks >= 12, cost >= 1.2x target CPA, 0 conversions, ci_upper <= 0.15
            if conversions == 0 and cost >= (1.2 * target_cpa) and clicks >= 12:
                # Narrowest Appropriate Scope Rule:
                # By default, bleeder is specific to the ad group where it drained budget!
                scope = "Ad Group"
                match_type = "Negative Exact"
                neg_text = f"[{query}]"
                clean_kw = query
                
                risk_level, risk_warning = analyze_over_exclusion_risk(clean_kw, match_type, scope)
                
                dedup_key = (campaign, ad_group, neg_text, match_type)
                if dedup_key not in seen_negatives:
                    seen_negatives.add(dedup_key)
                    explanation = (
                        f"Spend bleeder exceeding allowable CPA ceiling. Restricted to Ad Group Negative Exact "
                        f"to prevent continued drain without penalizing this query in other ad groups where it might convert."
                    )
                    evidence = f"Spent ${cost:.2f} (Target CPA: ${target_cpa:.2f}) across {clicks} clicks with zero conversions. Wilson 95% upper bound: {ci_upper:.1%}."
                    
                    suggestions.append({
                        "suggestion_id": f"NEG-{candidate_id:04d}",
                        "negative_keyword": neg_text,
                        "clean_keyword": clean_kw,
                        "query_text": query,
                        "campaign": campaign,
                        "ad_group": ad_group,
                        "recommended_scope": scope,
                        "recommended_match_type": match_type,
                        "trigger_type": "PERFORMANCE_BLEEDER",
                        "clicks": clicks,
                        "cost": round(cost, 2),
                        "conversions": int(conversions),
                        "ci_upper": ci_upper,
                        "evidence": evidence,
                        "explanation": explanation,
                        "over_exclusion_warning": risk_warning,
                        "risk_level": risk_level,
                        "analyst_status": "Pending Analyst Approval"
                    })
                    candidate_id += 1

    return suggestions
