"""
Automated Test Suite for the Three Optional PS-01 Enhancements (TriageIQ):
1. Context-Aware Negative Keyword Suggestions (Scope, Match Type, Risk Warnings).
2. Near-Duplicate Search-Intent Clustering (Conflict Detection, Qualifier Preservation).
3. Reviewer Precedents & Session-Level Learning (Guidance, Precedent Retrieval, Audit Trail).
"""

import unittest
import pandas as pd
import numpy as np

from triage_engine.rules import TriageEngine, AdvertiserProfile
from triage_engine.negatives import generate_context_aware_negative_suggestions, analyze_over_exclusion_risk
from triage_engine.clustering import cluster_search_queries
from triage_engine.learning import ReviewerPrecedentMemory, compute_query_similarity

class TestEnhancements(unittest.TestCase):

    def setUp(self):
        self.profile = AdvertiserProfile()
        self.engine = TriageEngine(
            target_cpa=220.0,
            min_clicks_for_promotion=10,
            min_conversions_for_promotion=2,
            advertiser_profile=self.profile
        )

    # =============================================================
    # ENHANCEMENT A: CONTEXT-AWARE NEGATIVE SUGGESTIONS
    # =============================================================
    def test_negative_suggestions_universal_trigger_campaign_scope(self):
        """
        Universal consumer terms ('personal loans') must receive Campaign-level Negative Phrase scope.
        """
        res_df = pd.DataFrame([{
            "row_id": 1,
            "query_text": "instant personal loans bad credit",
            "campaign": "General Commercial Lending",
            "ad_group": "Fast Cash",
            "decision": "BLOCK",
            "confidence": "HIGH",
            "needs_review": False,
            "clicks": 14,
            "cost": 150.0,
            "conversions": 0.0,
            "ci_upper": 0.12,
            "reason": "Matches exclusion trigger 'personal loans'"
        }])
        
        suggestions = generate_context_aware_negative_suggestions(res_df, self.profile, 220.0)
        self.assertGreater(len(suggestions), 0)
        sug = suggestions[0]
        self.assertEqual(sug["recommended_scope"], "Campaign")
        self.assertEqual(sug["recommended_match_type"], "Negative Phrase")
        self.assertIn("personal loan", sug["clean_keyword"].lower())
        self.assertIn("Violates Kestrel", sug["explanation"])
        self.assertEqual(sug["analyst_status"], "Pending Analyst Approval")

    def test_negative_suggestions_spend_bleeder_ad_group_scope(self):
        """
        Spend bleeders specific to an ad group must receive Ad Group-level Negative Exact scope
        under the Narrowest Appropriate Scope Rule.
        """
        res_df = pd.DataFrame([{
            "row_id": 2,
            "query_text": "semi truck commercial financing rates",
            "campaign": "Search | Equipment Finance",
            "ad_group": "Heavy Trucks",
            "decision": "BLOCK",
            "confidence": "HIGH",
            "needs_review": False,
            "clicks": 20,
            "cost": 350.0, # > 1.2x Target CPA ($264)
            "conversions": 0.0,
            "ci_upper": 0.08,
            "reason": "Spend bleeder exceeding allowable CPA"
        }])
        
        suggestions = generate_context_aware_negative_suggestions(res_df, self.profile, 220.0)
        self.assertGreater(len(suggestions), 0)
        sug = suggestions[0]
        self.assertEqual(sug["recommended_scope"], "Ad Group")
        self.assertEqual(sug["recommended_match_type"], "Negative Exact")
        self.assertEqual(sug["trigger_type"], "PERFORMANCE_BLEEDER")
        self.assertIn("Ad Group Negative Exact", sug["explanation"])
        self.assertEqual(sug["risk_level"], "LOW")

    def test_over_exclusion_risk_warning(self):
        """
        Single-word phrases or colliding commercial tokens must trigger risk warnings.
        """
        risk_level, warning = analyze_over_exclusion_risk("loan", "Negative Phrase", "Campaign")
        self.assertIn("Critical", warning)
        self.assertEqual(risk_level, "CRITICAL")
        
        risk_level, warning = analyze_over_exclusion_risk("semi truck financing", "Negative Exact", "Ad Group")
        self.assertEqual(risk_level, "LOW")
        self.assertIn("Low Risk", warning)

    # =============================================================
    # ENHANCEMENT B: INTENT CLUSTERING & CONFLICT DETECTION
    # =============================================================
    def test_clustering_preserves_consumer_vs_business_distinction(self):
        """
        'personal loan fast' and 'business loan fast' must NEVER be grouped in the same cluster.
        """
        records = [
            {"query_text": "personal loan fast", "impressions": 50, "clicks": 5, "cost": 25.0, "conversions": 0, "decision": "BLOCK"},
            {"query_text": "business loan fast", "impressions": 80, "clicks": 8, "cost": 40.0, "conversions": 1, "decision": "IGNORE"}
        ]
        clusters, updated = cluster_search_queries(records)
        self.assertEqual(len(clusters), 2, "Personal loans and business loans must remain in distinct clusters!")
        self.assertNotEqual(updated[0]["cluster_id"], updated[1]["cluster_id"])

    def test_clustering_decision_conflict_detection(self):
        """
        When member queries have divergent decisions, the cluster must flag has_conflict=True.
        """
        records = [
            {
                "row_id": 10,
                "query_text": "equipment financing fast online",
                "impressions": 100, "clicks": 15, "cost": 120.0, "conversions": 3,
                "decision": "PROMOTE", "needs_review": False
            },
            {
                "row_id": 11,
                "query_text": "fast online equipment financing",
                "impressions": 20, "clicks": 2, "cost": 15.0, "conversions": 0,
                "decision": "IGNORE", "needs_review": False
            }
        ]
        clusters, _ = cluster_search_queries(records)
        self.assertEqual(len(clusters), 1, "Syntactic variations must collapse into 1 cluster.")
        c = clusters[0]
        self.assertTrue(c["has_conflict"], "Must flag decision conflict between PROMOTE and IGNORE!")
        self.assertIn("MIXED_DECISIONS", c["conflict_type"])
        self.assertIn("PROMOTE", c["conflict_type"])
        self.assertIn("IGNORE", c["conflict_type"])
        self.assertIn("Decision Conflict", c["conflict_explanation"])
        self.assertEqual(len(c["member_queries"]), 2)

    # =============================================================
    # ENHANCEMENT C: REVIEWER PRECEDENTS & SESSION LEARNING
    # =============================================================
    def test_precedent_recording_and_retrieval(self):
        """
        Reviewer corrections must be stored, searchable, and surfaced as contextual precedents.
        """
        memory = ReviewerPrecedentMemory()
        
        # Record a past analyst correction
        memory.record_correction(
            query_text="dental practice equipment financing",
            original_decision="IGNORE",
            revised_decision="PROMOTE",
            campaign="Search | Equipment Finance",
            ad_group="Medical Equipment",
            reviewer_reason="High margin dental financing verified with underwriting",
            reviewer_name="Senior_Analyst"
        )
        
        # Unreviewed query arrives with similar tokens
        precedent = memory.find_best_precedent(
            target_query="dental office equipment financing",
            target_campaign="Search | Equipment Finance"
        )
        
        self.assertIsNotNone(precedent)
        self.assertTrue(precedent["has_precedent"])
        self.assertEqual(precedent["precedent_query"], "dental practice equipment financing")
        self.assertEqual(precedent["original_decision"], "IGNORE")
        self.assertEqual(precedent["revised_decision"], "PROMOTE")
        self.assertIn("High margin dental financing", precedent["reviewer_reason"])
        self.assertGreaterEqual(precedent["similarity"], 0.50)
        self.assertIn("Contextual Precedent", precedent["guidance_explanation"])

    def test_corrections_log_export(self):
        """
        Reviewer corrections must export to DataFrame cleanly.
        """
        memory = ReviewerPrecedentMemory()
        memory.record_correction(
            query_text="small business working capital loan",
            original_decision="IGNORE",
            revised_decision="PROMOTE",
            campaign="Search | Working Capital",
            ad_group="General",
            reviewer_reason="Core B2B target product",
            reviewer_name="Analyst_1"
        )
        
        df = memory.export_to_dataframe()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["Original Engine Decision"], "IGNORE")
        self.assertEqual(df.iloc[0]["Reviewer Revised Decision"], "PROMOTE")
        self.assertEqual(df.iloc[0]["Query"], "small business working capital loan")

if __name__ == "__main__":
    unittest.main()
