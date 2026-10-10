# AdCreative Intelligence

**AdCreative Intelligence** is a B2B SaaS creative analytics workspace built in Python and Streamlit. It connects automated computer vision feature extraction with creative-level statistical inference to help marketing and design teams answer five core questions:

1. **Which advertising creatives perform best?**
2. **Why might some creatives outperform others?**
3. **Which creative characteristics correlate with better results?**
4. **What should the marketing team test next?**
5. **How can the team turn analytical findings into new creative briefs?**

---

## 1. Project Overview

Modern performance marketing teams manage dozens of visual ad variants across channels (`Meta`, `TikTok`, `YouTube`, `Display`), yet creative decisions are frequently based on noisy raw click-through rates or unverified intuition. **AdCreative Intelligence** provides a rigorous, end-to-end analytical workspace that ingests campaign performance CSVs and creative image assets, extracts visual attributes with transparent measurement provenance, runs creative-level statistical hypothesis tests with Benjamini-Hochberg False Discovery Rate (FDR) correction, and synthesizes findings into 14-section creative strategy briefs and structured A/B experiment plans.

---

## 2. Key Features

- **Executive Overview Dashboard**: Primary and secondary KPI cards (`Total Spend`, `Total Conversions`, `Pooled CTR`, `Pooled CPA`, `ROAS` when revenue exists, `Impressions`, `Clicks`, `CPC`, `CVR`), interactive multi-metric time-series trends (`Spend`, `Conversions`, `CTR`, `ROAS`), top-performing creative cards with direct detail navigation, segment distributions (`Campaign`, `Platform`, `Placement`, `Audience`), and a comprehensive **Data Quality Summary** panel.
- **7-Step Guided Data Import & Column Mapper**: Interactive CSV upload, schema validation, custom header mapping (`suggest_column_mapping` & `apply_column_mapping`), multi-format image & `.zip` bundle ingestion, stem-based `ad_id` matching diagnostics, and persistent SQLite workspace storage (`database.py`).
- **Creative Library, Empirical Bayes Scorecard & Multi-Creative Comparison**: Switchable **Visual Grid View** and **Compact Table View**, multi-attribute filtering (`Campaign`, `Platform`, `Placement`, `Audience`, `Color Tone`, `Human Presence`, `Aspect Ratio`, `Composition Style`), **Creative Detail Inspector**, **Empirical Bayes Creative Scorecard** (`build_creative_scorecard`), and **Multi-Creative Side-by-Side Comparison** (`compare_multiple_creatives` for 2+ creatives).
- **Ranked Statistical Findings Workspace**: Evaluates categorical and continuous visual/metadata hypotheses with Welch-Satterthwaite creative-level $t$-tests, Spearman/Pearson correlations, 95% confidence intervals, Benjamini-Hochberg FDR $q$-values, plain-English marketer explanations, and confounding stratification checks.
- **14-Section Creative Brief Generator, Experiment Planner & Explainable Recommendations**: Guided 5-step brief builder with creative format selection, 15-field **Experiment Planner** (`generate_experiment_plan`), and 6-part **Explainable Recommendations** (`what_was_observed`, `supporting_data`, `why_it_matters`, `action_to_test`, `how_to_measure_success`, `remaining_uncertainty`).
- **Export & Reporting Center**: One-click downloads for Performance CSV, Creative Scorecard CSV, Statistical Findings CSV/JSON, Consolidated Analysis Report (Markdown & PDF), Creative Brief (`.md` & `.txt`), Experiment Plan CSV, Data Quality Summary CSV, and Extracted Visual Features CSV.

---

## 3. Architecture

```text
adcreative_intelligence/
├── .streamlit/
│   └── config.toml            # SaaS light neutral theme & typography configuration
├── app.py                     # Six-page Streamlit SaaS application shell & UI workflows
├── data_ingestion.py          # CSV validation, custom column mapping, image matching & data quality audit
├── feature_extraction.py      # Direct pixel geometry/color/luminance, heuristic CV proxies, Haar face cascade
├── statistical_engine.py      # Creative-level Welch t-tests, BH-FDR, Empirical Bayes scorecard & multi-ad comparison
├── recommendations.py         # 6-part explainable recommendations, 15-field experiment planner & PDF report builder
├── creative_brief.py          # 14-section deterministic creative strategy brief & export formatters
├── database.py                # SQLite persistent storage for workspaces, metrics, features, findings & briefs
├── synthetic_data.py          # Deterministic 18-ad synthetic demonstration dataset generator
├── test_pipeline.py           # 34 automated unit & pipeline integration tests
├── demo_assets/               # Pre-generated synthetic demo dataset (.csv + 18 .png creative assets)
├── requirements.txt           # Python package dependencies
└── README.md                  # Technical documentation
```

