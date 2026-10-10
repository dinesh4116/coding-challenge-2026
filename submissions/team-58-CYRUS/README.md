# SearchGuard AI: Evidence-Aware Search Term Triage & Decision Intelligence Platform

SearchGuard AI is a production-grade, explainable search-term triage platform built on the real Google Ads operational dataset `search_terms_report.csv` (25,000 records, 17,526 unique queries across 6 commercial lending campaigns).

---

## 1. Project Overview & Core Mission

When managing enterprise PPC campaigns in commercial finance, search-term triage is fraught with two dangerous failure modes:
1. **False Positives (Wasted Ad Spend):** Failing to block irrelevant searches (job seekers, government grant seekers, document templates, personal consumer banking) and high-spend non-converting bleeders.
2. **False Negatives (Premature Negative Keywording):** Naively blocking promising keywords based on small sample sizes (e.g., 2 clicks and 0 conversions) or conflating high text relevance with commercial performance.

**SearchGuard AI** solves this by establishing the **Decision Risk Ledger**, strictly decoupling three distinct concepts:
- **Text Relevance:** Semantic alignment with campaign theme (using TF-IDF n-gram vectorization and cosine similarity).
- **Observed Commercial Performance:** Mathematical metrics (CTR, CPC, Conversion Rate, CPA, ROAS) with division-by-zero safeguards and Wilson score 95% confidence intervals.
- **Decision Confidence & Evidence Maturity:** Sample size sufficiency (`STRONG`, `MODERATE`, `INSUFFICIENT`, `ZERO_CLICKS`), ensuring early-stage exploratory traffic is protected in `IGNORE` rather than falsely pruned.

Every record receives exactly one of three deterministic actions:
- `PROMOTE` (4,762 records / 19.05%): Validated commercial traction with strong ROAS/CPA economics.
- `BLOCK` (4,062 records / 16.25%): Confirmed semantic irrelevance or sustained non-converting spend.
- `IGNORE` (16,176 records / 64.70%): Insufficient evidence maturity or zero clicks; protected from premature actions.

---

## 2. Platform Architecture & Stack

### Backend Stack
- **Python 3.10+**
- **FastAPI**: REST API with Pydantic v2 schemas and CORS.
- **SQLAlchemy & SQLite**: ACID persistence for all 25,000 decision records, campaign configurations, and human review logs.
- **pandas & NumPy**: Vectorized feature engineering and dataset transformations.
- **scikit-learn**: TF-IDF n-gram vectorizer and cosine semantic relevance engine.
- **SciPy & Math**: Wilson score 95% confidence intervals for conversion rate.
- **pytest & HTTPX**: Comprehensive 16-test automated verification suite.

### Frontend Stack
- **React 18 & Vite**
- **Tailwind CSS**: Custom dark slate / deep navy enterprise design tokens.
- **Lucide React**: Clean enterprise iconography.
- **Recharts**: Responsive SVG charts (donuts, horizontal bars, multiple metrics).
- **React Router v6**: 10 distinct client-side pages.
- **Axios**: HTTP API client with proxying.

---

## 3. The 10 Application Pages

| # | Page Name | Route | Key Features |
|---|-----------|-------|--------------|
| 1 | **Dashboard Overview** | `/` | Platform KPI cards (25k rows, $3.11M spend, 14,404 conv, 10.09x ROAS), action donut, intent bar charts, architectural principles callout. |
| 2 | **Dataset Profiling** | `/profiling` | Real dataset integrity report (0 missing cells), column schemas, match type breakdown (broad 49.5%, phrase 32.3%, exact 18.2%), descriptive statistics. |
| 3 | **Search-Term Explorer** | `/explorer` | Real-time query search, multi-filter dropdowns (Action, Intent, Campaign, Match Type, Metric sorting), paginated data table. |
| 4 | **Decision Risk Ledger** | `/ledger` | **Flagship Feature**: Decoupled view of relevance vs performance vs confidence. Expandable row drawers detailing Algorithmic Reason, Wrong Decision Consequence, and Suggested Next Action. |
| 5 | **Campaign Comparison** | `/campaigns` | Side-by-side comparative table for all 6 campaigns, Spend vs Revenue multiple charts, and modal to configure Target CPA & ROAS thresholds. |
| 6 | **Duplicate-Query Explorer** | `/duplicates` | Analysis of 17,526 distinct terms. Toggle for **Conflicting Decisions Only** (revealing 5,337 instances where queries had divergent performance across ad groups). |
| 7 | **Human-Review Queue** | `/reviews` | Controlled review queue for the 1,547 flagged records. Accept or override actions with mandatory analyst rationale, live acceptance rate metrics, and review history ledger. |
| 8 | **Decision Audit Detail** | `/audit/:rowId` | Deep-dive counterfactual audit explaining influencing metrics, Wilson 95% CVR bounds, "What-If" scenario simulations, and trade-off risk analysis. |
| 9 | **CSV Export Center** | `/export` | One-click downloads for the complete 25,000-record Decision Risk Ledger CSV, PROMOTE keyword lists, BLOCK negative lists, or custom filtered slices. |
| 10 | **Model & Evaluation Report** | `/evaluation` | Honest scientific evaluation report without fabricated classification accuracy. Low-sample edge case safety tests, Naive baseline contrast, and documented limitations. |

---

## 4. Decision Risk Ledger Schema (34 Columns)

The output CSV (`data/processed/search_terms_decision_ledger.csv`) preserves all 10 original columns and appends 24 engineered features:

