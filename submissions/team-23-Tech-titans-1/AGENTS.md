# AGENTS.md: AdReach AI

## What this is
AdReach AI is a static, client-only Vite app (vanilla JS, no framework) that analyses ad performance datasets and ad creative images entirely in the browser. It has no backend, functions, database or external API calls. Uploaded files must never be sent anywhere.

## Architecture
- `index.html`: all static markup. The **Upload Dataset** card (`#dataset`) and the **Upload Advertisement Images** card (`#images`) are deliberately separate and independent. Neither one may require the other.
- `src/main.js`: the single UI controller. It holds module-level `state` (dataset, match index, images[], filters, current run). Rendering uses template strings, and **every** interpolated user value must go through `esc()` (escapeHtml).
- `src/dataset.js`: `loadDataset(file)` parses CSV (PapaParse, `header:false`) or Excel (SheetJS, imported dynamically) into rows, detects columns through `FIELDS` aliases (headers are normalised by lower-casing and stripping non-alphanumerics), validates the numbers and calculates per-row CTR/CVR/ROAS. `aggregate()` produces totals and ratios that are `null` when a calculation is invalid.
- `src/matching.js`: exact, case-insensitive matching only. The order is filename column, then ad ID (optional `ad_`/`ad-` prefix), then creative ID. If an ad ID and a creative ID point to different rows, the result is `ambiguous` and the image is not linked.
- `src/analysis.js`: decodes the image (createImageBitmap, with an `<img>` fallback) and draws it to a shared canvas downscaled to ≤512 px. `computeFeatures()` measures the pixels and `scoreFeatures()` applies the documented rules. `LIKELY_THRESHOLD = 65`. The function also returns a WEBP thumbnail blob that the gallery uses instead of full-resolution originals.
- `src/report.js`: CSV report built from real results only.

## Conventions and non-obvious decisions
- **Honesty constraints (product requirement):** never present the scoring as a trained ML model. Never add confidence percentages, accuracy figures or predicted reach numbers. Never show fabricated dataset values as uploaded data. If you change the scoring rules, update the “Method” section in `index.html`, which has the weights table and thresholds.
- Text-like coverage is a heuristic and is intentionally **excluded** from the score. It only triggers a suggestion.
- Images are analysed sequentially, with `yieldToBrowser()` between images to keep the UI responsive. The limit is 200 images per batch and 30 MB per image. Datasets are limited to 25 MB.
- Rows where clicks > impressions or purchases > clicks are treated as invalid for CTR and conversion rate, both per row and in aggregates.
- Object URLs are revoked when images are removed or cleared.
- Styling uses CSS custom properties in `src/style.css` (dark navy/blue palette). Fonts are self-hosted through Fontsource.
- Netlify config: `netlify.toml` (build `npm install --include=dev && npm run build`, publish `dist`). `vite` is a regular dependency so the build works even when devDependencies are skipped.