---

## 4. Installation Steps

### Prerequisites
- Python 3.10 or 3.11+

### Install Required Packages
```bash
pip install -r requirements.txt
```

---

## 5. How to Run the App

Start the Streamlit web application from the project root directory:

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 6. How to Run Tests

Execute the complete automated unit and integration test suite (34 tests):

```bash
python test_pipeline.py -v
```

---

## 7. CSV Schema

### Required Columns
| Column | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `ad_id` | String | Unique creative identifier | Non-empty, unique per creative (or aggregated across dates if `date` is provided) |
| `spend` | Float | Total ad spend (`$`) | Numeric, finite, $\ge 0$ |
| `impressions` | Integer/Float | Total ad impressions | Numeric, finite, $\ge 0$ |
| `clicks` | Integer/Float | Total clicks | Numeric, finite, $\ge 0$, must satisfy $\text{clicks} \le \text{impressions}$ |
| `conversions` | Integer/Float | Total conversions | Numeric, finite, $\ge 0$, must satisfy $\text{conversions} \le \text{clicks}$ (unless View-Through Conversions are enabled) |

### Supported Optional Columns
- `campaign` / `campaign_name`, `campaign_id`, `audience`, `placement`, `platform`, `date`, `revenue` / `conversion_value`, `variant`.
- If custom CSV headers are used (e.g., `Creative ID`, `Amount Spent`, `Link Clicks`, `Purchases`), **Step 3** of **Upload Creatives** provides an interactive column mapper to map them to the required schema without editing the file externally.

---

## 8. Image Matching Rules

- Supported image formats: `.png`, `.jpg`, `.jpeg`, `.webp` (plus `.zip` archives containing images).
- Matching is performed deterministically by comparing normalized file stems against `ad_id`:
  1. Exact match on filename or stem (`ad_warm_01.png` $\rightarrow$ `ad_warm_01`).
  2. Case-insensitive stem match (`AD_WARM_01.JPG` $\rightarrow$ `ad_warm_01`).
  3. Normalized alphanumeric stem match stripping spaces, hyphens, underscores, and browser duplicate suffixes (`ad-warm-01 (1).webp` $\rightarrow$ `ad_warm_01`).
- Unmatched CSV records (`unmatched_records`) and unmatched uploaded images (`unmatched_images`) are surfaced explicitly with full diagnostic tables; no records are ever silently dropped.

---

## 9. Extracted Features

Every extracted visual attribute is tagged with its measurement provenance in `FEATURE_PROVENANCE_MAP`:

1. **Direct Image Measurements**:
   - **Geometry & Format**: `width`, `height`, `megapixels`, `aspect_ratio`, `aspect_ratio_cat` (`1:1 Square`, `4:5 Vertical Feed`, `9:16 Portrait / Story`, `16:9 Landscape`), `format_suitability`.
   - **Color & Palette**: `dominant_color_rgb`, `dominant_color_hex`, `dominant_color_name`, `dominant_color_tone` (`Warm`, `Cool`, `Neutral`), `pct_warm_pixels`, `pct_cool_pixels`, `pct_neutral_pixels`, and `color_palette_distribution` (Top-3 RGB K-Means clusters).
   - **Luminance, Contrast & Colorfulness**: `brightness_score` & `brightness_cat` (ITU-R BT.601 luminance mean), `contrast_score` & `contrast_cat` (RMS luminance standard deviation), `colorfulness_score` & `colorfulness_cat` (Hasler & Süsstrunk opponent-color metric), `saturation_score` (HSV saturation mean).
2. **Heuristic Computer Vision Proxies**:
   - **Edge Complexity**: `edge_density_pct`, `visual_complexity` (Canny 100/200 edge-pixel density).
   - **Text / Copy Density Proxy**: `text_density_score`, `text_density_cat` (Morphological horizontal Sobel stroke-width filter estimating percentage of image area with text-like strokes — *explicitly labeled as a heuristic proxy, not OCR*).
   - **Visual Composition & Saliency**: `composition_style`, `rule_of_thirds_score`, `center_focus_ratio`, `visual_symmetry_score`, `detected_object_regions`, `primary_subject_coverage_pct`, `object_presence_cat`.
3. **Pretrained Frontal Face Cascade Detection**:
   - `face_count`, `has_human_presence`, `face_area_ratio`, `human_presence_cat` via OpenCV Haar Frontal Face Cascades (`haarcascade_frontalface_default.xml` & `haarcascade_frontalface_alt2.xml`).

---

## 10. Calculated Metrics

