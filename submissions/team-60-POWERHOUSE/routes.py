import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Path
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from typing import Optional, List, Dict, Any

from ..schemas.audit import (
    AuditRequest,
    AuditResponse,
    AdInput,
    SyntheticScenario,
    PageExtractionSummary,
    MatchStatus
)
from ..services.extraction import (
    fetch_html_from_url,
    parse_html_content,
    validate_snapshot_file,
    ExtractionException,
    ExtractedPageData
)
from ..services.claims import extract_claims_from_ad
from ..services.matching import audit_all_claims, analyze_cta_continuity
from ..services.scoring import calculate_score
from ..services.recommendations import generate_recommendations
from ..services.export import (
    generate_markdown_report,
    generate_csv_claims,
    generate_self_contained_html_report
)
from ..services.demo_data import (
    SYNTHETIC_SCENARIOS,
    get_scenario_by_id,
    load_scenario_html
)
from ..core.security import SecurityException

router = APIRouter(prefix="/api")

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "PS-03 Ad-to-Landing-Page Message Match Auditor"}

# Requirement 1: GET /api/demo
@router.get("/demo", response_model=List[SyntheticScenario])
def get_all_demo_scenarios():
    """
    Returns the 7 pre-configured synthetic scenarios labeled 'Synthetic example'.
    """
    return SYNTHETIC_SCENARIOS

# Alias for backward compatibility
@router.get("/demo-scenarios", response_model=List[SyntheticScenario])
def get_demo_scenarios_alias():
    return SYNTHETIC_SCENARIOS

