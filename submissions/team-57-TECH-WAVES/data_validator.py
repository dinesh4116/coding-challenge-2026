import re
import math
import pandas as pd
import numpy as np
import io

COLUMN_ALIASES = {
    'search_term': [
        'search term', 'search_term', 'query', 'search query', 'search_query', 
        'customer search term', 'user query', 'term'
    ],
    'match_type': [
        'match type', 'match_type', 'matchtype', 'match', 'query match type'
    ],
    'campaign': [
        'campaign', 'campaign name', 'campaign_name'
    ],
    'ad_group': [
        'ad group', 'ad_group', 'adgroup', 'ad group name', 'ad_group_name'
    ],
    'impressions': [
        'impressions', 'impr.', 'impr', 'impressions count', 'views'
    ],
    'clicks': [
        'clicks', 'click count'
    ],
    'cost': [
        'cost', 'spend', 'total cost', 'total spend', 'cost ($)', 'cost (usd)'
    ],
    'conversions': [
        'conversions', 'conv.', 'conv', 'conversions count', 'all conv.', 'all conversions'
    ],
    'conversion_value': [
        'conversion value', 'conversion_value', 'conv. value', 'conv value', 
        'total conv. value', 'total conversion value', 'revenue', 'value'
    ],
    'date': [
        'date', 'day', 'timestamp', 'week'
    ]
}

def clean_numeric_value(val):
    """
    Cleans numeric values by removing currency symbols, commas, and percentage signs.
    Distinguishes genuine 0 from missing data (None/NaN).
    Returns (cleaned_float_or_None, is_valid_or_error)
    """
    if val is None or pd.isna(val):
        return None, True
    
    val_str = str(val).strip()
    if val_str == '' or val_str.lower() in ['nan', 'null', 'none', '-', '--', 'n/a']:
        return None, True

    # Strip currency symbols, commas, whitespace, percentage signs
    cleaned_str = re.sub(r'[\$,€,£,₹,\s,%]', '', val_str)
    
    try:
        num = float(cleaned_str)
        return num, True
    except (ValueError, TypeError):
        return None, False

def map_columns(df_columns):
    """
    Maps incoming DataFrame column names to standard internal schema names.
    Returns: (mapped_dict, unmapped_columns, missing_required)
    """
    column_mapping = {}
    normalized_incoming = {str(col).strip().lower(): col for col in df_columns}
    
    for standard_col, aliases in COLUMN_ALIASES.items():
        found = False
        for alias in aliases:
            if alias.lower() in normalized_incoming:
                column_mapping[normalized_incoming[alias.lower()]] = standard_col
                found = True
                break
        if not found and standard_col in normalized_incoming:
            column_mapping[normalized_incoming[standard_col]] = standard_col

    missing_required = []
    if 'search_term' not in column_mapping.values():
        missing_required.append('search_term')

    unmapped = [col for col in df_columns if col not in column_mapping]
    return column_mapping, unmapped, missing_required