### Ad-Level Derived Metrics
For each creative $i$, zero denominators safely yield `NaN` (`Undefined / Unavailable`) rather than raising errors or fabricating zeros:
$$\text{CTR}_i = \frac{\text{clicks}_i}{\text{impressions}_i}, \quad \text{CVR}_i = \frac{\text{conversions}_i}{\text{clicks}_i}, \quad \text{CPC}_i = \frac{\text{spend}_i}{\text{clicks}_i}, \quad \text{CPA}_i = \frac{\text{spend}_i}{\text{conversions}_i}, \quad \text{ROAS}_i = \frac{\text{revenue}_i}{\text{spend}_i}$$

### Campaign-Level Pooled Metrics vs. Unweighted Ad-Level Distributions
`compute_aggregate_kpis()` computes both **Pooled Campaign Ratios** ($\sum \text{clicks} / \sum \text{impressions}$, etc.) and **Unweighted Ad-Level Means & Medians** across creatives.

---

## 11. Statistical Methods

- **Creative-Level Unit of Replication**: Categorical comparisons (`analyze_categorical_attribute`) treat the **creative (`ad_id`) as the unit of replication** using two-sided Welch-Satterthwaite $t$-tests, Student's $t$ 95% confidence intervals, Mann-Whitney $U$ tests, and Cohen's $d$, preventing impression-level pseudoreplication.
- **Continuous Associations**: Evaluated via Spearman rank correlation ($\rho$), Pearson correlation ($r$) with Fisher $z$ 95% confidence intervals, and exposure-weighted WLS / unweighted OLS slopes.
- **Multiple-Testing Control**: Benjamini-Hochberg False Discovery Rate ($q_{\text{FDR}}$) and Bonferroni corrections applied across all tested hypotheses.
- **Evidence Tiers**:
  - `Supported association` ($q_{\text{FDR}} < 0.05$, $N \ge 4$ per group, 95% CI excludes zero, $|\text{Uplift}| \ge 8\%$)
  - `Preliminary` ($p < 0.05$ or $q_{\text{FDR}} < 0.15$ with $|\text{Uplift}| \ge 10\%$ and $N \ge 3$)
  - `Underpowered` ($N < 3$ per group or $N < 6$ continuous)
  - `No clear association` / `Unsupported` ($p \ge 0.10$)
- **Empirical Bayes Creative Scorecard (`build_creative_scorecard`)**: Ranks creatives using shrinkage-adjusted CTR ($40\%$), CVR ($35\%$), and CPA efficiency ($25\%$) alongside 95% Wilson score confidence intervals.

---

## 12. Recommendation and Brief Logic

- **6-Part Explainable Recommendations (`generate_recommendations`)**: Every recommendation explicitly documents `what_was_observed`, `supporting_data`, `why_it_matters`, `action_to_test`, `how_to_measure_success`, and `remaining_uncertainty`.
- **15-Field Experiment Planner (`generate_experiment_plan`)**: Generates structured split-test specifications with control vs. variant concepts, single isolated variable, minimum sample size for 80% power ($\alpha = 0.05$), measurement period guidance, and decision criteria.
- **14-Section Creative Strategy Brief (`generate_creative_brief`)**: Synthesizes active findings deterministically into 14 structured brief sections. When no statistically supported findings exist, the brief explicitly discloses that recommendations are based on general creative suggestions rather than confirmed performance findings.

---

## 13. Export Options

All exports are available in **6. Export Center**:
1. **Validated Creative Performance Summary (`validated_performance_metrics.csv`)**
2. **Empirical Bayes Creative Scorecard (`creative_ranking_scorecard.csv`)**
3. **Ranked Statistical Findings (`ranked_statistical_findings.csv` & `.json`)**
4. **Consolidated Creative Analysis Report (`consolidated_adcreative_report.md` & `executive_analytical_report.pdf`)**
5. **14-Section Creative Brief (`executive_creative_brief.md` & `executive_creative_brief.txt`)**
6. **Structured Experiment Plan (`creative_experiment_plan.csv`)**
7. **Data Quality Summary (`data_quality_summary.csv`)**
8. **Extracted Visual Features & Enriched Dataset (`extracted_creative_features.csv` & `enriched_ad_performance_and_features.csv`)**

---

## 14. Limitations

- **Observational Data vs. Causality**: Observational associations between visual attributes and campaign metrics do not prove causation and may be confounded by audience targeting, placement, bidding strategy, or seasonal timing. Causal inference requires a controlled split-test isolating a single creative variable.
- **Computer Vision Proxies**: Text density and composition metrics are deterministic morphological/gradient proxies, not OCR or semantic deep-learning object detectors. Pretrained Haar cascades detect frontal human faces only.
- **Synthetic Demo Watermarking**: When the built-in 18-ad demo dataset is active, all UI views and exported files are explicitly watermarked `DEMO DATA — SYNTHETIC EXAMPLE`.
