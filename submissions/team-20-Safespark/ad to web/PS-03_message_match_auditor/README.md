# PS-03 — Ad-to-Landing-Page Message Match Auditor · Dataset

60 Google search ads, each paired with the landing page it sends people to. 15 fictional brands across
financial services, SaaS and consumer e-commerce (4 ads each). All brands, claims and pages are fictional.

**Files**
- `ads.csv` — one row per ad
- `landing_page_snapshots/pair_01.html` … `pair_60.html` — the fully rendered landing page for each ad,
  saved as a single HTML file. Open in any browser, or parse the HTML directly.

| Column | Meaning |
|---|---|
| pair_id | P01 – P60 |
| advertiser | Brand name |
| vertical | financial services / SaaS / consumer e-commerce |
| headline_1–3 | The ad's headlines (as shown in Google) |
| description_1–2 | The ad's description lines |
| final_url | The URL the ad points to (fictional `.example` domain — it does not exist online) |
| snapshot_file | The saved landing page for this ad |

**Important:** the live URLs are fictional. **Build against the snapshot files** — this replaces the live
fetching mentioned in the problem statement, so network conditions cannot block you.

**Your job:** for each pair, output a message-match score and a list of specific mismatches between what
the ad promises and what the page says, each backed by an **exact quote** from the page (or a clear
statement that the claim is absent). Pay attention to *where* on the page a claim appears — a promise
that only shows up in tiny footer text is not the same as one in the main headline.
