"""
TriageIQ — Campaign Intelligence Enterprise Dashboard.
Built with Python, Streamlit, Pandas, NumPy, and Altair.

Enterprise Visual Identity:
- Style: Campaign Intelligence (Sophisticated Marketing Analytics)
- Palette: Burnt Orange (#B85C38) + Sage Green (#526D50) + White (#FFFFFF) on Light Canvas (#F7F8F5)
- Typography: Clean enterprise hierarchy
- Full Contract Compliance: Decisions strictly in {PROMOTE, BLOCK, IGNORE}, needs_review boolean.
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
import io
import html
import datetime
from typing import Dict, Any, List, Optional

from triage_engine.rules import TriageEngine, AdvertiserProfile
from triage_engine.clustering import cluster_search_queries
from triage_engine.exporter import export_triage_results
from triage_engine.copilot import generate_copilot_response
from triage_engine.negatives import generate_context_aware_negative_suggestions
from triage_engine.learning import ReviewerPrecedentMemory
from run_cli import normalize_input_data

# -------------------------------------------------------------
# 1. PAGE CONFIGURATION & ENTERPRISE DESIGN SYSTEM
# -------------------------------------------------------------
st.set_page_config(
    page_title="TriageIQ — Campaign Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS (Light Theme: Burnt Orange + Sage Green + White)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html {
        scroll-behavior: smooth;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #FFFFFF;
    }
    
    .stApp {
        background-color: #08050D;
        color: #FFFFFF;
    }
    
    /* ========================================================= */
    /* TATVIC-STYLE HERO LANDING SECTION (Near-Black & Deep Purple) */
    /* ========================================================= */
    .hero-container {
        position: relative;
        background: radial-gradient(circle at 50% 16%, #18051F 0%, #08050D 68%);
        border: 1px solid rgba(160, 80, 200, 0.22);
        border-radius: 12px;
        margin-top: -1.2rem;
        margin-bottom: 2rem;
        padding: 24px 40px 65px 40px;
        overflow: hidden;
        text-align: center;
        box-sizing: border-box;
        box-shadow: 0 12px 48px rgba(8, 5, 13, 0.7);
    }
    
    /* Subtle Purple Ambient Lighting */
    .hero-ambient-glow {
        position: absolute;
        width: 650px;
        height: 650px;
        background: radial-gradient(circle, rgba(128, 0, 255, 0.22) 0%, rgba(24, 5, 31, 0.08) 50%, transparent 70%);
        top: 40px;
        left: 50%;
        transform: translateX(-50%);
        filter: blur(60px);
        pointer-events: none;
        z-index: 1;
    }
    
    .hero-ambient-left {
        position: absolute;
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, rgba(128, 0, 255, 0.14) 0%, transparent 70%);
        top: 100px;
        left: 5%;
        filter: blur(80px);
        pointer-events: none;
        z-index: 1;
    }
    
    .hero-ambient-right {
        position: absolute;
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, rgba(160, 32, 240, 0.14) 0%, transparent 70%);
        top: 100px;
        right: 5%;
        filter: blur(80px);
        pointer-events: none;
        z-index: 1;
    }

    /* Abstract Circular Arc behind Hero Content */
    .hero-arc-wrapper {
        position: absolute;
        top: 115px;
        left: 50%;
        transform: translateX(-50%);
        width: 860px;
        max-width: 90%;
        height: 480px;
        border-radius: 50% 50% 0 0 / 100% 100% 0 0;
        border-top: 1.5px solid rgba(180, 100, 255, 0.45);
        border-left: 1px solid rgba(128, 0, 255, 0.22);
        border-right: 1px solid rgba(128, 0, 255, 0.22);
        border-bottom: none;
        box-shadow: 0 -12px 50px rgba(128, 0, 255, 0.35), inset 0 8px 40px rgba(128, 0, 255, 0.16);
        background: radial-gradient(ellipse at 50% 0%, rgba(128, 0, 255, 0.14) 0%, rgba(24, 5, 31, 0.02) 60%, transparent 80%);
        pointer-events: none;
        z-index: 2;
    }

    /* Transparent Horizontal Navigation at Top */
    .hero-nav {
        position: relative;
        z-index: 10;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 12px 16px 12px;
    }
    
    .hero-logo-box {
        display: flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
    }
    
    .hero-logo-icon {
        background: #8000FF;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 0.95rem;
        width: 32px;
        height: 32px;
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 16px rgba(128, 0, 255, 0.6);
        letter-spacing: -0.02em;
    }
    
    .hero-logo-title {
        color: #FFFFFF;
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    .hero-nav-menu {
        display: flex;
        align-items: center;
        gap: 28px;
    }
    
    .hero-nav-item {
        color: #D1CBD5 !important;
        font-size: 0.88rem;
        font-weight: 500;
        text-decoration: none !important;
        transition: color 0.2s ease;
    }
    .hero-nav-item:hover {
        color: #FFFFFF !important;
    }
    
    .hero-nav-btn {
        background-color: #8000FF;
        color: #FFFFFF !important;
        font-weight: 600;
        font-size: 0.84rem;
        padding: 8px 22px;
        border-radius: 24px;
        text-decoration: none !important;
        box-shadow: 0 2px 14px rgba(128, 0, 255, 0.45);
        transition: all 0.2s ease;
        display: inline-block;
    }
    .hero-nav-btn:hover {
        background-color: #921aff;
        box-shadow: 0 4px 20px rgba(128, 0, 255, 0.65);
    }
    
    /* Thin Purple Divider below Header */
    .hero-nav-divider {
        position: relative;
        z-index: 10;
        height: 1px;
        background-color: rgba(160, 80, 200, 0.18);
        margin-bottom: 45px;
    }
    
    /* Hero Content Container */
    .hero-body {
        position: relative;
        z-index: 10;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Lavender Eyebrow Text */
    .hero-eyebrow {
        color: #D5A2FF;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 16px;
        text-shadow: 0 0 16px rgba(213, 162, 255, 0.35);
    }
    
    /* Large Two-Line Headline */
    .hero-title {
        color: #FFFFFF;
        font-size: 3.1rem;
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -0.03em;
        margin-top: 0;
        margin-bottom: 18px;
    }
    
    .hero-title-accent {
        color: #8000FF;
        background: linear-gradient(135deg, #A844FF 0%, #8000FF 55%, #6B00D6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 32px rgba(128, 0, 255, 0.4);
    }
    
    /* Muted White-Gray Supporting Description */
    .hero-desc {
        color: #D1CBD5;
        font-size: 1.05rem;
        line-height: 1.65;
        max-width: 720px;
        margin: 0 auto 34px auto;
        font-weight: 400;
    }
    
    /* Adjacent CTA Buttons */
    .hero-actions {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
        margin-top: 6px;
        margin-bottom: 6px;
    }
    
    .hero-btn-primary {
        background-color: #FFFFFF !important;
        color: #08050D !important;
        font-size: 0.95rem;
        font-weight: 700;
        padding: 13px 32px;
        border-radius: 30px;
        text-decoration: none !important;
        box-shadow: 0 4px 22px rgba(255, 255, 255, 0.22);
        transition: all 0.2s ease;
        display: inline-block;
        border: none;
    }
    .hero-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 28px rgba(255, 255, 255, 0.35);
    }
    
    .hero-btn-secondary {
        background-color: transparent !important;
        color: #FFFFFF !important;
        font-size: 0.95rem;
        font-weight: 600;
        padding: 12px 30px;
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.35);
        text-decoration: none !important;
        transition: all 0.2s ease;
        display: inline-block;
    }
    .hero-btn-secondary:hover {
        border-color: #D5A2FF;
        background-color: rgba(213, 162, 255, 0.1) !important;
        color: #D5A2FF !important;
        transform: translateY(-2px);
    }
    
    /* Global Container & Card Overrides */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #12091B !important;
        border: 1px solid rgba(160, 80, 200, 0.22) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* Streamlit Expander Dark Theme */
    div[data-testid="stExpander"] {
        background-color: #12091B !important;
        border: 1px solid rgba(160, 80, 200, 0.22) !important;
        border-radius: 10px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #FFFFFF !important;
        font-weight: 600;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #D5A2FF !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0B0713 !important;
        border-right: 1px solid rgba(160, 80, 200, 0.18) !important;
    }
    [data-testid="stSidebar"] * {
        color: #D1CBD5;
    }
    [data-testid="stSidebar"] strong, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 6px 12px;
        margin-bottom: 2px;
        transition: all 0.2s ease;
        color: #D1CBD5 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(128, 0, 255, 0.14);
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: rgba(128, 0, 255, 0.24) !important;
        border: 1px solid rgba(128, 0, 255, 0.5) !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    
    /* Input & Select Controls */
    .stTextInput input, .stSelectbox [data-baseweb="select"] > div, .stMultiSelect [data-baseweb="select"] > div {
        background-color: #160B22 !important;
        border-color: rgba(160, 80, 200, 0.3) !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
    }
    .stTextInput input:focus, .stSelectbox [data-baseweb="select"]:focus-within {
        border-color: #8000FF !important;
        box-shadow: 0 0 10px rgba(128, 0, 255, 0.45) !important;
    }
    
    /* Top Header Bar */
    .top-header {
        background: radial-gradient(circle at 50% 16%, #18051F 0%, #0E0717 100%);
        border: 1px solid rgba(160, 80, 200, 0.25);
        border-radius: 10px;
        padding: 18px 24px;
        margin-top: -1.2rem;
        margin-bottom: 1.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 24px rgba(8, 5, 13, 0.5);
    }
    .header-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .header-subtitle {
        font-size: 0.88rem;
        color: #D1CBD5;
        margin-top: 3px;
        margin-bottom: 0;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        background-color: rgba(16, 185, 129, 0.16);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.38);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    
    /* Brand Mark in Sidebar */
    .brand-mark {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0 14px 0;
        border-bottom: 1px solid rgba(160, 80, 200, 0.2);
        margin-bottom: 14px;
    }
    .brand-icon {
        background-color: #8000FF;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 1.05rem;
        width: 34px;
        height: 34px;
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        letter-spacing: -0.03em;
        box-shadow: 0 0 16px rgba(128, 0, 255, 0.6);
    }
    .brand-text {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .brand-subtext {
        font-size: 0.72rem;
        color: #D5A2FF;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    
    /* Tag Badges */
    .tag-promote { background-color: rgba(16, 185, 129, 0.16); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.38); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.76rem; }
    .tag-block   { background-color: rgba(239, 68, 68, 0.16); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.38); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.76rem; }
    .tag-ignore  { background-color: rgba(156, 163, 175, 0.14); color: #9CA3AF; border: 1px solid rgba(156, 163, 175, 0.3); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.76rem; }
    .tag-review  { background-color: rgba(245, 158, 11, 0.16); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.38); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.76rem; }
    .tag-neutral { background-color: rgba(128, 0, 255, 0.16); color: #D5A2FF; border: 1px solid rgba(128, 0, 255, 0.38); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.76rem; }
    
    /* Sidebar Navigation item custom styling */
    div[data-testid="stSidebarNav"] { display: none; }
    
    /* Clean button styling */
    .stButton>button {
        background-color: #8000FF !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(180, 100, 255, 0.4) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem;
        box-shadow: 0 2px 12px rgba(128, 0, 255, 0.4) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #921AFF !important;
        box-shadow: 0 4px 20px rgba(128, 0, 255, 0.65) !important;
        transform: translateY(-1px);
    }
    
    .stDownloadButton>button {
        background-color: #1A0D28 !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(160, 80, 200, 0.35) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton>button:hover {
        background-color: #26133B !important;
        border-color: #8000FF !important;
        color: #D5A2FF !important;
        box-shadow: 0 2px 14px rgba(128, 0, 255, 0.3) !important;
    }
    
    /* ========================================================= */
    /* PERSONAL AI COPILOT FLOATING BUTTON & POPUP MODAL STYLES  */
    /* ========================================================= */
    div.st-key-floating_copilot_btn {
        position: fixed !important;
        bottom: 28px !important;
        right: 32px !important;
        z-index: 999999 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div.st-key-floating_copilot_btn > button {
        background: linear-gradient(135deg, #8000FF 0%, #4B0099 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(213, 162, 255, 0.45) !important;
        border-radius: 30px !important;
        padding: 12px 24px !important;
        font-size: 0.94rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 8px 32px rgba(128, 0, 255, 0.55), 0 0 15px rgba(128, 0, 255, 0.3) !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div.st-key-floating_copilot_btn > button:hover {
        transform: translateY(-3px) scale(1.05) !important;
        box-shadow: 0 12px 38px rgba(128, 0, 255, 0.75), 0 0 25px rgba(213, 162, 255, 0.5) !important;
        border-color: #D5A2FF !important;
        background: linear-gradient(135deg, #931AFF 0%, #5B00B3 100%) !important;
    }

    /* Modal Dialog Overrides */
    div[data-baseweb="modal"] > div, div[role="dialog"] {
        background-color: #0E0717 !important;
        border: 1px solid rgba(160, 80, 200, 0.35) !important;
        border-radius: 14px !important;
        box-shadow: 0 16px 50px rgba(0, 0, 0, 0.85), 0 0 30px rgba(128, 0, 255, 0.25) !important;
        color: #FFFFFF !important;
    }
    div[data-baseweb="modal"] header, div[role="dialog"] header, div[role="dialog"] h2 {
        color: #FFFFFF !important;
    }
    div[data-baseweb="modal"] button[aria-label="Close"], div[role="dialog"] button[aria-label="Close"] {
        color: #D5A2FF !important;
    }

    /* Chat Messages inside Copilot */
    div[data-testid="stChatMessage"] {
        background-color: #140A1F !important;
        border: 1px solid rgba(160, 80, 200, 0.22) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        margin-bottom: 8px !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stChatMessage"] * {
        color: #E2DCF0 !important;
    }
    div[data-testid="stChatMessage"] strong, div[data-testid="stChatMessage"] h1, div[data-testid="stChatMessage"] h2, div[data-testid="stChatMessage"] h3, div[data-testid="stChatMessage"] h4 {
        color: #FFFFFF !important;
    }
    div[data-testid="stChatMessage"] code {
        background-color: #200E33 !important;
        color: #D5A2FF !important;
        border: 1px solid rgba(160, 80, 200, 0.3) !important;
        padding: 2px 5px !important;
        border-radius: 4px !important;
    }
    div[data-testid="stChatInput"] {
        border-radius: 10px !important;
    }
    div[data-testid="stChatInput"] textarea {
        background-color: #160B22 !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(160, 80, 200, 0.35) !important;
        border-radius: 8px !important;
    }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: #8000FF !important;
        box-shadow: 0 0 12px rgba(128, 0, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. SESSION STATE & ENGINE INITIALIZATION
# -------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = TriageEngine()
if "reviewer_actions" not in st.session_state:
    st.session_state.reviewer_actions = {}
if "precedent_memory" not in st.session_state:
    st.session_state.precedent_memory = ReviewerPrecedentMemory()
if "negative_approvals" not in st.session_state:
    st.session_state.negative_approvals = {}
if "selected_view" not in st.session_state:
    st.session_state.selected_view = "Campaign Intelligence"
if "custom_csv_df" not in st.session_state:
    st.session_state.custom_csv_df = None
if "custom_csv_name" not in st.session_state:
    st.session_state.custom_csv_name = None

def parse_csv_file(file_obj) -> Optional[pd.DataFrame]:
    """
    Robustly parses an uploaded CSV file handling byte seeks, encodings, delimiters, and Google Ads headers.
    """
    if file_obj is None:
        return None
    if isinstance(file_obj, pd.DataFrame):
        return file_obj

    raw_bytes = None
    try:
        if hasattr(file_obj, "getvalue"):
            raw_bytes = file_obj.getvalue()
        elif hasattr(file_obj, "read"):
            file_obj.seek(0)
            raw_bytes = file_obj.read()
        elif isinstance(file_obj, (bytes, bytearray)):
            raw_bytes = bytes(file_obj)
    except Exception:
        return None

    if not raw_bytes or len(raw_bytes) == 0:
        return None

    def has_relevant_cols(d: pd.DataFrame) -> bool:
        cols_str = " ".join([str(c).lower() for c in d.columns])
        return any(k in cols_str for k in ["query", "search", "term", "click", "cost", "spend", "impr", "conv"])

    # 1. Standard encodings
    for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]:
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
            if df is not None and not df.empty and len(df.columns) > 1 and has_relevant_cols(df):
                return df
        except Exception:
            continue

    # 2. Skip metadata/title rows (common in Google Ads UI CSV reports)
    for skip in [1, 2, 3, 4]:
        for enc in ["utf-8", "latin1"]:
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, skiprows=skip)
                if df is not None and not df.empty and len(df.columns) > 1 and has_relevant_cols(df):
                    return df
            except Exception:
                continue

    # 3. Alternate delimiters (semicolon, tab, pipe)
    for sep in [";", "\t", "|"]:
        for enc in ["utf-8", "latin1"]:
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, sep=sep)
                if df is not None and not df.empty and len(df.columns) > 1 and has_relevant_cols(df):
                    return df
            except Exception:
                continue

    # 4. Fallback with python engine and on_bad_lines
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), encoding="latin1", on_bad_lines="skip", engine="python")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    return None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "👋 **Hello! I'm your TriageIQ Personal AI Copilot.** I analyze all 25,000 search terms, Wilson statistical confidence bounds, and Kestrel commercial policies in real time.\n\nAsk me about any query (e.g. *'Audit row #6'* or *'Check equipment loan'*), cost savings calculations, small-sample noise rules, or policy thresholds!"
        }
    ]
if "show_copilot" not in st.session_state:
    st.session_state.show_copilot = False

def on_dismiss_copilot():
    st.session_state.show_copilot = False

@st.dialog("✨ TriageIQ Personal AI Copilot", width="large", on_dismiss=on_dismiss_copilot)
def render_copilot_modal(res_df: pd.DataFrame, clean_df: pd.DataFrame, target_cpa: float = 220.0):
    st.markdown("""
    <div style='background: radial-gradient(circle at 50% 0%, #1E082D 0%, #0E0717 100%); border: 1px solid rgba(160, 80, 200, 0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <div style='font-size: 1.15rem; font-weight: 700; color: #FFFFFF;'>🤖 Personal Search-Term Copilot</div>
            <div style='background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34D399; font-size: 0.75rem; font-weight: 600; padding: 3px 10px; border-radius: 20px;'>🟢 Online · 25,000 Terms Grounded</div>
        </div>
        <div style='font-size: 0.83rem; color: #D1CBD5; margin-top: 5px; line-height: 1.4;'>
            Real-time statistical triage assistant. Inspect any search query, calculate recoverable media waste, or evaluate Wilson score confidence bounds.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Starter Prompts
    st.markdown("<div style='font-size: 0.76rem; font-weight: 700; color: #D5A2FF; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;'>💡 Instant Starter Prompts</div>", unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    p4, p5, p6 = st.columns(3)
    
    prompt_clicked = None
    with p1:
        if st.button("🔍 Audit Row #6", key="modal_p_r6", use_container_width=True):
            prompt_clicked = "Audit Row #6"
    with p2:
        if st.button("💰 Calculate Cost Savings", key="modal_p_savings", use_container_width=True):
            prompt_clicked = "How much wasted spend can we save?"
    with p3:
        if st.button("⚠️ Why 1 Conv is Quarantined", key="modal_p_noise", use_container_width=True):
            prompt_clicked = "Why is 1 conversion quarantined in review?"
    with p4:
        if st.button("🚀 Top Promoted Keywords", key="modal_p_prom", use_container_width=True):
            prompt_clicked = "Show me top promoted keywords"
    with p5:
        if st.button("🎯 Explain Kestrel CPA Rules", key="modal_p_kestrel", use_container_width=True):
            prompt_clicked = "Explain Kestrel advertiser policy and CPA ceiling"
    with p6:
        if st.button("🗑️ Reset Chat", key="modal_p_reset", use_container_width=True):
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "👋 Chat reset! Ask me anything about any search term (e.g. *'Audit row #6'* or *'Check equipment loans'*), budget savings, or policy rules!"
                }
            ]
            st.rerun()

    if prompt_clicked:
        st.session_state.chat_history.append({"role": "user", "content": prompt_clicked})
        ans = generate_copilot_response(prompt_clicked, res_df, clean_df, target_cpa=target_cpa)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()

    st.markdown("<hr style='border:none; border-top: 1px solid rgba(160, 80, 200, 0.22); margin: 12px 0;'>", unsafe_allow_html=True)

    chat_box = st.container(height=340)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_query = st.chat_input("Ask about any query, row #, savings, or policy rule...", key="modal_chat_input")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        ans = generate_copilot_response(user_query, res_df, clean_df, target_cpa=target_cpa)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()

