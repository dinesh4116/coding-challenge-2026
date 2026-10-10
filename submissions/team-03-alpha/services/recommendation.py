ADVICE = {
    ("spend", "up"): ("Spend is far above this campaign's normal level for this weekday.",
        "Check for bid/budget edits, CPC spikes, new audiences or broad-match leakage; pause or cap bids if the extra spend isn't converting."),
    ("clicks", "down"): ("Clicks dropped sharply versus the campaign's usual volume.",
        "Check ad disapprovals, delivery status, bid or budget limits, and recent targeting or schedule changes."),
    ("ctr", "down"): ("CTR is well below baseline, so ads are being shown but not clicked.",
        "Review creative fatigue, new placements or keywords, competitor activity and ad-position changes."),
    ("conversions", "down"): ("Conversions fell sharply while traffic looks relatively normal.",
        "Check the landing page, checkout flow, offer or stock changes, then verify conversion tracking."),
    ("revenue", "down"): ("Revenue fell sharply versus the campaign's usual level.",
        "Check average order value, product availability/pricing, promo changes and revenue-value tracking before blaming traffic."),
    ("conversions", "tracking"): ("Clicks are normal but conversions dropped to zero - likely a tracking failure.",
        "Test the conversion tag/pixel and server events, check recent site or tag-manager releases, and confirm attribution settings."),
    ("spend", "budget"): ("The daily budget was exhausted, which is unusual for this campaign.",
        "Check whether spend ran ahead of pace; raise the budget if performance is strong or tighten bids and schedule."),
}

def advise(metric, kind):
    return ADVICE.get((metric, kind), ("Unusual deviation from baseline.", "Review recent campaign changes."))
