import re
from collections import defaultdict

STOPWORDS = {
    'for', 'in', 'the', 'a', 'an', 'to', 'of', 'and', 'with', 'on', 'at', 
    'by', 'from', 'about', 'into', 'over', 'after', 'your', 'my', 'our'
}

def normalize_query(query):
    """
    Normalizes query by lowercasing, removing punctuation, and filtering common stopwords.
    """
    clean_q = re.sub(r'[^\w\s]', ' ', str(query).lower())
    tokens = [t for t in clean_q.split() if t and t not in STOPWORDS]
    return sorted(tokens)

def compute_jaccard_similarity(tokens_a, tokens_b):
    """
    Computes Jaccard similarity between two token lists.
    """
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0

def cluster_search_terms(records, similarity_threshold=0.60, min_cluster_size=2):
    """
    Groups search terms into syntactic/token clusters.
    Computes aggregate metrics, detects recommendation conflicts, and preserves row mappings.
    Method: Syntactic token-set overlap and N-gram similarity.
    """
    if not records:
        return []

    # Pre-compute normalized tokens for each record
    normalized_data = []
    for r in records:
        tokens = normalize_query(r.get('search_term', ''))
        normalized_data.append({
            'record': r,
            'tokens': tokens,
            'token_str': " ".join(tokens)
        })

    # Grouping using greedy representative assignment with inverted token index
    clusters = [] # list of lists of record dicts
    cluster_representatives = []
    token_to_clusters = defaultdict(list) # token -> list of cluster indices

    for item in normalized_data:
        tokens = item['tokens']
        if not tokens:
            continue

        assigned = False
        
        # Fast candidate retrieval via inverted index
        candidate_cluster_ids = set()
        for t in tokens:
            if t in token_to_clusters:
                candidate_cluster_ids.update(token_to_clusters[t])

        for c_idx in candidate_cluster_ids:
            rep_tokens = cluster_representatives[c_idx]
            sim = compute_jaccard_similarity(tokens, rep_tokens)
            if sim >= similarity_threshold:
                clusters[c_idx].append(item['record'])
                assigned = True
                break
        
        if not assigned:
            new_idx = len(cluster_representatives)
            cluster_representatives.append(tokens)
            clusters.append([item['record']])
            for t in tokens:
                token_to_clusters[t].append(new_idx)

    # Filter and format clusters
    formatted_clusters = []
    cluster_counter = 1

    for c_items in clusters:
        # We present all clusters with size >= min_cluster_size, or single high spend terms
        if len(c_items) < min_cluster_size:
            continue

        total_spend = sum(float(x.get('cost') or 0.0) for x in c_items)
        total_clicks = sum(int(x.get('clicks') or 0) for x in c_items)
        total_conv = sum(float(x.get('conversions') or 0.0) for x in c_items)

        # Detect recommendation conflicts
        decisions = set(x.get('recommendation') for x in c_items)
        has_conflicts = ('PROMOTE' in decisions and 'BLOCK' in decisions) or \
                        ('PROMOTE' in decisions and 'HUMAN REVIEW' in decisions and len(c_items) > 1)
        
        conflict_summary = None
        if 'PROMOTE' in decisions and 'BLOCK' in decisions:
            conflict_summary = "High conflict: Cluster contains both PROMOTE and BLOCK terms across different contexts."
        elif 'PROMOTE' in decisions and 'HUMAN REVIEW' in decisions:
            conflict_summary = "Variance notice: Some queries have sufficient evidence to PROMOTE while similar variants remain uncertain."

        # Pick representative term (the one with highest spend or highest clicks)
        sorted_by_impact = sorted(c_items, key=lambda x: (float(x.get('cost') or 0.0), int(x.get('clicks') or 0)), reverse=True)
        rep_term = sorted_by_impact[0].get('search_term')

        # Decision distribution inside cluster
        decision_counts = defaultdict(int)
        for x in c_items:
            decision_counts[x.get('recommendation', 'UNKNOWN')] += 1

        formatted_clusters.append({
            'cluster_id': f"cluster_{cluster_counter}",
            'cluster_name': rep_term,
            'terms_count': len(c_items),
            'total_spend': round(total_spend, 2),
            'total_clicks': total_clicks,
            'total_conversions': round(total_conv, 1),
            'has_conflicts': has_conflicts,
            'conflict_summary': conflict_summary,
            'decision_breakdown': dict(decision_counts),
            'terms': [
                {
                    'row_id': x.get('row_id'),
                    'search_term': x.get('search_term'),
                    'campaign': x.get('campaign'),
                    'ad_group': x.get('ad_group'),
                    'recommendation': x.get('recommendation'),
                    'confidence': x.get('confidence'),
                    'clicks': x.get('clicks'),
                    'cost': x.get('cost'),
                    'conversions': x.get('conversions'),
                    'cpa': x.get('cpa')
                } for x in c_items
            ],
            'method': 'Syntactic Token-Overlap Clustering (Jaccard >= 0.60)'
        })
        cluster_counter += 1

    # Sort clusters by total spend descending
    formatted_clusters.sort(key=lambda c: c['total_spend'], reverse=True)
    return formatted_clusters