### Original Columns (Preserved 100%)
1. `row_id`: Integer primary key (1 to 25000)
2. `search_term`: Exact query string
3. `match_type`: `broad`, `phrase`, or `exact`
4. `campaign`: Campaign identifier
5. `ad_group`: Ad group cluster
6. `impressions`: Search impression count
7. `clicks`: Post-impression click count
8. `cost`: Observed ad spend
9. `conversions`: Form/lead submission count
10. `conversion_value`: Observed gross value

### Engineered Advertising & Uncertainty Features
11. `ctr`: `clicks / impressions` (None/null if impressions == 0)
12. `cpc`: `cost / clicks` (None/null if clicks == 0)
13. `conversion_rate`: `conversions / clicks` (None/null if clicks == 0)
14. `cost_per_conversion`: `cost / conversions` (None/null if conversions == 0)
15. `roas`: `conversion_value / cost` (None/null if cost == 0)
16. `cr_ci_lower`: Wilson score 95% confidence interval lower bound
17. `cr_ci_upper`: Wilson score 95% confidence interval upper bound
18. `historical_cost`: Observed past spend (transparently labeled as historical spend)

### Intent & Semantic Relevance Features
19. `intent_category`: `purchase`, `research`, `comparison`, `informational`, `irrelevant`
20. `intent_score`: Classification confidence score
21. `relevance_status`: `HIGH`, `MODERATE`, `LOW`, `IRRELEVANT`
22. `relevance_score`: Cosine similarity score against campaign corpus

### Decision Risk Ledger Fields
23. `evidence_status`: `STRONG`, `MODERATE`, `INSUFFICIENT`, `ZERO_CLICKS`
24. `recommended_action`: `PROMOTE`, `BLOCK`, `IGNORE`
25. `decision_confidence`: `HIGH`, `MEDIUM`, `LOW`
26. `decision_reason`: Primary documented algorithmic justification
27. `uncertainty_reason`: Description of statistical or semantic variance
28. `potential_consequence`: Consequence of an erroneous decision (e.g. false block risk)
29. `human_review_required`: Boolean flag for analyst sign-off
30. `suggested_next_action`: Actionable PPC strategy recommendation

### Duplicate Intelligence Fields
31. `is_duplicate_term`: Boolean indicating term frequency > 1
32. `term_frequency`: Total occurrences across dataset
33. `has_conflicting_decision`: Boolean indicating contradictory decisions across ad groups
34. `duplicate_group_id`: Consistent group cluster hash

---

## 5. Quickstart & Windows PowerShell Commands

### Step 1: Environment Setup
Ensure Python 3.10+ and Node.js v18+ are available.

```powershell
# Navigate to the project root
cd "c:\Users\kspra\Downloads\Search Term Traige"

# Activate the existing virtual environment (or create one)
.\.venv\Scripts\Activate.ps1

# Verify installed dependencies
python -m pip install -r requirements.txt
```

### Step 2: Run End-to-End Test Suite
Verify that all 16 automated tests pass:

```powershell
.\.venv\Scripts\python -m pytest tests -v
```

### Step 3: Run the Intelligence Pipeline
Process all 25,000 records, output the decision CSV, and seed the SQLite database:

```powershell
.\.venv\Scripts\python -m backend.app.pipeline.pipeline_runner
```

### Step 4: Start the FastAPI Backend
Launch the API server on port 8000:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 5: Start the React Frontend
In a new terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/` in your browser.

---

## 6. End-to-End API Verification Script
Run the automated verification script that tests all 10 API domains in under 3 seconds:

```powershell
.\.venv\Scripts\python scripts/verify_system.py
```

Sample output:
```text
============================================================
VERIFYING SEARCHGUARD AI BACKEND API ENDPOINTS
============================================================
[OK] Health Check: healthy
[OK] Overview: 25000 records, 17526 distinct terms
     Actions: PROMOTE: 4762, BLOCK: 4062, IGNORE: 16176
     Spend: $3,111,054.26, Conversions: 14,404, ROAS: 10.09x
[OK] Profile: 25000 rows, missing cells: 0
[OK] Records Search ('sba' + PROMOTE): 340 matches found
[OK] Campaigns: 6 campaigns returned
[OK] Conflicting Duplicate Groups: 5 sample groups returned
[OK] Counterfactual Audit for Record #3: Wilson 95% CVR [0.0258 - 0.1568]
[OK] Review Submission Logged: ID #1 for Record #3 (PROMOTE)
[OK] Review Stats: 1 reviews, 100.0% acceptance rate
[OK] Evaluation Report: 8,635 low-sample queries protected in IGNORE
[OK] Export Center: Successfully streamed CSV data
============================================================
ALL API ENDPOINTS AND SCIENTIFIC LOGIC VERIFIED 100%!
============================================================
```

---

## 7. Honest Evaluation & Scientific Limitations

1. **No Fake Accuracy Metrics:** Because the operational Google Ads search-terms report contains no ground-truth analyst labels, reporting synthetic classification metrics (F1 score, precision, recall) is scientifically invalid. Instead, the platform evaluates deterministic rule coverage, low-sample edge case pass rates (83.7% protected), and duplicate conflict resolution.
2. **Gross Value vs Net Margin:** `conversion_value` represents gross loan value generated, not net commercial lender margin. ROAS calculations represent gross revenue multiples.
3. **Broad Match Sensitivity:** Broad match accounts for 49.5% of records; conservative click volume thresholds (clicks >= 25 or cost >= $220) prevent premature negative keywording while allowing traffic exploration.
