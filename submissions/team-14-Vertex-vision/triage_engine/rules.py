"""
Decision Engine and Evidence Policy for Search Term Triage (TriageIQ).

Enforces the organizer's output contract:
- Exactly one decision per row: PROMOTE, BLOCK, or IGNORE.
- Human review is strictly represented via the boolean flag: needs_review.
- Preserves full auditability with supporting evidence, counterevidence, and next actions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from .stats import calculate_uncertainty_metrics, calculate_derived_metrics

@dataclass
class AdvertiserProfile:
    """
    Configurable business constraints and product offering boundaries.
    Default profile configured for Kestrel Business Funding.
    """
    name: str = "Kestrel Business Funding"
    industry: str = "US Small Business Lending"
    supported_products: List[str] = field(default_factory=lambda: [
        "working capital loans", "equipment finance", "business lines of credit",
        "merchant cash advances", "sba loans"
    ])
    # Explicit off-target triggers (Kestrel does NOT sell these, nor is it hiring)
    off_target_triggers: List[str] = field(default_factory=lambda: [
        # Multi-word triggers (checked first for greedy phrase matching)
        "personal loan", "personal loans", "home loan", "home loans",
        "car loan", "car loans", "auto loan", "auto loans", "vehicle loan",
        "student loan", "student loans", "college loan",
        "government grant", "federal grant", "gov grant", "small business grant",
        "invoice template", "bill template", "contract template",
        "download free", "sample test", "interview questions",
        # Single-word triggers
        "personal", "mortgage", "mortgages", "student", "grant", "grants",
        "job", "jobs", "hiring", "career", "careers", "salary", "salaries", "resume", "internship",
        "template", "templates", "free", "crack", "torrent", "nulled", "login", "portal",
        "reddit", "youtube", "wikipedia", "definition", "meaning", "pdf"
    ])
    default_target_cpa: float = 220.0
    default_target_roas: float = 3.0


class TriageEngine:
    def __init__(self, 
                 target_cpa: float = 220.0, 
                 target_roas: float = 3.0,
                 campaign_target_cpas: Optional[Dict[str, float]] = None,
                 min_clicks_for_promotion: int = 10,
                 min_conversions_for_promotion: int = 2,
                 advertiser_profile: Optional[AdvertiserProfile] = None,
                 prior_alpha: float = 1.2,
                 prior_beta: float = 28.0):
        """
        Initializes the Evidence-First Triage Engine.
        """
        self.target_cpa = float(target_cpa)
        self.target_roas = float(target_roas)
        self.campaign_target_cpas = campaign_target_cpas or {}
        self.min_clicks_for_promotion = int(min_clicks_for_promotion)
        self.min_conversions_for_promotion = int(min_conversions_for_promotion)
        self.advertiser_profile = advertiser_profile or AdvertiserProfile()
        self.prior_alpha = float(prior_alpha)
        self.prior_beta = float(prior_beta)
        
        # Session storage for human reviewer overrides
        # Key: query_text.lower(), Value: dict with final_decision, action, notes, reviewer
        self.session_overrides: Dict[str, Dict[str, Any]] = {}

    def get_target_cpa_for_campaign(self, campaign: str) -> float:
        """Returns campaign-specific target CPA if mapped, else global target CPA."""
        return self.campaign_target_cpas.get(campaign, self.target_cpa)

    def register_human_correction(self, query: str, action: str, decision: str, notes: str, reviewer: str = "Analyst", timestamp: Optional[str] = None):
        """
        Records an analyst correction in session memory without mutating original rule logic.
        """
        import datetime
        norm_query = query.strip().lower()
        valid_decision = decision.upper()
        if valid_decision not in {"PROMOTE", "BLOCK", "IGNORE"}:
            raise ValueError(f"Invalid decision '{valid_decision}'. Must be PROMOTE, BLOCK, or IGNORE.")
            
        now_ts = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_overrides[norm_query] = {
            "reviewer_action": action,
            "final_decision": valid_decision,
            "reviewer_notes": notes,
            "reviewer": reviewer,
            "reviewed_at": now_ts
        }

    def evaluate_query(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a search term row and returns a complete, audited decision contract:
        - Exactly one decision from: PROMOTE, BLOCK, IGNORE.
        - needs_review boolean flag.
        - Plain-English reason, supporting evidence, counterevidence, and next action.
        """
        row_id = row.get("row_id")
        raw_query = str(row.get("query_text") or row.get("search_term") or "").strip()
        query_lower = raw_query.lower()
        campaign = str(row.get("campaign", "Default Campaign")).strip()
        ad_group = str(row.get("ad_group", "Default Ad Group")).strip()
        match_type = str(row.get("match_type", "Broad")).strip()
        
        # Safe numeric conversions
        try:
            impressions = max(0, int(float(row.get("impressions", 0))))
        except (ValueError, TypeError):
            impressions = 0
            
        try:
            clicks = max(0, int(float(row.get("clicks", 0))))
        except (ValueError, TypeError):
            clicks = 0
            
        try:
            cost = max(0.0, float(row.get("cost", 0.0)))
        except (ValueError, TypeError):
            cost = 0.0
            
        try:
            conversions = max(0.0, float(row.get("conversions", 0.0)))
        except (ValueError, TypeError):
            conversions = 0.0
            
        try:
            conv_val = max(0.0, float(row.get("conversion_value", 0.0)))
        except (ValueError, TypeError):
            conv_val = 0.0

        active_target_cpa = self.get_target_cpa_for_campaign(campaign)
        
        # Performance derived metrics
        derived = calculate_derived_metrics(
            impressions=impressions,
            clicks=clicks,
            cost=cost,
            conversions=conversions,
            conversion_value=conv_val
        )
        
        # Statistical metrics
        stats_metrics = calculate_uncertainty_metrics(
            clicks=clicks,
            conversions=int(round(conversions)),
            cost=cost,
            prior_alpha=self.prior_alpha,
            prior_beta=self.prior_beta,
            target_cpa=active_target_cpa
        )
        
        raw_cvr = derived["raw_cvr"]
        cpa = derived["cpa"]
        roas = derived["roas"]
        ctr = derived["ctr"]
        cpc = derived["cpc"]
        
        ci_lower = stats_metrics["ci_lower"]
        ci_upper = stats_metrics["ci_upper"]
        ci_width = stats_metrics["ci_width"]
        shrunk_cvr = stats_metrics["shrunk_cvr"]
        uncertainty_score = stats_metrics["uncertainty_score"]
        
        # Check for explicit business exclusions
        padded_query = f" {query_lower} "
        matched_trigger = next(
            (t for t in self.advertiser_profile.off_target_triggers if f" {t} " in padded_query),
            None
        )

        # -------------------------------------------------------------
        # CORE DECISION LOGIC (Rule Engine Baseline)
        # -------------------------------------------------------------
        
        # Default initialization
        rule_decision = "IGNORE"
        confidence = "HIGH"
        needs_review = False
        reason = ""
        supporting_evidence = ""
        counterevidence = ""
        next_action = ""
        target_match_type = "None"
        action_level = "None"
        negative_type = "N/A"
        proposed_bid = 0.0

        # Branch 1: Explicit off-target business constraint with 0 conversions
        if matched_trigger and conversions == 0:
            rule_decision = "BLOCK"
            confidence = "HIGH"
            needs_review = False
            action_level = "Campaign"
            negative_type = "Negative Phrase"
            target_match_type = f'"{matched_trigger}"'
            reason = f"Non-commercial / off-target intent: contains '{matched_trigger}' outside {self.advertiser_profile.name} product offering ($ {cost:.2f} spent, 0 conversions)."
            supporting_evidence = f"Violates business scope: {self.advertiser_profile.name} does not offer '{matched_trigger}'. Zero loan applications across {clicks} clicks."
            counterevidence = "None; explicit business offering constraint."
            next_action = f"Add Campaign-level Negative Phrase '{matched_trigger}' to eliminate off-target ad spend."

        # Branch 2: Conflicting signal (off-target trigger BUT logged conversions)
        elif matched_trigger and conversions > 0:
            rule_decision = "IGNORE"
            confidence = "LOW"
            needs_review = True
            reason = f"Conflicting signal: contains off-target term '{matched_trigger}' but logged {int(conversions)} conversion(s). Verify attribution."
            supporting_evidence = f"Logged {int(conversions)} conversion(s) (${conv_val:.2f} attributed value)."
            counterevidence = f"Matches exclusion trigger '{matched_trigger}' outside business offering. Potential conversion tracking misattribution or atypical query."
            next_action = "Manual analyst verification required: check lead validity in CRM before deciding whether to exclude or bid."

        # Branch 3: Sustained spend bleeder with statistical confirmation
        # Cost >= 1.5x target CPA, clicks >= 15, zero conversions, and Wilson upper bound <= 15%
        elif conversions == 0 and cost >= (1.5 * active_target_cpa) and clicks >= 15 and ci_upper <= 0.15:
            rule_decision = "BLOCK"
            confidence = "HIGH"
            needs_review = False
            action_level = "Ad Group" if clicks < 30 else "Campaign"
            negative_type = "Negative Exact"
            target_match_type = f"[{raw_query}]"
            reason = f"Sustained spend bleeder: spent ${cost:.2f} across {clicks} clicks with 0 conversions (95% CI upper bound CVR {ci_upper:.1%})."
            supporting_evidence = f"Statistically adequate volume ({clicks} clicks) exceeding 1.5x target CPA (${cost:.2f} vs ${active_target_cpa:.2f}) with zero conversions."
            counterevidence = f"Theoretical upper bound CVR is {ci_upper:.1%}; risk of false exclusion is low (< 5%)."
            next_action = f"Add {action_level}-level Negative Exact [{raw_query}] to prevent continued spend drain."

        # Branch 4: Underpowered bleeder / Borderline spend (0.8x to 1.5x target CPA with 0 conversions)
        elif conversions == 0 and (0.8 * active_target_cpa <= cost < 1.5 * active_target_cpa):
            rule_decision = "IGNORE"
            confidence = "MEDIUM"
            needs_review = True
            reason = f"Borderline spend (${cost:.2f}, {clicks} clicks, 0 convs); underpowered for automated block. Human review recommended."
            supporting_evidence = "None; zero conversions recorded."
            counterevidence = f"Spend is high (${cost:.2f}), but {clicks} click(s) is insufficient to statistically prove zero commercial viability."
            next_action = "Analyst review: inspect query relevance. If clearly off-topic, block proactively; otherwise monitor for 5-10 more clicks."

        # Branch 5: High-evidence promotion candidate
        # PREREQUISITES: Meets explicit evidence threshold, profitable CPA, and narrow confidence interval
        elif (conversions >= self.min_conversions_for_promotion and 
              clicks >= self.min_clicks_for_promotion and 
              cpa is not None and cpa <= (1.15 * active_target_cpa) and 
              ci_lower >= 0.015 and ci_width <= 0.40):
            rule_decision = "PROMOTE"
            confidence = "HIGH"
            needs_review = False
            action_level = "Ad Group"
            target_match_type = f"[{raw_query}]"
            proposed_bid = min(round(active_target_cpa * shrunk_cvr, 2), 25.0)
            reason = f"High-evidence promotion candidate: {int(conversions)} convs, profitable CPA ${cpa:.2f} (<= ${active_target_cpa:.2f}), robust Wilson lower CVR {ci_lower:.1%}."
            supporting_evidence = f"{int(conversions)} conversions across {clicks} clicks; CPA ${cpa:.2f} meets profitability target ${active_target_cpa:.2f}; 95% CI [{ci_lower:.1%}, {ci_upper:.1%}]."
            counterevidence = f"Attributed value of ${conv_val:.2f} does not represent net profit. Continued monitoring of CPA required once promoted."
            next_action = f"Promote as Exact Match [{raw_query}] in {ad_group} with suggested Max CPC bid ${proposed_bid:.2f}."

        # Branch 6: Small-sample conversion anomaly (THE CLASSIC TRAP: e.g., 1-2 clicks, 1 conversion)
        elif conversions > 0 and (clicks < self.min_clicks_for_promotion or conversions < self.min_conversions_for_promotion or ci_width > 0.40):
            rule_decision = "IGNORE"
            confidence = "LOW"
            needs_review = True
            reason = f"Small-sample noise: {int(conversions)} conv from {clicks} click(s) (raw CVR {raw_cvr:.0%}, 95% CI [{ci_lower:.1%}, {ci_upper:.1%}]). Insufficient evidence to justify budget."
            supporting_evidence = f"Logged {int(conversions)} conversion(s) (${conv_val:.2f} attributed value)."
            counterevidence = f"Extreme small-sample variance: sample of {clicks} click(s) produces wide 95% interval [{ci_lower:.1%}, {ci_upper:.1%}] (spread {ci_width:.1%}). High probability of random fluke."
            next_action = "Route to analyst review: verify whether commercial intent warrants promotion before dedicating keyword bid."

        # Branch 7: High-volume converter with UNPROFITABLE CPA
        elif conversions >= self.min_conversions_for_promotion and clicks >= self.min_clicks_for_promotion and cpa is not None and cpa > (1.15 * active_target_cpa):
            rule_decision = "IGNORE"
            confidence = "MEDIUM"
            needs_review = True
            reason = f"Unprofitable converter: {int(conversions)} convs, but CPA ${cpa:.2f} exceeds target ${active_target_cpa:.2f}. Restructuring required."
            supporting_evidence = f"{int(conversions)} loan applications submitted."
            counterevidence = f"CPA ${cpa:.2f} exceeds allowable cost ceiling ${active_target_cpa:.2f}."
            next_action = "Review landing page and bid strategy; consider lower bid rather than promoting as primary keyword."

        # Branch 8: Default dormant / low-volume long tail (Normal status quo)
        else:
            rule_decision = "IGNORE"
            confidence = "HIGH"
            needs_review = False
            reason = f"Low volume/spend (${cost:.2f}, {clicks} clicks, {impressions} impr); leave alone to preserve keyword list limits."
            supporting_evidence = "Negligible financial exposure and traffic volume."
            counterevidence = "Insufficient evidence to evaluate commercial performance."
            next_action = "Maintain status quo; do not add negative or positive keyword."

        # -------------------------------------------------------------
        # APPLY REVIEWER FEEDBACK (Session Memory Layer)
        # -------------------------------------------------------------
        final_decision = rule_decision
        reviewer_action = None
        reviewer_notes = None
        is_reviewed = False
        reviewed_at = None
        
        if query_lower in self.session_overrides:
            override = self.session_overrides[query_lower]
            final_decision = override["final_decision"]
            reviewer_action = override["reviewer_action"]
            reviewer_notes = override["reviewer_notes"]
            reviewed_at = override.get("reviewed_at")
            is_reviewed = True
            needs_review = False  # Human has reviewed this item
            confidence = "HIGH (REVIEWER CONFIRMED)"
            reason = f"Analyst override ({override['reviewer']}): {reviewer_notes}"
            if final_decision == "PROMOTE":
                target_match_type = f"[{raw_query}]"
                action_level = "Ad Group"
                negative_type = "N/A"
                proposed_bid = min(round(active_target_cpa * max(shrunk_cvr, 0.05), 2), 25.0)
                next_action = f"Promote as Exact Match [{raw_query}] (confirmed by analyst)."
            elif final_decision == "BLOCK":
                target_match_type = f"[{raw_query}]"
                action_level = "Campaign"
                negative_type = "Negative Exact"
                proposed_bid = 0.0
                next_action = f"Add Campaign-level Negative Exact [{raw_query}] (confirmed by analyst)."
            else:
                target_match_type = "None"
                action_level = "None"
                negative_type = "N/A"
                proposed_bid = 0.0
                next_action = "Dismissed by analyst; maintain status quo."

        return {
            "row_id": row_id,
            "query_text": raw_query,
            "campaign": campaign,
            "ad_group": ad_group,
            "match_type": match_type,
            # Output Contract Fields
            "decision": final_decision,
            "confidence": confidence,
            "needs_review": needs_review,
            "reason": reason,
            "supporting_evidence": supporting_evidence,
            "counterevidence": counterevidence,
            "next_action": next_action,
            "original_decision": rule_decision,
            "is_reviewed": is_reviewed,
            "reviewer_action": reviewer_action,
            "reviewer_notes": reviewer_notes,
            "reviewed_at": reviewed_at,
            # Google Ads Recommendation Attributes
            "target_match_type": target_match_type,
            "action_level": action_level,
            "negative_type": negative_type,
            "proposed_bid": proposed_bid,
            # Core Performance & Statistical Fields
            "impressions": impressions,
            "clicks": clicks,
            "cost": cost,
            "conversions": conversions,
            "conversion_value": conv_val,
            "ctr": derived["ctr"],
            "cpc": derived["cpc"],
            "raw_cvr": derived["raw_cvr"],
            "shrunk_cvr": stats_metrics["shrunk_cvr"],
            "ci_lower": stats_metrics["ci_lower"],
            "ci_upper": stats_metrics["ci_upper"],
            "ci_width": stats_metrics["ci_width"],
            "cpa": derived["cpa"],
            "roas": derived["roas"],
            "uncertainty_score": stats_metrics["uncertainty_score"]
        }