# Dataset Paths (Relative with fallback)
local_prod_path = os.path.join(os.path.dirname(__file__), "data", "production_search_terms_25k.csv")
fallback_prod_path = r"C:\Users\richr\Downloads\Srishti-2K26-Datasets-All\PS-01_search_term_triage_dataset\PS-01_search_term_triage\search_terms_report.csv"
PRODUCTION_DATA_PATH = local_prod_path if os.path.exists(local_prod_path) else fallback_prod_path
sample_data_path = os.path.join(os.path.dirname(__file__), "data", "search_terms_25k.csv")

# -------------------------------------------------------------
# 3. SIDEBAR NAVIGATION & SETTINGS
# -------------------------------------------------------------
with st.sidebar:
    # Brand Identity
    st.html("""<div class="brand-mark">
    <div class="brand-icon">IQ</div>
    <div>
        <div class="brand-text">TriageIQ</div>
        <div class="brand-subtext">Campaign Intelligence</div>
    </div>
</div>""")
    
    st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#68736B; text-transform:uppercase; margin-bottom:6px;'>Navigation</p>", unsafe_allow_html=True)
    
    nav_options = [
        "📊 Campaign Intelligence",
        "⚠️ Human Review Queue",
        "🧩 Intent Clusters",
        "📋 All Decisions",
        "📥 Google Ads Exports",
        "✨ AI Search Copilot"
    ]
    
    # Track current view index
    current_selected = st.session_state.get("selected_view", "Campaign Intelligence")
    default_index = 0
    for idx, opt in enumerate(nav_options):
        if current_selected in opt:
            default_index = idx
            break
            
    chosen_nav = st.radio("Navigation Menu", nav_options, index=default_index, label_visibility="collapsed")
    current_view = chosen_nav.split(" ", 1)[1]
    st.session_state.selected_view = current_view
    
    st.markdown("""
    <div style='background: radial-gradient(circle at 50% 0%, #1E0B30 0%, #10061A 100%); border: 1px solid rgba(160, 80, 200, 0.35); border-radius: 10px; padding: 12px; margin-top: 14px; margin-bottom: 8px;'>
        <div style='display:flex; align-items:center; gap:8px;'>
            <div style='font-size:1.25rem;'>✨</div>
            <div>
                <div style='font-weight:700; font-size:0.86rem; color:#FFFFFF;'>Personal AI Copilot</div>
                <div style='font-size:0.72rem; color:#D5A2FF;'>Grounded in 25,000 queries</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("💬 Pop Up AI Copilot", key="sidebar_copilot_modal_btn", use_container_width=True):
        st.session_state.show_copilot = True
        st.rerun()
    
    st.markdown("---")
    
    # Collapsible Settings & Data Controls (Keeps sidebar clean)
    with st.expander("⚙️ Settings & Policy Parameters", expanded=True):
        st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#D5A2FF; text-transform:uppercase; margin-bottom:6px;'>Data Source</p>", unsafe_allow_html=True)
        source_options = ["📁 Upload Custom CSV"]
        if os.path.exists(PRODUCTION_DATA_PATH):
            source_options.append("Kestrel Business Funding (90-Day Production Report)")
        if os.path.exists(sample_data_path):
            source_options.append("🧪 Standard Benchmark (25k)")
            
        default_idx = 0
        if "selected_source_override" in st.session_state and st.session_state.selected_source_override in source_options:
            default_idx = source_options.index(st.session_state.selected_source_override)
            del st.session_state["selected_source_override"]
            
        selected_source = st.selectbox("Select Dataset", source_options, index=default_idx)
        
        if selected_source == "📁 Upload Custom CSV":
            uploaded_file = st.file_uploader("Upload Search Terms CSV", type=["csv"], key="sidebar_csv_uploader", label_visibility="collapsed")
            if uploaded_file is not None:
                if st.session_state.custom_csv_name != uploaded_file.name or st.session_state.custom_csv_df is None:
                    parsed_df = parse_csv_file(uploaded_file)
                    if parsed_df is not None:
                        st.session_state.custom_csv_df = parsed_df
                        st.session_state.custom_csv_name = uploaded_file.name
                        st.rerun()
                        
            if st.session_state.custom_csv_df is not None:
                st.markdown(f"""<div style='font-size:0.74rem; color:#D1CBD5; margin-top:4px; margin-bottom:6px; padding:6px 10px; background:rgba(52,211,153,0.1); border:1px solid rgba(52,211,153,0.25); border-radius:6px;'>
                    Loaded: <strong style='color:#34D399;'>{st.session_state.custom_csv_name or 'Uploaded File'}</strong> ({len(st.session_state.custom_csv_df):,} rows)
                </div>""", unsafe_allow_html=True)
                if st.button("🗑️ Clear / Upload Different File", key="btn_sidebar_clear_csv", use_container_width=True):
                    st.session_state.custom_csv_df = None
                    st.session_state.custom_csv_name = None
                    st.rerun()
            
        st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#D5A2FF; text-transform:uppercase; margin-top:12px; margin-bottom:6px;'>Evidence & CPA Policy</p>", unsafe_allow_html=True)
        
        target_cpa = st.number_input(
            "Target CPA Ceiling ($)",
            min_value=10.0,
            max_value=1000.0,
            value=220.0,
            step=10.0,
            help="Derived from account economics. Caps allowable cost per conversion."
        )
        
        min_clicks = st.slider(
            "Min Clicks (Evidence Gate)",
            min_value=5,
            max_value=30,
            value=10,
            help="Explicit minimum evidence requirement before promotion is considered."
        )
        
        min_convs = st.slider(
            "Min Conversions",
            min_value=1,
            max_value=5,
            value=2,
            help="Single conversions are treated as potential variance noise."
        )
        
        confidence_level = st.selectbox(
            "Wilson Confidence Level",
            [0.90, 0.95, 0.99],
            index=1,
            help="Asymmetric binomial confidence bounds."
        )
        
        st.html("""<div style="font-size: 0.74rem; color: #D1CBD5; line-height: 1.4; margin-top: 10px; padding: 10px; background-color: #150C22; border: 1px solid rgba(160, 80, 200, 0.25); border-radius: 8px;">
    <strong style="color: #FFFFFF;">Advertiser Boundaries:</strong><br>
    <em style="color: #D5A2FF;">Kestrel Business Funding</em><br>
    Exclusions: Personal loans, mortgages, car loans, student loans, grants, jobs.
</div>""")

# -------------------------------------------------------------
# 4. DATA INGESTION & PIPELINE EXECUTION
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_benchmark_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def load_and_prepare_data(source_choice: str):
    if source_choice == "📁 Upload Custom CSV":
        if st.session_state.custom_csv_df is not None:
            return st.session_state.custom_csv_df, (st.session_state.custom_csv_name or "Custom Uploaded File")
        return None, "Awaiting file upload"
    elif source_choice.startswith("Kestrel"):
        if os.path.exists(PRODUCTION_DATA_PATH):
            return load_benchmark_data(PRODUCTION_DATA_PATH), "Kestrel Business Funding (90-Day Production Report)"
        elif os.path.exists(fallback_prod_path):
            return load_benchmark_data(fallback_prod_path), "Kestrel Business Funding (90-Day Production Report)"
        elif os.path.exists(sample_data_path):
            return load_benchmark_data(sample_data_path), "Standard Benchmark (25k)"
    elif os.path.exists(sample_data_path):
        return load_benchmark_data(sample_data_path), "Standard Benchmark (25k)"
    return None, "Dataset Not Available"

raw_df, dataset_name = load_and_prepare_data(selected_source)

if raw_df is None:
    st.markdown("""
    <div style='background: radial-gradient(circle at 50% 16%, #1E082D 0%, #0E0717 100%); border: 1px solid rgba(160, 80, 200, 0.28); border-radius: 12px; padding: 28px 32px; margin: 30px auto; max-width: 780px; text-align: center;'>
        <div style='font-size: 2.2rem; margin-bottom: 8px;'>📁</div>
        <div style='font-size: 1.4rem; font-weight: 700; color: #FFFFFF;'>Upload Search Terms Report (CSV)</div>
        <div style='font-size: 0.88rem; color: #D1CBD5; margin-top: 6px; line-height: 1.5;'>
            Upload any Google Ads Search Term report to run automated triage (<span style='color:#34D399; font-weight:600;'>PROMOTE</span>, <span style='color:#F87171; font-weight:600;'>BLOCK</span>, <span style='color:#9CA3AF; font-weight:600;'>IGNORE</span>), Wilson confidence intervals, and near-duplicate intent clustering.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_u1, col_u2, col_u3 = st.columns([1, 2, 1])
    with col_u2:
        main_upload = st.file_uploader("Upload Search Terms CSV", type=["csv"], key="main_stage_csv_uploader", label_visibility="collapsed")
        if main_upload is not None:
            if st.session_state.custom_csv_name != main_upload.name or st.session_state.custom_csv_df is None:
                parsed_df = parse_csv_file(main_upload)
                if parsed_df is not None:
                    st.session_state.custom_csv_df = parsed_df
                    st.session_state.custom_csv_name = main_upload.name
                    st.rerun()
                else:
                    st.error("⚠️ Could not parse search terms from this file. Please verify it is a valid CSV.")
            
        st.markdown("<div style='text-align: center; margin: 18px 0 10px 0; color: #A79BB3; font-size: 0.8rem; font-weight: 600;'>— OR BENCHMARK DATASET —</div>", unsafe_allow_html=True)
        if st.button("🚀 Load 25,000-Row Production Benchmark", key="btn_quick_load_bench", use_container_width=True):
            st.session_state.selected_source_override = "Kestrel Business Funding (90-Day Production Report)"
            st.rerun()
            
    if raw_df is None:
        st.stop()

# Cached high-performance triage execution pipeline for instant web response
@st.cache_data(show_spinner=False)
def run_triage_pipeline(
    raw_df: pd.DataFrame,
    target_cpa: float,
    min_clicks: int,
    min_convs: int
):
    clean_df = normalize_input_data(raw_df)

    campaign_target_cpas = {}
    camp_summary = clean_df.groupby("campaign").agg({"cost": "sum", "conversions": "sum"})
    for camp_name, r in camp_summary.iterrows():
        camp_cpa = round(r["cost"] / max(1.0, r["conversions"]), 2)
        campaign_target_cpas[camp_name] = camp_cpa

    engine = TriageEngine(
        target_cpa=target_cpa,
        campaign_target_cpas=campaign_target_cpas,
        min_clicks_for_promotion=min_clicks,
        min_conversions_for_promotion=min_convs
    )

    records = clean_df.to_dict(orient="records")
    evaluated_records = []
    for r in records:
        eval_res = engine.evaluate_query(r)
        merged = {**r, **eval_res}
        evaluated_records.append(merged)

    clusters_summary, records = cluster_search_queries(evaluated_records)
    results = records
    res_df = pd.DataFrame(results)
    return clean_df, clusters_summary, results, res_df

clean_df, clusters_summary, results, res_df = run_triage_pipeline(
    raw_df, target_cpa, min_clicks, min_convs
)

# Apply active reviewer corrections from session memory with sub-millisecond overhead
if st.session_state.reviewer_actions:
    res_df = res_df.copy()
    results = [dict(r) for r in results]
    res_lookup = {r["query_text"].lower().strip(): r for r in results}
    for q_norm, ov in st.session_state.reviewer_actions.items():
        mask = res_df["query_text"].str.lower().str.strip() == q_norm
        if mask.any():
            res_df.loc[mask, "decision"] = ov["final_decision"]
            res_df.loc[mask, "needs_review"] = False
            res_df.loc[mask, "confidence"] = "HIGH"
            res_df.loc[mask, "reason"] = f"Reviewer override: {ov.get('reviewer_notes', 'Analyst verified')}"
        if q_norm in res_lookup:
            res_lookup[q_norm]["decision"] = ov["final_decision"]
            res_lookup[q_norm]["needs_review"] = False
            res_lookup[q_norm]["confidence"] = "HIGH"
            res_lookup[q_norm]["reason"] = f"Reviewer override: {ov.get('reviewer_notes', 'Analyst verified')}"

# Context-Aware Negative Keyword Suggestions (Enhancement A)
adv_profile = AdvertiserProfile()
negative_suggestions = generate_context_aware_negative_suggestions(res_df, adv_profile, target_cpa=target_cpa)
for s in negative_suggestions:
    if s["suggestion_id"] in st.session_state.negative_approvals:
        s["analyst_status"] = st.session_state.negative_approvals[s["suggestion_id"]]

# Core Metrics
total_queries = len(res_df)
promoted_count = int((res_df["decision"] == "PROMOTE").sum())
blocked_count = int((res_df["decision"] == "BLOCK").sum())
ignored_count = int((res_df["decision"] == "IGNORE").sum())
review_needed_count = int(res_df["needs_review"].sum())

# Defensible Financial Metrics
historical_blocked_spend = float(res_df[res_df["decision"] == "BLOCK"]["cost"].sum())
attributed_promoted_conv = int(res_df[res_df["decision"] == "PROMOTE"]["conversions"].sum())
attributed_promoted_val = float(res_df[res_df["decision"] == "PROMOTE"]["conversion_value"].sum())

# -------------------------------------------------------------
# 5. REUSABLE NATIVE EVIDENCE CARD RENDERER
# (Aligned with PS-01 Hackathon Contract: Query, Badges, Metrics, Prominent Reason & Collapsible Evidence)
# -------------------------------------------------------------
def render_evidence_card(row_data: Any, is_review_queue: bool = False, key_prefix: str = "card"):
    """
    Renders a compact, clean, and evidence-first recommendation card.
    Information Hierarchy:
    1. Header: Query + Decision Badge + Confidence + Needs Review + Campaign Context
    2. Metrics Row: Clicks, Spend, Conversions, Conversion Value, CPA (when meaningful), Wilson 95% CI
    3. Reason: One clear human-readable sentence prominently visible without expanding
    4. Additional Evidence: Collapsible expander for Supporting Evidence, Limitations & Action Plan
    5. Action Buttons (if in review queue): Approve, Block, Dismiss
    """
    row_id = row_data.get("row_id", 0)
    query_text = str(row_data.get("query_text", "")).strip()
    decision = str(row_data.get("decision", "IGNORE")).strip()
    needs_review = bool(row_data.get("needs_review", False))
    confidence = str(row_data.get("confidence", "MEDIUM")).strip()
    campaign = str(row_data.get("campaign", "")).strip()
    ad_group = str(row_data.get("ad_group", "")).strip()
    match_type = str(row_data.get("match_type", "Broad")).strip()
    
    clicks = int(row_data.get("clicks", 0))
    cost = float(row_data.get("cost", 0.0))
    conversions = float(row_data.get("conversions", 0.0))
    conv_val = float(row_data.get("conversion_value", 0.0))
    raw_cvr = float(row_data.get("raw_cvr", 0.0))
    ci_lower = float(row_data.get("ci_lower", 0.0))
    ci_upper = float(row_data.get("ci_upper", 0.0))
    cpa = row_data.get("cpa")
    
    # Meaningful CPA display: only show when conversions > 0
    cpa_str = f"${cpa:,.2f}" if (cpa is not None and pd.notnull(cpa) and conversions > 0) else "—"
    
    # Statistical uncertainty display
    ci_str = f"[{ci_lower:.1%}, {ci_upper:.1%}]" if clicks > 0 else "N/A"
    
    supp_ev = str(row_data.get("supporting_evidence", "")).strip()
    counter_ev = str(row_data.get("counterevidence", "")).strip()
    reason = str(row_data.get("reason", "")).strip()
    next_action = str(row_data.get("next_action", "")).strip()
    
    with st.container(border=True):
        # 1. HEADER ROW: Query, Badges, Campaign & Ad Group
        col_hdr_left, col_hdr_right = st.columns([3, 2])
        
        with col_hdr_left:
            dec_color_map = {
                "PROMOTE": ("rgba(16, 185, 129, 0.16)", "#34D399", "rgba(16, 185, 129, 0.38)"),
                "BLOCK": ("rgba(239, 68, 68, 0.16)", "#F87171", "rgba(239, 68, 68, 0.38)"),
                "IGNORE": ("rgba(156, 163, 175, 0.14)", "#9CA3AF", "rgba(156, 163, 175, 0.3)")
            }
            bg, fg, bd = dec_color_map.get(decision, ("rgba(156, 163, 175, 0.14)", "#9CA3AF", "rgba(156, 163, 175, 0.3)"))
            dec_badge = f"<span style='background-color:{bg}; color:{fg}; border:1px solid {bd}; padding:2px 8px; border-radius:4px; font-weight:700; font-size:0.75rem; letter-spacing:0.03em;'>{decision}</span>"
            
            review_badge = ""
            if needs_review:
                review_badge = "<span style='background-color:rgba(245, 158, 11, 0.16); color:#FBBF24; border:1px solid rgba(245, 158, 11, 0.38); padding:2px 8px; border-radius:4px; font-weight:700; font-size:0.75rem; margin-left:6px;'>NEEDS REVIEW</span>"
                
            conf_badge = f"<span style='font-size:0.78rem; color:#D1CBD5; margin-left:8px;'>Confidence: <strong style='color:#FFFFFF;'>{confidence}</strong></span>"
            
            st.markdown(
                f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:6px;'>"
                f"<span style='font-size:1.02rem; font-weight:700; color:#FFFFFF;'>#{row_id}</span> "
                f"<code style='font-size:0.92rem; font-weight:600; color:#FFFFFF; background-color:#1E1030; padding:2px 6px; border-radius:4px; border:1px solid rgba(160, 80, 200, 0.35);'>{html.escape(query_text)}</code> "
                f"{dec_badge} {review_badge} {conf_badge}"
                f"</div>",
                unsafe_allow_html=True
            )
            
        with col_hdr_right:
            st.markdown(
                f"<div style='text-align:right; font-size:0.8rem; color:#D1CBD5; padding-top:4px;'>"
                f"<span>{html.escape(campaign)}</span> &nbsp;›&nbsp; <em style='color:#D5A2FF;'>{html.escape(ad_group)}</em> ({html.escape(match_type)})"
                f"</div>",
                unsafe_allow_html=True
            )
            
        # 2. METRICS ROW (Compact, responsive flex row)
        st.markdown(
            f"<div style='font-size:0.79rem; color:#D1CBD5; background-color:#0E0716; padding:6px 14px; border-radius:6px; margin-top:8px; margin-bottom:8px; border:1px solid rgba(160, 80, 200, 0.22); display:flex; flex-wrap:wrap; gap:16px; align-items:center;'>"
            f"<span>Clicks: <strong style='color:#FFFFFF;'>{clicks:,}</strong></span>"
            f"<span>Spend: <strong style='color:#FFFFFF;'>${cost:,.2f}</strong></span>"
            f"<span>Conversions: <strong style='color:#FFFFFF;'>{int(conversions):,}</strong></span>"
            f"<span>Attributed Value: <strong style='color:#FFFFFF;'>${conv_val:,.2f}</strong></span>"
            f"<span>CPA: <strong style='color:#FFFFFF;'>{cpa_str}</strong></span>"
            f"<span>Wilson 95% CI: <strong style='color:#FFFFFF;'>{ci_str}</strong></span>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # 3. REASON (Prominently visible directly on the card without expanding)
        dec_accent = "#34D399" if decision == "PROMOTE" else ("#F87171" if decision == "BLOCK" else ("#FBBF24" if needs_review else "#9CA3AF"))
        st.markdown(
            f"<div style='margin-top:6px; margin-bottom:10px; font-size:0.85rem; color:#FFFFFF; line-height:1.45; padding:8px 14px; background-color:#140A1F; border-left:3.5px solid {dec_accent}; border-top:1px solid rgba(160, 80, 200, 0.22); border-right:1px solid rgba(160, 80, 200, 0.22); border-bottom:1px solid rgba(160, 80, 200, 0.22); border-radius:0 6px 6px 0;'>"
            f"<strong style='color:#D5A2FF;'>Reason:</strong> {html.escape(reason)}"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # 4. ADDITIONAL EVIDENCE (Compact, Expandable Section)
        with st.expander("🔎 Supporting Evidence, Limitations & Action Plan", expanded=False):
            col_supp, col_count = st.columns(2)
            with col_supp:
                st.markdown(
                    f"<div style='background-color:rgba(16, 185, 129, 0.08); border:1px solid rgba(16, 185, 129, 0.25); border-radius:6px; padding:10px 14px; height:100%;'>"
                    f"<div style='font-size:0.75rem; font-weight:700; color:#34D399; margin-bottom:4px; letter-spacing:0.04em;'>🟢 SUPPORTING EVIDENCE</div>"
                    f"<div style='font-size:0.82rem; color:#F3EFF7; line-height:1.4;'>{html.escape(supp_ev)}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_count:
                st.markdown(
                    f"<div style='background-color:rgba(239, 68, 68, 0.08); border:1px solid rgba(239, 68, 68, 0.25); border-radius:6px; padding:10px 14px; height:100%;'>"
                    f"<div style='font-size:0.75rem; font-weight:700; color:#F87171; margin-bottom:4px; letter-spacing:0.04em;'>🔴 COUNTEREVIDENCE & LIMITATIONS</div>"
                    f"<div style='font-size:0.82rem; color:#F3EFF7; line-height:1.4;'>{html.escape(counter_ev)}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
            st.markdown(
                f"<div style='margin-top:10px; font-size:0.82rem; color:#D1CBD5; line-height:1.45;'>"
                f"<strong style='color:#FFFFFF;'>Recommended Next Action:</strong> <span style='color:#D5A2FF; font-weight:600;'>{html.escape(next_action)}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # Check for reviewer precedent match (Enhancement C)
        precedent = None
        try:
            precedent = st.session_state.precedent_memory.find_best_precedent(query_text, target_campaign=campaign)
        except TypeError:
            try:
                precedent = st.session_state.precedent_memory.find_best_precedent(query_text)
            except Exception:
                precedent = None
        except Exception:
            precedent = None
        if precedent and precedent.get("similarity", 0) >= 0.45:
            sim_pct = int(precedent["similarity"] * 100)
            rev_dec = precedent["revised_decision"]
            rev_color = "#34D399" if rev_dec == "PROMOTE" else ("#F87171" if rev_dec == "BLOCK" else "#D1CBD5")
            st.markdown(
                f"<div style='background:rgba(128, 0, 255, 0.09); border:1px solid rgba(160, 80, 200, 0.35); border-radius:6px; padding:8px 12px; margin-top:8px; margin-bottom:8px;'>"
                f"<div style='font-size:0.75rem; font-weight:700; color:#D5A2FF; letter-spacing:0.04em;'>💡 CONTEXTUAL REVIEWER PRECEDENT ({sim_pct}% SIMILARITY)</div>"
                f"<div style='font-size:0.82rem; color:#F3EFF7; margin-top:2px;'>"
                f"Previous reviewer overrode similar query <code style='background-color:#1E1030; color:#FFFFFF; padding:1px 5px; border-radius:3px;'>{html.escape(precedent['query_text'])}</code> to "
                f"<strong style='color:{rev_color};'>{rev_dec}</strong>. Rationale: <em>\"{html.escape(precedent.get('reason', 'Analyst verified'))}\"</em>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # 5. REVIEWER ACTIONS (If in Review Queue)
        if is_review_queue:
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            has_valid_precedent = precedent and precedent.get("similarity", 0) >= 0.45 and precedent.get("revised_decision") != decision
            
            if has_valid_precedent:
                b_prec, b1, b2, b3 = st.columns([1.8, 1.4, 1.4, 1.4])
                with b_prec:
                    if st.button(f"⚡ Apply Precedent ({precedent['revised_decision']})", key=f"btn_prec_{key_prefix}_{row_id}", type="primary", use_container_width=True):
                        notes = f"Precedent applied from '{precedent['query_text']}': {precedent.get('reason', '')}"
                        st.session_state.reviewer_actions[query_text.lower().strip()] = {
                            "reviewer_action": f"APPLIED_PRECEDENT_{precedent['revised_decision']}",
                            "final_decision": precedent["revised_decision"],
                            "reviewer_notes": notes,
                            "reviewer": "Analyst (Precedent Guided)"
                        }
                        st.session_state.precedent_memory.record_correction(
                            query_text=query_text,
                            campaign=campaign,
                            ad_group=ad_group,
                            original_decision=decision,
                            revised_decision=precedent["revised_decision"],
                            reason=notes,
                            reviewer="Analyst (Precedent Guided)",
                            metrics={"clicks": clicks, "cost": cost, "conversions": conversions}
                        )
                        st.toast(f"✓ Applied precedent: '{query_text}' -> {precedent['revised_decision']}!", icon="⚡")
                        st.rerun()
            else:
                b1, b2, b3 = st.columns([1.5, 1.5, 3])
                
            with b1:
                if st.button("✅ Approve Promotion", key=f"btn_prom_{key_prefix}_{row_id}", use_container_width=True):
                    notes = "Analyst verified commercial intent warrants promotion."
                    st.session_state.reviewer_actions[query_text.lower().strip()] = {
                        "reviewer_action": "APPROVED_PROMOTION",
                        "final_decision": "PROMOTE",
                        "reviewer_notes": notes,
                        "reviewer": "Human Analyst"
                    }
                    st.session_state.precedent_memory.record_correction(
                        query_text=query_text,
                        campaign=campaign,
                        ad_group=ad_group,
                        original_decision=decision,
                        revised_decision="PROMOTE",
                        reason=notes,
                        reviewer="Human Analyst",
                        metrics={"clicks": clicks, "cost": cost, "conversions": conversions}
                    )
                    st.toast(f"✓ '{query_text}' updated to PROMOTE in session memory!", icon="✅")
                    st.rerun()
            with b2:
                if st.button("🚫 Confirm Block", key=f"btn_blk_{key_prefix}_{row_id}", use_container_width=True):
                    notes = "Analyst verified query is off-target or wasteful."
                    st.session_state.reviewer_actions[query_text.lower().strip()] = {
                        "reviewer_action": "CONFIRMED_BLOCK",
                        "final_decision": "BLOCK",
                        "reviewer_notes": notes,
                        "reviewer": "Human Analyst"
                    }
                    st.session_state.precedent_memory.record_correction(
                        query_text=query_text,
                        campaign=campaign,
                        ad_group=ad_group,
                        original_decision=decision,
                        revised_decision="BLOCK",
                        reason=notes,
                        reviewer="Human Analyst",
                        metrics={"clicks": clicks, "cost": cost, "conversions": conversions}
                    )
                    st.toast(f"✓ '{query_text}' updated to BLOCK in session memory!", icon="🚫")
                    st.rerun()
            with b3:
                if st.button("💤 Dismiss (Keep Ignored)", key=f"btn_dsm_{key_prefix}_{row_id}", use_container_width=True):
                    notes = "Analyst dismissed to maintain status quo."
                    st.session_state.reviewer_actions[query_text.lower().strip()] = {
                        "reviewer_action": "DISMISSED_IGNORE",
                        "final_decision": "IGNORE",
                        "reviewer_notes": notes,
                        "reviewer": "Human Analyst"
                    }
                    st.session_state.precedent_memory.record_correction(
                        query_text=query_text,
                        campaign=campaign,
                        ad_group=ad_group,
                        original_decision=decision,
                        revised_decision="IGNORE",
                        reason=notes,
                        reviewer="Human Analyst",
                        metrics={"clicks": clicks, "cost": cost, "conversions": conversions}
                    )
                    st.toast(f"✓ '{query_text}' dismissed and marked resolved!", icon="💤")
                    st.rerun()

# -------------------------------------------------------------
# 6. TOP HEADER & TATVIC HERO RENDERING
# -------------------------------------------------------------
if current_view == "Campaign Intelligence":
    # Full-width near-black hero section with deep purple lighting & electric purple accents
    hero_html = f"""<div class="hero-container">
    <!-- Subtle Purple Ambient Lighting -->
    <div class="hero-ambient-glow"></div>
    <div class="hero-ambient-left"></div>
    <div class="hero-ambient-right"></div>
    <div class="hero-arc-wrapper"></div>
    
    <!-- 1. Transparent Horizontal Header -->
    <div class="hero-nav">
        <div class="hero-logo-box">
            <div class="hero-logo-icon">IQ</div>
            <div class="hero-logo-title">TriageIQ</div>
        </div>
        <div class="hero-nav-menu">
            <a href="#operational-dashboard" class="hero-nav-item">Platform</a>
            <a href="#operational-dashboard" class="hero-nav-item">Evidence Policy</a>
            <a href="#operational-dashboard" class="hero-nav-item">Intent Clusters</a>
            <a href="#operational-dashboard" class="hero-nav-item">Audit Trail</a>
            <a href="#operational-dashboard" class="hero-nav-btn">Analyze Account</a>
        </div>
    </div>
    
    <!-- Thin Purple Divider below Header -->
    <div class="hero-nav-divider"></div>
    
    <!-- 2. Hero Center Content -->
    <div class="hero-body">
        <div class="hero-eyebrow">
            EVIDENCE-FIRST SEARCH INTELLIGENCE PLATFORM
        </div>
        
        <h1 class="hero-title">
            Audit Search Term Waste with<br>
            <span class="hero-title-accent">Statistical Confidence.</span>
        </h1>
        
        <p class="hero-desc">
            Transform 25,000+ unmanaged search terms into validated exact-match keywords, campaign exclusions, and auditable human-review queues with Wilson confidence bounds and empirical Bayes shrinkage.
        </p>
        
        <div class="hero-actions">
            <a href="#operational-dashboard" class="hero-btn-primary">Explore Campaign Intelligence ↓</a>
            <a href="#operational-dashboard" class="hero-btn-secondary">Review Flagged Terms ({review_needed_count:,}) ›</a>
        </div>
    </div>
</div>
<div id="operational-dashboard"></div>"""
    st.html(hero_html)
    
    # Clean white section beginning immediately below the hero
    top_header_html = f"""<div class="top-header">
    <div>
        <h1 class="header-title">Campaign Intelligence Console</h1>
        <p class="header-subtitle">
            Understand search-term performance, identify opportunities, and surface decisions that need human judgment.
        </p>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <span class="status-badge">✓ Validated ({total_queries:,} terms)</span>
        <span style="font-size:0.82rem; color:#68736B; font-weight:500;">Dataset: <strong>{dataset_name}</strong></span>
    </div>
</div>"""
    st.html(top_header_html)

else:
    # Standard enterprise top header for workspace views
    workspace_header_html = f"""<div class="top-header">
    <div>
        <h1 class="header-title">{current_view}</h1>
        <p class="header-subtitle">
            TriageIQ Enterprise Campaign Optimization Suite · {current_view}
        </p>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <span class="status-badge">✓ Validated ({total_queries:,} terms)</span>
        <span style="font-size:0.82rem; color:#68736B; font-weight:500;">Dataset: <strong>{dataset_name}</strong></span>
    </div>
</div>"""
    st.html(workspace_header_html)


# =============================================================
# VIEW 1: CAMPAIGN INTELLIGENCE (SIGNATURE OVERVIEW)
# =============================================================
if current_view == "Campaign Intelligence":
    
    # B. Five Compact KPI Cards (Mutually Exclusive Contract + Human Review Overlay)
    k1, k2, k3, k4, k5 = st.columns(5)
    
    with k1:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #8000FF; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D5A2FF; text-transform:uppercase; letter-spacing:0.04em;'>Total Queries</div>"
                f"<div style='font-size:1.75rem; font-weight:700; color:#FFFFFF; line-height:1.15; margin-top:2px;'>{total_queries:,}</div>"
                "<div style='font-size:0.75rem; color:#D1CBD5; margin-top:4px;'>100% Ingested</div>"
                "</div>",
                unsafe_allow_html=True
            )
            
    with k2:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #10B981; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#34D399; text-transform:uppercase; letter-spacing:0.04em;'>Promote</div>"
                f"<div style='font-size:1.75rem; font-weight:700; color:#FFFFFF; line-height:1.15; margin-top:2px;'>{promoted_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#34D399; margin-top:4px;'><strong>{promoted_count/total_queries:.1%}</strong> · Exact Match</div>"
                "</div>",
                unsafe_allow_html=True
            )
            
    with k3:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #EF4444; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#F87171; text-transform:uppercase; letter-spacing:0.04em;'>Block</div>"
                f"<div style='font-size:1.75rem; font-weight:700; color:#FFFFFF; line-height:1.15; margin-top:2px;'>{blocked_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#F87171; margin-top:4px;'><strong>{blocked_count/total_queries:.1%}</strong> · Negative Match</div>"
                "</div>",
                unsafe_allow_html=True
            )
            
    with k4:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #9CA3AF; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D1CBD5; text-transform:uppercase; letter-spacing:0.04em;'>Ignore</div>"
                f"<div style='font-size:1.75rem; font-weight:700; color:#FFFFFF; line-height:1.15; margin-top:2px;'>{ignored_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#AFA8B8; margin-top:4px;'><strong>{ignored_count/total_queries:.1%}</strong> · Status Quo</div>"
                "</div>",
                unsafe_allow_html=True
            )
            
    with k5:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #F59E0B; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#FBBF24; text-transform:uppercase; letter-spacing:0.04em;'>Human Review</div>"
                f"<div style='font-size:1.75rem; font-weight:700; color:#FFFFFF; line-height:1.15; margin-top:2px;'>{review_needed_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#FBBF24; margin-top:4px;'><strong>{review_needed_count/total_queries:.1%}</strong> · Flagged Overlay</div>"
                "</div>",
                unsafe_allow_html=True
            )

    # C. Compact Financial Summary (Defensible Accounting Terminology)
    with st.container(border=True):
        fin_col1, fin_col2, fin_col3 = st.columns(3)
        with fin_col1:
            st.markdown(
                "<div>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D1CBD5; text-transform:uppercase;'>Historical Spend Associated with Blocked Terms</div>"
                f"<div style='font-size:1.35rem; font-weight:700; color:#F87171; margin-top:2px;'>${historical_blocked_spend:,.2f}</div>"
                "<div style='font-size:0.76rem; color:#AFA8B8;'>Potential future spend reduction by excluding off-target and bleeder queries.</div>"
                "</div>",
                unsafe_allow_html=True
            )
        with fin_col2:
            st.markdown(
                "<div>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D1CBD5; text-transform:uppercase;'>Attributed Conversion Value</div>"
                f"<div style='font-size:1.35rem; font-weight:700; color:#34D399; margin-top:2px;'>${attributed_promoted_val:,.2f}</div>"
                f"<div style='font-size:0.76rem; color:#AFA8B8;'>Gross application value across {attributed_promoted_conv:,} conversions from promoted terms.</div>"
                "</div>",
                unsafe_allow_html=True
            )
        with fin_col3:
            st.markdown(
                "<div>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D1CBD5; text-transform:uppercase;'>Account Baseline CPA</div>"
                f"<div style='font-size:1.35rem; font-weight:700; color:#FFFFFF; margin-top:2px;'>${clean_df['cost'].sum() / max(1.0, clean_df['conversions'].sum()):,.2f}</div>"
                "<div style='font-size:0.76rem; color:#AFA8B8;'>Weighted account cost per loan conversion across active campaigns.</div>"
                "</div>",
                unsafe_allow_html=True
            )

    # D. Two Analytics Panels (Aligned Containers & Heights)
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        with st.container(border=True):
            st.markdown(
                "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>Spend by Campaign</div>"
                "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:12px;'>Historical media expenditure distributed across campaigns (USD).</div>",
                unsafe_allow_html=True
            )
            camp_spend_df = clean_df.groupby("campaign")["cost"].sum().reset_index()
            camp_spend_df.columns = ["Campaign", "Spend"]
            
            spend_chart = alt.Chart(camp_spend_df).mark_bar(color="#8000FF", cornerRadiusEnd=4).encode(
                x=alt.X("Spend:Q", title="Total Spend ($)", axis=alt.Axis(format="$,.0f", labelColor="#D1CBD5", titleColor="#FFFFFF", gridColor="rgba(160, 80, 200, 0.12)")),
                y=alt.Y("Campaign:N", sort="-x", title="", axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11, labelLimit=200)),
                tooltip=[alt.Tooltip("Campaign:N"), alt.Tooltip("Spend:Q", format="$,.2f")]
            ).properties(height=240)
            
            st.altair_chart(spend_chart, use_container_width=True)

    with chart_col2:
        with st.container(border=True):
            st.markdown(
                "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>Decision Distribution by Campaign</div>"
                "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:12px;'>Normalized proportion of Promote, Block, and Ignore decisions.</div>",
                unsafe_allow_html=True
            )
            dist_df = res_df.groupby(["campaign", "decision"]).size().reset_index(name="count")
            
            decision_colors = alt.Scale(
                domain=["PROMOTE", "BLOCK", "IGNORE"],
                range=["#10B981", "#EF4444", "#6B7280"]
            )
            
            dist_chart = alt.Chart(dist_df).mark_bar().encode(
                y=alt.Y("campaign:N", sort="-x", title="", axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11, labelLimit=200)),
                x=alt.X("count:Q", stack="normalize", axis=alt.Axis(format="%", title="Decision Share", labelColor="#D1CBD5", titleColor="#FFFFFF", gridColor="rgba(160, 80, 200, 0.12)"), title=""),
                color=alt.Color("decision:N", scale=decision_colors, title="Decision"),
                tooltip=[alt.Tooltip("campaign:N", title="Campaign"), alt.Tooltip("decision:N", title="Decision"), alt.Tooltip("count:Q", title="Queries")]
            ).properties(height=240)
            
            st.altair_chart(dist_chart, use_container_width=True)

    # E. Compact Performance Section
    diag_c1, diag_c2 = st.columns(2)
    
    with diag_c1:
        with st.container(border=True):
            st.markdown(
                f"<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>Performance vs Target CPA (${target_cpa:,.2f})</div>"
                "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:12px;'>Campaign-level CPA efficiency benchmarked against allowable ceiling.</div>",
                unsafe_allow_html=True
            )
            cpa_perf = clean_df.groupby("campaign").agg({"cost": "sum", "conversions": "sum"}).reset_index()
            cpa_perf["Actual CPA"] = cpa_perf["cost"] / cpa_perf["conversions"].replace(0, np.nan)
            cpa_perf["Target CPA"] = target_cpa
            cpa_perf["CPA Variance"] = ((cpa_perf["Actual CPA"] - cpa_perf["Target CPA"]) / cpa_perf["Target CPA"])
            
            cpa_display = cpa_perf[["campaign", "cost", "conversions", "Actual CPA", "CPA Variance"]].copy()
            cpa_display.columns = ["Campaign", "Spend ($)", "Conversions", "Actual CPA ($)", "Variance vs Target"]
            cpa_display["Spend ($)"] = cpa_display["Spend ($)"].apply(lambda x: f"${x:,.2f}")
            cpa_display["Actual CPA ($)"] = cpa_display["Actual CPA ($)"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "—")
            cpa_display["Variance vs Target"] = cpa_display["Variance vs Target"].apply(lambda x: f"{x:+.1%}" if pd.notnull(x) else "—")
            st.dataframe(cpa_display, hide_index=True, use_container_width=True, height=190)

    with diag_c2:
        with st.container(border=True):
            st.markdown(
                "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>Top Review Reasons Breakdown</div>"
                "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:12px;'>Primary uncertainty rationales routing queries to Human Review.</div>",
                unsafe_allow_html=True
            )
            review_reasons = res_df[res_df["needs_review"] == True]["reason"].apply(
                lambda r: "Small-sample noise (1-2 convs)" if "Small-sample" in str(r) else
                          ("Borderline spend bleeder" if "Borderline" in str(r) else
                          ("Unprofitable converter" if "Unprofitable" in str(r) else
                          ("Conflicting off-target signal" if "Conflicting" in str(r) else "Other uncertainty")))
            ).value_counts().reset_index()
            review_reasons.columns = ["Reason Category", "Query Count"]
            
            reason_chart = alt.Chart(review_reasons).mark_bar(color="#F59E0B", cornerRadiusEnd=3).encode(
                x=alt.X("Query Count:Q", title="Queries Flagged", axis=alt.Axis(labelColor="#D1CBD5", titleColor="#FFFFFF", gridColor="rgba(160, 80, 200, 0.12)")),
                y=alt.Y("Reason Category:N", sort="-x", title="", axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11, labelLimit=200)),
                tooltip=["Reason Category", "Query Count"]
            ).properties(height=180)
            
            st.altair_chart(reason_chart, use_container_width=True)

    # F. Priority Recommendations (Curated 4 Instructive Archetypes)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-weight:700; font-size:1.08rem; color:#FFFFFF; margin-bottom:4px;'>Priority Search-Term Recommendations</div>"
        "<div style='font-size:0.82rem; color:#D1CBD5; margin-bottom:14px;'>Representative archetypes illustrating high-evidence candidates, quarantined variance traps, and business exclusions.</div>",
        unsafe_allow_html=True
    )
    
    # 4 distinct canonical examples (Row 3: Promoted Winner; Row 6: 1-click 1-conv trap; Row 1: Spend bleeder; Row 5: Off-target exclusion)
    sample_ids = [3, 6, 1, 5]
    sample_showcase = res_df[res_df["row_id"].isin(sample_ids)].copy()
    if len(sample_showcase) < 4:
        sample_showcase = res_df.head(4).copy()
        
    for _, sc_row in sample_showcase.iterrows():
        render_evidence_card(sc_row, is_review_queue=False)
        
    # Quick Action to open full Review Queue
    col_nav_btn, _ = st.columns([2, 3])
    with col_nav_btn:
        if st.button(f"👉 Open Full Review Queue ({review_needed_count:,} Flagged Queries)", key="btn_goto_rq_from_ci"):
            st.session_state.selected_view = "Human Review Queue"
            st.rerun()

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    
    # G. Reorganized Campaign & Ad Group Performance Explorer (Dedicated Collapsible Drilldown)
    with st.expander("📁 Campaign & Ad Group Performance Explorer (Granular Drilldown)", expanded=False):
        ag_summary = res_df.groupby(["campaign", "ad_group"]).agg(
            total_queries=("query_text", "count"),
            clicks=("clicks", "sum"),
            spend=("cost", "sum"),
            conversions=("conversions", "sum"),
            value=("conversion_value", "sum"),
            promoted=("decision", lambda s: (s == "PROMOTE").sum()),
            blocked=("decision", lambda s: (s == "BLOCK").sum()),
            review_needed=("needs_review", "sum")
        ).reset_index()
        
        ag_summary["cpa"] = ag_summary["spend"] / ag_summary["conversions"].replace(0, np.nan)
        ag_summary["review_rate"] = ag_summary["review_needed"] / ag_summary["total_queries"]
        
        ag_filter_c1, ag_filter_c2 = st.columns([3, 2])
        with ag_filter_c1:
            ag_search = st.text_input("🔍 Search Ad Group Name", "")
        with ag_filter_c2:
            camp_pick = st.selectbox("Filter Campaign", ["All Campaigns"] + sorted(ag_summary["campaign"].unique().tolist()))
            
        filtered_ag = ag_summary
        if ag_search:
            filtered_ag = filtered_ag[filtered_ag["ad_group"].str.contains(ag_search, case=False, na=False)]
        if camp_pick != "All Campaigns":
            filtered_ag = filtered_ag[filtered_ag["campaign"] == camp_pick]
            
        disp_ag = filtered_ag.copy()
        disp_ag["spend"] = disp_ag["spend"].apply(lambda x: f"${x:,.2f}")
        disp_ag["value"] = disp_ag["value"].apply(lambda x: f"${x:,.2f}")
        disp_ag["cpa"] = disp_ag["cpa"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "—")
        disp_ag["review_rate"] = disp_ag["review_rate"].apply(lambda x: f"{x:.1%}")
        disp_ag.columns = [
            "Campaign", "Ad Group", "Total Queries", "Clicks", "Spend ($)", "Conversions",
            "Value ($)", "Promoted", "Blocked", "Review Needed", "CPA ($)", "Review Rate"
        ]
        st.dataframe(disp_ag, hide_index=True, use_container_width=True)


