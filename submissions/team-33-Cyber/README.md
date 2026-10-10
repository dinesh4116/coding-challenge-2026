# SearchSense AI — Search Term Triage Engine (PS-01)

SearchSense AI is an explainable search term intelligence and triage platform built for Google Ads advertisers, agency teams, and marketing analysts. It automatically standardizes search term report CSVs, evaluates search intent and performance metrics against configurable business rules, and triages search queries into four distinct, evidence-backed decision categories: **PROMOTE**, **BLOCK**, **IGNORE**, and **HUMAN REVIEW**.

---

## 🌟 Key Features

1. **Synthetic 25,000-Row Data Generator:** Generates a 25,000-row synthetic Google Ads search-term dataset instantly with a single click for testing.
2. **Flexible CSV Schema Auto-Mapping:** Automatically maps column aliases (e.g. `Search term`, `Spend`, `Orders`, `Query`) to standard canonical fields without breaking on unknown CSV structures.
3. **Explainable Rule-Based Decision Engine:** Evaluates text intent (buying signals vs non-commercial keywords) alongside performance evidence (Clicks, Spend, Conversions, ROAS) to assign transparent decisions.
4. **Human Review Workspace:** Routes low-confidence, ambiguous, or high-spend non-converting search terms to a dedicated human review queue with reviewer override & rationale logging.
5. **Cybersecurity-Style Premium UI:** Built with a modern dark theme, status badges, interactive Plotly distribution charts, and dynamic filtering.
6. **One-Click Export Centre:** Separate CSV downloads for Negative Keyword Blocklists (`BLOCK`), Keyword Expansion Targets (`PROMOTE`), Low Traffic terms (`IGNORE`), and Human Review Queues.

---

## 🛠️ Project Structure

- `app.py`: Main Streamlit application frontend with multi-page sidebar navigation and design system.
- `decision_engine.py`: Core rule engine evaluating relevance, evidence sufficiency, and decision explanations.
- `csv_processor.py`: Resilient CSV parser, auto-column mapper, and standardizer.
- `data_generator.py`: Reproducible synthetic 25,000-row search-term generator.
- `tests/test_decision_engine.py`: Unit test suite verifying decision logic edge cases.
- `tests/test_csv_processing.py`: Unit test suite verifying schema mapping and error handling.
- `data/sample_search_terms_25000.csv`: Pre-generated 25,000-row synthetic demonstration dataset.
- `requirements.txt`: Python package dependencies.
- `.gitignore`: Git configuration excluding temporary caches and venv files.

---

## 💻 Local Windows Setup & Quickstart

### Prerequisites
- Python 3.10+ installed on Windows.
- Git installed.

### Step-by-Step Instructions

1. **Open PowerShell or Command Prompt in the repository folder:**
   ```powershell
   cd d:\SearchSense-Triage
   ```

2. **(Optional) Create and activate a Python virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install required dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run automated unit tests to verify system integrity:**
   ```powershell
   python -m pytest tests/
   ```

5. **Launch the SearchSense AI application:**
   ```powershell
   python -m streamlit run app.py
   ```
   *The application will launch automatically in your web browser at `http://localhost:8501`.*

---

## 📥 How to Upload the Official Hackathon CSV

1. Open the application sidebar and navigate to **`2. Data Studio`**.
2. Drag and drop or upload your official hackathon CSV file under **Upload Search Term CSV**.
3. Inspect the auto-detected column mappings. SearchSense AI automatically maps standard Google Ads export headers (`Search term`, `Match type`, `Campaign`, `Cost`, `Clicks`, `Conversions`, `Conversion value`).
4. Navigate to **`3. Triage Analysis`**, configure your business context (e.g., product description and target keywords), and click **🚀 ANALYSE SEARCH TERMS NOW**.
5. Inspect results in **Interactive Results Explorer**, override uncertain cases in **`4. Human Review Queue`**, and export ready-to-use lists in **`6. Export Centre`**.

---

## 🐙 How to Push to GitHub

To publish this project to GitHub, execute the following commands in your terminal:

```powershell
git init
git add .
git commit -m "Initial commit - SearchSense AI Triage Engine (PS-01)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SearchSense-Triage.git
git push -u origin main
```
