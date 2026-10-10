"""
Personal AI Copilot Module for TriageIQ (PS-01 Search Term Triage Engine).
Provides real-time grounded intelligence, statistical audit reasoning,
and interactive query diagnostics directly to the user.
"""

import re
import html
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def generate_copilot_response(
    user_query: str,
    res_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    target_cpa: float = 220.0
) -> str:
    """
    Generates a mathematically accurate, grounded response from the active
    search-term dataset, engine decisions, and Kestrel advertiser policy.
    """
    q = user_query.lower().strip()
    
    # -------------------------------------------------------------
    # 1. SPECIFIC ROW LOOKUP (e.g., 'row 6', 'row #3', '#1', '6', 'audit row 5')
    # -------------------------------------------------------------
    row_match = re.search(r'(?:row\s*#?|#\s*|^)(\d+)(?:\s*$|\b)', q)
    if row_match:
        rid = int(row_match.group(1))
        matches = res_df[res_df["row_id"] == rid]
        if not matches.empty:
            r = matches.iloc[0]
            clicks = int(r.get("clicks", 0))
            cost = float(r.get("cost", 0.0))
            convs = float(r.get("conversions", 0.0))
            conv_val = float(r.get("conversion_value", 0.0))
            cpa = r.get("cpa")
            cpa_val = f"${cpa:,.2f}" if (cpa is not None and pd.notnull(cpa) and convs > 0) else "— (0 conversions)"
            ci_str = f"[{r.get('ci_lower', 0.0):.1%}, {r.get('ci_upper', 0.0):.1%}]" if clicks > 0 else "N/A"
            review_txt = "⚠️ Flagged for Human Review (`needs_review = True`)" if r.get("needs_review") else "✅ Confident Decision (`needs_review = False`)"
            
            # Special insight for small-sample converting queries (e.g. Row 6)
            special_insight = ""
            if r.get("needs_review") and convs >= 1 and clicks < 10:
                special_insight = f"""
#### 💡 Why This Row Is Quarantined (Small-Sample Guardrail)
> **Statistical Caution:** Although `{r.get('query_text')}` recorded an observed conversion at a nominal CPA of {cpa_val}, the sample size is only **{clicks} clicks**. The Wilson 95% lower bound is **{r.get('ci_lower', 0.0):.1%}**, which indicates high uncertainty. Promoting this term prematurely could waste ad spend if the conversion was an anomaly. It is safely placed in **Human Review** (`needs_review = True`) while preserving status quo (`decision: IGNORE`).
"""
            
            return f"""### 🔍 Audit Dossier for Row #{rid}: `{r.get('query_text', '')}`

- **Organizer Contract Decision:** `{r.get('decision', 'IGNORE')}` (Confidence: `{r.get('confidence', 'MEDIUM')}`)
- **Review Disposition:** {review_txt}
- **Campaign & Group Context:** *{r.get('campaign', '')}* › *{r.get('ad_group', '')}* ({r.get('match_type', 'Broad')})

#### 📊 Performance & Statistical Evidence
- **Volume:** **{clicks:,} clicks** &nbsp;|&nbsp; **Spend:** **${cost:,.2f}**
- **Conversions:** **{int(convs):,}** &nbsp;|&nbsp; **Attributed Value:** **${conv_val:,.2f}**
- **Actual CPA:** **{cpa_val}** *(Target CPA Ceiling: ${target_cpa:,.2f})*
- **Wilson 95% Confidence Interval:** `{ci_str}`
{special_insight}
#### 🎯 Decision Rationale
> {r.get('reason', '')}

#### ⚖️ Supporting Evidence & Constraints
- **🟢 Supporting Evidence:** {r.get('supporting_evidence', 'N/A')}
- **🔴 Counterevidence & Limitations:** {r.get('counterevidence', 'N/A')}
- **📌 Recommended Next Action:** **{r.get('next_action', 'N/A')}**"""
        else:
            return f"⚠️ Row #{rid} was not found in the current dataset (valid row IDs range from 1 to {len(res_df):,})."

    # -------------------------------------------------------------
    # 2. SPECIFIC SEARCH QUERY SEARCH (e.g., 'what about equipment loan', 'audit personal loans')
    # -------------------------------------------------------------
    # Look for query words in quotes or after keywords
    search_term = None
    term_match = re.search(r"['\"]([^'\"]+)['\"]", user_query)
    if term_match:
        search_term = term_match.group(1).strip()
    elif any(k in q for k in ["about ", "query ", "search for ", "audit ", "check "]):
        for prefix in ["about ", "query ", "search for ", "audit ", "check "]:
            if prefix in q:
                candidate = q.split(prefix, 1)[1].strip(" ?.!\"'")
                if len(candidate) > 3 and not candidate.startswith("row"):
                    search_term = candidate
                    break
                    
    if search_term:
        term_matches = res_df[res_df["query_text"].str.contains(search_term, case=False, na=False)]
        if not term_matches.empty:
            r = term_matches.iloc[0]
            total_matches = len(term_matches)
            cpa = r.get("cpa")
            cpa_val = f"${cpa:,.2f}" if (cpa is not None and pd.notnull(cpa) and r.get("conversions", 0) > 0) else "—"
            review_txt = "⚠️ Needs Human Review" if r.get("needs_review") else "✅ Confident Decision"
            
            note = f"\n*(Showing top match of {total_matches:,} queries matching '{search_term}')*" if total_matches > 1 else ""
            return f"""### 🔍 Query Match: `{r.get('query_text', '')}` (Row #{r.get('row_id')}){note}

- **Primary Decision:** `{r.get('decision', 'IGNORE')}` ({review_txt})
- **Performance:** {r.get('clicks', 0):,} clicks · ${r.get('cost', 0.0):,.2f} spend · {int(r.get('conversions', 0)):,} convs
- **Actual CPA:** {cpa_val} *(Target: ${target_cpa:,.2f})*
- **Wilson 95% Bound:** [{r.get('ci_lower', 0.0):.1%}, {r.get('ci_upper', 0.0):.1%}]
- **Rationale:** {r.get('reason', '')}
- **Recommended Action:** **{r.get('next_action', '')}**"""

    # -------------------------------------------------------------
    # 3. SAVINGS, WASTE, AND BLOCKED SPEND
    # -------------------------------------------------------------
    if any(k in q for k in ["save", "saving", "waste", "blocked spend", "cut spend", "how much money"]):
        blocked_df = res_df[res_df["decision"] == "BLOCK"]
        total_blocked_spend = float(blocked_df["cost"].sum())
        total_blocked_count = len(blocked_df)
        pct_blocked = (total_blocked_count / max(1, len(res_df))) * 100
        
        # Categorize waste
        off_target_spend = float(blocked_df[blocked_df["reason"].str.contains("off-target|non-commercial|personal|template|grant|job", case=False, na=False)]["cost"].sum())
        bleeder_spend = total_blocked_spend - off_target_spend
        
        return f"""### 💰 Financial Waste Elimination Summary

By deploying TriageIQ's negative keyword exclusions to Google Ads, the account can recover:

- **Potential Media Waste Reduction:** **${total_blocked_spend:,.2f}**
- **Search Terms Blocked:** **{total_blocked_count:,} queries** ({pct_blocked:.1f}% of active search volume)

#### 📉 Breakdown of Waste Drivers
1. **Off-Target & Consumer Query Exclusions:** **${off_target_spend:,.2f}**
   - High-cost traffic with zero commercial intent (e.g., consumer personal loans, mortgages, auto loans, grant seekers, and employment hunters).
2. **Spend Bleeders with Zero Conversions:** **${bleeder_spend:,.2f}**
   - Commercial keywords where expenditure surpassed the allowable CPA threshold (${target_cpa:,.2f}) with zero conversions.

👉 **How to apply:** Navigate to **📥 Google Ads Exports** in the sidebar, download `google_ads_negative_keywords.csv`, and import directly into Google Ads Editor."""

    # -------------------------------------------------------------
    # 4. SMALL SAMPLE NOISE / VARIANCE TRAP (ROW 6 PHENOMENON)
    # -------------------------------------------------------------
    if any(k in q for k in ["small sample", "variance trap", "1 conversion", "1 conv", "single conversion", "one conversion"]):
        one_conv_df = res_df[(res_df["conversions"] == 1) & (res_df["clicks"] <= 3)]
        one_conv_count = len(one_conv_df)
        
        return f"""### ⚠️ The Small-Sample Variance Trap (1 Conversion != Success)

One of the most dangerous pitfalls in Google Ads search-term management is **premature promotion**:

#### Why TriageIQ treats single conversions cautiously:
1. **The Fallacy of Low CPA on N=1:**
   - A query with **1 click, $12.50 spend, and 1 conversion** has a nominal CPA of $12.50.
   - However, a sample size of $N=1$ provides near-zero statistical significance.
2. **Asymmetric Wilson Confidence Bound:**
   - On 1 conversion from 1 click, the 95% Wilson confidence interval is **[2.5%, 97.5%]**.
   - The lower bound is nearly zero! This means the true long-term conversion rate could easily be unprofitable.
3. **Engine Policy & Quarantining:**
   - TriageIQ enforces a minimum evidence gate (default: **{engine_params_min_clicks(res_df)} clicks and 2 conversions**).
   - In accordance with the organizer's contract, these queries receive **`decision: IGNORE`** with **`needs_review: True`**.
   - This quarantines the query in the **Human Review Queue** so a senior media buyer can evaluate business viability before risking campaign budget."""

    # -------------------------------------------------------------
    # 5. KESTREL ADVERTISER BOUNDARIES & EXCLUSION POLICIES
    # -------------------------------------------------------------
    if any(k in q for k in ["kestrel", "boundary", "boundaries", "exclusion", "exclude", "negative policy", "product"]):
        return f"""### 🛡️ Advertiser Boundaries: Kestrel Business Funding

TriageIQ is customized with explicit business boundaries to protect Kestrel's small business lending budget:

#### 🟢 Supported Core Products (Allowed / Promoted)
- Small business working capital loans
- Commercial equipment financing and leasing
- Business lines of credit
- Merchant cash advances (MCA)
- SBA 7(a) and 504 commercial loans

#### 🔴 Explicit Negative Triggers (Instantly Blocked)
- **Consumer Loans:** `personal loans`, `auto loans`, `car financing`, `mortgages`, `student loans`
- **Grants & Handouts:** `government grant`, `federal grants`, `stimulus checks`
- **Career & Employment:** `jobs`, `hiring`, `salary`, `careers`, `resume`, `internship`
- **Non-Buyers:** `templates`, `sample invoice`, `login`, `portal`, `wikipedia`, `pdf`

These triggers are mapped to **Campaign-level Negative Phrase** and **Ad Group-level Negative Exact** keywords."""

    # -------------------------------------------------------------
    # 6. TOP PROMOTION CANDIDATES
    # -------------------------------------------------------------
    if any(k in q for k in ["top candidate", "best keyword", "top promoted", "winner", "promote candidate", "best terms"]):
        prom_df = res_df[res_df["decision"] == "PROMOTE"].sort_values(by="conversions", ascending=False).head(3)
        if prom_df.empty:
            return "Currently no queries have met the high-evidence threshold for promotion."
            
        winners_txt = ""
        for idx, (_, w) in enumerate(prom_df.iterrows(), 1):
            winners_txt += f"""{idx}. **`{w['query_text']}`** (Row #{w['row_id']})
   - Conversions: **{int(w['conversions'])}** · Spend: **${w['cost']:,.2f}** · Actual CPA: **${w['cpa']:,.2f}**
   - Wilson Lower Bound: **{w['ci_lower']:.1%}** · Suggested Max CPC: **${w['proposed_bid']:,.2f}**\n"""
            
        return f"""### 🚀 Top High-Evidence Promoted Candidates

These search terms have cleared all statistical evidence gates and demonstrated sustained profitability:

{winners_txt}
These candidates are formatted into `google_ads_promoted_keywords.csv` as **Exact Match** keywords with bids calibrated to Empirical Bayes conversion probabilities."""

    # -------------------------------------------------------------
    # 7. CAMPAIGN PERFORMANCE & EFFICIENCY
    # -------------------------------------------------------------
    if any(k in q for k in ["campaign performance", "best campaign", "which campaign", "campaign efficiency", "cpa by campaign"]):
        camp_agg = clean_df.groupby("campaign").agg({"cost": "sum", "conversions": "sum"}).reset_index()
        camp_agg["cpa"] = camp_agg["cost"] / camp_agg["conversions"].replace(0, np.nan)
        camp_agg = camp_agg.sort_values(by="conversions", ascending=False)
        
        camp_txt = ""
        for _, c in camp_agg.head(4).iterrows():
            cpa_str = f"${c['cpa']:,.2f}" if pd.notnull(c["cpa"]) else "—"
            camp_txt += f"- **{c['campaign']}**: Spend ${c['cost']:,.2f} · Conversions {int(c['conversions']):,} · CPA **{cpa_str}**\n"
            
        return f"""### 📊 Campaign Performance & Conversion Overview

Account performance across key campaigns:

{camp_txt}
- **Account Baseline CPA:** **${clean_df['cost'].sum() / max(1.0, clean_df['conversions'].sum()):,.2f}**
- **Allowable Target CPA:** **${target_cpa:,.2f}**"""

    # -------------------------------------------------------------
    # 8. HOW THE DECISION ENGINE & WILSON INTERVAL WORKS
    # -------------------------------------------------------------
    if any(k in q for k in ["how it work", "decision engine", "wilson", "empirical bayes", "algorithm", "methodology"]):
        return f"""### ⚙️ How TriageIQ's Evidence Engine Operates

TriageIQ enforces a **three-tier statistical decision framework**:

1. **Strict 3-Way Contract:**
   - Every search term is assigned exactly one decision: **`PROMOTE`**, **`BLOCK`**, or **`IGNORE`**.
   - Human review is strictly decoupled as a boolean flag (`needs_review`).
2. **Wilson Binomial Confidence Bounds:**
   - Computes an asymmetric confidence interval $[p_-, p_+]$ for conversion rate.
   - For low click counts, the lower bound $p_-$ shrinks toward 0, preventing accidental promotion of lucky queries.
3. **Empirical Bayes Shrinkage:**
   - Shrinks query-level conversion rates toward the campaign baseline prior to filter out variance noise.
4. **Three Action Categories:**
   - **`PROMOTE`**: High volume ($\ge 10$ clicks, $\ge 2$ convs), Wilson lower bound $> 0$, and CPA $\le$ Target CPA.
   - **`BLOCK`**: Excluded business triggers OR cost bleeder with 0 conversions exceeding allowable CPA.
   - **`IGNORE`**: Insufficient data (1-5 clicks) to make a confident intervention, preserving the status quo."""

    # -------------------------------------------------------------
    # 9. CONTEXT-AWARE NEGATIVE SUGGESTIONS & OVER-EXCLUSION RISKS
    # -------------------------------------------------------------
    if any(k in q for k in ["negative suggestion", "negative keyword", "negative scope", "over-exclusion", "exclusion risk"]):
        return f"""### 🛡️ Context-Aware Negative Keyword Guidance

TriageIQ generates negative keyword candidates using the **Narrowest Appropriate Scope Rule**:

1. **Narrow Scope Enforcement:**
   - Universal off-target business exclusions (`personal loans`, `student loans`, `grants`, `jobs`) receive **Campaign-level Negative Phrase** scope.
   - Ad-group specific spend bleeders receive **Ad Group-level Negative Exact** scope to avoid mistakenly blocking relevant queries in other ad groups.
2. **Over-Exclusion Risk Analysis:**
   - Every negative phrase is audited for collisions with B2B commercial vocabulary (`business`, `commercial`, `equipment`, `loans`).
   - If a phrase contains generic or broad words, an amber warning flag is generated to prevent accidental suppression of legitimate commercial borrowers.
3. **Analyst Approval Workflow:**
   - All negative suggestions are initially marked **Pending Analyst Approval** and do not alter Google Ads until approved."""

    # -------------------------------------------------------------
    # 10. INTENT CLUSTERING & DECISION CONFLICTS
    # -------------------------------------------------------------
    if any(k in q for k in ["cluster", "clustering", "intent", "near-duplicate", "conflict"]):
        conflict_count = int(res_df.get("cluster_has_conflict", pd.Series([False]*len(res_df))).sum())
        return f"""### 🧩 Near-Duplicate Search-Intent Clustering

TriageIQ groups semantically equivalent queries using token normalization and intent categorization:

1. **Syntactic Collapse with Qualifier Preservation:**
   - Collapses word re-orderings, punctuation, and pluralizations.
   - Strictly preserves commercial qualifiers: *business vs personal*, *calculator*, *alternative*, *bad credit*, *jobs*.
2. **Decision Conflict Detection:**
   - Flags clusters where member queries received conflicting decisions (e.g. one variant was `PROMOTE` while another was `IGNORE` due to click thresholds).
   - Currently **{conflict_count:,} search terms** belong to clusters with decision divergence.
3. **Reviewer Reconciliation:**
   - Analysts can inspect clusters in the **🧩 Intent Clusters** tab and reconcile cluster-wide policies with a single click."""

    # -------------------------------------------------------------
    # 11. REVIEWER PRECEDENTS & SESSION LEARNING
    # -------------------------------------------------------------
    if any(k in q for k in ["precedent", "reviewer correction", "session learning", "analyst learning", "correction"]):
        return f"""### 💡 Reviewer Precedents & Contextual Learning

TriageIQ learns from analyst corrections dynamically within the session without model retraining:

1. **Precedent Recording:**
   - When an analyst changes a recommendation (e.g. in the Review Queue), TriageIQ logs the original decision, revised decision, query text, campaign, reason code, and timestamp.
2. **Contextual Guidance:**
   - Unreviewed queries are cross-referenced against historical corrections using token similarity.
   - When a similar query is detected, TriageIQ surfaces a precedent banner explaining how a human reviewer handled the case previously.
3. **Guidance, Not Universal Ground Truth:**
   - Precedents are offered as guidance. They do not silently override statistical data, preserving the analyst's ultimate judgment."""

    # -------------------------------------------------------------
    # 9. GENERAL CONVERSATIONAL / FALLBACK RESPONSE
    # -------------------------------------------------------------
    total_queries = len(res_df)
    prom_count = int((res_df["decision"] == "PROMOTE").sum())
    block_count = int((res_df["decision"] == "BLOCK").sum())
    ign_count = int((res_df["decision"] == "IGNORE").sum())
    rev_count = int(res_df["needs_review"].sum())
    
    return f"""### 🤖 TriageIQ Search Copilot

I'm monitoring your active **{total_queries:,} search terms**. Current account status:

- **🚀 Promoted Winners:** **{prom_count:,}** terms ({prom_count/total_queries:.1%})
- **🚫 Blocked Exclusions:** **{block_count:,}** terms ({block_count/total_queries:.1%})
- **⏸️ Ignored (Status Quo):** **{ign_count:,}** terms ({ign_count/total_queries:.1%})
- **⚠️ Human Review Queue:** **{rev_count:,}** flagged terms ({rev_count/total_queries:.1%})

#### What you can ask me:
- **Inspect any row:** *"Audit row #6"* or *"Why was row 3 promoted?"*
- **Search any query:** *"Check 'equipment financing calculator'"*
- **Financial impact:** *"How much historical spend can we save?"*
- **Methodology:** *"Why are 1-conversion keywords quarantined?"*
- **Policy rules:** *"Explain Kestrel's negative keyword boundaries"*"""

def engine_params_min_clicks(df: pd.DataFrame) -> int:
    return 10
