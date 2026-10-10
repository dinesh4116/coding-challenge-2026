# QueryPilot — PS-01: Search Term Triage Engine

QueryPilot is a full-stack statistical search term triage engine and forensic intelligence platform for paid search optimization. Built with a **React + TypeScript (Vite)** frontend styled in the **PlacementOS** enterprise design system, powered by a high-performance **FastAPI backend** and a rigorous deterministic Python statistical engine (`SciPy`, `numpy`, `pandas`).

> **Dataset Status Notice:** The organizers' official CSV dataset has **not** been received or bundled in this repository. All sample outputs and pre-loaded examples in `data/sample_synthetic.csv` are explicitly labeled **`SYNTHETIC`** and are used strictly to test statistical edge cases. Do not treat synthetic sample results as official dataset claims.

---

## 1. Quick Start

### Option A: Modern Web Application (React + FastAPI) [Recommended]

1. **Install Backend Dependencies & Start FastAPI**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip.exe install -r requirements.txt fastapi uvicorn python-multipart httpx
   .\.venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Install Frontend Dependencies & Start Vite**:
   ```bash
   npm install
   npm run dev
   ```

3. Open **`http://localhost:3000`** in your browser. (FastAPI docs available at `http://127.0.0.1:8000/docs`).

### Option B: Streamlit Standalone Interface
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### Option C: Run Automated Tests
```powershell
.\.venv\Scripts\pytest.exe -v
```
*(31 tests passed covering statistical formulas, edge cases, workflow anomalies, and API endpoints).*

### Option D: Deploy to Vercel (Production Ready)

QueryPilot is fully pre-configured for zero-friction Vercel deployment:
- **Frontend SPA**: React 19 + TypeScript + Vite compiled to optimized static assets (`dist`).
- **Backend API**: Python Serverless Function (`api/index.py`) serving the FastAPI triage endpoints (`/api/preview`, `/api/analyze`, `/api/export`, `/api/health`).
- **Client Mirror Fallback**: `src/triageEngine.ts` automatically runs statistical calculations client-side if serverless cold-start or offline conditions occur.

