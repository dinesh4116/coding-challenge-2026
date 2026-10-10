# Ad-to-Landing-Page Message Match Auditor (PS-03)

Audits whether a landing page actually supports what an ad promises, and **where on the page** the
supporting evidence appears (hero, main, features, pricing, FAQ, footer, unknown).
Works fully **offline** on saved HTML snapshots. Local AI via **Ollama + Qwen3:4B**. No paid APIs.

> The tool only audits and recommends. It never changes a Google Ads account.

## What is included

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard (upload, results, human review, export) |
| `parser.py` | HTML -> ordered text blocks with section labels and stable source paths |
| `verifier.py` | Checks every quotation against the extracted page text |
| `auditor.py` | Ollama integration, rule checks (price/timing/CTA), audit pipeline, batch processing |
| `scoring.py` | Configurable position-aware score + separate audit confidence |
| `schemas.py` | Pydantic models |
| `data_loader.py` | CSV/Excel loading, validation, snapshot matching |
| `exports.py` | CSV, JSON and prioritised fix-list exports |
| `fetcher.py` | OPTIONAL live fetching with SSRF protection |
| `data/sample_ads.csv (60 official PS-03 dataset pairs; previous 7-row demo is data/demo_sample_ads.csv)`, `data/snapshots/` | **Synthetic** example ads and pages (fictional companies) |
| `tests/` | pytest suite |

## Windows setup (PowerShell)

1. Install **Python 3.11** from python.org (tick "Add python.exe to PATH"). Check: `py -3.11 --version`
2. Install **Ollama for Windows** from https://ollama.com/download, then pull the model:
   ```powershell
   ollama pull qwen3:4b
   ollama list
   ```
3. In the project folder:
   ```powershell
   cd ad-message-auditor
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   (If scripts are blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.)
4. Run the tests: `python -m pytest -v`
5. Start the dashboard: `streamlit run app.py`
6. In the dashboard: **Upload & process -> Load bundled PS-03 dataset (60 ad/page pairs) -> Run audit**.
   Untick "Use Ollama AI analysis" in the sidebar to run rule-based checks only (no Ollama needed).

## Included PS-03 dataset\n\nThe bundled default dataset is the uploaded PS-03 dataset: 60 ad/page pairs (`P01`–`P60`) and all 60 offline HTML snapshots. The CSV uses normalized columns and each `snapshot_file` points to the matching file in `data/snapshots/`. The original 7-row demo is retained as `data/demo_sample_ads.csv`. The live URLs are fictional; use the offline snapshots.\n\n## Input format

CSV or Excel. Column names are matched case-insensitively (aliases in `data_loader.COLUMN_ALIASES`):

| Column | Required | Notes |
|---|---|---|
| `pair_id` | recommended | Links an ad to `<pair_id>.html` if `snapshot_file` is empty |
| `ad_headlines` | yes | Several headlines separated by `|` or new lines (or `headline_1`, `headline_2`, ...) |
| `ad_descriptions` | no | Same format |
| `landing_page_url` | no | Must be http/https |
| `snapshot_file` | no | File name inside the snapshot folder |

Snapshots can be loaded from a folder or uploaded as a `.zip`. Optional layout metadata can sit beside a
snapshot as `<name>.layout.json`: `{"viewport_height": 800, "elements": {"<source_path>": {"top": 120}}}`.
Only then is `above_the_fold` filled in; HTML alone never proves visual prominence.

## How it works

1. **Parse**: scripts, styles and hidden elements are removed; each visible text is emitted once with
   `block_id`, `section`, `tag`, `document_order`, DOM `source_path`, original text and normalised text.
2. **Section classification**: page footer, navigation, id/class tokens (`hero`, `faq`, `pricing`, ...),
   section headings, `<header>` with H1, `<main>`. Anything else is `unknown` (low confidence, review requested).
3. **Analyse**: rule checks (prices, time promises, call-to-action intent) plus the Qwen3:4B model, which is told
   page text is untrusted data. If Ollama is down or returns invalid JSON twice, rule findings are still produced,
   confidence drops and review is requested.
4. **Verify**: a quotation counts only if its normalised text is inside ONE extracted block. Fabricated quotes are
   rejected (kept separately as `rejected_quote`) and the finding becomes `uncertain`. `missing` findings never
   carry a quote. Incomplete snapshots make `missing` findings `uncertain`.
5. **Score**: see below.

## Scoring (initial heuristics, not validated)

Five dimensions start at 100: main offer 30%, features 25%, pricing/timing/eligibility 20%, CTA 15%,
prominence 10%. Penalty per verified finding = severity (low 10, medium 25, high 50) x status multiplier
(contradicted 1.0, missing 0.8, partial 0.5). Supported/uncertain findings are never penalised, and
partial/contradicted findings only count if their quote was verified. A verified supporting claim that sits only in
the footer (-60), FAQ (-30) or an unclassified section (-20) reduces the prominence dimension: a position concern,
not a claim that the ad is false. Weights and penalties live in `scoring.ScoringConfig`.

`match_score` is `None` ("not evaluated") when nothing could be evaluated. **`audit_confidence` (0-1)** is separate
and drops for incomplete snapshots, LLM failure, uncertain findings, rejected quotes and mostly unclassified pages.

## Optional live fetching

Off by default. Tick it in the sidebar; used only for pairs without a snapshot. Public http/https only,
ports 80/443, private/loopback/link-local addresses blocked, redirects re-validated, size/time limits, JavaScript is
never executed. Results are labelled `live_fetch`.

## Limitations

- Section detection depends on the page's HTML quality; unlabelled pages end up `unknown`.
- Rule checks are simple heuristics (currency prices, "same-day"/"N days" phrases, CTA intent groups).
- Qwen3:4B is small; every quote is verified, but its claim judgements still deserve human review.
- Live fetching cannot render JavaScript and has a small DNS-rebinding window (see `fetcher.py`).
- Scoring weights are initial heuristics.