# Requirement 1: GET /api/demo/{id}
@router.get("/demo/{id}")
def get_demo_scenario_by_id(id: str = Path(...)):
    """
    Returns a specific scenario with its real HTML content loaded from sample_data/pages/.
    """
    scenario = get_scenario_by_id(id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{id}' not found.")
    
    html_content = ""
    try:
        html_content = load_scenario_html(scenario)
    except FileNotFoundError:
        pass

    return {
        **scenario.model_dump(),
        "html_content": html_content
    }

def run_audit_pipeline(
    ad_input: AdInput,
    raw_html: str,
    page_url: Optional[str] = None,
    is_synthetic: bool = False,
    source_desc: str = "Live Webpage"
) -> AuditResponse:
    """
    Core deterministic pipeline executing all audit steps.
    No demo result is ever hardcoded; every scenario executes this identical logic.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Parse and extract page structure
    page_data: ExtractedPageData = parse_html_content(raw_html, url=page_url)

    # 2. Extract atomic claims from Ad
    claims_atomic = extract_claims_from_ad(ad_input)

    # 3. Match claims deterministically and verify quotes
    claims_audited = audit_all_claims(claims_atomic, page_data)

    # 4. Dedicated CTA continuity analysis (Requirement 7)
    cta_analysis = analyze_cta_continuity(ad_input.cta, page_data)

    # 5. Compute explainable score according to documented formula (Requirement 3)
    score, grade, verdict, breakdown = calculate_score(claims_audited, page_data, cta_analysis)

    # 6. Generate prioritized recommendations
    recommendations = generate_recommendations(claims_audited, breakdown, page_data)

    # 7. Page summary for frontend display
    page_summary = PageExtractionSummary(
        url=page_url,
        title=page_data.title,
        headings_h1=page_data.headings_h1,
        headings_h2_h3=page_data.headings_h2_h3,
        hero_text=page_data.hero_text,
        detected_ctas=page_data.detected_ctas,
        footer_disclosures=page_data.footer_disclosures,
        word_count=page_data.word_count,
        reading_time_minutes=page_data.reading_time_minutes,
        text_length=len(page_data.normalized_text)
    )

    # Calculate status counts
    supported_cnt = sum(1 for c in claims_audited if c.status == MatchStatus.SUPPORTED)
    partial_cnt = sum(1 for c in claims_audited if c.status == MatchStatus.PARTIAL_MATCH)
    not_found_cnt = sum(1 for c in claims_audited if c.status == MatchStatus.NOT_FOUND)
    contradicted_cnt = sum(1 for c in claims_audited if c.status == MatchStatus.CONTRADICTED)
    uncertain_cnt = sum(1 for c in claims_audited if c.status == MatchStatus.UNCERTAIN)

    return AuditResponse(
        success=True,
        is_synthetic_demo=is_synthetic,
        demo_badge="Synthetic example" if is_synthetic else None,
        timestamp=timestamp,
        source_description=source_desc,
        overall_score=score,
        grade=grade,
        presentation_aid_note="Letter grade is a presentation aid derived from the numerical score.",
        summary_verdict=verdict,
        score_breakdown=breakdown,
        cta_analysis=cta_analysis,
        total_claims=len(claims_audited),
        supported_count=supported_cnt,
        partial_count=partial_cnt,
        not_found_count=not_found_cnt,
        contradicted_count=contradicted_cnt,
        uncertain_count=uncertain_cnt,
        claims=claims_audited,
        recommendations=recommendations,
        page_summary=page_summary
    )

class UrlAuditPayload(AuditRequest):
    pass

# Requirement 1: POST /api/audit/url
@router.post("/audit/url", response_model=AuditResponse)
async def audit_by_url(payload: UrlAuditPayload):
    """
    Audits an ad against a live URL with SSRF protection.
    """
    if not payload.url or not payload.url.strip():
        return AuditResponse(
            success=False,
            is_synthetic_demo=payload.is_synthetic_demo,
            demo_badge="Synthetic example" if payload.is_synthetic_demo else None,
            error_type="MISSING_URL",
            error_message="A valid target URL is required.",
            overall_score=None
        )

    try:
        raw_html = await fetch_html_from_url(payload.url.strip())
        return run_audit_pipeline(
            ad_input=payload.ad,
            raw_html=raw_html,
            page_url=payload.url.strip(),
            is_synthetic=payload.is_synthetic_demo,
            source_desc=f"Live URL: {payload.url.strip()}"
        )
    except SecurityException as sec_err:
        return AuditResponse(
            success=False,
            is_synthetic_demo=payload.is_synthetic_demo,
            demo_badge="Synthetic example" if payload.is_synthetic_demo else None,
            error_type="SECURITY_VIOLATION",
            error_message=str(sec_err),
            overall_score=None
        )
    except ExtractionException as ext_err:
        return AuditResponse(
            success=False,
            is_synthetic_demo=payload.is_synthetic_demo,
            demo_badge="Synthetic example" if payload.is_synthetic_demo else None,
            error_type="EXTRACTION_FAILED",
            error_message=str(ext_err),
            overall_score=None
        )
    except Exception as e:
        return AuditResponse(
            success=False,
            is_synthetic_demo=payload.is_synthetic_demo,
            demo_badge="Synthetic example" if payload.is_synthetic_demo else None,
            error_type="PROCESSING_ERROR",
            error_message=f"Audit analysis failed: {str(e)}",
            overall_score=None
        )

# Requirement 1: POST /api/audit/snapshot (multipart)
@router.post("/audit/snapshot", response_model=AuditResponse)
async def audit_by_snapshot(
    headline: str = Form(...),
    description: str = Form(...),
    cta: Optional[str] = Form(None),
    html_file: UploadFile = File(...)
):
    """
    Audits an ad against an uploaded HTML snapshot with extension, size, and binary checks.
    """
    try:
        content_bytes = await html_file.read()
        
        # Snapshot validation (Requirement 5)
        is_valid, validation_err = validate_snapshot_file(html_file.filename or "", content_bytes)
        if not is_valid:
            return AuditResponse(
                success=False,
                error_type="INVALID_SNAPSHOT",
                error_message=validation_err,
                overall_score=None
            )

        raw_html = content_bytes.decode("utf-8", errors="replace")
        ad_input = AdInput(headline=headline, description=description, cta=cta)

        return run_audit_pipeline(
            ad_input=ad_input,
            raw_html=raw_html,
            page_url=f"Snapshot: {html_file.filename}",
            is_synthetic=False,
            source_desc=f"Uploaded Snapshot: {html_file.filename}"
        )
    except ExtractionException as ext_err:
        return AuditResponse(
            success=False,
            error_type="EXTRACTION_FAILED",
            error_message=str(ext_err),
            overall_score=None
        )
    except Exception as e:
        return AuditResponse(
            success=False,
            error_type="PROCESSING_ERROR",
            error_message=f"Failed to process snapshot: {str(e)}",
            overall_score=None
        )

# Alias route: POST /api/audit/upload
@router.post("/audit/upload", response_model=AuditResponse)
async def audit_upload_alias(
    headline: str = Form(...),
    description: str = Form(...),
    cta: Optional[str] = Form(None),
    html_file: UploadFile = File(...)
):
    return await audit_by_snapshot(headline=headline, description=description, cta=cta, html_file=html_file)

# General / Backward compatible POST /api/audit
@router.post("/audit", response_model=AuditResponse)
async def audit_general(request: AuditRequest):
    try:
        if request.html_content and request.html_content.strip():
            return run_audit_pipeline(
                ad_input=request.ad,
                raw_html=request.html_content.strip(),
                page_url="Direct HTML Snapshot",
                is_synthetic=request.is_synthetic_demo,
                source_desc="Direct HTML Snapshot"
            )
        elif request.url and request.url.strip():
            raw_html = await fetch_html_from_url(request.url.strip())
            return run_audit_pipeline(
                ad_input=request.ad,
                raw_html=raw_html,
                page_url=request.url.strip(),
                is_synthetic=request.is_synthetic_demo,
                source_desc=f"Live URL: {request.url.strip()}"
            )
        else:
            return AuditResponse(
                success=False,
                is_synthetic_demo=request.is_synthetic_demo,
                demo_badge="Synthetic example" if request.is_synthetic_demo else None,
                error_type="MISSING_INPUT",
                error_message="Please provide either a valid Landing Page URL or an HTML snapshot.",
                overall_score=None
            )
    except SecurityException as sec_err:
        return AuditResponse(
            success=False,
            is_synthetic_demo=request.is_synthetic_demo,
            demo_badge="Synthetic example" if request.is_synthetic_demo else None,
            error_type="SECURITY_VIOLATION",
            error_message=str(sec_err),
            overall_score=None
        )
    except ExtractionException as ext_err:
        return AuditResponse(
            success=False,
            is_synthetic_demo=request.is_synthetic_demo,
            demo_badge="Synthetic example" if request.is_synthetic_demo else None,
            error_type="EXTRACTION_FAILED",
            error_message=str(ext_err),
            overall_score=None
        )
    except Exception as e:
        return AuditResponse(
            success=False,
            is_synthetic_demo=request.is_synthetic_demo,
            demo_badge="Synthetic example" if request.is_synthetic_demo else None,
            error_type="PROCESSING_ERROR",
            error_message=f"Analysis failed: {str(e)}",
            overall_score=None
        )

# Requirement 1 & 9: POST /api/export/{format} (csv | json | html)
@router.post("/export/{format}")
def export_by_format(
    format: str = Path(..., pattern="^(csv|json|html|markdown)$"),
    audit: AuditResponse = ...
):
    """
    Exports audit report in CSV (with formula injection escaping),
    HTML (self-contained with escaped text), or JSON format.
    """
    fmt = format.lower()
    if fmt == "csv":
        csv_text = generate_csv_claims(audit)
        return PlainTextResponse(content=csv_text, media_type="text/csv")
    elif fmt == "html":
        html_text = generate_self_contained_html_report(audit)
        return HTMLResponse(content=html_text)
    elif fmt == "json":
        return JSONResponse(content=audit.model_dump())
    elif fmt == "markdown":
        md_text = generate_markdown_report(audit)
        return PlainTextResponse(content=md_text, media_type="text/markdown")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format '{format}'.")

# Aliases for export endpoints
@router.post("/export/markdown", response_class=PlainTextResponse)
def export_markdown_alias(audit: AuditResponse):
    return generate_markdown_report(audit)

@router.post("/export/csv", response_class=PlainTextResponse)
def export_csv_alias(audit: AuditResponse):
    return generate_csv_claims(audit)
