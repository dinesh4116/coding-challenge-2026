import re
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

# Negative Intent Lexicons
NEGATIVE_INTENTS = {
    "careers_jobs": [
        "jobs", "job", "career", "careers", "internship", "intern", "hiring",
        "salary", "salaries", "glassdoor", "indeed", "resume", "vacancy", "openings"
    ],
    "free_piracy": [
        "free", "crack", "cracked", "torrent", "pirate", "keygen", "warez",
        "nulled", "download free", "freeware", "open source alternative free"
    ],
    "support_login": [
        "login", "log in", "sign in", "signin", "portal", "customer care",
        "customer service", "toll free", "helpline", "hotline", "phone number",
        "contact number", "support desk", "reset password", "my account", "refund"
    ],
    "informational_diy": [
        "diy", "how to make", "what is", "meaning of", "definition", "wikipedia",
        "syllabus", "pdf download", "slideshare", "research paper", "history of"
    ],
    "counterfeit_mismatch": [
        "replica", "fake", "counterfeit", "knockoff", "first copy", "dupe"
    ]
}

COMMERCIAL_INTENTS = [
    "buy", "order", "purchase", "shop", "deal", "discount", "coupon",
    "pricing", "price", "cost", "hire", "quote", "agency", "software",
    "platform", "solution", "tool", "service", "services", "best", "top",
    "review", "compare", "vs", "supplier", "vendor", "store", "near me"
]

def wilson_score_lower_bound(pos: int, n: int, confidence: float = 0.95) -> float:
    """Calculate the Wilson score interval lower bound for Bernoulli parameter."""
    if n <= 0:
        return 0.0
    # Conversions can exceed clicks in real exports (view-through / all-conv.), which would
    # make p > 1 and crash the square root below. Clamp to a valid proportion.
    pos = max(0.0, min(float(pos), float(n)))
    z = 1.95996  # 95% confidence z-score
    p = pos / n
    denominator = 1 + z**2 / n
    centre_adjusted_probability = p + z**2 / (2 * n)
    adjusted_std_dev = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    return max(0.0, lower_bound)

def analyze_query_intent(query: str, campaign: str = "", ad_group: str = "") -> Dict[str, Any]:
    """Analyze query for commercial intent, negative signals, and campaign relevance."""
    q_lower = str(query).lower().strip()
    words = set(re.findall(r'\b[a-z0-9\-]+\b', q_lower))
    
    # Check negative intents
    found_negatives = []
    matched_neg_category = None
    for category, keywords in NEGATIVE_INTENTS.items():
        for kw in keywords:
            if " " in kw:
                if kw in q_lower:
                    found_negatives.append(kw)
                    if not matched_neg_category:
                        matched_neg_category = category
            else:
                if kw in words:
                    found_negatives.append(kw)
                    if not matched_neg_category:
                        matched_neg_category = category

    # Check commercial intents
    found_commercial = [kw for kw in COMMERCIAL_INTENTS if (kw in words or ((" " in kw) and kw in q_lower))]

    # Campaign & Ad Group context relevance
    context_tokens = set(re.findall(r'\b[a-z0-9]+\b', f"{campaign} {ad_group}".lower()))
    # Remove common filler words
    stop_words = {"the", "and", "or", "for", "in", "of", "to", "with", "campaign", "adgroup", "ad", "group", "search", "exact", "phrase", "broad"}
    context_tokens = context_tokens - stop_words

    token_overlap = len(words.intersection(context_tokens))
    relevance_score = 0.5  # Neutral default
    
    if len(context_tokens) > 0:
        relevance_score = min(1.0, 0.4 + (token_overlap / max(1, len(words))) * 0.6)
    
    # Heavy penalty if negative intent found
    if found_negatives:
        relevance_score = max(0.05, relevance_score - 0.55)
    elif found_commercial:
        relevance_score = min(1.0, relevance_score + 0.25)

    return {
        "negative_signals": found_negatives,
        "negative_category": matched_neg_category,
        "commercial_signals": found_commercial,
        "relevance_score": round(relevance_score, 3),
        "token_overlap": token_overlap
    }

