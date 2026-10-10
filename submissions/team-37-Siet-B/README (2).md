# PS-02: Ad Creative Intelligence

**An AI-assisted platform for exploring the relationship between advertising creative attributes and campaign performance.**

🔗 **Live Demo:** [Ad Creative Intelligence](https://ps02-ad-creative-intelligence.onrender.com)

## Overview

Ad Creative Intelligence is a web application prototype designed to help marketers organize advertising creatives, analyze campaign performance, and explore patterns that may be associated with better advertising outcomes.

Instead of manually comparing multiple ad variations, users can work toward a more structured, data-driven understanding of creative performance.

## Problem Statement

Advertising teams frequently create multiple creative variations but struggle to identify which visual and content attributes are associated with better campaign results. Manually reviewing creatives and comparing performance metrics can be time-consuming and inconsistent.

Our solution aims to bring creative information and campaign performance data together in one place, supporting faster analysis and more informed creative decisions.

## Solution

Ad Creative Intelligence combines a web-based interface with Python-based data processing to support advertising creative analysis.

The project is designed to support:
- Organizing advertising creative files.
- Reviewing campaign performance metrics.
- Exploring relationships between creative attributes and performance.
- Identifying promising patterns while accounting for limited data and uncertainty.

**Project status:** Prototype / under development. Available functionality depends on the current implementation.

## Key Features

List only the features that are currently functional in the deployed application.

- **Web Interface:** Browser-based interface built with Flask, HTML, CSS, and JavaScript.
- **Creative File Handling:** Image-processing support using Pillow and OpenCV.
- **Campaign Data Processing:** Pandas and NumPy for tabular data analysis and calculations.
- **Performance Analysis:** Support for metrics such as click-through rate (CTR), conversion rate, and cost per acquisition (CPA), where implemented.
- **Evidence-Aware Insights:** Intended to distinguish observed patterns from conclusions that require more evidence.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Data Processing | Pandas, NumPy |
| Image Processing | Pillow, OpenCV |
| Document Processing | PyMuPDF, python-docx |
| Deployment | Render, Gunicorn |

## How It Works

1. **Creative Input:** Provide advertising creatives through the supported input workflow.
2. **Data Preparation:** Organize the available campaign information and creative attributes.
3. **Performance Analysis:** Calculate or review relevant campaign metrics.
4. **Insight Exploration:** Examine patterns between creative characteristics and campaign performance.
5. **Decision Support:** Use the findings to inform future creative experiments.

*Note: The workflow above describes the intended process. Confirm each step against the currently deployed implementation.*

## Performance Metrics

- **Click-Through Rate (CTR):** Clicks / Impressions × 100
- **Conversion Rate:** Conversions / Clicks × 100
- **Cost per Acquisition (CPA):** Spend / Conversions

Metrics with zero denominators should be reported as unavailable. Comparisons should account for differences in audience, budget, placement, campaign objective, and reporting period.

## Running Locally

### Prerequisites
- Python
- Git
- A web browser

### Installation

```bash
git clone https://github.com/ragavi36-2007/ps02-ad-creative-intelligence.git
cd ps02-ad-creative-intelligence

python -m venv .venv
```

Activate the virtual environment in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and run the application:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open the local URL displayed in the terminal, typically `http://127.0.0.1:5000`.

### Deployment

The application is deployed on Render.

**Live application:** https://ps02-ad-creative-intelligence.onrender.com

## Limitations

- The quality of insights depends on the amount and reliability of the available campaign data.
- Observed associations do not establish that a creative attribute caused a performance improvement.
- Automated attribute extraction and statistical confidence estimates should be considered available only when implemented and validated.

## Future Enhancements

- Automated creative-attribute extraction using computer vision and OCR.
- Statistical comparisons with sample sizes, effect sizes, and confidence intervals.
- AI-assisted creative-brief recommendations.
- Creative-fatigue detection across time periods.
- Video-ad analysis.
- Exportable campaign insight reports.

## License

No license has been added yet.
