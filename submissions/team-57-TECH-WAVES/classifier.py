import re
import math
from .confidence import calculate_confidence_score
from .db import get_all_feedback

# Known negative intent token groups
NEGATIVE_INTENT_PATTERNS = {
    'piracy_free': [r'\bfree\b', r'\bcracked?\b', r'\btorrent\b', r'\bkeygen\b', r'\bwarez\b', r'\bnulled\b', r'\bpirate\b'],
    'employment': [r'\bjobs?\b', r'\bcareers?\b', r'\bsalary\b', r'\bsalaries\b', r'\bhiring\b', r'\binternships?\b', r'\bresume\b', r'\bglassdoor\b', r'\bindeed\b'],
    'academic_diy': [r'\btutorials?\b', r'\bdiy\b', r'\bhow to make\b', r'\bhow to build\b', r'\bsyllabus\b', r'\bhomework\b', r'\bpdf\b', r'\bslideshare\b', r'\bcourse free\b', r'\blecture\b', r'\btemplates?\b'],
    'support_login': [r'\blogin\b', r'\blog in\b', r'\bsignin\b', r'\bportal\b', r'\bcustomer care\b', r'\btoll free\b', r'\bsupport phone\b'],
    'consumer_unrelated': [r'\bpersonal loans?\b', r'\bpersonal debt\b', r'\bcar loans?\b', r'\bauto loans?\b', r'\bmortgages?\b', r'\bstudent loans?\b'],
    'free_grants': [r'\bfree money\b', r'\bgrants?\b', r'\bgovernment grants?\b']
}

COMMERCIAL_INTENT_PATTERNS = [
    r'\bpricing\b', r'\bbuy\b', r'\bpurchase\b', r'\bquote\b', r'\bcost of\b',
    r'\bvendor\b', r'\bplatform\b', r'\bsoftware\b', r'\bservices?\b',
    r'\bagency\b', r'\bcompany\b', r'\bsolutions?\b', r'\bdemo\b',
    r'\benterprise\b', r'\bb2b\b', r'\bprovider\b', r'\btool\b', r'\bsystem\b',
    r'\bbusiness loans?\b', r'\bcommercial loans?\b', r'\bline of credit\b',
    r'\bmerchant cash advance\b', r'\bworking capital\b', r'\bequipment finance\b',
    r'\bequipment loans?\b', r'\bsba loans?\b', r'\bstartup funding\b',
    r'\binvoice factoring\b', r'\brevenue based financing\b', r'\blenders?\b',
    r'\bapproval\b', r'\bapply\b', r'\bfinancing\b'
]

INFORMATIONAL_INTENT_PATTERNS = [
    r'\bvs\b', r'\bdifference between\b', r'\bmeaning\b', r'\bwhat is\b',
    r'\bexamples?\b', r'\breviews?\b', r'\bcalculator\b'
]

DEFAULT_CONFIG = {
    'min_clicks_for_promote': 15,
    'min_conv_for_promote': 2.0,      # strictly >= 2 conversions
    'max_cpa_for_promote': 150.0,
    'min_roas_for_promote': 1.5,
    'min_spend_for_block': 40.0,
    'high_spend_review_threshold': 250.0,
    'min_clicks_for_block': 12,
    'low_sample_click_cutoff': 5
}

