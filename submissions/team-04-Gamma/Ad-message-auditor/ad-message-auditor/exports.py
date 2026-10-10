"""Flatten audit results for CSV / JSON / prioritised fix-list export, merging human reviews.

Review dict format: {"<pair_id>::<finding_index>": {"decision": "accepted|rejected|pending",
"corrected_status": "<status or ''>", "notes": "..."}}.
This tool only audits and recommends. It never changes a Google Ads account.
"""
import io
import json
from typing import Dict, List, Optional

import pandas as pd

from schemas import AuditResult

SEV_RANK = {"high": 0, "medium": 1, "low": 2, "none": 3}
STATUS_RANK = {"contradicted": 0, "missing": 1, "partial": 2, "uncertain": 3, "supported": 4}


def review_key(pair_id: str, idx: int) -> str:
    return f"{pair_id}::{idx}"


def results_to_rows(results: List[AuditResult], reviews: Optional[Dict[str, dict]] = None) -> List[dict]:
    reviews = reviews or {}
    rows: List[dict] = []
    for r in results:
        base = {"pair_id": r.pair_id, "ad_headlines": " | ".join(r.ad_headlines),
                "ad_descriptions": " | ".join(r.ad_descriptions), "landing_page_url": r.landing_page_url or "",
                "source_type": r.source_type, "audit_status": r.audit_status, "match_score": r.match_score,
                "audit_confidence": r.audit_confidence, "pair_needs_human_review": r.needs_human_review,
                "summary": r.summary}
        if not r.findings:
            rows.append({**base, "finding_index": None})
            continue
        for i, f in enumerate(r.findings):
            rv = reviews.get(review_key(r.pair_id, i), {})
            rows.append({**base, "finding_index": i, "mismatch_type": f.mismatch_type, "claim": f.claim,
                         "status": f.status, "severity": f.severity, "evidence_quote": f.evidence_quote,
                         "evidence_verified": f.evidence_verified, "source_block_id": f.source_block_id,
                         "source_section": f.source_section, "document_order": f.document_order,
                         "explanation": f.explanation, "recommended_fix": f.recommended_fix,
                         "needs_human_review": f.needs_human_review, "position_concern": f.position_concern,
                         "rejected_quote": f.unverified_quote, "finding_source": f.finding_source,
                         "reviewer_decision": rv.get("decision", ""), "reviewer_status": rv.get("corrected_status", ""),
                         "reviewer_notes": rv.get("notes", "")})
    return rows


def to_csv_bytes(results: List[AuditResult], reviews: Optional[Dict[str, dict]] = None) -> bytes:
    return pd.DataFrame(results_to_rows(results, reviews)).to_csv(index=False).encode("utf-8-sig")


def to_json_bytes(results: List[AuditResult], reviews: Optional[Dict[str, dict]] = None) -> bytes:
    payload = {"results": [r.model_dump() for r in results], "reviews": reviews or {},
               "note": "Audit only. No Google Ads account was changed."}
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def fix_list(results: List[AuditResult], reviews: Optional[Dict[str, dict]] = None) -> pd.DataFrame:
    """Prioritised fixes: high severity first, contradicted before missing, rejected findings excluded."""
    reviews = reviews or {}
    rows = []
    for r in results:
        for i, f in enumerate(r.findings):
            rv = reviews.get(review_key(r.pair_id, i), {})
            if rv.get("decision") == "rejected":
                continue
            status = rv.get("corrected_status") or f.status
            if status == "supported" and not f.position_concern:
                continue
            rows.append({"pair_id": r.pair_id, "severity": f.severity, "status": status,
                         "mismatch_type": f.mismatch_type, "claim": f.claim,
                         "recommended_fix": f.recommended_fix, "source_section": f.source_section or "",
                         "needs_human_review": f.needs_human_review})
    rows.sort(key=lambda x: (SEV_RANK.get(x["severity"], 9), STATUS_RANK.get(x["status"], 9), x["pair_id"]))
    df = pd.DataFrame(rows, columns=["pair_id", "severity", "status", "mismatch_type", "claim",
                                     "recommended_fix", "source_section", "needs_human_review"])
    df.insert(0, "priority", range(1, len(df) + 1))
    return df
