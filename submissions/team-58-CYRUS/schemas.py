from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DecisionRecordBase(BaseModel):
    row_id: int
    search_term: str
    match_type: str
    campaign: str
    ad_group: str
    impressions: int
    clicks: int
    cost: float
    conversions: int
    conversion_value: float

    # Engineered metrics (safe None)
    ctr: Optional[float] = None
    cpc: Optional[float] = None
    conversion_rate: Optional[float] = None
    cost_per_conversion: Optional[float] = None
    roas: Optional[float] = None
    cr_ci_lower: Optional[float] = None
    cr_ci_upper: Optional[float] = None

    # Intent and relevance
    intent_category: str
    intent_score: float
    relevance_status: str
    relevance_score: float

    # Decision Risk Ledger
    evidence_status: str
    recommended_action: str
    decision_confidence: str
    decision_reason: str
    uncertainty_reason: str
    potential_consequence: str
    human_review_required: bool
    suggested_next_action: str
    historical_cost: float

    # Duplicates & Review
    is_duplicate_term: bool
    term_frequency: int
    has_conflicting_decision: bool
    duplicate_group_id: Optional[str] = None
    review_status: str
    analyst_action: Optional[str] = None
    analyst_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DecisionRecordListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[DecisionRecordBase]

class OverviewMetrics(BaseModel):
    total_records: int
    unique_terms: int
    action_counts: Dict[str, int]
    intent_counts: Dict[str, int]
    evidence_counts: Dict[str, int]
    total_spend: float
    total_clicks: int
    total_impressions: int
    total_conversions: int
    total_conversion_value: float
    review_queue_count: int
    reviewed_count: int
    duplicate_term_count: int
    conflicting_term_count: int
    avg_ctr: Optional[float] = None
    avg_cpc: Optional[float] = None
    avg_cvr: Optional[float] = None
    avg_roas: Optional[float] = None

class HumanReviewCreate(BaseModel):
    row_id: int
    reviewer_action: str  # ACCEPTED, PROMOTE, BLOCK, IGNORE
    review_reason: str
    reviewer_name: Optional[str] = "Lead Analyst"

class HumanReviewResponse(BaseModel):
    id: int
    row_id: int
    search_term: str
    campaign: str
    original_action: str
    reviewer_action: str
    review_reason: str
    reviewer_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class CounterfactualAuditResponse(BaseModel):
    row_id: int
    search_term: str
    campaign: str
    ad_group: str
    match_type: str
    impressions: int
    clicks: int
    cost: float
    conversions: int
    conversion_value: float
    ctr: Optional[float]
    cpc: Optional[float]
    conversion_rate: Optional[float]
    cost_per_conversion: Optional[float]
    roas: Optional[float]
    cr_confidence_interval: Dict[str, Optional[float]]
    intent_category: str
    relevance_status: str
    evidence_status: str
    recommended_action: str
    decision_confidence: str
    primary_influencing_metrics: List[Dict[str, Any]]
    why_chosen: str
    uncertainty_assessment: str
    counterfactual_scenarios: List[Dict[str, Any]]
    evidence_needed_to_flip_action: str
    tradeoff_risk_analysis: Dict[str, str]
    historical_cost: float
    human_review_required: bool
    suggested_next_action: str

class CampaignSummary(BaseModel):
    campaign_name: str
    record_count: int
    total_cost: float
    total_conversions: int
    total_value: float
    total_clicks: int
    total_impressions: int
    ctr: Optional[float]
    cpc: Optional[float]
    cvr: Optional[float]
    cpa: Optional[float]
    roas: Optional[float]
    promote_count: int
    block_count: int
    ignore_count: int
    review_required_count: int

class CampaignConfigUpdate(BaseModel):
    description: Optional[str] = None
    target_cpa: float
    target_roas: float
    min_clicks_threshold: int
    min_spend_threshold: float

class DuplicateGroupSummary(BaseModel):
    search_term: str
    occurrence_count: int
    campaigns: List[str]
    ad_groups: List[str]
    total_cost: float
    total_conversions: int
    decisions: List[str]
    is_conflicting: bool
    records: List[DecisionRecordBase]
