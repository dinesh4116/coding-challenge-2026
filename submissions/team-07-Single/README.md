# QueryPilot AI — Search Term Triage Engine

## Run locally (Windows / VS Code)

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment (recommended):

   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   ```

5. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

6. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

   (equivalently: `streamlit run app.py`)

7. Streamlit opens a local browser tab. Upload your own CSV or use `sample_search_terms.csv`.

> **Theme note:** the dark dashboard theme (including dark data tables) is configured in
> `.streamlit/config.toml`. Streamlit reads this file **at server startup**, so restart the
> server after changing it. Always run Streamlit from this project folder so the config is found.

## Smoke test (fast pre-demo check)

```bash
.venv\Scripts\python smoke_test.py
```

Runs 11 checks: full app execution via `streamlit.testing.v1.AppTest`, CSV upload paths
(valid / missing columns / negatives / invalid numbers / empty file), search with special
characters, decision filters, relevance routing, and the core triage rules. All checks should
print `[ok]` and end with `All smoke tests passed.`

## Required CSV columns

`query, campaign, ad_group, impressions, clicks, cost, conversions, conversion_value`

The app also normalizes common column variants such as `search term`, `spend`, `ad group name`, and `conv. value`, and tolerates formatted numbers like `1,234.50` or `$50`.

## What it does

- Reads and validates search-term metrics.
- Produces Promote / Block / Ignore / Review recommendations.
- Includes a human-readable reason and transparent evidence score.
- Shows portfolio metrics and decision distribution.
- Exports the full result as CSV.
- Routes low-evidence cases away from confident decisions.

## Important limitations

This hackathon MVP uses transparent heuristics, not a trained ML model. The confidence score is a rule-based evidence score, not a calibrated probability. `Block` suggestions must be reviewed before applying negative keywords. For a stronger version, label a validation set with an analyst, use time-aware train/test splits, and report precision, recall, and abstention rate. Do not claim measured accuracy without labelled ground-truth data.
