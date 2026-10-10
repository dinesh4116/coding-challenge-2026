MessageMatch - Ad-to-Landing-Page Message Match Auditor

Paste an ad (and optionally its photo), find its original website,
check claims, offer deadlines and photos, then export a CSV.

HOW TO RUN (Windows)
1. Open PowerShell inside this folder.
2. python -m pip install -r requirements.txt
3. python -m streamlit run app.py

The app opens at http://localhost:8501
(Or just double-click run.bat)

HOW TO USE
1. Type the ad copy and upload the ad photo (optional).
2. Click "Find original website" or enter the URL yourself.
3. Click "Audit message match" to see the score and claim results.
4. Download the CSV report or the audit history.

NOTES
- Rule-based screening only. Verify flagged items by hand.
- If a site blocks reading, paste the landing-page text instead.
- Optional: install pytesseract + Tesseract to read text from the ad image.


