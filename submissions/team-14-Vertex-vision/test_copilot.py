import unittest
import pandas as pd
import numpy as np

from triage_engine.copilot import generate_copilot_response

class TestCopilot(unittest.TestCase):
    def setUp(self):
        self.res_df = pd.DataFrame([
            {
                "row_id": 1,
                "query_text": "business loan equipment",
                "decision": "PROMOTE",
                "confidence": "HIGH",
                "needs_review": False,
                "reason": "Sustained volume and low CPA",
                "clicks": 45,
                "cost": 300.0,
                "conversions": 5.0,
                "conversion_value": 2500.0,
                "cpa": 60.0,
                "proposed_bid": 4.50,
                "ci_lower": 0.04,
                "ci_upper": 0.22,
                "campaign": "Equipment Financing",
                "ad_group": "Loans",
                "match_type": "Exact",
                "supporting_evidence": "Consistent conversions",
                "counterevidence": "None",
                "next_action": "Promote as Exact Match keyword"
            },
            {
                "row_id": 6,
                "query_text": "equipment financing calculator",
                "decision": "IGNORE",
                "confidence": "MEDIUM",
                "needs_review": True,
                "reason": "1 conversion observed with 4 clicks",
                "clicks": 4,
                "cost": 45.0,
                "conversions": 1.0,
                "conversion_value": 200.0,
                "cpa": 45.0,
                "proposed_bid": 2.10,
                "ci_lower": 0.045,
                "ci_upper": 0.58,
                "campaign": "Equipment Financing",
                "ad_group": "Calculators",
                "match_type": "Broad",
                "supporting_evidence": "Recorded 1 conversion",
                "counterevidence": "Sample size too small (n=4)",
                "next_action": "Hold in human review queue"
            },
            {
                "row_id": 12,
                "query_text": "personal loans for bad credit",
                "decision": "BLOCK",
                "confidence": "HIGH",
                "needs_review": False,
                "reason": "Non-commercial consumer query matches negative policy",
                "clicks": 18,
                "cost": 120.0,
                "conversions": 0.0,
                "conversion_value": 0.0,
                "cpa": None,
                "proposed_bid": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.15,
                "campaign": "General",
                "ad_group": "Loans",
                "match_type": "Broad",
                "supporting_evidence": "Matches consumer exclusion",
                "counterevidence": "None",
                "next_action": "Add to negative keywords"
            }
        ])
        
        self.clean_df = self.res_df.copy()

    def test_row_lookup_row_6(self):
        resp = generate_copilot_response("Audit row #6", self.res_df, self.clean_df, 220.0)
        self.assertIn("equipment financing calculator", resp)
        self.assertIn("Row #6", resp)
        self.assertIn("needs_review = True", resp)
        self.assertIn("Small-Sample Guardrail", resp)

    def test_row_lookup_plain_number(self):
        resp = generate_copilot_response("1", self.res_df, self.clean_df, 220.0)
        self.assertIn("business loan equipment", resp)
        self.assertIn("Row #1", resp)
        self.assertIn("PROMOTE", resp)

    def test_savings_calculation(self):
        resp = generate_copilot_response("How much money can we save?", self.res_df, self.clean_df, 220.0)
        self.assertIn("$120.00", resp)
        self.assertIn("Media Waste Reduction", resp)

    def test_small_sample_noise_explanation(self):
        resp = generate_copilot_response("Why is 1 conversion quarantined?", self.res_df, self.clean_df, 220.0)
        self.assertIn("Small-Sample Variance Trap", resp)
        self.assertIn("Wilson Confidence Bound", resp)

    def test_kestrel_boundaries(self):
        resp = generate_copilot_response("What are Kestrel exclusion boundaries?", self.res_df, self.clean_df, 220.0)
        self.assertIn("Kestrel Business Funding", resp)
        self.assertIn("Consumer Loans", resp)

    def test_top_promoted_candidates(self):
        resp = generate_copilot_response("Show top promoted keywords", self.res_df, self.clean_df, 220.0)
        self.assertIn("business loan equipment", resp)

    def test_methodology_explanation(self):
        resp = generate_copilot_response("How does the decision engine work?", self.res_df, self.clean_df, 220.0)
        self.assertIn("Wilson Binomial", resp)
        self.assertIn("PROMOTE", resp)

if __name__ == "__main__":
    unittest.main()
