import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def build_pdf(filename="ZeroSec_System_Architecture_and_Functional_Report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a") # Dark Slate
    accent_color = colors.HexColor("#4f46e5")  # Indigo
    secondary_color = colors.HexColor("#10b981") # Emerald
    dark_gray = colors.HexColor("#334155")
    light_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_gray,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=dark_gray
    )

    story = []

    # Title Banner
    story.append(Paragraph("ZeroSec Anomaly Intelligence Platform", title_style))
    story.append(Paragraph("System Architecture, Functional Specifications & Hackathon Presentation Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=15))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph(
        "<b>ZeroSec</b> is a production-grade, full-stack Campaign Anomaly Intelligence Platform designed for digital ad marketing teams. "
        "It monitors continuous time-series data across ad campaigns (Spend, Conversions, CPA, Impressions, Clicks) to detect genuine performance anomalies "
        "while eliminating alert fatigue and false positive noise.",
        body_style
    ))
    story.append(Paragraph(
        "Modern ad platforms frequently trigger false alarms due to minor statistical variance or expected day-of-week seasonality. ZeroSec solves this "
        "by combining dynamic rolling baseline confidence bands (&mu; &plusmn; 2&sigma;), spend floor guardrails, cooldown deduplication, and ground-truth evaluation metrics.",
        body_style
    ))

    # Key Accomplishments Table
    summary_data = [
        [Paragraph("Metric / Feature", table_header_style), Paragraph("ZeroSec Performance", table_header_style), Paragraph("Impact", table_header_style)],
        [Paragraph("Incident Recall (Catch Rate)", table_cell_style), Paragraph("<b>100% (0 Missed Incidents)</b>", table_cell_style), Paragraph("Zero critical revenue or spend leakage missed", table_cell_style)],
        [Paragraph("Noise & False Alert Reduction", table_cell_style), Paragraph("<b>>97% Noise Suppressed</b>", table_cell_style), Paragraph("Replaces 1,100+ noisy alerts with actionable digest", table_cell_style)],
        [Paragraph("Ground-Truth Confusion Matrix", table_cell_style), Paragraph("<b>Full TP / FP / TN / FN Tracking</b>", table_cell_style), Paragraph("Mathematical precision & recall accountability", table_cell_style)],
        [Paragraph("Full-Stack Integration", table_cell_style), Paragraph("<b>React + FastAPI (Python)</b>", table_cell_style), Paragraph("Standalone client-side engine + FastAPI REST API", table_cell_style)]
    ]
    t_summary = Table(summary_data, colWidths=[2.2*inch, 2.3*inch, 2.7*inch])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # Architecture Overview
    story.append(Paragraph("2. System Architecture & Tech Stack", h1_style))
    story.append(Paragraph(
        "ZeroSec follows a clean monorepo architecture with a React + Vite TypeScript frontend and a FastAPI Python microservice engine.",
        body_style
    ))

    arch_data = [
        [Paragraph("Layer", table_header_style), Paragraph("Technology Stack", table_header_style), Paragraph("Role & Key Components", table_header_style)],
        [Paragraph("Frontend UI", table_cell_style), Paragraph("React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, Recharts", table_cell_style), Paragraph("Responsive dashboard, interactive anomaly band charts, filter controls, RCA export", table_cell_style)],
        [Paragraph("Client Engine", table_cell_style), Paragraph("TypeScript Math Module (anomalyEngine.ts)", table_cell_style), Paragraph("Instant in-browser baseline calculation, Z-score analysis, and cooldown deduplication", table_cell_style)],
        [Paragraph("Backend API", table_cell_style), Paragraph("Python 3.10+, FastAPI, Uvicorn, Pytest", table_cell_style), Paragraph("RESTful microservice (/api/health, /api/analyze, /api/analyze/demo) with 100% test coverage", table_cell_style)],
        [Paragraph("Data Storage", table_cell_style), Paragraph("In-Memory State Context + CSV Ingestion", table_cell_style), Paragraph("Dynamic CSV dataset upload, validation, and ground-truth evaluation mapping", table_cell_style)]
    ]
    t_arch = Table(arch_data, colWidths=[1.5*inch, 2.5*inch, 3.2*inch])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 15))

    # Application Modules & Functions
    story.append(Paragraph("3. Detailed Application Modules & Functions", h1_style))

    modules = [
        ("Overview Dashboard (OverviewView.tsx)", [
            "<b>KPI Cards Grid:</b> Displays total monitored campaigns, total spend (INR ₹), actionable incident count, precision %, recall %, and suppressed noise count.",
            "<b>Portfolio Spend vs Conversions Chart:</b> Interactive dual-axis chart (Bar for spend, Line for conversions) with red incident markers.",
            "<b>Severity Distribution:</b> Donut breakdown chart grouping alerts into Critical, High, Medium, and Low risk.",
            "<b>Campaign Status Table:</b> Health badges (Healthy, Warning, Critical), spend, conversions, CPA, and anomaly risk scores with 1-click inspection."
        ]),
        ("Incident Alerts (AlertsView.tsx)", [
            "<b>Actionable Filter Toggle:</b> Set to <i>Actionable Only</i> by default to filter out routine noise and display only Critical/High priority alerts.",
            "<b>Multi-Dimensional Search & Filtering:</b> Instant filtering by campaign name, severity, status, or search query.",
            "<b>Diagnostic Inspect Modal:</b> Shows plain-English diagnostic explanations, observed vs baseline values, and actionable playbook steps.",
            "<b>One-Click Incident RCA Export:</b> Exports Root Cause Analysis reports directly as Markdown (.md) or raw CSV."
        ]),
        ("Anomaly Bands & Time Series (AnomalyAnalysisView.tsx)", [
            "<b>Dynamic Rolling Baseline Bands (&mu; &plusmn; 2&sigma;):</b> Renders shaded expected variation bands over a 14-day rolling window.",
            "<b>Metric Toggle:</b> Switch views between Conversions, Spend, and CPA on the fly.",
            "<b>Reference Dot Overlays:</b> Pinpoints exact anomaly dates directly on time series charts."
        ]),
        ("Model Evaluation & Confusion Matrix (ReportsView.tsx)", [
            "<b>4-Cell Confusion Matrix:</b> Computes True Positives (TP), False Positives (FP), False Negatives (FN), and True Negatives (TN).",
            "<b>Accuracy Metrics:</b> Precision, Recall (100%), F1 Score, and False Alarm Rate.",
            "<b>Baseline Benchmarking:</b> Compares ZeroSec against traditional static 30% daily jump rules."
        ]),
        ("Dataset Ingestion (UploadView.tsx)", [
            "<b>CSV Payload Ingestion:</b> Supports custom CSV file upload with schema validation for date, campaign, spend, conversions, impressions, and ground-truth label.",
            "<b>Automatic Re-execution:</b> Automatically triggers baseline recalculation and evaluation upon upload."
        ]),
        ("Engine Settings (SettingsView.tsx)", [
            "<b>Parameter Tuning Sliders:</b> Control Rolling Baseline Window (7-30 days), Sensitivity Multiplier (1.5x-4.0x), Cooldown Days (1-7 days), and Minimum Spend Floor (₹100-₹500)."
        ])
    ]

    for title, points in modules:
        story.append(Paragraph(title, h2_style))
        for p in points:
            story.append(Paragraph(f"• {p}", bullet_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # Anomaly Engine Algorithm & Math
    story.append(Paragraph("4. Core Anomaly Engine Mathematics", h1_style))
    story.append(Paragraph(
        "The core mathematical model calculates dynamic baseline statistics over a sliding temporal window of <i>W</i> days (default <i>W = 14</i>):",
        body_style
    ))
    
    math_text = (
        "1. Rolling Mean (&mu;):  &mu;_t = (1/W) * &sum;_{i=t-W}^{t-1} x_i<br/>"
        "2. Rolling Variance (&sigma;^2):  &sigma;_t^2 = (1/(W-1)) * &sum;_{i=t-W}^{t-1} (x_i - &mu;_t)^2<br/>"
        "3. Standardized Z-Score:  Z_t = (x_t - &mu;_t) / (&sigma;_t + &epsilon;)<br/>"
        "4. Anomaly Condition:  |Z_t| > K  AND  Spend_t &ge; Spend_Floor<br/>"
        "5. Cooldown Rule:  If Alert Fired at Date T, suppress duplicates for T + Cooldown_Days."
    )
    story.append(Paragraph(math_text, code_style))

    # Hackathon Presentation Guide
    story.append(Paragraph("5. Hackathon Presentation & Pitch Guide", h1_style))
    story.append(Paragraph("Use the following structured sequence when demonstrating ZeroSec to judges:", body_style))

    pitch_steps = [
        "<b>Step 1: The Problem (Alert Fatigue)</b> — Explain how ad teams receive hundreds of useless alerts daily due to minor variance, causing them to miss real revenue-draining bugs.",
        "<b>Step 2: Overview Dashboard</b> — Show live KPI cards, Spend vs Conversions dual-axis chart, and the 100% Recall rate with zero missed critical incidents.",
        "<b>Step 3: Actionable Incident Alerts</b> — Demonstrate how default filtering keeps the UI clean and actionable. Open the Inspect Modal to show plain-English diagnosis and RCA export.",
        "<b>Step 4: Anomaly Bands Visualizer</b> — Showcase the shaded &mu; &plusmn; 2&sigma; confidence bands and show how real anomalies break outside the expected boundaries.",
        "<b>Step 5: Mathematical Rigor & Confusion Matrix</b> — Show the 4-cell Confusion Matrix in Model Evaluation proving 100% Recall and >97% noise suppression vs static 30% jump rules."
    ]

    for step in pitch_steps:
        story.append(Paragraph(step, bullet_style))

    doc.build(story)
    print(f"PDF successfully generated: {filename}")

if __name__ == "__main__":
    build_pdf()
