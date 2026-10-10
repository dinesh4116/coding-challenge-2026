"""
AdCreative Intelligence - Pipeline Test Suite
Comprehensive unit tests covering:
1. Image feature extraction (color, palette distribution, brightness, contrast, dimensions,
   aspect ratio, composition features, pretrained Haar cascade face detection, text proxy, error status)
2. CSV validation (missing columns, missing data, duplicates, negative/invalid values, impossible ratios)
3. Image-to-ad matching (stem normalization, missing images, missing CSV records, zero silent discards)
4. Metric calculations (ad-level & pooled aggregate CTR, CVR, CPC, CPA, zero denominators)
5. Statistical comparisons (categorical & continuous, multiple testing FDR, 10 required finding fields)
6. Small sample sizes (Underpowered & Not estimable classifications)
7. Dynamic Creative Brief integration (zero hardcoded analytical results).
"""

import io
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from data_ingestion import (
    validate_and_parse_csv,
    match_images_to_records,
    ingest_ad_dataset,
    compute_derived_metrics,
    safe_divide,
    generate_example_csv_content,
)
from feature_extraction import (
    extract_features_from_image,
    batch_extract_features,
    classify_dominant_color,
    categorize_aspect_ratio,
    compute_hasler_susstrunk_colorfulness,
)
from statistical_engine import (
    run_full_statistical_analysis,
    analyze_categorical_attribute,
    analyze_continuous_attribute,
    apply_multiple_testing_correction,
    rank_findings,
    compute_aggregate_kpis,
    compute_proportion_difference_ci,
    compute_cohens_d,
    classify_evidence,
    investigate_confounding,
)
from synthetic_data import generate_synthetic_dataset
from creative_brief import generate_creative_brief


