import re
from html import escape

import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Ad Message Match Auditor",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Ad-to-Landing-Page Message Match Auditor")
st.caption(
    "A prototype that checks ad claims against supplied landing-page text or an HTML snapshot. "
    "It does not provide legal advice or independently verify the truth of claims."
)

st.info(
    "For reliable results, upload a saved HTML snapshot or paste the page text. "
    "The URL field is recorded for reference only; this prototype does not fetch live URLs."
)

# ---------- Helpers ----------

def extract_page_sections(html: str):
    """Extract visible text by approximate page section, preserving source quotes."""
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript", "svg", "template"]):
        element.decompose()

    sections = []
    body = soup.body or soup

    # If semantic containers exist, use them. Otherwise use headings/paragraphs/buttons.
    containers = body.find_all(
        ["header", "main", "section", "article", "footer", "nav"],
        recursive=True,
    )

    if containers:
        # Keep outer semantic containers only to avoid duplicate nested text.
        selected = []
        for container in containers:
            if not any(parent in selected for parent in container.parents):
                selected.append(container)

        for container in selected:
            tag = container.name.lower()
            if tag == "header":
                label = "Hero / Header"
            elif tag == "main":
                label = "Main content"
            elif tag == "footer":
                label = "Footer / Terms"
            elif tag == "nav":
                label = "Navigation"
            else:
                label = tag.capitalize()

            text = container.get_text(" ", strip=True)
            if text:
                sections.append({"label": label, "text": text})
    else:
        text = body.get_text(" ", strip=True)
        if text:
            sections.append({"label": "Page text", "text": text})

    # Fall back if semantic containers were empty.
    if not sections:
        text = body.get_text(" ", strip=True)
        if text:
            sections.append({"label": "Page text", "text": text})

    return sections


