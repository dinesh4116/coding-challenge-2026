import base64
import html
import io
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from PIL import Image

try:
    from ddgs import DDGS
except ImportError:  # older package name
    from duckduckgo_search import DDGS

UA = {"User-Agent": "Mozilla/5.0 (MessageMatch hackathon MVP)"}
SKIP_DOMAINS = ("facebook.", "youtube.", "reddit.", "quora.", "wikipedia.",
                "pinterest.", "linkedin.", "twitter.", "x.com", "instagram.")
HEDGES = ("vary", "varies", "depend", "subject to", "eligib", "terms",
          "conditions", "may ", "might", "up to", "verification")

# ---------- search ----------
def tokens(s):
    return set(re.findall(r"[a-z0-9]{3,}", s.lower()))

def search_sites(ad, brand=""):
    q = f"{brand} " + " ".join(ad.split()[:12])
    results = []
    with DDGS() as d:
        for r in d.text(q.strip(), max_results=10):
            results.append(r)
    ad_t = tokens(ad)
    out = []
    for r in results:
        url = r.get("href") or r.get("url", "")
        if not url or any(x in url for x in SKIP_DOMAINS):
            continue
        blob = f"{r.get('title','')} {r.get('body','')}"
        score = len(ad_t & tokens(blob))
        if brand and brand.lower().replace(" ", "") in urlparse(url).netloc.lower():
            score += 10
        out.append({"url": url, "title": r.get("title", ""),
                    "snippet": r.get("body", ""), "score": score})
    return sorted(out, key=lambda x: -x["score"])[:6]

# ---------- fetch ----------
def fetch_page(url):
    """Return page text plus image URLs (og:image first)."""
    resp = requests.get(url, headers=UA, timeout=12)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    images = []
    og = soup.find("meta", attrs={"property": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
    if og and og.get("content"):
        images.append(urljoin(url, og["content"]))
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:") or src.lower().endswith(".svg"):
            continue
        if any(w in src.lower() for w in ("logo", "icon", "sprite", "pixel", "tracking")):
            continue
        images.append(urljoin(url, src))
    images = list(dict.fromkeys(images))[:8]
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    desc = meta.get("content", "") if meta else ""
    body = soup.get_text(" ", strip=True)
    return {"text": f"{title}. {desc}. {body}", "images": images}

def fetch_text(url):
    return fetch_page(url)["text"]

# ---------- photos ----------
def download_image(url, timeout=6):
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None

def thumb_uri(img, size=(160, 160)):
    """Small base64 data-URI, usable in st.dataframe ImageColumn."""
    im = img.copy()
    im.thumbnail(size)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def dhash(img, n=8):
    g = img.convert("L").resize((n + 1, n))
    px = list(g.getdata())
    bits = []
    for row in range(n):
        for col in range(n):
            bits.append(px[row * (n + 1) + col] > px[row * (n + 1) + col + 1])
    return bits

def visual_similarity(a, b):
    ha, hb = dhash(a), dhash(b)
    return round(100 * sum(x == y for x, y in zip(ha, hb)) / len(ha))

@st.cache_data(show_spinner=False, ttl=3600)
def preview_image_url(url):
    try:
        imgs = fetch_page(url)["images"]
        return imgs[0] if imgs else ""
    except Exception:
        return ""

def ocr_image(img):
    """Optional: needs `pip install pytesseract` + the Tesseract program."""
    try:
        import pytesseract
        return pytesseract.image_to_string(img).strip()
    except Exception as e:
        return f"__ERR__{e}"

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]

def best_sentence(claim, sents):
    ct = tokens(claim)
    best, score = "", 0
    for s in sents:
        sc = len(ct & tokens(s))
        if sc > score:
            best, score = s, sc
    return best[:300]

# ---------- claim rules ----------
CLAIM_RULES = {
    "Speed": r"(?:in|within)\s+(?:one|1|\d+)\s+(?:day|hour|minute)s?|same[- ]day|24[- ]?hours?|instant(?:ly)?|overnight",
    "Fees": r"no (?:hidden )?fees?|zero (?:fees|processing fees?)|fee[- ]free|no charges?",
    "Price/discount": r"\d+\s?% off|save \d+\s?%|[$₹]\s?\d[\d,.]*|rs\.?\s?\d[\d,.]*",
    "Free": r"\bfree\b(?: \w+){0,2}",
    "Guarantee": r"guarantee[d]?|risk[- ]free|100% (?:safe|secure)",
    "Rate": r"\d+(?:\.\d+)?\s?% (?:apr|interest|rate)|lowest (?:rate|price)|best (?:rate|price)",
}

def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()

def check_claims(ad, page):
    rows, sents, page_n = [], sentences(page), norm(page)
    for kind, pat in CLAIM_RULES.items():
        for m in re.finditer(pat, ad, re.I):
            claim = m.group(0).strip()
            ev = best_sentence(claim, sents)
            if norm(claim) in page_n:
                status = "Supported"
            elif ev and any(h in ev.lower() for h in HEDGES):
                status = "Not explicitly supported"
            else:
                status = "Not found on page"
            rows.append({"Type": kind, "Claim": claim, "Status": status,
                         "Evidence": ev or "No related sentence found on the page."})
    return rows

# ---------- offer deadlines ----------
MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_P = (rf"(?:{MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?"
          rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}\.?(?:,?\s+\d{{4}})?"
          rf"|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})")
