"""
CLI Pipeline Runner for Search Term Triage Engine (TriageIQ).

Batch processes Google Ads Search Term reports:
- Vectorized input loading and validation.
- Preserves all original columns and assigns stable row_id.
- Runs deterministic intent clustering.
- Evaluates evidence policy and statistical uncertainty.
- Exports validated Google Ads Editor files and complete audit log.
"""

import argparse
import sys
import os
import time
import pandas as pd
from typing import Dict, Any, List, Tuple

from triage_engine.rules import TriageEngine, AdvertiserProfile
from triage_engine.clustering import cluster_search_queries
from triage_engine.exporter import export_triage_results
from triage_engine.negatives import generate_context_aware_negative_suggestions

def normalize_input_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates input columns, preserves all original data, and standardizes key fields.
    """
    df = df.copy()
    
    # Ensure stable row_id exists
    if "row_id" not in df.columns:
        df["row_id"] = range(1, len(df) + 1)
    else:
        # Fill any missing row_ids with sequential indices
        df["row_id"] = df["row_id"].fillna(pd.Series(range(1, len(df) + 1)))
        
    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower().replace("_", " ")
        if "query" in c_clean or "search term" in c_clean or "keyword" in c_clean or "term" in c_clean:
            col_map[col] = "query_text"
        elif "match" in c_clean:
            col_map[col] = "match_type"
        elif "campaign" in c_clean:
            col_map[col] = "campaign"
        elif "ad group" in c_clean or "adgroup" in c_clean:
            col_map[col] = "ad_group"
        elif "impr" in c_clean:
            col_map[col] = "impressions"
        elif "click" in c_clean:
            col_map[col] = "clicks"
        elif "cost" in c_clean or "spend" in c_clean:
            col_map[col] = "cost"
        elif "conv. val" in c_clean or "conversion value" in c_clean or "revenue" in c_clean or "value" in c_clean:
            col_map[col] = "conversion_value"
        elif "conv" in c_clean:
            col_map[col] = "conversions"

    # Rename standardized columns while retaining original data
    df = df.rename(columns=col_map)
    
    # Safeguard numeric fields against NaNs, strings, and negatives
    for num_col in ["impressions", "clicks", "cost", "conversions", "conversion_value"]:
        if num_col not in df.columns:
            df[num_col] = 0.0
        else:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0.0).clip(lower=0.0)
            
    if "query_text" not in df.columns:
        text_cols = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype) == "string"]
        if text_cols:
            df["query_text"] = df[text_cols[0]]
        else:
            raise ValueError("Could not find a 'query text' or 'search_term' column in input data.")
            
    df["query_text"] = df["query_text"].fillna("").astype(str).str.strip()
    
    if "campaign" not in df.columns:
        df["campaign"] = "Default Campaign"
    else:
        df["campaign"] = df["campaign"].fillna("Default Campaign").astype(str)
        
    if "ad_group" not in df.columns:
        df["ad_group"] = "Default Ad Group"
    else:
        df["ad_group"] = df["ad_group"].fillna("Default Ad Group").astype(str)
        
    if "match_type" not in df.columns:
        df["match_type"] = "Broad"
    else:
        df["match_type"] = df["match_type"].fillna("Broad").astype(str)
        
    return df


def run_triage_pipeline(input_path: str, output_dir: str, target_cpa: float = None, enable_clustering: bool = True) -> Dict[str, Any]:
    print(f"\n" + "="*70)
    print("   TRIAGEIQ: EVIDENCE-FIRST SEARCH INTELLIGENCE PIPELINE")
    print("="*70)
    print(f"[*] Input File        : {input_path}")
    print(f"[*] Output Directory  : {output_dir}")
    
    t0 = time.time()
    if not os.path.exists(input_path):
        print(f"[!] Error: File '{input_path}' not found.")
        sys.exit(1)
        
    print("[*] Ingesting search terms dataset...")
    raw_df = pd.read_csv(input_path)
    total_raw_rows = len(raw_df)
    print(f"    Loaded {total_raw_rows:,} records.")
    
    clean_df = normalize_input_data(raw_df)
    
    # Calculate account & campaign economic benchmarks
    tot_cost = clean_df["cost"].sum()
    tot_convs = clean_df["conversions"].sum()
    account_avg_cpa = round(tot_cost / max(1.0, tot_convs), 2)
    
    if target_cpa is None:
        effective_target_cpa = account_avg_cpa
        print(f"[*] Auto-calibrated Account Baseline CPA: ${effective_target_cpa:.2f}")
    else:
        effective_target_cpa = float(target_cpa)
        print(f"[*] User-Specified Target CPA           : ${effective_target_cpa:.2f}")

    campaign_target_cpas = {}
    camp_summary = clean_df.groupby("campaign").agg({"cost": "sum", "conversions": "sum"})
    for camp_name, row in camp_summary.iterrows():
        camp_cpa = round(row["cost"] / max(1.0, row["conversions"]), 2)
        campaign_target_cpas[camp_name] = camp_cpa

    records = clean_df.to_dict(orient="records")

    cluster_summary = None
    if enable_clustering:
        print("[*] Running intent clustering to group near-duplicate queries...")
        clusters, records = cluster_search_queries(records)
        cluster_summary = {
            "total_clusters": len(clusters),
            "multi_variant_clusters": sum(1 for c in clusters if c["variant_count"] > 1)
        }
        print(f"    Identified {len(clusters):,} intent clusters ({cluster_summary['multi_variant_clusters']:,} multi-variant).")

    print("[*] Initializing statistical evidence engine (Wilson CI + Empirical Bayes)...")
    engine = TriageEngine(target_cpa=effective_target_cpa, campaign_target_cpas=campaign_target_cpas)
    
    print("[*] Triaging terms against statistical uncertainty thresholds...")
    results: List[Dict[str, Any]] = []
    for r in records:
        eval_res = engine.evaluate_query(r)
        # Preserve cluster traceability
        if "cluster_id" in r:
            eval_res["cluster_id"] = r["cluster_id"]
            eval_res["cluster_canonical_query"] = r.get("cluster_canonical_query", "")
            eval_res["cluster_size"] = r.get("cluster_size", 1)
        results.append(eval_res)
        
    t_eval = time.time() - t0
    print(f"    Evaluated {len(results):,} terms in {t_eval:.2f}s ({len(results)/t_eval:,.0f} terms/sec).")

    print("[*] Generating Google Ads Editor export files...")
    adv_profile = AdvertiserProfile()
    res_df = pd.DataFrame(results)
    neg_sugs = generate_context_aware_negative_suggestions(res_df, adv_profile, target_cpa=effective_target_cpa)
    exported_files = export_triage_results(results, output_dir, negative_suggestions=neg_sugs)
    
    # Calculate executive metrics
    counts = res_df["decision"].value_counts().to_dict()
    
    promotes = counts.get("PROMOTE", 0)
    blocks = counts.get("BLOCK", 0)
    ignores = counts.get("IGNORE", 0)
    needs_review_count = int(res_df["needs_review"].sum())
    
    # Defensible financial metrics (no inflated savings claims)
    blocked_spend = res_df[res_df["decision"] == "BLOCK"]["cost"].sum()
    promoted_conv = res_df[res_df["decision"] == "PROMOTE"]["conversions"].sum()
    promoted_value = res_df[res_df["decision"] == "PROMOTE"]["conversion_value"].sum()

    print("\n" + "-"*70)
    print("                 EXECUTIVE AUDIT SUMMARY")
    print("-"*70)
    print(f" Total Terms Ingested      : {len(results):,}")
    print(f" [PROMOTE] Decisions       : {promotes:,} ({promotes/len(results):.1%}) - High-evidence candidates")
    print(f" [BLOCK] Decisions         : {blocks:,} ({blocks/len(results):.1%}) - Excluded off-target/bleeders")
    print(f" [IGNORE] Decisions        : {ignores:,} ({ignores/len(results):.1%}) - Dormant / unproven long-tail")
    print(f" -> Flagged for Review     : {needs_review_count:,} ({needs_review_count/len(results):.1%}) [needs_review=True]")
    print("-" + "-"*69)
    print(f" Historical Spend on Blocked Terms : ${blocked_spend:,.2f} (Potential future spend reduction)")
    print(f" Attributed Conversion Value        : ${promoted_value:,.2f} ({int(promoted_conv):,} loan applications)")
    print("-" + "-"*69)
    print(f" [>] Complete Audit Log       : {exported_files['full_report']}")
    print(f" [>] Negative Keywords Upload : {exported_files['negatives']}")
    print(f" [>] Promoted Keywords Upload : {exported_files['promoted']}")
    print(f" [>] Human Review Queue File  : {exported_files['review_queue']}")
    print(f" [>] Negative Suggestions CSV : {exported_files['negative_suggestions']}")
    print(f" [>] Reviewer Corrections Log : {exported_files['corrections_log']}")
    print("="*70 + "\n")
    
    return {
        "counts": counts,
        "needs_review_count": needs_review_count,
        "exported_files": exported_files,
        "cluster_summary": cluster_summary,
        "total_rows": len(results)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TriageIQ Search Term Triage Engine")
    parser.add_argument("--input", "-i", type=str, default="data/search_terms_25k.csv", help="Path to input CSV file")
    parser.add_argument("--output-dir", "-o", type=str, default="output", help="Directory for exported results")
    parser.add_argument("--target-cpa", type=float, default=None, help="Target CPA threshold (auto-derived if omitted)")
    parser.add_argument("--no-cluster", action="store_true", help="Disable intent clustering")
    
    args = parser.parse_args()
    run_triage_pipeline(
        input_path=args.input,
        output_dir=args.output_dir,
        target_cpa=args.target_cpa,
        enable_clustering=not args.no_cluster
    )
