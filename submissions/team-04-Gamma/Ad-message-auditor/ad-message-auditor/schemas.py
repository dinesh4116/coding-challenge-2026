"""Pydantic data models shared by every module.

Three layers of data flow through the system:

1. Page layer   - ``TextBlock`` / ``ParsedPage`` (what the parser extracted).
2. Claim layer  - ``RawFinding`` (unverified output of the LLM or the rule checks).
3. Result layer - ``Finding`` / ``AuditResult`` (verified, scored, exportable).

A ``RawFinding`` is never trusted. Only ``verifier.verify_findings`` turns it into
a ``Finding`` and decides whether its quotation counts as verified evidence.
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SectionName = Literal["hero", "main", "features", "pricing", "faq", "footer", "unknown"]
Confidence = Literal["high", "medium", "low"]
Status = Literal["supported", "partial", "missing", "contradicted", "uncertain"]
Severity = Literal["none", "low", "medium", "high"]
MismatchType = Literal[
    "offer", "timing", "pricing", "fees", "eligibility", "trial",
    "guarantee", "feature", "cta", "regulated_claim", "other",
]
AuditStatus = Literal["completed", "needs_review", "failed"]

MISMATCH_TYPES = list(MismatchType.__args__)
STATUSES = list(Status.__args__)
SEVERITIES = list(Severity.__args__)
SECTIONS = list(SectionName.__args__)


# --------------------------------------------------------------------- page layer
class TextBlock(BaseModel):
    block_id: str
    section: SectionName = "unknown"
    section_confidence: Confidence = "low"
    section_reason: str = ""
    tag: str
    kind: str = "text"              # heading | paragraph | list_item | button | link | table_cell | text
    text: str                       # original text, whitespace collapsed only
    normalized_text: str            # NFKC + case-folded + punctuation-normalised (used for matching)
    document_order: int = Field(ge=1)
    source_path: str = ""           # stable DOM path, e.g. body>main>section#hero>h1[1]
    labels: List[str] = Field(default_factory=list)   # pricing, disclaimer, navigation, cta
    above_the_fold: Optional[bool] = None             # only set when layout metadata is supplied


class ParsedPage(BaseModel):
    title: str = ""
    url: Optional[str] = None
    blocks: List[TextBlock] = Field(default_factory=list)
    snapshot_complete: bool = True
    completeness_notes: List[str] = Field(default_factory=list)
    layout_used: bool = False


# ------------------------------------------------------------------- input layer
class AdPair(BaseModel):
    pair_id: str
    ad_headlines: List[str] = Field(default_factory=list)
    ad_descriptions: List[str] = Field(default_factory=list)
    landing_page_url: Optional[str] = None
    snapshot_file: Optional[str] = None


# ----------------------------------------------------------------- claim layer
class RawFinding(BaseModel):
    claim: str
    mismatch_type: MismatchType = "other"
    status: Status
    severity: Severity = "medium"
    evidence_quote: Optional[str] = None
    explanation: str = ""
    recommended_fix: str = ""
    finding_source: Literal["llm", "rule"] = "llm"


class LLMResponse(BaseModel):
    findings: List[RawFinding] = Field(default_factory=list)


# --------------------------------------------------------------- result layer
class Finding(BaseModel):
    mismatch_type: MismatchType = "other"
    claim: str
    status: Status
    severity: Severity = "low"
    evidence_quote: Optional[str] = None      # ONLY set when verified against the page text
    evidence_verified: bool = False
    source_block_id: Optional[str] = None
    source_section: Optional[SectionName] = None
    document_order: Optional[int] = Field(default=None, ge=1)
    explanation: str = ""
    recommended_fix: str = ""
    needs_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    unverified_quote: Optional[str] = None    # a model quote that FAILED verification (shown as rejected)
    position_concern: bool = False
    position_note: str = ""
    finding_source: Literal["llm", "rule"] = "llm"


class AuditResult(BaseModel):
    pair_id: str
    ad_headlines: List[str] = Field(default_factory=list)
    ad_descriptions: List[str] = Field(default_factory=list)
    landing_page_url: Optional[str] = None
    source_type: Literal["offline_snapshot", "live_fetch", "none"] = "offline_snapshot"
    page_title: str = ""
    audit_status: AuditStatus = "needs_review"
    match_score: Optional[float] = Field(default=None, ge=0, le=100)   # None = could not be evaluated
    audit_confidence: float = Field(default=0.0, ge=0, le=1)           # separate from match_score
    summary: str = ""
    findings: List[Finding] = Field(default_factory=list)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    needs_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    snapshot_notes: List[str] = Field(default_factory=list)
    llm_status: str = "disabled"       # ok | disabled | unavailable | invalid_output | skipped_empty
