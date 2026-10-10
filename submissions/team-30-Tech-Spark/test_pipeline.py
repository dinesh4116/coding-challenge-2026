"""
AdCreative Intelligence - Pipeline Test Suite
Comprehensive unit tests covering:
1. Image feature extraction (color, palette distribution, brightness, contrast, dimensions,
   aspect ratio, composition features, pretrained Haar cascade face detection, text proxy, error status)
2. CSV validation (missing columns, missing data, duplicates, negative/invalid values, impossible ratios,
   custom column mapping, and Data Quality Summary)
3. Image-to-ad matching (stem normalization, missing images, missing CSV records, zero silent discards)
4. Metric calculations (ad-level & pooled aggregate CTR, CVR, CPC, CPA, ROAS, zero denominators)
5. Statistical comparisons (categorical & continuous, multiple testing FDR, 10 required finding fields,
   Creative Scorecard, and Multi-Creative Side-by-Side Comparison)
6. Small sample sizes (Underpowered & Not estimable classifications)
7. Dynamic Creative Brief integration (14-section brief, low-evidence fallback, Experiment Planner,
   and 6-part Explainable Recommendations).
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
    normalize_identifier_candidates,
    ensure_persistent_image,
    suggest_column_mapping,
    apply_column_mapping,
    compute_data_quality_summary,
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
    build_creative_scorecard,
    compare_multiple_creatives,
)
from synthetic_data import generate_synthetic_dataset
from creative_brief import generate_creative_brief
from recommendations import generate_recommendations, generate_experiment_plan


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

    def test_creative_library_image_matching_extensions_persistence_and_diagnostics(self):
        class SimulatedUploadedFile(io.BytesIO):
            def __init__(self, data: bytes, name: str):
                super().__init__(data)
                self.name = name

        def _make_img_bytes(fmt: str, color: tuple) -> bytes:
            buf = io.BytesIO()
            Image.new("RGB", (80, 80), color=color).save(buf, format=fmt)
            return buf.getvalue()

        f_png = SimulatedUploadedFile(_make_img_bytes("PNG", (220, 60, 40)), "  AD_WARM_01.PNG  ")
        f_jpg = SimulatedUploadedFile(_make_img_bytes("JPEG", (210, 70, 50)), "ad-warm-02.jpg")
        f_jpeg = SimulatedUploadedFile(_make_img_bytes("JPEG", (40, 90, 210)), "ad_cool_01.png.jpeg")
        f_webp = SimulatedUploadedFile(_make_img_bytes("WEBP", (50, 100, 220)), "ad_cool_02 (1).webp")

        csv_data = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_warm_01,450.0,18500,640,48\n"
            "ad_warm_02,320.5,14200,490,35\n"
            "ad_cool_01,510.0,21000,410,19\n"
            "ad_cool_02,280.0,12500,230,11\n"
            "ad_missing_99,150.0,8000,120,5\n"
        )

        res = ingest_ad_dataset(csv_data.encode("utf-8"), [f_png, f_jpg, f_jpeg, f_webp])
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.matched_images), 4)
        for matched_id in ("ad_warm_01", "ad_warm_02", "ad_cool_01", "ad_cool_02"):
            self.assertIn(matched_id, res.matched_images)
            self.assertIsInstance(res.matched_images[matched_id], Image.Image)

        f_png.close()
        f_jpg.close()
        f_jpeg.close()
        f_webp.close()

        feat_dict = batch_extract_features(res.matched_images)
        for matched_id in ("ad_warm_01", "ad_warm_02", "ad_cool_01", "ad_cool_02"):
            self.assertEqual(feat_dict[matched_id]["extraction_status"], "success")
            self.assertEqual(res.matched_images[matched_id].size, (80, 80))

        self.assertEqual(res.unmatched_records, ["ad_missing_99"])
        self.assertEqual(len(res.matching_diagnostics), 5)
        missing_diag = [d for d in res.matching_diagnostics if d["csv_ad_id"] == "ad_missing_99"][0]
        self.assertEqual(missing_diag["match_status"], "Missing Image")
        self.assertIn("ad_missing_99", missing_diag["diagnostic"])
        self.assertIn("AD_WARM_01.PNG", missing_diag["uploaded_filenames"])

    def test_custom_column_mapping_and_data_quality_summary(self):
        raw_df = pd.DataFrame({
            "Creative ID": ["c_01", "c_02"],
            "Amount Spent": [150.0, 250.0],
            "Impr": [10000, 15000],
            "Link Clicks": [300, 450],
            "Purchases": [15, 25],
            "Purchase Value": [600.0, 1000.0],
            "Campaign": ["Spring_Acquisition", "Spring_Acquisition"],
            "Reporting Date": ["2026-03-01", "2026-03-07"],
        })
        suggested = suggest_column_mapping(list(raw_df.columns))
        self.assertEqual(suggested["ad_id"], "Creative ID")
        self.assertEqual(suggested["spend"], "Amount Spent")
        self.assertEqual(suggested["impressions"], "Impr")
        self.assertEqual(suggested["clicks"], "Link Clicks")
        self.assertEqual(suggested["conversions"], "Purchases")
        self.assertEqual(suggested["revenue"], "Purchase Value")
        self.assertEqual(suggested["campaign_name"], "Campaign")
        self.assertEqual(suggested["date"], "Reporting Date")

        mapped_df = apply_column_mapping(raw_df, suggested)
        res = ingest_ad_dataset(mapped_df, {})
        self.assertTrue(res.is_valid)
        self.assertIn("roas", res.df.columns)
        self.assertIn("campaign_name", res.df.columns)
        self.assertIn("campaign", res.df.columns)

        dq_emp = compute_data_quality_summary(res.df, res, is_synthetic=False)
        self.assertEqual(dq_emp["creative_count"], 2)
        self.assertEqual(dq_emp["performance_record_count"], 2)
        self.assertEqual(dq_emp["dataset_origin_label"], "IMPORTED EMPIRICAL DATASET")
        self.assertIn("2026-03-01", dq_emp["date_coverage"])
        self.assertIn("revenue", dq_emp["present_optional_fields"])

        dq_syn = compute_data_quality_summary(res.df, res, is_synthetic=True)
        self.assertEqual(dq_syn["dataset_origin_label"], "DEMO DATA — SYNTHETIC EXAMPLE")


class TestAggregatePerformanceMetrics(unittest.TestCase):
    def test_pooled_aggregate_metrics_vs_naive_average(self):
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
        small_df = self.df.iloc[:4].copy()
        small_df["dominant_color_tone"] = ["Warm", "Warm", "Cool", "Cool"]
        findings = analyze_categorical_attribute(small_df, "dominant_color_tone", "Warm", "Cool")
        findings = apply_multiple_testing_correction(findings)
        for f in findings:
            self.assertEqual(f.evidence_classification, "Underpowered")

        empty_grp = analyze_categorical_attribute(small_df, "dominant_color_tone", "Warm", "Neutral")
        self.assertEqual(len(empty_grp), 1)
        self.assertEqual(empty_grp[0].evidence_classification, "Not estimable")

    def test_n1_descriptive_only_and_corrupted_record_exclusion(self):
        n1_df = self.df.iloc[:4].copy()
        n1_df["dominant_color_tone"] = ["Warm", "Cool", "Cool", "Cool"]
        findings_n1 = analyze_categorical_attribute(n1_df, "dominant_color_tone", "Warm", "Cool")
        findings_n1 = apply_multiple_testing_correction(findings_n1)
        for f in findings_n1:
            self.assertEqual(f.evidence_classification, "Underpowered")
            self.assertIn("Descriptive Comparison Only", f.statistical_method)

        dirty_df = self.df.copy()
        dirty_df["extraction_status"] = ["success"] * 14 + ["error", "unmatched"]
        dirty_df.loc[14:, "dominant_color_tone"] = "Unknown"
        findings_clean = run_full_statistical_analysis(dirty_df)
        for f in findings_clean:
            for grp_ads in f.traceable_ad_ids.values():
                self.assertNotIn("ad_14", grp_ads)
                self.assertNotIn("ad_15", grp_ads)

    def test_multiple_testing_fdr_and_evidence_classification_rules(self):
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
        self.assertTrue(empty_brief["is_low_evidence_fallback"])


class TestAdditionalEdgeCasesAndExports(unittest.TestCase):
    def test_zero_impression_click_and_conversion_violations(self):
        bad_csv = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_bad_zero,50,0,5,0\n"
        )
        df, errors, _ = validate_and_parse_csv(bad_csv.encode("utf-8"))
        self.assertIsNone(df)
        self.assertTrue(any("exceeding impressions" in e.lower() for e in errors))

        bad_csv_2 = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_bad_cnv,50,1000,0,2\n"
        )
        df2, errors2, _ = validate_and_parse_csv(bad_csv_2.encode("utf-8"))
        self.assertIsNone(df2)
        self.assertTrue(any("conversions exceeding clicks" in e.lower() for e in errors2))

    def test_grayscale_and_rgba_transparent_image_extraction(self):
        gray_img = Image.new("L", (200, 200), color=128)
        gray_feats = extract_features_from_image(gray_img, use_cache=False)
        self.assertEqual(gray_feats["extraction_status"], "success")
        self.assertEqual(gray_feats["dominant_color_tone"], "Neutral")
        self.assertIn("unavailable_features", gray_feats)
        self.assertIn("Unavailable", gray_feats["unavailable_features"]["ocr_text_extraction"])

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
        self.assertIn("experiment_plan", brief)
        self.assertGreater(len(brief["ab_test_matrix"]), 0)
        self.assertGreater(len(brief["experiment_plan"]), 0)
        self.assertIn("SYNTHETIC DATASET", brief["full_markdown"])
        finding_attrs = {f.attribute.split(":")[0].strip() for f in findings}
        for exp in brief["ab_test_matrix"]:
            self.assertIn(exp["attribute_tested"], finding_attrs)


class TestEnhancedAnalyticalIntelligence(unittest.TestCase):
    def test_dataframe_reingestion_and_roas_calculations(self):
        csv_no_rev = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,100.0,10000,300,15\n"
            "ad_2,200.0,20000,400,20\n"
        )
        df_no_rev, errs, _ = validate_and_parse_csv(csv_no_rev.encode("utf-8"))
        self.assertIsNotNone(df_no_rev)
        self.assertEqual(errs, [])
        self.assertNotIn("roas", df_no_rev.columns)
        kpis_no_rev = compute_aggregate_kpis(df_no_rev)
        self.assertIsNone(kpis_no_rev["aggregate_roas"])
        self.assertIsNone(kpis_no_rev["total_revenue"])

        csv_with_rev = (
            "ad_id,spend,impressions,clicks,conversions,revenue,variant\n"
            "ad_1,100.0,10000,300,15,450.0,Variant_A\n"
            "ad_2,300.0,20000,400,20,600.0,Variant_B\n"
            "ad_zero_spend,0.0,1000,20,1,50.0,Variant_A\n"
        )
        df_rev, errs_rev, warns_rev = validate_and_parse_csv(csv_with_rev.encode("utf-8"))
        self.assertIsNotNone(df_rev)
        self.assertEqual(errs_rev, [])
        self.assertIn("roas", df_rev.columns)
        self.assertTrue(any("0 spend" in w for w in warns_rev))

        r1 = df_rev[df_rev["ad_id"] == "ad_1"]["roas"].iloc[0]
        r2 = df_rev[df_rev["ad_id"] == "ad_2"]["roas"].iloc[0]
        r0 = df_rev[df_rev["ad_id"] == "ad_zero_spend"]["roas"].iloc[0]
        self.assertAlmostEqual(r1, 4.5, places=4)
        self.assertAlmostEqual(r2, 2.0, places=4)
        self.assertTrue(np.isnan(r0))

        kpis_rev = compute_aggregate_kpis(df_rev)
        self.assertAlmostEqual(kpis_rev["total_revenue"], 1100.0, places=2)
        self.assertAlmostEqual(kpis_rev["aggregate_roas"], 2.75, places=4)
        self.assertAlmostEqual(kpis_rev["mean_ad_roas"], 3.25, places=4)

        img_a = Image.new("RGB", (200, 200), color=(230, 80, 30))
        re_res = ingest_ad_dataset(df_rev, {"ad_1.png": img_a})
        self.assertTrue(re_res.is_valid)
        self.assertIn("ad_1", re_res.matched_images)
        self.assertIn("roas", re_res.df.columns)
        self.assertIn("variant", re_res.df.columns)

        bad_rev_csv = (
            "ad_id,spend,impressions,clicks,conversions,revenue\n"
            "ad_neg,100.0,10000,300,15,-50.0\n"
        )
        df_bad, errs_bad, _ = validate_and_parse_csv(bad_rev_csv.encode("utf-8"))
        self.assertIsNone(df_bad)
        self.assertTrue(any("negative" in e.lower() for e in errs_bad))

    def test_csv_only_statistical_comparisons_and_variant_contrasts(self):
        from statistical_engine import compare_creative_variants

        csv_only = (
            "ad_id,spend,impressions,clicks,conversions,placement\n"
            "ad_a1,120,10000,420,42,Feed\n"
            "ad_a2,130,11000,450,45,Feed\n"
            "ad_a3,110,9500,390,39,Feed\n"
            "ad_a4,140,12000,490,50,Feed\n"
            "ad_b1,120,10000,150,10,Stories\n"
            "ad_b2,130,11000,165,11,Stories\n"
            "ad_b3,110,9500,140,9,Stories\n"
            "ad_b4,140,12000,180,12,Stories\n"
        )
        res = ingest_ad_dataset(csv_only.encode("utf-8"), {})
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.matched_images), 0)

        findings = run_full_statistical_analysis(res.df)
        self.assertGreater(len(findings), 0)
        self.assertTrue(any("placement" in f.attribute for f in findings))

        csv_bare = (
            "ad_id,spend,impressions,clicks,conversions\n"
            "ad_1,100,10000,400,40\n"
            "ad_2,100,10000,380,38\n"
            "ad_3,100,10000,150,12\n"
            "ad_4,100,10000,140,10\n"
        )
        res_bare = ingest_ad_dataset(csv_bare.encode("utf-8"), {})
        findings_bare = run_full_statistical_analysis(res_bare.df)
        self.assertGreater(len(findings_bare), 0)
        self.assertTrue(any("creative_variant" in f.attribute or "spend_allocation_tier" in f.attribute for f in findings_bare))

        row_a = res.df.iloc[0]
        row_b = res.df.iloc[4]
        cmp_res = compare_creative_variants(row_a, row_b)
        self.assertIsInstance(cmp_res, list)
        by_metric = {item["metric"]: item for item in cmp_res}
        self.assertIn("CTR", by_metric)
        self.assertIn("CVR", by_metric)
        self.assertEqual(by_metric["CTR"]["creative_a"], "ad_a1")
        self.assertEqual(by_metric["CTR"]["creative_b"], "ad_b1")
        self.assertLess(by_metric["CTR"]["p_value"], 0.001)
        self.assertGreater(by_metric["CTR"]["ci_95_lower"], 0.0)

    def test_small_continuous_sample_underpowered_and_roas_associations(self):
        from statistical_engine import analyze_continuous_attribute, analyze_categorical_attribute

        small_df = pd.DataFrame({
            "ad_id": ["a1", "a2", "a3"],
            "spend": [100.0, 120.0, 140.0],
            "impressions": [10000, 10000, 10000],
            "clicks": [200, 300, 400],
            "conversions": [10, 20, 30],
            "brightness_score": [35.0, 55.0, 75.0],
        })
        small_df = compute_derived_metrics(small_df)
        f_small = analyze_continuous_attribute(small_df, "brightness_score", "ctr")
        self.assertIsNotNone(f_small)
        self.assertEqual(f_small.evidence_classification, "Underpowered")
        self.assertEqual(f_small.sample_sizes["creatives_count"], 3)

        roas_df = pd.DataFrame({
            "ad_id": [f"ad_{i}" for i in range(8)],
            "spend": [100.0] * 8,
            "impressions": [10000] * 8,
            "clicks": [350, 360, 340, 355, 180, 190, 175, 185],
            "conversions": [35, 36, 34, 35, 15, 16, 14, 15],
            "revenue": [450.0, 480.0, 440.0, 460.0, 180.0, 190.0, 170.0, 185.0],
            "dominant_color_tone": ["Warm"] * 4 + ["Cool"] * 4,
            "extraction_status": ["success"] * 8,
        })
        roas_df = compute_derived_metrics(roas_df)
        cat_findings = analyze_categorical_attribute(roas_df, "dominant_color_tone", "Warm", "Cool")
        metrics_found = {f.outcome_metric for f in cat_findings}
        self.assertIn("ROAS", metrics_found)

    def test_rank_creatives_wilson_ci_and_reliability_tiers(self):
        from statistical_engine import compute_wilson_ci, rank_creatives

        ci_l, ci_u = compute_wilson_ci(50, 1000)
        self.assertLess(ci_l, 0.05)
        self.assertGreater(ci_u, 0.05)

        df_rank = pd.DataFrame({
            "ad_id": ["noisy_low_vol", "reliable_winner", "average_ad", "weak_ad"],
            "spend": [5.0, 400.0, 200.0, 200.0],
            "impressions": [100, 20000, 10000, 10000],
            "clicks": [5, 900, 250, 100],
            "conversions": [1, 90, 20, 5],
        })
        df_rank = compute_derived_metrics(df_rank)
        ranked = rank_creatives(df_rank, primary_metric="composite")
        self.assertEqual(len(ranked), 4)
        self.assertIn("ctr_ci_lower", ranked.columns)
        self.assertIn("ctr_ci_95", ranked.columns)
        self.assertIn("reliability_tier", ranked.columns)
        self.assertIn("composite_rank_score", ranked.columns)
        self.assertIn("vs_campaign_fdr_q", ranked.columns)

        top_ad = ranked.iloc[0]["ad_id"]
        self.assertEqual(top_ad, "reliable_winner")
        noisy_tier = ranked[ranked["ad_id"] == "noisy_low_vol"]["reliability_tier"].iloc[0]
        self.assertIn("Low Volume", noisy_tier)

    def test_creative_scorecard_and_multi_creative_comparison(self):
        df = pd.DataFrame({
            "ad_id": ["ad_1", "ad_2", "ad_3"],
            "spend": [300.0, 250.0, 200.0],
            "impressions": [20000, 15000, 500],
            "clicks": [800, 450, 10],
            "conversions": [60, 25, 1],
            "platform": ["Meta", "TikTok", "Meta"],
        })
        df = compute_derived_metrics(df)

        scorecard = build_creative_scorecard(df, primary_metric="composite")
        self.assertIn("scorecard_df", scorecard)
        self.assertIn("formula_documentation", scorecard)
        self.assertIn("weights", scorecard)
        self.assertIn("comparison_group_warnings", scorecard)
        self.assertEqual(len(scorecard["scorecard_df"]), 3)
        self.assertGreater(len(scorecard["comparison_group_warnings"]), 0)

        multi_cmp = compare_multiple_creatives(df, ["ad_1", "ad_2", "ad_3"])
        self.assertEqual(multi_cmp["reference_ad_id"], "ad_1")
        self.assertFalse(multi_cmp["comparison_table"].empty)
        self.assertGreater(len(multi_cmp["pairwise_tests"]), 0)
        self.assertGreater(len(multi_cmp["sample_size_warnings"]), 0)

    def test_experiment_planner_and_explainable_recommendations(self):
        df, imgs = generate_synthetic_dataset()
        df = compute_derived_metrics(df)
        feat_dict = batch_extract_features(imgs)
        feat_df = pd.DataFrame([{"ad_id": k, **v} for k, v in feat_dict.items()])
        merged = pd.merge(df, feat_df, on="ad_id", how="left")
        findings = run_full_statistical_analysis(merged)

        recs = generate_recommendations(findings, df_metrics=merged)
        all_recs = (
            recs["category_a_observed_evidence"]
            + recs["category_b_hypotheses_to_test"]
            + recs["category_c_blocked_insufficient_evidence"]
        )
        self.assertGreater(len(all_recs), 0)
        explain_keys = {
            "what_was_observed",
            "supporting_data",
            "why_it_matters",
            "action_to_test",
            "how_to_measure_success",
            "remaining_uncertainty",
        }
        for r in all_recs:
            self.assertTrue(explain_keys.issubset(set(r.keys())))

        exp_plan = generate_experiment_plan(findings, df_metrics=merged)
        self.assertGreater(len(exp_plan), 0)
        required_exp_keys = {
            "experiment_id",
            "experiment_name",
            "hypothesis",
            "control_concept",
            "variant_concept",
            "variable_changed",
            "primary_metric",
            "secondary_metrics",
            "target_audience_or_placement",
            "minimum_data_considerations",
            "measurement_period_guidance",
            "decision_criteria",
            "risks_and_limitations",
            "evidence_tier",
            "status",
        }
        for exp in exp_plan:
            self.assertTrue(required_exp_keys.issubset(set(exp.keys())))

    def test_confounding_within_stratum_and_ab_test_planning_units(self):
        df, imgs = generate_synthetic_dataset()
        df = compute_derived_metrics(df)
        df["placement"] = ["Feed" if i % 2 == 0 else "Stories" for i in range(len(df))]
        feat_dict = batch_extract_features(imgs)
        feat_df = pd.DataFrame([{"ad_id": k, **v} for k, v in feat_dict.items()])
        merged = pd.merge(df, feat_df, on="ad_id", how="left")
        findings = run_full_statistical_analysis(merged)

        conf_notes = investigate_confounding(merged, findings)
        self.assertGreater(len(conf_notes), 0)
        self.assertIn("stratified_consistency", conf_notes[0])

        brief = generate_creative_brief(
            findings,
            merged,
            dataset_is_synthetic=True,
            campaign_objective="Maximize CTR and conversion efficiency across Meta & TikTok",
            target_audience="Performance-focused D2C acquisition shoppers",
            creative_format="9:16 Vertical Story / Reel (1080×1920 px)",
        )
        self.assertIn("top_ranked_creatives", brief)
        self.assertGreater(len(brief["top_ranked_creatives"]), 0)
        self.assertIn("structured_recommendations", brief)
        self.assertIn("structured_sections", brief)
        required_14_sections = {
            "brief_title",
            "target_audience",
            "campaign_objective",
            "creative_format",
            "core_insight",
            "recommended_hook",
            "visual_direction",
            "copy_angle",
            "call_to_action",
            "creative_do_list",
            "creative_avoid_list",
            "variant_ideas",
            "suggested_test_plan",
            "success_metrics",
            "assumptions_and_limitations",
            # Legacy 10-section keys preserved
            "key_insight",
            "creative_concept",
            "hook",
            "main_message",
            "recommended_experiment",
        }
        self.assertTrue(required_14_sections.issubset(set(brief["structured_sections"].keys())))
        self.assertIn("Maximize CTR", brief["structured_sections"]["campaign_objective"])
        self.assertIn("Performance-focused D2C", brief["structured_sections"]["target_audience"])
        self.assertIn("9:16 Vertical Story", brief["structured_sections"]["creative_format"])

        for exp in brief["ab_test_matrix"]:
            self.assertIn("guardrail_kpi", exp)
            self.assertIn("exemplar_ad_ids", exp)
            self.assertIn("confounding_controls", exp)
            self.assertIn("impressions", exp["min_sample_size_per_variant"])

        from recommendations import generate_pdf_report_bytes
        recs = generate_recommendations(findings, df_metrics=merged)
        pdf_bytes = generate_pdf_report_bytes(
            project_name="Unit Test Campaign",
            project_id="test_proj_01",
            df_metrics=merged,
            findings=findings,
            recommendations=recs,
            is_synthetic=True,
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
