# Ad-to-Landing-Page Message Match Auditor

A beginner-friendly Streamlit prototype for a hackathon project.

## Features
- Enter ad headline, description, CTA, and optional custom claims.
- Upload an offline HTML snapshot or paste landing-page text.
- Extract visible text from HTML using BeautifulSoup.
- Show a basic word-overlap indicator.
- Run simple phrase-based checks for selected claim types.
- Display relevant sentences only when the quotations can be verified against the extracted page text.
- Approximate section labels for semantic HTML regions such as header, main, and footer.
- Check whether the ad CTA appears in the supplied page text.

## Important limitations
- This is a prototype, not a legal compliance tool.
- The score is word overlap only; it does not represent message-match quality.
- Phrase-based rules can miss paraphrases and can incorrectly classify claims.
- A quotation's presence does not prove that a claim is supported or contradicted.
- The URL field is for reference only. Live URL fetching is not implemented.
- Section labels are approximate; real-world HTML structures vary.

## Run on Windows
1. Install Python 3.11+ if needed.
2. Extract the ZIP.
3. Open the extracted folder in VS Code or a terminal.
4. Create and activate a virtual environment (optional but recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Run the app:

   ```powershell
   python -m streamlit run app.py
   ```

7. Open the local URL shown in the terminal, usually `http://localhost:8501`.

## Test data
Upload `sample.html` and use:
- Ad headline: `Get Your Loan Approved Today!`
- Ad description: `Apply online for a personal loan with fast approval.`
- CTA: `Apply Now`

Expected behavior: the app should flag the exact "approved today" wording as not substantiated by its simple phrase check if the page only contains conditional approval language, find relevant conditional-approval sentences as quotations, and recognize "Apply Now" if it appears on the page.
