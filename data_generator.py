import random
import csv
import os

def generate_synthetic_dataset(output_path="data/sample_search_terms_25000.csv", num_rows=25000, seed=42):
    """
    Generates a reproducible 25,000-row synthetic Google Ads Search Terms dataset.
    Uses pure Python standard library to ensure 100% compliance with Windows AppLocker / security environments.
    """
    random.seed(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    campaign_configs = {
        "Laptop Sales": {
            "ad_groups": ["Gaming Laptops", "Business Laptops", "Budget Laptops", "Refurbished Laptops"],
            "relevant_templates": [
                "buy {brand} laptop online", "best {brand} laptop price", "discount {brand} gaming laptop",
                "cheap {brand} i7 laptop deal", "order high performance laptop", "{brand} laptop store near me",
                "lightweight ultrabook buy", "touchscreen laptop deals"
            ],
            "irrelevant_templates": [
                "how to repair laptop screen", "free laptop wallpaper 4k", "laptop battery teardown video",
                "download laptop driver free", "laptop keyboard key stuck fix", "laptop wikipedia history",
                "diy laptop desk wood", "used laptop price comparison reddit"
            ],
            "ambiguous_templates": [
                "{brand} laptop vs desktop", "laptop specs comparison", "best laptop brand 2026",
                "is {brand} laptop good", "laptop heating problem solutions", "upcoming laptop release date"
            ],
            "brands": ["Dell", "HP", "Lenovo", "Asus", "Acer", "Apple", "MSI"]
        },
        "Laptop Accessories": {
            "ad_groups": ["Laptop Bags", "Docking Stations", "Chargers & Adapters", "Cooling Pads"],
            "relevant_templates": [
                "buy {accessory} online", "best {accessory} for laptop", "{accessory} price deal",
                "heavy duty {accessory}", "fast shipping laptop {accessory}", "universal {accessory} adapter"
            ],
            "irrelevant_templates": [
                "how to sew laptop bag at home", "diy cooling pad cardboard", "free charger schematic",
                "what is a docking station defined", "docking station driver linux", "vintage laptop bag"
            ],
            "ambiguous_templates": [
                "top 10 laptop accessories", "do I need a cooling pad", "type c hub vs docking station",
                "best sleeve for 15 inch laptop review"
            ],
            "accessories": ["leather sleeve", "65w USB-C charger", "dual monitor dock", "rgb cooling pad", "privacy screen filter"]
        },
        "Laptop Repair": {
            "ad_groups": ["Screen Replacement", "Battery Repair", "Virus Removal", "Hardware Diagnostics"],
            "relevant_templates": [
                "laptop screen repair service near me", "same day battery replacement service",
                "urgent virus removal shop", "fix broken laptop hinge cost", "local laptop repair technician"
            ],
            "irrelevant_templates": [
                "laptop repair course free pdf", "how to replace screen yourself step by step",
                "laptop repair manual download", "laptop technician salary 2026", "laptop schematic diagram"
            ],
            "ambiguous_templates": [
                "laptop repair cost guide", "is screen replacement worth it", "laptop repair kit price",
                "symptoms of bad laptop motherboard"
            ],
            "accessories": []
        },
        "Online Learning Courses": {
            "ad_groups": ["Python Bootcamp", "Data Science Cert", "Web Development", "AI Engineering"],
            "relevant_templates": [
                "enroll in {topic} course", "best paid {topic} certification", "online {topic} bootcamp price",
                "learn {topic} online course with certificate", "top rated {topic} training program"
            ],
            "irrelevant_templates": [
                "free {topic} tutorial youtube", "download {topic} torrent book", "what is {topic} definition",
                "{topic} jobs salary entry level", "{topic} open source github repo", "free python cheatsheet pdf"
            ],
            "ambiguous_templates": [
                "{topic} vs web dev which is better", "is {topic} hard to learn", "{topic} roadmap 2026",
                "best books for learning {topic}"
            ],
            "topics": ["Python coding", "Data Science", "Full Stack Web Dev", "Machine Learning", "Cloud Architecture"]
        },
        "Fitness Equipment": {
            "ad_groups": ["Treadmills", "Adjustable Dumbbells", "Exercise Bikes", "Home Gym Sets"],
            "relevant_templates": [
                "buy heavy duty treadmill online", "adjustable dumbbells set best price", "order exercise bike home delivery",
                "commercial grade home gym equipment", "folding treadmill sale free shipping"
            ],
            "irrelevant_templates": [
                "diy wood dumbbells at home", "free treadmill workout plan pdf", "treadmill motor troubleshooting",
                "history of exercise bike", "used gym equipment free craigslist", "treadmill error code fix"
            ],
            "ambiguous_templates": [
                "treadmill vs exercise bike calories burned", "are adjustable dumbbells safe",
                "best home gym setup under 500", "treadmill maintenance tips"
            ],
            "accessories": []
        }
    }

    match_types = ["Exact", "Phrase", "Broad"]
    records = []
    rows_per_campaign = num_rows // len(campaign_configs)

    for campaign_name, config in campaign_configs.items():
        for _ in range(rows_per_campaign):
            ad_group = random.choice(config["ad_groups"])
            match_type = random.choices(match_types, weights=[0.25, 0.45, 0.30])[0]
            intent = random.choices(["RELEVANT", "IRRELEVANT", "AMBIGUOUS"], weights=[0.45, 0.35, 0.20])[0]
            
            if intent == "RELEVANT":
                tmpl = random.choice(config["relevant_templates"])
            elif intent == "IRRELEVANT":
                tmpl = random.choice(config["irrelevant_templates"])
            else:
                tmpl = random.choice(config["ambiguous_templates"])

            query = tmpl
            if "{brand}" in query:
                query = query.replace("{brand}", random.choice(config.get("brands", ["Generic"])))
            if "{accessory}" in query:
                query = query.replace("{accessory}", random.choice(config.get("accessories", ["accessory"])))
            if "{topic}" in query:
                query = query.replace("{topic}", random.choice(config.get("topics", ["coding"])))

            if intent == "RELEVANT":
                impressions = int(random.expovariate(1/500) + 10)
                ctr = random.uniform(0.02, 0.12)
                clicks = max(0, int(impressions * ctr))
                cpc = random.uniform(1.2, 5.5)
                cost = round(clicks * cpc, 2)
                cvr = random.uniform(0.05, 0.25)
                conversions = int(random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.2, 0.1])[0]) if clicks > 0 else 0
                avg_value = random.uniform(40, 250)
                conversion_value = round(conversions * avg_value, 2)
                synth_gt = "PROMOTE"
            elif intent == "IRRELEVANT":
                impressions = int(random.expovariate(1/300) + 5)
                ctr = random.uniform(0.005, 0.04)
                clicks = max(0, int(impressions * ctr))
                cpc = random.uniform(0.5, 3.0)
                cost = round(clicks * cpc, 2)
                conversions = 1 if (clicks > 30 and random.random() < 0.02) else 0
                conversion_value = round(conversions * random.uniform(10, 50), 2)
                synth_gt = "BLOCK"
            else:
                impressions = int(random.expovariate(1/200) + 5)
                ctr = random.uniform(0.01, 0.05)
                clicks = max(0, int(impressions * ctr))
                cpc = random.uniform(0.8, 4.0)
                cost = round(clicks * cpc, 2)
                conversions = 1 if (clicks > 20 and random.random() < 0.1) else 0
                conversion_value = round(conversions * random.uniform(20, 100), 2)
                synth_gt = "HUMAN REVIEW"

            records.append({
                "query_text": query,
                "match_type": match_type,
                "campaign": campaign_name,
                "ad_group": ad_group,
                "impressions": impressions,
                "clicks": clicks,
                "cost": cost,
                "conversions": conversions,
                "conversion_value": conversion_value,
                "_synthetic_ground_truth": synth_gt
            })

    headers = ["query_text", "match_type", "campaign", "ad_group", "impressions", "clicks", "cost", "conversions", "conversion_value", "_synthetic_ground_truth"]
    
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records[:num_rows])

    print(f"Generated synthetic dataset with {len(records[:num_rows])} rows at '{output_path}'.")
    return output_path

if __name__ == "__main__":
    generate_synthetic_dataset()