CUE_P = r"(?:offer\s+)?(?:ends?|ending|expires?|valid\s+(?:till|until|through|thru)|until|till|through|last day)(?:\s+on)?"
DEADLINE_RE = re.compile(rf"({CUE_P})\s+({DATE_P})", re.I)
RELATIVE_RE = re.compile(
    r"(?:ends?|expires?|valid)\s+(?:today|tonight|tomorrow|this\s+\w+|in\s+\d+\s+(?:hours?|days?))"
    r"|limited[- ]time|last chance|while (?:stocks?|supplies) last|hurry", re.I)

def parse_date(txt):
    txt = re.sub(r"(\d)(st|nd|rd|th)", r"\1", txt, flags=re.I)
    try:
        d = dparser.parse(txt, dayfirst=True,
                          default=datetime(date.today().year, 1, 1)).date()
        return d
    except (ValueError, OverflowError):
        return None

def check_deadlines(ad, page):
    rows, today = [], date.today()
    page_cue = {parse_date(m.group(2)) for m in DEADLINE_RE.finditer(page)} - {None}
    page_any = {parse_date(m.group(0)) for m in re.finditer(DATE_P, page, re.I)} - {None}
    for m in DEADLINE_RE.finditer(ad):
        d = parse_date(m.group(2))
        if not d:
            continue
        claim = m.group(0)
        if d in page_cue or d in page_any:
            status, ev = "Supported", f"Landing page also shows {d:%d %b %Y}."
        elif page_cue:
            status = "Date mismatch"
            ev = "Landing page deadline(s): " + ", ".join(f"{x:%d %b %Y}" for x in sorted(page_cue))
        else:
            status, ev = "Not found on page", "No offer end date found on the landing page."
        if d < today:
            ev += f" WARNING: {d:%d %b %Y} has already passed - the offer may be expired."
            status = "Expired" if status != "Supported" else "Supported (but past date)"
        rows.append({"Type": "Offer deadline", "Claim": claim, "Status": status, "Evidence": ev})
    for m in RELATIVE_RE.finditer(ad):
        claim = m.group(0)
        found = re.search(r"ends?|expires?|limited|offer", page, re.I)
        rows.append({"Type": "Urgency", "Claim": claim,
                     "Status": "Needs review",
                     "Evidence": ("Page mentions an offer/expiry, check it manually."
                                  if found else "Relative deadline cannot be verified; page shows no matching urgency.")})
    return rows