#### Method 1: Vercel Dashboard (Recommended)
1. Push repository changes to GitHub.
2. In the [Vercel Dashboard](https://vercel.com/new), click **Import Project** and select `MohamedKaish/QueryPilot`.
3. Vercel automatically detects the preset settings from `vercel.json`:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `./`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Click **Deploy**.

#### Method 2: Vercel CLI
```bash
# Preview deployment
npx vercel

# Production deployment
npx vercel --prod
```

---

## 2. Project Structure

```text
api/index.py                # Vercel Serverless Function entrypoint (FastAPI)
api/requirements.txt        # Serverless Python dependencies (FastAPI, SciPy, pandas, numpy)
vercel.json                 # Vercel deployment routing (API serverless + Vite SPA rewrites)
.vercelignore               # Vercel asset bundle exclusion rules
server.py                   # FastAPI backend server with REST endpoints
src/App.tsx                 # PlacementOS React triage application
src/triageEngine.ts         # High-precision TypeScript client mirror of statistical engine
src/demoDatasets.ts         # Benchmark datasets (4 real-world test cases)
app.py                      # Streamlit UI (upload, schema mapping, quality report, thresholds, export)
triage/__init__.py          # Package exports
triage/init.py              # Compatibility alias
triage/config.py            # Configurable heuristic thresholds and column mapping schema
triage/loader.py            # Flexible CSV parser, schema profiler, and anomaly detector
triage/stats.py             # Wilson CI, exact binomial tails (SciPy), BH FDR adjustment, LOO shrinkage
triage/engine.py            # Deterministic row-by-row triage engine (PROMOTE / BLOCK / IGNORE)
triage/export.py            # Deterministic filtering, sorting, and CSV serialization
tests/test_stats.py         # Unit tests for Wilson interval, binomial tails, BH FDR, and shrinkage (9 tests)
tests/test_engine.py        # Acceptance tests (2-click/1-conv trap, costly 0-conv block, winner, edge cases) (5 tests)
tests/test_app_workflow.py  # End-to-end integration & workflow acceptance tests (12 tests)
tests/test_api_integration.py # Integration tests for FastAPI endpoints (5 tests)
data/sample_synthetic.csv   # Clearly labeled SYNTHETIC dataset covering all statistical & anomaly cases
requirements.txt            # Production Python dependencies
requirements-dev.txt        # Development dependencies (pytest, Streamlit)
README.md                   # Documentation, methodology, and statistical/operational limitations
```

---

## 3. Methodology & Statistical Pipeline

Every input row receives **exactly one** deterministic decision (`PROMOTE`, `BLOCK`, or `IGNORE`), a one-line numerical reason, a decision-support confidence tier, a boolean `review_flag`, and explicit `quality_flags`.

### A. Leave-One-Out (LOO) Empirical Bayes Shrunk Baseline
To evaluate whether a search term converts significantly better or worse than expected without allowing a high-volume term to distort its own benchmark:
1. **Account LOO Baseline ($\text{CVR}_{\text{acct}, -i}$):** Computed across all non-anomalous rows in the dataset **excluding** row $i$'s clicks and conversions.
2. **Campaign LOO Baseline ($\text{CVR}_{c, -i}$):** Computed across all non-anomalous rows in row $i$'s campaign **excluding** row $i$'s clicks and conversions.
3. **Empirical Bayes Shrinkage ($p_{0, i}$):** Shrunk toward the account LOO baseline with configurable credibility weight $k$ (`shrinkage_k = 100` clicks by default):
   $$p_{0, i} = \frac{N_{c, -i} \cdot \text{CVR}_{c, -i} + k \cdot \text{CVR}_{\text{acct}, -i}}{N_{c, -i} + k}$$

### B. Exact Binomial Tails, Wilson Interval, and Benjamini–Hochberg Adjustment
- **Wilson Confidence Interval (`wilson_interval`):** Computes the $(1 - \alpha)$ Wilson score interval for observed conversion rate $\hat{p}_i = \text{conversions}_i / \text{clicks}_i$.
- **Exact One-Sided Binomial Tests (`exact_binomial_tails` via `scipy.stats.binom`):**
  - Upper tail $p_{\text{upper}} = P(X \ge \lfloor x_i \rfloor \mid n_i, p_{0, i})$ tests for outperformance (`PROMOTE`).
  - Lower tail $p_{\text{lower}} = P(X \le \lceil x_i \rceil \mid n_i, p_{0, i})$ tests for underperformance (`BLOCK`).
- **Benjamini–Hochberg Adjustment (`benjamini_hochberg`):** Controls the False Discovery Rate (FDR) across tested candidate families to produce $q_{\text{upper}}$ and $q_{\text{lower}}$.

### C. Decision Rules & Heuristic Defaults
Default parameters (`alpha = 0.05`, `shrinkage_k = 100`, `min_test_clicks = 10`, `min_promote_conversions = 2.0`, `block_cost_cpa_multiplier = 1.0`) are **operational heuristics, not universal truths**:
- **Hard Single-Conversion Guardrail:** A search term with fewer than `2` conversions is **never** promoted (`PROMOTE` is strictly forbidden when `conversions < 2`), preventing the classic **2-click / 1-conversion (50% CVR) small-sample trap**.
- **`PROMOTE`:** Requires no fatal data anomalies, `clicks >= min_test_clicks`, `conversions >= max(2, min_promote_conversions)`, `observed_cvr > shrunk_baseline_cvr`, and statistical significance at `alpha`.
- **`BLOCK`:** Requires no fatal data anomalies, `clicks >= min_test_clicks`, `cost >= block_cost_cpa_multiplier * account_cpa`, `observed_cvr < shrunk_baseline_cvr`, and lower-tail significance at `alpha`.
- **`IGNORE`:** Assigned to all rows with insufficient click volume, baseline-consistent conversion rates, below-gate spend, or fatal data anomalies (which are flagged for human review rather than silently concealed).

---

## 4. Documented Statistical & Operational Limitations

1. **Confidence Tiers Are Not Calibrated Probabilities:**
   Labels such as `Tier 1: High (FDR & CI Confirmed)`, `Tier 2: Medium`, and `Tier 3: Low` are deterministic decision-support categories—**never** interpret or report them as "90% likely correct."
2. **No Ground-Truth Accuracy Claims:**
   Search term triage lacks ground-truth labels for unobserved counterfactual future performance. We do not claim classification accuracy, precision, or recall.
3. **In-Sample Empirical Baseline Estimation & Multiple Testing:**
   Baselines ($\text{CVR}_{c, -i}$ and $\text{CVR}_{\text{acct}, -i}$) are estimated from the same uploaded dataset rather than an independent historical holdout. While leave-one-out subtraction removes direct self-influence and Benjamini–Hochberg adjusts for multiple comparisons across tested rows, uncertainty in the baseline itself is not propagated into a full hierarchical posterior.
4. **Independence Assumptions vs. Repeat Users / Auctions:**
   The binomial model treats clicks as independent Bernoulli trials with constant conversion probability $p_{0,i}$. In real ad auctions, repeat clicks by the same user, time-of-day effects, device mix, and ad rank shifts violate strict i.i.d. assumptions.
5. **Conversion Lag (Attribution Delay):**
   Recent clicks may have conversions that have not yet been recorded due to attribution windows (e.g., 7-day or 30-day B2B sales cycles). Running triage on very recent date ranges can bias conversion rates downward and over-trigger `BLOCK` recommendations.
6. **Fractional Conversions Handling:**
   Data-driven or multi-touch attribution often produces fractional conversions (e.g., `1.6` or `9.4`). Because the exact binomial distribution is discrete, `triage/stats.py` uses continuous $\hat{p} = x/n$ in the Wilson interval and conservative integer bounding in exact binomial tails ($\lfloor x \rfloor$ for upper-tail promotion tests, $\lceil x \rceil$ for lower-tail block tests) and flags all fractional rows (`FRACTIONAL_CONVERSIONS`, `review_flag = True`).
7. **Conversion Value Is Informational Only:**
   The `conversion_value` column is preserved for human inspection in the UI and CSV export, but automated triage decisions are driven strictly by click/conversion volume, CVR, and CPA cost gates so a single outlier order value cannot hijack statistical significance.
8. **Missing Semantic Relevance Checks & Unknown Existing-Keyword Status:**
   This MVP uses purely numerical performance signals. It does not inspect semantic intent, brand safety, landing-page alignment, or whether a `PROMOTE` search term already exists as a targeted keyword in the account.
9. **Out of Scope for MVP:**
   Campaign vs. ad-group negative keyword placement routing, near-duplicate n-gram clustering, and interactive reviewer feedback loops are intentionally excluded from this MVP.
