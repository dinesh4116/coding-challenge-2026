# AdReach AI

**AI-Powered Advertisement Creative Analysis.** This is a static web app for a college hackathon demo. It reads advertisement performance datasets (CSV / Excel), analyses advertisement images pixel by pixel, and estimates each creative's reach potential. Everything runs in the browser, so no file ever leaves the user's device.

## Features

- **Upload Dataset** (its own section): drag-and-drop or browse for `.csv`, `.xlsx` or `.xls` files. The app parses the real file and shows the file name, type, size and status. It also shows the recognised columns, warnings for invalid values, KPI totals and a preview table. CTR, conversion rate and ROAS are calculated only when the required columns exist and each calculation is valid. You can replace or remove the dataset at any time.
- **Upload Advertisement Images** (its own section): add 1–200 JPG, JPEG, PNG or WEBP files per batch by multi-select or drag-and-drop. Every image is previewed before analysis. You can remove one image or clear them all.
- **Image analysis**: measures dimensions, aspect ratio, brightness, contrast, colourfulness, dominant colours, hue distribution, clarity (Laplacian variance), edge density and an approximate text-like detail share. A transparent rule-based score out of 100 gives either “Likely to Get Reach” or “Less Likely to Get Reach”, together with an explanation, 2–3 suggestions and the analysis's limitations.
- **Dataset ↔ image matching**: an image is linked only on an exact, unambiguous match of filename, ad ID or creative ID. Matched images show their real historical metrics. Unmatched images are analysed on their own.
- **Bulk dashboard**: progress bar, totals, likely and less-likely counts, failures, search, filters, score sorting, a detail view and a downloadable CSV report.

> **Honesty note:** the image scoring is a rule-based visual-scoring prototype. It is **not** a trained machine-learning model, and it reports no confidence percentages, accuracy figures or predicted reach numbers. The rules and weights are documented in the in-app “Method” section and in `src/analysis.js`.

## Tech stack

- Vanilla JavaScript (ES modules) and Vite
- [PapaParse](https://www.papaparse.com/) for CSV parsing and report generation
- [SheetJS (xlsx)](https://sheetjs.com/) for Excel parsing (loaded on demand)
- Canvas 2D API for image processing
- Self-hosted fonts via Fontsource (Sora, IBM Plex Sans, JetBrains Mono)

## Run locally

```bash
npm install
npm run dev
```

Then open the URL that Vite prints (usually http://localhost:5173).

## Deploy to Netlify (beginner-friendly)

The project is already set up for Netlify through `netlify.toml` (build command `npm install --include=dev && npm run build`, publish folder `dist`).

**Option A: from Git (recommended)**
1. Push this folder to a GitHub, GitLab or Bitbucket repository.
2. Sign in at https://app.netlify.com and click **Add new project → Import an existing project**.
3. Choose your Git provider and pick the repository.
4. Netlify reads `netlify.toml` automatically. Check that the build command is `npm install --include=dev && npm run build` and the publish directory is `dist`, then click **Deploy**.
5. After a minute or two you get a live URL like `https://your-site.netlify.app`. Every new push redeploys automatically.

**Option B: Netlify CLI**
1. `npm install -g netlify-cli`
2. `netlify login`
3. `netlify init` (to link or create a project), then `netlify deploy --build --prod`

You don't need any environment variables, a database, a backend or paid APIs.

## Manual test checklist

Use `public/samples/sample-ad-performance.csv` (illustrative values only) together with your own images:

1. **Dataset only.** Upload the sample CSV without images. Check the file details, the recognised columns, the KPI totals, the CTR/conversion/ROAS values, and the warning for the row with `not available` clicks. Check that the zero-impression row shows “—”.
2. **Five images, no dataset.** Add five images and click **Analyse 5 images**. Each card should show a score, a category, an explanation and suggestions, and “Matched to dataset” should show “—”.
3. **Dataset + images.** Rename some images to `AD-1001.jpg`, `ad_AD-1004.png` or `CR-503.webp` and keep others with unrelated names. Only the renamed images should show “Dataset match”. All others should show “No dataset match, analysed independently”.
4. **Batch + report.** Add a larger batch (for example 50–200 images), analyse it, and use the search, filters and sorting. Then click **Download CSV report** and open the file in Excel or Google Sheets.

## Project structure

```
index.html            Page layout (upload cards, dashboard, method section, detail dialog)
src/main.js           UI controller: uploads, rendering, analysis queue, detail view
src/dataset.js        CSV/Excel parsing, column detection, validation, metrics
src/matching.js       Exact, unambiguous image ↔ dataset matching
src/analysis.js       Pixel feature extraction and transparent scoring rules
src/report.js         CSV report generation
src/style.css         Dark navy/blue dashboard styles
public/samples/       Sample dataset for trying the tool