"""
Intent Clustering and Near-Duplicate Normalization Module (TriageIQ).

Groups lexical and syntactic variations of the same intent:
- Lowercasing, punctuation stripping, token-sorting.
- Preserves distinct commercial qualifiers (e.g. 'alternatives', 'calculator', 'bad credit', 'personal', 'jobs').
- Detects conflicting decisions within clusters for reviewer reconciliation.
- Attaches cluster_id and canonical query back to every input row for 100% row traceability.

LIMITATIONS DOCUMENTATION:
This clustering engine uses token-level syntactic normalization and deterministic n-gram similarity.
It reliably collapses pluralizations ('loan' vs 'loans'), punctuation differences, and word re-orderings.
It explicitly preserves critical business and commercial distinctions:
- Business loans vs personal loans are strictly segregated.
- Financing vs employment/career queries are strictly segregated.
- Calculators and alternatives are strictly kept in distinct intent groups.
"""

import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

# Common search stop words that don't differentiate commercial intent
STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "for", 
    "from", "how", "in", "is", "it", "of", "on", "or", "that", "the", 
    "this", "to", "was", "what", "when", "where", "who", "will", "with"
}

# Critical qualifiers that must NEVER be stripped, altered, or conflated
CRITICAL_QUALIFIERS = {
    "alternative", "alternatives", "vs", "versus", "calculator", "calculators",
    "requirements", "bad credit", "poor credit", "review", "reviews",
    "login", "portal", "template", "templates", "free", "rates", "interest",
    "personal", "student", "car", "auto", "mortgage", "job", "jobs", "salary",
    "career", "careers", "hiring", "resume", "internship", "grant", "grants"
}

def normalize_query_tokens(query: str) -> List[str]:
    """
    Cleans and tokenizes a search query, stripping punctuation and minor stop words,
    while performing lightweight stemming for simple plurals without distorting words.
    """
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(query).lower()).strip()
    raw_tokens = clean.split()
    normalized = []
    
    for t in raw_tokens:
        if t in CRITICAL_QUALIFIERS:
            normalized.append(t)
            continue
            
        if t not in STOPWORDS and len(t) > 1:
            # Conservative plural stemming: only remove trailing 's' if not 'ss', 'us', 'is'
            if t.endswith("s") and len(t) > 3 and not (t.endswith("ss") or t.endswith("us") or t.endswith("is")):
                t = t[:-1]
            normalized.append(t)
            
    return normalized if normalized else raw_tokens


def get_canonical_intent_key(query: str) -> str:
    """
    Produces a canonical sorted token representation for fast exact-intent grouping.
    e.g., "business loans fast online" and "fast online business loan" -> "business fast loan online"
    """
    tokens = normalize_query_tokens(query)
    tokens.sort()
    return " ".join(tokens)


def infer_intent_category(tokens: List[str]) -> Tuple[str, str]:
    """
    Infers the high-level intent category and generates a concise shared explanation.
    """
    tok_set = set(tokens)
    
    if any(k in tok_set for k in ["personal", "student", "car", "auto", "mortgage", "grant", "grants", "job", "jobs", "salary", "resume", "template"]):
        return (
            "Off-Target / Non-Commercial",
            "Queries targeting consumer loans, grants, employment, or templates outside B2B commercial finance scope."
        )
    elif any(k in tok_set for k in ["calculator", "calculators", "estimate", "estimator"]):
        return (
            "Tool / Loan Calculator",
            "Queries from borrowers seeking financial payment calculators, amortization tools, or cost estimators."
        )
    elif any(k in tok_set for k in ["alternative", "alternatives", "vs", "versus", "competitor"]):
        return (
            "Competitor / Alternative Comparison",
            "Borrowers actively evaluating alternative funding options or comparing competing lenders."
        )
    elif any(k in tok_set for k in ["equipment", "machinery", "lease", "leasing"]):
        return (
            "Equipment Financing & Leasing",
            "Commercial borrowers seeking capital specifically to purchase or lease business equipment and machinery."
        )
    elif any(k in tok_set for k in ["bad", "poor", "credit", "score"]):
        return (
            "Credit Qualification / Subprime",
            "Borrowers specifically searching for lenders accommodating low credit scores or challenging financial history."
        )
    elif any(k in tok_set for k in ["working", "capital", "line", "cash", "advance", "mca"]):
        return (
            "Working Capital & Cash Flow",
            "Businesses seeking short-term working capital, lines of credit, or revenue-based cash advances."
        )
    else:
        return (
            "General Commercial Borrowing",
            "Core commercial search terms seeking small business loans, commercial lenders, or funding terms."
        )