class TestDataIngestionAndMatching(unittest.TestCase):
    def test_example_csv_generation(self):
        csv_str = generate_example_csv_content()
        self.assertIn("ad_id", csv_str)
        self.assertIn("spend", csv_str)
        df, errors, warnings = validate_and_parse_csv(csv_str.encode("utf-8"))
        self.assertEqual(len(errors), 0)
        self.assertGreater(len(df), 5)
        self.assertIn("ctr", df.columns)
        self.assertIn("cvr", df.columns)
        self.assertIn("cpc", df.columns)
        self.assertIn("cpa", df.columns)

    def test_missing_required_columns(self):
        bad_csv = "ad_id,spend,clicks\nad_1,100,5"
        df, errors, warnings = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("Missing required column" in e for e in errors))

    def test_missing_data_and_non_numeric_values(self):
        bad_csv = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,100,1000,,5\n"
            ",200,2000,50,5\n"
            "ad_3,abc,2000,50,5\n"
        )
        df, errors, warnings = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("ad_id" in e for e in errors))
        self.assertTrue(any("clicks" in e for e in errors))
        self.assertTrue(any("spend" in e for e in errors))

    def test_duplicate_ad_ids(self):
        bad_csv = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,100,1000,50,5\n"
            "ad_1,200,2000,80,8\n"
        )
        df, errors, warnings = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("duplicate" in e.lower() for e in errors))

    def test_negative_metrics_rejection(self):
        bad_csv = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,-50,1000,50,5\n"
        )
        df, errors, warnings = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("negative" in e.lower() for e in errors))

    def test_impossible_metric_ratios(self):
        # Clicks > impressions
        bad_csv_1 = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,50,100,200,5\n"
        )
        df1, errors1, _ = validate_and_parse_csv(bad_csv_1.encode("utf-8"))
        self.assertIsNone(df1)
        self.assertTrue(any("exceeding impressions" in e.lower() for e in errors1))

        # Conversions > clicks
        bad_csv_2 = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,50,1000,10,25\n"
        )
        df2, errors2, _ = validate_and_parse_csv(bad_csv_2.encode("utf-8"))
        self.assertIsNone(df2)
        self.assertTrue(any("conversions exceeding clicks" in e.lower() for e in errors2))

    def test_zero_denominators_and_warnings_preserved(self):
        csv_data = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_zero_imp,0,0,0,0\n"
            "ad_zero_clk,50,5000,0,0\n"
            "ad_zero_cnv,100,10000,200,0\n"
            "ad_valid,100,10000,200,10\n"
        )
        df, errors, warnings = validate_and_parse_csv(csv_data.encode("utf-8"))
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(df)
        # Never silently discard records with 0 denominators
        self.assertEqual(len(df), 4)
        self.assertTrue(any("0 impressions" in w for w in warnings))
        self.assertTrue(any("0 clicks" in w for w in warnings))
        self.assertTrue(any("0 conversions" in w for w in warnings))

        zero_row = df[df["ad_id"] == "ad_zero_imp"].iloc[0]
        self.assertTrue(np.isnan(zero_row["ctr"]))
        self.assertTrue(np.isnan(zero_row["cvr"]))
        self.assertTrue(np.isnan(zero_row["cpc"]))
        self.assertTrue(np.isnan(zero_row["cpa"]))

        zero_cnv_row = df[df["ad_id"] == "ad_zero_cnv"].iloc[0]
        self.assertAlmostEqual(zero_cnv_row["ctr"], 0.02)
        self.assertEqual(zero_cnv_row["cvr"], 0.0)
        self.assertAlmostEqual(zero_cnv_row["cpc"], 0.50)
        self.assertTrue(np.isnan(zero_cnv_row["cpa"]))

        self.assertIsNone(safe_divide(10, 0))
        self.assertIsNone(safe_divide(10, None))
        self.assertEqual(safe_divide(10, 2), 5.0)

    def test_image_matching_and_unmatched_audit(self):
        csv_data = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "AD_01,100,1000,20,2\n"
            "ad_02,100,1000,20,2\n"
            "ad_missing_img,100,1000,20,2\n"
        )
        images = {
            "ad_01.png": Image.new("RGB", (100, 100), color=(200, 50, 50)),
            "AD_02.JPEG": Image.new("RGB", (100, 100), color=(50, 50, 200)),
            "ad_orphan.png": Image.new("RGB", (100, 100), color=(50, 200, 50)),
        }
        res = ingest_ad_dataset(csv_data.encode("utf-8"), images)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.df), 3)  # No records silently dropped
        self.assertEqual(len(res.matched_images), 2)
        self.assertIn("AD_01", res.matched_images)
        self.assertIn("ad_02", res.matched_images)
        self.assertEqual(res.unmatched_records, ["ad_missing_img"])
        self.assertEqual(res.unmatched_images, ["ad_orphan.png"])


class TestAggregatePerformanceMetrics(unittest.TestCase):
    def test_pooled_aggregate_metrics_vs_naive_average(self):
        # Ad 1: 1,000 imp, 100 clicks (10% CTR)
        # Ad 2: 99,000 imp, 900 clicks (0.91% CTR)
        # Pooled CTR = 1,000 / 100,000 = 0.01 (1.0%), NOT naive average (5.45%)
        df = pd.DataFrame({
            "ad_id": ["ad_small", "ad_large"],
            "spend": [100.0, 900.0],
            "impressions": [1000, 99000],
            "clicks": [100, 900],
            "conversions": [10, 40],
        })
        df = compute_derived_metrics(df)
        kpis = compute_aggregate_kpis(df)
        self.assertAlmostEqual(kpis["aggregate_ctr"], 1000 / 100000)
        self.assertAlmostEqual(kpis["aggregate_cvr"], 50 / 1000)
        self.assertAlmostEqual(kpis["aggregate_cpc"], 1000.0 / 1000)
        self.assertAlmostEqual(kpis["aggregate_cpa"], 1000.0 / 50)
        self.assertNotAlmostEqual(kpis["aggregate_ctr"], df["ctr"].mean())

    def test_aggregate_metrics_zero_denominators(self):
        df = pd.DataFrame({
            "ad_id": ["ad_1"],
            "spend": [100.0],
            "impressions": [0],
            "clicks": [0],
            "conversions": [0],
        })
        kpis = compute_aggregate_kpis(df)
        self.assertIsNone(kpis["aggregate_ctr"])
        self.assertIsNone(kpis["aggregate_cvr"])
        self.assertIsNone(kpis["aggregate_cpc"])
        self.assertIsNone(kpis["aggregate_cpa"])


