# Prototype Validation Report

## Dataset checks
- Input file: `search_terms_report.csv`
- Input rows: 25,000
- Input columns: 10
- Missing values: 0 in all 10 provided columns
- Required dataset columns validated by the triage engine before processing.

## Baseline run (default thresholds)
- PROMOTE: 815 rows
- BLOCK: 4,140 rows
- IGNORE: 20,045 rows
- Human-review flag: 20,535 rows
- Output fields: 21, including input fields, calculated metrics, intent, action, confidence, review flag, and explanation.

These are counts produced by the current rules, **not** measured accuracy or ground-truth labels. Validate outputs against the organisers' rubric and spot-check examples before presenting the results.

## Checks performed
- `triage_engine.py` processed the full 25,000 rows without raising an exception.
- The generated recommendation table was exported to `sample_recommendations.csv`.
- `app.py` and `triage_engine.py` pass Python syntax compilation.

## Remaining verification before submission
1. Install dependencies and launch the Streamlit dashboard on the team laptop.
2. Open the Overview, Explore decisions, Campaign analysis, and How decisions work tabs.
3. Test filters and both CSV download buttons.
4. Spot-check unsupported queries, relevant high-performing queries, and low-sample cases.
5. Make sure the presentation's thresholds and claims match the final code and the official rubric.
