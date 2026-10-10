# 🎯 TriageIQ — Evidence-First Search Intelligence (PS-01)
PUBLIC URL LINK :  https://admirable-sawine-ad4590.netlify.app/
> **Audited, Contract-Compliant Search Term Triage Engine & Review Dashboard**  
> Built for Google Ads Search Term Reports with Wilson Confidence Intervals, Empirical Bayes Shrinkage, Intent Clustering, and Human-in-the-Loop Review.

---

## 📋 1. Organizer Output Contract Compliance

Every input search-term record receives **strictly one** of the three mandated decisions:
* **`PROMOTE`**: Statistically validated candidates meeting sample evidence criteria, profitable CPA ceiling, and narrow Wilson intervals.
* **`BLOCK`**: Excluded terms violating advertiser business scope (e.g. personal loans, car loans, mortgages, student loans, grants, jobs) or sustained spend bleeders.
* **`IGNORE`**: Dormant long-tail terms preserved without cluttering account limits, or terms with insufficient evidence.

### Human Review Handling (`needs_review`)
Human review is represented separately via the boolean flag **`needs_review`**:
* When sample size is underpowered (e.g. 1 click, 1 conversion) or signals conflict, the row receives **`decision = "IGNORE"`** and **`needs_review = True`**.
* The complete audit CSV (`full_triage_audit.csv`) contains 100% of input rows (exactly 25,000 rows for the official dataset) with valid decisions and complete evidence cards.

---

## 📐 2. The Evidence Policy & Uncertainty Framework

### The Problem Trap: 1 Click, 1 Conversion (`apply business loan approval`)
* **Raw CVR**: $100\%$ ($1 / 1$)
* **Wilson 95% Confidence Interval**: $[20.6\%, 100.0\%]$ (Spread: $79.4\%$)
* **Why Wilson Lower Bound $> 1.5\%$ Alone Fails**: At $n=1$, the Wilson lower bound is $20.6\% > 1.5\%$. Relying purely on lower bound thresholding would erroneously promote this noise.
* **TriageIQ Multi-Gate Evidence Policy**:
  1. **Evidence Prerequisite**: Clicks $\ge 10$ and Conversions $\ge 2$.
  2. **Interval Quality**: Wilson 95% interval width $\le 40\%$.
  3. **Economic Ceiling**: CPA $\le 1.15 \times \text{Target CPA}$.
  4. **Intent Alignment**: Must not contain off-target root exclusions.
* **Result**: Quarantined to `IGNORE` with `needs_review = True`, `confidence = "LOW"`, and an explicit explanation citing sample variance.

---

## 🏢 3. Advertiser Business Boundaries (Kestrel Business Funding)

Configurable `AdvertiserProfile` encapsulates business offerings:
* **Supported**: Working capital loans, equipment finance, business lines of credit, merchant cash advances, SBA loans.
* **Explicit Exclusions**: Personal loans, mortgages, car loans, student loans, government grants, careers/jobs, free invoice templates.
* Off-target queries with 0 conversions are immediately blocked at the **Campaign level** as **Negative Phrase** to prevent brand dilution.

---

## 💰 4. Defensible Financial Terminology

Misleading claims (e.g. "guaranteed savings") have been replaced with audit-defensible metrics:
* **Historical Spend on Blocked Terms**: The actual historical cost of queries now recommended for exclusion. Labeled as potential future spend reduction, not realized savings.
* **Attributed Conversion Value**: Total gross application value tracked by Google Ads, clearly distinguished from net revenue or profit.

---

## 📊 5. Verification & Benchmark on Production Dataset (25k Search Terms)

Evaluated against the 25,000-row Kestrel Business Funding production report (`search_terms_report.csv`) in **1.28 seconds**:

| Metric | Production Dataset Value | Description |
| :--- | :--- | :--- |
| **Total Ingested Rows** | **25,000** | 100% input preservation (zero dropped/duplicated rows) |
| **`PROMOTE` Decisions** | **1,179 (4.7%)** | Statistically verified exact match candidates |
| **`BLOCK` Decisions** | **5,267 (21.1%)** | Excluded off-target queries and sustained bleeders |
| **`IGNORE` Decisions** | **18,554 (74.2%)** | Dormant long-tail and unproven traffic |
| **`needs_review = True`** | **4,155 (16.6%)** | Underpowered conversions, borderline spend, and conflicts |
| **Historical Spend on Blocked Terms** | **$372,126.02** | Potential future spend reduction |
| **Attributed Conversion Value** | **$18,673,641.00** | Across 8,521 tracked loan applications |
| **Intent Clusters** | **16,775 clusters** | 6,219 multi-variant clusters consolidated |

---

## 🧪 6. Automated Unit Tests

All 11 unit tests pass in **0.002 seconds**:
```bash
.\.venv\Scripts\python.exe -m unittest tests/test_triage.py
```
1. `test_one_click_one_conversion_quarantined` (PASS)
2. `test_two_clicks_one_conversion_quarantined` (PASS)
3. `test_zero_clicks_zero_conversions_status_quo` (PASS)
4. `test_clearly_unsupported_product_blocked` (PASS)
5. `test_sufficient_evidence_strong_performance_promoted` (PASS)
6. `test_sufficient_evidence_poor_performance_blocked` (PASS)
7. `test_borderline_spend_insufficient_evidence_routed_to_review` (PASS)
8. `test_missing_or_invalid_numeric_fields_handled_safely` (PASS)
9. `test_clustering_near_duplicates_vs_distinct_intent` (PASS)
10. `test_reviewer_override_records_original_and_final_decision` (PASS)
11. `test_output_contract_fields_presence` (PASS)

---

## 🖥️ 7. Running the Application

```powershell
# Run the batch CLI pipeline
.\.venv\Scripts\python.exe run_cli.py --input "data/search_terms_25k.csv" --output-dir "output_kestrel"

# Launch the Streamlit Dashboard (or double-click run_app.bat)
.\.venv\Scripts\python.exe -m streamlit run app.py
```