def triage_search_terms(df: pd.DataFrame, target_cpa: float = 35.0, target_roas: float = 3.0) -> pd.DataFrame:
    """
    Main triage engine. Vectorized processing of Google Ads search terms.
    Evaluates:
    - Statistical credibility (Wilson lower bound, sample size)
    - Economic efficiency (CPA, ROAS, Cost)
    - Semantic intent & relevance
    - Single-conversion trap avoidance
    """
    df = df.copy()

    # Ensure numeric columns are properly formatted and fill NaNs
    num_cols = ['impressions', 'clicks', 'cost', 'conversions', 'conversion_value']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0

    # Ensure text columns
    text_cols = ['query', 'campaign', 'ad_group', 'match_type']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna('')
        else:
            df[col] = ''

    # Derived performance metrics
    df['ctr'] = np.where(df['impressions'] > 0, (df['clicks'] / df['impressions']) * 100, 0.0)
    df['cvr'] = np.where(df['clicks'] > 0, (df['conversions'] / df['clicks']) * 100, 0.0)
    df['cpa'] = np.where(df['conversions'] > 0, df['cost'] / df['conversions'], 0.0)
    df['roas'] = np.where(df['cost'] > 0, df['conversion_value'] / df['cost'], 0.0)
    df['cpc'] = np.where(df['clicks'] > 0, df['cost'] / df['clicks'], 0.0)

    # Round derived metrics
    df['ctr'] = df['ctr'].round(2)
    df['cvr'] = df['cvr'].round(2)
    df['cpa'] = df['cpa'].round(2)
    df['roas'] = df['roas'].round(2)
    df['cpc'] = df['cpc'].round(2)

    results = []

    for idx, row in df.iterrows():
        query = str(row['query'])
        campaign = str(row['campaign'])
        ad_group = str(row['ad_group'])
        impr = int(row['impressions'])
        clicks = int(row['clicks'])
        cost = float(row['cost'])
        conv = float(row['conversions'])
        val = float(row['conversion_value'])
        cvr = float(row['cvr'])
        cpa = float(row['cpa'])
        roas = float(row['roas'])

        intent = analyze_query_intent(query, campaign, ad_group)
        neg_signals = intent['negative_signals']
        neg_cat = intent['negative_category']
        relevance = intent['relevance_score']

        # Statistical calculations
        wilson_cvr = wilson_score_lower_bound(conv, clicks) * 100 if clicks > 0 else 0.0

        action = "IGNORE"
        confidence = 50.0
        reason = ""
        missing_info = ""
        financial_impact = ""
        needs_review = 0

        # CASE 1: Clear Negative Intent Signals (BLOCK)
        if len(neg_signals) > 0 and relevance < 0.40:
            action = "BLOCK"
            sig_list = ", ".join(f"'{s}'" for s in neg_signals[:3])
            
            # Confidence based on negative clarity and spent budget
            if cost > 0:
                confidence = min(98.0, 84.0 + min(14.0, cost / 15.0))
                financial_impact = f"Prevent recurring budget drain: ${cost:.2f} spent with zero purchase intent."
            else:
                confidence = 88.0
                financial_impact = "Proactively shields ad spend before impressions accrue wasted clicks."

            reason = f"Irrelevant search intent detected ({neg_cat or 'unwanted context'}). Contains negative keywords: {sig_list}."
            missing_info = "None. Intent is unambiguously mismatched with commercial conversion goals."

        # CASE 2: High Spend Bleeder (Zero Conversions, Heavy Waste) (BLOCK or REVIEW)
        elif clicks >= 18 and conv == 0 and cost >= (target_cpa * 1.5):
            if relevance < 0.55:
                action = "BLOCK"
                confidence = min(95.0, 78.0 + (cost / (target_cpa * 1.5)) * 10.0)
                reason = f"High budget leakage without results: ${cost:.2f} spent across {clicks} clicks with 0 conversions and low thematic alignment."
                missing_info = "No conversion signal recorded over sufficient statistical sample."
                financial_impact = f"Estimated monthly waste eliminated: ~${cost:.2f}."
            else:
                # IMPORTANT PRINCIPLE: Low conversion counts alone must never justify blocking a relevant term!
                action = "IGNORE"
                needs_review = 1
                confidence = 62.0
                reason = f"High spend (${cost:.2f}, {clicks} clicks) without conversions, but term is highly relevant to '{campaign}'. Do not block prematurely; evaluate ad copy, landing page experience, or pricing friction."
                missing_info = f"Requires landing page bounce rate and conversion funnel audit before negative exclusion."
                financial_impact = f"Guards against accidentally killing a high-value core product query with temporary landing page issues."

        # CASE 3: Single Conversion Trap (Clicks <= 3, Conv >= 1) -> DO NOT AUTOMATICALLY PROMOTE!
        elif conv >= 1 and clicks <= 3:
            action = "IGNORE"
            needs_review = 1
            confidence = 52.0
            reason = f"Single-Conversion Trap: Query generated {conv:.0f} conversion on only {clicks} click(s). While initial signal is positive, small sample size has high statistical volatility (Wilson lower bound: {wilson_cvr:.1f}%)."
            missing_info = f"Needs at least {max(10, 15 - clicks)} more clicks to establish stable conversion rate and verify repeat intent."
            financial_impact = "Prevents premature bid allocation on anomalous one-time queries."

        # CASE 4: Valid High-Performance Candidate (PROMOTE)
        elif conv >= 2 and clicks >= 8 and (roas >= target_roas or (cpa > 0 and cpa <= target_cpa * 1.25)) and relevance >= 0.50:
            action = "PROMOTE"
            # Confidence scales with sample size and economic strength
            evidence_weight = min(30.0, (clicks / 20.0) * 15.0 + (conv / 4.0) * 15.0)
            economic_weight = min(30.0, (roas / target_roas) * 15.0 if roas > 0 else 20.0)
            relevance_weight = relevance * 35.0
            confidence = round(min(97.0, max(75.0, 20.0 + evidence_weight + economic_weight + relevance_weight)), 1)
            
            reason = f"Statistically validated top performer: {conv:.0f} conversions, {cvr:.1f}% CVR (Wilson bound: {wilson_cvr:.1f}%), {f'ROAS {roas:.2f}x' if roas > 0 else f'CPA ${cpa:.2f}'}. High commercial synergy with '{ad_group}'."
            missing_info = "Ready for deliberate exact/phrase match targeting. Recommend dedicated landing page or bid increase."
            financial_impact = f"Scale profitable volume: Query delivered ${val:.2f} conversion value from ${cost:.2f} spend."

        # CASE 5: Moderate Converter but Borderline Evidence
        elif conv >= 1 and clicks >= 4 and clicks < 10:
            if relevance >= 0.60:
                action = "IGNORE"
                needs_review = 1
                confidence = 64.0
                reason = f"Encouraging initial traction ({conv:.0f} conversions, {cvr:.1f}% CVR), but sample size ({clicks} clicks) remains in the statistical exploration phase."
                missing_info = f"Gather 10-15 more clicks to confirm that CPA (${cpa:.2f}) remains sustainable under increased traffic."
                financial_impact = "Avoids premature bid escalation while keeping query active for observation."
            else:
                action = "IGNORE"
                confidence = 55.0
                reason = f"Conversion recorded ({conv:.0f}), but relevance score ({relevance:.2f}) is questionable. Keep monitoring."
                missing_info = "Awaiting further conversion signals."
                financial_impact = "Neutral monitoring."

        # CASE 6: Insufficient Sample Size (Low Impressions / Low Clicks) (IGNORE)
        elif clicks < 10:
            action = "IGNORE"
            confidence = round(min(72.0, 50.0 + (impr / 50.0) * 10.0), 1)
            reason = f"Insufficient data: Query has only accumulated {clicks} click(s) and {impr} impression(s). Not enough statistical power for definitive triage."
            missing_info = f"Requires at least {max(1, 10 - clicks)} additional clicks to establish a reliable baseline."
            financial_impact = "No action recommended; let search auction gather natural volume."

        # CASE 7: High Traffic Low Conversion Rate (borderline)
        elif clicks >= 10 and conv == 0 and cost < (target_cpa * 1.5):
            action = "IGNORE"
            confidence = 65.0
            reason = f"Moderate volume ({clicks} clicks, ${cost:.2f} spend) with no conversions yet, but spend remains within acceptable learning threshold (< ${target_cpa * 1.5:.2f})."
            missing_info = f"Monitor next ${max(10.0, (target_cpa * 1.5) - cost):.2f} spend. If no conversions emerge, escalate to block/review."
            financial_impact = "Permits ongoing statistical exploration without excessive budget risk."

        # DEFAULT FALLBACK
        else:
            action = "IGNORE"
            confidence = 58.0
            reason = f"Performance is within neutral parameters (Clicks: {clicks}, Conv: {conv:.0f}, CVR: {cvr:.1f}%). Continue observation."
            missing_info = "Insufficient divergence from baseline campaign performance."
            financial_impact = "Maintain standard automated bidding monitoring."

        # Flag terms for human review if confidence is low or conflicting
        if confidence < 65.0 or (action == "PROMOTE" and confidence < 78.0):
            needs_review = 1

        results.append({
            "action": action,
            "confidence": round(confidence, 1),
            "reason": reason,
            "missing_info": missing_info,
            "financial_impact": financial_impact,
            "needs_review": needs_review
        })

    results_df = pd.DataFrame(results)
    for col in results_df.columns:
        df[col] = results_df[col]

    return df

