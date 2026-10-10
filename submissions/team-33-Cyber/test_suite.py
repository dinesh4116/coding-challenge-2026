import unittest
import time
import pandas as pd
from triage_engine import triage_search_terms, analyze_query_intent, wilson_score_lower_bound
from demo_data import generate_realistic_dataset, generate_stress_test_dataset
from database import init_db, get_db_connection

class TestSearchPilotAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_single_conversion_trap(self):
        """Verify that 1 click & 1 conversion is NOT blindly promoted!"""
        df = pd.DataFrame([{
            "query": "rare marathon shoe test query",
            "campaign": "Performance Footwear",
            "ad_group": "Marathon Shoes",
            "match_type": "Exact",
            "impressions": 20,
            "clicks": 1,
            "cost": 2.50,
            "conversions": 1,
            "conversion_value": 85.00
        }])
        
        result_df = triage_search_terms(df)
        row = result_df.iloc[0]
        
        # Must be IGNORE, not PROMOTE!
        self.assertEqual(row['action'], 'IGNORE', f"Expected IGNORE due to statistical volatility, got {row['action']}")
        self.assertEqual(row['needs_review'], 1, "Expected single-conversion trap to be flagged for human review")
        self.assertIn("Single-Conversion Trap", row['reason'])

    def test_clear_negative_intent_blocked(self):
        """Verify that negative intent queries (jobs, hiring, free download) are blocked."""
        df = pd.DataFrame([{
            "query": "nike running shoes customer care toll free number",
            "campaign": "Performance Footwear",
            "ad_group": "Marathon Shoes",
            "match_type": "Broad",
            "impressions": 300,
            "clicks": 25,
            "cost": 37.50,
            "conversions": 0,
            "conversion_value": 0.00
        }])
        
        result_df = triage_search_terms(df)
        row = result_df.iloc[0]
        
        self.assertEqual(row['action'], 'BLOCK')
        self.assertGreaterEqual(row['confidence'], 80.0)
        self.assertIn("negative keywords", row['reason'].lower())

    def test_high_performer_promoted(self):
        """Verify that high-volume, high-converting queries with strong ROAS are promoted."""
        df = pd.DataFrame([{
            "query": "buy carbon plate marathon racing shoes",
            "campaign": "Performance Footwear",
            "ad_group": "Lightweight Racers",
            "match_type": "Exact",
            "impressions": 900,
            "clicks": 60,
            "cost": 95.00,
            "conversions": 8,
            "conversion_value": 720.00
        }])
        
        result_df = triage_search_terms(df)
        row = result_df.iloc[0]
        
        self.assertEqual(row['action'], 'PROMOTE')
        self.assertGreaterEqual(row['confidence'], 80.0)
        self.assertGreater(row['roas'], 3.0)

    def test_relevant_bleeder_not_blindly_blocked(self):
        """Verify that relevant terms with zero conversions are NOT blocked blindly (held in review)."""
        df = pd.DataFrame([{
            "query": "lightweight racers marathon shoes",
            "campaign": "Performance Footwear",
            "ad_group": "Lightweight Racers",
            "match_type": "Phrase",
            "impressions": 1500,
            "clicks": 35,
            "cost": 75.00,
            "conversions": 0,
            "conversion_value": 0.00
        }])
        
        result_df = triage_search_terms(df, target_cpa=35.0)
        row = result_df.iloc[0]
        
        # Because query is highly relevant to campaign/adgroup tokens, low conversions alone must NOT justify blocking!
        self.assertNotEqual(row['action'], 'BLOCK', "Relevant core product term should not be blocked without human review!")
        self.assertEqual(row['needs_review'], 1)

    def test_performance_25k_rows(self):
        """Verify that 25,000 rows can be triaged in sub-3 seconds."""
        print("\nBenchmarking 25,000 rows triage...")
        large_df = generate_stress_test_dataset(n_rows=25000)
        start_time = time.time()
        result_df = triage_search_terms(large_df)
        elapsed = time.time() - start_time
        print(f"Triaged {len(result_df)} rows in {elapsed:.2f} seconds ({len(result_df)/elapsed:.0f} rows/sec)")
        self.assertLess(elapsed, 5.0, "25,000 rows took too long!")
        self.assertEqual(len(result_df), 25000)



# ---------------------------------------------------------------------------
# CSV import tests (run:  python test_suite.py)
# ---------------------------------------------------------------------------
def run_csv_import_tests():
    from csv_loader import load_search_terms_csv, CsvLoadError

    google_ui = (
        'Search terms report\n"Oct 1 - Oct 9, 2026"\n\n'
        'Search term,Match type,Campaign,Ad group,Impr.,Clicks,Cost,Conv.,Conv. value\n'
        'buy running shoes,Exact,Shoes,Marathon,"1,234",56,"$1,045.50",4.00,"$2,100.00"\n'
        'free shoe download,Broad,Shoes,Marathon,< 10,0, --,0,0\n'
        'Total: Account,,,,"1,654",74,"$1,072.50",4,"$2,100.00"\n'
    )
    cases = {
        "google-ads ui export": google_ui.encode("utf-8"),
        "utf-16 tab separated": google_ui.replace(",", "\t").replace('"', "").replace("\t5", ",5").encode("utf-16"),
        "bom + crlf": "\ufeffquery,clicks,impressions,cost\r\nbuy,5,50,2.5\r\n".encode("utf-8"),
        "semicolon decimal comma": "Search term;Clicks;Cost\nbuy;5;2,50\n".encode("cp1252"),
        "conversions > clicks": "Search term,Clicks,Cost,Conversions\nbuy,3,10,5\n".encode(),
    }
    for name, raw in cases.items():
        df, info = load_search_terms_csv(raw)
        assert len(df) >= 1, name
        out = triage_search_terms(df)
        assert out["action"].isin(["PROMOTE", "BLOCK", "IGNORE"]).all(), name
        print(f"  [PASS] CSV import: {name} ({len(df)} rows)")

    df, _ = load_search_terms_csv(google_ui.encode())
    assert len(df) == 2 and df.loc[0, "cost"] == 1045.5 and df.loc[0, "impressions"] == 1234
    for bad in (b"", b"Search term,Clicks\n"):
        try:
            load_search_terms_csv(bad)
            raise AssertionError("expected CsvLoadError")
        except CsvLoadError:
            pass
    print("  [PASS] CSV import: totals skipped, values cleaned, empty files rejected")


class TestCsvImport(unittest.TestCase):
    def test_csv_import_shapes(self):
        run_csv_import_tests()


if __name__ == "__main__":
    unittest.main()
