"""
Exporter Module for Google Ads Editor and Complete Audit Trail (TriageIQ).

Generates six actionable files:
1. full_triage_audit.csv: 100% of input rows with required contract decisions, confidence, and full evidence.
2. google_ads_negative_keywords.csv: Clean deduplicated exclusions ready for Google Ads Editor.
3. google_ads_promoted_keywords.csv: Clean deduplicated additions with suggested Max CPC bids.
4. human_review_queue.csv: Exactly the rows where needs_review == True.
5. negative_keyword_suggestions.csv: Context-aware negative suggestions with scope, match type, and over-exclusion risk warnings.
6. reviewer_corrections_log.csv: Complete audit trail of analyst corrections and session rationale.
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional

def export_triage_results(
    results: List[Dict[str, Any]], 
    output_dir: str,
    negative_suggestions: Optional[List[Dict[str, Any]]] = None,
    corrections_df: Optional[pd.DataFrame] = None
) -> Dict[str, str]:
    """
    Exports triage decisions into validated CSV files.
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    
    # 1. Full Audit Report
    # Ensure stable ordering and columns
    full_report_path = os.path.join(output_dir, "full_triage_audit.csv")
    df.to_csv(full_report_path, index=False, encoding="utf-8-sig")
    
    # 2. Google Ads Upload: Negative Keywords
    # Standard Google Ads Editor schema: Campaign, Ad Group, Keyword, Criterion Type
    negatives = df[df["decision"] == "BLOCK"].copy()
    if not negatives.empty:
        # If action level is Campaign, Ad Group should be blank for account-wide coverage
        neg_export = pd.DataFrame({
            "Campaign": negatives["campaign"],
            "Ad Group": negatives.apply(lambda r: r["ad_group"] if r.get("action_level") == "Ad Group" else "", axis=1),
            "Keyword": negatives["query_text"],
            "Criterion Type": negatives["negative_type"]
        })
        # Deduplicate to prevent Google Ads Editor import conflicts
        neg_export = neg_export.drop_duplicates(subset=["Campaign", "Ad Group", "Keyword", "Criterion Type"]).reset_index(drop=True)
    else:
        neg_export = pd.DataFrame(columns=["Campaign", "Ad Group", "Keyword", "Criterion Type"])
        
    negatives_path = os.path.join(output_dir, "google_ads_negative_keywords.csv")
    neg_export.to_csv(negatives_path, index=False, encoding="utf-8-sig")
    
    # 3. Google Ads Upload: Promoted Keywords
    # Standard Google Ads Editor schema: Campaign, Ad Group, Keyword, Match Type, Max CPC
    promotes = df[df["decision"] == "PROMOTE"].copy()
    if not promotes.empty:
        prom_export = pd.DataFrame({
            "Campaign": promotes["campaign"],
            "Ad Group": promotes["ad_group"],
            "Keyword": promotes["query_text"],
            "Match Type": "Exact",
            "Max CPC": promotes["proposed_bid"]
        })
        # Deduplicate unique keyword per ad group
        prom_export = prom_export.drop_duplicates(subset=["Campaign", "Ad Group", "Keyword"]).reset_index(drop=True)
    else:
        prom_export = pd.DataFrame(columns=["Campaign", "Ad Group", "Keyword", "Match Type", "Max CPC"])
        
    promoted_path = os.path.join(output_dir, "google_ads_promoted_keywords.csv")
    prom_export.to_csv(promoted_path, index=False, encoding="utf-8-sig")
    
    # 4. Human Review Queue (Strictly rows where needs_review == True)
    review_queue = df[df["needs_review"] == True].copy()
    review_queue_path = os.path.join(output_dir, "human_review_queue.csv")
    review_queue.to_csv(review_queue_path, index=False, encoding="utf-8-sig")
    
    # 5. Context-Aware Negative Suggestions (Enhancement A)
    neg_suggestions_path = os.path.join(output_dir, "negative_keyword_suggestions.csv")
    if negative_suggestions:
        sug_df = pd.DataFrame(negative_suggestions)
        sug_df.to_csv(neg_suggestions_path, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=[
            "suggestion_id", "negative_keyword", "clean_keyword", "query_text", 
            "campaign", "ad_group", "recommended_scope", "recommended_match_type", 
            "trigger_type", "clicks", "cost", "conversions", "ci_upper", 
            "evidence", "explanation", "over_exclusion_warning", "risk_level", "analyst_status"
        ]).to_csv(neg_suggestions_path, index=False, encoding="utf-8-sig")

    # 6. Reviewer Corrections Log (Enhancement C)
    corrections_path = os.path.join(output_dir, "reviewer_corrections_log.csv")
    if corrections_df is not None and not corrections_df.empty:
        corrections_df.to_csv(corrections_path, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=[
            "Timestamp", "Query", "Campaign", "Ad Group", 
            "Original Engine Decision", "Reviewer Revised Decision", 
            "Reviewer Reason", "Reviewer Name"
        ]).to_csv(corrections_path, index=False, encoding="utf-8-sig")
    
    return {
        "full_report": full_report_path,
        "negatives": negatives_path,
        "promoted": promoted_path,
        "review_queue": review_queue_path,
        "negative_suggestions": neg_suggestions_path,
        "corrections_log": corrections_path
    }
