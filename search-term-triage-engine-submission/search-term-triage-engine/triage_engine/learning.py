"""
Reviewer Precedent & Session-Level Learning Engine (TriageIQ).

Implements Enhancement C:
- Records analyst corrections in session memory (original decision, revised decision, query, campaign, ad group, reason, timestamp).
- Computes contextual similarity between unreviewed queries and past analyst decisions.
- Surfaces relevant precedents with similarity metrics and plain-English guidance.
- Treats corrections as consultative guidance without silently overwriting statistical evidence.
- Preserves full audit separation between engine recommendations and reviewer decisions.
"""

import re
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

def tokenize_query(q: str) -> set:
    """Extracts alphanumeric tokens for Jaccard and overlap comparison."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(q).lower()).strip()
    tokens = set(clean.split())
    # Remove single characters
    return {t for t in tokens if len(t) > 1}


def compute_query_similarity(q1: str, q2: str) -> float:
    """
    Computes token-level Jaccard similarity between two search queries.
    """
    t1 = tokenize_query(q1)
    t2 = tokenize_query(q2)
    if not t1 or not t2:
        return 0.0
    
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    if not union:
        return 0.0
        
    return len(intersection) / len(union)


class ReviewerPrecedentMemory:
    """
    Manages session-level memory of human analyst corrections,
    precedent indexing, and contextual similarity queries.
    """
    def __init__(self):
        # List of correction records
        self.corrections: List[Dict[str, Any]] = []
        # Fast lookup by normalized query
        self.by_query: Dict[str, Dict[str, Any]] = {}

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self.corrections

    def record_correction(
        self,
        query_text: str,
        original_decision: str,
        revised_decision: str,
        campaign: str = "—",
        ad_group: str = "—",
        reviewer_reason: str = "",
        reason: str = "",
        reviewer_name: str = "",
        reviewer: str = "",
        metrics: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Records an analyst correction with full audit metadata.
        """
        norm_q = str(query_text).strip().lower()
        now_ts = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_reason = reviewer_reason or reason or "Analyst verified commercial intent."
        final_reviewer = reviewer_name or reviewer or "Human Analyst"
        
        record = {
            "query_text": str(query_text).strip(),
            "query_normalized": norm_q,
            "campaign": str(campaign).strip(),
            "ad_group": str(ad_group).strip(),
            "original_decision": str(original_decision).upper(),
            "revised_decision": str(revised_decision).upper(),
            "reviewer_reason": str(final_reason).strip(),
            "reason": str(final_reason).strip(),
            "reviewer_name": str(final_reviewer).strip(),
            "reviewer": str(final_reviewer).strip(),
            "metrics": metrics or {},
            "timestamp": now_ts
        }
        
        self.by_query[norm_q] = record
        
        # Replace if query already in list, else append
        self.corrections = [c for c in self.corrections if c["query_normalized"] != norm_q]
        self.corrections.append(record)
        
        return record

    def find_best_precedent(
        self,
        target_query: str,
        target_campaign: str = "",
        campaign: str = "",
        min_similarity: float = 0.40,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Searches previous reviewer corrections for the most relevant contextual precedent.
        Returns precedent dictionary with similarity score and guidance explanation if found.
        """
        norm_target = str(target_query).strip().lower()
        effective_campaign = target_campaign or campaign or ""
        
        # Exact match check first
        if norm_target in self.by_query:
            rec = self.by_query[norm_target]
            return {
                "has_precedent": True,
                "query_text": rec["query_text"],
                "precedent_query": rec["query_text"],
                "original_decision": rec["original_decision"],
                "revised_decision": rec["revised_decision"],
                "reviewer_reason": rec["reviewer_reason"],
                "reason": rec["reviewer_reason"],
                "reviewer_name": rec["reviewer_name"],
                "reviewer": rec["reviewer_name"],
                "timestamp": rec["timestamp"],
                "similarity": 1.0,
                "guidance_explanation": (
                    f"Direct Precedent (100% Match): A reviewer previously revised '{rec['query_text']}' "
                    f"from {rec['original_decision']} to {rec['revised_decision']} on {rec['timestamp']} "
                    f"(Reason: '{rec['reviewer_reason']}')."
                )
            }
            
        # Fuzzy / semantic token matching
        best_match = None
        best_score = 0.0
        
        target_tokens = tokenize_query(target_query)
        if not target_tokens:
            return None
            
        for rec in self.corrections:
            sim = compute_query_similarity(target_query, rec["query_text"])
            
            # Boost score slightly if from the exact same campaign
            if effective_campaign and rec["campaign"] and effective_campaign.lower() == rec["campaign"].lower():
                sim += 0.08
                
            if sim > best_score and sim >= min_similarity:
                best_score = sim
                best_match = rec
                
        if best_match:
            return {
                "has_precedent": True,
                "query_text": best_match["query_text"],
                "precedent_query": best_match["query_text"],
                "original_decision": best_match["original_decision"],
                "revised_decision": best_match["revised_decision"],
                "reviewer_reason": best_match["reviewer_reason"],
                "reason": best_match["reviewer_reason"],
                "reviewer_name": best_match["reviewer_name"],
                "reviewer": best_match["reviewer_name"],
                "timestamp": best_match["timestamp"],
                "similarity": round(min(best_score, 0.99), 2),
                "guidance_explanation": (
                    f"Contextual Precedent ({min(best_score, 0.99):.0%} Similarity): A reviewer previously updated similar query "
                    f"'{best_match['query_text']}' from {best_match['original_decision']} to {best_match['revised_decision']} on {best_match['timestamp']} "
                    f"(Reason: '{best_match['reviewer_reason']}'). Consider whether this rationale applies here."
                )
            }
            
        return None

    def export_to_dataframe(self) -> pd.DataFrame:
        """Returns corrections log as a DataFrame for export."""
        if not self.corrections:
            return pd.DataFrame(columns=[
                "Timestamp", "Query", "Campaign", "Ad Group", 
                "Original Engine Decision", "Reviewer Revised Decision", 
                "Reviewer Reason", "Reviewer Name"
            ])
            
        return pd.DataFrame([
            {
                "Timestamp": c["timestamp"],
                "Query": c["query_text"],
                "Campaign": c["campaign"],
                "Ad Group": c["ad_group"],
                "Original Engine Decision": c["original_decision"],
                "Reviewer Revised Decision": c["revised_decision"],
                "Reviewer Reason": c["reviewer_reason"],
                "Reviewer Name": c["reviewer_name"]
            }
            for c in self.corrections
        ])
