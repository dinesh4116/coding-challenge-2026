import random
import pandas as pd
import numpy as np

def generate_realistic_search_terms(n_rows: int = 25000, seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic 25,000-row Google Ads Search Terms Report mirroring real account distributions:
    - ~60% long tail (1-2 impressions, 0 clicks)
    - Trap rows (1-3 clicks, 1 conversion -> noise)
    - Spend bleeders ($60-$300 cost, 0 conversions)
    - Real performers (15+ clicks, 3+ conversions, profitable CPA)
    - Negative trigger terms ('free', 'login', 'jobs', 'crack')
    - Intent clusters (near-duplicate queries)
    """
    random.seed(seed)
    np.random.seed(seed)
    
    campaign_adgroups = {
        "Search - B2B SaaS Core": ["CRM Platform", "Lead Management", "Sales Pipeline", "Email Automation"],
        "Search - Enterprise High Intent": ["Enterprise Demo", "Cloud Migration", "Security Compliance"],
        "Search - Competitors": ["Salesforce Alternative", "Hubspot Competitor", "Zoho Alternative"],
        "Search - MidMarket Solutions": ["Workflow Automation", "API Integration", "Customer Portal"],
        "Search - Generic Cloud Tools": ["Business Software", "Productivity Apps", "Office Tools"]
    }
    
    campaigns = list(campaign_adgroups.keys())
    match_types = ["Broad", "Phrase", "Exact"]
    
    # Vocabulary components
    core_nouns = ["crm", "software", "tool", "platform", "app", "dashboard", "system", "service"]
    modifiers = ["best", "top", "cheap", "cloud", "online", "enterprise", "small business", "automated", "easy", "custom"]
    actions = ["buy", "trial", "pricing", "cost", "demo", "review", "comparison", "solution"]
    negative_words = ["free", "crack", "torrent", "login", "careers", "jobs", "salary", "reddit", "download free", "null"]
    
    # Near duplicate clusters
    cluster_templates = [
        ["best crm for small business", "small business best crm", "best crm small business software", "top crm for small businesses", "small business crms"],
        ["enterprise cloud migration tool", "cloud migration tool enterprise", "tools for cloud migration enterprise", "enterprise tool cloud migration"],
        ["sales automation platform online", "online sales automation platforms", "sales automation platform for teams", "sales automations platform online"],
        ["hubspot alternative for startups", "startup hubspot alternative", "alternatives to hubspot for startups", "startup alternative hubspot"],
        ["lead management software pricing", "pricing lead management software", "lead management soft ware cost", "cost of lead management software"]
    ]

    records = []
    
    # 1. Near-duplicate clusters (~2,500 rows)
    n_cluster_rows = 2500
    while len(records) < n_cluster_rows:
        cluster = random.choice(cluster_templates)
        query = random.choice(cluster)
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        mt = random.choice(match_types)
        
        # Coordinated behavior across cluster
        impr = random.randint(2, 25)
        clicks = int(impr * random.uniform(0.04, 0.20))
        cpc = round(random.uniform(1.20, 3.80), 2)
        cost = round(clicks * cpc, 2)
        # Moderate converter or bleeder
        conv = 1 if (clicks >= 8 and random.random() < 0.3) else 0
        conv_val = round(conv * random.uniform(80.0, 300.0), 2)
        
        records.append({
            "query text": query,
            "match type": mt,
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })
        
    # 2. Trap queries: Low sample size, fluke conversions (~2,500 rows)
    # The exact trap PS-01 tests: 1-3 clicks, 1 conversion!
    n_trap_rows = 2500
    for _ in range(n_trap_rows):
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        query = f"{random.choice(modifiers)} {random.choice(core_nouns)} {random.choice(actions)}"
        clicks = random.randint(1, 3)
        impr = clicks * random.randint(2, 6)
        cpc = round(random.uniform(1.50, 4.00), 2)
        cost = round(clicks * cpc, 2)
        conv = 1 # Fluke conversion!
        conv_val = round(random.uniform(50.0, 150.0), 2)
        
        records.append({
            "query text": query,
            "match type": random.choice(match_types),
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })

    # 3. Proven Winners (~800 rows): Statistically high volume, profitable CPA
    n_winner_rows = 800
    for _ in range(n_winner_rows):
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        query = f"{random.choice(['buy', 'get', 'best'])} {ag.lower()} {random.choice(['software', 'now', 'trial'])}"
        clicks = random.randint(16, 85)
        impr = clicks * random.randint(5, 12)
        cpc = round(random.uniform(1.80, 2.80), 2)
        cost = round(clicks * cpc, 2)
        conv = random.randint(3, max(4, int(clicks * 0.12)))
        conv_val = round(conv * random.uniform(120.0, 450.0), 2)
        
        records.append({
            "query text": query,
            "match type": "Phrase" if random.random() > 0.4 else "Exact",
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })

    # 4. Spend Bleeders / Money Pits (~1,200 rows): Heavy spend, 0 conversions
    n_bleeder_rows = 1200
    for _ in range(n_bleeder_rows):
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        query = f"how to {random.choice(core_nouns)} {random.choice(actions)} guide"
        clicks = random.randint(25, 110)
        impr = clicks * random.randint(6, 15)
        cpc = round(random.uniform(2.20, 3.60), 2)
        cost = round(clicks * cpc, 2) # Cost $55 - $350
        conv = 0
        conv_val = 0.0
        
        records.append({
            "query text": query,
            "match type": "Broad",
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })

    # 5. Non-commercial Negative Trigger queries (~1,000 rows): contain 'free', 'crack', 'jobs', etc.
    n_neg_trigger_rows = 1000
    for _ in range(n_neg_trigger_rows):
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        neg_term = random.choice(negative_words)
        query = f"{random.choice(core_nouns)} {neg_term} {random.choice(['download', 'online', 'portal'])}"
        clicks = random.randint(2, 14)
        impr = clicks * random.randint(4, 10)
        cpc = round(random.uniform(0.80, 2.50), 2)
        cost = round(clicks * cpc, 2)
        conv = 0
        conv_val = 0.0
        
        records.append({
            "query text": query,
            "match type": "Broad",
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })

    # 6. Long-tail zero-click dormant (~17,000 rows): The bulk of real Google Ads accounts
    remaining = n_rows - len(records)
    for _ in range(remaining):
        camp = random.choice(campaigns)
        ag = random.choice(campaign_adgroups[camp])
        query = f"{random.choice(modifiers)} {random.choice(core_nouns)} {random.choice(modifiers)} {random.randint(2024, 2026)}"
        impr = random.randint(1, 4)
        clicks = 0
        cost = 0.0
        conv = 0
        conv_val = 0.0
        
        records.append({
            "query text": query,
            "match type": random.choice(match_types),
            "campaign": camp,
            "ad group": ag,
            "impressions": impr,
            "clicks": clicks,
            "cost": cost,
            "conversions": conv,
            "conversion value": conv_val
        })

    df = pd.DataFrame(records)
    # Shuffle to realistic random order
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    out_file = "data/search_terms_25k.csv"
    print(f"Generating realistic 25,000-row Search Terms Report at {out_file}...")
    df = generate_realistic_search_terms(25000)
    df.to_csv(out_file, index=False)
    print(f"Dataset generated successfully! Shape: {df.shape}")
    print(df.head())
