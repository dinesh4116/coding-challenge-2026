# AdCreative Intelligence (PS-02)

**AdCreative Intelligence** is an evidence-based visual advertising intelligence application built in Python and Streamlit. It connects automated computer vision feature extraction with creative-level statistical inference to help marketing and design teams understand which visual attributes are associated with advertising performance (**CTR, CVR, CPC, CPA**) while maintaining strict scientific honesty against spurious causal claims or ungrounded AI assertions.

---

## 1. Project Overview & Architecture

```text
adcreative_intelligence/
├── app.py                     # Five-page interactive Streamlit web application
├── data_ingestion.py          # CSV schema validation, logical bounds checks, stem-based image matching
├── feature_extraction.py      # Direct pixel measurements, heuristic CV proxies, Haar frontal face cascade
├── statistical_engine.py      # Creative-level Welch-Satterthwaite t-tests, WLS/OLS, Spearman/Pearson, FDR
├── creative_brief.py          # Data-grounded creative brief generator, A/B test matrix & export builders
├── synthetic_data.py          # Labeled 18-ad synthetic demonstration dataset generator
├── test_pipeline.py           # 25 automated unit & integration tests
├── demo_assets/               # Pre-generated synthetic demonstration dataset (.csv + 18 .png creatives)
├── requirements.txt           # Python package dependencies
└── README.md                  # Technical documentation
```

---

## 2. Installation & Launch Instructions

### Prerequisites
- Python 3.11+

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch the Web Application
```bash
streamlit run app.py
```
*(On Windows with Python 3.11 installed in the user profile: `& "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run app.py`)*

Open `http://localhost:8501` in your browser.

---

## 3. Expected CSV Schema & Validation Rules

### Required Columns
| Column | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `ad_id` | String | Unique creative identifier | Non-empty, no duplicate `ad_id` values |
| `spend` | Float | Total ad spend (`$`) | Numeric, finite, $\ge 0$ |
| `impressions` | Integer/Float | Total ad impressions | Numeric, finite, $\ge 0$ |
| `clicks` | Integer/Float | Total clicks | Numeric, finite, $\ge 0$, must satisfy $\text{clicks} \le \text{impressions}$ |
| `conversions` | Integer/Float | Total conversions | Numeric, finite, $\ge 0$, must satisfy $\text{conversions} \le \text{clicks}$ (unless View-Through Conversions are explicitly enabled) |

### Optional Confounder Metadata Columns
- `campaign_name`, `campaign_id`, `audience`, `placement`, `platform` (automatically ingested and used for confounding/clustering stratification checks).

### Audit & Zero-Silent-Discard Guarantee
- Invalid CSV rows (missing values, non-numeric text, negative numbers, duplicate IDs, $\text{clicks} > \text{impressions}$, or $\text{conversions} > \text{clicks}$) halt ingestion with row-level diagnostic errors.
- Zero denominators (`0 impressions`, `0 clicks`, `0 conversions`), fractional counts, and `spend > 0` with `0 impressions` are flagged with explicit warnings while preserving valid records.
- Statistical comparisons strictly exclude corrupted or unmatched records (`extraction_status != "success"`).

---

## 4. Image Naming & Matching Rules

- Supported image formats: `.png`, `.jpg`, `.jpeg`, `.webp` (including `RGB`, `RGBA` transparent, `P` palette, and `L` grayscale modes).
- Matching is performed deterministically by comparing normalized file stems against `ad_id`:
  1. Exact match on filename or stem (`ad_01.png` $\rightarrow$ `ad_01`).
  2. Case-insensitive stem match (`AD_01.JPG` $\rightarrow$ `ad_01`).
  3. Normalized alphanumeric stem match (stripping spaces, hyphens, and underscores).
- Both **CSV records missing images** (`unmatched_records`) and **orphan uploaded images missing CSV records** (`unmatched_images`) are reported in the Data Ingestion & Matching Audit table.

---

## 5. Extracted Creative Features & Explicit Provenance

Every extracted feature is tagged with its exact measurement provenance in `FEATURE_PROVENANCE_MAP` so that basic image processing is never misrepresented as semantic AI:

1. **Direct Image Measurements**:
   - **Geometry & Format**: `width`, `height`, `megapixels`, `aspect_ratio`, `aspect_ratio_cat` (`1:1 Square`, `4:5 Vertical Feed`, `9:16 Portrait / Story`, `16:9 Landscape`), `format_suitability`.
   - **Color & Tone Distribution**: `dominant_color_rgb`, `dominant_color_hex`, `dominant_color_name`, `dominant_color_tone` (`Warm`, `Cool`, `Neutral`), `pct_warm_pixels`, `pct_cool_pixels`, `pct_neutral_pixels`, and `color_palette_distribution` (Top-3 RGB K-Means palette shares).
   - **Luminance, Contrast & Colorfulness**: `brightness_score` & `brightness_cat` (ITU-R BT.601 luminance mean), `contrast_score` & `contrast_cat` (RMS luminance standard deviation), `colorfulness_score` & `colorfulness_cat` (Hasler & Süsstrunk opponent-color metric), `saturation_score` (HSV saturation mean).
2. **Heuristic Estimates (Not OCR / Not Semantic Object Detection)**:
   - **Edge Complexity**: `edge_density_pct`, `visual_complexity` (Canny 100/200 edge-pixel percentage).
   - **Text / Copy Density Proxy**: `text_density_score`, `text_density_cat` (Morphological horizontal Sobel stroke-width filter estimating percentage of image area with text-like strokes — *explicitly labeled as a heuristic proxy, NOT Optical Character Recognition*).
   - **Visual Composition & Saliency Contours**: `composition_style`, `rule_of_thirds_score`, `center_focus_ratio`, `visual_symmetry_score`, `detected_object_regions`, `primary_subject_coverage_pct`, `object_presence_cat` (Sobel gradient energy distribution and Otsu thresholded contours — *explicitly labeled as a heuristic estimate, NOT semantic object detection*).
3. **Pretrained Frontal Face Cascade Detection (Frontal Faces Only)**:
   - `face_count`, `has_human_presence`, `face_area_ratio`, `human_presence_cat` using OpenCV Pretrained Haar Frontal Face Cascades (`haarcascade_frontalface_default.xml` & `haarcascade_frontalface_alt2.xml`). *Explicitly documented as detecting frontal human faces only, not full-body poses or non-frontal profiles.*
4. **Explicitly Unavailable Capabilities**:
   - `ocr_text_extraction`, `semantic_object_detection`, `comprehensive_human_body_detection`, and `brand_logo_recognition` are explicitly marked as `Unavailable` in `unavailable_features`.

---

## 6. Calculated Performance Metrics

### Ad-Level Metrics
For each creative $i$, zero denominators safely yield `NaN` (`Undefined`):
$$\text{CTR}_i = \frac{\text{clicks}_i}{\text{impressions}_i}, \quad \text{CVR}_i = \frac{\text{conversions}_i}{\text{clicks}_i}, \quad \text{CPC}_i = \frac{\text{spend}_i}{\text{clicks}_i}, \quad \text{CPA}_i = \frac{\text{spend}_i}{\text{conversions}_i}$$

### Campaign-Level Pooled Metrics vs. Unweighted Ad-Level Distributions
`compute_aggregate_kpis()` calculates and displays **both**:
1. **Campaign-Level Pooled Metrics** (weighted by exposure volume):
   $$\text{Pooled CTR} = \frac{\sum \text{clicks}_i}{\sum \text{impressions}_i}, \quad \text{Pooled CVR} = \frac{\sum \text{conversions}_i}{\sum \text{clicks}_i}, \quad \text{Pooled CPC} = \frac{\sum \text{spend}_i}{\sum \text{clicks}_i}, \quad \text{Pooled CPA} = \frac{\sum \text{spend}_i}{\sum \text{conversions}_i}$$
2. **Unweighted Ad-Level Mean & Median Metrics** (`mean_ad_ctr`, `median_ad_ctr`, `mean_ad_cvr`, `median_ad_cvr`, `mean_ad_cpc`, `median_ad_cpc`, `mean_ad_cpa`, `median_ad_cpa`), treating each creative as an equal weight ($1/N$).

---

## 7. Statistical Methodology & Limitations