def generate_negative_keyword_suggestions(block_df: pd.DataFrame, all_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate negative keyword suggestions with collision checking.
    Verifies that proposed negative phrase doesn't unintentionally block converting queries!
    """
    suggestions = []
    
    # Pre-calculate converting words across all search terms to prevent collision
    converting_terms = all_df[all_df['conversions'] > 0]['query'].str.lower().tolist()
    converting_words = set()
    for t in converting_terms:
        converting_words.update(re.findall(r'\b[a-z0-9\-]+\b', t))

    for _, row in block_df.iterrows():
        query = str(row['query']).strip()
        q_lower = query.lower()
        reason = str(row['reason'])
        cost = float(row['cost'])
        campaign = str(row['campaign'])
        ad_group = str(row['ad_group'])
        term_id = int(row['id']) if 'id' in row else None

        # Check for specific isolated negative tokens (e.g., 'jobs', 'free', 'login')
        words = re.findall(r'\b[a-z0-9\-]+\b', q_lower)
        neg_token_match = None
        for category, kws in NEGATIVE_INTENTS.items():
            for kw in kws:
                if kw in words or ((" " in kw) and kw in q_lower):
                    # Check if this token collides with converting terms
                    if kw not in converting_words:
                        neg_token_match = kw
                        break
            if neg_token_match:
                break

        if neg_token_match and len(neg_token_match.split()) <= 2:
            suggested_kw = f'"{neg_token_match}"'
            match_type = 'Phrase'
            scope = 'Campaign'
            rec_reason = f"Blocks unwanted sub-phrase '{neg_token_match}' across campaign. Collision check verified zero overlap with converting queries."
        else:
            suggested_kw = f'[{query}]'
            match_type = 'Exact'
            scope = 'Ad Group' if len(ad_group) > 0 else 'Campaign'
            rec_reason = f"Precise exact match negative prevents this query without risking broad phrase over-blocking."

        suggestions.append({
            "term_id": term_id,
            "keyword": suggested_kw,
            "match_type": match_type,
            "scope": scope,
            "campaign": campaign,
            "ad_group": ad_group,
            "reason": rec_reason,
            "estimated_waste": round(cost, 2),
            "status": "PENDING"
        })

    return suggestions