def split_sentences(text: str):
    """Split text into readable sentence-like evidence snippets."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def normalize(text: str):
    return re.sub(r"\s+", " ", text).strip().lower()


def exact_quote_exists(quote: str, full_text: str):
    """Case-insensitive verification that quote is actually in extracted text."""
    return normalize(quote) in normalize(full_text)


def check_phrase_match(phrases, text):
    normalized_text = normalize(text)
    return any(normalize(phrase) in normalized_text for phrase in phrases)


def get_relevant_keywords(check_name):
    if check_name == "Same-day approval":
        return ["approval", "approved", "eligibility", "lender", "disbursement", "today"]
    if check_name == "No paperwork":
        return ["paperwork", "documents", "documentation", "application"]
    if check_name == "Online application":
        return ["apply", "online", "application", "website"]
    if check_name == "Guaranteed outcome":
        return ["guarantee", "guaranteed", "terms", "conditions", "eligibility"]
    return []


# ---------- Input UI ----------

left, right = st.columns(2)

with left:
    st.header("1. Advertisement details")
    headline = st.text_input(
        "Ad headline",
        placeholder="Get Your Loan Approved Today!",
    )
    description = st.text_area(
        "Ad description",
        placeholder="Fast approval with minimal paperwork. Apply online today.",
        height=130,
    )
    cta = st.text_input("Ad call-to-action (CTA)", placeholder="Apply Now")
    extra_claims = st.text_area(
        "Additional claims to check (optional)",
        placeholder="Example: No hidden fees\nGuaranteed approval",
        help="Enter one claim per line. These are checked using simple phrase matching.",
        height=90,
    )

with right:
    st.header("2. Landing-page details")
    page_url = st.text_input(
        "Landing-page URL (optional)",
        placeholder="https://example.com/personal-loan",
        help="Saved for reference only. Live URL fetching is not implemented in this prototype.",
    )
    uploaded_file = st.file_uploader(
        "Upload an offline HTML snapshot",
        type=["html", "htm"],
    )
    pasted_text = st.text_area(
        "Or paste landing-page text",
        placeholder="Paste the actual visible landing-page text here...",
        height=250,
    )

# Extract uploaded snapshot if provided. The uploaded file takes priority over pasted text.
sections = []
source_name = "Pasted text"
if uploaded_file is not None:
    html_bytes = uploaded_file.getvalue()
    html = html_bytes.decode("utf-8", errors="replace")
    sections = extract_page_sections(html)
    source_name = f"HTML snapshot: {uploaded_file.name}"
    st.success(f"Loaded {uploaded_file.name}")
elif pasted_text.strip():
    sections = [{"label": "Pasted page text", "text": pasted_text.strip()}]

page_text = "\n".join(section["text"] for section in sections)
if sections:
    with st.expander("Preview extracted landing-page content"):
        st.caption(f"Source: {source_name}")
        for section in sections:
            st.markdown(f"**{section['label']}**")
            st.write(section["text"][:5000])

st.divider()

# ---------- Analysis ----------

if st.button("Analyze message match", type="primary", use_container_width=True):
    if not headline.strip():
        st.error("Please enter an advertisement headline.")
    elif not page_text.strip():
        st.error("Please upload an HTML snapshot or paste landing-page text.")
    else:
        ad_text = f"{headline} {description}".strip()
        ad_words = set(re.findall(r"\b[\w'-]+\b", ad_text.lower()))
        page_words = set(re.findall(r"\b[\w'-]+\b", page_text.lower()))
        meaningful_words = {
            word for word in ad_words
            if word not in {"a", "an", "and", "or", "the", "to", "of", "in", "on", "with", "your", "you", "for"}
        }
        matched_words = meaningful_words.intersection(page_words)
        score = round(len(matched_words) / len(meaningful_words) * 100) if meaningful_words else 0

        st.header("3. Preliminary results")
        st.metric("Word-overlap score", f"{score}/100")
        st.caption(
            "This is a simple word-overlap indicator, not a measure of truth, relevance, or compliance."
        )
        st.write("**Matching words:**")
        st.write(", ".join(sorted(matched_words)) if matched_words else "No meaningful matching words found.")

        st.header("4. Promise-level checks")
        st.caption(
            "Phrase-based checks can miss paraphrases. 'Not substantiated' means the checked wording was not found; it does not prove the claim is false."
        )

        checks = [
            {
                "name": "Same-day approval",
                "triggers": ["approved today", "approval today", "same-day approval", "approved in one day"],
                "support": ["approved today", "approval today", "same-day approval", "approved in one day"],
            },
            {
                "name": "No paperwork",
                "triggers": ["no paperwork", "zero paperwork", "without paperwork", "paperwork-free"],
                "support": ["no paperwork", "zero paperwork", "without paperwork", "paperwork-free"],
            },
            {
                "name": "Online application",
                "triggers": ["apply online", "online application", "apply on our website"],
                "support": ["apply online", "online application", "apply on our website"],
            },
            {
                "name": "Guaranteed outcome",
                "triggers": ["guaranteed approval", "guaranteed acceptance", "guaranteed results"],
                "support": ["guaranteed approval", "guaranteed acceptance", "guaranteed results"],
            },
        ]

        custom_claims = [line.strip() for line in extra_claims.splitlines() if line.strip()]
        for claim in custom_claims:
            checks.append({
                "name": f"Custom claim: {claim}",
                "triggers": [claim],
                "support": [claim],
            })

        for check in checks:
            if not check_phrase_match(check["triggers"], ad_text):
                continue

            with st.container(border=True):
                st.subheader(check["name"])
                found_support_phrase = check_phrase_match(check["support"], page_text)

                if found_support_phrase:
                    st.success("Related wording found on the landing page.")
                    st.write(
                        "This confirms only that related wording appears; it does not establish that the full claim is adequately supported."
                    )
                else:
                    st.warning("Not substantiated by the specific phrases checked.")
                    st.write(
                        "Suggested fix: Review the ad claim and ensure any promise is accurate, clear, and supported by the page."
                    )

                keywords = get_relevant_keywords(check["name"])
                if check["name"].startswith("Custom claim:"):
                    keywords = re.findall(r"\b[\w'-]+\b", check["name"].split(":", 1)[1].lower())

                candidate_quotes = []
                for section in sections:
                    for sentence in split_sentences(section["text"]):
                        sentence_lower = sentence.lower()
                        if any(keyword in sentence_lower for keyword in keywords):
                            candidate_quotes.append((section["label"], sentence))

                # Deduplicate by normalized quotation while preserving order.
                seen = set()
                unique_quotes = []
                for label, quote in candidate_quotes:
                    key = normalize(quote)
                    if key not in seen and exact_quote_exists(quote, page_text):
                        seen.add(key)
                        unique_quotes.append((label, quote))

                if unique_quotes:
                    st.write("**Relevant evidence quotations from the supplied page:**")
                    for label, quote in unique_quotes[:3]:
                        st.markdown(f"> “{quote}”")
                        st.caption(f"Section: {label} · Verified against extracted page text")
                else:
                    st.info(
                        "No relevant sentence was found for this check. The auditor will not invent a quotation."
                    )

        st.header("5. Call-to-action check")
        if cta.strip():
            if normalize(cta) in normalize(page_text):
                st.success(f'CTA "{cta}" appears in the supplied landing-page text.')
            else:
                st.warning(f'CTA "{cta}" was not found in the supplied landing-page text.')
                st.write("Suggested fix: Check whether the ad CTA and landing-page action are consistent.")
        else:
            st.info("Enter a CTA to check consistency.")

        st.header("6. Notes and limitations")
        st.write(
            "- Evidence quotations are checked against the text extracted from the supplied snapshot or pasted text.\n"
            "- Section labels are approximate and depend on the HTML structure.\n"
            "- The current prototype uses rules and phrase matching, not a semantic AI model.\n"
            "- It does not fetch live URLs, render JavaScript-heavy pages, or provide legal/compliance advice."
        )