def analyze_query_intent(query_text):
    """
    Analyzes search query intent and extracts matching tokens.
    Returns { 'intent_type': ..., 'matched_tokens': [...], 'matched_category': ... }
    """
    q = query_text.lower()
    
    # Check negative patterns
    for cat, patterns in NEGATIVE_INTENT_PATTERNS.items():
        matched = []
        for pat in patterns:
            if re.search(pat, q):
                matched.append(pat.replace(r'\b', '').replace('\\', ''))
        if matched:
            return {
                'intent_type': 'negative_irrelevant',
                'matched_tokens': matched,
                'matched_category': cat
            }

    # Check commercial patterns
    comm_matched = []
    for pat in COMMERCIAL_INTENT_PATTERNS:
        if re.search(pat, q):
            comm_matched.append(pat.replace(r'\b', '').replace('\\', ''))
    
    if len(comm_matched) >= 1:
        return {
            'intent_type': 'high_commercial',
            'matched_tokens': comm_matched,
            'matched_category': 'commercial'
        }

    # Check informational patterns
    info_matched = []
    for pat in INFORMATIONAL_INTENT_PATTERNS:
        if re.search(pat, q):
            info_matched.append(pat.replace(r'\b', '').replace('\\', ''))
    
    if info_matched:
        return {
            'intent_type': 'informational',
            'matched_tokens': info_matched,
            'matched_category': 'informational'
        }

    # Check ambiguity (queries with 1 or 2 generic words)
    words = q.split()
    if len(words) <= 2:
        return {
            'intent_type': 'ambiguous',
            'matched_tokens': words,
            'matched_category': 'ambiguous'
        }

    return {
        'intent_type': 'neutral',
        'matched_tokens': [],
        'matched_category': 'neutral'
    }

def get_feedback_lookup():
    """
    Retrieves stored reviewer overrides from SQLite to inform classification.
    """
    try:
        feedback_list = get_all_feedback()
        lookup = {}
        for item in feedback_list:
            key = f"{item['search_term'].strip().lower()}__{item.get('campaign', '').strip().lower()}"
            lookup[key] = item
        return lookup
    except Exception:
        return {}