class TestFeatureExtraction(unittest.TestCase):
    def test_dominant_color_classification(self):
        name, _, tone = classify_dominant_color((255, 0, 0))
        self.assertEqual(name, "Red")
        self.assertEqual(tone, "Warm")

        name, _, tone = classify_dominant_color((0, 0, 255))
        self.assertEqual(name, "Blue")
        self.assertEqual(tone, "Cool")

        name, _, tone = classify_dominant_color((250, 250, 250))
        self.assertEqual(name, "White")
        self.assertEqual(tone, "Neutral")

    def test_aspect_ratio_categorization(self):
        self.assertEqual(categorize_aspect_ratio(1.0), "1:1 Square")
        self.assertEqual(categorize_aspect_ratio(0.5625), "9:16 Portrait / Story")
        self.assertEqual(categorize_aspect_ratio(1.777), "16:9 Landscape")

    def test_feature_extraction_completeness_and_composition(self):
        test_img = Image.new("RGB", (300, 300), color=(220, 50, 50))
        feats = extract_features_from_image(test_img, use_cache=False)

        required_keys = [
            "image_hash", "width", "height", "aspect_ratio", "aspect_ratio_cat",
            "dominant_color_name", "dominant_color_hex", "dominant_color_tone",
            "color_palette_distribution", "brightness_score", "brightness_cat",
            "contrast_score", "contrast_cat", "colorfulness_score", "colorfulness_cat",
            "visual_complexity", "rule_of_thirds_score", "center_focus_ratio",
            "visual_symmetry_score", "composition_style", "detected_object_regions",
            "face_count", "has_human_presence", "human_presence_cat",
            "text_density_score", "text_density_cat", "extraction_status",
            "extraction_error", "feature_sources",
        ]
        for k in required_keys:
            self.assertIn(k, feats, f"Missing key {k} in feature extraction output")

        self.assertEqual(feats["extraction_status"], "success")
        self.assertIsNone(feats["extraction_error"])
        self.assertEqual(feats["width"], 300)
        self.assertEqual(feats["height"], 300)
        self.assertEqual(feats["aspect_ratio_cat"], "1:1 Square")
        self.assertEqual(feats["dominant_color_tone"], "Warm")
        self.assertIsInstance(feats["color_palette_distribution"], list)

    def test_corrupted_image_error_status(self):
        feats = extract_features_from_image(b"not_a_valid_image_byte_stream", use_cache=False)
        self.assertEqual(feats["extraction_status"], "error")
        self.assertIsNotNone(feats["extraction_error"])


