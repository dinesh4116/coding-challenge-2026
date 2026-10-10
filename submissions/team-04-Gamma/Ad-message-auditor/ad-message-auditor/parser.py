"""HTML -> ordered, section-labelled text blocks (position-aware extraction).

Design notes
------------
* Every visible text is emitted exactly ONCE. A container whose children contain
  block-level elements is never emitted as a whole; its children are walked instead,
  and only its own "loose" text nodes are emitted separately.
* Section labels come from HTML landmarks, id/class tokens and section headings only.
  When nothing reliable is found the block is labelled ``unknown`` (never guessed).
* HTML alone cannot prove that something is "above the fold". ``above_the_fold`` stays
  ``None`` unless layout metadata (e.g. from a rendered screenshot run) is supplied.
"""
import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from schemas import ParsedPage, TextBlock

logger = logging.getLogger(__name__)

REMOVE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "canvas",
               "object", "embed", "link", "meta", "head"]
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
BLOCK_TAGS = set(HEADINGS) | {
    "p", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th", "div", "section",
    "article", "aside", "header", "footer", "nav", "main", "form", "blockquote", "details",
    "figure", "dl", "dt", "dd", "fieldset", "pre"}
STRUCT_TEXT = set(HEADINGS) | {"p", "li", "td", "th", "dd", "dt", "summary", "blockquote",
                               "figcaption", "label", "legend", "caption", "pre"}
KIND_BY_TAG = {"p": "paragraph", "li": "list_item", "button": "button", "a": "link",
               "td": "table_cell", "th": "table_cell"}
SECTIONING = {"article", "section", "main", "aside", "nav"}

_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201c": '"',
                         "\u201d": '"', "\u201e": '"', "\u2013": "-", "\u2014": "-",
                         "\u2212": "-"})


def collapse_ws(text: str) -> str:
    """Collapse whitespace only. Characters themselves are left untouched."""
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_text(text: str) -> str:
    """Consistent matching form: NFKC, curly quotes/dashes straightened, case-folded."""
    t = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    return re.sub(r"\s+", " ", t).strip().casefold()


# ------------------------------------------------------------ section classification
SECTION_KEYWORDS = [
    ("faq", {"faq", "faqs", "accordion", "questions"}),
    ("pricing", {"pricing", "price", "prices", "plans", "plan", "rates", "fees"}),
    ("hero", {"hero", "banner", "jumbotron", "masthead", "splash"}),
    ("features", {"features", "feature", "benefits", "benefit", "services", "service",
                  "advantages", "how", "why"}),
]
HEADING_PATTERNS = [
    ("faq", re.compile(r"\bfaqs?\b|frequently asked|common questions", re.I)),
    ("pricing", re.compile(r"\bpricing\b|\bplans?\b|\bprices?\b|\brates?\b|\bfees?\b", re.I)),
    ("features", re.compile(r"\bfeatures?\b|\bbenefits?\b|why choose|how it works|what you get", re.I)),
]
_HEADING_TAG_RE = re.compile(r"^h[1-6]$")


def _tokens(el: Tag) -> set:
    parts = []
    for key in ("id", "class", "aria-label", "data-section", "role"):
        v = el.get(key)
        if isinstance(v, list):
            v = " ".join(v)
        if v:
            parts.append(str(v).lower())
    return {t for t in re.split(r"[^a-z0-9]+", " ".join(parts)) if t}