# =============================================================
# VIEW 2: HUMAN REVIEW QUEUE (ANALYST WORKSPACE)
# =============================================================
elif current_view == "Human Review Queue":
    with st.container(border=True):
        st.markdown(
            "<div style='font-weight:700; font-size:1.15rem; color:#FFFFFF;'>Analyst Triage Workspace</div>"
            "<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
            "Audit queries exhibiting high statistical variance, borderline spend, or contradictory signals. "
            "Your decisions are recorded in session memory and dynamically update account exports and KPI tallies."
            "</div>",
            unsafe_allow_html=True
        )
        
        rq_df = res_df[res_df["needs_review"] == True].copy()
        learned_count = len(st.session_state.precedent_memory.history)
        active_overrides_count = len(st.session_state.reviewer_actions)
        
        m_c1, m_c2, m_c3 = st.columns(3)
        with m_c1:
            st.metric("Flagged for Review", f"{len(rq_df):,} terms")
        with m_c2:
            st.metric("Session Overrides", f"{active_overrides_count:,} resolved")
        with m_c3:
            st.metric("Learned Precedents", f"{learned_count:,} precedents in memory")
            
        if learned_count > 0:
            with st.expander(f"📚 View Reviewer Learning Log ({learned_count} active precedents in session memory)", expanded=False):
                prec_df = st.session_state.precedent_memory.export_to_dataframe()
                st.dataframe(prec_df, hide_index=True, use_container_width=True)
                if st.button("🗑️ Clear Precedent Memory", key="btn_clear_prec_mem"):
                    st.session_state.precedent_memory.history.clear()
                    st.toast("Precedent memory cleared.", icon="ℹ️")
                    st.rerun()
        
        if len(rq_df) == 0:
            st.success("🎉 All flagged search terms have been reviewed or resolved!")
        else:
            # Search & Filtering toolbar
            f1, f2, f3 = st.columns([3, 2, 2])
            with f1:
                query_search = st.text_input("🔍 Search Query", "", key="rq_text_filter")
            with f2:
                camp_filter = st.selectbox("Campaign", ["All Campaigns"] + sorted(rq_df["campaign"].unique().tolist()), key="rq_camp_filter")
            with f3:
                sort_choice = st.selectbox("Sort By", ["Spend (High to Low)", "Clicks (High to Low)", "Conversions (High to Low)", "Row ID"], key="rq_sort_choice")
                
            filtered_rq = rq_df
            if query_search:
                filtered_rq = filtered_rq[filtered_rq["query_text"].str.contains(query_search, case=False, na=False)]
            if camp_filter != "All Campaigns":
                filtered_rq = filtered_rq[filtered_rq["campaign"] == camp_filter]
                
            if sort_choice == "Spend (High to Low)":
                filtered_rq = filtered_rq.sort_values(by="cost", ascending=False)
            elif sort_choice == "Clicks (High to Low)":
                filtered_rq = filtered_rq.sort_values(by="clicks", ascending=False)
            elif sort_choice == "Conversions (High to Low)":
                filtered_rq = filtered_rq.sort_values(by="conversions", ascending=False)
            else:
                filtered_rq = filtered_rq.sort_values(by="row_id", ascending=True)
                
            st.caption(f"Displaying **{min(25, len(filtered_rq))}** of **{len(filtered_rq):,}** queries requiring analyst review:")
            
            for _, rq_row in filtered_rq.head(25).iterrows():
                render_evidence_card(rq_row, is_review_queue=True)


