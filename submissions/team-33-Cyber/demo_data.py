import random
import os
import pandas as pd
import numpy as np
from typing import List, Dict

CAMPAIGN_TEMPLATES = [
    {
        "campaign": "Performance Footwear - Search - US",
        "ad_groups": ["Marathon Running Shoes", "Trail Running Gear", "Lightweight Racers", "Orthopedic Sneakers"],
        "match_types": ["Broad", "Phrase", "Exact"],
        "commercial_queries": [
            ("buy lightweight marathon shoes online", 450, 42, 68.50, 6, 420.00),
            ("best marathon racing shoes carbon plate", 780, 65, 112.40, 9, 680.00),
            ("trail running shoes waterproof vibram", 320, 28, 48.20, 4, 310.00),
            ("cushioned running shoes for flat feet", 510, 45, 76.50, 5, 390.00),
            ("wide toe box running shoe purchase", 290, 24, 42.00, 3, 225.00),
            ("men long distance running sneakers sale", 610, 52, 88.40, 7, 540.00),
            ("women trail marathon shoes discount code", 380, 31, 52.70, 4, 300.00)
        ],
        "single_conv_trap": [
            ("what shoe to wear for 5k race", 45, 1, 1.85, 1, 85.00),
            ("green running shoelaces amazon", 25, 1, 1.20, 1, 95.00),
            ("celebrity marathon finish line footwear", 80, 2, 3.40, 1, 110.00),
            ("running sneakers in rain reddit", 60, 2, 2.90, 1, 90.00),
            ("marathon shoe weight comparison 2026", 95, 3, 4.80, 1, 120.00)
        ],
        "bleeders_zero_conv": [
            ("how to stretch running shoes wider", 1200, 48, 86.40, 0, 0.00),
            ("marathon running tips for beginner runners", 2100, 75, 135.00, 0, 0.00),
            ("history of marathon footwear technology", 650, 28, 50.40, 0, 0.00),
            ("shoe repair sole replacement nearby", 890, 36, 64.80, 0, 0.00)
        ],
        "irrelevant_negative": [
            ("nike running shoe factory jobs hiring", 420, 18, 27.00, 0, 0.00),
            ("footwear product manager salary glassdoor", 310, 12, 19.20, 0, 0.00),
            ("running shoes 3d model free download blender", 680, 29, 43.50, 0, 0.00),
            ("marathon footwear customer service toll free number", 240, 14, 21.00, 0, 0.00),
            ("fake counterfeit carbon plate running shoes", 510, 22, 33.00, 0, 0.00)
        ],
        "insufficient_volume": [
            ("ultra marathon footwear zero drop test", 18, 1, 1.60, 0, 0.00),
            ("lightweight racing flats neon pink size 11", 12, 0, 0.00, 0, 0.00),
            ("carbon shoe energy return percentage chart", 24, 2, 3.10, 0, 0.00),
            ("road to trail hybrid sneaker reviews", 15, 1, 1.40, 0, 0.00)
        ]
    },
    {
        "campaign": "Cloud ERP Software - B2B Solutions",
        "ad_groups": ["Manufacturing ERP", "Wholesale Distribution ERP", "Cloud Accounting Platform", "Supply Chain Suite"],
        "match_types": ["Phrase", "Exact", "Broad"],
        "commercial_queries": [
            ("enterprise cloud erp software pricing demo", 620, 38, 285.00, 4, 1800.00),
            ("best manufacturing erp system implementation", 840, 52, 416.00, 5, 2500.00),
            ("supply chain inventory management platform quote", 490, 31, 232.50, 3, 1350.00),
            ("b2b cloud accounting software mid market", 570, 36, 270.00, 4, 1900.00),
            ("compare sap oracle alternative erp vendor", 710, 44, 352.00, 5, 2200.00)
        ],
        "single_conv_trap": [
            ("what is erp software architecture pdf", 35, 1, 7.50, 1, 450.00),
            ("sample erp invoice template excel", 42, 2, 14.00, 1, 400.00),
            ("erp vendor market share statista", 28, 1, 8.00, 1, 500.00)
        ],
        "bleeders_zero_conv": [
            ("erp implementation failures case studies", 1450, 42, 315.00, 0, 0.00),
            ("how to build custom python erp system", 980, 34, 255.00, 0, 0.00),
            ("enterprise software consultant hourly rate", 820, 29, 217.50, 0, 0.00)
        ],
        "irrelevant_negative": [
            ("erp technical support login portal sign in", 890, 38, 285.00, 0, 0.00),
            ("sap erp consultant jobs openings remote", 1120, 46, 345.00, 0, 0.00),
            ("enterprise erp activation keygen crack download", 760, 32, 240.00, 0, 0.00),
            ("erp software salary expectations glassdoor", 540, 24, 180.00, 0, 0.00),
            ("erp software meaning in hindi slideshare", 410, 18, 135.00, 0, 0.00)
        ],
        "insufficient_volume": [
            ("supply chain erp compliance iso 9001", 14, 1, 7.50, 0, 0.00),
            ("cloud erp multi currency consolidation api", 22, 2, 15.00, 0, 0.00),
            ("manufacturing bom routing erp submodule", 19, 0, 0.00, 0, 0.00)
        ]
    },
    {
        "campaign": "Smart Home IoT Security - Direct To Consumer",
        "ad_groups": ["Video Doorbells", "Smart Deadbolts", "Outdoor Floodlight Cams", "Indoor Security Hub"],
        "match_types": ["Broad", "Phrase", "Exact"],
        "commercial_queries": [
            ("buy 4k wireless video doorbell camera", 910, 68, 102.00, 8, 720.00),
            ("smart deadbolt lock with fingerprint keyless shop", 740, 54, 86.40, 7, 630.00),
            ("best outdoor floodlight security camera no subscription", 830, 61, 97.60, 6, 540.00),
            ("home automation security bundle discount package", 650, 48, 76.80, 5, 480.00)
        ],
        "single_conv_trap": [
            ("doorbell chime transformer voltage 16v", 65, 1, 1.50, 1, 90.00),
            ("battery powered security camera reset button", 50, 2, 3.20, 1, 80.00)
        ],
        "bleeders_zero_conv": [
            ("how to bypass smart lock without key", 1850, 58, 92.80, 0, 0.00),
            ("ring camera blue light flashing meaning", 2200, 72, 115.20, 0, 0.00),
            ("diy home security camera wiring diagram", 1400, 44, 70.40, 0, 0.00)
        ],
        "irrelevant_negative": [
            ("smart security camera technician jobs salary", 450, 19, 30.40, 0, 0.00),
            ("smart home security app customer service phone number", 680, 28, 44.80, 0, 0.00),
            ("free cloud storage security cam apk download", 790, 34, 54.40, 0, 0.00),
            ("smart lock user manual pdf download free", 520, 23, 36.80, 0, 0.00)
        ],
        "insufficient_volume": [
            ("zigbee vs z wave security hub sensor", 28, 2, 3.20, 0, 0.00),
            ("ip camera rtsp stream home assistant", 19, 1, 1.60, 0, 0.00)
        ]
    }
]

