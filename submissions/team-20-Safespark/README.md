# 🚀 BigBoost AI — Ad-to-Landing-Page Message Match Auditor & CRO Intelligence Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![Google Gemini API](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash-4285F4.svg)](https://ai.google.dev/)
[![Enterprise Grade](https://img.shields.io/badge/Compliance-FTC%20%7C%20CFPB%20%7C%20FDA-2E7D32.svg)]()
[![Design System](https://img.shields.io/badge/Theme-Pure%20White%20%7C%20Fresh%20Green-2E7D32.svg)]()

> **Enterprise-Grade AI Audit Engine by BigBoost AI**  
> Protect PPC advertising budgets, eliminate conversion friction, enforce statutory regulatory compliance, and automate landing page copy optimization with zero hallucination.

---
live demo link : https://ad-to-landinggit-dgsbvja6emfjarvt7a8veu.streamlit.app/

## 🌟 Executive Overview

In performance marketing, a disconnect between the search ad promise and the destination landing page copy causes immediate user bounce, destroys Google Ads Quality Scores, inflates Cost-Per-Click (CPC), and in regulated verticals, triggers severe regulatory enforcement and ad account bans.

**BigBoost AI's Message Match Auditor** solves this with an enterprise-grade auditing engine powered by **Google Gemini 3.5**. It audits search ad copy against live or snapshot landing pages, verifies every single claim with programmatic anti-hallucination checks, quantifies financial ad spend leakage, flags statutory compliance exposure, and generates instant one-click copy fixes.

---

## ⚡ Core Feature Matrix

### 1. 🌐 Real-Time Live URL Fetching with Anti-Bot & JS Hydration
* **Anti-Bot & WAF Protection Bypass**: Emulates modern Chrome 124 desktop headers (`Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, session cookies, and Google search referrer) to bypass Cloudflare, PerimeterX, and AWS WAF blocks.
* **Modern JavaScript Hydration Recovery**: Recursively parses client-side rendered Single Page Applications (SPAs) and hydration scripts:
  * **Next.js**: Deep JSON parsing of `__NEXT_DATA__` state props.
  * **Nuxt.js**: State parsing of `__NUXT_DATA__`.
  * **Schema.org**: Ingests `application/ld+json` for pricing, guarantees, and offers.
* **Interactive Live Browser Mockup**: Injects `<base href="...">` tags dynamically so live CSS stylesheets, web fonts, and CDN images load seamlessly inside the interactive preview, bypassing cross-origin `X-Frame-Options: DENY` and CSP blocks.
* **Dual Ingestion Mode**: Choose between real-time live URL scraping or pre-cached offline snapshot files (60 built-in pairs).

---

### 2. ⚖️ Regulated Category Compliance Exposure Engine
Detects deceptive advertising and statutory compliance exposure when ad copy claims are unsubstantiated on destination landing pages (`page_quote: "NONE"`).

* **8 Regulated Vertical Registries**:
  1. **Financial Services & Banking**: CFPB, FTC, Truth in Lending Act (TILA / Regulation Z), Dodd-Frank Act.
  2. **Personal Loans & Mortgages**: Regulation Z (12 CFR § 1026.24), Equal Credit Opportunity Act (ECOA), Google Personal Loans Policy.
  3. **Insurance & Annuities**: State Insurance Commissioners (NAIC), FTC, CMS Marketing Guidelines.
  4. **Healthcare, Medical & Telehealth**: FDA, FTC Health Products Guidance, HIPAA.
  5. **Pharmaceuticals & Supplements**: FDA, FTC Act Section 5, DSHEA Act.
  6. **Legal Services & Attorneys**: State Bar Associations, ABA Model Rule 7.1.
  7. **Cryptocurrency & Web3 Investments**: SEC, CFTC, FinCEN, FTC Act Section 5.
  8. **Higher Education & Vocational Training**: U.S. Dept. of Education, FTC 16 CFR Part 254.
* **High-Visibility Compliance Alerts**: Surfaced when ads promise rates, speeds, or guarantees absent from the landing page.
* **Risk Tiering**: Highlights critical ad disapproval and Google Ads account suspension risks.
* **Dedicated Compliance Exposure Tab**: Provides detailed statutory authorities, governing bodies, uncorroborated claims breakdown, and legal remediation steps.

---

### 3. 🛡️ Programmatic Zero-Hallucination Guard
* **Deterministic Verification Engine**: Every cited `page_quote` from the AI is programmatically cross-referenced against the raw landing page DOM text in Python.
* **4-State Evidence Taxonomy**:
  * `✅ VERIFIED`: Verbatim quote confirmed in landing page text.
  * `🚨 HALLUCINATED`: Warning flagged if quoted text does not exist on the page.
  * `ℹ️ OMISSION_NOTED ('NONE')`: Confirms the ad promise is completely missing from the page.
  * `⚪ EMPTY`: No quote cited.
* **Above-The-Fold (Hero) Detection**: Determines whether the verified proof appears in the top Hero viewport or is buried deep below the fold.

---

### 4. 💰 Dynamic Financial Wasted Spend Calculator
Quantifies the exact monthly and annualized PPC ad budget exposure resulting from message match disconnects:

$$\text{Monthly Wasted Spend} = \text{Monthly Ad Spend} \times \left(\frac{100 - \text{Match Score}}{100}\right)$$

$$\text{Annualized Budget Loss} = \text{Monthly Wasted Spend} \times 12$$

* **Interactive Budget Slider**: Adjust monthly PPC budgets from $100 to $2,000,000.
* **CRO Risk Tiering**:
  * 🔴 **Critical Risk (<50% Score)**: High immediate bounce friction; severe budget leakage.
  * 🟠 **Moderate Risk (50–80% Score)**: Partial message alignment; optimization will lift conversion rate.
  * 🟢 **Low Risk (>80% Score)**: Efficient budget utilization; high message symmetry.

---

### 5. 🏆 Conversion Rate Optimization (CRO) Risk Leaderboard (Bulk Audits)
* **Simultaneous Portfolio Auditing**: Audit multiple campaigns (5, 10, 20, or all 60 campaigns) in a single click with real-time progress tracking.
* **Prioritized Risk Ranking**: Automatically ranks campaigns by lowest match score first to immediately isolate the **Top Critical Risk Campaigns**.
* **Portfolio KPI Dashboard**:
  * Audited Campaigns Count
  * Portfolio Average Match Score
  * Total Monthly Wasted Ad Spend
  * Critical Risk Campaigns Count
  * ⚖️ Regulated Category Compliance Exposure Count
* **Bulk Export**: Instant export of the full portfolio leaderboard to `.xlsx` (Excel) or `.csv`.

---

### 6. ⚡ One-Click Automated Copy Fixer (Remediation)
Remediates message friction with copy-paste ready copy blocks:
* **Option A: Landing Page Hero Remediation (Recommended)**
  * Rewritten Hero Headline (matching ad promise verbatim).
  * Supporting Hero Subheadline (reinforcing primary value prop).
  * High-Converting Call-to-Action (CTA) Button text.
* **Option B: Alternative Ad Copy Headlines**
  * Headlines 1, 2, and 3 rewritten to match existing landing page content if the page cannot be updated.

---

### 7. 📤 Multi-Format Enterprise Reporting & Export
Export complete audit findings in professional formats:
* **Multi-Sheet Excel Workbook (`.xlsx`)**:
  * `Audit Summary`: Executive metrics, scores, financial KPIs, and compliance status.
  * `Mismatches`: Normalized table of all mismatches with quotes, severity, and fixes.
  * `Confirmed Matches`: Positive message symmetries.
  * `Action Plan`: Prioritized strategic steps.
  * `Copy Remediation`: Hero headline rewrites and ad copy alternatives.
  * `Compliance Audit`: Statutory details, regulators, and uncorroborated claim flags.
* **Word Document (`.docx`)**: Formatted executive report for stakeholder presentations.
* **Tabular CSV (`.csv`)**: Raw mismatches table for BI tools.
* **Developer JSON (`.json`)**: Raw structured JSON response for API integrations.

---

### 8. 🎨 Strict Enterprise Visual Design System
* **Pure White Canvas**: `#FFFFFF` background for high contrast and readability.
* **Fresh Green Primary**: `#2E7D32` / `#4CAF50` (Trust, positive match, and compliance).
* **Light Blue Accent**: `#0288D1` / `#2196F3` (Information, metadata, and RSA preview).
* **Alert Red**: `#D32F2F` (Critical mismatches, hallucinations, and compliance violations).
* **Strict Rule**: Zero Dark Blue, Violet, or Purple anywhere in the interface.
* **Dual-Pane Layout**: Google SERP RSA Ad Simulation preview alongside a 620px tall interactive browser mockup window.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend Framework** | Streamlit (Python) |
| **AI / LLM Engine** | Google Gemini API (`gemini-3.5-flash`, `gemini-3.8-flash`) |
| **Web Scraping & DOM** | Requests (Chrome 124 Headers), BeautifulSoup4, lxml |
| **Data Manipulation** | Pandas, NumPy |
| **Report Generation** | OpenPyXL (Excel `.xlsx`), Python-Docx (Word `.docx`) |
| **Formatting & Utilities** | Python standard libraries (`json`, `io`, `pathlib`, `re`, `html`) |

---

## 🚀 Quickstart & Setup Guide

### 1. Clone & Navigate
```bash
git clone https://github.com/santhoshg-io/Ad-to-Landing.git
cd Ad-to-Landing
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Gemini API Key
Provide your Google Gemini API key via one of three methods:

* **Method A: Streamlit Secrets (`.streamlit/secrets.toml`)** (Best for production / cloud):
  ```toml
  GEMINI_API_KEY = "your_gemini_api_key_here"
  ```
* **Method B: Environment Variable**:
  ```bash
  # Windows PowerShell
  $env:GEMINI_API_KEY="your_gemini_api_key_here"

  # macOS / Linux
  export GEMINI_API_KEY="your_gemini_api_key_here"
  ```
* **Method C: In-App UI**: Enter it directly in the Streamlit sidebar input.

### 4. Launch Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📁 Repository Directory Structure

```plaintext
├── app.py                             # Core single-file Streamlit application
├── requirements.txt                   # Production dependency specifications
├── README.md                          # Comprehensive enterprise documentation
├── ads.csv                            # Dataset of 60 Responsive Search Ad records
├── landing_page_snapshots/            # Pre-cached offline HTML landing page files
│   ├── pait_0001.html
│   ├── pair_02.html
│   └── ...
└── .streamlit/                        # Streamlit configuration & cloud secrets
    ├── config.toml                    # Server & theme configuration
    └── secrets.toml                   # (Optional) API credentials
```

---

## 🌐 Deploying to Streamlit Community Cloud

1. Push this repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and select your repository.
3. Set the **Main file path** to `app.py`.
4. Under **Advanced Settings > Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
5. Click **Deploy**! Your enterprise auditor is live in under 60 seconds.

---

## 🏢 About BigBoost AI
**BigBoost AI** builds enterprise-grade AI intelligence platforms for digital performance advertising, conversion rate optimization, and automated compliance auditing.

* **Product**: Ad-to-Landing-Page Message Match Auditor & CRO Intelligence
* **Version**: 2.5.0 Enterprise Edition
* **License**: Proprietary / Enterprise Commercial License
* **Support**: support@bigboost.ai