def score(rows):
    if not rows:
        return 100
    pts = sum(1 if r["Status"].startswith("Supported") else
              0.5 if r["Status"] in ("Not explicitly supported", "Needs review") else 0 for r in rows)
    return round(100 * pts / len(rows))

# ---------- UI ----------
st.set_page_config(page_title="MessageMatch", page_icon="🎯", layout="wide")

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.mm-hero {background: linear-gradient(120deg,#4f46e5 0%,#7c3aed 55%,#db2777 100%);
  border-radius: 18px; padding: 26px 30px; color: #fff; margin-bottom: 18px;}
.mm-hero h1 {margin: 0; font-size: 2rem; color:#fff;}
.mm-hero p {margin: 4px 0 0; opacity: .9;}
.mm-step {display:flex; align-items:center; gap:10px; margin: 18px 0 6px;}
.mm-step span {background:#4f46e5; color:#fff; border-radius:50%; width:28px; height:28px;
  display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:.9rem;}
.mm-step b {font-size:1.15rem;}
.mm-card {border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:14px 16px;
  margin-bottom:10px; background: rgba(128,128,128,.06);}
.mm-card.ok {border-left:6px solid #16a34a;}
.mm-card.warn {border-left:6px solid #f59e0b;}
.mm-card.bad {border-left:6px solid #dc2626;}
.mm-pill {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem;
  font-weight:600; margin-right:6px;}
.mm-pill.type {background:rgba(79,70,229,.15); color:#6366f1;}
.mm-pill.ok {background:rgba(22,163,74,.18); color:#16a34a;}
.mm-pill.warn {background:rgba(245,158,11,.2); color:#d97706;}
.mm-pill.bad {background:rgba(220,38,38,.18); color:#dc2626;}
.mm-claim {font-size:1.02rem; font-weight:600; margin:8px 0 4px;}
.mm-ev {font-size:.88rem; opacity:.8;}
.mm-score {text-align:center; padding:10px 0;}
.mm-ring {width:130px; height:130px; border-radius:50%; margin:0 auto;
  display:flex; align-items:center; justify-content:center;}
.mm-ring div {width:98px; height:98px; border-radius:50%; background:var(--background-color, #fff);
  display:flex; flex-direction:column; align-items:center; justify-content:center;}
.mm-ring b {font-size:1.9rem; line-height:1;}
.mm-ring small {opacity:.7;}
.mm-photo-label {font-size:.8rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em; opacity:.7;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    "<div class='mm-hero'><h1>🎯 MessageMatch</h1>"
    "<p>Check that what your ad promises is what the landing page delivers - copy, deadlines and photos.</p></div>",
    unsafe_allow_html=True)

def step(n, title):
    st.markdown(f"<div class='mm-step'><span>{n}</span><b>{title}</b></div>", unsafe_allow_html=True)

def status_class(s):
    if s.startswith("Supported"):
        return "ok"
    if s in ("Date mismatch", "Expired", "Not found on page"):
        return "bad"
    return "warn"

def fill_from_ocr(text):
    st.session_state["ad_text"] = text

st.session_state.setdefault("ad_text", "Get your loan approved in one day. No hidden fees! Offer ends Dec 31, 2026.")
st.session_state.setdefault("history", [])

# ---------- step 1: the ad (copy + photo column) ----------
step(1, "Your ad")
col_copy, col_photo = st.columns([3, 2], gap="large")

with col_photo:
    st.markdown("<div class='mm-photo-label'>Ad photo / creative</div>", unsafe_allow_html=True)
    up = st.file_uploader("Upload the ad image", type=["png", "jpg", "jpeg", "webp"],
                          label_visibility="collapsed")
    ad_img = None
    if up:
        ad_img = Image.open(up).convert("RGB")
        st.image(ad_img, use_container_width=True)
        if st.button("📝 Read text from image (OCR)"):
            txt = ocr_image(ad_img)
            if txt.startswith("__ERR__"):
                st.warning("OCR is not set up. Run `pip install pytesseract` and install the "
                           "Tesseract program, or just type the ad copy.")
            elif txt:
                fill_from_ocr(txt)
                st.rerun()
            else:
                st.info("No text found in the image.")
    else:
        st.caption("Optional. Add a screenshot of the ad so it is saved with the report.")

with col_copy:
    ad = st.text_area("Advertisement copy", key="ad_text", height=170)
    brand = st.text_input("Brand name (optional, improves the search)")

# ---------- step 2: the landing page ----------
step(2, "Find the landing page")
c_find, c_url = st.columns([1, 2], gap="large")
with c_find:
    if st.button("🔎 Find original website", use_container_width=True):
        with st.spinner("Searching the web..."):
            try:
                st.session_state["cands"] = search_sites(ad, brand)
                st.session_state.pop("picked", None)
            except Exception as e:
                st.session_state["cands"] = []
                st.error(f"Search failed: {e}")
with c_url:
    manual_url = st.text_input("...or enter the website URL yourself", placeholder="https://example.com/offer")

cands = st.session_state.get("cands", [])
if cands:
    st.caption("A search result is not proof of the real advertiser. Please confirm.")
    with ThreadPoolExecutor(max_workers=6) as ex:
        thumbs = list(ex.map(lambda c: preview_image_url(c["url"]), cands))
    for i, (c, th) in enumerate(zip(cands, thumbs)):
        picked = st.session_state.get("picked") == c["url"]
        with st.container(border=True):
            ci, ct, cb = st.columns([1, 5, 1.4], vertical_alignment="center")
            with ci:
                if th:
                    st.image(th, width=90)
                else:
                    st.markdown("<div style='font-size:2rem;text-align:center'>🌐</div>", unsafe_allow_html=True)
            with ct:
                st.markdown(f"**{c['title'][:80] or c['url']}**")
                st.caption(c["url"])
                st.write(c["snippet"][:180])
            with cb:
                if st.button("✔ Selected" if picked else "Use this", key=f"pick{i}",
                             type="primary" if picked else "secondary", use_container_width=True):
                    st.session_state["picked"] = c["url"]
                    st.rerun()

url = manual_url.strip() or st.session_state.get("picked")
if url:
    st.success(f"Landing page: {url}")

with st.expander("Site blocks reading? Paste the landing-page text instead"):
    manual_text = st.text_area("Landing-page text", key="manual", height=140)

# ---------- step 3: audit ----------
step(3, "Audit")
if st.button("✅ Audit message match", type="primary"):
    page, page_images = manual_text.strip(), []
    if url and not page:
        with st.spinner(f"Reading {url} ..."):
            try:
                data = fetch_page(url)
                page, page_images = data["text"], data["images"]
            except Exception as e:
                st.error(f"Could not read the page ({e}). Paste the text in the box above.")
    elif url:
        try:
            page_images = fetch_page(url)["images"]
        except Exception:
            pass
    if not page:
        if not url:
            st.warning("Search for a website, enter a URL, or paste landing-page text first.")
    else:
        rows = check_claims(ad, page) + check_deadlines(ad, page)
        sc = score(rows)
        # photos: download landing images and compare with the ad photo
        page_pics = []
        if page_images:
            with st.spinner("Loading landing-page photos..."):
                with ThreadPoolExecutor(max_workers=6) as ex:
                    imgs = list(ex.map(download_image, page_images))
            page_pics = [(u, im) for u, im in zip(page_images, imgs) if im is not None]
        best_sim = None
        if ad_img is not None and page_pics:
            best_sim = max(visual_similarity(ad_img, im) for _, im in page_pics)
        st.session_state["result"] = {
            "rows": rows, "score": sc, "url": url or "(pasted text)", "brand": brand,
            "ad": ad, "ad_img": ad_img, "page_pics": page_pics, "best_sim": best_sim}
        st.session_state["history"].insert(0, {
            "Photo": thumb_uri(ad_img) if ad_img is not None else None,
            "Brand": brand or "-",
            "Ad copy": (ad[:70] + "...") if len(ad) > 70 else ad,
            "Landing page": url or "(pasted text)",
            "Score": sc,
            "Claims": len(rows),
            "Need review": sum(not r["Status"].startswith("Supported") for r in rows),
            "Checked": datetime.now().strftime("%d %b %H:%M"),
        })

res = st.session_state.get("result")
if res:
    rows, sc = res["rows"], res["score"]
    color = "#16a34a" if sc >= 80 else "#f59e0b" if sc >= 50 else "#dc2626"
    label = "Good match" if sc >= 80 else "Needs work" if sc >= 50 else "Poor match"
    left, right = st.columns([2, 3], gap="large")

    with left:  # photo column + score
        st.markdown(
            f"<div class='mm-score'><div class='mm-ring' style='background:conic-gradient({color} {sc*3.6}deg, rgba(128,128,128,.25) 0)'>"
            f"<div><b>{sc}</b><small>/ 100</small></div></div>"
            f"<p style='margin-top:8px;font-weight:600;color:{color}'>{label}</p></div>",
            unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m1.metric("Claims checked", len(rows))
        m2.metric("Need review", sum(not r["Status"].startswith("Supported") for r in rows))

        st.markdown("<div class='mm-photo-label'>Ad photo</div>", unsafe_allow_html=True)
        if res["ad_img"] is not None:
            st.image(res["ad_img"], use_container_width=True)
        else:
            st.caption("No ad photo uploaded.")
        st.markdown("<div class='mm-photo-label' style='margin-top:12px'>Landing-page photos</div>",
                    unsafe_allow_html=True)
        if res["page_pics"]:
            st.image([im for _, im in res["page_pics"][:4]], width=140)
            if res["best_sim"] is not None:
                st.caption(f"Rough visual similarity to the ad photo: **{res['best_sim']}%** "
                           "(simple image fingerprint - treat as a hint, not proof).")
        else:
            st.caption("No photos could be read from the landing page.")

    with right:
        if not rows:
            st.info("No checkable claims found in the ad.")
        tabs = st.tabs(["All", "Needs review", "Supported"])
        groups = [rows,
                  [r for r in rows if not r["Status"].startswith("Supported")],
                  [r for r in rows if r["Status"].startswith("Supported")]]
        for tab, grp in zip(tabs, groups):
            with tab:
                if not grp:
                    st.caption("Nothing here.")
                for r in grp:
                    k = status_class(r["Status"])
                    st.markdown(
                        f"<div class='mm-card {k}'>"
                        f"<span class='mm-pill type'>{html.escape(r['Type'])}</span>"
                        f"<span class='mm-pill {k}'>{html.escape(r['Status'])}</span>"
                        f"<div class='mm-claim'>“{html.escape(r['Claim'])}”</div>"
                        f"<div class='mm-ev'>Evidence: {html.escape(r['Evidence'])}</div></div>",
                        unsafe_allow_html=True)
        if rows:
            df = pd.DataFrame(rows)
            df.insert(0, "Ad photo", res["ad_img"] is not None and "uploaded" or "none")
            df["Landing page"] = res["url"]
            st.download_button("⬇ Download audit report (CSV)", df.to_csv(index=False),
                               "messagematch_report.csv", "text/csv")
        st.caption("Rule-based screening only. Verify flagged items by hand.")

# ---------- history with photo column ----------
if st.session_state["history"]:
    st.markdown("---")
    st.subheader("Audit history")
    hist = pd.DataFrame(st.session_state["history"])
    st.dataframe(
        hist, hide_index=True, use_container_width=True,
        row_height=70,
        column_config={
            "Photo": st.column_config.ImageColumn("Ad photo", width="small"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
        })
    st.download_button("⬇ Download history (CSV)", hist.drop(columns=["Photo"]).to_csv(index=False),
                       "messagematch_history.csv", "text/csv")
