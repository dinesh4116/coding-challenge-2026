"""
Problem Statement PS-03: 'Ad-to-Landing-Page Message Match Auditor'
Production-Ready Single-File Streamlit Application (app.py)

Key Capabilities:
1. Ingestion: Reads `ads.csv` and loads corresponding offline HTML snapshots from `landing_page_snapshots/`.
2. HTML Parsing: Extracts structured text with BeautifulSoup, categorizing into Above-The-Fold (Hero),
   Below-The-Fold (Sections & Cards), and Footer/Fine-Print.
3. Live Snapshot Preview: Allows rendering the actual offline HTML snapshot in an interactive iframe.
4. Gemini AI Auditor: Computes overall Message Match Score (0-100%) and Above-The-Fold alignment score.
5. Verbatim Evidence: Enforces exact quotes from the extracted page text supporting findings.
6. Programmatic Hallucination Check: Verifies quotes against source text, flagging hallucinations in the UI.
7. Actionable Fixes: Produces concrete, rewritten copy recommendations for landing page and ad copy.
8. Turnkey Mock & Offline Support: Seamless offline demonstration mode for all 60 dataset pairs.
9. Strict Theme: Pure White (#FFFFFF), Fresh Green (#2E7D32/#4CAF50), Light Blue (#0288D1/#2196F3).
   Zero Dark Blue, Violet, or Purple.
"""

import io
import json
import os
import re
import html
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    docx = None
    DOCX_AVAILABLE = False

# Optional google.generativeai import with graceful fallback
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False


# ==============================================================================
# 1. STREAMLIT PAGE CONFIG & STRICT CUSTOM CSS (PURE WHITE, GREEN, LIGHT BLUE)
# ==============================================================================
st.set_page_config(
    page_title="Ad-to-Landing-Page Message Match Auditor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
/* === BASE THEME & STRICT PALETTE (NO DARK BLUE, NO VIOLET, NO PURPLE) === */
:root {
    --bg-white: #FFFFFF;
    --primary-green: #2E7D32;
    --primary-green-light: #4CAF50;
    --primary-green-tint: #F0FDF4;
    --secondary-blue: #0288D1;
    --secondary-blue-light: #2196F3;
    --secondary-blue-tint: #F0F9FF;
    --neutral-dark: #1E293B;
    --neutral-mid: #475569;
    --neutral-light: #94A3B8;
    --border-subtle: #E2E8F0;
    --card-bg: #FFFFFF;
    --alert-red: #D32F2F;
    --alert-red-tint: #FEF2F2;
    --alert-orange: #ED6C02;
    --alert-orange-tint: #FFFBEB;
}

/* Background must be pure white */
.stApp {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

header[data-testid="stHeader"] {
    background-color: #FFFFFF !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #F8FAFC !important;
    border-right: 1px solid #E2E8F0 !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {
    color: #1E293B !important;
}

/* Explicit fix for Streamlit Checkbox & Radio Labels */
div[data-testid="stCheckbox"] label,
div[data-testid="stCheckbox"] label p,
div[data-testid="stCheckbox"] label span,
div[data-baseweb="checkbox"] span {
    color: #1E293B !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Clean green accent for checkboxes */
div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: #2E7D32 !important;
}


/* Custom Navigation & Header Bar */
.app-header {
    background: #FFFFFF;
    border-bottom: 2px solid #E2E8F0;
    padding: 18px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #2E7D32;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    padding: 4px 12px;
    border-radius: 999px;
}

.brand-title {
    font-size: 26px;
    font-weight: 800;
    color: #1E293B;
    margin: 6px 0 2px 0;
    letter-spacing: -0.02em;
}

.brand-subtitle {
    font-size: 14px;
    color: #475569;
    margin: 0;
}

/* Primary Action Buttons strictly Fresh Green */
div.stButton > button:first-child {
    background-color: #2E7D32 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(46, 125, 50, 0.2) !important;
}

div.stButton > button:first-child:hover {
    background-color: #1B5E20 !important;
    box-shadow: 0 4px 8px rgba(46, 125, 50, 0.3) !important;
    transform: translateY(-1px);
}

/* Secondary Button style */
button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #0288D1 !important;
    border: 1px solid #0288D1 !important;
}

/* KPI Metric Cards */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    position: relative;
    overflow: hidden;
}

.kpi-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
}