def classify_section(el: Tag) -> Tuple[str, str, str, List[str]]:
    """Return (section, confidence, reason, extra_labels) for the element holding a text."""
    chain = [a for a in [el, *el.parents]
             if isinstance(a, Tag) and a.name not in ("[document]", "html", "body")]
    # 1) Page footer (a <footer> inside <article>/<section> is NOT the page footer)
    for i, a in enumerate(chain):
        toks = _tokens(a)
        page_footer = a.name == "footer" and not any(p.name in SECTIONING for p in chain[i + 1:])
        if page_footer or a.get("role") == "contentinfo" or "footer" in toks:
            return "footer", "high", f"inside <{a.name}> page footer", []
    # 2) Navigation
    for a in chain:
        if a.name == "nav" or a.get("role") == "navigation":
            return "unknown", "low", "navigation element", ["navigation"]
    # 3) Nearest labelled ancestor wins
    main_el: Optional[Tag] = None
    sectioning: Optional[Tag] = None
    for i, a in enumerate(chain):
        toks = _tokens(a)
        if toks & {"cookie", "consent", "gdpr"}:
            return "unknown", "low", "cookie/consent banner", []
        for sec, kws in SECTION_KEYWORDS:
            if toks & kws:
                return sec, "high", f"<{a.name}> id/class/aria-label suggests '{sec}'", []
        if a.name in ("section", "article", "aside", "div") and \
                not a.find(["section", "article", "main", "footer", "header", "nav"]):
            h = a.find(_HEADING_TAG_RE)
            if h is not None:
                for sec, rx in HEADING_PATTERNS:
                    if rx.search(h.get_text(" ")):
                        return sec, "medium", f"section heading '{collapse_ws(h.get_text())[:40]}'", []
        if a.name == "header" and not any(p.name in ("article", "section", "aside", "main")
                                          for p in chain[i + 1:]):
            if a.find("h1"):
                return "hero", "medium", "site <header> containing an H1", []
            return "unknown", "low", "site header without an H1", []
        if a.name == "main" or a.get("role") == "main":
            main_el = a
            break
        if a.name in ("section", "article") and sectioning is None:
            sectioning = a
    if main_el is not None:
        return "main", "high", "inside <main>", []
    if sectioning is not None:
        return "main", "medium", f"inside <{sectioning.name}> without a recognised label", []
    return "unknown", "low", "no landmark, label or heading identified this section", []


# ------------------------------------------------------------------- text labelling
PRICE_RE = re.compile(r"[$€£₹]\s?\d|\d\s?%|\bper (?:month|year|week|day)\b|/\s?(?:mo|month|yr|year)\b|\bAPR\b", re.I)
DISCLAIMER_RE = re.compile(r"^\s*[*†‡]|terms (?:and conditions )?apply|subject to|conditions apply|"
                           r"see (?:full )?terms|not available in all|representative apr", re.I)


def _is_disclaimer(el: Tag, text: str) -> bool:
    if DISCLAIMER_RE.search(text) or el.name == "small":
        return True
    for a in [el, *list(el.parents)[:4]]:
        if isinstance(a, Tag) and _tokens(a) & {"disclaimer", "legal", "terms", "finprint", "fineprint"}:
            return True
    return False


def _path(el: Tag) -> str:
    parts = []
    for a in [el, *el.parents]:
        if not isinstance(a, Tag) or a.name in ("[document]", "html"):
            continue
        idx = 1
        for sib in a.previous_siblings:
            if isinstance(sib, Tag) and sib.name == a.name:
                idx += 1
        ident = f"#{a['id']}" if a.get("id") else ""
        parts.append(f"{a.name}{ident}" + (f"[{idx}]" if not ident else ""))
    return ">".join(reversed(parts))


def _is_hidden(el: Tag) -> bool:
    if el.attrs is None:
        return False
    style = (el.get("style") or "").replace(" ", "").lower()
    return (el.has_attr("hidden") or el.get("aria-hidden") == "true"
            or "display:none" in style or "visibility:hidden" in style)


def _has_block_desc(el: Tag) -> bool:
    return any(d.name in BLOCK_TAGS for d in el.find_all(True))


def _has_cta_desc(el: Tag) -> bool:
    return any(d.name in ("a", "button") for d in el.find_all(True))


