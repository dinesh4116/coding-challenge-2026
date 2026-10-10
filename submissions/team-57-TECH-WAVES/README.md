# Search Term Triage Engine (PS-01)
> **Explainable Search Intelligence for Google Ads**  
> Problem Statement: **PS-01**

The **Search Term Triage Engine** is a full-stack, local-first web application designed for Google Ads performance marketing analysts. Rather than forcing every search query into an arbitrary binary classification or relying on opaque external AI APIs, the engine executes **modular, explainable rule classification**, **statistical uncertainty checks**, **token similarity clustering**, and **traceable wasted-spend modeling**.

The engine operates 100% locally with zero external API fees or external data transmission risks.

---

## 🌟 Key Capabilities

1. **Modular 4-Way Decision Triage**:
   - `PROMOTE`: High commercial intent with verified statistical significance (clicks $\ge$ 15, repeated conversions $\ge$ 2, profitable CPA $\le$ $150).
   - `BLOCK`: High-confidence non-commercial or irrelevant intent (e.g. piracy, job seekers, DIY, login portals) or excessive spend with zero return.
   - `IGNORE`: Natural low-cost exploratory search queries below intervention thresholds.
   - `HUMAN REVIEW`: High-uncertainty queries routed to an oversight backlog. **Crucially: 2 clicks and 1 conversion is never blindly promoted; high spend with 0 conversions is never blindly blocked if commercial intent is present.**
2. **Confidence & Uncertainty Engine**:
   - Multi-factor heuristic indicator (0–100%) quantifying Data Completeness (25%), Sample Sufficiency (35%), Intent Clarity (25%), and Signal Agreement (15%).
   - Transparently discloses uncertainty factors, sample size variance, and missing metrics.
3. **Syntactic Query Clustering**:
   - Groups near-duplicate phrases using token-overlap Jaccard similarity ($\ge$ 0.60).
   - Uncovers intra-cluster conflicts (e.g. one variant was promoted while another was blocked).
4. **Negative Keyword Builder & Google Ads Editor Export**:
   - Auto-generates exact, phrase, or broad negative recommendations with campaign vs. ad-group scope.
   - Exports CSV formatted for Google Ads Editor bulk upload.
5. **Wasted-Spend Intelligence & What-If Simulator**:
   - Distinguishes historical actual spend, confirmed non-commercial leakage, and spend under investigation.
   - Interactive sliders for negative keyword spend cutoff and analyst adoption rate to project annual savings.
6. **SQLite Reviewer Feedback & Continuous Learning**:
   - Overrides and analyst rationales are persisted in SQLite and inform subsequent re-analyses without universal overfitting.
7. **Scale & Data Integrity**:
   - Tested and verified on **25,000+ rows** in under 7 seconds.
   - Protected against CSV formula injection (`=`, `+`, `-`, `@`).

---

## 🏗️ Project Architecture

```
Search Term Triage Engine/
├── backend/
│   ├── app.py                      # Flask REST API with active session state & CORS
│   ├── services/
│   │   ├── classifier.py           # Explainable rule-based decision engine
│   │   ├── confidence.py           # Multi-factor confidence & uncertainty scoring
│   │   ├── clustering.py           # Jaccard token-set query clustering
│   │   ├── spend_analysis.py       # Avoidable spend & what-if simulator
│   │   ├── data_validator.py       # Robust CSV parsing & malformed row isolation
│   │   ├── report_generator.py     # Formula-safe CSV & executive audit reports
│   │   └── db.py                   # SQLite persistence for feedback & audit logs
│   ├── tests/
│   │   ├── test_triage_engine.py   # Unit, uncertainty, and 25k-row stress tests
│   │   └── test_api.py             # Flask API endpoint integration tests
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/             # Navbar, Sidebar, StatCard, Badges, DetailDrawer, Toast
│   │   ├── pages/                  # 11 Dedicated views (Dashboard, Analysis, Queue, Clusters, etc.)
│   │   ├── services/api.ts         # REST client connecting to backend
│   │   ├── types/index.ts          # TypeScript domain models
│   │   ├── App.tsx                 # Main layout and routing state
│   │   └── index.css               # Dark navy aesthetic & Tailwind utilities
│   ├── tailwind.config.js          # Custom colors (navy, electric blue, decision badges)
│   ├── vite.config.ts              # Vite config with API proxy
│   └── package.json
├── sample_data/
│   ├── sample_search_terms.csv     # Curated diverse Google Ads queries
│   └── generate_sample_data.py     # Script to generate up to 25k+ synthetic rows
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python**: 3.10 – 3.14
- **Node.js**: v18+ (tested on Node v24)
- **npm**: v9+ (tested on npm 11)

---

### 1. Backend Setup

#### Windows PowerShell:
```powershell
# In repository root
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

#### Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

---

### 2. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

### 3. Running the Application

You need two terminal windows (one for the backend and one for the frontend):

#### Terminal 1 — Start Flask Backend:
```powershell
# Windows
.\venv\Scripts\python.exe backend/app.py

# Linux/macOS
python backend/app.py
```
*Backend will start on `http://127.0.0.1:5000` (pre-loaded with sample demo data).*

#### Terminal 2 — Start Vite Frontend:
```bash
cd frontend
npm run dev
```
*Frontend will start on `http://localhost:5173/`.*

Open **`http://localhost:5173/`** in your browser.

---

## 🧪 Running Automated Tests

A comprehensive 22-test automated suite is provided covering data validation, uncertainty safeguards (2 clicks / 1 conv), zero-conversion checks, formula injection, SQLite persistence, and a 25,000-row performance test.

To run the test suite:
```powershell
# Windows PowerShell
.\venv\Scripts\python.exe -m pytest -v backend/tests/

# Linux / macOS
python -m pytest -v backend/tests/
```

### Verified Test Results:
```text
backend/tests/test_api.py::test_api_health PASSED
backend/tests/test_api.py::test_api_summary PASSED
backend/tests/test_api.py::test_api_results_filtering PASSED
backend/tests/test_api.py::test_api_review_queue PASSED
backend/tests/test_api.py::test_api_reviewer_action PASSED
backend/tests/test_api.py::test_api_spend_simulation PASSED
backend/tests/test_api.py::test_api_negative_keywords PASSED
backend/tests/test_api.py::test_api_export_results PASSED
backend/tests/test_api.py::test_api_export_negatives PASSED
backend/tests/test_api.py::test_api_upload_file PASSED
backend/tests/test_triage_engine.py::test_numeric_cleaning_and_zero_distinction PASSED
backend/tests/test_triage_engine.py::test_csv_validation_missing_required_column PASSED
backend/tests/test_triage_engine.py::test_csv_validation_empty_query_rejected PASSED
backend/tests/test_triage_engine.py::test_csv_validation_malformed_numeric_rejected PASSED
backend/tests/test_triage_engine.py::test_low_sample_conversion_anomaly_routed_to_human_review PASSED
backend/tests/test_triage_engine.py::test_zero_conversions_does_not_blindly_trigger_block PASSED
backend/tests/test_triage_engine.py::test_irrelevant_intent_triggers_block PASSED
backend/tests/test_triage_engine.py::test_proven_performer_triggers_promote PASSED
backend/tests/test_triage_engine.py::test_clustering_and_conflict_detection PASSED
backend/tests/test_triage_engine.py::test_csv_injection_sanitization PASSED
backend/tests/test_triage_engine.py::test_reviewer_feedback_persistence PASSED
backend/tests/test_triage_engine.py::test_large_dataset_performance_25k_rows PASSED

============================= 22 passed in 7.86s =============================
```

---

## 📊 Generating Large Datasets (25,000+ Rows)

To test the application at massive scale, run the synthetic dataset generator:
```powershell
.\venv\Scripts\python.exe sample_data/generate_sample_data.py 25000 sample_data/large_25k_search_terms.csv
```
You can then upload `large_25k_search_terms.csv` via the browser drag-and-drop interface.

---

## 🔒 Security & Data Quality

- **Zero API Dependency**: Does not transmit Google Ads queries to external APIs.
- **Formula Injection Safeguards**: All CSV export cells starting with `=`, `+`, `-`, or `@` are sanitized with leading single quotes.
- **Distinguishing Missing Data vs Genuine 0**: Blanks or `N/A` are parsed as missing values rather than assumed to be zero.
- **SQLite Persistence**: Stores reviewer feedback and negative keyword decisions locally in `backend/data/triage_engine.db`.
