# Campaign Anomaly Detector
Flask + MySQL + Chart.js. Per-campaign baselines (median/MAD, weekday-aware) -> significance gates -> severity -> explanation + next step.

## Run
1. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. `mysql -u root -p < database/database.sql`
4. Set DB credentials if needed: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`
5. `python app.py` -> http://127.0.0.1:5000/upload -> click Analyze (loads sample data)