class _Extractor:
    def __init__(self, layout: Optional[dict]):
        self.blocks: List[TextBlock] = []
        self.loose_counter: Dict[str, int] = {}
        self.layout = layout or {}

    def emit(self, el: Tag, text: str, loose: bool = False) -> None:
        clean = collapse_ws(text)
        if not clean:
            return
        section, conf, reason, labels = classify_section(el)
        path = _path(el)
        if loose:
            n = self.loose_counter.get(path, 0) + 1
            self.loose_counter[path] = n
            path = f"{path}/#text[{n}]"
        if PRICE_RE.search(clean):
            labels.append("pricing")
        if _is_disclaimer(el, clean):
            labels.append("disclaimer")
        tag = el.name
        atf = None
        elements = self.layout.get("elements") or {}
        if path in elements and self.layout.get("viewport_height"):
            atf = float(elements[path].get("top", 1e9)) < float(self.layout["viewport_height"])
        order = len(self.blocks) + 1
        self.blocks.append(TextBlock(
            block_id=f"block_{order:03d}", section=section, section_confidence=conf,
            section_reason=reason, tag=tag, kind="heading" if tag in HEADINGS else KIND_BY_TAG.get(tag, "text"),
            text=clean, normalized_text=normalize_text(clean), document_order=order,
            source_path=path, labels=labels, above_the_fold=atf))

    def walk(self, el: Tag) -> None:
        for child in el.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                if str(child).strip():
                    self.emit(el, str(child), loose=True)
                continue
            if not isinstance(child, Tag) or child.name == "br":
                continue
            name = child.name
            if name in ("a", "button") or name in STRUCT_TEXT:
                if name != "button" and _has_block_desc(child):
                    self.walk(child)
                else:
                    self.emit(child, child.get_text())
            elif _has_block_desc(child) or _has_cta_desc(child):
                self.walk(child)
            else:
                self.emit(child, child.get_text())


def assess_completeness(html: str, blocks: List[TextBlock]) -> Tuple[bool, List[str]]:
    notes: List[str] = []
    complete = True
    total = sum(len(b.text) for b in blocks)
    if not (html or "").strip():
        notes.append("Snapshot is empty.")
        complete = False
    elif not blocks:
        notes.append("No visible text could be extracted from the snapshot.")
        complete = False
    elif total < 150:
        notes.append(f"Only {total} characters of visible text were extracted; the snapshot may be "
                     "incomplete or the page may be client-side rendered.")
        complete = False
    if blocks and total < 400 and re.search(r"""id=["'](?:root|app|__next|__nuxt)["']""", html or ""):
        notes.append("Page looks like a JavaScript single-page-app shell; content is probably "
                     "rendered client-side and missing from this snapshot.")
        complete = False
    if blocks and not any(b.kind == "heading" for b in blocks):
        notes.append("No headings were found, so section classification is less reliable.")
    return complete, notes


def parse_html(html: str, url: Optional[str] = None, layout: Optional[dict] = None) -> ParsedPage:
    """Parse an HTML string into a ``ParsedPage`` of ordered, labelled text blocks."""
    html = html or ""
    soup = BeautifulSoup(html, "lxml")
    title = collapse_ws(soup.title.get_text()) if soup.title else ""
    for el in soup.find_all(REMOVE_TAGS):
        el.decompose()
    for el in [e for e in soup.find_all(True) if _is_hidden(e)]:
        if not getattr(el, "decomposed", False):
            el.decompose()
    ex = _Extractor(layout)
    ex.walk(soup.body or soup)
    complete, notes = assess_completeness(html, ex.blocks)
    layout_used = any(b.above_the_fold is not None for b in ex.blocks)
    logger.debug("parsed %d blocks (complete=%s)", len(ex.blocks), complete)
    return ParsedPage(title=title, url=url, blocks=ex.blocks, snapshot_complete=complete,
                      completeness_notes=notes, layout_used=layout_used)


def parse_file(path, url: Optional[str] = None, layout: Optional[dict] = None) -> ParsedPage:
    from data_loader import read_snapshot
    return parse_html(read_snapshot(path), url=url, layout=layout)
