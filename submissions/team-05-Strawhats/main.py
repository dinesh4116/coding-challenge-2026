
import re
from typing import Optional

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="MatchProof AI",
    description="Evidence-backed Ad Auditor",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



class AnalyzeRequest(BaseModel):
    ad_text: str = Field(min_length=3, max_length=10000)

    destination_url: Optional[str] = None

    # Supply this when the dataset or URL inspector
    # has already recorded the HTTP response status.
    http_status: Optional[int] = Field(default=None, ge=100, le=599)

    landing_page_text: Optional[str] = Field(
        default=None, max_length=200000
    )
    snapshot_html: Optional[str] = Field(
        default=None, max_length=500000
    )



def extract_visible_text(source: str, is_html: bool = False) -> str:
    if not is_html:
        return re.sub(r"\s+", " ", source).strip()

    soup = BeautifulSoup(source, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [
        part.strip(" \t-•")
        for part in parts
        if len(part.strip()) >= 8
    ]


def words(text: str) -> set[str]:
    ignored = {
        "the", "and", "for", "with", "your", "you", "our",
        "get", "this", "that", "from", "are", "was", "will",
        "can", "has", "have", "all", "now", "its", "into",
        "a", "an", "to", "of", "in", "on", "is", "by",
    }
    return {
        word for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 1 and word not in ignored
    }


def detect_claims(ad_text: str) -> list[str]:
    sentences = split_sentences(ad_text)

    markers = (
        "free", "guarantee", "guaranteed", "instant",
        "same-day", "same day", "within", "save", "discount",
        "off", "fastest", "best", "approved", "approval",
        "delivery", "no fee", "zero fee", "risk-free",
        "risk free", "100%", "money back", "24/7",
        "limited time",
    )

    claims = [
        sentence for sentence in sentences
        if any(marker in sentence.lower() for marker in markers)
    ]

    return claims or sentences[:5]


def explicit_contradiction(claim: str, evidence: str) -> bool:
    shared = words(claim) & words(evidence)

    if len(shared) < 2:
        return False

    lower = evidence.lower()
    negations = (
        "not ", "never ", "no ", "cannot ", "can't ",
        "isn't ", "aren't ", "doesn't ", "do not ",
        "not available", "excluded", "fee applies",
    )

    return any(cue in lower for cue in negations)


def analyze_claim(claim: str, page_sentences: list[str]) -> dict:
    claim_words = words(claim)

    if not claim_words:
        return {
            "claim": claim,
            "status": "not_verified",
            "severity": "medium",
            "evidence_quote": None,
            "explanation": "No reliable comparison terms detected.",
            "recommended_fix": "Review this claim manually.",
        }

    best_sentence = None
    best_overlap = 0.0

    for sentence in page_sentences:
        page_words = words(sentence)

        if not page_words:
            continue

        overlap = len(claim_words & page_words) / len(claim_words)

        if overlap > best_overlap:
            best_overlap = overlap
            best_sentence = sentence

    if best_sentence and best_overlap >= 0.60:
        if explicit_contradiction(claim, best_sentence):
            return {
                "claim": claim,
                "status": "contradicted",
                "severity": "high",
                "evidence_quote": best_sentence,
                "explanation": (
                    "Potential conflicting language found. "
                    "Manual review is required."
                ),
                "recommended_fix": (
                    "Align the ad promise with the actual offer."
                ),
            }

        return {
            "claim": claim,
            "status": "supported",
            "severity": "low",
            "evidence_quote": best_sentence,
            "explanation": (
                "Similar terms were found on the page; "
                "this does not guarantee semantic support."
            ),
            "recommended_fix": (
                "Keep the ad and landing page consistent."
            ),
        }

    high_risk = any(
        term in claim.lower()
        for term in (
            "guarantee", "guaranteed", "free",
            "same-day", "same day", "100%",
        )
    )

    return {
        "claim": claim,
        "status": "missing_support",
        "severity": "high" if high_risk else "medium",
        "evidence_quote": None,
        "explanation": (
            "No sufficiently similar supporting statement was found. "
            "This does not prove the claim is false."
        ),
        "recommended_fix": (
            "Substantiate the claim on the page or revise the ad."
        ),
    }


def calculate_score(findings: list[dict]) -> int:
    if not findings:
        return 0

    points = {
        "supported": 100,
        "missing_support": 25,
        "contradicted": 0,
        "not_verified": 0,
    }

    return round(
        sum(points[f["status"]] for f in findings) / len(findings)
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "MatchProof AI"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    
    # Handle inaccessible destinations before analyzing claims.
    if request.http_status == 404:
        return {
            "destination_url": request.destination_url,
            "page_status": "inaccessible",
            "http_status": 404,
            "score": None,
            "score_status": "unavailable",
            "message": (
                "Landing page inaccessible — "
                "unable to assess message match."
            ),
            "findings": [],
            "evidence_quotes": [],
            "reason": (
                "The destination returned HTTP 404 Not Found. "
                "No landing-page evidence was available "
                "for assessment."
            ),
        }

    if request.snapshot_html is not None:
        page_text = extract_visible_text(
            request.snapshot_html, is_html=True
        )
        source_type = "html_snapshot"

    elif request.landing_page_text is not None:
        page_text = extract_visible_text(request.landing_page_text)
        source_type = "plain_text"

    else:
        return {
            "error": "Provide landing_page_text or snapshot_html."
        }

    if not page_text:
        return {
            "score": 0,
            "source_type": source_type,
            "page_inspectable": False,
            "findings": [],
            "summary": "No readable page text was extracted.",
        }

    claims = detect_claims(request.ad_text)
    page_sentences = split_sentences(page_text)

    findings = [
        analyze_claim(claim, page_sentences)
        for claim in claims
    ]

    # Every evidence quote must exist in the extracted page text.
    for finding in findings:
        quote = finding["evidence_quote"]

        if quote is not None and quote not in page_text:
            finding["status"] = "not_verified"
            finding["severity"] = "medium"
            finding["evidence_quote"] = None
            finding["explanation"] = (
                "Evidence failed exact text verification."
            )

    statuses = (
        "supported", "missing_support",
        "contradicted", "not_verified",
    )

    counts = {
        status: sum(f["status"] == status for f in findings)
        for status in statuses
    }

    return {
        "score": calculate_score(findings),
        "score_type": "heuristic_message_match_0_to_100",
        "source_type": source_type,
        "page_inspectable": True,
        "claims_analyzed": len(findings),
        "summary": (
            f"Analyzed {len(findings)} claims: "
            f"{counts['supported']} potentially supported, "
            f"{counts['missing_support']} missing support, "
            f"{counts['contradicted']} potentially contradicted."
        ),
        "counts": counts,
        "findings": findings,
        "limitations": [
            "Keyword overlap does not prove semantic support.",
            "Missing evidence does not prove a claim is false.",
            "The score is a heuristic, not a validated metric.",
        ],
    }
