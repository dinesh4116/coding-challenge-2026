import math

def calculate_confidence_score(record, intent_info, rules_triggered):
    """
    Computes an explainable, heuristic confidence indicator (0 to 100).
    Explicitly labeled as a confidence indicator based on:
      1. Data completeness (presence of required metrics)
      2. Sample size sufficiency (Wilson score / click volume)
      3. Signal consistency / agreement (CTR, CVR, CPA, intent alignment)
      4. Intent clarity (distinct commercial vs negative vs ambiguous terms)
    """
    clicks = record.get('clicks')
    impressions = record.get('impressions')
    cost = record.get('cost')
    conversions = record.get('conversions')
    conversion_value = record.get('conversion_value')

    uncertainty_factors = []
    missing_data = []

    # 1. Data Completeness (0 to 100)
    completeness_score = 100.0
    if impressions is None:
        completeness_score -= 20
        missing_data.append("Missing impressions metric")
    if clicks is None:
        completeness_score -= 25
        missing_data.append("Missing clicks metric")
    if cost is None:
        completeness_score -= 25
        missing_data.append("Missing cost metric")
    if conversions is None:
        completeness_score -= 20
        missing_data.append("Missing conversion metric")
    if conversion_value is None:
        completeness_score -= 10
        missing_data.append("Missing conversion value metric")
    
    completeness_score = max(0.0, completeness_score)

    # 2. Sample Size Sufficiency (0 to 100)
    sample_score = 0.0
    safe_clicks = clicks if (clicks is not None and not math.isnan(clicks)) else 0
    safe_impr = impressions if (impressions is not None and not math.isnan(impressions)) else 0

    if safe_clicks >= 50:
        sample_score = 100.0
    elif safe_clicks >= 25:
        sample_score = 85.0
    elif safe_clicks >= 10:
        sample_score = 65.0
    elif safe_clicks >= 5:
        sample_score = 45.0
        uncertainty_factors.append(f"Low click volume ({safe_clicks} clicks) limits statistical significance")
    elif safe_clicks >= 1:
        sample_score = 25.0
        uncertainty_factors.append(f"Very sparse click sample ({safe_clicks} clicks); high statistical uncertainty")
    else:
        sample_score = 10.0
        uncertainty_factors.append("Zero clicks observed; sample volume is insufficient")

    # Critical uncertainty check: Few clicks with 1 conversion
    safe_conv = conversions if (conversions is not None and not math.isnan(conversions)) else 0
    is_small_sample_anomaly = False
    if safe_clicks <= 5 and safe_conv >= 1:
        # Heavily penalize sample score to reflect high statistical uncertainty
        sample_score = 15.0
        is_small_sample_anomaly = True
        uncertainty_factors.append(f"Small sample anomaly: {safe_conv} conversion from only {safe_clicks} clicks has wide error margin")

    # 3. Intent Clarity (0 to 100)
    intent_score = 50.0
    intent_type = intent_info.get('intent_type', 'neutral')
    matched_tokens = intent_info.get('matched_tokens', [])

    if intent_type in ['negative_irrelevant', 'high_commercial']:
        if len(matched_tokens) >= 2:
            intent_score = 95.0
        else:
            intent_score = 80.0
    elif intent_type == 'informational':
        intent_score = 70.0
    elif intent_type == 'ambiguous':
        intent_score = 35.0
        uncertainty_factors.append("Broad or ambiguous query intent without specific product qualifier")
    else: # neutral
        intent_score = 55.0

    # 4. Signal Agreement / Consistency (0 to 100)
    agreement_score = 75.0
    safe_cost = cost if (cost is not None and not math.isnan(cost)) else 0

    # Conflicting signals check
    if safe_clicks >= 20 and safe_conv == 0 and intent_type == 'high_commercial':
        agreement_score = 50.0
        uncertainty_factors.append(f"Conflicting signals: High commercial intent but zero conversions after {safe_clicks} clicks and ${safe_cost:.2f} spend")
    elif safe_clicks >= 25 and safe_conv >= 3 and intent_type == 'negative_irrelevant':
        agreement_score = 40.0
        uncertainty_factors.append("Unusual discrepancy: High conversion count despite negative intent keyword match")

    # Weighted Overall Confidence
    confidence_raw = (
        (completeness_score * 0.25) +
        (sample_score * 0.35) +
        (intent_score * 0.25) +
        (agreement_score * 0.15)
    )

    if is_small_sample_anomaly:
        confidence_raw = min(confidence_raw, 45.0)

    confidence_score = round(max(5.0, min(98.0, confidence_raw)), 1)

    if confidence_score >= 75.0:
        confidence_label = "High"
    elif confidence_score >= 50.0:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"

    return {
        'score': confidence_score,
        'label': confidence_label,
        'breakdown': {
            'completeness_score': round(completeness_score, 1),
            'sample_score': round(sample_score, 1),
            'intent_score': round(intent_score, 1),
            'agreement_score': round(agreement_score, 1)
        },
        'uncertainty_factors': uncertainty_factors,
        'missing_data': missing_data
    }
