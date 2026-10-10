from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from datetime import datetime
from backend.app.database import Base

class DecisionRecord(Base):
    __tablename__ = "decisions"

    row_id = Column(Integer, primary_key=True, index=True)
    search_term = Column(String(500), nullable=False, index=True)
    match_type = Column(String(50), nullable=False, index=True)
    campaign = Column(String(200), nullable=False, index=True)
    ad_group = Column(String(200), nullable=False, index=True)
    impressions = Column(Integer, nullable=False)
    clicks = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    conversions = Column(Integer, nullable=False)
    conversion_value = Column(Float, nullable=False)

    # Engineered performance features (nullable for safe zero denominators)
    ctr = Column(Float, nullable=True)
    cpc = Column(Float, nullable=True)
    conversion_rate = Column(Float, nullable=True)
    cost_per_conversion = Column(Float, nullable=True)
    roas = Column(Float, nullable=True)
    cr_ci_lower = Column(Float, nullable=True)
    cr_ci_upper = Column(Float, nullable=True)

    # Search-intent and relevance
    intent_category = Column(String(50), nullable=False, index=True)
    intent_score = Column(Float, nullable=False)
    relevance_status = Column(String(50), nullable=False, index=True)
    relevance_score = Column(Float, nullable=False)

    # Decision Risk Ledger
    evidence_status = Column(String(50), nullable=False, index=True)
    recommended_action = Column(String(50), nullable=False, index=True)
    decision_confidence = Column(String(50), nullable=False, index=True)
    decision_reason = Column(Text, nullable=False)
    uncertainty_reason = Column(Text, nullable=False)
    potential_consequence = Column(Text, nullable=False)
    human_review_required = Column(Boolean, nullable=False, default=False, index=True)
    suggested_next_action = Column(Text, nullable=False)
    historical_cost = Column(Float, nullable=False, default=0.0)

    # Duplicate Intelligence
    is_duplicate_term = Column(Boolean, nullable=False, default=False, index=True)
    term_frequency = Column(Integer, nullable=False, default=1)
    has_conflicting_decision = Column(Boolean, nullable=False, default=False, index=True)
    duplicate_group_id = Column(String(100), nullable=True, index=True)

    # Human Review Status tracking
    review_status = Column(String(50), nullable=False, default="UNREVIEWED", index=True)
    analyst_action = Column(String(50), nullable=True)
    analyst_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    row_id = Column(Integer, nullable=False, index=True)
    search_term = Column(String(500), nullable=False)
    campaign = Column(String(200), nullable=False)
    original_action = Column(String(50), nullable=False)
    reviewer_action = Column(String(50), nullable=False)
    review_reason = Column(Text, nullable=False)
    reviewer_name = Column(String(100), nullable=False, default="Analyst")
    created_at = Column(DateTime, default=datetime.utcnow)

class CampaignConfig(Base):
    __tablename__ = "campaign_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    target_cpa = Column(Float, nullable=False, default=150.0)
    target_roas = Column(Float, nullable=False, default=4.0)
    min_clicks_threshold = Column(Integer, nullable=False, default=10)
    min_spend_threshold = Column(Float, nullable=False, default=100.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
