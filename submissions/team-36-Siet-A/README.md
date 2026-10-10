# Search Term Triage Engine

A browser-only tool that triages Google Ads search terms into **promote**, **block**, or **ignore**, with confidence and a one-line reason. Thin samples are sent to human review instead of being guessed.

## How to open

**Option A — three files** (keep them in the same folder):

1. Double-click `index.html` (opens in your browser).
2. No install, no internet, no server.

**Option B — one file:**

1. Double-click `search-term-triage.html`.

## How to use

1. Drop a CSV/TSV/TXT search-terms report, or click **Try with sample data**.
2. Review the **Terms** tab. Amber **review** badges mean the data was too thin to judge.
3. Use **Your call** to correct decisions. Corrections feed word-based suggestions for other review terms.
4. Check **Groups** (pooled near-duplicates) and **Block patterns** (phrase-negative candidates).
5. Export: full results, keywords to add, exact negatives, phrase negatives.

## What it does

- Wilson 95% interval for conversion rate; small samples abstain instead of promoting on luck.
- Groups word-order and plural variants so thin terms can borrow pooled evidence.
- Suggests campaign- vs ad-group-level exact negatives, and phrase negatives for losing words.
- Learns from your corrections within the session (auto-applied suggestions do not feed learning).
- Parses Google Ads exports: title lines, Total rows, quoted numbers, UTF-16 BOM, comma/semicolon/tab.

## Files

| File | Role |
|------|------|
| `index.html` | Page structure |
| `style.css` | Look and layout |
| `script.js` | Pure logic (top) + UI (below `UI` marker) |
| `search-term-triage.html` | Everything inlined, with CSP |
| `test-logic.js` | Node tests for the decision engine |

Run tests: `node test-logic.js`
