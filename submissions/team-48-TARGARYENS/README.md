# Signal — Search Term Triage

A decision-support prototype for reviewing Google Ads search terms. It helps identify queries to **promote**, **block**, **ignore**, or send to **human review**, with a reason for each recommendation.

## Live demo

[Open the Vercel demo](https://signal-search-triage-vercel.vercel.app/)

The Vercel edition runs in the browser. Uploaded CSV data and review corrections stay in the current browser session; they are not saved to a server.

## Two ways to run the prototype

### Vercel edition

Open the live demo above. Upload a Google Ads search-terms CSV to view recommendations, review uncertain terms, and export the results.

The browser edition’s files are `index.html`, `styles.css`, `app.js`, and `engine.js`.

### Streamlit edition

Run the Python app locally:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Then open the local URL shown in the terminal.

The Streamlit edition starts from `app.py` and uses `triage.py` for its analysis logic.

## Review approach

Recommendations use search-term performance signals and include a confidence level and a short explanation. Terms with limited evidence can be routed to human review instead of being promoted based on a single conversion. Reviewers can record corrections and export the results.

## Input data

Upload a Google Ads search-terms report as a CSV. The app accepts standard Google Ads column names and common snake_case alternatives. Include search term, clicks, impressions, cost, and conversions where available; campaign and ad-group details are useful optional fields.

## Project files

- `app.py`, `triage.py`, `requirements.txt` — Streamlit edition
- `index.html`, `styles.css`, `app.js`, `engine.js` — browser/Vercel edition
- `test-engine.cjs` — checks for the browser edition’s analysis logic
- `README.md` — setup and project overview

## Prototype note

This tool provides recommendations for human review. Check proposed keyword and negative-keyword changes before applying them in Google Ads.
