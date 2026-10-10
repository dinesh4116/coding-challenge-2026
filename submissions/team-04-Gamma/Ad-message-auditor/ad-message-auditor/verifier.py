"""Evidence verification. A model-generated finding is NEVER verified just because it
matches the JSON schema: every quotation is checked against the extracted page text.

Rules
-----
* A quote is verified only if its normalised form is a substring of ONE extracted block.
  The original quote text is preserved for display (never silently rewritten).
* A supported/partial/contradicted finding without a verified quote is downgraded to
  ``uncertain`` and flagged for human review; the rejected quote is kept separately.
* ``missing`` findings never carry a quote. They only say "not found in inspected content",
  and become ``uncertain`` if the snapshot is incomplete.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from parser import normalize_text
from schemas import Finding, ParsedPage, RawFinding, TextBlock

logger = logging.getLogger(__name__)
MIN_QUOTE_CHARS = 4
POSITION_WEAK = {"footer": "footer", "faq": "FAQ", "unknown": "an unclassified area"}


@dataclass
class VerificationResult:
    verified: bool
    block: Optional[TextBlock] = None
    reason: str = ""


def verify_quote(quote: Optional[str], blocks: List[TextBlock]) -> VerificationResult:
    nq = normalize_text(quote or "")
    if len(nq) < MIN_QUOTE_CHARS:
        return VerificationResult(False, None, "Quotation is empty or too short to verify.")
    for b in sorted(blocks, key=lambda x: x.document_order):
        if nq in b.normalized_text:
            return VerificationResult(True, b, "Exact match in extracted text.")
    return VerificationResult(False, None, "Quotation was not found in any single extracted text block.")


def verify_findings(raw_findings: List[RawFinding], page: ParsedPage,
                    complete: Optional[bool] = None) -> List[Finding]:
    """Turn unverified findings into verified ``Finding`` objects."""
    complete = page.snapshot_complete if complete is None else complete
    out: List[Finding] = []
    for raw in raw_findings:
        status = raw.status
        reasons: List[str] = []
        quote = (raw.evidence_quote or "").strip() or None
        f = Finding(mismatch_type=raw.mismatch_type, claim=raw.claim, status=status,
                    severity=raw.severity, explanation=raw.explanation,
                    recommended_fix=raw.recommended_fix, finding_source=raw.finding_source)
        if status == "missing":
            if quote:
                f.unverified_quote = quote       # a 'missing' finding must not carry evidence
                reasons.append("A quotation was attached to a 'missing' finding and was discarded.")
            if not complete:
                f.status = "uncertain"
                reasons.append("Snapshot may be incomplete, so absence cannot be confirmed.")
            else:
                f.explanation = (f.explanation + " " if f.explanation else "") + \
                    "Claim was not found in the inspected page content."
        elif status in ("supported", "partial", "contradicted", "uncertain"):
            if quote:
                vr = verify_quote(quote, page.blocks)
                if vr.verified and vr.block is not None:
                    b = vr.block
                    f.evidence_quote, f.evidence_verified = quote, True
                    f.source_block_id, f.source_section, f.document_order = b.block_id, b.section, b.document_order
                    if b.section == "unknown" or b.section_confidence == "low":
                        reasons.append("Section of the evidence could not be classified reliably.")
                    if status in ("supported", "partial") and b.section in POSITION_WEAK:
                        f.position_concern = True
                        f.position_note = (f"Supporting text appears in {POSITION_WEAK[b.section]} "
                                           "(document position only; visual prominence is not verified).")
                else:
                    f.unverified_quote = quote
                    reasons.append(f"Quotation rejected: {vr.reason}")
                    if status != "uncertain":
                        f.status = "uncertain"
            elif status != "uncertain":
                f.status = "uncertain"
                reasons.append("No evidence quotation was provided for this finding.")
        if f.status == "uncertain" and not reasons:
            reasons.append("Finding is uncertain.")
        if not complete:
            reasons.append("Snapshot may be incomplete.")
        if f.status == "supported":
            f.severity = "none"
        elif f.severity == "none":
            f.severity = "low"
        f.review_reasons = list(dict.fromkeys(reasons))
        f.needs_human_review = bool(f.review_reasons)
        out.append(f)
    return out
