"""
Automated Test Suite for TriageIQ Decision Engine and Evidence Policy.

Validates all 8 organizer-required test scenarios plus clustering and feedback:
1. One click and one conversion (The Classic Trap).
2. Two clicks and one conversion.
3. Zero clicks and zero conversions.
4. Clearly unsupported product query (Business constraint).
5. Relevant query with sufficient evidence and strong performance.
6. Relevant query with sufficient evidence and poor performance (Spend bleeder).
7. High-cost query with insufficient evidence (Borderline underpowered).
8. Missing or invalid numeric fields (Robustness).
9. Intent clustering near-duplicates vs distinct intent.
10. Reviewer feedback recording and session learning.
11. Output contract compliance (strictly PROMOTE, BLOCK, IGNORE, needs_review boolean).
"""

import unittest
from triage_engine.rules import TriageEngine, AdvertiserProfile
from triage_engine.stats import wilson_score_interval, empirical_bayes_cvr, calculate_derived_metrics
from triage_engine.clustering import cluster_search_queries
from run_cli import normalize_input_data
import pandas as pd
import numpy as np

class TestTriageEngine(unittest.TestCase):
    
    def setUp(self):
        self.profile = AdvertiserProfile()
        self.engine = TriageEngine(
            target_cpa=220.0,
            target_roas=3.0,
            min_clicks_for_promotion=10,
            min_conversions_for_promotion=2,
            advertiser_profile=self.profile
        )

    # -------------------------------------------------------------
    # 1. ONE CLICK AND ONE CONVERSION (The Specific Prompt Trap)
    # -------------------------------------------------------------
    def test_one_click_one_conversion_quarantined(self):
        """
        Query: 'apply business loan approval'
        Clicks: 1, Conversions: 1, Cost: $21.85, Raw CVR: 100%.
        Wilson 95% lower bound is ~20.7%, which is > 1.5%, BUT interval width is 79.3%.
        The evidence policy MUST reject promotion, set decision='IGNORE', and needs_review=True.
        """
        row = {
            "row_id": 6,
            "query_text": "apply business loan approval",
            "campaign": "Search | Generic Business Loans",
            "ad_group": "Startup Funding",
            "impressions": 15,
            "clicks": 1,
            "cost": 21.85,
            "conversions": 1,
            "conversion_value": 915.90
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "IGNORE", "1-click conversion must NOT be promoted!")
        self.assertTrue(res["needs_review"], "1-click conversion must be flagged for human review!")
        self.assertEqual(res["confidence"], "LOW")
        self.assertIn("Small-sample noise", res["reason"])
        self.assertIn("1 click(s)", res["reason"])
        self.assertGreater(res["ci_width"], 0.70)

    # -------------------------------------------------------------
    # 2. TWO CLICKS AND ONE CONVERSION
    # -------------------------------------------------------------
    def test_two_clicks_one_conversion_quarantined(self):
        """
        Query with 2 clicks and 1 conversion has raw CVR = 50%.
        Must not be promoted; routed to needs_review=True and decision='IGNORE'.
        """
        row = {
            "row_id": 101,
            "query_text": "instant revolving business line of credit",
            "campaign": "Search | Line of Credit",
            "ad_group": "Business Line of Credit",
            "impressions": 20,
            "clicks": 2,
            "cost": 42.00,
            "conversions": 1,
            "conversion_value": 500.00
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "IGNORE")
        self.assertTrue(res["needs_review"])
        self.assertEqual(res["confidence"], "LOW")
        self.assertIn("Small-sample noise", res["reason"])

    # -------------------------------------------------------------
    # 3. ZERO CLICKS AND ZERO CONVERSIONS (Dormant long-tail)
    # -------------------------------------------------------------
    def test_zero_clicks_zero_conversions_status_quo(self):
        """
        Query with 20 impressions, 0 clicks, $0.00 cost.
        Must be IGNORE with needs_review=False (status quo preserved, no keyword clutter).
        """
        row = {
            "row_id": 2,
            "query_text": "reliable sba loan requirements calculator",
            "campaign": "Search | SBA Loans",
            "ad_group": "SBA Loans",
            "impressions": 29,
            "clicks": 0,
            "cost": 0.0,
            "conversions": 0,
            "conversion_value": 0.0
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "IGNORE")
        self.assertFalse(res["needs_review"])
        self.assertEqual(res["confidence"], "HIGH")
        self.assertIn("Low volume/spend", res["reason"])

    # -------------------------------------------------------------
    # 4. CLEARLY UNSUPPORTED PRODUCT QUERY (Business constraint)
    # -------------------------------------------------------------
    def test_clearly_unsupported_product_blocked(self):
        """
        Kestrel does NOT sell personal loans, mortgages, student loans, car loans, or grants.
        Query 'personal loan for bad credit' with 0 conversions must be BLOCK at Campaign level.
        """
        row = {
            "row_id": 303,
            "query_text": "best personal loan bad credit same day",
            "campaign": "Search | Generic Business Loans",
            "ad_group": "Business Loans",
            "impressions": 120,
            "clicks": 8,
            "cost": 65.00,
            "conversions": 0,
            "conversion_value": 0.0
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["needs_review"])
        self.assertEqual(res["confidence"], "HIGH")
        self.assertEqual(res["action_level"], "Campaign")
        self.assertEqual(res["negative_type"], "Negative Phrase")
        self.assertIn("personal", res["reason"].lower())

    # -------------------------------------------------------------
    # 5. RELEVANT QUERY WITH SUFFICIENT EVIDENCE & STRONG PERFORMANCE
    # -------------------------------------------------------------
    def test_sufficient_evidence_strong_performance_promoted(self):
        """
        Query with 61 clicks, 4 conversions, $719.63 cost (CPA $179.91 <= $220.00 target).
        Wilson 95% lower bound is ~2.6% (> 1.5%), interval width is narrow (13.1%).
        Must be PROMOTE to Ad Group Exact Match with suggested CPC bid.
        """
        row = {
            "row_id": 3,
            "query_text": "instant revolving business credit new york",
            "campaign": "Search | Line of Credit",
            "ad_group": "Business Line of Credit",
            "impressions": 603,
            "clicks": 61,
            "cost": 719.63,
            "conversions": 4,
            "conversion_value": 6126.55
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "PROMOTE")
        self.assertFalse(res["needs_review"])
        self.assertEqual(res["confidence"], "HIGH")
        self.assertEqual(res["target_match_type"], "[instant revolving business credit new york]")
        self.assertEqual(res["action_level"], "Ad Group")
        self.assertGreater(res["proposed_bid"], 0.0)
        self.assertIn("High-evidence promotion candidate", res["reason"])

    # -------------------------------------------------------------
    # 6. RELEVANT QUERY WITH SUFFICIENT EVIDENCE & POOR PERFORMANCE
    # -------------------------------------------------------------
    def test_sufficient_evidence_poor_performance_blocked(self):
        """
        Spend bleeder: 40 clicks, $450 cost (> 1.5x target $220), 0 conversions.
        Wilson upper bound CVR < 8%. Must be BLOCK as Negative Exact.
        """
        row = {
            "row_id": 404,
            "query_text": "how to get a business loan with no revenue",
            "campaign": "Search | Generic Business Loans",
            "ad_group": "Business Loans",
            "impressions": 500,
            "clicks": 40,
            "cost": 450.00,
            "conversions": 0,
            "conversion_value": 0.0
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["needs_review"])
        self.assertEqual(res["confidence"], "HIGH")
        self.assertEqual(res["negative_type"], "Negative Exact")
        self.assertIn("Sustained spend bleeder", res["reason"])

    # -------------------------------------------------------------
    # 7. HIGH-COST QUERY WITH INSUFFICIENT EVIDENCE (Borderline spend)
    # -------------------------------------------------------------
    def test_borderline_spend_insufficient_evidence_routed_to_review(self):
        """
        Cost is $200 (between 0.8x and 1.5x target $220), but only 9 clicks and 0 conversions.
        Underpowered for automated block. Must be IGNORE with needs_review=True.
        """
        row = {
            "row_id": 505,
            "query_text": "working capital line for medical practice",
            "campaign": "Search | Working Capital",
            "ad_group": "Working Capital",
            "impressions": 80,
            "clicks": 9,
            "cost": 200.00,
            "conversions": 0,
            "conversion_value": 0.0
        }
        res = self.engine.evaluate_query(row)
        
        self.assertEqual(res["decision"], "IGNORE")
        self.assertTrue(res["needs_review"])
        self.assertEqual(res["confidence"], "MEDIUM")
        self.assertIn("Borderline spend", res["reason"])

    # -------------------------------------------------------------
    # 8. MISSING OR INVALID NUMERIC FIELDS (Robustness)
    # -------------------------------------------------------------
    def test_missing_or_invalid_numeric_fields_handled_safely(self):
        """
        Record with NaNs, negative numbers, or invalid strings should not crash the engine.
        """
        row = {
            "row_id": 606,
            "query_text": "equipment financing options",
            "campaign": "Search | Equipment Finance",
            "ad_group": "Equipment Finance",
            "impressions": "invalid_num",
            "clicks": None,
            "cost": -50.0,
            "conversions": np.nan,
            "conversion_value": "null"
        }
        res = self.engine.evaluate_query(row)
        
        self.assertIn(res["decision"], {"PROMOTE", "BLOCK", "IGNORE"})
        self.assertIsInstance(res["needs_review"], bool)
        self.assertEqual(res["clicks"], 0)
        self.assertEqual(res["cost"], 0.0)
        self.assertEqual(res["conversions"], 0.0)

    # -------------------------------------------------------------
    # 9. INTENT CLUSTERING: NEAR-DUPLICATES VS DISTINCT INTENT
    # -------------------------------------------------------------
    def test_clustering_near_duplicates_vs_distinct_intent(self):
        """
        'business loans online' and 'online business loan' should cluster together.
        'business loan alternatives' has a distinct qualifier and MUST NOT be in the same cluster!
        """
        records = [
            {"query_text": "business loans online", "impressions": 100, "clicks": 10, "cost": 50.0, "conversions": 1, "conversion_value": 100.0},
            {"query_text": "online business loan", "impressions": 80, "clicks": 8, "cost": 40.0, "conversions": 1, "conversion_value": 100.0},
            {"query_text": "business loan alternatives", "impressions": 50, "clicks": 5, "cost": 25.0, "conversions": 0, "conversion_value": 0.0}
        ]
        clusters, updated_records = cluster_search_queries(records)
        
        # There should be 2 clusters, NOT 1!
        self.assertEqual(len(clusters), 2, "Distinct qualifier 'alternatives' must not be merged with generic query!")
        
        # Verify row-level traceability
        self.assertIn("cluster_id", updated_records[0])
        self.assertEqual(updated_records[0]["cluster_id"], updated_records[1]["cluster_id"])
        self.assertNotEqual(updated_records[0]["cluster_id"], updated_records[2]["cluster_id"])

    # -------------------------------------------------------------
    # 10. REVIEWER FEEDBACK & SESSION MEMORY PRESERVATION
    # -------------------------------------------------------------
    def test_reviewer_override_records_original_and_final_decision(self):
        """
        When analyst overrides an item, original_decision is preserved in audit trail,
        decision becomes the reviewer choice, and needs_review is cleared.
        """
        row = {
            "row_id": 707,
            "query_text": "niche dental equipment lease",
            "campaign": "Search | Equipment Finance",
            "ad_group": "Medical Equipment",
            "impressions": 12,
            "clicks": 2,
            "cost": 40.0,
            "conversions": 1,
            "conversion_value": 800.0
        }
        # Pre-review evaluation
        pre = self.engine.evaluate_query(row)
        self.assertEqual(pre["decision"], "IGNORE")
        self.assertTrue(pre["needs_review"])
        self.assertEqual(pre["original_decision"], "IGNORE")
        
        # Analyst approves promotion
        self.engine.register_human_correction(
            query="niche dental equipment lease",
            action="APPROVED_PROMOTION",
            decision="PROMOTE",
            notes="High margin medical equipment line confirmed by senior underwriter",
            reviewer="Lead_Underwriter"
        )
        
        # Post-review evaluation
        post = self.engine.evaluate_query(row)
        self.assertEqual(post["decision"], "PROMOTE")
        self.assertFalse(post["needs_review"])
        self.assertEqual(post["original_decision"], "IGNORE", "Must preserve pre-review recommendation!")
        self.assertEqual(post["reviewer_action"], "APPROVED_PROMOTION")
        self.assertIn("Lead_Underwriter", post["reason"])

    # -------------------------------------------------------------
    # 11. OUTPUT CONTRACT VERIFICATION
    # -------------------------------------------------------------
    def test_output_contract_fields_presence(self):
        """
        Verifies that every required contract field is present on output.
        """
        row = {
            "row_id": 1,
            "query_text": "instant invoice template reviews",
            "campaign": "Search | Generic Business Loans",
            "ad_group": "Business Loans",
            "impressions": 21,
            "clicks": 2,
            "cost": 13.7,
            "conversions": 0,
            "conversion_value": 0.0
        }
        res = self.engine.evaluate_query(row)
        
        required_fields = [
            "row_id", "query_text", "campaign", "ad_group", "decision", "confidence",
            "needs_review", "reason", "supporting_evidence", "counterevidence",
            "next_action", "original_decision"
        ]
        for field in required_fields:
            self.assertIn(field, res, f"Field '{field}' missing from decision contract!")
            
        self.assertIn(res["decision"], {"PROMOTE", "BLOCK", "IGNORE"})
        self.assertIsInstance(res["needs_review"], bool)

if __name__ == "__main__":
    unittest.main()