def classify_search_term(record, config=None, feedback_lookup=None):
    """
    Applies modular, explainable decision logic to a single search term row.
    Returns full triage record with evidence, confidence, and recommended action.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    if feedback_lookup is None:
        feedback_lookup = get_feedback_lookup()

    search_term = record.get('search_term', '').strip()
    campaign = record.get('campaign', 'General Campaign')
    ad_group = record.get('ad_group', 'General Ad Group')
    
    clicks = record.get('clicks')
    impressions = record.get('impressions')
    cost = record.get('cost')
    conv = record.get('conversions')
    conv_val = record.get('conversion_value')
    ctr = record.get('ctr')
    cpa = record.get('cpa')
    roas = record.get('roas')

    positive_evidence = []
    negative_evidence = []
    rules_triggered = []

    # 1. Intent Analysis
    intent_info = analyze_query_intent(search_term)
    intent_type = intent_info['intent_type']
    matched_tokens = intent_info['matched_tokens']

    # 2. Check Reviewer Feedback History
    feedback_key = f"{search_term.lower()}__{campaign.lower()}"
    prior_feedback = feedback_lookup.get(feedback_key)

    # 3. Check Missing Critical Data
    critical_missing = []
    if clicks is None:
        critical_missing.append('clicks')
    if cost is None:
        critical_missing.append('cost')
    if conv is None:
        critical_missing.append('conversions')

    # Safe numeric values for conditions
    safe_clicks = clicks if (clicks is not None and not math.isnan(clicks)) else 0
    safe_cost = cost if (cost is not None and not math.isnan(cost)) else 0.0
    safe_conv = conv if (conv is not None and not math.isnan(conv)) else 0.0
    safe_conv_val = conv_val if (conv_val is not None and not math.isnan(conv_val)) else 0.0

    # Classify decision
    decision = "IGNORE"
    explanation = ""
    action = "Monitor performance and maintain current ad group settings."
    suggested_negative = search_term
    suggested_scope = "Campaign"
    suggested_match_type = "Exact"

    # RULE 0: Missing Critical Metrics -> HUMAN REVIEW
    if critical_missing:
        decision = "HUMAN REVIEW"
        rules_triggered.append("RULE_CRITICAL_METRIC_MISSING")
        negative_evidence.append(f"Missing essential performance metrics: {', '.join(critical_missing)}")
        explanation = f"Human review recommended: The dataset lacks essential metrics ({', '.join(critical_missing)}) to assess query viability."
        action = "Audit Google Ads tracking setup or upload a complete report containing cost and conversion data."

    # RULE 1: Reviewer feedback override
    elif prior_feedback:
        decision = prior_feedback['reviewer_decision']
        rules_triggered.append("RULE_REVIEWER_OVERRIDE_APPLIED")
        positive_evidence.append(f"Historical reviewer correction applied: changed to {decision} by analyst")
        explanation = f"Analyst override applied: Term was previously reviewed and marked as {decision}. Note: '{prior_feedback.get('reason', 'None provided')}'."
        action = f"Apply reviewer preference: {decision}."

    # RULE 2: Small sample size with conversion (CRITICAL SAFEGUARD: 2 clicks, 1 conversion)
    elif safe_clicks <= cfg['low_sample_click_cutoff'] and safe_conv >= 1:
        decision = "HUMAN REVIEW"
        rules_triggered.append("RULE_LOW_SAMPLE_CONVERSION_ANOMALY")
        positive_evidence.append(f"Recorded {safe_conv:.0f} conversion ({safe_conv/safe_clicks*100:.0f}% observed CVR)")
        negative_evidence.append(f"Insufficient sample size: Only {safe_clicks} clicks observed")
        explanation = f"Human review recommended: The query recorded {safe_conv:.0f} conversion from only {safe_clicks} clicks, which is insufficient evidence to reliably prove performance."
        action = "Keep in current ad group and allow click volume to reach statistical significance before promotion."

    # RULE 3: Irrelevant Intent with Spend or Clicks -> BLOCK
    elif intent_type == 'negative_irrelevant':
        rules_triggered.append("RULE_IRRELEVANT_INTENT_DETECTED")
        negative_evidence.append(f"Contains irrelevant search tokens: {', '.join(matched_tokens)} ({intent_info['matched_category']})")
        if safe_cost > 0:
            negative_evidence.append(f"Incurred ${safe_cost:.2f} historical spend with zero verified business return")

        # Determine negative match type and scope
        if intent_info['matched_category'] in ['piracy_free', 'employment']:
            suggested_negative = matched_tokens[0] if matched_tokens else search_term
            suggested_match_type = "Phrase"
            suggested_scope = "Campaign"
        else:
            suggested_negative = search_term
            suggested_match_type = "Exact"
            suggested_scope = "Campaign"

        decision = "BLOCK"
        explanation = f"Block recommended: Strong evidence of non-commercial/irrelevant intent ({', '.join(matched_tokens)}). Prevents budget leakage."
        action = f"Add '{suggested_negative}' as a {suggested_match_type} match negative keyword at {suggested_scope} level."

    # RULE 4: High Spend with Zero Conversions (SAFEGUARD: Check commercial intent vs irrelevance)
    elif safe_conv == 0 and safe_cost >= cfg['high_spend_review_threshold']:
        rules_triggered.append("RULE_HIGH_SPEND_ZERO_CONVERSIONS")
        negative_evidence.append(f"High accumulated spend (${safe_cost:.2f}) across {safe_clicks} clicks with 0 conversions")

        if intent_type == 'high_commercial':
            decision = "HUMAN REVIEW"
            positive_evidence.append(f"Query demonstrates commercial search intent ({', '.join(matched_tokens)})")
            explanation = f"Human review recommended: Query has high spend (${safe_cost:.2f}) with 0 conversions, but carries commercial intent. Investigate landing page, offer relevance, or conversion tracking delays."
            action = "Audit landing page bounce rate and conversion attribution delay before deciding to block."
        else:
            decision = "BLOCK"
            suggested_negative = search_term
            suggested_match_type = "Exact"
            suggested_scope = "Campaign"
            explanation = f"Block recommended: Incurred ${safe_cost:.2f} spend and {safe_clicks} clicks without converting. Query does not show clear high-commercial intent."
            action = f"Add '{search_term}' as an Exact match negative keyword to eliminate ongoing budget waste."

    # RULE 5: Strong Positive Performance -> PROMOTE
    elif (safe_clicks >= cfg['min_clicks_for_promote'] and 
          safe_conv >= cfg['min_conv_for_promote'] and 
          (cpa is None or cpa <= cfg['max_cpa_for_promote']) and
          (roas is None or roas >= cfg['min_roas_for_promote'] or safe_conv_val > safe_cost)):
        
        decision = "PROMOTE"
        rules_triggered.append("RULE_PROVEN_HIGH_PERFORMER")
        positive_evidence.append(f"Consistent conversion volume: {safe_conv:.0f} conversions from {safe_clicks} clicks")
        if cpa:
            positive_evidence.append(f"Profitable CPA of ${cpa:.2f} is within acceptable threshold (<= ${cfg['max_cpa_for_promote']:.2f})")
        if roas:
            positive_evidence.append(f"Strong ROAS of {roas:.2f}x")
        cpa_display = f"${cpa:.2f}" if cpa is not None else "N/A"
        explanation = f"Promote recommended: Term demonstrates verified commercial intent and efficient conversion economics ({safe_conv:.0f} conversions at {cpa_display} CPA)."
        action = f"Add '{search_term}' as an Exact/Phrase match keyword in ad group '{ad_group}' with dedicated ad copy and landing page."

    # RULE 6: Ambiguous Query or Conflicting Signals -> HUMAN REVIEW
    elif intent_type == 'ambiguous' and safe_cost >= 50.0:
        decision = "HUMAN REVIEW"
        rules_triggered.append("RULE_AMBIGUOUS_QUERY_INTENT")
        negative_evidence.append("Broad or ambiguous query text lacks specific qualifying product intent")
        explanation = f"Human review recommended: The search term '{search_term}' is broad/ambiguous with ${safe_cost:.2f} spend. Analyst judgment needed to determine campaign alignment."
        action = "Review search term context against ad group themes and search query reports."

    # RULE 7: Moderate Spend, Zero Conversions, Weak Clicks -> IGNORE (Let accumulate data)
    elif safe_conv == 0 and safe_cost < cfg['min_spend_for_block']:
        decision = "IGNORE"
        rules_triggered.append("RULE_LOW_SPEND_NOISE")
        positive_evidence.append(f"Low accumulated cost (${safe_cost:.2f}) is below intervention threshold")
        explanation = "Leave unchanged: Query represents normal low-volume exploratory search traffic. Incurred cost does not warrant negative keyword action."
        action = "No action required; allow natural accumulation of performance data."

    # Default fallback
    else:
        decision = "IGNORE"
        rules_triggered.append("RULE_DEFAULT_BASELINE")
        explanation = "Leave unchanged: Query metrics are currently within acceptable baseline parameters with no intervention trigger."
        action = "No immediate change needed."

    # Calculate Confidence & Uncertainty
    confidence = calculate_confidence_score(record, intent_info, rules_triggered)

    return {
        **record,
        'recommendation': decision,
        'confidence': confidence['score'],
        'confidence_label': confidence['label'],
        'confidence_details': confidence,
        'intent_type': intent_type,
        'intent_tokens': matched_tokens,
        'positive_evidence': positive_evidence,
        'negative_evidence': negative_evidence,
        'missing_data': confidence['missing_data'],
        'uncertainty_factors': confidence['uncertainty_factors'],
        'rules_triggered': rules_triggered,
        'explanation': explanation,
        'recommended_next_action': action,
        'suggested_negative': suggested_negative,
        'suggested_scope': suggested_scope,
        'suggested_match_type': suggested_match_type,
        'review_status': 'Under Review' if decision == 'HUMAN REVIEW' else 'Analyzed'
    }

def batch_classify_records(records, config=None):
    """
    Classifies a list of processed records efficiently.
    """
    feedback_lookup = get_feedback_lookup()
    results = []
    for r in records:
        results.append(classify_search_term(r, config=config, feedback_lookup=feedback_lookup))
    return results
