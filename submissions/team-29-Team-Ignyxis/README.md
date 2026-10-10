# Search Term Triage Engine — PS-01

An explainable, rule-based prototype for triaging search-term reports for Kestrel Business Funding.

## Features
- Loads the supplied 25,000-row CSV by default, or accepts a CSV upload.
- Classifies search intent against the products listed in the supplied dataset README.
- Generates PROMOTE / BLOCK / IGNORE recommendations with confidence, rationale, and a human-review flag.
- Calculates CTR, conversion rate, CPA, and observed ROAS with safe handling of zero denominators.
- Filters and searches results, summarizes by campaign, and exports the full or filtered output to CSV.
- Configurable thresholds; no connection to an advertising account and no automatic campaign changes.

## Run locally

Use Python 3.10+.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The included `search_terms_report.csv` is the supplied dataset. To load a different file, use the sidebar uploader.

## Output decisions
- **PROMOTE**: query appears relevant and meets configured minimum clicks, conversions, and observed ROAS.
- **BLOCK**: strong lexical evidence indicates an unsupported product or clearly irrelevant intent; review before applying as a negative keyword.
- **IGNORE**: evidence is thin, intent is ambiguous, or promotion criteria are not met.
- **Human review**: flags uncertain/medium-evidence recommendations for manual inspection.

## Important limitations
The engine is a transparent baseline based on keyword patterns and explicit thresholds, not a trained ML model. Validate patterns and decision thresholds against the event's scoring rubric and business constraints. Conversion attribution can be noisy; BLOCK is only a recommendation, not an automatic account action. Follow event rules for permitted tools and outside assistance.