# =============================================================
# VIEW 3: INTENT CLUSTERS
# =============================================================
elif current_view == "Intent Clusters":
    with st.container(border=True):
        st.markdown(
            "<div style='font-weight:700; font-size:1.15rem; color:#FFFFFF;'>Near-Duplicate Search-Intent Clustering & Harmonization Engine</div>"
            "<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:14px;'>"
            "Token-normalized clustering groups semantically similar search queries expressing the same underlying commercial intent. "
            "Normalizes word order, punctuation, and pluralization while strictly preserving critical qualifiers (e.g. personal vs business, jobs vs loans). "
            "Detects conflicting decisions across variations and provides 1-click reviewer harmonization controls."
            "</div>",
            unsafe_allow_html=True
        )
        
        multi_clusters = [c for c in clusters_summary if c.get("variant_count", 1) > 1]
        conflict_clusters = [c for c in clusters_summary if c.get("has_conflict", False)]
        total_cluster_spend = sum(c.get("total_cost", 0.0) for c in clusters_summary)
        
        # KPI Bar
        k_c1, k_c2, k_c3, k_c4 = st.columns(4)
        with k_c1:
            st.metric("Total Intent Clusters", f"{len(clusters_summary):,}")
        with k_c2:
            st.metric("Multi-Variant Clusters", f"{len(multi_clusters):,}")
        with k_c3:
            st.metric("Conflicting Decisions", f"{len(conflict_clusters):,}", delta="Review Needed" if conflict_clusters else "Uniform", delta_color="inverse")
        with k_c4:
            st.metric("Grouped Clustered Spend", f"${total_cluster_spend:,.2f}")
            
        st.markdown("<hr style='border:none; border-top: 1px solid rgba(160, 80, 200, 0.22); margin: 12px 0;'>", unsafe_allow_html=True)
        
        # Filtering & Search Bar
        f1, f2, f3, f4 = st.columns([2.5, 2, 2, 1.5])
        with f1:
            cl_search = st.text_input("🔍 Search Cluster Query Text", "", key="cl_search_input")
        with f2:
            cl_filter = st.selectbox(
                "Filter Cluster Type", 
                ["Multi-Variant Clusters Only (Recommended)", "⚠️ Conflicting Decision Clusters Only", "All Clusters"],
                index=0
            )
        with f3:
            all_categories = sorted(list(set(c.get("intent_category", "General Commercial Borrowing") for c in clusters_summary)))
            cat_filter = st.selectbox("Intent Category", ["All Categories"] + all_categories, index=0)
        with f4:
            sort_by = st.selectbox("Sort By", ["Spend (High to Low)", "Variants (High to Low)", "Conversions (High to Low)", "Cluster ID"], index=0)
            
        # Filter logic
        if cl_filter.startswith("Multi-Variant"):
            filtered_clusters = multi_clusters
        elif cl_filter.startswith("⚠️ Conflicting"):
            filtered_clusters = conflict_clusters
        else:
            filtered_clusters = clusters_summary
            
        if cat_filter != "All Categories":
            filtered_clusters = [c for c in filtered_clusters if c.get("intent_category") == cat_filter]
            
        if cl_search:
            filtered_clusters = [c for c in filtered_clusters if cl_search.lower() in c.get("canonical_query", "").lower() or cl_search.lower() in c.get("intent_key", "").lower()]
            
        if sort_by == "Spend (High to Low)":
            filtered_clusters = sorted(filtered_clusters, key=lambda x: x.get("total_cost", 0.0), reverse=True)
        elif sort_by == "Variants (High to Low)":
            filtered_clusters = sorted(filtered_clusters, key=lambda x: x.get("variant_count", 1), reverse=True)
        elif sort_by == "Conversions (High to Low)":
            filtered_clusters = sorted(filtered_clusters, key=lambda x: x.get("total_conversions", 0), reverse=True)
        else:
            filtered_clusters = sorted(filtered_clusters, key=lambda x: x.get("cluster_id", ""))
            
        st.write(f"Displaying **{min(30, len(filtered_clusters)):,}** of **{len(filtered_clusters):,}** intent clusters:")
        
        for c in filtered_clusters[:30]:
            cid = c.get("cluster_id", "CLUSTER-00000")
            canonical_q = c.get("canonical_query", "")
            var_count = c.get("variant_count", 1)
            t_clicks = c.get("total_clicks", 0)
            t_cost = c.get("total_cost", 0.0)
            t_conv = int(c.get("total_conversions", 0))
            t_val = c.get("total_conversion_value", 0.0)
            cat_name = c.get("intent_category", "Commercial Intent")
            cat_expl = c.get("intent_explanation", "")
            has_conf = c.get("has_conflict", False)
            conf_type = c.get("conflict_type", "UNIFORM")
            conf_expl = c.get("conflict_explanation", "")
            
            agg_cpa_str = f"${t_cost / t_conv:,.2f}" if t_conv > 0 else "—"
            
            with st.container(border=True):
                # Header row
                h_c1, h_c2 = st.columns([3, 2])
                with h_c1:
                    conflict_badge = "<span style='background:rgba(239, 68, 68, 0.2); color:#F87171; border:1px solid rgba(239, 68, 68, 0.5); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:8px;'>⚠️ DECISION CONFLICT</span>" if has_conf else "<span style='background:rgba(16, 185, 129, 0.15); color:#34D399; border:1px solid rgba(16, 185, 129, 0.4); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:8px;'>✓ UNIFORM</span>"
                    
                    st.markdown(
                        f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:6px;'>"
                        f"<strong style='color:#FFFFFF; font-size:1.05rem;'>{cid}</strong> "
                        f"<code style='background:#1E1030; color:#FFFFFF; padding:2px 8px; border-radius:4px; border:1px solid rgba(160, 80, 200, 0.35); font-size:0.95rem;'>{html.escape(canonical_q)}</code> "
                        f"<span style='background:rgba(128, 0, 255, 0.15); color:#D5A2FF; border:1px solid rgba(128, 0, 255, 0.35); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:600;'>{var_count} variants</span>"
                        f"{conflict_badge}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with h_c2:
                    st.markdown(
                        f"<div style='text-align:right; font-size:0.78rem; color:#D5A2FF;'>"
                        f"<strong>Category:</strong> {html.escape(cat_name)}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                # Metrics Row
                st.markdown(
                    f"<div style='font-size:0.79rem; color:#D1CBD5; background-color:#0E0716; padding:6px 14px; border-radius:6px; margin-top:8px; margin-bottom:8px; border:1px solid rgba(160, 80, 200, 0.22); display:flex; flex-wrap:wrap; gap:16px; align-items:center;'>"
                    f"<span>Total Clicks: <strong style='color:#FFFFFF;'>{t_clicks:,}</strong></span>"
                    f"<span>Total Spend: <strong style='color:#FFFFFF;'>${t_cost:,.2f}</strong></span>"
                    f"<span>Total Convs: <strong style='color:#FFFFFF;'>{t_conv:,}</strong></span>"
                    f"<span>Attributed Value: <strong style='color:#FFFFFF;'>${t_val:,.2f}</strong></span>"
                    f"<span>Aggregated CPA: <strong style='color:#FFFFFF;'>{agg_cpa_str}</strong></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
                # Shared Intent Explanation
                st.markdown(
                    f"<div style='font-size:0.83rem; color:#F3EFF7; margin-bottom:8px;'>"
                    f"<strong style='color:#D5A2FF;'>Commercial Intent:</strong> {html.escape(cat_expl)}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
                # Conflict Warning & Harmonization Controls
                if has_conf:
                    st.markdown(
                        f"<div style='background:rgba(239, 68, 68, 0.08); border:1px solid rgba(239, 68, 68, 0.3); border-radius:6px; padding:10px 14px; margin-bottom:10px;'>"
                        f"<div style='font-size:0.78rem; font-weight:700; color:#F87171; margin-bottom:3px;'>⚠️ DIVERGENT DECISIONS DETECTED ({conf_type})</div>"
                        f"<div style='font-size:0.82rem; color:#F3EFF7;'>{html.escape(conf_expl)}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("<div style='font-size:0.78rem; font-weight:700; color:#D5A2FF; margin-bottom:4px;'>⚡ 1-Click Cluster Reconciliation (Harmonize All Variations)</div>", unsafe_allow_html=True)
                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                    with btn_c1:
                        if st.button(f"🚀 Harmonize: Set All to PROMOTE", key=f"btn_harm_prom_{cid}", use_container_width=True):
                            for mq in c.get("member_queries", []):
                                q_norm = mq["query_text"].lower().strip()
                                st.session_state.reviewer_actions[q_norm] = {
                                    "reviewer_action": "CLUSTER_HARMONIZATION_PROMOTE",
                                    "final_decision": "PROMOTE",
                                    "reviewer_notes": f"Cluster harmonization across {var_count} variants in {cid}",
                                    "reviewer": "Human Analyst"
                                }
                                st.session_state.precedent_memory.record_correction(
                                    query_text=mq["query_text"],
                                    campaign=mq.get("campaign", "—"),
                                    ad_group=mq.get("ad_group", "—"),
                                    original_decision=mq.get("decision", "IGNORE"),
                                    revised_decision="PROMOTE",
                                    reason=f"Harmonized with intent cluster '{canonical_q}'",
                                    reviewer="Human Analyst",
                                    metrics={"clicks": mq.get("clicks", 0), "cost": mq.get("cost", 0.0), "conversions": mq.get("conversions", 0)}
                                )
                            st.toast(f"✓ Harmonized cluster '{canonical_q}' to PROMOTE across {var_count} variations!", icon="🚀")
                            st.rerun()
                    with btn_c2:
                        if st.button(f"🚫 Harmonize: Set All to BLOCK", key=f"btn_harm_blk_{cid}", use_container_width=True):
                            for mq in c.get("member_queries", []):
                                q_norm = mq["query_text"].lower().strip()
                                st.session_state.reviewer_actions[q_norm] = {
                                    "reviewer_action": "CLUSTER_HARMONIZATION_BLOCK",
                                    "final_decision": "BLOCK",
                                    "reviewer_notes": f"Cluster harmonization across {var_count} variants in {cid}",
                                    "reviewer": "Human Analyst"
                                }
                                st.session_state.precedent_memory.record_correction(
                                    query_text=mq["query_text"],
                                    campaign=mq.get("campaign", "—"),
                                    ad_group=mq.get("ad_group", "—"),
                                    original_decision=mq.get("decision", "IGNORE"),
                                    revised_decision="BLOCK",
                                    reason=f"Harmonized with intent cluster '{canonical_q}'",
                                    reviewer="Human Analyst",
                                    metrics={"clicks": mq.get("clicks", 0), "cost": mq.get("cost", 0.0), "conversions": mq.get("conversions", 0)}
                                )
                            st.toast(f"✓ Harmonized cluster '{canonical_q}' to BLOCK across {var_count} variations!", icon="🚫")
                            st.rerun()
                    with btn_c3:
                        if st.button(f"💤 Harmonize: Set All to IGNORE", key=f"btn_harm_ign_{cid}", use_container_width=True):
                            for mq in c.get("member_queries", []):
                                q_norm = mq["query_text"].lower().strip()
                                st.session_state.reviewer_actions[q_norm] = {
                                    "reviewer_action": "CLUSTER_HARMONIZATION_IGNORE",
                                    "final_decision": "IGNORE",
                                    "reviewer_notes": f"Cluster harmonization across {var_count} variants in {cid}",
                                    "reviewer": "Human Analyst"
                                }
                                st.session_state.precedent_memory.record_correction(
                                    query_text=mq["query_text"],
                                    campaign=mq.get("campaign", "—"),
                                    ad_group=mq.get("ad_group", "—"),
                                    original_decision=mq.get("decision", "IGNORE"),
                                    revised_decision="IGNORE",
                                    reason=f"Harmonized with intent cluster '{canonical_q}'",
                                    reviewer="Human Analyst",
                                    metrics={"clicks": mq.get("clicks", 0), "cost": mq.get("cost", 0.0), "conversions": mq.get("conversions", 0)}
                                )
                            st.toast(f"✓ Harmonized cluster '{canonical_q}' to IGNORE across {var_count} variations!", icon="💤")
                            st.rerun()

                # Member queries breakdown table
                with st.expander(f"🔎 Inspect All {var_count} Individual Query Variations", expanded=has_conf):
                    m_records = c.get("member_queries", [])
                    if m_records:
                        m_df = pd.DataFrame(m_records)
                        # Format for clean display
                        disp_m_df = m_df[[col for col in ["row_id", "query_text", "campaign", "ad_group", "clicks", "cost", "conversions", "decision", "needs_review", "reason"] if col in m_df.columns]].copy()
                        disp_m_df["cost"] = disp_m_df["cost"].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(disp_m_df, hide_index=True, use_container_width=True)
                    else:
                        for v in c.get("variants", []):
                            st.write(f"- `{v}`")


# =============================================================
# VIEW 4: ALL DECISIONS (COMPLETE AUDIT TABLE)
# =============================================================
elif current_view == "All Decisions":
    with st.container(border=True):
        st.markdown(
            "<div style='font-weight:700; font-size:1.15rem; color:#FFFFFF;'>Complete Decision Audit Trail</div>"
            "<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
            "Searchable index of all processed queries enforcing the required PROMOTE / BLOCK / IGNORE contract."
            "</div>",
            unsafe_allow_html=True
        )
        
        t_c1, t_c2, t_c3 = st.columns(3)
        with t_c1:
            chosen_decisions = st.multiselect("Filter Decision", ["PROMOTE", "BLOCK", "IGNORE"], default=["PROMOTE", "BLOCK", "IGNORE"])
        with t_c2:
            chosen_review = st.selectbox("Review Filter", ["All Rows", "Needs Review Only", "No Review Needed"], index=0)
        with t_c3:
            table_search = st.text_input("🔍 Search Query Text", "")
            
        filtered_audit = res_df[res_df["decision"].isin(chosen_decisions)]
        if chosen_review == "Needs Review Only":
            filtered_audit = filtered_audit[filtered_audit["needs_review"] == True]
        elif chosen_review == "No Review Needed":
            filtered_audit = filtered_audit[filtered_audit["needs_review"] == False]
            
        if table_search:
            filtered_audit = filtered_audit[filtered_audit["query_text"].str.contains(table_search, case=False, na=False)]
            
        st.write(f"Displaying **{min(1000, len(filtered_audit)):,}** of **{len(filtered_audit):,}** search terms:")
        
        audit_cols = [
            "row_id", "query_text", "decision", "confidence", "needs_review",
            "reason", "supporting_evidence", "counterevidence", "next_action",
            "campaign", "ad_group", "impressions", "clicks", "cost", "conversions", "raw_cvr", "ci_lower", "ci_upper", "cpa", "proposed_bid"
        ]
        st.dataframe(filtered_audit[audit_cols].head(1000), hide_index=True, use_container_width=True)


# =============================================================
# VIEW 5: GOOGLE ADS EXPORTS
# =============================================================
elif current_view == "Google Ads Exports":
    with st.container(border=True):
        st.markdown(
            "<div style='font-weight:700; font-size:1.15rem; color:#FFFFFF;'>Google Ads Upload-Ready Export Files</div>"
            "<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:14px;'>"
            "Pre-formatted CSV files ready for direct import into Google Ads Editor without transformation."
            "</div>",
            unsafe_allow_html=True
        )
        
        export_dir = "output_kestrel" if selected_source.startswith("Kestrel") else "output"
        corrections_df = st.session_state.precedent_memory.export_to_dataframe()
        exported_paths = export_triage_results(
            results, 
            export_dir,
            negative_suggestions=negative_suggestions,
            corrections_df=corrections_df
        )
        
        neg_count = len(res_df[res_df["decision"] == "BLOCK"][["campaign", "query_text"]].drop_duplicates())
        prom_count = len(res_df[res_df["decision"] == "PROMOTE"][["campaign", "ad_group", "query_text"]].drop_duplicates())
        sug_count = len(negative_suggestions)
        corr_count = len(corrections_df)
        
        # 6 Export Cards in 3 rows
        e_c1, e_c2 = st.columns(2)
        with e_c1:
            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>📋 Complete Audit Log</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#D5A2FF; border:1px solid rgba(160, 80, 200, 0.3); padding:2px 6px; border-radius:4px;'>full_triage_audit.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Complete record containing 100% of input rows (<strong style='color:#FFFFFF;'>{total_queries:,} rows</strong>) with contract decisions, confidence ratings, and full supporting evidence."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["full_report"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Complete Audit CSV ({total_queries:,} rows)",
                        data=f.read(),
                        file_name="full_triage_audit.csv",
                        mime="text/csv",
                        key="btn_dl_full_audit"
                    )
                    
            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>⚠️ Human Review Queue</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#FBBF24; border:1px solid rgba(245, 158, 11, 0.3); padding:2px 6px; border-radius:4px;'>human_review_queue.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Exactly the <strong style='color:#FFFFFF;'>{review_needed_count:,} rows</strong> where <code>needs_review == True</code> with uncertainty bounds and reason codes for manual disposition."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["review_queue"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Review Queue CSV ({review_needed_count:,} rows)",
                        data=f.read(),
                        file_name="human_review_queue.csv",
                        mime="text/csv",
                        key="btn_dl_review_queue"
                    )

            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>💡 Negative Keyword Candidates</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#F87171; border:1px solid rgba(239, 68, 68, 0.3); padding:2px 6px; border-radius:4px;'>negative_keyword_suggestions.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Context-aware negative suggestions (<strong style='color:#FFFFFF;'>{sug_count:,} rules</strong>) adhering to Narrowest Appropriate Scope rule with over-exclusion risk flags."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["negative_suggestions"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Negative Candidates CSV ({sug_count:,} rules)",
                        data=f.read(),
                        file_name="negative_keyword_suggestions.csv",
                        mime="text/csv",
                        key="btn_dl_neg_sug_csv"
                    )

        with e_c2:
            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>🚫 Negative Keywords Upload</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#F87171; border:1px solid rgba(239, 68, 68, 0.3); padding:2px 6px; border-radius:4px;'>google_ads_negative_keywords.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Deduplicated <strong style='color:#FFFFFF;'>{neg_count:,} negative keyword rules</strong> formatted with Campaign-level Negative Phrase and Ad Group-level Negative Exact syntax."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["negatives"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Negative Keywords CSV ({neg_count:,} rules)",
                        data=f.read(),
                        file_name="google_ads_negative_keywords.csv",
                        mime="text/csv",
                        key="btn_dl_neg_upload"
                    )
                    
            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>🚀 Promoted Keywords Upload</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#34D399; border:1px solid rgba(16, 185, 129, 0.3); padding:2px 6px; border-radius:4px;'>google_ads_promoted_keywords.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Deduplicated <strong style='color:#FFFFFF;'>{prom_count:,} Exact Match keywords</strong> with suggested Max CPC bids calibrated to Target CPA and Empirical Bayes conversion potential."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["promoted"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Promoted Keywords CSV ({prom_count:,} rules)",
                        data=f.read(),
                        file_name="google_ads_promoted_keywords.csv",
                        mime="text/csv",
                        key="btn_dl_prom_upload"
                    )

            with st.container(border=True):
                st.markdown(
                    "<div style='font-weight:700; font-size:1.02rem; color:#FFFFFF;'>📚 Reviewer Corrections Log</div>"
                    "<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:8px;'><code style='background-color:#1E1030; color:#D5A2FF; border:1px solid rgba(160, 80, 200, 0.3); padding:2px 6px; border-radius:4px;'>reviewer_corrections_log.csv</code></div>"
                    f"<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                    f"Complete audit trail of analyst corrections (<strong style='color:#FFFFFF;'>{corr_count:,} corrections recorded</strong>) with original decisions, revised outcomes, and session notes."
                    "</div>",
                    unsafe_allow_html=True
                )
                with open(exported_paths["corrections_log"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Corrections Log CSV ({corr_count:,} logs)",
                        data=f.read(),
                        file_name="reviewer_corrections_log.csv",
                        mime="text/csv",
                        key="btn_dl_corr_log_csv"
                    )

        # Interactive Context-Aware Negative Keyword Suggestions Approval Workbench (Enhancement A)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<div style='font-weight:700; font-size:1.12rem; color:#FFFFFF;'>🔍 Context-Aware Negative Keyword Suggestions Workbench</div>"
                "<div style='font-size:0.83rem; color:#D1CBD5; margin-bottom:12px;'>"
                "Candidate negative keywords generated from explicit business scope exclusions and sufficiently supported bleeders. "
                "Enforces the <strong>Narrowest Appropriate Scope Rule</strong> (Universal exclusions at Campaign Phrase; Bleeders at Ad Group Exact). "
                "All suggestions require explicit analyst approval prior to live Google Ads deployment."
                "</div>",
                unsafe_allow_html=True
            )
            
            sug_pending = sum(1 for s in negative_suggestions if s.get("analyst_status") == "PENDING_APPROVAL")
            sug_approved = sum(1 for s in negative_suggestions if s.get("analyst_status") == "APPROVED")
            sug_rejected = sum(1 for s in negative_suggestions if s.get("analyst_status") == "REJECTED")
            sug_risky = sum(1 for s in negative_suggestions if s.get("risk_level") in ["HIGH", "CRITICAL"])
            
            w_c1, w_c2, w_c3, w_c4 = st.columns(4)
            with w_c1:
                st.metric("Total Candidates", f"{len(negative_suggestions):,}")
            with w_c2:
                st.metric("Pending Approval", f"{sug_pending:,}")
            with w_c3:
                st.metric("Approved by Analyst", f"{sug_approved:,}")
            with w_c4:
                st.metric("High Over-Exclusion Risk", f"{sug_risky:,}", delta="Requires Inspection" if sug_risky else "Safe", delta_color="inverse")
                
            # Filters & Batch Actions
            wf_c1, wf_c2, wf_c3, wf_c4 = st.columns([2.5, 2, 2, 2.5])
            with wf_c1:
                sug_search = st.text_input("🔍 Search Negative Keyword", "", key="sug_text_search")
            with wf_c2:
                status_filter = st.selectbox("Approval Status", ["All Candidates", "Pending Approval Only", "Approved Only", "Rejected Only"], index=0, key="sug_status_filter")
            with wf_c3:
                scope_filter = st.selectbox("Scope Filter", ["All Scopes", "Campaign Scope Only", "Ad Group Scope Only"], index=0, key="sug_scope_filter")
            with wf_c4:
                risk_filter = st.selectbox("Risk Filter", ["All Risk Levels", "LOW Risk Only", "HIGH / CRITICAL Risk Only"], index=0, key="sug_risk_filter")
                
            # Quick batch controls
            b_c1, b_c2, _ = st.columns([2.2, 2.2, 3])
            with b_c1:
                if st.button("✅ Approve All Low-Risk Candidates", key="btn_appr_all_low_risk"):
                    for s in negative_suggestions:
                        if s.get("risk_level") == "LOW" and s.get("analyst_status") == "PENDING_APPROVAL":
                            st.session_state.negative_approvals[s["suggestion_id"]] = "APPROVED"
                    st.toast("Approved all low-risk negative suggestions!", icon="✅")
                    st.rerun()
            with b_c2:
                if st.button("🔄 Reset All Approval Decisions", key="btn_reset_all_approvals"):
                    st.session_state.negative_approvals.clear()
                    st.toast("Reset all negative approval states.", icon="ℹ️")
                    st.rerun()
                    
            # Filter candidates
            filtered_sug = negative_suggestions
            if status_filter == "Pending Approval Only":
                filtered_sug = [s for s in filtered_sug if s.get("analyst_status") == "PENDING_APPROVAL"]
            elif status_filter == "Approved Only":
                filtered_sug = [s for s in filtered_sug if s.get("analyst_status") == "APPROVED"]
            elif status_filter == "Rejected Only":
                filtered_sug = [s for s in filtered_sug if s.get("analyst_status") == "REJECTED"]
                
            if scope_filter == "Campaign Scope Only":
                filtered_sug = [s for s in filtered_sug if s.get("recommended_scope") == "Campaign"]
            elif scope_filter == "Ad Group Scope Only":
                filtered_sug = [s for s in filtered_sug if s.get("recommended_scope") == "Ad Group"]
                
            if risk_filter == "LOW Risk Only":
                filtered_sug = [s for s in filtered_sug if s.get("risk_level") == "LOW"]
            elif risk_filter == "HIGH / CRITICAL Risk Only":
                filtered_sug = [s for s in filtered_sug if s.get("risk_level") in ["HIGH", "CRITICAL"]]
                
            if sug_search:
                filtered_sug = [s for s in filtered_sug if sug_search.lower() in s.get("negative_keyword", "").lower() or sug_search.lower() in s.get("query_text", "").lower()]
                
            st.caption(f"Displaying **{min(20, len(filtered_sug))}** of **{len(filtered_sug):,}** candidate suggestions:")
            
            for s in filtered_sug[:20]:
                sid = s.get("suggestion_id", "SUG-0000")
                kw = s.get("negative_keyword", "")
                scope = s.get("recommended_scope", "Campaign")
                mtype = s.get("recommended_match_type", "Phrase")
                camp = s.get("campaign", "—")
                ag = s.get("ad_group", "—")
                trig = s.get("trigger_type", "SCOPE_EXCLUSION")
                sp_cost = s.get("cost", 0.0)
                sp_clicks = s.get("clicks", 0)
                r_level = s.get("risk_level", "LOW")
                oe_warn = s.get("over_exclusion_warning", "")
                astatus = s.get("analyst_status", "PENDING_APPROVAL")
                
                # Badges
                status_badge = f"<span style='background:rgba(245, 158, 11, 0.18); color:#FBBF24; border:1px solid rgba(245, 158, 11, 0.4); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;'>⏳ PENDING APPROVAL</span>" if astatus == "PENDING_APPROVAL" else (
                    f"<span style='background:rgba(16, 185, 129, 0.18); color:#34D399; border:1px solid rgba(16, 185, 129, 0.4); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;'>✅ APPROVED</span>" if astatus == "APPROVED" else
                    f"<span style='background:rgba(239, 68, 68, 0.18); color:#F87171; border:1px solid rgba(239, 68, 68, 0.4); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;'>❌ REJECTED</span>"
                )
                
                risk_badge = f"<span style='background:rgba(16, 185, 129, 0.12); color:#34D399; border:1px solid rgba(16, 185, 129, 0.3); padding:2px 6px; border-radius:4px; font-size:0.72rem; font-weight:600;'>Risk: LOW</span>" if r_level == "LOW" else (
                    f"<span style='background:rgba(239, 68, 68, 0.15); color:#F87171; border:1px solid rgba(239, 68, 68, 0.4); padding:2px 6px; border-radius:4px; font-size:0.72rem; font-weight:700;'>Risk: {r_level}</span>"
                )
                
                with st.container(border=True):
                    sc1, sc2 = st.columns([3, 2])
                    with sc1:
                        st.markdown(
                            f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:6px;'>"
                            f"<code style='background:#1E1030; color:#FFFFFF; padding:2px 8px; border-radius:4px; border:1px solid rgba(160, 80, 200, 0.4); font-size:0.95rem; font-weight:700;'>{html.escape(kw)}</code> "
                            f"<span style='background:rgba(128, 0, 255, 0.15); color:#D5A2FF; border:1px solid rgba(128, 0, 255, 0.35); padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:600;'>{scope} {mtype}</span> "
                            f"{risk_badge} {status_badge}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with sc2:
                        st.markdown(
                            f"<div style='text-align:right; font-size:0.78rem; color:#D1CBD5;'>"
                            f"Target: <strong>{html.escape(camp)}</strong> › <em style='color:#D5A2FF;'>{html.escape(ag)}</em>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                    st.markdown(
                        f"<div style='font-size:0.81rem; color:#D1CBD5; margin-top:6px; margin-bottom:4px;'>"
                        f"<strong>Evidence & Rationale:</strong> {html.escape(s.get('evidence', ''))} — {html.escape(s.get('explanation', ''))}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                    if oe_warn:
                        st.markdown(
                            f"<div style='font-size:0.78rem; color:#FBBF24; background:rgba(245, 158, 11, 0.08); padding:4px 8px; border-radius:4px; margin-bottom:6px;'>"
                            f"<strong>Over-Exclusion Guardrail:</strong> {html.escape(oe_warn)}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                    # Approval Controls
                    b_appr, b_rej, _ = st.columns([1.2, 1.2, 4])
                    with b_appr:
                        if st.button("✅ Approve", key=f"btn_appr_{sid}", use_container_width=True):
                            st.session_state.negative_approvals[sid] = "APPROVED"
                            st.toast(f"Approved negative keyword candidate: '{kw}'", icon="✅")
                            st.rerun()
                    with b_rej:
                        if st.button("❌ Reject", key=f"btn_rej_{sid}", use_container_width=True):
                            st.session_state.negative_approvals[sid] = "REJECTED"
                            st.toast(f"Rejected negative keyword candidate: '{kw}'", icon="❌")
                            st.rerun()

# =============================================================
# VIEW 6: PERSONAL AI COPILOT COCKPIT (FULL DEDICATED SUITE)
# =============================================================
elif current_view == "AI Search Copilot":
    st.markdown("""
    <div style='background: radial-gradient(circle at 50% 16%, #1E082D 0%, #0E0717 100%); border: 1px solid rgba(160, 80, 200, 0.28); border-radius: 12px; padding: 22px 26px; margin-bottom: 20px;'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <div style='font-size:1.6rem; font-weight:700; color:#FFFFFF;'>✨ TriageIQ Personal AI Intelligence Suite</div>
                <div style='font-size:0.88rem; color:#D1CBD5; margin-top:4px;'>Autonomous triage reasoning, statistical confidence diagnostics, and real-time query exploration grounded in 25,000 terms.</div>
            </div>
            <div style='text-align:right;'>
                <div style='background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16, 185, 129, 0.4); color:#34D399; font-size:0.8rem; font-weight:700; padding:4px 12px; border-radius:20px; display:inline-block;'>🟢 Active AI Engine Online</div>
                <div style='font-size:0.75rem; color:#D5A2FF; margin-top:4px;'>Deterministic Statistical Grounding</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Four KPI indicators
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #8000FF; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#D5A2FF; text-transform:uppercase;'>Queries Analyzed</div>"
                f"<div style='font-size:1.6rem; font-weight:700; color:#FFFFFF; margin-top:2px;'>{total_queries:,}</div>"
                "<div style='font-size:0.75rem; color:#D1CBD5;'>100% Deterministic Coverage</div>"
                "</div>",
                unsafe_allow_html=True
            )
    with c2:
        with st.container(border=True):
            blocked_df = res_df[res_df["decision"] == "BLOCK"]
            b_cost = float(blocked_df["cost"].sum())
            st.markdown(
                "<div style='border-left:4px solid #EF4444; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#F87171; text-transform:uppercase;'>Wasted Spend Blocked</div>"
                f"<div style='font-size:1.6rem; font-weight:700; color:#FFFFFF; margin-top:2px;'>${b_cost:,.2f}</div>"
                f"<div style='font-size:0.75rem; color:#F87171;'>{len(blocked_df):,} negative candidates</div>"
                "</div>",
                unsafe_allow_html=True
            )
    with c3:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #10B981; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#34D399; text-transform:uppercase;'>Promoted Exact Match</div>"
                f"<div style='font-size:1.6rem; font-weight:700; color:#FFFFFF; margin-top:2px;'>{promoted_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#34D399;'>High-evidence winners</div>"
                "</div>",
                unsafe_allow_html=True
            )
    with c4:
        with st.container(border=True):
            st.markdown(
                "<div style='border-left:4px solid #F59E0B; padding-left:10px;'>"
                "<div style='font-size:0.75rem; font-weight:700; color:#FBBF24; text-transform:uppercase;'>Review Queue</div>"
                f"<div style='font-size:1.6rem; font-weight:700; color:#FFFFFF; margin-top:2px;'>{review_needed_count:,}</div>"
                f"<div style='font-size:0.75rem; color:#FBBF24;'>Flagged for human disposition</div>"
                "</div>",
                unsafe_allow_html=True
            )

    # Main Copilot Section: Left = Interactive Chat Console, Right = Live Row Inspector
    copilot_c1, copilot_c2 = st.columns([3, 2])
    
    with copilot_c1:
        with st.container(border=True):
            st.markdown("<div style='font-weight:700; font-size:1.05rem; color:#FFFFFF; margin-bottom:8px;'>💬 Interactive Search Copilot Chat</div>", unsafe_allow_html=True)
            
            # Preset Prompts
            p1, p2, p3 = st.columns(3)
            dedicated_prompt = None
            with p1:
                if st.button("🔍 Audit Row #6", key="ded_p_r6", use_container_width=True):
                    dedicated_prompt = "Audit Row #6"
            with p2:
                if st.button("💰 Calculate Savings", key="ded_p_savings", use_container_width=True):
                    dedicated_prompt = "How much wasted spend can we save?"
            with p3:
                if st.button("⚠️ Small Sample Trap", key="ded_p_noise", use_container_width=True):
                    dedicated_prompt = "Why is 1 conversion quarantined in review?"
            
            p4, p5, p6 = st.columns(3)
            with p4:
                if st.button("🚀 Top Promoted", key="ded_p_prom", use_container_width=True):
                    dedicated_prompt = "Show me top promoted keywords"
            with p5:
                if st.button("🎯 Kestrel Policy", key="ded_p_policy", use_container_width=True):
                    dedicated_prompt = "Explain Kestrel advertiser policy and CPA ceiling"
            with p6:
                if st.button("🗑️ Reset Chat", key="ded_p_clear", use_container_width=True):
                    st.session_state.chat_history = [
                        {
                            "role": "assistant",
                            "content": "👋 Chat reset! Ask me about any query (e.g. *'Audit row #6'*), savings calculations, or Kestrel policies!"
                        }
                    ]
                    st.rerun()

            if dedicated_prompt:
                st.session_state.chat_history.append({"role": "user", "content": dedicated_prompt})
                ans = generate_copilot_response(dedicated_prompt, res_df, clean_df, target_cpa=target_cpa)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                st.rerun()

            st.markdown("<hr style='border:none; border-top: 1px solid rgba(160, 80, 200, 0.22); margin: 12px 0;'>", unsafe_allow_html=True)

            chat_stream = st.container(height=420)
            with chat_stream:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            chat_in = st.chat_input("Ask about any query, row #, savings, or policy rule...", key="dedicated_chat_input")
            if chat_in:
                st.session_state.chat_history.append({"role": "user", "content": chat_in})
                ans = generate_copilot_response(chat_in, res_df, clean_df, target_cpa=target_cpa)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                st.rerun()

    with copilot_c2:
        with st.container(border=True):
            st.markdown("<div style='font-weight:700; font-size:1.05rem; color:#FFFFFF; margin-bottom:8px;'>🔬 Deep Query Inspector</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.8rem; color:#D1CBD5; margin-bottom:12px;'>Instantly inspect any search term row with complete Wilson bounds and evidence breakdown:</div>", unsafe_allow_html=True)
            
            selected_row_inspect = st.number_input("Inspect Row ID #", min_value=1, max_value=len(res_df), value=6, step=1)
            
            inspect_matches = res_df[res_df["row_id"] == selected_row_inspect]
            if not inspect_matches.empty:
                r_insp = inspect_matches.iloc[0]
                render_evidence_card(r_insp, is_review_queue=True, key_prefix="insp")
            else:
                st.warning(f"Row #{selected_row_inspect} not found in dataset.")

# =============================================================
# FLOATING PERSONAL AI COPILOT LAUNCHER & MODAL POPUP
# =============================================================
if st.button("✨ Ask Personal AI Copilot", key="floating_copilot_btn", help="Open TriageIQ Personal AI Assistant"):
    st.session_state.show_copilot = True
    st.rerun()

if st.session_state.get("show_copilot", False):
    render_copilot_modal(res_df, clean_df, target_cpa=target_cpa)
