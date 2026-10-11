# Signal — Vercel edition

A static, browser-only edition of the Search Term Triage Engine. It retains the existing Streamlit application at the repository root. Uploaded CSV contents are processed in the browser and are never sent to Vercel.

## Deploy on Vercel

1. Open [Vercel Drop](https://vercel.com/drop) and sign in.
2. Upload the `signal-search-triage-vercel.zip` archive or this folder.
3. Name the project `signal-search-triage` and deploy. This static site needs no build or install step.
4. Open the generated `*.vercel.app` URL and upload a Google Ads search-terms CSV.

## Local preview

Open `index.html` in a modern browser. No account, server, or dependency installation is required.

## Features

- Standard Google Ads and snake_case CSV headers; required fields are search term, clicks, impressions, cost, and conversions.
- Explainable `PROMOTE`, `BLOCK`, `IGNORE`, and `REVIEW` decisions with confidence and configurable evidence thresholds.
- One conversion never auto-promotes. Thin and mixed evidence stays in the human review queue.
- Search and filter all rows; record human corrections and notes in the current browser session.
- Exact normalized query clusters, campaign comparisons, and historical spend views.
- Full audit, promote-candidate, and exact-negative candidate CSV exports.
- In-memory processing for reports with 25,000 rows. No sample rows are bundled.

Near-duplicate grouping removes case, punctuation, and extra spacing only; it does not infer semantic similarity. Spend charts show historical reported costs, not forecast savings. Review match type, scope, attribution window, and account policy before applying exports in Google Ads.
