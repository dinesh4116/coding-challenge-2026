PS-01: Search Term Triage Engine

Problem
Google Ads campaigns generate thousands of search terms.
Manually reviewing these terms is time-consuming and
difficult.

Our Solution
We developed a Python-based application that analyzes
search-term performance and classifies each term into:

- PROMOTE: Promising search terms
- BLOCK: Poor-performing search terms
- IGNORE: Terms without sufficient evidence for action

Technologies Used
- Python
- Streamlit
- Pandas

Features
- Upload Google Ads search-term CSV files
- Analyze clicks, cost, conversions and conversion value
- Classify terms as PROMOTE, BLOCK or IGNORE
- Display confidence levels and explanations
- Flag uncertain decisions for human review
- Display a summary dashboard
- Download the results as CSV

Dataset
Tested using the organizer-provided dataset containing
25,000 search terms.

How to Run

1. Install Python.
2. Open the project folder in a terminal.
3. Install dependencies:

   pip install -r requirements.txt

4. Start the application:

   streamlit run app.py

5. Open the local URL displayed in the terminal.
6. Upload a CSV file to analyze the search terms.

Decision Logic
The prototype uses rule-based performance thresholds
and a statistical confidence check.

It avoids promoting search terms based on very small
numbers of clicks or conversions.

Uncertain cases are flagged for human review.

Output
The system generates a downloadable CSV containing:
- Original search-term data
- Decision
- Confidence
- Reason
- Human review requirement

Limitations
The thresholds are prototype settings and may need
adjustment for different advertising campaigns.

Application Screenshot

[Search Term Triage Dashboard](dashboard.png)

Evaluation Results

The application was tested using 25,000 search terms.

- PROMOTE: 431
- BLOCK: 96
- IGNORE: 24,473

The application provides confidence levels, explanations,
human-review flags, and a downloadable results CSV.
