def analyze_spend_intelligence(records, simulation_params=None):
    """
    Computes rigorous spend intelligence without exaggerating claims or double counting.
    Distinguishes:
      - Historical actual cost
      - Spend flagged for investigation
      - Potentially avoidable spend under explicit stated assumptions
    """
    if not records:
        return {
            'total_spend': 0.0,
            'blocked_spend': 0.0,
            'review_spend': 0.0,
            'promote_spend': 0.0,
            'ignore_spend': 0.0,
            'estimated_avoidable_spend': 0.0,
            'campaign_summaries': [],
            'assumptions': [],
            'high_cost_investigations': []
        }

    # Simulation parameters default
    sim = {
        'negative_spend_cutoff': 30.0,  # hypothetical spend before negative keyword is introduced
        'negative_adoption_rate': 0.90, # 90% of recommended negatives implemented
        'target_cpa_threshold': 120.0
    }
    if simulation_params:
        sim.update(simulation_params)

    total_spend = 0.0
    blocked_spend = 0.0
    review_spend = 0.0
    promote_spend = 0.0
    ignore_spend = 0.0
    avoidable_spend_calculated = 0.0

    campaign_data = {}
    high_cost_investigations = []

    for r in records:
        cost = float(r.get('cost') or 0.0)
        conv = float(r.get('conversions') or 0.0)
        rec = r.get('recommendation', 'IGNORE')
        camp = r.get('campaign', 'General Campaign')
        
        total_spend += cost

        # Accumulate by recommendation
        if rec == 'BLOCK':
            blocked_spend += cost
            # Calculation of potentially avoidable spend:
            # If negative was introduced after spending cutoff, excess is avoidable
            excess = max(0.0, cost - sim['negative_spend_cutoff'])
            avoidable_spend_calculated += (excess * sim['negative_adoption_rate'])

        elif rec == 'HUMAN REVIEW':
            review_spend += cost
            # Flag high cost items for immediate attention
            if cost >= 100.0 or (cost >= 50.0 and conv == 0):
                high_cost_investigations.append({
                    'row_id': r.get('row_id'),
                    'search_term': r.get('search_term'),
                    'campaign': camp,
                    'cost': round(cost, 2),
                    'conversions': round(conv, 1),
                    'clicks': r.get('clicks'),
                    'reason': r.get('explanation')
                })

        elif rec == 'PROMOTE':
            promote_spend += cost
        else:
            ignore_spend += cost

        # Campaign aggregates
        if camp not in campaign_data:
            campaign_data[camp] = {
                'campaign': camp,
                'total_spend': 0.0,
                'blocked_spend': 0.0,
                'review_spend': 0.0,
                'promote_spend': 0.0,
                'conversions': 0.0,
                'conversion_value': 0.0,
                'query_count': 0
            }
        
        c_entry = campaign_data[camp]
        c_entry['total_spend'] += cost
        c_entry['query_count'] += 1
        c_entry['conversions'] += conv
        c_entry['conversion_value'] += float(r.get('conversion_value') or 0.0)
        
        if rec == 'BLOCK':
            c_entry['blocked_spend'] += cost
        elif rec == 'HUMAN REVIEW':
            c_entry['review_spend'] += cost
        elif rec == 'PROMOTE':
            c_entry['promote_spend'] += cost

    # Sort high cost investigations by cost descending
    high_cost_investigations.sort(key=lambda x: x['cost'], reverse=True)

    # Format campaign summaries
    campaign_summaries = []
    for c_name, c_dict in campaign_data.items():
        c_spend = c_dict['total_spend']
        c_conv = c_dict['conversions']
        c_val = c_dict['conversion_value']
        
        cpa = round(c_spend / c_conv, 2) if c_conv > 0 else None
        roas = round(c_val / c_spend, 2) if c_spend > 0 else None
        
        campaign_summaries.append({
            'campaign': c_name,
            'total_spend': round(c_spend, 2),
            'blocked_spend': round(c_dict['blocked_spend'], 2),
            'review_spend': round(c_dict['review_spend'], 2),
            'promote_spend': round(c_dict['promote_spend'], 2),
            'conversions': round(c_conv, 1),
            'conversion_value': round(c_val, 2),
            'cpa': cpa,
            'roas': roas,
            'query_count': c_dict['query_count'],
            'potential_savings_rate': round((c_dict['blocked_spend'] / c_spend * 100), 1) if c_spend > 0 else 0.0
        })

    campaign_summaries.sort(key=lambda x: x['total_spend'], reverse=True)

    assumptions = [
        f"Avoidable spend is modeled assuming negative keywords are implemented once a search query reaches ${sim['negative_spend_cutoff']:.2f} in spend.",
        f"Assumes an analyst negative keyword adoption rate of {sim['negative_adoption_rate']*100:.0f}%.",
        "Spend on zero-conversion terms with high commercial intent is classified under 'Human Review' (at-risk), NOT automatically categorized as wasted spend.",
        "Verified savings can only be confirmed retrospectively after negative keywords have been actively serving in the Google Ads account."
    ]

    return {
        'total_spend': round(total_spend, 2),
        'blocked_spend': round(blocked_spend, 2),
        'review_spend': round(review_spend, 2),
        'promote_spend': round(promote_spend, 2),
        'ignore_spend': round(ignore_spend, 2),
        'estimated_avoidable_spend': round(avoidable_spend_calculated, 2),
        'avoidable_spend_percentage': round((avoidable_spend_calculated / total_spend * 100), 1) if total_spend > 0 else 0.0,
        'blocked_spend_percentage': round((blocked_spend / total_spend * 100), 1) if total_spend > 0 else 0.0,
        'review_spend_percentage': round((review_spend / total_spend * 100), 1) if total_spend > 0 else 0.0,
        'assumptions': assumptions,
        'campaign_summaries': campaign_summaries,
        'high_cost_investigations': high_cost_investigations[:15],
        'simulation_params': sim
    }
