import re

class DecisionEngine:

    """
    Explainable, cautious rule-based decision engine for Google Ads Search Term Triage.
    Produces decisions: PROMOTE, BLOCK, IGNORE, HUMAN REVIEW.
    Guarantees transparent step-by-step evidence justification.
    """

    def __init__(self, context_config=None):
        self.context = context_config or {
            "business_name": "General Business",
            "product_description": "Products or services",
            "relevant_intents": [],
            "irrelevant_intents": [],
            "negative_keywords": ["free", "torrent", "crack", "hack", "teardown", "repair manual", "salary", "jobs", "wikipedia", "cardboard", "diy", "schematic"],
            "min_clicks_threshold": 10,
            "min_cost_threshold": 15.0,
            "target_cpa_threshold": 50.0,
            "roas_threshold": 1.0
        }

    def _assess_relevance(self, query, campaign="", ad_group=""):
        """
        Assesses text match against business context & negative keywords.
        Returns: ('RELEVANT' | 'IRRELEVANT' | 'AMBIGUOUS', list_of_signals)
        """
        query_lower = query.lower().strip()
        signals = []

        if not query_lower:
            return "AMBIGUOUS", ["Empty query text"]

        # Check explicit negative keywords
        negatives = [kw.lower().strip() for kw in self.context.get("negative_keywords", []) if kw.strip()]
        matched_negatives = [kw for kw in negatives if re.search(r'\b' + re.escape(kw) + r'\b', query_lower)]
        
        if matched_negatives:
            signals.append(f"Contains negative keywords: {', '.join(matched_negatives)}")
            return "IRRELEVANT", signals

        # Check user configured irrelevant phrases
        user_irrelevant = [p.lower().strip() for p in self.context.get("irrelevant_intents", []) if p.strip()]
        matched_user_irr = [p for p in user_irrelevant if p in query_lower]
        if matched_user_irr:
            signals.append(f"Matches specified irrelevant intent: {', '.join(matched_user_irr)}")
            return "IRRELEVANT", signals

        # Check user configured relevant phrases
        user_relevant = [p.lower().strip() for p in self.context.get("relevant_intents", []) if p.strip()]
        matched_user_rel = [p for p in user_relevant if p in query_lower]

        # Commercial high-intent buying signals
        commercial_terms = ["buy", "order", "price", "cost", "sale", "discount", "best", "store", "shop", "deal", "near me", "service", "bootcamp", "certification"]
        matched_commercial = [kw for kw in commercial_terms if re.search(r'\b' + re.escape(kw) + r'\b', query_lower)]

        if matched_user_rel:
            signals.append(f"Matches explicit target intent: {', '.join(matched_user_rel)}")
            return "RELEVANT", signals

        if matched_commercial:
            signals.append(f"Contains strong commercial intent terms: {', '.join(matched_commercial)}")
            return "RELEVANT", signals

        # Informational / non-commercial intent indicators
        info_terms = ["how to", "what is", "vs", "comparison", "definition", "symptoms", "history", "roadmap", "tips"]
        matched_info = [kw for kw in info_terms if kw in query_lower]
        if matched_info:
            signals.append(f"Contains informational/research intent: {', '.join(matched_info)}")
            return "AMBIGUOUS", signals

        signals.append("No explicit commercial or negative keywords detected")
        return "AMBIGUOUS", signals

    def evaluate_row(self, row):
        """
        Evaluates a single standardized dataframe row.
        Returns dict with decision, confidence, explanation, recommended_action, review_required.
        """
        query = str(row.get("query_text", "")).strip()
        campaign = str(row.get("campaign", ""))
        ad_group = str(row.get("ad_group", ""))
        
        impressions = row.get("impressions")
        clicks = row.get("clicks")
        cost = row.get("cost")
        conversions = row.get("conversions")
        conv_value = row.get("conversion_value")

        # 1. Check for missing or invalid query text
        if not query or query.lower() == "nan":
            return {
                "decision": "HUMAN REVIEW",
                "confidence": "LOW",
                "explanation": "Query text is missing or invalid.",
                "recommended_action": "Verify source data for empty query entries.",
                "review_required": True,
                "uncertainty_reason": "Missing required text data",
                "evidence_summary": "Query: [Empty]"
            }

        # 2. Track metrics availability
        available_metrics = []
        if clicks is not None: available_metrics.append("clicks")
        if cost is not None: available_metrics.append("cost")
        if conversions is not None: available_metrics.append("conversions")
        if conv_value is not None: available_metrics.append("conversion_value")

        # 3. Assess Text Relevance
        relevance_category, relevance_signals = self._assess_relevance(query, campaign, ad_group)

        min_clicks = self.context.get("min_clicks_threshold", 10)
        min_cost = self.context.get("min_cost_threshold", 15.0)

        # Handle metrics evidence
        has_metrics = ("clicks" in available_metrics and "cost" in available_metrics)
        clicks_val = clicks if clicks is not None else 0
        cost_val = cost if cost is not None else 0.0
        conv_val = conversions if conversions is not None else 0
        conv_val_val = conv_value if conv_value is not None else 0.0


        # DECISION TREE LOGIC
        
        # RULE 1: Clear Irrelevant Intent (High Confidence Block)
        if relevance_category == "IRRELEVANT":
            expl = f"Query contains non-commercial or negative keywords ({'; '.join(relevance_signals)})."
            if has_metrics and cost_val > 0:
                expl += f" Wasted spend to date: ${cost_val:.2f} across {clicks_val} clicks."
            
            return {
                "decision": "BLOCK",
                "confidence": "HIGH",
                "explanation": expl,
                "recommended_action": "Add term as a negative keyword to prevent wasteful spending.",
                "review_required": False,
                "uncertainty_reason": "None",
                "evidence_summary": f"Relevance: Irrelevant | Spend: ${cost_val:.2f} | Clicks: {clicks_val}"
            }

        # RULE 2: High Performance & Relevant Intent
        if relevance_category == "RELEVANT":
            if has_metrics and conv_val >= 1:
                cpa = cost_val / conv_val if conv_val > 0 else 0
                roas = (conv_val_val / cost_val) if cost_val > 0 and conv_val_val > 0 else (1.0 if conv_val_val == 0 else 0)
                min_roas = self.context.get("roas_threshold", 1.0)
                
                # Check for low ROAS / unprofitable conversion evidence
                if cost_val > 0 and conv_val_val > 0 and roas < min_roas:
                    return {
                        "decision": "HUMAN REVIEW",
                        "confidence": "MEDIUM",
                        "explanation": f"Relevant commercial intent ({relevance_signals[0]}), but unprofitable ROAS ({roas:.2f}x < target {min_roas}x) on ${cost_val:.2f} spend.",
                        "recommended_action": "Route to reviewer to evaluate bid reduction or landing page profitability.",
                        "review_required": True,
                        "uncertainty_reason": "Low ROAS despite confirmed conversions",
                        "evidence_summary": f"Relevance: Relevant | Convs: {conv_val} | ROAS: {roas:.2f}x"
                    }

                cpa_str = f" (CPA: ${cpa:.2f})" if conv_val > 0 else ""
                roas_str = f" (ROAS: {roas:.2f}x)" if cost_val > 0 and conv_val_val > 0 else ""
                return {
                    "decision": "PROMOTE",
                    "confidence": "HIGH",
                    "explanation": f"Relevant query with confirmed conversions ({conv_val} convs, ${cost_val:.2f} spend){cpa_str}{roas_str}. {relevance_signals[0]}.",
                    "recommended_action": "Add as exact/phrase match keyword and increase budget allocation.",
                    "review_required": False,
                    "uncertainty_reason": "None",
                    "evidence_summary": f"Relevance: Relevant | Convs: {conv_val} | Spend: ${cost_val:.2f}"
                }

            elif has_metrics and clicks_val >= min_clicks and conv_val == 0 and cost_val >= min_cost:
                # High clicks/spend but 0 conversions despite relevant intent
                return {
                    "decision": "HUMAN REVIEW",
                    "confidence": "MEDIUM",
                    "explanation": f"Relevant commercial intent ({relevance_signals[0]}), but high spend (${cost_val:.2f} across {clicks_val} clicks) yielded zero conversions.",
                    "recommended_action": "Review landing page offer or check for high CPC / weak landing page alignment.",
                    "review_required": True,
                    "uncertainty_reason": "High spend without conversions despite commercial intent",
                    "evidence_summary": f"Relevance: Relevant | Spend: ${cost_val:.2f} | Clicks: {clicks_val} | Convs: 0"
                }
            elif has_metrics and clicks_val < min_clicks:
                return {
                    "decision": "IGNORE",
                    "confidence": "MEDIUM",
                    "explanation": f"Relevant intent ({relevance_signals[0]}), but low volume data ({clicks_val} clicks, ${cost_val:.2f} cost) - insufficient statistical volume.",
                    "recommended_action": "Continue monitoring performance until click volume threshold is met.",
                    "review_required": False,
                    "uncertainty_reason": "Low volume / insufficient data",
                    "evidence_summary": f"Relevance: Relevant | Low volume ({clicks_val} clicks)"
                }
            else:
                # Relevant but missing performance metrics
                return {
                    "decision": "PROMOTE",
                    "confidence": "MEDIUM",
                    "explanation": f"Relevant commercial search intent detected ({relevance_signals[0]}). Detailed performance metrics unavailable.",
                    "recommended_action": "Consider targeting as keyword based on intent alignment.",
                    "review_required": False,
                    "uncertainty_reason": "Missing detailed performance metrics",
                    "evidence_summary": f"Relevance: Relevant | Metrics: Insufficient"
                }

        # RULE 3: Ambiguous Query Handling
        if relevance_category == "AMBIGUOUS":
            if has_metrics and conv_val >= 2 and cost_val > 0:
                # Ambiguous text but proven strong performance evidence
                return {
                    "decision": "PROMOTE",
                    "confidence": "MEDIUM",
                    "explanation": f"Ambiguous query intent, but proven performance evidence with {conv_val} conversions (${conv_val_val:.2f} value) on ${cost_val:.2f} spend.",
                    "recommended_action": "Promote keyword due to strong historical conversion performance.",
                    "review_required": False,
                    "uncertainty_reason": "Ambiguous intent overridden by strong performance",
                    "evidence_summary": f"Relevance: Ambiguous | Convs: {conv_val} | Spend: ${cost_val:.2f}"
                }
            elif has_metrics and cost_val > min_cost and conv_val == 0:
                # Ambiguous text with high unproductive spend -> Block or Human Review
                return {
                    "decision": "BLOCK",
                    "confidence": "MEDIUM",
                    "explanation": f"Ambiguous query with zero conversions after significant spend (${cost_val:.2f}, {clicks_val} clicks).",
                    "recommended_action": "Add as negative keyword to eliminate unrewarded ad spend.",
                    "review_required": False,
                    "uncertainty_reason": "None",
                    "evidence_summary": f"Relevance: Ambiguous | Spend: ${cost_val:.2f} | Convs: 0"
                }
            elif not has_metrics or clicks_val == 0:
                return {
                    "decision": "IGNORE",
                    "confidence": "LOW",
                    "explanation": f"Ambiguous query text with zero or minimal traffic ({clicks_val} clicks). No immediate action justified.",
                    "recommended_action": "No action required. Monitor for future traffic trends.",
                    "review_required": False,
                    "uncertainty_reason": "Low volume + ambiguous text",
                    "evidence_summary": "Relevance: Ambiguous | Clicks: 0"
                }
            else:
                # Classic Human Review candidate
                return {
                    "decision": "HUMAN REVIEW",
                    "confidence": "LOW",
                    "explanation": f"Ambiguous intent ({relevance_signals[0]}). Moderate spend (${cost_val:.2f}, {clicks_val} clicks) without conclusive ROI.",
                    "recommended_action": "Route to human reviewer to verify business intent alignment.",
                    "review_required": True,
                    "uncertainty_reason": "Ambiguous business relevance and inconclusive performance metrics",
                    "evidence_summary": f"Relevance: Ambiguous | Clicks: {clicks_val} | Cost: ${cost_val:.2f}"
                }

        # Fallback safety rule
        return {
            "decision": "HUMAN REVIEW",
            "confidence": "LOW",
            "explanation": "Unclassified search term pattern outside safe automated rules.",
            "recommended_action": "Manual inspection required by PPC specialist.",
            "review_required": True,
            "uncertainty_reason": "Unclassified edge case",
            "evidence_summary": "Metrics/Text outside rule bounds"
        }

    def process_records(self, records):
        """
        Processes a list of record dictionaries.
        Returns enriched list of dict records.
        """
        output_records = []
        for rec in records:
            eval_res = self.evaluate_row(rec)
            merged = {**rec, **eval_res}
            output_records.append(merged)
        return output_records

    # Alias for backward compatibility
    def process_dataframe(self, records):
        return self.process_records(records)

