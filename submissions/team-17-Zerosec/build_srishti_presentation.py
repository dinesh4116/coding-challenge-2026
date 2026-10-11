import os
import pptx
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor

def clean_text_frame(tf):
    """Clean all paragraphs in a text frame down to a single empty paragraph."""
    for p in tf.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    tf.paragraphs[0].text = ""

def create_presentation():
    template_path = r'C:\Users\dell\Downloads\SRISHTI2K26_Devsprint_Template_v4.pptx'
    output_path = r'D:\Psg hackathon\ZeroSec_DevSprint_PS04_Presentation.pptx'
    submission_path = r'D:\coding-challenge-2026\submissions\team-17-Zerosec\ZeroSec_DevSprint_PS04_Presentation.pptx'

    prs = pptx.Presentation(template_path)

    COLOR_PRIMARY = RGBColor(15, 23, 42)    # Dark slate
    COLOR_BODY = RGBColor(51, 65, 85)       # Slate body
    COLOR_CALLOUT = RGBColor(67, 56, 202)   # Deep Indigo

    def format_content_card(shape, items, header_text=None):
        tf = shape.text_frame
        tf.word_wrap = True
        clean_text_frame(tf)

        first_p = tf.paragraphs[0]
        if header_text:
            first_p.text = header_text
            first_p.font.bold = True
            first_p.font.size = Pt(17)
            first_p.font.color.rgb = COLOR_PRIMARY
            first_p.space_after = Pt(10)
            
            for item in items:
                p = tf.add_paragraph()
                p.text = item
                p.font.size = Pt(13)
                p.font.color.rgb = COLOR_BODY
                p.space_after = Pt(7)
        else:
            first_p.text = items[0]
            first_p.font.size = Pt(13)
            first_p.font.color.rgb = COLOR_BODY
            first_p.space_after = Pt(7)
            for item in items[1:]:
                p = tf.add_paragraph()
                p.text = item
                p.font.size = Pt(13)
                p.font.color.rgb = COLOR_BODY
                p.space_after = Pt(7)

    def format_callout_box(shape, text):
        tf = shape.text_frame
        tf.word_wrap = True
        clean_text_frame(tf)
        p0 = tf.paragraphs[0]
        p0.text = text
        p0.font.size = Pt(12.5)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_CALLOUT

    # ==========================================
    # SLIDE 1: Title Slide
    # ==========================================
    s1 = prs.slides[0]
    # Shape 5: Project Title
    tf_title = s1.shapes[5].text_frame
    clean_text_frame(tf_title)
    p_title = tf_title.paragraphs[0]
    p_title.text = "ZeroSec: Campaign Anomaly Alerting"
    p_title.font.size = Pt(32)
    p_title.font.bold = True
    p_title.font.color.rgb = RGBColor(255, 255, 255)
    
    # Shape 6: Subtitle / Team Info
    tf_sub = s1.shapes[6].text_frame
    clean_text_frame(tf_sub)
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = "Team 17 - Zerosec   |   Problem Statement: PS-04   |   Time-Series Anomaly Intelligence"
    p_sub.font.size = Pt(14)
    p_sub.font.color.rgb = RGBColor(241, 245, 249)

    # ==========================================
    # SLIDE 2: Problem Statement
    # ==========================================
    s2 = prs.slides[1]
    s2_items = [
        "- The Situation: Digital marketing teams monitor daily continuous time-series (Spend, Conversions, CPA) across dozens of live campaigns.",
        "- Fixed-Threshold Failure: Rules like 'alert if spend moves >30%' constantly cry wolf on small campaigns where a single conversion swings numbers, while staying silently blind on large campaigns where a 10% drift is a critical emergency.",
        "- The Alert Fatigue Trap: Alerts that cry wolf get muted within a fortnight. The muted channel is exactly where real silent incidents (broken tags, 404 pages) burn budgets unnoticed.",
        "- The Real Challenge: Accurately reporting false-positive rates, distinguishing noise from incidents, and eliminating alert fatigue."
    ]
    format_content_card(s2.shapes[2], s2_items, "The Alert Fatigue Crisis in Digital Advertising")
    format_callout_box(s2.shapes[5], "Key Fact: Naive 30% jump rules fired 1,103 noisy alerts with only 1.4% precision on 180-day benchmark data.")

    # ==========================================
    # SLIDE 3: Proposed Solution
    # ==========================================
    # ==========================================
    # SLIDE 3: Proposed Solution
    # ==========================================
    s3 = prs.slides[2]
    s3_items = [
        "- Summary: An autonomous anomaly intelligence engine that derives per-campaign volatility bands (rolling median / MAD & Poisson tails) to catch real incidents while achieving 94.2% noise reduction vs naive thresholds.",
        "- Dynamic Volatility Modeling: Calculates 28-day rolling baselines per campaign rather than using an arbitrary, rigid global percentage threshold.",
        "- Intelligent Triaging: Separates true broken incidents from natural seasonal shifts, routing them to Immediate vs. Digest notification tiers.",
        "- Cooldown Suppression Shield: Automatically groups multi-day sustained anomalies and suppresses redundant alerts inside cooldown windows.",
        "- Automated Diagnosis: Every alert includes a plain-English explanation, measured evidence, and an actionable diagnostic playbook."
    ]
    format_content_card(s3.shapes[2], s3_items, "ZeroSec: Time-Series Anomaly Intelligence")
    format_callout_box(s3.shapes[5], "Flow: 180-Day Ingestion -> Rolling Median/MAD & Poisson Baselines -> Grouping & Cooldown -> Actionable Alerts")

    # ==========================================
    # SLIDE 4: Technology Stack & Implementation
    # ==========================================
    s4 = prs.slides[3]
    s4_items = [
        "- Frontend: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, Recharts (Composed time-series, confidence envelopes & evaluation matrix).",
        "- Backend & API: Python 3.10+, FastAPI REST microservice (/analyze, /demo-data, /health), Uvicorn, Pytest (96 unit tests passing, 100% green).",
        "- Statistical Core: Rolling median & MAD with Student-t small-sample correction for continuous metrics, exact Poisson tail for counts, and low-volume guards.",
        "- Step-by-Step Delivery: Statistical engine validated with 96 tests -> FastAPI microservice built -> Interactive React dashboard built -> 1-click Markdown RCA export."
    ]
    format_content_card(s4.shapes[2], s4_items, "Full-Stack Production-Ready Architecture")
    format_callout_box(s4.shapes[5], "Tech Stack: React 18 + Vite | Python FastAPI Microservice | 96 Passing Pytest Unit Tests")

    # ==========================================
    # SLIDE 5: Impact & Benefits
    # ==========================================
    s5 = prs.slides[4]
    s5_items = [
        "- 100% Immediate Alert Precision: 4 out of 4 immediate incident alerts matched real emergencies on Day 0 (zero false emergency pages).",
        "- 94.2% Alert Reduction vs Naive Baseline: Replaced 1,103 noisy alerts from naive ±30% rules with 64 managed notifications (4 immediate, 60 digest).",
        "- 178 Multi-Metric Anomalies Grouped: Correlated anomalies across spend, clicks, and conversions merged into cohesive campaign incident episodes.",
        "- 95 Repetitive Findings Suppressed: Cooldown shield prevents fatigue by suppressing recurring notifications while an outage is already acknowledged.",
        "- Automated Diagnostic Playbooks: Root cause hypotheses and step-by-step diagnostic checklists generated for every incident to streamline triage."
    ]
    format_content_card(s5.shapes[2], s5_items, "Measurable Empirical Benchmarks (Synthetic 180-Day Dataset)")
    format_callout_box(s5.shapes[5], "Empirical Impact: 94.2% Alert Reduction vs Naive Rules (64 Managed Alerts vs 1,103 Naive Fired)")

    # ==========================================
    # SLIDE 6: Prototype, Feasibility & Future Scope
    # ==========================================
    s6 = prs.slides[5]
    s6_items = [
        "- Live Prototype: Fully interactive dashboard with KPI telemetry, dynamic anomaly bands, actionable alert feed, and 4-cell confusion matrix.",
        "- Production Feasibility: Lightweight statistical algorithms run with sub-millisecond latency and zero heavy GPU or LLM operational costs.",
        "- Offline Edge Resilience: Hybrid dual-engine design runs either via FastAPI backend or standalone client-side in the browser.",
        "- Future Scope: Automated kill-switch webhooks to auto-pause bleeding ad campaigns, plus direct bi-directional Google & Meta Ads API sync."
    ]
    format_content_card(s6.shapes[2], s6_items, "Working Prototype & Future Scalability")
    
    # Place prototype preview image on Slide 6 in place of the placeholder box
    img_path = r'D:\Psg hackathon\zerosec_dashboard_preview.png'
    if os.path.exists(img_path):
        # Insert image into the right panel below the icon
        s6.shapes.add_picture(img_path, left=Inches(8.35), top=Inches(3.7), width=Inches(3.1))
        # Clear text in shape 5 so it doesn't overlap
        clean_text_frame(s6.shapes[5].text_frame)
    else:
        format_callout_box(s6.shapes[5], "Live Prototype: Interactive React + FastAPI Dashboard with 1-Click RCA & CSV Ingestion")

    # ==========================================
    # SLIDE 7: Conclusion
    # ==========================================
    s7 = prs.slides[6]
    s7_items = [
        "- Problem Solved: Replaced broken, noisy static rules with intelligent, per-campaign dynamic baselines that protect ad budgets without alert fatigue.",
        "- Transparent Accuracy: 94.2% alert noise reduction, 100% immediate alert precision, and transparently reported false-positive benchmarks.",
        "- Complete Submission: Full-stack implementation, 96 passing tests, complete documentation, and PDF functional report.",
        "- Thank You: We welcome your questions and look forward to demonstrating the live prototype!"
    ]
    format_content_card(s7.shapes[2], s7_items, "Summary & Key Takeaways")
    format_callout_box(s7.shapes[5], '"ZeroSec: Silence the noise, catch every emergency."')

    # Save presentations with fallback if original is open
    try:
        prs.save(output_path)
        print(f"Presentation saved successfully to: {output_path}")
    except PermissionError:
        alt_path = output_path.replace(".pptx", "_Updated.pptx")
        prs.save(alt_path)
        print(f"Original PPTX locked by another program. Saved to: {alt_path}")

    # Also save to coding-challenge submission directory if exists
    if os.path.exists(os.path.dirname(submission_path)):
        try:
            prs.save(submission_path)
            print(f"Presentation synced to submission repo: {submission_path}")
        except PermissionError:
            pass

if __name__ == '__main__':
    create_presentation()