class TestStatisticalEngineAndFindings(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 16
        data = {
            "ad_id": [f"ad_{i:02d}" for i in range(n)],
            "impressions": [20000 + i * 1000 for i in range(n)],
            "spend": [400 + i * 20 for i in range(n)],
            "dominant_color_tone": ["Warm"] * 8 + ["Cool"] * 8,
            "human_presence_cat": ["With Human"] * 8 + ["No Human"] * 8,
            "brightness_cat": ["High Brightness (>65)"] * 8 + ["Low Brightness (<35)"] * 8,
            "brightness_score": [75.0 + i for i in range(8)] + [30.0 + i for i in range(8)],
            "contrast_score": [60.0 + i for i in range(8)] + [40.0 + i for i in range(8)],
            "colorfulness_score": [65.0 + i for i in range(8)] + [30.0 + i for i in range(8)],
            "saturation_score": [60.0 + i for i in range(8)] + [30.0 + i for i in range(8)],
            "edge_density_pct": [6.0 + (i * 0.2) for i in range(n)],
            "text_density_score": [15.0 + (i * 0.5) for i in range(n)],
            "aspect_ratio": [1.0] * n,
            "aspect_ratio_cat": ["1:1 Square"] * n,
            "contrast_cat": ["High Contrast (>65)"] * 8 + ["Low Contrast (<40)"] * 8,
            "visual_complexity": ["Clean / Minimal"] * n,
            "text_density_cat": ["Minimal Copy"] * n,
            "colorfulness_cat": ["Highly Vibrant"] * 8 + ["Subdued / Monochromatic"] * 8,
            "composition_style": ["Centered Hero"] * 8 + ["Rule-of-Thirds Dynamic"] * 8,
            "object_presence_cat": ["Clear Foreground Subject"] * 8 + ["Ambient / Minimal Foreground"] * 8,
            "rule_of_thirds_score": [45.0 + i for i in range(n)],
            "center_focus_ratio": [65.0 - i for i in range(n)],
            "visual_symmetry_score": [70.0 + (i % 5) for i in range(n)],
        }
        df = pd.DataFrame(data)
        clicks = []
        convs = []
        for i in range(n):
            imp = df.loc[i, "impressions"]
            is_warm = df.loc[i, "dominant_color_tone"] == "Warm"
            rate = 0.035 if is_warm else 0.020
            c = int(imp * rate)
            cv_rate = 0.055 if is_warm else 0.035
            cnv = int(c * cv_rate)
            clicks.append(c)
            convs.append(cnv)

        df["clicks"] = clicks
        df["conversions"] = convs
        df = compute_derived_metrics(df)
        self.df = df

    def test_proportion_difference_ci(self):
        diff, ci_low, ci_upp, se = compute_proportion_difference_ci(300, 10000, 200, 10000)
        self.assertAlmostEqual(diff, 0.01, places=4)
        self.assertTrue(ci_low < diff < ci_upp)
        self.assertGreater(se, 0.0)

    def test_cohens_d(self):
        grp_a = np.array([10, 11, 12, 13, 14])
        grp_b = np.array([5, 6, 7, 8, 9])
        d = compute_cohens_d(grp_a, grp_b)
        self.assertGreater(d, 2.0)

    def test_full_analysis_ten_required_fields(self):
        findings = run_full_statistical_analysis(self.df)
        self.assertGreater(len(findings), 10)

        for f in findings:
            self.assertTrue(bool(f.attribute))
            self.assertIn(f.outcome_metric, ["CTR", "CVR", "CPC", "CPA"])
            self.assertTrue(bool(f.direction_of_association))
            self.assertIsInstance(f.effect_size, dict)
            self.assertIsInstance(f.sample_sizes, dict)
            self.assertIsInstance(f.uncertainty, dict)
            self.assertIn("ci_95_lower", f.uncertainty)
            self.assertIn("ci_95_upper", f.uncertainty)
            self.assertIn("raw_p_value", f.uncertainty)
            self.assertIn("fdr_q_value", f.uncertainty)
            self.assertTrue(bool(f.statistical_method))
            self.assertIsNotNone(f.adjusted_p_value)
            self.assertIn(
                f.evidence_classification,
                ["Supported association", "Preliminary", "Underpowered", "No clear association", "Unsupported"],
            )
            self.assertTrue(bool(f.limitations))
            self.assertIn("A non-significant result does not prove", f.limitations)

    def test_small_sample_size_underpowered_and_not_estimable(self):
        # n=2 per group -> Underpowered
        small_df = self.df.iloc[:4].copy()
        small_df["dominant_color_tone"] = ["Warm", "Warm", "Cool", "Cool"]
        findings = analyze_categorical_attribute(small_df, "dominant_color_tone", "Warm", "Cool")
        findings = apply_multiple_testing_correction(findings)
        for f in findings:
            self.assertEqual(f.evidence_classification, "Underpowered")

        # n=0 in one group -> Not estimable
        empty_grp = analyze_categorical_attribute(small_df, "dominant_color_tone", "Warm", "Neutral")
        self.assertEqual(len(empty_grp), 1)
        self.assertEqual(empty_grp[0].evidence_classification, "Not estimable")

    def test_n1_descriptive_only_and_corrupted_record_exclusion(self):
        # n=1 in one group -> Descriptive Comparison Only + Underpowered after multiple testing correction
        n1_df = self.df.iloc[:4].copy()
        n1_df["dominant_color_tone"] = ["Warm", "Cool", "Cool", "Cool"]
        findings_n1 = analyze_categorical_attribute(n1_df, "dominant_color_tone", "Warm", "Cool")
        findings_n1 = apply_multiple_testing_correction(findings_n1)
        for f in findings_n1:
            self.assertEqual(f.evidence_classification, "Underpowered")
            self.assertIn("Descriptive Comparison Only", f.statistical_method)

        # Corrupted / unmatched records (extraction_status != 'success') must be excluded from statistical analysis
        dirty_df = self.df.copy()
        dirty_df["extraction_status"] = ["success"] * 14 + ["error", "unmatched"]
        dirty_df.loc[14:, "dominant_color_tone"] = "Unknown"
        findings_clean = run_full_statistical_analysis(dirty_df)
        for f in findings_clean:
            for grp_ads in f.traceable_ad_ids.values():
                self.assertNotIn("ad_14", grp_ads)
                self.assertNotIn("ad_15", grp_ads)

    def test_multiple_testing_fdr_and_evidence_classification_rules(self):
        # Test classify_evidence tiers explicitly
        self.assertEqual(classify_evidence(0.001, 0.01, 6, 6, 25.0, 0.005, 0.025), "Supported association")
        self.assertEqual(classify_evidence(0.03, 0.12, 5, 5, 15.0, 0.001, 0.020), "Preliminary")
        self.assertEqual(classify_evidence(0.01, 0.02, 2, 5, 30.0, 0.005, 0.030), "Underpowered")
        self.assertEqual(classify_evidence(0.55, 0.70, 6, 6, 2.0, -0.01, 0.012), "No clear association")
        self.assertEqual(classify_evidence(0.35, 0.50, 3, 3, 5.0, -0.02, 0.03), "Unsupported")

    def test_empty_data_behavior(self):
        empty_df = pd.DataFrame()
        kpis = compute_aggregate_kpis(empty_df)
        self.assertEqual(kpis["total_creatives"], 0)
        self.assertIsNone(kpis["aggregate_ctr"])
        self.assertIsNone(kpis["mean_ad_ctr"])

        empty_findings = run_full_statistical_analysis(empty_df)
        self.assertEqual(empty_findings, [])

        empty_brief = generate_creative_brief([], empty_df, dataset_is_synthetic=False)
        self.assertIn("full_markdown", empty_brief)
        self.assertEqual(len(empty_brief["supported_findings"]), 0)


class TestAdditionalEdgeCasesAndExports(unittest.TestCase):
    def test_zero_impression_click_and_conversion_violations(self):
        # clicks > 0 when impressions == 0 must be rejected
        bad_csv = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_bad_zero,50,0,5,0\n"
        )
        df, errors, _ = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("exceeding impressions" in e.lower() for e in errors))

        # conversions > 0 when clicks == 0 (without allow_view_through_conversions) must be rejected
        bad_csv_2 = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_bad_cnv,50,1000,0,2\n"
        )
        df2, errors2, _ = validate_and_parse_csv(bad_csv_2.encode("utf-8"))
        self.assertIsNone(df2)
        self.assertTrue(any("conversions exceeding clicks" in e.lower() for e in errors2))

    def test_grayscale_and_rgba_transparent_image_extraction(self):
        # Grayscale ('L' mode) image
        gray_img = Image.new("L", (200, 200), color=128)
        gray_feats = extract_features_from_image(gray_img, use_cache=False)
        self.assertEqual(gray_feats["extraction_status"], "success")
        self.assertEqual(gray_feats["dominant_color_tone"], "Neutral")
        self.assertIn("unavailable_features", gray_feats)
        self.assertIn("Unavailable", gray_feats["unavailable_features"]["ocr_text_extraction"])

        # RGBA transparent image
        rgba_img = Image.new("RGBA", (200, 400), color=(255, 80, 20, 180))
        rgba_feats = extract_features_from_image(rgba_img, use_cache=False)
        self.assertEqual(rgba_feats["extraction_status"], "success")
        self.assertEqual(rgba_feats["width"], 200)
        self.assertEqual(rgba_feats["height"], 400)
        self.assertIn("format_suitability", rgba_feats)
        self.assertAlmostEqual(
            rgba_feats["pct_warm_pixels"] + rgba_feats["pct_cool_pixels"] + rgba_feats["pct_neutral_pixels"],
            100.0,
            places=0,
        )

    def test_export_helpers_and_ad_level_kpis(self):
        from creative_brief import findings_to_export_df, build_consolidated_report_markdown

        df, imgs = generate_synthetic_dataset()
        res = ingest_ad_dataset(generate_example_csv_content().encode("utf-8"), imgs)
        self.assertTrue(res.is_valid)

        kpis = compute_aggregate_kpis(res.df)
        self.assertIsNotNone(kpis["aggregate_ctr"])
        self.assertIsNotNone(kpis["mean_ad_ctr"])
        self.assertIsNotNone(kpis["median_ad_ctr"])

        feat_dict = batch_extract_features(res.matched_images)
        feat_df = pd.DataFrame([{"ad_id": k, **v} for k, v in feat_dict.items()])
        merged = pd.merge(res.df, feat_df, on="ad_id", how="left")
        findings = run_full_statistical_analysis(merged)

        exp_df = findings_to_export_df(findings)
        self.assertEqual(len(exp_df), len(findings))
        self.assertIn("estimand", exp_df.columns)
        self.assertIn("adjusted_fdr_q_value", exp_df.columns)

        report_md = build_consolidated_report_markdown(merged, findings, res, is_synthetic=True)
        self.assertIn("CONSOLIDATED ADCREATIVE INTELLIGENCE REPORT", report_md)
        self.assertIn("CAMPAIGN-LEVEL POOLED METRICS VS. AD-LEVEL DISTRIBUTION", report_md)



class TestDynamicCreativeBrief(unittest.TestCase):
    def test_dynamic_brief_generation(self):
        df, imgs = generate_synthetic_dataset()
        df = compute_derived_metrics(df)
        feat_dict = batch_extract_features(imgs)
        feat_df = pd.DataFrame([{"ad_id": k, **v} for k, v in feat_dict.items()])
        merged = pd.merge(df, feat_df, on="ad_id", how="left")
        findings = run_full_statistical_analysis(merged)
        brief = generate_creative_brief(findings, merged, dataset_is_synthetic=True)

        self.assertIn("full_markdown", brief)
        self.assertIn("actionable_dos", brief)
        self.assertIn("ab_test_matrix", brief)
        self.assertGreater(len(brief["ab_test_matrix"]), 0)
        self.assertIn("SYNTHETIC DATASET", brief["full_markdown"])
        # Verify A/B test matrix attributes come from actual findings
        finding_attrs = {f.attribute.split(":")[0].strip() for f in findings}
        for exp in brief["ab_test_matrix"]:
            self.assertIn(exp["attribute_tested"], finding_attrs)


if __name__ == "__main__":
    unittest.main()