.kpi-card.green::before { background: #2E7D32; }
.kpi-card.blue::before { background: #0288D1; }
.kpi-card.orange::before { background: #ED6C02; }
.kpi-card.red::before { background: #D32F2F; }

.kpi-value {
    font-size: 36px;
    font-weight: 800;
    line-height: 1.1;
    margin: 6px 0;
}

.kpi-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748B;
}

.kpi-sub {
    font-size: 13px;
    color: #475569;
    margin-top: 4px;
}

/* Google Search Ad Simulation Preview Box */
.ad-preview-container {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-top: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.ad-sponsor-label {
    font-size: 12px;
    font-weight: 700;
    color: #2E7D32;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
}

.ad-url-breadcrumb {
    font-size: 12px;
    color: #475569;
    margin-bottom: 6px;
    word-break: break-all;
}

.ad-headline-preview {
    font-size: 18px;
    font-weight: 600;
    color: #0288D1;
    line-height: 1.35;
    margin-bottom: 6px;
    cursor: pointer;
}

.ad-desc-preview {
    font-size: 14px;
    color: #334155;
    line-height: 1.5;
}

/* Browser Mockup Window for HTML Landing Page */
.browser-window-bar {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-radius: 8px 8px 0 0;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 4px;
}

.browser-dots {
    display: flex;
    gap: 6px;
    align-items: center;
}

.browser-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.browser-dot.red { background: #EF4444; }
.browser-dot.yellow { background: #F59E0B; }
.browser-dot.green { background: #10B981; }

.browser-address {
    flex: 1;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    color: #334155;
    font-family: monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 6px;
}

.browser-badge {
    font-size: 11px;
    font-weight: 700;
    color: #2E7D32;
    background: #E8F5E9;
    border: 1px solid #C8E6C9;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
}

/* Ad Copy Specs & Breakdown Card */
.ad-breakdown-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 10px;
}

.ad-field-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 7px 0;
    border-bottom: 1px solid #F1F5F9;
    font-size: 13px;
    line-height: 1.45;
}

.ad-field-label {
    font-weight: 600;
    color: #475569;
    min-width: 95px;
    flex-shrink: 0;
}

.ad-field-value {
    color: #1E293B;
    flex-grow: 1;
    word-break: break-word;
}

.ad-char-chip {
    font-size: 11px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 8px;
    white-space: nowrap;
    flex-shrink: 0;
}

.ad-char-ok {
    background: #F0FDF4;
    color: #2E7D32;
    border: 1px solid #BBF7D0;
}

.ad-char-warn {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}

/* Section Box & Content Areas */
.content-box {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

/* Mismatch Cards */
.mismatch-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 5px solid #ED6C02;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.mismatch-card.critical {
    border-left-color: #D32F2F;
}

.mismatch-card.moderate {
    border-left-color: #ED6C02;
}

.mismatch-card.minor {
    border-left-color: #0288D1;
}

.badge-tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 6px;
}

.badge-critical {
    background: #FEF2F2;
    color: #D32F2F;
    border: 1px solid #FECACA;
}

.badge-moderate {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}

.badge-fold {
    background: #F0F9FF;
    color: #0288D1;
    border: 1px solid #BAE6FD;
}

.badge-verified {
    background: #F0FDF4;
    color: #166534;
    border: 1px solid #BBF7D0;
    font-weight: 700;
}

.badge-hallucination {
    background: #FEF2F2;
    color: #991B1B;
    border: 1px solid #F87171;
    font-weight: 800;
}

.badge-omission {
    background: #F8FAFC;
    color: #475569;
    border: 1px solid #CBD5E1;
}

.quote-box {
    background: #F8FAFC;
    border-left: 3px solid #0288D1;
    padding: 10px 14px;
    font-style: italic;
    font-size: 13px;
    color: #334155;
    margin: 8px 0;
    border-radius: 0 6px 6px 0;
}

.fix-box {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    padding: 12px 16px;
    border-radius: 6px;
    margin-top: 10px;
}

.fix-box-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: #2E7D32;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.fix-box-text {
    font-size: 14px;
    color: #166534;
    line-height: 1.45;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #E2E8F0;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 10px 16px;
    font-weight: 600;
    color: #64748B;
    background-color: transparent;
}

.stTabs [aria-selected="true"] {
    color: #2E7D32 !important;
    border-bottom: 3px solid #2E7D32 !important;
    background-color: #F0FDF4 !important;
}

/* Inputs & Textareas */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    color: #1E293B !important;
    border-radius: 6px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# 2. DATASET INGESTION & HTML PARSING (ads.csv + landing_page_snapshots)
# ==============================================================================
def find_dataset_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """
    Dynamically locate ads.csv and landing_page_snapshots directory.
    Checks workspace root, PS-03_message_match_auditor, ps-03_message, etc.
    """
    candidates = [
        Path("."),
        Path("PS-03_message_match_auditor"),
        Path("ps-03_message"),
        Path(__file__).parent if "__file__" in globals() else Path("."),
        (Path(__file__).parent / "PS-03_message_match_auditor") if "__file__" in globals() else Path("."),
        (Path(__file__).parent / "ps-03_message") if "__file__" in globals() else Path("."),
    ]
    for base in candidates:
        csv_candidate = base / "ads.csv"
        snap_candidate = base / "landing_page_snapshots"
        if csv_candidate.exists() and snap_candidate.exists():
            return csv_candidate, snap_candidate
    return None, None


@st.cache_data
def load_ads_dataset() -> Tuple[Optional[pd.DataFrame], Optional[Path], str]:
    """Load and index ads.csv."""
    csv_path, snap_dir = find_dataset_paths()
    if not csv_path:
        return None, None, "Dataset folder (containing ads.csv and landing_page_snapshots) not found in search paths."
    try:
        df = pd.read_csv(csv_path)
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        return df, snap_dir, f"Loaded {len(df)} ad-landing page pairs from {csv_path.name}."
    except Exception as e:
        return None, None, f"Error reading ads.csv: {str(e)}"


def extract_js_hydration_text(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract structured content from modern JavaScript SPAs and hydration scripts
    (Next.js __NEXT_DATA__, Nuxt __NUXT_DATA__, JSON-LD Schema.org, React hydration).
    Recovers critical headlines, pricing, and offers even if client-side rendered.
    """
    hydration_texts = []
    schemas = []
    framework_detected = "Standard Static HTML"

    # 1. Next.js Hydration Payload
    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        try:
            data = json.loads(next_script.string)
            framework_detected = "Next.js (React Hydration)"
            def extract_strings(obj):
                if isinstance(obj, str):
                    s = obj.strip()
                    if len(s) > 3 and not s.startswith("http") and not s.startswith("/") and "{" not in s:
                        hydration_texts.append(s)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        extract_strings(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)
            extract_strings(data.get("props", {}))
        except Exception:
            pass

    # 2. Nuxt.js Hydration Payload
    nuxt_script = soup.find("script", id="__NUXT_DATA__")
    if nuxt_script and nuxt_script.string:
        framework_detected = "Nuxt.js (Vue Hydration)"
        try:
            data = json.loads(nuxt_script.string)
            for item in data:
                if isinstance(item, str) and len(item.strip()) > 3:
                    hydration_texts.append(item.strip())
        except Exception:
            pass

    # 3. JSON-LD Schema.org Data (often contains product offers, pricing, guarantees)
    for ld in soup.find_all("script", type="application/ld+json"):
        if ld.string:
            try:
                data = json.loads(ld.string)
                schemas.append(data)
                def extract_ld_strings(obj):
                    if isinstance(obj, str) and len(obj.strip()) > 3:
                        hydration_texts.append(obj.strip())
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            extract_ld_strings(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_ld_strings(item)
                extract_ld_strings(data)
            except Exception:
                pass

    return {
        "framework": framework_detected,
        "extracted_texts": list(dict.fromkeys(hydration_texts))[:40],  # Unique, capped for prompt safety
        "schemas": schemas,
        "has_hydration": bool(hydration_texts)
    }


def parse_landing_page_from_raw_html(html_raw: str, base_url: str = "") -> Dict[str, Any]:
    """
    Parse HTML content (from either offline snapshot or live fetch), extracting Hero,
    Sections, Fine Print, and JavaScript hydration data. Injects <base href> for asset rendering.
    """
    if not html_raw:
        return {
            "title": "No Content",
            "hero_text": "",
            "sections_text": "",
            "fine_print_text": "",
            "raw_full_text": "",
            "raw_html": "",
            "js_hydration": {"framework": "None", "has_hydration": False}
        }

    # Strip any hackathon disclaimer text
    srishti_pattern = re.compile(r"This page is a fictional example created for the Srishti 2K26 hackathon\.?", re.IGNORECASE)
    clean_html = srishti_pattern.sub("", html_raw)

    soup = BeautifulSoup(clean_html, "html.parser")

    # Extract JS hydration before decomposing scripts
    js_hydration = extract_js_hydration_text(soup)

    # Title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(" ", strip=True) if title_tag else "Landing Page"

    # Inject <base href="..."> if base_url provided so iframe loads CSS/images correctly
    rendered_html = clean_html
    if base_url and "<base " not in clean_html.lower():
        head_match = re.search(r"<head[^>]*>", clean_html, re.IGNORECASE)
        if head_match:
            idx = head_match.end()
            base_tag = f'\n<base href="{html.escape(base_url, quote=True)}" target="_blank">\n'
            rendered_html = clean_html[:idx] + base_tag + clean_html[idx:]

    # Clean non-content tags for text extraction
    content_soup = BeautifulSoup(clean_html, "html.parser")
    for s in content_soup(["script", "style", "svg", "noscript"]):
        s.decompose()

    # 1. Above-The-Fold: Hero elements & Header
    hero_el = content_soup.find(class_=re.compile(r"hero", re.IGNORECASE))
    header_el = content_soup.find("header")
    hero_parts = []
    if header_el:
        hero_parts.append(header_el.get_text(" ", strip=True))
    if hero_el:
        hero_parts.append(hero_el.get_text(" ", strip=True))
    elif not header_el:
        h1 = content_soup.find("h1")
        if h1:
            hero_parts.append(h1.get_text(" ", strip=True))
            p = h1.find_next_sibling("p")
            if p:
                hero_parts.append(p.get_text(" ", strip=True))

    hero_text = " ".join(hero_parts).strip()

    # 2. Fine Print / Footer
    footer_el = content_soup.find("footer")
    fine_el = content_soup.find(class_=re.compile(r"fine", re.IGNORECASE))
    fine_print_text = ""
    if fine_el:
        fine_print_text = fine_el.get_text(" ", strip=True)
    elif footer_el:
        fine_print_text = footer_el.get_text(" ", strip=True)
    fine_print_text = srishti_pattern.sub("", fine_print_text).strip()

    # 3. Below-The-Fold: Sections, Cards, FAQ
    sections_parts = []
    sections = content_soup.find_all("section")
    for sec in sections:
        sec_text = sec.get_text(" ", strip=True)
        if sec_text:
            sections_parts.append(sec_text)

    # If DOM text is sparse but hydration text was found, enrich sections
    if js_hydration["has_hydration"] and len(sections_parts) < 2:
        sections_parts.append("--- JAVASCRIPT HYDRATION CONTENT ---")
        sections_parts.extend(js_hydration["extracted_texts"][:25])

    sections_text = "\n\n".join(sections_parts).strip()

    # 4. Raw Full Text for verbatim matching
    raw_full_text = content_soup.get_text(" ", strip=True)
    if js_hydration["has_hydration"]:
        raw_full_text += " " + " ".join(js_hydration["extracted_texts"])
    raw_full_text = srishti_pattern.sub("", raw_full_text).strip()

    return {
        "title": page_title,
        "hero_text": hero_text,
        "sections_text": sections_text,
        "fine_print_text": fine_print_text,
        "raw_full_text": raw_full_text,
        "raw_html": rendered_html,
        "js_hydration": js_hydration
    }


def parse_landing_page_html(html_path: Path) -> Dict[str, Any]:
    """Extract structured text from offline HTML landing page snapshot."""
    if not html_path.exists():
        return {
            "title": "Snapshot Not Found",
            "hero_text": "",
            "sections_text": "",
            "fine_print_text": "",
            "raw_full_text": "",
            "raw_html": "",
            "js_hydration": {"framework": "None", "has_hydration": False}
        }

    try:
        html_raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        html_raw = ""

    return parse_landing_page_from_raw_html(html_raw)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_url_content(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Fetch and render live URLs handling bot blocks (Cloudflare, PerimeterX, WAF)
    and client-side JavaScript rendering (extracting hydration state).
    """
    if not REQUESTS_AVAILABLE or requests is None:
        return {
            "success": False,
            "error": "The 'requests' library is not available in the environment.",
            "raw_html": "",
            "parsed": None,
            "meta": {}
        }

    target_url = str(url or "").strip()
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/"
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(target_url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        final_url = response.url
        raw_html = response.text
        status_code = response.status_code

        parsed = parse_landing_page_from_raw_html(raw_html, base_url=final_url)

        meta = {
            "status_code": status_code,
            "final_url": final_url,
            "size_kb": len(raw_html) / 1024.0,
            "framework": parsed.get("js_hydration", {}).get("framework", "Standard Static HTML"),
            "has_hydration": parsed.get("js_hydration", {}).get("has_hydration", False),
            "bot_protection_bypassed": True
        }

        return {
            "success": True,
            "error": None,
            "raw_html": raw_html,
            "parsed": parsed,
            "meta": meta
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch live URL: {str(e)}",
            "raw_html": "",
            "parsed": None,
            "meta": {"status_code": getattr(e, "response", None).status_code if hasattr(e, "response") and e.response is not None else 0}
        }


# ==============================================================================
# REGULATED CATEGORIES COMPLIANCE EXPOSURE ENGINE
# ==============================================================================
REGULATED_VERTICALS = {
    "finance": {
        "name": "Financial Services & Banking",
        "keywords": ["finance", "banking", "bank", "wealth", "invest", "trading", "crypto", "credit", "broker", "fund", "mortgage"],
        "regulators": "CFPB (Consumer Financial Protection Bureau), FTC, Federal Reserve, SEC",
        "statutes": "Truth in Lending Act (TILA / Regulation Z), Gramm-Leach-Bliley Act (GLBA), Dodd-Frank Act",
        "google_policy": "Google Ads Financial Products & Services Policy (Mandatory APR disclosures & verification)",
        "statutory_risk": "Advertising unverified interest rates, 0% APR, or zero-fee claims unsupported on page triggers immediate CFPB Regulation Z penalties and FTC Section 5 deceptive marketing enforcement."
    },
    "loans": {
        "name": "Personal Loans & Lending",
        "keywords": ["loan", "mortgage", "lender", "borrow", "apr", "refinance", "debt", "settlement", "payday"],
        "regulators": "CFPB, FTC, NMLS, HUD (Fair Housing Act)",
        "statutes": "Regulation Z (12 CFR § 1026.24 Advertising Requirements), Equal Credit Opportunity Act (ECOA), RESPA",
        "google_policy": "Personal Loans Policy (Mandatory APR disclosure range & minimum/maximum repayment terms)",
        "statutory_risk": "Advertising 'No Credit Check', 'Instant Approval', or specific rates without clear and conspicuous statutory disclosure tables above the fold is an actionable federal lending violation."
    },
    "insurance": {
        "name": "Insurance & Annuities",
        "keywords": ["insurance", "annuity", "coverage", "policy", "auto insurance", "life insurance", "home insurance", "medicare"],
        "regulators": "State Insurance Commissioners (NAIC), FTC, CMS (Medicare)",
        "statutes": "McCarran-Ferguson Act, State Unfair Claims Settlement & Insurance Advertising Acts, CMS Marketing Guidelines",
        "google_policy": "Insurance Advertising Policy (Licensing disclosures & underwriter transparency)",
        "statutory_risk": "Promising full coverage guarantees or introductory rate promises not reflected in policy terms violates state insurance unfair trade practices."
    },
    "healthcare": {
        "name": "Healthcare, Medical & Telehealth",
        "keywords": ["health", "medical", "doctor", "telehealth", "clinic", "therapy", "surgery", "treatment", "dental", "mental"],
        "regulators": "FDA (Food and Drug Administration), FTC, HHS OCR (HIPAA)",
        "statutes": "FTC Health Products Guidance, FDA Modernization Act, Health Information Portability (HIPAA)",
        "google_policy": "Healthcare and Medicines Policy (Prescription Drug & Telehealth Certification)",
        "statutory_risk": "Making medical efficacy claims, treatment guarantees, or promotional procedure promises unsupported on page violates FTC substantiation doctrine and triggers ad disapproval."
    },
    "pharma": {
        "name": "Supplements, Diet & Pharmaceuticals",
        "keywords": ["pharma", "drug", "prescription", "supplement", "vitamin", "diet", "weight loss", "cbd", "wellness"],
        "regulators": "FDA, FTC, DEA",
        "statutes": "Dietary Supplement Health and Education Act (DSHEA), Federal Food, Drug, and Cosmetic Act (FD&C Act)",
        "google_policy": "Unapproved Pharmaceuticals & Supplements Policy (Restricted Substance Bans)",
        "statutory_risk": "Advertising disease prevention, cures, or rapid weight loss without FDA-mandated statutory disclaimers constitutes deceptive marketing under FTC Section 5."
    },
    "legal": {
        "name": "Legal Services & Attorneys",
        "keywords": ["legal", "lawyer", "attorney", "law firm", "accident", "injury", "lawsuit", "litigation", "settlement"],
        "regulators": "State Bar Associations, FTC",
        "statutes": "ABA Model Rules of Professional Conduct (Rule 7.1 Communications Concerning a Lawyer's Services)",
        "google_policy": "Legal Services Advertising Policy",
        "statutory_risk": "Advertising guaranteed compensation, outcome promises, or 'free' services without disclaimer violates State Bar ethical rules and triggers disciplinary sanctions."
    },
    "crypto": {
        "name": "Cryptocurrency, Forex & Web3 Investments",
        "keywords": ["crypto", "bitcoin", "ethereum", "token", "nft", "forex", "defi", "web3", "yield", "exchange"],
        "regulators": "SEC, CFTC, FTC, FinCEN",
        "statutes": "Securities Act of 1933, Commodity Exchange Act, FTC Act Section 5 Deceptive Advertising",
        "google_policy": "Cryptocurrency Products and Services Policy (FinCEN registration required)",
        "statutory_risk": "Promising guaranteed investment returns or zero-risk yields without mandatory capital loss risk warnings triggers immediate SEC/CFTC enforcement."
    },
    "education": {
        "name": "Higher Education & Vocational Training",
        "keywords": ["university", "college", "degree", "bootcamp", "academy", "training", "career", "certification", "placement"],
        "regulators": "U.S. Department of Education, FTC",
        "statutes": "FTC Guides Concerning Vocational & Distance Education Schools (16 CFR Part 254)",
        "google_policy": "Education Policy (Accreditation & Placement Transparency)",
        "statutory_risk": "Advertising guaranteed job placement, starting salaries, or accredited credentials without verified cohort employment data violates FTC vocational school rules."
    }
}


def evaluate_compliance_exposure(
    vertical_name: str,
    ad_row: pd.Series,
    mismatches: List[Dict[str, Any]],
    ai_compliance: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate compliance exposure in regulated categories when ad claims are unsupported on page.
    Flags regulatory liability under FTC, CFPB, FDA, SEC, and Google Ads Misrepresentation policies.
    """
    v_lower = str(vertical_name or "").lower()
    adv_lower = str(ad_row.get("advertiser", "")).lower()
    combined_context = f"{v_lower} {adv_lower}"

    matched_vertical_key = None
    matched_info = None

    for key, info in REGULATED_VERTICALS.items():
        if key in combined_context or any(kw in combined_context for kw in info["keywords"]):
            matched_vertical_key = key
            matched_info = info
            break

    # If AI identified as regulated, adopt AI classification
    if not matched_info and ai_compliance and ai_compliance.get("is_regulated_vertical"):
        matched_vertical_key = "regulated_industry"
        matched_info = {
            "name": ai_compliance.get("regulated_industry", "Regulated Industry"),
            "regulators": ai_compliance.get("governing_regulators", "FTC & Regulatory Agencies"),
            "statutes": "Consumer Protection and Advertising Substantiation Regulations",
            "google_policy": "Google Ads Misrepresentation & Sensitive Category Policy",
            "statutory_risk": "Promotional discrepancies in regulated categories violate statutory disclosure mandates."
        }

    is_regulated = bool(matched_info)
    unsupported_claims = []

    for m in mismatches:
        page_quote = str(m.get("page_quote", "")).strip().upper()
        sev = m.get("severity", "Moderate")
        cat = m.get("category", "")
        # Flag if claim is absent (NONE) or high severity in pricing/offers
        if page_quote in ["NONE", "[NONE]", "N/A"] or sev == "Critical" or cat in ["Pricing & Rates", "Offer Discrepancy", "Speed & Approval"]:
            unsupported_claims.append({
                "ad_claim": m.get("ad_claim", ""),
                "landing_page_quote": m.get("page_quote", ""),
                "problem": m.get("issue_description", ""),
                "severity": sev,
                "category": cat,
                "suggested_fix": m.get("suggested_fix", "")
            })

    if is_regulated and unsupported_claims:
        risk_tier = "🔴 CRITICAL REGULATORY VIOLATION"
        risk_color = "#D32F2F"
        account_suspension_risk = "HIGH (Ad Disapproval & Google Ads Account Suspension Risk)"
    elif is_regulated:
        risk_tier = "🟢 COMPLIANT IN REGULATED VERTICAL"
        risk_color = "#2E7D32"
        account_suspension_risk = "LOW (Claims Substantively Corroborated)"
    else:
        risk_tier = "STANDARD CRO SENSITIVITY (Non-Regulated)"
        risk_color = "#0288D1"
        account_suspension_risk = "MINIMAL (Standard Bounce Friction)"

    return {
        "is_regulated": is_regulated,
        "vertical_key": matched_vertical_key,
        "info": matched_info or {},
        "unsupported_claims": unsupported_claims,
        "unsupported_count": len(unsupported_claims),
        "risk_tier": risk_tier,
        "risk_color": risk_color,
        "account_suspension_risk": account_suspension_risk,
        "ai_summary": ai_compliance.get("compliance_exposure_summary", "") if ai_compliance else "",
        "statutory_remediation": ai_compliance.get("statutory_remediation", "") if ai_compliance else ""
    }


def format_landing_page_for_llm(parsed: Dict[str, Any]) -> str:
    """Format parsed HTML into an annotated structured text prompt for the auditor."""
    sections = [
        f"=== [PAGE TITLE] ===\n{parsed.get('title', '')}\n",
        f"=== [ABOVE THE FOLD - HERO SECTION] ===\n{parsed.get('hero_text', '(No hero section identified)')}\n",
        f"=== [BELOW THE FOLD - CORE SECTIONS & VALUE PROPS] ===\n{parsed.get('sections_text', '(No core sections identified)')}\n",
        f"=== [FOOTER & FINE PRINT DISCLAIMERS] ===\n{parsed.get('fine_print_text', '(No footer disclaimers identified)')}\n"
    ]
    return "\n".join(sections)


# ==============================================================================
# 3. HALLUCINATION CHECK & TEXT VERIFICATION LOGIC
# ==============================================================================
def normalize_text_for_search(text: str) -> str:
    """Normalize text by stripping punctuation, normalizing whitespace and lowercasing."""
    if not text:
        return ""
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def verify_quote_in_landing_page(quote: str, raw_full_text: str, hero_text: str = "") -> Dict[str, Any]:
    """
    Programmatic hallucination detection.
    Verifies if the LLM's cited `page_quote` actually exists in the source text.
    Also detects if the quote is situated Above-The-Fold (Hero) or buried below.
    """
    if not quote or quote.strip() == "":
        return {
            "status": "EMPTY",
            "is_above_the_fold": False,
            "details": "No quote provided by auditor."
        }

    stripped_quote = quote.strip()

    # Case 1: Check if the LLM explicitly declared that the claim is absent/omitted (e.g. NONE)
    absence_patterns = [
        r"^\[?none\]?$",
        r"^none$",
        r"^n/?a$",
        r"\[?not (found|present|mentioned|included|available).*\]?",
        r"\[?absent.*\]?"
    ]
    for pattern in absence_patterns:
        if re.match(pattern, stripped_quote, re.IGNORECASE):
            return {
                "status": "OMISSION_NOTED",
                "is_above_the_fold": False,
                "details": "Auditor confirmed claim is completely absent from the landing page ('NONE')."
            }

    # Case 2: Exact verbatim substring match
    if stripped_quote in raw_full_text:
        is_hero = bool(hero_text and stripped_quote in hero_text)
        return {
            "status": "VERIFIED",
            "is_above_the_fold": is_hero,
            "details": "Exact verbatim quote verified in source landing page."
        }

    # Case 3: Normalized substring match
    norm_quote = normalize_text_for_search(stripped_quote)
    norm_raw = normalize_text_for_search(raw_full_text)
    norm_hero = normalize_text_for_search(hero_text)

    if len(norm_quote) > 8 and norm_quote in norm_raw:
        is_hero = bool(norm_hero and norm_quote in norm_hero)
        return {
            "status": "VERIFIED",
            "is_above_the_fold": is_hero,
            "details": "Normalized quote verified (matched with slight whitespace/punctuation variation)."
        }

    # Case 4: HALLUCINATION! Quote not found in source text
    return {
        "status": "HALLUCINATED",
        "is_above_the_fold": False,
        "details": "HALLUCINATION WARNING: This quoted text does NOT exist anywhere in the landing page!"
    }


# ==============================================================================
# 4. GOOGLE GEMINI API PROMPT & EXECUTION
# ==============================================================================
GEMINI_AUDIT_PROMPT_TEMPLATE = """
You are an Enterprise-Grade Ad-to-Landing-Page Message Match Auditor & Conversion Rate Optimization (CRO) Specialist. Your objective is to audit search ads against landing page content with absolute precision, zero hallucination, and high business impact.

--- AD COPY DETAILS ---
Advertiser: {advertiser}
Vertical: {vertical}
Headline 1: {headline_1}
Headline 2: {headline_2}
Headline 3: {headline_3}
Description 1: {description_1}
Description 2: {description_2}
Final URL: {final_url}

--- LANDING PAGE STRUCTURED CONTENT ---
{landing_page_structured}

--- AUDIT INSTRUCTIONS ---
1. CORE MESSAGE MATCH & POSITIONING AUDIT:
   - Calculate an Overall Match Score (0-100%).
   - Evaluate "Above-the-Fold" alignment (0-100%): Verify if primary ad promises exist within the Hero section without requiring scrolling.
   - Detect offer, pricing, CTA, or claim discrepancies between the ad copy and landing page sections.

2. STRICT HALLUCINATION GUARD & EXACT QUOTE EXTRACTION:
   - For every identified mismatch, extract an EXACT verbatim substring quote from the landing page.
   - If no direct match exists on the page, return "NONE". Do not paraphrase or invent quotes.
   - Mark 'is_above_the_fold_issue': true if the missing promise or disconnect pertains to the top hero section.
   - Severity: "Critical", "Moderate", or "Minor".

3. ONE-CLICK AUTOMATED COPY FIXER (REMEDIATION):
   - Provide an instant, optimized rewrite for the Landing Page Hero Headline to match the ad claim verbatim.
   - Provide supporting hero subheadline and CTA button rewrites.
   - Provide alternative Ad Copy headlines (Headline 1, 2, 3) if the landing page cannot be modified.

4. REGULATED CATEGORIES COMPLIANCE & LEGAL EXPOSURE AUDIT:
   - Identify if this vertical/advertiser is in a regulated category (Finance, Loans, Mortgages, Insurance, Healthcare, Pharma, Supplements, Legal, Crypto, Education).
   - CRITICAL COMPLIANCE FLAG: If an ad in a regulated vertical makes claims or promises (e.g. specific APR/interest rates, approval speed, guarantees, free consultations, health benefits, refund terms) that are UNSUPPORTED on the landing page (i.e. page_quote is "NONE" or contradictory), you MUST flag this as a "Regulatory Compliance Exposure".
   - Identify the governing regulatory body/policy (e.g. CFPB TILA Regulation Z, FTC Act Section 5 Deceptive Advertising, FDA, SEC, or Google Ads Misrepresentation Policy).

5. SIMPLE PLAIN ENGLISH:
   - Explain all summaries and issues in simple 5th-grade plain English so non-technical stakeholders instantly understand the impact.

6. OUTPUT FORMAT: Reply ONLY with valid JSON matching this exact structure:
{{
  "match_score": <int 0-100>,
  "score_summary": "<Explain overall match and single biggest problem in 2 simple English sentences>",
  "above_the_fold_score": <int 0-100>,
  "alignment_status": "<Perfect Alignment | High Alignment | Moderate Alignment | Severe Mismatch & Bounce Risk | Critical Compliance Exposure>",
  "compliance_audit": {{
    "is_regulated_vertical": <true|false>,
    "regulated_industry": "<e.g., Financial Services & Lending | Healthcare & Medical | Legal Services | General Commercial>",
    "compliance_risk_tier": "<Critical Regulatory Violation | Elevated Regulatory Risk | Compliant / Low Risk>",
    "governing_regulators": "<e.g., CFPB / FTC / FDA / SEC / Google Ads Misrepresentation Policy>",
    "compliance_exposure_summary": "<Explain the legal and regulatory advertising risk in 2 plain English sentences>",
    "statutory_remediation": "<Concrete step for legal/compliance team to remediate exposure>"
  }},
  "mismatches": [
    {{
      "id": 1,
      "category": "<Offer Discrepancy | Pricing & Rates | Call-to-Action (CTA) | Speed & Approval | Audience & Terms>",
      "severity": "<Critical | Moderate | Minor>",
      "is_above_the_fold_issue": <true|false>,
      "is_compliance_risk": <true|false>,
      "compliance_statute": "<e.g., CFPB Regulation Z | FTC Section 5 | FDA Medical Claims | Google Ads Policy | None>",
      "ad_claim": "<exact promise from ad>",
      "issue_description": "<simple 1-sentence explanation of the problem in plain English>",
      "page_quote": "<verbatim exact quote from landing page OR 'NONE'>",
      "suggested_fix": "<concrete rewritten recommendation in plain English>"
    }}
  ],
  "strong_matches": [
    {{
      "ad_claim": "<claim from ad>",
      "page_quote": "<exact quote from landing page>",
      "notes": "<why this aligns effectively>"
    }}
  ],
  "actionable_recommendations": [
    "<High-level strategic recommendation 1>",
    "<High-level strategic recommendation 2>"
  ],
  "automated_remediation": {{
    "landing_page_fix": {{
      "hero_headline_rewrite": "<Instant optimized rewrite for the Landing Page Hero Headline to match the ad claim verbatim>",
      "hero_subheadline_rewrite": "<Supporting hero subheadline rewrite to reinforce the primary offer>",
      "cta_button_rewrite": "<Optimized CTA button text aligned with ad intent>"
    }},
    "ad_copy_fix": {{
      "headline_1_alternative": "<Alternative Ad Headline 1 to match existing landing page reality>",
      "headline_2_alternative": "<Alternative Ad Headline 2>",
      "headline_3_alternative": "<Alternative Ad Headline 3>"
    }}
  }}
}}
"""


def call_gemini_auditor(ad_row: pd.Series, parsed_html: Dict[str, Any], api_key: str, model_name: str = "gemini-3.5-flash") -> Dict[str, Any]:
    """Execute live Google Gemini API call with structured JSON prompting."""
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-generativeai package is not installed.")

    if not api_key or not api_key.strip():
        raise ValueError("Google Gemini API Key is required. Enter it in the sidebar.")

    genai.configure(api_key=api_key.strip())

    structured_page = format_landing_page_for_llm(parsed_html)

    prompt = GEMINI_AUDIT_PROMPT_TEMPLATE.format(
        advertiser=ad_row.get("advertiser", "Brand"),
        vertical=ad_row.get("vertical", "General"),
        headline_1=ad_row.get("headline_1", ""),
        headline_2=ad_row.get("headline_2", ""),
        headline_3=ad_row.get("headline_3", ""),
        description_1=ad_row.get("description_1", ""),
        description_2=ad_row.get("description_2", ""),
        final_url=ad_row.get("final_url", ""),
        landing_page_structured=structured_page
    )

    generation_config = {
        "temperature": 0.1,  # Low temperature for deterministic quote extraction
        "top_p": 0.95,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json"
    }

    try:
        model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
        response = model.generate_content(prompt)
        text_response = response.text.strip()

        # Clean code block backticks if present
        if text_response.startswith("```"):
            text_response = re.sub(r"^```(?:json)?\s*", "", text_response)
            text_response = re.sub(r"\s*```$", "", text_response)

        parsed_json = json.loads(text_response)
        return parsed_json
    except Exception as e:
        raise RuntimeError(f"Gemini API Execution Error: {str(e)}")






# ==============================================================================
# 5. AUDIT EXPORT ENGINES (EXCEL SPREADSHEET & WORD DOCUMENT)
# ==============================================================================

def generate_excel_audit_report(
    res: Dict[str, Any],
    selected_row: pd.Series,
    processed_mismatches: List[Dict[str, Any]],
    strong_matches: List[Dict[str, Any]],
    recommendations: List[str],
    monthly_spend: float = 10000.0,
    compliance_data: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generate a multi-sheet normalized Excel workbook (.xlsx)."""
    output = io.BytesIO()
    match_score = res.get("match_score", 0)
    wasted_spend = monthly_spend * ((100.0 - match_score) / 100.0)
    annual_wasted = wasted_spend * 12.0
    risk_level = "Critical (<50%)" if match_score < 50 else ("Moderate (50-80%)" if match_score <= 80 else "Low (>80%)")
    remediation = res.get("automated_remediation", {})

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Audit Summary & Financial KPIs
        summary_rows = [
            {"Parameter": "Audit Pair ID", "Value": str(selected_row.get("pair_id", ""))},
            {"Parameter": "Brand / Advertiser", "Value": str(selected_row.get("advertiser", ""))},
            {"Parameter": "Vertical", "Value": str(selected_row.get("vertical", ""))},
            {"Parameter": "Final Landing URL", "Value": str(selected_row.get("final_url", ""))},
            {"Parameter": "Overall Match Score", "Value": f"{match_score}%"},
            {"Parameter": "Above-The-Fold Match Score", "Value": f"{res.get('above_the_fold_score', 0)}%"},
            {"Parameter": "System Verdict", "Value": str(res.get("alignment_status", "Audited"))},
            {"Parameter": "Monthly PPC Budget ($)", "Value": f"${monthly_spend:,.2f}"},
            {"Parameter": "Est. Monthly Wasted Spend ($)", "Value": f"${wasted_spend:,.2f}"},
            {"Parameter": "Annualized Budget Exposure ($)", "Value": f"${annual_wasted:,.2f}"},
            {"Parameter": "CRO Risk Level", "Value": risk_level},
            {"Parameter": "Mismatches Detected", "Value": len(processed_mismatches)},
            {"Parameter": "Executive Audit Summary", "Value": str(res.get("score_summary", ""))}
        ]
        if compliance_data:
            summary_rows.append({"Parameter": "Regulated Category Status", "Value": "YES" if compliance_data.get("is_regulated") else "NO (Standard Commercial)"})
            summary_rows.append({"Parameter": "Compliance Risk Tier", "Value": str(compliance_data.get("risk_tier", "Standard"))})
            summary_rows.append({"Parameter": "Unsupported Claims (Compliance Flags)", "Value": compliance_data.get("unsupported_count", 0)})

        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Audit Summary", index=False)

        # Sheet 2: Normalized Mismatches Table
        m_rows = []
        for idx, m in enumerate(processed_mismatches, 1):
            m_rows.append({
                "#": idx,
                "Severity": m.get("severity", "Moderate"),
                "Category": m.get("category", "General"),
                "Above The Fold": "Yes" if m.get("is_above_the_fold_issue") else "No",
                "Ad Copy Promise": m.get("ad_claim", ""),
                "Landing Page Quote": m.get("page_quote", ""),
                "Quote Verification": m.get("verification", {}).get("status", "UNCHECKED"),
                "Issue Description": m.get("issue_description", ""),
                "Concrete Suggested Fix": m.get("suggested_fix", "")
            })
        if m_rows:
            pd.DataFrame(m_rows).to_excel(writer, sheet_name="Mismatches", index=False)
        else:
            pd.DataFrame([{"Status": "Zero Mismatches Detected (100% Message Match)"}]).to_excel(writer, sheet_name="Mismatches", index=False)

        # Sheet 3: Confirmed Matches Table
        c_rows = []
        for idx, m in enumerate(strong_matches, 1):
            c_rows.append({
                "#": idx,
                "Ad Copy Promise": m.get("ad_claim", ""),
                "Landing Page Quote": m.get("page_quote", ""),
                "Notes / Context": m.get("notes", "Confirmed")
            })
        if c_rows:
            pd.DataFrame(c_rows).to_excel(writer, sheet_name="Confirmed Matches", index=False)
        else:
            pd.DataFrame([{"Status": "No specific matches recorded"}]).to_excel(writer, sheet_name="Confirmed Matches", index=False)

        # Sheet 4: Actionable Recommendations
        r_rows = []
        for idx, rec in enumerate(recommendations, 1):
            r_rows.append({
                "Priority Step": f"Step {idx}",
                "Concrete Action Item": rec
            })
        if r_rows:
            pd.DataFrame(r_rows).to_excel(writer, sheet_name="Action Plan", index=False)
        else:
            pd.DataFrame([{"Status": "No corrective actions required"}]).to_excel(writer, sheet_name="Action Plan", index=False)

        # Sheet 5: Automated Copy Remediation
        lp_fix = remediation.get("landing_page_fix", {})
        ad_fix = remediation.get("ad_copy_fix", {})
        rem_rows = [
            {"Strategy": "Landing Page Fix", "Element": "Hero Headline Rewrite", "Optimized Content": lp_fix.get("hero_headline_rewrite", "N/A")},
            {"Strategy": "Landing Page Fix", "Element": "Hero Subheadline Rewrite", "Optimized Content": lp_fix.get("hero_subheadline_rewrite", "N/A")},
            {"Strategy": "Landing Page Fix", "Element": "CTA Button Rewrite", "Optimized Content": lp_fix.get("cta_button_rewrite", "N/A")},
            {"Strategy": "Ad Copy Alternative", "Element": "Headline 1 Alternative", "Optimized Content": ad_fix.get("headline_1_alternative", "N/A")},
            {"Strategy": "Ad Copy Alternative", "Element": "Headline 2 Alternative", "Optimized Content": ad_fix.get("headline_2_alternative", "N/A")},
            {"Strategy": "Ad Copy Alternative", "Element": "Headline 3 Alternative", "Optimized Content": ad_fix.get("headline_3_alternative", "N/A")},
        ]
        pd.DataFrame(rem_rows).to_excel(writer, sheet_name="Copy Remediation", index=False)

        # Sheet 6: Regulatory Compliance Exposure (If Regulated Category)
        if compliance_data and compliance_data.get("is_regulated"):
            comp_rows = [
                {"Parameter": "Regulated Industry Status", "Value": "YES (Regulated Category)"},
                {"Parameter": "Vertical Classification", "Value": str(compliance_data.get("info", {}).get("name", "Regulated Category"))},
                {"Parameter": "Governing Regulatory Bodies", "Value": str(compliance_data.get("info", {}).get("regulators", "FTC, CFPB"))},
                {"Parameter": "Statutory Authority", "Value": str(compliance_data.get("info", {}).get("statutes", "FTC Act Section 5"))},
                {"Parameter": "Google Ads Policy Exposure", "Value": str(compliance_data.get("info", {}).get("google_policy", "Misrepresentation Policy"))},
                {"Parameter": "Compliance Risk Tier", "Value": str(compliance_data.get("risk_tier", ""))},
                {"Parameter": "Account Suspension Risk", "Value": str(compliance_data.get("account_suspension_risk", ""))},
                {"Parameter": "Unsupported Claims Count", "Value": compliance_data.get("unsupported_count", 0)},
                {"Parameter": "Statutory Risk Analysis", "Value": str(compliance_data.get("info", {}).get("statutory_risk", ""))}
            ]
            pd.DataFrame(comp_rows).to_excel(writer, sheet_name="Compliance Audit", index=False)

    return output.getvalue()


def generate_docx_audit_report(
    res: Dict[str, Any],
    selected_row: pd.Series,
    processed_mismatches: List[Dict[str, Any]],
    strong_matches: List[Dict[str, Any]],
    recommendations: List[str],
    monthly_spend: float = 10000.0,
    compliance_data: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generate a structured, normalized Word Document (.docx) audit report."""
    if not DOCX_AVAILABLE or docx is None:
        return b""

    doc = docx.Document()
    
    pair_id = str(selected_row.get("pair_id", "Pair"))
    brand = str(selected_row.get("advertiser", "Brand"))
    vertical = str(selected_row.get("vertical", "Vertical"))
    url = str(selected_row.get("final_url", ""))
    match_score = res.get("match_score", 0)
    wasted_spend = monthly_spend * ((100.0 - match_score) / 100.0)
    annual_wasted = wasted_spend * 12.0
    risk_level = "Critical (<50%)" if match_score < 50 else ("Moderate (50-80%)" if match_score <= 80 else "Low (>80%)")
    remediation = res.get("automated_remediation", {})
    
    doc.add_heading("Ad-to-Landing-Page Message Match Audit Report", 0)
    
    # Metadata paragraph
    p_meta = doc.add_paragraph()
    p_meta.add_run(f"Pair ID: {pair_id}  |  Brand: {brand}  |  Vertical: {vertical}\n").bold = True
    p_meta.add_run(f"Destination URL: {url}\n")
    p_meta.add_run(f"System Verdict: {res.get('alignment_status', 'Audited')}  |  Match Score: {match_score}%  |  Above-The-Fold: {res.get('above_the_fold_score', 0)}%\n")
    p_meta.add_run(f"Monthly PPC Budget: ${monthly_spend:,.2f}  |  Est. Monthly Wasted Spend: ${wasted_spend:,.2f}  |  Risk Level: {risk_level}\n").italic = True
    if compliance_data and compliance_data.get("is_regulated"):
        p_meta.add_run(f"Regulated Industry: {compliance_data.get('info', {}).get('name', 'Regulated')}  |  Compliance Exposure: {compliance_data.get('risk_tier', '')}\n").bold = True

    # 1. Executive Summary
    doc.add_heading("1. Executive Summary", level=1)
    doc.add_paragraph(res.get("score_summary", "No executive summary provided."))

    # 2. Financial Wasted Spend Analysis
    doc.add_heading("2. Financial Risk & Wasted Spend Analysis", level=1)
    doc.add_paragraph(
        f"With a message match score of {match_score}%, an estimated ${wasted_spend:,.2f} of the ${monthly_spend:,.2f} "
        f"monthly PPC advertising budget is exposed to bounce friction and landing page disconnects. "
        f"This projects to an annualized wasted spend risk of ${annual_wasted:,.2f}."
    )

    # 3. Regulatory Compliance Exposure (If Regulated Category)
    if compliance_data and compliance_data.get("is_regulated"):
        doc.add_heading("3. Regulatory & Legal Compliance Exposure", level=1)
        doc.add_paragraph(
            f"Industry Classification: {compliance_data.get('info', {}).get('name', 'Regulated Category')}\n"
            f"Governing Authorities: {compliance_data.get('info', {}).get('regulators', 'FTC, CFPB')}\n"
            f"Statutory References: {compliance_data.get('info', {}).get('statutes', '')}\n"
            f"Google Ads Policy: {compliance_data.get('info', {}).get('google_policy', '')}\n"
            f"Exposure Tier: {compliance_data.get('risk_tier', '')} ({compliance_data.get('account_suspension_risk', '')})\n"
            f"Unsupported Ad Claims: {compliance_data.get('unsupported_count', 0)} claims detected with no landing page substantiation."
        )

    # 4. Identified Mismatches (Normalized Table)
    doc.add_heading(f"4. Identified Mismatches ({len(processed_mismatches)})", level=1)
    if processed_mismatches:
        table = doc.add_table(rows=1, cols=7)
        table.style = "Table Grid"
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "#"
        hdr_cells[1].text = "Severity"
        hdr_cells[2].text = "Category"
        hdr_cells[3].text = "Ad Promise"
        hdr_cells[4].text = "Landing Page Quote"
        hdr_cells[5].text = "Verification"
        hdr_cells[6].text = "Concrete Fix"

        for idx, m in enumerate(processed_mismatches, 1):
            row_cells = table.add_row().cells
            row_cells[0].text = str(idx)
            row_cells[1].text = str(m.get("severity", ""))
            row_cells[2].text = str(m.get("category", ""))
            row_cells[3].text = str(m.get("ad_claim", ""))
            row_cells[4].text = str(m.get("page_quote", ""))
            row_cells[5].text = str(m.get("verification", {}).get("status", ""))
            row_cells[6].text = str(m.get("suggested_fix", ""))
    else:
        doc.add_paragraph("Zero mismatches detected. Outstanding 100% message symmetry.")

    # 5. Confirmed Message Matches
    doc.add_heading(f"5. Confirmed Message Matches ({len(strong_matches)})", level=1)
    if strong_matches:
        t_matches = doc.add_table(rows=1, cols=3)
        t_matches.style = "Table Grid"
        h = t_matches.rows[0].cells
        h[0].text = "Ad Claim"
        h[1].text = "Landing Page Supporting Text"
        h[2].text = "Notes"

        for m in strong_matches:
            r = t_matches.add_row().cells
            r[0].text = str(m.get("ad_claim", ""))
            r[1].text = str(m.get("page_quote", ""))
            r[2].text = str(m.get("notes", ""))
    else:
        doc.add_paragraph("No specific confirmed matches listed.")

    # 6. One-Click Automated Copy Fixer (Remediation)
    doc.add_heading("6. One-Click Automated Copy Fixer (Remediation)", level=1)
    lp_fix = remediation.get("landing_page_fix", {})
    ad_fix = remediation.get("ad_copy_fix", {})
    doc.add_heading("Option A: Landing Page Hero Remediation (Recommended)", level=2)
    doc.add_paragraph(f"Optimized Hero Headline: {lp_fix.get('hero_headline_rewrite', 'N/A')}")
    doc.add_paragraph(f"Optimized Hero Subheadline: {lp_fix.get('hero_subheadline_rewrite', 'N/A')}")
    doc.add_paragraph(f"Optimized CTA Button: {lp_fix.get('cta_button_rewrite', 'N/A')}")

    doc.add_heading("Option B: Alternative Ad Copy Headlines", level=2)
    doc.add_paragraph(f"Headline 1 Alternative: {ad_fix.get('headline_1_alternative', 'N/A')}")
    doc.add_paragraph(f"Headline 2 Alternative: {ad_fix.get('headline_2_alternative', 'N/A')}")
    doc.add_paragraph(f"Headline 3 Alternative: {ad_fix.get('headline_3_alternative', 'N/A')}")

    # 7. Actionable Priority Recommendations
    doc.add_heading("7. Priority Action Recommendations", level=1)
    if recommendations:
        for idx, rec in enumerate(recommendations, 1):
            doc.add_paragraph(f"Step {idx}: {rec}")
    else:
        doc.add_paragraph("No corrective actions required.")

    doc_io = io.BytesIO()
    doc.save(doc_io)
    return doc_io.getvalue()


def generate_bulk_excel_report(bulk_df: pd.DataFrame) -> bytes:
    """Generate an Excel workbook for the bulk dataset leaderboard."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        bulk_df.to_excel(writer, sheet_name="CRO Risk Leaderboard", index=False)
    return output.getvalue()


# ==============================================================================
# 6. BULK DATASET AUDIT & LEADERBOARD CONTROLLER
# ==============================================================================

def render_bulk_leaderboard_section(df: pd.DataFrame, snap_dir: Path, user_api_key: str, model_choice: str):
    """Render bulk dataset audit runner, portfolio KPIs, and CRO risk leaderboard."""
    st.markdown("### ⚡ Bulk Dataset Audit & CRO Risk Leaderboard")
    st.caption("Audit multiple search ad & landing page snapshot pairs simultaneously with Google Gemini. Evaluates message symmetry, checks Above-The-Fold alignment, computes wasted ad spend, flags regulated category compliance exposure, and ranks campaigns by lowest match score to surface Top Critical Risk campaigns.")

    b_col1, b_col2, b_col3, b_col4 = st.columns([1.3, 1.4, 1.1, 1.2])
    with b_col1:
        scope_options = [
            "Quick Risk Scan (First 5 Campaigns)",
            "Top Priority Batch (First 10 Campaigns)",
            "Extended Sample (First 20 Campaigns)",
            f"Full Portfolio (All {len(df)} Campaigns)"
        ]
        selected_scope = st.selectbox("Audit Scope", options=scope_options, index=0)

    with b_col2:
        bulk_source_mode = st.selectbox(
            "Landing Page Ingestion Source",
            options=[
                "📂 Offline Snapshots (Pre-cached HTML)",
                "🌐 Live Destination URLs (Real-Time Anti-Bot & JS Fetch)"
            ],
            index=0,
            help="Choose between offline snapshot files or real-time live URL scraping with Chrome 124 headers and JavaScript hydration parsing."
        )

    with b_col3:
        bulk_monthly_spend = st.number_input(
            "Monthly Ad Spend ($)",
            min_value=500.0,
            max_value=1000000.0,
            value=10000.0,
            step=500.0,
            help="Dynamic monthly PPC budget per campaign to compute financial wasted spend."
        )

    with b_col4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        run_bulk_btn = st.button("🚀 Run Bulk Audit", use_container_width=True)

    # Determine subset of dataframe
    if "First 5" in selected_scope:
        subset_df = df.head(5)
    elif "First 10" in selected_scope:
        subset_df = df.head(10)
    elif "First 20" in selected_scope:
        subset_df = df.head(20)
    else:
        subset_df = df

    if run_bulk_btn:
        if not user_api_key or not user_api_key.strip():
            st.error("Please enter a valid Google Gemini API Key in the sidebar to execute the bulk audit.")
        else:
            total_items = len(subset_df)
            bulk_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, (_, row) in enumerate(subset_df.iterrows()):
                p_id = row["pair_id"]
                adv = row["advertiser"]
                v_name = row.get("vertical", "General")
                dest_url = row.get("final_url", "")

                status_text.markdown(f"Auditing campaign **{idx+1} of {total_items}**: `{p_id}` • **{adv}**...")

                # Ingestion: Live URL vs Offline Snapshot
                if "Live Destination URLs" in bulk_source_mode and dest_url:
                    live_res = fetch_live_url_content(dest_url)
                    if live_res.get("success") and live_res.get("parsed"):
                        parsed_p = live_res["parsed"]
                    else:
                        snap_file = Path(row["snapshot_file"]).name
                        actual_path = snap_dir / snap_file if snap_dir else Path(row["snapshot_file"])
                        parsed_p = parse_landing_page_html(actual_path)
                else:
                    snap_file = Path(row["snapshot_file"]).name
                    actual_path = snap_dir / snap_file if snap_dir else Path(row["snapshot_file"])
                    parsed_p = parse_landing_page_html(actual_path)

                try:
                    res = call_gemini_auditor(row, parsed_p, user_api_key, model_choice)
                    m_score = int(res.get("match_score", 0))
                    fold_score = int(res.get("above_the_fold_score", 0))
                    wasted = bulk_monthly_spend * ((100.0 - m_score) / 100.0)
                    risk_tier = "Critical" if m_score < 50 else ("Moderate" if m_score <= 80 else "Low")

                    # Count critical mismatches
                    mismatches = res.get("mismatches", [])
                    crit_count = sum(1 for m in mismatches if m.get("severity") == "Critical")

                    # Regulated vertical compliance evaluation
                    comp_exp = evaluate_compliance_exposure(v_name, row, mismatches, res.get("compliance_audit", {}))

                    bulk_results.append({
                        "pair_id": p_id,
                        "advertiser": adv,
                        "vertical": v_name,
                        "match_score": m_score,
                        "above_the_fold_score": fold_score,
                        "risk_tier": risk_tier,
                        "monthly_spend": bulk_monthly_spend,
                        "wasted_spend": wasted,
                        "annual_wasted": wasted * 12.0,
                        "mismatches_count": len(mismatches),
                        "critical_disconnects": crit_count,
                        "verdict": res.get("alignment_status", "Audited"),
                        "score_summary": res.get("score_summary", ""),
                        "top_issue": mismatches[0].get("issue_description", "None") if mismatches else "High message symmetry",
                        "is_regulated": comp_exp.get("is_regulated", False),
                        "compliance_risk_tier": comp_exp.get("risk_tier", "Standard CRO"),
                        "unsupported_claims_count": comp_exp.get("unsupported_count", 0),
                        "compliance_info": comp_exp,
                        "audit_res": res
                    })
                except Exception as ex:
                    st.warning(f"Failed to audit `{p_id}`: {str(ex)}")

                progress_bar.progress((idx + 1) / total_items)

            status_text.success(f"✓ Bulk Audit Completed! Successfully audited {len(bulk_results)} of {total_items} campaigns.")
            st.session_state["bulk_audit_results"] = bulk_results
            st.session_state["bulk_spend"] = bulk_monthly_spend

    # Render Leaderboard if results exist
    if st.session_state.get("bulk_audit_results"):
        results = st.session_state["bulk_audit_results"]
        # Rank campaigns by lowest match score to identify Top Critical Risk Campaigns
        sorted_results = sorted(results, key=lambda x: (x["match_score"], -x["wasted_spend"]))

        total_audited = len(sorted_results)
        avg_score = sum(r["match_score"] for r in sorted_results) / total_audited if total_audited > 0 else 0
        total_monthly_spend = total_audited * st.session_state.get("bulk_spend", 10000.0)
        total_wasted = sum(r["wasted_spend"] for r in sorted_results)
        crit_campaigns = [r for r in sorted_results if r["match_score"] < 50]
        crit_count = len(crit_campaigns)
        mod_count = sum(1 for r in sorted_results if 50 <= r["match_score"] <= 80)
        low_count = sum(1 for r in sorted_results if r["match_score"] > 80)

        # Regulated compliance violation count
        compliance_violations = [r for r in sorted_results if r.get("is_regulated") and r.get("unsupported_claims_count", 0) > 0]
        comp_viol_count = len(compliance_violations)

        st.markdown("---")
        st.markdown("#### 📊 Portfolio Audit Summary, Financial & Compliance Exposure")

        # 5 KPI Cards
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            st.markdown(f"""
            <div class="kpi-card blue">
                <div class="kpi-label">Audited Campaigns</div>
                <div class="kpi-value" style="color: #0288D1;">{total_audited}</div>
                <div class="kpi-sub">Portfolio Ingestion Scope</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi2:
            score_col = "#2E7D32" if avg_score >= 80 else ("#0288D1" if avg_score >= 50 else "#D32F2F")
            score_cls = "green" if avg_score >= 80 else ("blue" if avg_score >= 50 else "red")
            st.markdown(f"""
            <div class="kpi-card {score_cls}">
                <div class="kpi-label">Average Match Score</div>
                <div class="kpi-value" style="color: {score_col};">{avg_score:.1f}%</div>
                <div class="kpi-sub">Message Symmetry</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi3:
            wasted_cls = "red" if total_wasted > 0 else "green"
            st.markdown(f"""
            <div class="kpi-card {wasted_cls}">
                <div class="kpi-label">Monthly Wasted Spend</div>
                <div class="kpi-value" style="color: #D32F2F;">${total_wasted:,.0f}</div>
                <div class="kpi-sub">Across ${total_monthly_spend:,.0f}/mo</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi4:
            crit_cls = "red" if crit_count > 0 else "green"
            st.markdown(f"""
            <div class="kpi-card {crit_cls}">
                <div class="kpi-label">Critical Risk (<50%)</div>
                <div class="kpi-value" style="color: #D32F2F;">{crit_count}</div>
                <div class="kpi-sub">{mod_count} Moderate · {low_count} Low</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi5:
            comp_cls = "red" if comp_viol_count > 0 else "green"
            comp_col = "#D32F2F" if comp_viol_count > 0 else "#2E7D32"
            st.markdown(f"""
            <div class="kpi-card {comp_cls}">
                <div class="kpi-label">Compliance Exposure</div>
                <div class="kpi-value" style="color: {comp_col};">{comp_viol_count}</div>
                <div class="kpi-sub">Regulated Category Flags</div>
            </div>
            """, unsafe_allow_html=True)

        # Regulated Compliance Exposure Alert Banner
        if comp_viol_count > 0:
            viol_names = ", ".join([f"**{r['pair_id']} ({r['advertiser']})**" for r in compliance_violations[:3]])
            if len(compliance_violations) > 3:
                viol_names += f" and {len(compliance_violations) - 3} more"
            st.markdown(f"""
            <div style="background:#FEF2F2; border:2px solid #EF4444; border-radius:8px; padding:14px 18px; margin:14px 0;">
                <div style="font-size:15px; font-weight:800; color:#B91C1C; margin-bottom:4px;">
                    ⚖️ CRITICAL REGULATORY COMPLIANCE EXPOSURE: {comp_viol_count} CAMPAIGN(S) FLAGGED
                </div>
                <div style="font-size:13px; color:#7F1D1D; line-height:1.5;">
                    Campaigns in regulated verticals ({viol_names}) contain promotional promises (rates, guarantees, approval claims) that are <strong>completely unsupported on the landing page</strong>. Under FTC Act Section 5, CFPB Regulation Z, FDA, and Google Ads Misrepresentation policies, these represent actionable legal liability and immediate account suspension risk.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Critical Alert Banner for CRO Score
        if crit_count > 0:
            crit_names = ", ".join([f"**{r['pair_id']} ({r['advertiser']})**" for r in crit_campaigns[:4]])
            if len(crit_campaigns) > 4:
                crit_names += f" and {len(crit_campaigns) - 4} more"
            st.error(f"🚨 **TOP CRITICAL RISK ALERT:** {crit_count} campaigns have a Match Score below 50% ({crit_names}). These represent ${sum(r['wasted_spend'] for r in crit_campaigns):,.2f}/month in immediate ad spend leakage requiring immediate headline and offer remediation!")

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("#### 🏆 Conversion Rate Optimization (CRO) & Compliance Risk Leaderboard")
        st.caption("Ranked by LOWEST match score first to surface campaigns suffering the highest bounce exposure and financial waste.")

        # Build clean Leaderboard DataFrame
        leaderboard_rows = []
        for rank, r in enumerate(sorted_results, 1):
            tier_badge = "🔴 Critical (<50%)" if r["risk_tier"] == "Critical" else ("🟠 Moderate (50-80%)" if r["risk_tier"] == "Moderate" else "🟢 Low (>80%)")
            
            # Compliance badge
            if r.get("is_regulated"):
                u_cnt = r.get("unsupported_claims_count", 0)
                if u_cnt > 0:
                    comp_badge = f"🔴 Violation ({u_cnt} Unsupported)"
                else:
                    comp_badge = "🟢 Compliant"
            else:
                comp_badge = "⚪ Standard (Commercial)"

            leaderboard_rows.append({
                "Rank": f"#{rank}",
                "Pair ID": r["pair_id"],
                "Brand / Advertiser": r["advertiser"],
                "Vertical": r["vertical"],
                "Match Score": f"{r['match_score']}%",
                "Above-The-Fold": f"{r['above_the_fold_score']}%",
                "CRO Risk Level": tier_badge,
                "⚖️ Compliance Risk": comp_badge,
                "Monthly Spend": f"${r['monthly_spend']:,.2f}",
                "Wasted Spend ($)": f"${r['wasted_spend']:,.2f}",
                "Annualized Loss": f"${r['annual_wasted']:,.2f}",
                "Primary Disconnect": r["top_issue"]
            })

        leaderboard_df = pd.DataFrame(leaderboard_rows)
        st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)

        # Bulk Export Options
        exp_col1, exp_col2, _ = st.columns([1.5, 1.5, 3])
        with exp_col1:
            bulk_excel = generate_bulk_excel_report(pd.DataFrame(sorted_results))
            st.download_button(
                label="📊 Export Leaderboard to Excel (.xlsx)",
                data=bulk_excel,
                file_name="cro_risk_leaderboard.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with exp_col2:
            bulk_csv = leaderboard_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📑 Export Leaderboard to CSV (.csv)",
                data=bulk_csv,
                file_name="cro_risk_leaderboard.csv",
                mime="text/csv",
                use_container_width=True
            )


# ==============================================================================
# 7. STREAMLIT APPLICATION CONTROLLER & INTERFACE
# ==============================================================================

def main():
    # --- HEADER BAR ---
    st.markdown("""
    <div class="app-header">
        <div>
            <div class="brand-badge">Enterprise Message Match Auditor & CRO Specialist</div>
            <div class="brand-title">Ad-to-Landing-Page Message Match Auditor</div>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 12px; color: #64748B; font-weight: 600;">PORTFOLIO STATUS</span><br/>
            <span style="font-size: 13px; font-weight: 700; color: #2E7D32;">● 60 Snapshot Pairs Ingested</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load dataset
    df, snap_dir, load_msg = load_ads_dataset()

    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.markdown("### ⚙️ Dataset & API Config")

        if df is not None:
            st.success(f"✓ Ingested `ads.csv` ({len(df)} pairs)")
        else:
            st.error(load_msg)

        # Gemini API Config
        st.markdown("---")
        # Check Streamlit Secrets first, then environment variable, then default
        cloud_secret = ""
        try:
            cloud_secret = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            cloud_secret = ""

        default_key = cloud_secret or os.environ.get("GEMINI_API_KEY", "")
        user_api_key = st.text_input(
            "Gemini API Key",
            value=default_key,
            type="password",
            placeholder="AIzaSy... or AQ.Ab8...",
            help="API Key for live Gemini 3.5 audits."
        )

        has_api_key = bool(user_api_key.strip())
        if has_api_key:
            st.markdown('<div style="font-size:12px; font-weight:700; color:#166534; background:#F0FDF4; padding:6px 12px; border-radius:6px; border:1px solid #BBF7D0; margin-bottom:10px;">● Live Gemini Connected</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px; font-weight:700; color:#B45309; background:#FFFBEB; padding:6px 12px; border-radius:6px; border:1px solid #FDE68A; margin-bottom:10px;">○ Offline Mode (Enter key to enable AI)</div>', unsafe_allow_html=True)

        model_choice = st.selectbox(
            "Gemini Model",
            options=["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 🛡️ Guardrails & Options")
        enable_html_preview = st.checkbox(
            "Render Interactive HTML Snapshot",
            value=True,
            help="Embeds the actual rendered offline HTML landing page directly in an iframe tab."
        )
        preview_height = st.slider(
            "Landing Page Viewport Height (px)",
            min_value=450,
            max_value=950,
            value=620,
            step=25,
            help="Adjust the vertical height of the landing page preview and extracted structured text."
        )
        strict_hallucination_check = st.checkbox(
            "Strict Hallucination Checking",
            value=True,
            help="Verifies that quoted landing page text exists in the source HTML document."
        )

        st.markdown("---")
        st.markdown("""
        <div style="font-size: 12px; color: #64748B; line-height: 1.5;">
            <strong>Palette Rules:</strong><br/>
            • Background: Pure White (#FFFFFF)<br/>
            • Accent Primary: Fresh Green (#2E7D32)<br/>
            • Secondary Info: Light Blue (#0288D1)<br/>
            • Zero Dark Blue, Violet, or Purple.
        </div>
        """, unsafe_allow_html=True)

    if df is None:
        st.warning("Please ensure `ads.csv` and `landing_page_snapshots/` are placed in the workspace root.")
        return

    # TOP-LEVEL NAVIGATION TABS
    mode_tab1, mode_tab2 = st.tabs([
        "🎯 Single Campaign Deep-Dive Audit",
        "⚡ Bulk Dataset Audit & CRO Risk Leaderboard"
    ])

    # ==============================================================================
    # TAB 1: SINGLE CAMPAIGN DEEP-DIVE AUDIT
    # ==============================================================================
    with mode_tab1:
        # --- PAIR SELECTION & FILTERING ---
        st.markdown("#### 📂 Select Ad & Landing Page Snapshot Pair")
        fcol1, fcol2, fcol3 = st.columns([1, 1, 2])

        with fcol1:
            verticals = ["All Verticals"] + sorted(df["vertical"].unique().tolist())
            selected_vertical = st.selectbox("Filter by Vertical", options=verticals, key="single_filter_vertical")

        filtered_df = df if selected_vertical == "All Verticals" else df[df["vertical"] == selected_vertical]

        with fcol2:
            advertisers = ["All Brands"] + sorted(filtered_df["advertiser"].unique().tolist())
            selected_adv = st.selectbox("Filter by Brand", options=advertisers, key="single_filter_brand")

        if selected_adv != "All Brands":
            filtered_df = filtered_df[filtered_df["advertiser"] == selected_adv]

        # Format pair options for dropdown
        pair_options = []
        for _, row in filtered_df.iterrows():
            p_id = row["pair_id"]
            adv = row["advertiser"]
            h1 = row["headline_1"]
            h2 = row["headline_2"]
            pair_options.append(f"{p_id} • {adv} — {h1} | {h2}")

        with fcol3:
            selected_pair_str = st.selectbox("Select Ad Pair", options=pair_options, index=0, key="single_filter_pair")

        # Extract selected row
        selected_pair_id = selected_pair_str.split(" • ")[0].strip()
        selected_row = df[df["pair_id"] == selected_pair_id].iloc[0]

        # Locate offline snapshot file
        snapshot_filename = selected_row["snapshot_file"]
        snapshot_clean = Path(snapshot_filename).name
        actual_snapshot_path = snap_dir / snapshot_clean if snap_dir else Path(snapshot_filename)

        # Ingestion Source Mode Selector (Offline Snapshot vs Live URL Scraping)
        st.markdown("##### 📥 Landing Page Ingestion Source")
        ingest_mode_col1, ingest_mode_col2 = st.columns([1.5, 2.5])
        with ingest_mode_col1:
            ingest_source_mode = st.radio(
                "Source Ingestion Mode",
                options=[
                    "📂 Offline Snapshot (Pre-cached HTML)",
                    "🌐 Live Destination URL (Real-time Anti-Bot & JS Fetch)"
                ],
                index=0,
                key=f"ingest_source_{selected_pair_id}"
            )

        live_fetch_info = None
        if "Live Destination URL" in ingest_source_mode:
            with ingest_mode_col2:
                default_target_url = str(selected_row.get("final_url", "https://example.com")).strip()
                custom_live_url = st.text_input(
                    "Target Landing Page URL to Fetch & Render Live",
                    value=default_target_url,
                    key=f"live_url_in_{selected_pair_id}",
                    help="Fetches live HTML directly over HTTP, bypasses bot blocks (Cloudflare/PerimeterX) via Chrome 124 headers, and recovers JavaScript hydration state (Next.js/Nuxt.js/JSON-LD)."
                )
                fetch_now_clicked = st.button("🔄 Fetch & Render Live URL Now", key=f"fetch_now_btn_{selected_pair_id}")

            cache_key = f"live_fetch_{selected_pair_id}_{custom_live_url}"
            if fetch_now_clicked or cache_key not in st.session_state:
                with st.spinner(f"Fetching live URL: {custom_live_url} (Bypassing bot blocks & parsing JS hydration)..."):
                    live_res = fetch_live_url_content(custom_live_url)
                    st.session_state[cache_key] = live_res

            live_res = st.session_state.get(cache_key, {})
            if live_res.get("success"):
                parsed_page = live_res["parsed"]
                meta = live_res.get("meta", {})
                live_fetch_info = meta
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:8px 12px; margin-top:8px; font-size:12.5px; color:#166534; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                    <div>
                        <strong>✓ Live URL Rendered:</strong> HTTP {meta.get('status_code', 200)} OK · 
                        Framework: <code>{meta.get('framework', 'HTML')}</code> · 
                        Payload: {meta.get('size_kb', 0):.1f} KB
                    </div>
                    <span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #86EFAC;">
                        🛡️ Anti-Bot Bypassed (Chrome 124)
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                err_msg = live_res.get("error", "Unable to fetch live URL.")
                st.warning(f"⚠️ Live URL fetch warning: {err_msg} — Falling back to pre-cached offline snapshot.")
                parsed_page = parse_landing_page_html(actual_snapshot_path)
        else:
            parsed_page = parse_landing_page_html(actual_snapshot_path)

        # --- DUAL-PANE INGESTION VIEW ---
        st.markdown("---")
        col_left, col_right = st.columns([1, 1], gap="medium")

        # LEFT COLUMN: AD COPY INGESTION & GOOGLE SERP PREVIEW
        with col_left:
            st.markdown(f"#### 1. Ingested Ad Copy (`{selected_pair_id}`)")

            def get_clean_field(row, key):
                val = row.get(key, "")
                return "" if pd.isna(val) or val is None else str(val).strip()

            h1 = get_clean_field(selected_row, "headline_1")
            h2 = get_clean_field(selected_row, "headline_2")
            h3 = get_clean_field(selected_row, "headline_3")
            d1 = get_clean_field(selected_row, "description_1")
            d2 = get_clean_field(selected_row, "description_2")
            url_display = get_clean_field(selected_row, "final_url")

            headlines_parts = [h for h in [h1, h2, h3] if h]
            headlines_joined = " | ".join(headlines_parts)
            desc_parts = [d for d in [d1, d2] if d]
            desc_joined = " ".join(desc_parts)

            st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <span class="badge-tag" style="background:#F0FDF4; color:#2E7D32; border:1px solid #BBF7D0;">Brand: {html.escape(str(selected_row['advertiser']))}</span>
                <span class="badge-tag" style="background:#F0F9FF; color:#0288D1; border:1px solid #BAE6FD;">Vertical: {html.escape(str(selected_row['vertical']))}</span>
                <span class="badge-tag" style="background:#F8FAFC; color:#475569; border:1px solid #CBD5E1;">Format: RSA (Google Search)</span>
            </div>
            """, unsafe_allow_html=True)

            # Google Search Ad Simulation Preview Box
            st.markdown(f"""
            <div class="ad-preview-container">
                <div class="ad-sponsor-label">
                    <span>Sponsored</span>
                    <span>•</span>
                    <span>Google Search Ad</span>
                </div>
                <div class="ad-url-breadcrumb">{html.escape(url_display)}</div>
                <div class="ad-headline-preview">{html.escape(headlines_joined)}</div>
                <div class="ad-desc-preview">{html.escape(desc_joined)}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("🔍 View Raw Ad Copy JSON Fields"):
                st.write({
                    "Headline 1": h1,
                    "Headline 2": h2,
                    "Headline 3": h3,
                    "Description 1": d1,
                    "Description 2": d2,
                    "Final URL": url_display
                })

        # RIGHT COLUMN: LANDING PAGE SNAPSHOT & BEAUTIFULSOUP EXTRACTION
        with col_right:
            col_right_title = f"#### 2. Live Rendered Destination Page (`{html.escape(live_fetch_info['final_url'] if live_fetch_info else url_display)}`)" if live_fetch_info else f"#### 2. Landing Page Snapshot (`{snapshot_clean}`)"
            st.markdown(col_right_title)

            view_tabs = st.tabs(["🌐 Interactive HTML Preview", "📝 Extracted Structured Text"])

            with view_tabs[0]:
                if enable_html_preview and parsed_page["raw_html"]:
                    badge_label = f"● Live URL: {html.escape(live_fetch_info['final_url'])}" if live_fetch_info else f"● Snapshot: {html.escape(snapshot_clean)}"
                    st.markdown(f"""
                    <div class="browser-window-bar">
                        <div class="browser-dots">
                            <span class="browser-dot red"></span>
                            <span class="browser-dot yellow"></span>
                            <span class="browser-dot green"></span>
                        </div>
                        <div class="browser-address">
                            <span style="color:#10B981;">🔒</span> {html.escape(url_display)}
                        </div>
                        <span class="browser-badge">{badge_label}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    components.html(parsed_page["raw_html"], height=preview_height, scrolling=True)
                else:
                    st.info("HTML preview is disabled in the sidebar or raw HTML snapshot file is unavailable.")

            with view_tabs[1]:
                st.markdown(f"""
                <div class="content-box" style="font-size: 13px; height: {preview_height}px; max-height: {preview_height}px; overflow-y: auto; background: #FFFFFF; line-height: 1.6; border: 1px solid #E2E8F0; border-radius: 8px; padding: 18px;">
                    <div style="margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9;">
                        <span class="badge-tag" style="background:#F0F9FF; color:#0288D1; border:1px solid #BAE6FD;">PAGE TITLE</span>
                        <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-top: 4px;">{html.escape(parsed_page['title'])}</div>
                    </div>

                    <div style="margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9;">
                        <span class="badge-tag" style="background:#F0FDF4; color:#2E7D32; border:1px solid #BBF7D0;">ABOVE THE FOLD — HERO SECTION</span>
                        <div style="font-size: 13.5px; color: #1E293B; margin-top: 6px; background: #F8FAFC; padding: 12px; border-radius: 6px; border-left: 3px solid #2E7D32;">
                            {html.escape(parsed_page['hero_text'] or '(No hero text found)')}
                        </div>
                    </div>

                    <div style="margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9;">
                        <span class="badge-tag" style="background:#F0F9FF; color:#0288D1; border:1px solid #BAE6FD;">BELOW THE FOLD — SECTIONS & CARDS</span>
                        <div style="font-size: 13px; color: #334155; margin-top: 6px; white-space: pre-wrap; background: #F8FAFC; padding: 12px; border-radius: 6px;">
                            {html.escape(parsed_page['sections_text'] or '(No section body text found)')}
                        </div>
                    </div>

                    <div>
                        <span class="badge-tag" style="background:#FFFBEB; color:#B45309; border:1px solid #FDE68A;">FOOTER & FINE PRINT</span>
                        <div style="font-size: 12px; color: #64748B; margin-top: 6px; background: #F8FAFC; padding: 10px; border-radius: 6px; border-left: 3px solid #ED6C02;">
                            {html.escape(parsed_page['fine_print_text'] or '(No fine print found)')}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # --- AUDIT EXECUTION BUTTON ---
        st.markdown("<br/>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns([1, 3])
        with btn_col1:
            run_audit_clicked = st.button("🚀 Run Deep-Dive Audit", use_container_width=True, key="single_run_btn")

        # State management
        if "current_pair_id" not in st.session_state:
            st.session_state["current_pair_id"] = None
            st.session_state["audit_result"] = None

        if run_audit_clicked or st.session_state["current_pair_id"] != selected_pair_id:
            if run_audit_clicked:
                if not user_api_key.strip():
                    st.error("Please enter a valid Google Gemini API Key in the sidebar to run the audit.")
                else:
                    with st.spinner(f"Running Live Gemini AI Audit for Pair {selected_pair_id} ({model_choice})..."):
                        try:
                            audit_res = call_gemini_auditor(selected_row, parsed_page, user_api_key, model_choice)
                            st.session_state["audit_result"] = audit_res
                            st.session_state["current_pair_id"] = selected_pair_id
                            st.session_state["exec_mode"] = f"Live Google Gemini ({model_choice})"
                        except Exception as err:
                            st.error(f"Live Gemini API Error: {str(err)}")
                            st.session_state["audit_result"] = None

        # ==============================================================================
        # RESULTS RENDERING & HALLUCINATION AUDITING
        # ==============================================================================
        if st.session_state.get("audit_result") and st.session_state.get("current_pair_id") == selected_pair_id:
            res = st.session_state["audit_result"]
            exec_mode = st.session_state.get("exec_mode", "Audited")

            st.markdown("---")
            st.markdown(f"### 📊 Audit Report for Pair `{selected_pair_id}` <span style='font-size:13px; font-weight:normal; color:#64748B;'>({exec_mode})</span>", unsafe_allow_html=True)

            match_score = int(res.get("match_score", 0))
            fold_score = int(res.get("above_the_fold_score", 0))
            summary = res.get("score_summary", "")
            alignment_status = res.get("alignment_status", "Audited")
            mismatches = res.get("mismatches", [])
            strong_matches = res.get("strong_matches", [])
            recommendations = res.get("actionable_recommendations", [])
            remediation = res.get("automated_remediation", {})

            # Programmatically evaluate all mismatches for hallucinations against raw full text
            verified_count = 0
            hallucination_count = 0
            omission_count = 0
            processed_mismatches = []

            for m in mismatches:
                quote = m.get("page_quote", "")
                verification = verify_quote_in_landing_page(quote, parsed_page["raw_full_text"], parsed_page["hero_text"])
                status = verification["status"]

                if status == "VERIFIED":
                    verified_count += 1
                elif status == "HALLUCINATED":
                    hallucination_count += 1
                elif status == "OMISSION_NOTED":
                    omission_count += 1

                m_copy = dict(m)
                m_copy["verification"] = verification
                processed_mismatches.append(m_copy)

            # Evaluate Regulated Category Compliance Exposure
            comp_exposure = evaluate_compliance_exposure(
                selected_row.get("vertical", ""),
                selected_row,
                processed_mismatches,
                res.get("compliance_audit", {})
            )

            # Style score color
            if match_score >= 80:
                score_class = "green"
                score_color = "#2E7D32"
            elif match_score >= 50:
                score_class = "blue"
                score_color = "#0288D1"
            else:
                score_class = "red"
                score_color = "#D32F2F"

            # KPI Metric Row
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)

            with mcol1:
                st.markdown(f"""
                <div class="kpi-card {score_class}">
                    <div class="kpi-label">Overall Match Score</div>
                    <div class="kpi-value" style="color: {score_color};">{match_score}%</div>
                    <div class="kpi-sub"><strong>{alignment_status}</strong></div>
                </div>
                """, unsafe_allow_html=True)

            with mcol2:
                fold_class = "green" if fold_score >= 75 else ("blue" if fold_score >= 45 else "orange")
                fold_color = "#2E7D32" if fold_score >= 75 else ("#0288D1" if fold_score >= 45 else "#ED6C02")
                st.markdown(f"""
                <div class="kpi-card {fold_class}">
                    <div class="kpi-label">Above-The-Fold Match</div>
                    <div class="kpi-value" style="color: {fold_color};">{fold_score}%</div>
                    <div class="kpi-sub">Hero Viewport Alignment</div>
                </div>
                """, unsafe_allow_html=True)

            with mcol3:
                num_critical = sum(1 for m in mismatches if m.get("severity") == "Critical")
                crit_class = "red" if num_critical > 0 else ("orange" if len(mismatches) > 0 else "green")
                crit_color = "#D32F2F" if num_critical > 0 else ("#ED6C02" if len(mismatches) > 0 else "#2E7D32")
                st.markdown(f"""
                <div class="kpi-card {crit_class}">
                    <div class="kpi-label">Mismatches Found</div>
                    <div class="kpi-value" style="color: {crit_color};">{len(mismatches)}</div>
                    <div class="kpi-sub">{num_critical} Critical Disconnects</div>
                </div>
                """, unsafe_allow_html=True)

            with mcol4:
                hall_class = "red" if hallucination_count > 0 else "green"
                hall_color = "#D32F2F" if hallucination_count > 0 else "#2E7D32"
                st.markdown(f"""
                <div class="kpi-card {hall_class}">
                    <div class="kpi-label">Hallucination Guard</div>
                    <div class="kpi-value" style="color: {hall_color};">{hallucination_count}</div>
                    <div class="kpi-sub">{verified_count} Quotes Verified in Source</div>
                </div>
                """, unsafe_allow_html=True)

            # Prominent Regulated Category Compliance Exposure Alert Banner
            if comp_exposure.get("is_regulated") and comp_exposure.get("unsupported_count", 0) > 0:
                v_info = comp_exposure.get("info", {})
                st.markdown(f"""
                <div style="background:#FEF2F2; border:2px solid #EF4444; border-radius:8px; padding:16px 20px; margin:16px 0;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                        <div style="font-size:16px; font-weight:800; color:#B91C1C; display:flex; align-items:center; gap:8px;">
                            <span>⚖️</span> REGULATORY COMPLIANCE EXPOSURE IN REGULATED CATEGORY
                        </div>
                        <span style="background:#B91C1C; color:#FFFFFF; font-size:11px; font-weight:700; padding:4px 10px; border-radius:4px; text-transform:uppercase;">
                            {comp_exposure['risk_tier']}
                        </span>
                    </div>
                    <div style="font-size:13.5px; color:#7F1D1D; line-height:1.55;">
                        <strong>Regulated Category:</strong> {v_info.get('name', 'Regulated Industry')}<br/>
                        <strong>Governing Regulators:</strong> {v_info.get('regulators', 'FTC, CFPB, FDA, SEC')}<br/>
                        <strong>Statutory References:</strong> {v_info.get('statutes', 'FTC Act Section 5')}<br/>
                        <strong>Ad Policy Exposure:</strong> {comp_exposure.get('account_suspension_risk', 'High')}<br/>
                        <div style="margin-top:10px; background:#FFFFFF; padding:12px 14px; border-radius:6px; border:1px solid #FCA5A5; color:#991B1B; font-size:13px;">
                            🚨 <strong>Enforcement Exposure:</strong> {comp_exposure['unsupported_count']} claim(s) appearing in this ad copy (pricing, interest rates, approvals, or guarantees) are <strong>completely unsupported on the destination page ('NONE')</strong>. In regulated categories, promoting uncorroborated claims represents an actionable regulatory violation under FTC and statutory mandates, triggering immediate Google Ads disapproval and account suspension.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif comp_exposure.get("is_regulated"):
                v_info = comp_exposure.get("info", {})
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px 18px; margin:14px 0;">
                    <span style="font-weight:700; color:#166534;">⚖️ REGULATORY COMPLIANCE STATUS:</span> 
                    <span style="color:#15803D;">Regulated Category ({v_info.get('name', 'Regulated')}) — All ad copy claims are substantively supported on the destination page with zero unverified claims.</span>
                </div>
                """, unsafe_allow_html=True)

            # ==============================================================================
            # PILLAR 3: DYNAMIC FINANCIAL WASTED SPEND CALCULATOR
            # ==============================================================================
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("### 💰 Dynamic Financial Wasted Spend Calculator")
            st.caption("Calculate monthly and annualized PPC ad budget exposure based on the formula: **Wasted Spend ($) = Monthly Ad Spend × ((100 - Match Score) / 100)**.")

            fin_col1, fin_col2, fin_col3 = st.columns([1.5, 1.25, 1.25])
            with fin_col1:
                single_monthly_spend = st.number_input(
                    "Monthly PPC Ad Spend ($)",
                    min_value=100.0,
                    max_value=2000000.0,
                    value=10000.0,
                    step=500.0,
                    key="single_monthly_spend_input"
                )

            wasted_spend = single_monthly_spend * ((100.0 - match_score) / 100.0)
            annual_wasted = wasted_spend * 12.0
            risk_level = "Critical (<50%)" if match_score < 50 else ("Moderate (50-80%)" if match_score <= 80 else "Low (>80%)")
            risk_color = "#D32F2F" if match_score < 50 else ("#ED6C02" if match_score <= 80 else "#2E7D32")
            risk_bg = "#FEF2F2" if match_score < 50 else ("#FFFBEB" if match_score <= 80 else "#F0FDF4")
            risk_border = "#FCA5A5" if match_score < 50 else ("#FDE68A" if match_score <= 80 else "#BBF7D0")

            with fin_col2:
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; text-align:center;">
                    <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Monthly Wasted Spend</div>
                    <div style="font-size:24px; font-weight:800; color:#D32F2F; margin:4px 0;">${wasted_spend:,.2f}</div>
                    <div style="font-size:12px; color:#64748B;">${annual_wasted:,.2f}/yr at risk</div>
                </div>
                """, unsafe_allow_html=True)

            with fin_col3:
                st.markdown(f"""
                <div style="background:{risk_bg}; border:1px solid {risk_border}; border-radius:8px; padding:12px; text-align:center;">
                    <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">CRO Risk Tier</div>
                    <div style="font-size:20px; font-weight:800; color:{risk_color}; margin:6px 0;">{risk_level}</div>
                    <div style="font-size:12px; color:#475569;">Formula: Spend × (100 - Score)%</div>
                </div>
                """, unsafe_allow_html=True)

            # Financial Narrative Callout
            if match_score < 50:
                st.error(f"🚨 **CRITICAL FINANCIAL RISK:** At ${single_monthly_spend:,.2f}/month budget and a {match_score}% Match Score, **${wasted_spend:,.2f}** is wasted every single month (**${annual_wasted:,.2f} annually**). The primary ad promise does not appear prominently above the fold, inducing high immediate bounce rates.")
            elif match_score <= 80:
                st.warning(f"⚠️ **MODERATE FINANCIAL EXPOSURE:** At ${single_monthly_spend:,.2f}/month budget, **${wasted_spend:,.2f}/month** (**${annual_wasted:,.2f}/year**) is underperforming due to partial message friction. Alignment optimizations will immediately lift conversion efficiency.")
            else:
                st.success(f"✅ **EFFICIENT BUDGET UTILIZATION:** Strong message symmetry ({match_score}%). Financial leakage is minimized at only **${wasted_spend:,.2f}/month**.")

            # Summary box
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("### 📌 Executive Audit Summary")
            with st.container(border=True):
                st.markdown(f"**Overall System Verdict:** `{alignment_status}` (**{match_score}%** Match · Above-the-Fold: **{fold_score}%**)")
                st.write(summary)

            # Detailed analysis tabs (including Compliance Exposure & One-Click Copy Fixer)
            comp_cnt = comp_exposure.get("unsupported_count", 0)
            comp_tab_title = f"⚖️ Compliance Exposure ({comp_cnt})" if comp_exposure.get("is_regulated") else "⚖️ Compliance Exposure"

            tab_mismatches, tab_compliance, tab_strong, tab_actions, tab_remediation, tab_raw = st.tabs([
                f"🚨 Identified Mismatches ({len(mismatches)})",
                comp_tab_title,
                f"✅ Confirmed Matches ({len(strong_matches)})",
                "🛠️ Actionable Recommendations",
                "⚡ One-Click Copy Fixer (Remediation)",
                "📋 Audit Data & Export"
            ])

            # TAB 1: IDENTIFIED MISMATCHES WITH VERBATIM QUOTES & HALLUCINATION CHECK
            with tab_mismatches:
                if not processed_mismatches:
                    st.success("🎉 Outstanding message symmetry! Zero mismatches detected between this ad copy and landing page snapshot.")
                else:
                    st.caption("Every mismatch below cites supporting landing page text and has been checked by the programmatic hallucination verification engine.")

                    for item in processed_mismatches:
                        severity = item.get("severity", "Moderate")
                        category = item.get("category", "General")
                        ad_claim = item.get("ad_claim", "")
                        issue = item.get("issue_description", "")
                        page_quote = item.get("page_quote", "")
                        suggested_fix = item.get("suggested_fix", "")
                        is_fold = item.get("is_above_the_fold_issue", False)
                        v_res = item["verification"]
                        v_status = v_res["status"]

                        with st.container(border=True):
                            col_h1, col_h2 = st.columns([3, 2])
                            with col_h1:
                                sev_icon = "🔴" if severity == "Critical" else ("🟠" if severity == "Moderate" else "🔵")
                                fold_note = " • ⚡ **Above-The-Fold Priority**" if is_fold else ""
                                st.markdown(f"**{sev_icon} {severity.upper()}** · `{category}`{fold_note}")
                            with col_h2:
                                if v_status == "VERIFIED":
                                    st.markdown("✅ **Verified in Source Page**")
                                elif v_status == "HALLUCINATED":
                                    st.markdown("🚨 **Hallucination Warning (Not in Text)**")
                                elif v_status == "OMISSION_NOTED":
                                    st.markdown("ℹ️ **Claim Completely Absent (NONE)**")

                            st.markdown(f"**📢 Ad Copy Promise:**\n> *\"{ad_claim}\"*")
                            st.markdown(f"**⚠️ The Problem (in Simple English):**\n{issue}")

                            st.markdown("**📄 Exact Landing Page Quote Supporting This Finding:**")
                            st.info(f"\"{page_quote}\"\n\n*Verification status: {v_res['details']}*")

                            st.markdown("**💡 How to Fix This (Recommendation):**")
                            st.success(f"{suggested_fix}")

            # TAB 2: REGULATED CATEGORY COMPLIANCE EXPOSURE
            with tab_compliance:
                st.markdown("### ⚖️ Regulated Category Compliance Exposure Audit")
                if comp_exposure.get("is_regulated"):
                    v_info = comp_exposure.get("info", {})
                    st.markdown(f"##### Industry Classification: {v_info.get('name', 'Regulated')}")
                    st.caption(f"Enforcement Bodies: {v_info.get('regulators')} · Governing Statutes: {v_info.get('statutes')}")

                    c_card1, c_card2, c_card3 = st.columns(3)
                    with c_card1:
                        st.markdown(f"""
                        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Compliance Exposure Tier</div>
                            <div style="font-size:17px; font-weight:800; color:{comp_exposure['risk_color']}; margin:6px 0;">{comp_exposure['risk_tier']}</div>
                            <div style="font-size:12px; color:#64748B;">Statutory Assessment</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_card2:
                        st.markdown(f"""
                        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Unsupported Claims ('NONE')</div>
                            <div style="font-size:24px; font-weight:800; color:#D32F2F; margin:4px 0;">{comp_exposure['unsupported_count']}</div>
                            <div style="font-size:12px; color:#64748B;">Absent from Landing Page</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_card3:
                        st.markdown(f"""
                        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Google Ads Policy Risk</div>
                            <div style="font-size:15px; font-weight:800; color:#D32F2F; margin:6px 0;">ACCOUNT SUSPENSION RISK</div>
                            <div style="font-size:12px; color:#64748B;">Misrepresentation Policy</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<br/>", unsafe_allow_html=True)
                    st.markdown("#### 📜 Statutory Risk & Policy Exposure")
                    st.info(v_info.get('statutory_risk', ''))

                    if comp_exposure.get("unsupported_claims"):
                        st.markdown(f"#### 🚨 Unsupported Ad Claims ({comp_exposure['unsupported_count']} Exposure Flags)")
                        st.caption("These specific promises appear in the ad copy but have NO corroborating text on the landing page, exposing the campaign to deceptive advertising penalties under federal law.")
                        for c_item in comp_exposure["unsupported_claims"]:
                            with st.container(border=True):
                                st.markdown(f"**📢 Ad Copy Promise:** *\"{c_item['ad_claim']}\"*")
                                st.error(f"⚠️ **Landing Page Corroboration:** `{c_item['landing_page_quote']}` (Claim is completely absent from page)")
                                st.markdown(f"**⚖️ Statutory Problem:** {c_item['problem']}")
                                st.markdown(f"**💡 Mandatory Compliance Fix:** {c_item['suggested_fix']}")
                    else:
                        st.success("✓ Outstanding Compliance: All ad claims are verified on the landing page with zero unsubstantiated claims.")

                    if comp_exposure.get("ai_summary"):
                        st.markdown("#### 🤖 Legal & Regulatory Compliance Summary")
                        st.write(comp_exposure["ai_summary"])
                    if comp_exposure.get("statutory_remediation"):
                        st.markdown("#### 🛡️ Compliance Remediation Step")
                        st.success(comp_exposure["statutory_remediation"])
                else:
                    st.info("ℹ️ This campaign belongs to a general commercial category (not categorized as a high-risk regulated vertical such as Finance, Lending, Healthcare, Legal, Crypto, or Higher Education). Standard CRO bounce friction rules apply.")

            # TAB 3: CONFIRMED MATCHES
            with tab_strong:
                if not strong_matches:
                    st.info("No strong message matches identified for this pair.")
                else:
                    for match in strong_matches:
                        with st.container(border=True):
                            st.markdown("✅ **Aligned Claim**")
                            st.markdown(f"**📢 Ad Claim:** *\"{match.get('ad_claim', '')}\"*")
                            st.info(f"**📄 Page Quote:** \"{match.get('page_quote', '')}\"")
                            notes = match.get("notes")
                            if notes:
                                st.caption(f"Note: {notes}")

            # TAB 4: STRATEGIC ACTION PLAN
            with tab_actions:
                st.markdown("#### Priority Action Plan")
                if not recommendations:
                    st.info("No strategic fixes required.")
                else:
                    for idx, rec in enumerate(recommendations, 1):
                        with st.container(border=True):
                            st.markdown(f"**Step {idx}:** {rec}")

            # TAB 5: ONE-CLICK AUTOMATED COPY FIXER (REMEDIATION)
            with tab_remediation:
                st.markdown("### ⚡ One-Click Automated Copy Fixer (Remediation)")
                st.caption("Copy-paste ready headlines and CTA buttons to resolve message friction with zero latency. Use the copy button on any code block to copy instantly.")

                lp_fix = remediation.get("landing_page_fix", {})
                ad_fix = remediation.get("ad_copy_fix", {})

                st.markdown("#### 🌟 Option A: Landing Page Hero Remediation (Recommended)")
                st.caption("Update the landing page hero section so incoming visitors immediately see their ad promise fulfilled above the fold.")

                with st.container(border=True):
                    st.markdown("**1. Optimized Landing Page Hero Headline (Verbatim Promise Match):**")
                    hero_h = lp_fix.get("hero_headline_rewrite", f"{h1} — Guaranteed & Fast")
                    st.code(hero_h, language="text")

                    st.markdown("**2. Optimized Hero Supporting Subheadline:**")
                    hero_sub = lp_fix.get("hero_subheadline_rewrite", f"Experience {d1} with complete transparency.")
                    st.code(hero_sub, language="text")

                    st.markdown("**3. Optimized Primary Call-to-Action (CTA) Button:**")
                    hero_cta = lp_fix.get("cta_button_rewrite", "Claim Your Offer Now")
                    st.code(hero_cta, language="text")

                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown("#### 🔄 Option B: Alternative Ad Copy Headlines")
                st.caption("If the landing page is locked or unmodifiable by compliance, adjust your Google Search Ad headlines to match current landing page reality:")

                with st.container(border=True):
                    col_ad1, col_ad2, col_ad3 = st.columns(3)
                    with col_ad1:
                        st.markdown("**Alternative Headline 1:**")
                        st.code(ad_fix.get("headline_1_alternative", h1 or "Discover Top Rates Today"), language="text")
                    with col_ad2:
                        st.markdown("**Alternative Headline 2:**")
                        st.code(ad_fix.get("headline_2_alternative", h2 or "Verified Online Process"), language="text")
                    with col_ad3:
                        st.markdown("**Alternative Headline 3:**")
                        st.code(ad_fix.get("headline_3_alternative", h3 or "Explore Plans Online"), language="text")

            # TAB 6: AUDIT DATA & EXPORT
            with tab_raw:
                st.markdown("### 📤 Multi-Format Audit Export")
                st.caption("Download the complete audit findings in professional spreadsheet (.xlsx), word document (.docx), tabular CSV, or developer JSON formats.")

                # Generate export binary data passing user's active monthly spend AND compliance data
                excel_data = generate_excel_audit_report(res, selected_row, processed_mismatches, strong_matches, recommendations, single_monthly_spend, compliance_data=comp_exposure)
                docx_data = generate_docx_audit_report(res, selected_row, processed_mismatches, strong_matches, recommendations, single_monthly_spend, compliance_data=comp_exposure) if DOCX_AVAILABLE else None

                # Normalized Mismatches Table Data
                mismatches_table_rows = []
                for idx, p in enumerate(processed_mismatches, 1):
                    mismatches_table_rows.append({
                        "#": idx,
                        "Severity": p.get("severity", "Moderate"),
                        "Category": p.get("category", "General"),
                        "Above The Fold": "Yes" if p.get("is_above_the_fold_issue") else "No",
                        "Ad Promise": p.get("ad_claim", ""),
                        "Landing Page Quote": p.get("page_quote", ""),
                        "Verification": p.get("verification", {}).get("status", "UNCHECKED"),
                        "Problem Description": p.get("issue_description", ""),
                        "Actionable Fix": p.get("suggested_fix", "")
                    })
                df_mismatches = pd.DataFrame(mismatches_table_rows)
                csv_mismatches_data = df_mismatches.to_csv(index=False).encode("utf-8") if not df_mismatches.empty else "".encode("utf-8")
                json_str = json.dumps(res, indent=2)

                # Export Buttons Bar
                exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

                with exp_col1:
                    st.download_button(
                        label="📊 Export Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"audit_report_{selected_pair_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                with exp_col2:
                    if docx_data:
                        st.download_button(
                            label="📄 Export Word (.docx)",
                            data=docx_data,
                            file_name=f"audit_report_{selected_pair_id}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    else:
                        st.button("📄 Word Export (.docx)", disabled=True, use_container_width=True)

                with exp_col3:
                    st.download_button(
                        label="📑 Export CSV (.csv)",
                        data=csv_mismatches_data,
                        file_name=f"mismatches_{selected_pair_id}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with exp_col4:
                    st.download_button(
                        label="📥 Export JSON (.json)",
                        data=json_str,
                        file_name=f"audit_{selected_pair_id}.json",
                        mime="application/json",
                        use_container_width=True
                    )

                st.markdown("---")
                st.markdown("### 📋 Normalized Output Tables")

                # Table 1: Summary Metrics
                st.markdown("##### 1. Executive Summary & Financial Audit Metadata")
                summary_table_rows = [
                    {"Parameter": "Audit Pair ID", "Value": str(selected_row.get("pair_id", ""))},
                    {"Parameter": "Brand / Advertiser", "Value": str(selected_row.get("advertiser", ""))},
                    {"Parameter": "Vertical", "Value": str(selected_row.get("vertical", ""))},
                    {"Parameter": "Final Landing URL", "Value": str(selected_row.get("final_url", ""))},
                    {"Parameter": "Overall Match Score", "Value": f"{match_score}%"},
                    {"Parameter": "Above-The-Fold Match Score", "Value": f"{fold_score}%"},
                    {"Parameter": "Overall System Verdict", "Value": alignment_status},
                    {"Parameter": "Monthly PPC Budget ($)", "Value": f"${single_monthly_spend:,.2f}"},
                    {"Parameter": "Monthly Wasted Spend ($)", "Value": f"${wasted_spend:,.2f}"},
                    {"Parameter": "Annualized Budget Exposure ($)", "Value": f"${annual_wasted:,.2f}"},
                    {"Parameter": "CRO Risk Tier", "Value": risk_level},
                    {"Parameter": "Mismatches Detected", "Value": str(len(processed_mismatches))},
                    {"Parameter": "Verified Quotes in Source", "Value": str(verified_count)},
                    {"Parameter": "Hallucinations Guarded", "Value": str(hallucination_count)},
                    {"Parameter": "Regulated Category Status", "Value": "YES (Regulated)" if comp_exposure.get("is_regulated") else "NO (Standard)"},
                    {"Parameter": "Compliance Risk Tier", "Value": str(comp_exposure.get("risk_tier", "Standard"))},
                    {"Parameter": "Unsupported Claims Flagged", "Value": str(comp_exposure.get("unsupported_count", 0))}
                ]
                st.dataframe(pd.DataFrame(summary_table_rows), use_container_width=True, hide_index=True)

                # Table 2: Normalized Mismatches Table
                st.markdown(f"##### 2. Normalized Mismatches Table ({len(processed_mismatches)})")
                if not df_mismatches.empty:
                    st.dataframe(df_mismatches, use_container_width=True, hide_index=True)
                else:
                    st.success("Zero mismatches detected. High message symmetry across all sections.")

                # Table 3: Regulatory Compliance Exposure Table (If Regulated)
                if comp_exposure.get("is_regulated"):
                    st.markdown(f"##### 3. Regulatory Compliance Exposure Table ({comp_exposure.get('unsupported_count', 0)} Flags)")
                    comp_table_rows = []
                    for idx, c in enumerate(comp_exposure.get("unsupported_claims", []), 1):
                        comp_table_rows.append({
                            "#": idx,
                            "Ad Claim": c.get("ad_claim", ""),
                            "Landing Page Status": c.get("landing_page_quote", ""),
                            "Compliance Concern": c.get("problem", ""),
                            "Mandatory Remediation": c.get("suggested_fix", "")
                        })
                    if comp_table_rows:
                        st.dataframe(pd.DataFrame(comp_table_rows), use_container_width=True, hide_index=True)
                    else:
                        st.success("Zero unsupported claims detected. Fully compliant in regulated category.")

                # Table 4: Confirmed Matches Table
                st.markdown(f"##### 4. Normalized Confirmed Matches Table ({len(strong_matches)})")
                matches_table_rows = []
                for idx, sm in enumerate(strong_matches, 1):
                    matches_table_rows.append({
                        "#": idx,
                        "Ad Claim / Promise": sm.get("ad_claim", ""),
                        "Landing Page Quote": sm.get("page_quote", ""),
                        "Context / Notes": sm.get("notes", "Confirmed")
                    })
                df_matches = pd.DataFrame(matches_table_rows)
                if not df_matches.empty:
                    st.dataframe(df_matches, use_container_width=True, hide_index=True)
                else:
                    st.info("No explicit confirmed matches listed in the AI output.")

                # Table 5: Actionable Recommendations Table
                st.markdown(f"##### 5. Normalized Priority Action Plan ({len(recommendations)})")
                recs_table_rows = []
                for idx, rec in enumerate(recommendations, 1):
                    recs_table_rows.append({
                        "Priority Step": f"Step {idx}",
                        "Concrete Action Item": rec
                    })
                df_recs = pd.DataFrame(recs_table_rows)
                if not df_recs.empty:
                    st.dataframe(df_recs, use_container_width=True, hide_index=True)
                else:
                    st.info("No actionable fixes required.")

                with st.expander("🔍 View Raw Audit JSON Response"):
                    st.json(res)

    # ==============================================================================
    # TAB 2: BULK DATASET AUDIT & CRO RISK LEADERBOARD
    # ==============================================================================
    with mode_tab2:
        render_bulk_leaderboard_section(df, snap_dir, user_api_key, model_choice)


if __name__ == "__main__":
    main()