def validate_and_process_csv(file_or_content):
    """
    Processes a raw CSV input (file path, file-like object, or string).
    Returns a dictionary containing:
      - 'status': 'success' or 'error'
      - 'records': list of validated and enriched record dicts
      - 'rejected_rows': list of dicts {row_index, original_data, reason}
      - 'metadata': summary dictionary with counts and column mappings
    """
    try:
        if isinstance(file_or_content, bytes):
            try:
                file_or_content = file_or_content.decode('utf-8')
            except UnicodeDecodeError:
                file_or_content = file_or_content.decode('latin-1')

        if isinstance(file_or_content, str):
            if '\n' in file_or_content or ',' in file_or_content:
                df_raw = pd.read_csv(io.StringIO(file_or_content), skip_blank_lines=False)
            else:
                df_raw = pd.read_csv(file_or_content, skip_blank_lines=False)
        elif hasattr(file_or_content, 'read'):
            content = file_or_content.read()
            if isinstance(content, bytes):
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    content = content.decode('latin-1')
            df_raw = pd.read_csv(io.StringIO(content), skip_blank_lines=False)
        elif isinstance(file_or_content, pd.DataFrame):
            df_raw = file_or_content.copy()
        else:
            return {
                'status': 'error',
                'error': 'Unsupported file format or input type.',
                'records': [],
                'rejected_rows': [],
                'metadata': {}
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': f'Failed to parse CSV file: {str(e)}',
            'records': [],
            'rejected_rows': [],
            'metadata': {}
        }

    total_input_rows = len(df_raw)
    col_mapping, unmapped, missing_required = map_columns(df_raw.columns)
    
    if 'search_term' in missing_required:
        return {
            'status': 'error',
            'error': f"Required 'Search Term' / 'Query' column could not be found. Detected columns: {list(df_raw.columns)}",
            'records': [],
            'rejected_rows': [],
            'metadata': {
                'total_rows': total_input_rows,
                'detected_columns': list(df_raw.columns),
                'missing_required': missing_required
            }
        }

    # Rename mapped columns
    df_renamed = df_raw.rename(columns=col_mapping)
    
    records = []
    rejected_rows = []
    
    numeric_fields = ['impressions', 'clicks', 'cost', 'conversions', 'conversion_value']
    
    for idx, row in df_renamed.iterrows():
        raw_row_dict = df_raw.iloc[idx].to_dict()
        row_id = f"row_{idx + 1}"
        
        # 1. Validate search term
        term_val = row.get('search_term')
        if term_val is None or pd.isna(term_val) or str(term_val).strip() == '':
            rejected_rows.append({
                'row_id': row_id,
                'row_number': idx + 2, # accounting for header line
                'search_term': '',
                'reason': 'Empty or missing search term',
                'raw_data': raw_row_dict
            })
            continue

        search_term_clean = str(term_val).strip()
        
        # 2. Parse numerics
        parsed_numbers = {}
        row_has_bad_numeric = False
        bad_col_name = None

        for num_col in numeric_fields:
            if num_col in row:
                val, is_valid = clean_numeric_value(row[num_col])
                if not is_valid:
                    row_has_bad_numeric = True
                    bad_col_name = num_col
                    break
                parsed_numbers[num_col] = val
            else:
                parsed_numbers[num_col] = None  # Explicitly distinguished from recorded 0

        if row_has_bad_numeric:
            rejected_rows.append({
                'row_id': row_id,
                'row_number': idx + 2,
                'search_term': search_term_clean,
                'reason': f"Malformed numeric value in column '{bad_col_name}': '{row.get(bad_col_name)}'",
                'raw_data': raw_row_dict
            })
            continue

        # Derived calculations
        impr = parsed_numbers.get('impressions')
        clicks = parsed_numbers.get('clicks')
        cost = parsed_numbers.get('cost')
        conv = parsed_numbers.get('conversions')
        conv_val = parsed_numbers.get('conversion_value')

        ctr = ((clicks / impr) * 100) if (impr is not None and clicks is not None and impr > 0) else None
        cpc = (cost / clicks) if (clicks is not None and cost is not None and clicks > 0) else None
        cvr = ((conv / clicks) * 100) if (clicks is not None and conv is not None and clicks > 0) else None
        cpa = (cost / conv) if (conv is not None and cost is not None and conv > 0) else None
        roas = (conv_val / cost) if (cost is not None and conv_val is not None and cost > 0) else None

        campaign_val = str(row.get('campaign', 'General Campaign')).strip() if not pd.isna(row.get('campaign')) else 'General Campaign'
        ad_group_val = str(row.get('ad_group', 'General Ad Group')).strip() if not pd.isna(row.get('ad_group')) else 'General Ad Group'
        match_type_val = str(row.get('match_type', 'Exact')).strip().capitalize() if not pd.isna(row.get('match_type')) else 'Broad'
        date_val = str(row.get('date', '')).strip() if not pd.isna(row.get('date')) else None

        record = {
            'row_id': row_id,
            'row_number': idx + 2,
            'search_term': search_term_clean,
            'campaign': campaign_val if campaign_val != '' else 'General Campaign',
            'ad_group': ad_group_val if ad_group_val != '' else 'General Ad Group',
            'match_type': match_type_val if match_type_val != '' else 'Broad',
            'date': date_val,
            'impressions': impr,
            'clicks': clicks,
            'cost': cost,
            'conversions': conv,
            'conversion_value': conv_val,
            'ctr': round(ctr, 2) if (ctr is not None and not math.isnan(ctr)) else None,
            'cpc': round(cpc, 2) if (cpc is not None and not math.isnan(cpc)) else None,
            'cvr': round(cvr, 2) if (cvr is not None and not math.isnan(cvr)) else None,
            'cpa': round(cpa, 2) if (cpa is not None and not math.isnan(cpa)) else None,
            'roas': round(roas, 2) if (roas is not None and not math.isnan(roas)) else None
        }
        records.append(record)

    metadata = {
        'total_rows': total_input_rows,
        'processed_rows': len(records),
        'rejected_rows_count': len(rejected_rows),
        'detected_columns': list(df_raw.columns),
        'mapped_columns': col_mapping,
        'unmapped_columns': unmapped
    }

    return {
        'status': 'success',
        'records': records,
        'rejected_rows': rejected_rows,
        'metadata': metadata
    }