- **Unit of Replication (Avoiding Impression-Level Pseudoreplication)**:
  - Impressions and clicks are clustered within creatives (`ad_id`), not independent experimental units. Treating millions of impressions as independent Bernoulli trials in a naive two-proportion $z$-test severely understates standard errors when there is between-ad heterogeneity.
  - Categorical group comparisons (`analyze_categorical_attribute`) therefore treat the **creative (`ad_id`) as the unit of replication**, computing two-sided Welch-Satterthwaite $t$-tests and Student's $t$ 95% confidence intervals across ad-level metrics alongside nonparametric Mann-Whitney $U$ checks and Cohen's $d$, while reporting pooled campaign rates and exposure counts alongside ad-level means.
  - When a group has fewer than 2 creatives ($n_A < 2$ or $n_B < 2$), inferential $p$-values are not fabricated; the comparison is marked `"Descriptive Comparison Only (Insufficient Creatives n < 2 for Ad-Level Inference)"` and classified as `Underpowered`.
- **Continuous Associations**:
  - Evaluated via nonparametric Spearman rank correlation ($\rho$), Pearson linear correlation ($r$) with Fisher $z$-transform 95% confidence intervals, and exposure-weighted WLS / unweighted OLS regression slopes.
- **Multiple-Testing Correction**:
  - All tested hypotheses are jointly adjusted using the **Benjamini-Hochberg False Discovery Rate (FDR)** procedure ($q$-values) and **Bonferroni** correction.
- **Observational Non-Causality**:
  - All findings explicitly state that associations are observational and may be confounded by audience targeting, placement, bid strategy, or budget allocation.

---

## 8. Evidence Classification Rules & Ranking Formula

Every finding is classified into one of five transparent evidence tiers:
- 🟢 **Supported association**: Benjamini-Hochberg adjusted $q_{\text{FDR}} < 0.05$, minimum group sample size $N \ge 4$ creatives per group (or $N \ge 6$ for continuous), 95% confidence interval excludes zero, and relative effect $\ge 8\%$ (or $|\rho| \ge 0.40$).
- 🟡 **Preliminary**: Nominal $p < 0.05$ before multiple-testing correction, OR $q_{\text{FDR}} < 0.15$ with relative effect $\ge 10\%$ and $N \ge 3$ per group.
- 🟣 **Underpowered**: Creative sample size $N < 3$ in at least one group (or $N < 6$ total for continuous).
- ⚪ **No clear association**: Adequate sample size ($N \ge 5$ per group), negligible effect size ($|\text{Uplift}| < 6\%$ or $|\rho| < 0.15$), and $p > 0.20$. *(Includes reminder: absence of evidence is not evidence of absence).*
- 🔴 **Unsupported**: Non-significant ($p \ge 0.10$) with insufficient evidence.

Findings are ordered by a documented composite score:
$$\text{Rank Score} = \left(0.50 \cdot \min(-\log_{10}(q_{\text{FDR}} + 10^{-8}), 6.0) + 0.35 \cdot \min\left(\frac{|\text{Uplift}\%|}{15.0}, 4.0\right) + 0.15 \cdot \min(\sqrt{N}, 4.0)\right) \times M_{\text{tier}}$$

---

## 9. Creative Brief Generation Logic & Exports

`generate_creative_brief()` synthesizes active statistical findings with zero hardcoded claims:
- Separates **Confirmed Statistical Associations (`Supported association`)** from **Exploratory Hypotheses (`Preliminary` / `Underpowered`)** and **Null / Cautionary Contrasts (`No clear association` / `Unsupported`)**.
- Generates a prioritized **A/B Test Experimental Matrix** with control/variant definitions, primary KPIs, and minimum sample size estimates for 80% statistical power at $\alpha = 0.05$.
- Supports one-click exports across the application:
  - Validated Performance Metrics (`validated_performance_metrics.csv`)
  - Extracted Creative Features (`extracted_creative_features.csv`)
  - Enriched Performance + Features Dataset (`enriched_ad_performance_and_features.csv`)
  - Ranked Statistical Findings (`ranked_statistical_findings.csv` & `.json`)
  - Executive Creative Brief (`executive_creative_brief.md` & `ab_test_experimental_matrix.csv`)
  - Consolidated Project Report (`consolidated_adcreative_report.md`)

---

## 10. Test Execution Instructions

Run the complete automated test suite (25 unit and pipeline integration tests):
```bash
python test_pipeline.py -v
```
*(Or on Windows with Python 3.11: `& "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" test_pipeline.py -v`)*
