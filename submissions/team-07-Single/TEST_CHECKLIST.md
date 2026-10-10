# Manual acceptance test checklist

Automated first: `.venv\Scripts\python smoke_test.py` should end with `All smoke tests passed.`
Then confirm the following manually in the browser.

## Startup and theme

- [ ] App starts with `python -m streamlit run app.py` (run from the project folder).
- [ ] Sample CSV loads without a schema error.
- [ ] Tables (decision summary + recommendations) render **dark** — no white table backgrounds.
      If tables are light, the server was started before `.streamlit/config.toml` existed:
      stop it (Ctrl+C) and start it again.
- [ ] No `TypeError: ... unexpected keyword argument 'theme'` in the terminal or on screen.

## Dashboard and calculations

- [ ] KPI cards show term count, spend, conversions and blended CPA.
- [ ] Decision overview shows Promote / Block / Ignore / Review (sample data yields at
      least one of each).
- [ ] Each output row has a reason and confidence score (0.00–1.00).
- [ ] Pie chart legend is readable and matches the summary table counts.

## Interaction

- [ ] Search and decision filters work.
- [ ] Search with special characters such as `(` or `$` does not crash.
- [ ] Download CSV opens and includes decision/reason columns.
- [ ] Relevance terms entered in the sidebar route non-matching queries to Review.

## CSV validation

- [ ] Upload a CSV missing `cost`: app shows a helpful missing-column error.
- [ ] Upload a CSV with invalid numeric values: app warns and drops invalid rows,
      valid rows remain.
- [ ] Upload a CSV with negative costs/clicks: app rejects it.
- [ ] Upload an empty file: app reports an empty file, no traceback.
- [ ] Formatted numbers (`1,234.50`, `$50`) are accepted.
- [ ] Alias headers (`search term`, `spend`, `conv. value`, `ad group name`) are accepted.

## Guardrails

- [ ] Confirm low-click, low-spend queries are not promoted.
- [ ] Traffic-source cards say "Connection not configured" where no integration exists.
- [ ] The banner states this is decision support, not an automatic Google Ads change.