def generate_sample_csv_template():
    """
    Generates a realistic sample CSV template with various edge cases.
    """
    sample_data = [
        # Search Term, Match type, Campaign, Ad group, Impressions, Clicks, Cost, Conversions, Conv. value, Date
        # Strong performers (PROMOTE candidates)
        ["enterprise crm software for sales", "Broad", "B2B Software", "CRM Solutions", 1450, 92, 450.50, 8.0, 4800.00, "2026-03-01"],
        ["best inventory management platform", "Phrase", "B2B Software", "Inventory", 820, 54, 280.00, 5.0, 2500.00, "2026-03-02"],
        ["b2b lead generation tool pricing", "Exact", "B2B Software", "Lead Gen", 420, 38, 195.20, 4.0, 1900.00, "2026-03-02"],
        ["cloud erp implementation services", "Broad", "Enterprise ERP", "Implementation", 2100, 115, 890.00, 9.0, 9500.00, "2026-03-03"],
        
        # High spend, 0 conversions, clearly irrelevant intent (BLOCK candidates)
        ["free download full cracked crm software", "Broad", "B2B Software", "CRM Solutions", 3200, 140, 510.00, 0.0, 0.00, "2026-03-01"],
        ["crm software engineer jobs entry level salary", "Broad", "B2B Software", "CRM Solutions", 1850, 78, 290.40, 0.0, 0.00, "2026-03-02"],
        ["how to build your own inventory system tutorial pdf", "Phrase", "B2B Software", "Inventory", 950, 42, 168.00, 0.0, 0.00, "2026-03-03"],
        ["open source crm torrent pirate bay", "Broad", "B2B Software", "CRM Solutions", 640, 31, 112.50, 0.0, 0.00, "2026-03-03"],
        ["erp software internships reddit", "Broad", "Enterprise ERP", "Implementation", 510, 25, 95.00, 0.0, 0.00, "2026-03-04"],

        # Low sample size with 1 conversion - CRITICAL UNCERTAINTY TEST (Must route to HUMAN REVIEW)
        ["sales automation tool discount code", "Broad", "B2B Software", "CRM Solutions", 15, 2, 8.40, 1.0, 250.00, "2026-03-04"],
        ["cheap cloud crm demo", "Broad", "B2B Software", "CRM Solutions", 22, 3, 14.50, 1.0, 180.00, "2026-03-04"],

        # High spend, 0 conversions, but RELEVANT commercial intent (HUMAN REVIEW - Warning signal, not auto-block!)
        ["enterprise salesforce integration consultants", "Phrase", "Enterprise ERP", "Consulting", 1200, 48, 620.00, 0.0, 0.00, "2026-03-05"],
        ["custom erp development company usa", "Exact", "Enterprise ERP", "Development", 850, 35, 480.00, 0.0, 0.00, "2026-03-05"],

        # Ambiguous queries (HUMAN REVIEW)
        ["crm vs erp differences", "Broad", "B2B Software", "CRM Solutions", 2100, 65, 145.00, 0.0, 0.00, "2026-03-05"],
        ["business software", "Broad", "B2B Software", "General", 4500, 110, 330.00, 1.0, 150.00, "2026-03-06"],

        # Near-duplicate queries for clustering
        ["buy running shoes online", "Broad", "E-Commerce", "Shoes", 900, 45, 110.00, 3.0, 360.00, "2026-03-06"],
        ["buy shoes for running online", "Phrase", "E-Commerce", "Shoes", 850, 41, 98.00, 2.0, 240.00, "2026-03-06"],
        ["purchase running shoes store", "Broad", "E-Commerce", "Shoes", 720, 36, 85.00, 2.0, 210.00, "2026-03-06"],

        # Low volume, acceptable noise (IGNORE candidates)
        ["acme crm login portal", "Exact", "B2B Software", "CRM Solutions", 45, 6, 4.20, 0.0, 0.00, "2026-03-07"],
        ["crm dashboard screenshots", "Broad", "B2B Software", "CRM Solutions", 60, 4, 3.80, 0.0, 0.00, "2026-03-07"],
        ["inventory tracking system specs", "Phrase", "B2B Software", "Inventory", 80, 5, 6.10, 0.0, 0.00, "2026-03-07"],

        # Missing metric rows (to test handling of missing values vs genuine 0)
        ["warehouse management barcode scanner app", "Broad", "B2B Software", "Inventory", 110, 8, 19.50, None, None, "2026-03-07"]
    ]

    columns = [
        "Search term", "Match type", "Campaign", "Ad group", 
        "Impressions", "Clicks", "Cost", "Conversions", "Conv. value", "Date"
    ]
    
    df = pd.DataFrame(sample_data, columns=columns)
    return df.to_csv(index=False)