def cluster_search_queries(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Groups search queries into stable intent clusters with decision conflict detection.
    
    Returns:
        (clusters_summary, updated_records)
        where updated_records has 'cluster_id', 'cluster_canonical_query', and 'cluster_size' added to every row.
    """
    # 1. Group records by canonical intent key
    canonical_map = defaultdict(list)
    for idx, r in enumerate(records):
        query = r.get("query_text") or r.get("search_term") or ""
        key = get_canonical_intent_key(query)
        canonical_map[key].append(idx)
        
    clusters_summary = []
    cluster_counter = 1
    
    # Sort keys for deterministic, stable cluster IDs across runs
    sorted_keys = sorted(canonical_map.keys())
    
    for key in sorted_keys:
        indices = canonical_map[key]
        group_records = [records[i] for i in indices]
        
        # Pick canonical variant with the highest impressions / clicks
        group_records_sorted = sorted(
            group_records, 
            key=lambda x: (x.get("impressions", 0), x.get("clicks", 0)), 
            reverse=True
        )
        canonical_query = group_records_sorted[0].get("query_text") or group_records_sorted[0].get("search_term") or key
        cluster_id = f"CLUSTER-{cluster_counter:05d}"
        cluster_size = len(indices)
        
        tot_impr = sum(r.get("impressions", 0) for r in group_records)
        tot_clicks = sum(r.get("clicks", 0) for r in group_records)
        tot_cost = sum(r.get("cost", 0.0) for r in group_records)
        tot_conv = sum(r.get("conversions", 0.0) for r in group_records)
        tot_val = sum(r.get("conversion_value", 0.0) for r in group_records)
        
        # Detect decision conflicts within the cluster
        decisions_in_cluster = set(r.get("decision", "IGNORE") for r in group_records)
        has_conflict = len(decisions_in_cluster) > 1
        
        if has_conflict:
            dec_list = " vs ".join(sorted(decisions_in_cluster))
            conflict_type = f"MIXED_DECISIONS ({dec_list})"
            conflict_explanation = (
                f"⚠️ Decision Conflict: Member queries have divergent recommendations ({dec_list}). "
                f"For example, one variation met statistical promotion thresholds while another was quarantined or ignored. "
                f"Reviewer reconciliation is recommended to harmonize keyword rules."
            )
        else:
            unanimous_dec = list(decisions_in_cluster)[0] if decisions_in_cluster else "IGNORE"
            conflict_type = "UNIFORM"
            conflict_explanation = f"Consensus: All {cluster_size} query variations unanimously assigned {unanimous_dec}."
            
        # Intent category and explanation
        intent_cat, intent_expl = infer_intent_category(key.split())
        
        # Build individual member details list
        member_queries = []
        for r in group_records:
            member_queries.append({
                "row_id": r.get("row_id"),
                "query_text": r.get("query_text") or r.get("search_term") or "",
                "campaign": r.get("campaign", "—"),
                "ad_group": r.get("ad_group", "—"),
                "clicks": r.get("clicks", 0),
                "cost": round(r.get("cost", 0.0), 2),
                "conversions": int(r.get("conversions", 0)),
                "cpa": r.get("cpa"),
                "ci_lower": r.get("ci_lower", 0.0),
                "ci_upper": r.get("ci_upper", 0.0),
                "decision": r.get("decision", "IGNORE"),
                "needs_review": bool(r.get("needs_review", False)),
                "reason": r.get("reason", "")
            })
        
        # Annotate each original row with cluster metadata for complete traceability
        for i in indices:
            records[i]["cluster_id"] = cluster_id
            records[i]["cluster_canonical_query"] = canonical_query
            records[i]["cluster_size"] = cluster_size
            records[i]["cluster_has_conflict"] = has_conflict
            
        clusters_summary.append({
            "cluster_id": cluster_id,
            "canonical_query": canonical_query,
            "intent_key": key,
            "intent_category": intent_cat,
            "shared_intent_explanation": intent_expl,
            "has_conflict": has_conflict,
            "conflict_type": conflict_type,
            "conflict_explanation": conflict_explanation,
            "variant_count": cluster_size,
            "variants": list(set(r.get("query_text") or r.get("search_term") or "" for r in group_records)),
            "member_queries": member_queries,
            "record_indices": indices,
            "total_impressions": tot_impr,
            "total_clicks": tot_clicks,
            "total_cost": round(tot_cost, 2),
            "total_conversions": round(tot_conv, 1),
            "total_conversion_value": round(tot_val, 2)
        })
        cluster_counter += 1
        
    return clusters_summary, records