def generate_realistic_dataset(n_target_rows: int = 500) -> pd.DataFrame:
    """Generate authentic, high-fidelity Google Ads search terms dataset."""
    random.seed(42)
    rows = []

    for campaign_info in CAMPAIGN_TEMPLATES:
        camp_name = campaign_info["campaign"]
        ad_groups = campaign_info["ad_groups"]
        match_types = campaign_info["match_types"]

        # 1. Commercial Top Performers (Promote candidates)
        for q_tuple in campaign_info["commercial_queries"]:
            q, impr, clicks, cost, conv, val = q_tuple
            rows.append({
                "Search term": q,
                "Campaign": camp_name,
                "Ad group": random.choice(ad_groups),
                "Match type": random.choice(match_types),
                "Impressions": impr,
                "Clicks": clicks,
                "Cost": round(cost, 2),
                "Conversions": conv,
                "Conversion value": round(val, 2)
            })

        # 2. Single-Conversion Trap (High volatility edge case)
        for q_tuple in campaign_info["single_conv_trap"]:
            q, impr, clicks, cost, conv, val = q_tuple
            rows.append({
                "Search term": q,
                "Campaign": camp_name,
                "Ad group": random.choice(ad_groups),
                "Match type": random.choice(match_types),
                "Impressions": impr,
                "Clicks": clicks,
                "Cost": round(cost, 2),
                "Conversions": conv,
                "Conversion value": round(val, 2)
            })

        # 3. High-Spend Bleeders (Zero conversions, budget waste)
        for q_tuple in campaign_info["bleeders_zero_conv"]:
            q, impr, clicks, cost, conv, val = q_tuple
            rows.append({
                "Search term": q,
                "Campaign": camp_name,
                "Ad group": random.choice(ad_groups),
                "Match type": random.choice(match_types),
                "Impressions": impr,
                "Clicks": clicks,
                "Cost": round(cost, 2),
                "Conversions": conv,
                "Conversion value": round(val, 2)
            })

        # 4. Clear Irrelevant Negatives (Block candidates: jobs, free, login, cracks)
        for q_tuple in campaign_info["irrelevant_negative"]:
            q, impr, clicks, cost, conv, val = q_tuple
            rows.append({
                "Search term": q,
                "Campaign": camp_name,
                "Ad group": random.choice(ad_groups),
                "Match type": random.choice(match_types),
                "Impressions": impr,
                "Clicks": clicks,
                "Cost": round(cost, 2),
                "Conversions": conv,
                "Conversion value": round(val, 2)
            })

        # 5. Low-volume / insufficient evidence queries
        for q_tuple in campaign_info["insufficient_volume"]:
            q, impr, clicks, cost, conv, val = q_tuple
            rows.append({
                "Search term": q,
                "Campaign": camp_name,
                "Ad group": random.choice(ad_groups),
                "Match type": random.choice(match_types),
                "Impressions": impr,
                "Clicks": clicks,
                "Cost": round(cost, 2),
                "Conversions": conv,
                "Conversion value": round(val, 2)
            })

    # Expand systematically to reach requested size with authentic long-tail variations
    base_rows = list(rows)
    multiplier_variations = [
        "best", "top rated", "discount", "online store", "review 2026",
        "cheap", "official", "near me", "coupon", "guide"
    ]
    
    current_count = len(rows)
    while current_count < n_target_rows:
        sample = random.choice(base_rows)
        modifier = random.choice(multiplier_variations)
        new_q = f"{sample['Search term']} {modifier}".strip()
        
        # Scale volume with realistic variance
        var_factor = random.uniform(0.3, 1.8)
        new_impr = max(5, int(sample['Impressions'] * var_factor))
        new_clicks = max(0, int(sample['Clicks'] * var_factor))
        new_cost = round(sample['Cost'] * var_factor, 2)
        new_conv = max(0, int(sample['Conversions'] * var_factor)) if sample['Conversions'] > 0 else 0
        new_val = round(sample['Conversion value'] * var_factor, 2) if new_conv > 0 else 0.0

        rows.append({
            "Search term": new_q,
            "Campaign": sample["Campaign"],
            "Ad group": sample["Ad group"],
            "Match type": sample["Match type"],
            "Impressions": new_impr,
            "Clicks": new_clicks,
            "Cost": new_cost,
            "Conversions": new_conv,
            "Conversion value": new_val
        })
        current_count += 1

    df = pd.DataFrame(rows[:n_target_rows])
    return df

def generate_stress_test_dataset(n_rows: int = 25000) -> pd.DataFrame:
    """Generate 25,000 row Google Ads dataset to verify high performance and stability."""
    return generate_realistic_dataset(n_target_rows=n_rows)

def save_sample_csv(target_path: str):
    """Save sample CSV file for users to download and inspect."""
    df = generate_realistic_dataset(n_target_rows=150)
    df.to_csv(target_path, index=False)
    print(f"Sample CSV saved to {target_path} ({len(df)} rows)")

if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_google_ads_search_terms.csv")
    save_sample_csv(test_path)
