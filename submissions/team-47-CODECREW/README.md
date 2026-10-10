# Search Term Triage Engine

A hackathon project that analyzes search-term performance and categorizes search queries into actionable decisions using explainable, rule-based logic.

## Problem Statement

Search-term reports can contain large numbers of queries. Manually reviewing every query makes it difficult to identify which terms should be promoted, blocked, ignored, or reviewed further.

## Solution

The Search Term Triage Engine processes an uploaded CSV file, evaluates search-term performance metrics, and generates triage decisions with explanations and confidence scores.

## Features

- Upload search-term data in CSV format.
- Analyze impressions, clicks, cost, conversions, and conversion value.
- Categorize search terms as **Promote**, **Block**, or **Ignore**.
- Flag uncertain decisions for human review.
- Display summary metrics and triage results.
- Export processed results.
- Provide an API using FastAPI.
- Interactive Flutter dashboard.

## Technology Stack

- **Frontend:** Flutter
- **Backend:** Python and FastAPI
- **Data processing:** Pandas
- **API documentation:** Swagger UI

## Project Structure

```text
search_term_triage/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── mobile_app/
│   ├── lib/
│   │   └── main.dart
│   └── pubspec.yaml
├── .gitignore
└── README.md
```

## Requirements

- Python installed
- Flutter SDK installed
- Git installed
- Google Chrome or another supported browser

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/vijaygu2008/search-term-triage-engine.git
cd search-term-triage-engine
```

### 2. Set up the backend

Open a terminal in the project root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Start the backend server

From the `backend` directory, run:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open the API documentation:

http://127.0.0.1:8000/docs

Keep this terminal running.

### 4. Start the Flutter dashboard

Open a second terminal:

```powershell
cd mobile_app
flutter pub get
flutter run -d chrome
```

## Input Data

The CSV file should contain the following columns:

- `query_text`
- `match_type`
- `campaign`
- `ad_group`
- `impressions`
- `clicks`
- `cost`
- `conversions`
- `conversion_value`

Use the sample dataset included with the project, if available.

## Decision Transparency

The backend uses rule-based logic to generate decisions, confidence scores, reasons, and human-review flags.

Confidence scores are heuristic indicators and should not be interpreted as statistically calibrated probabilities. Decisions should be validated against real campaign data before production use.

## Future Enhancements

- Machine-learning-based decision support.
- Better uncertainty estimation for small datasets.
- Advanced filtering and visual analytics.
- Deployment for remote access.
- Expanded automated testing.

## Author

**VIJAY**

GitHub: https://github.com/vijaygu2008

## Disclaimer

This project is intended for hackathon demonstration and experimentation. Validate all recommendations before applying them to live advertising campaigns.
