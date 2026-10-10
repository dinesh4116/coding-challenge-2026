import io
import csv
from datetime import datetime, timezone

def sanitize_csv_cell(value):
    """
    Prevents CSV / Excel formula injection by prepending a single quote
    if the string begins with =, +, -, @, tab, or carriage return.
    """
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + str_val
    return str_val

def generate_csv_export(records):
    """
    Generates full triage results as a CSV string with formula injection protection.
    """
    output = io.StringIO()
    fieldnames = [
        'Row ID', 'Search Term', 'Campaign', 'Ad Group', 'Match Type',
        'Impressions', 'Clicks', 'Cost', 'Conversions', 'Conv. Value',
        'CTR (%)', 'CPC ($)', 'CVR (%)', 'CPA ($)', 'ROAS',
        'Recommendation', 'Confidence Score', 'Confidence Level',
        'Explanation', 'Recommended Action', 'Review Status'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for r in records:
        writer.writerow({
            'Row ID': sanitize_csv_cell(r.get('row_id')),
            'Search Term': sanitize_csv_cell(r.get('search_term')),
            'Campaign': sanitize_csv_cell(r.get('campaign')),
            'Ad Group': sanitize_csv_cell(r.get('ad_group')),
            'Match Type': sanitize_csv_cell(r.get('match_type')),
            'Impressions': r.get('impressions') if r.get('impressions') is not None else "",
            'Clicks': r.get('clicks') if r.get('clicks') is not None else "",
            'Cost': r.get('cost') if r.get('cost') is not None else "",
            'Conversions': r.get('conversions') if r.get('conversions') is not None else "",
            'Conv. Value': r.get('conversion_value') if r.get('conversion_value') is not None else "",
            'CTR (%)': r.get('ctr') if r.get('ctr') is not None else "",
            'CPC ($)': r.get('cpc') if r.get('cpc') is not None else "",
            'CVR (%)': r.get('cvr') if r.get('cvr') is not None else "",
            'CPA ($)': r.get('cpa') if r.get('cpa') is not None else "",
            'ROAS': r.get('roas') if r.get('roas') is not None else "",
            'Recommendation': sanitize_csv_cell(r.get('recommendation')),
            'Confidence Score': r.get('confidence'),
            'Confidence Level': sanitize_csv_cell(r.get('confidence_label')),
            'Explanation': sanitize_csv_cell(r.get('explanation')),
            'Recommended Action': sanitize_csv_cell(r.get('recommended_next_action')),
            'Review Status': sanitize_csv_cell(r.get('review_status'))
        })
        
    return output.getvalue()

def generate_negatives_csv(negatives_list):
    """
    Generates negative keyword CSV formatted for Google Ads Editor / Bulk Upload.
    Columns: Campaign, Ad Group, Keyword, Criterion Type
    """
    output = io.StringIO()
    fieldnames = ['Campaign', 'Ad Group', 'Keyword', 'Criterion Type', 'Scope', 'Reason', 'Confidence']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in negatives_list:
        kw = item.get('suggested_negative') or item.get('search_term', '')
        match_type = item.get('match_type', 'Exact').capitalize()
        scope = item.get('scope', 'Campaign').capitalize()
        
        # Format keyword for Google Ads Editor standard
        formatted_kw = kw
        if match_type == 'Exact':
            formatted_kw = f"[{kw}]"
        elif match_type == 'Phrase':
            formatted_kw = f'"{kw}"'
            
        writer.writerow({
            'Campaign': sanitize_csv_cell(item.get('campaign', '')),
            'Ad Group': sanitize_csv_cell(item.get('ad_group', '')) if scope == 'Ad group' else '',
            'Keyword': sanitize_csv_cell(formatted_kw),
            'Criterion Type': f"Negative {match_type}",
            'Scope': sanitize_csv_cell(scope),
            'Reason': sanitize_csv_cell(item.get('reason', '')),
            'Confidence': item.get('confidence', '')
        })

    return output.getvalue()

def generate_rejected_rows_csv(rejected_rows):
    """
    Generates CSV of rejected rows for auditor inspection.
    """
    output = io.StringIO()
    fieldnames = ['Row Number', 'Row ID', 'Search Term', 'Rejection Reason', 'Raw Data Snippet']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in rejected_rows:
        writer.writerow({
            'Row Number': item.get('row_number', ''),
            'Row ID': sanitize_csv_cell(item.get('row_id', '')),
            'Search Term': sanitize_csv_cell(item.get('search_term', '')),
            'Rejection Reason': sanitize_csv_cell(item.get('reason', '')),
            'Raw Data Snippet': sanitize_csv_cell(str(item.get('raw_data', ''))[:200])
        })

    return output.getvalue()

def generate_executive_audit_report(summary_data):
    """
    Generates a structured executive audit report object with HTML rendering option.
    """
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    dataset_name = summary_data.get('dataset_name', 'Uploaded Search Query File')
    total_processed = summary_data.get('total_processed', 0)
    total_rejected = summary_data.get('total_rejected', 0)
    decision_counts = summary_data.get('decision_counts', {})
    confidence_counts = summary_data.get('confidence_counts', {})
    spend_intel = summary_data.get('spend_intelligence', {})
    campaign_summaries = spend_intel.get('campaign_summaries', [])

    assumption_items = "".join([f"<li>{a}</li>" for a in spend_intel.get('assumptions', [])])
    
    table_rows = []
    for c in campaign_summaries[:10]:
        roas_str = f"{c.get('roas'):.2f}x" if c.get('roas') is not None else "N/A"
        table_rows.append(
            f"<tr><td><strong>{c['campaign']}</strong></td>"
            f"<td>{c['query_count']}</td>"
            f"<td>${c['total_spend']:,.2f}</td>"
            f"<td><span style='color: #ef4444;'>${c['blocked_spend']:,.2f}</span></td>"
            f"<td>{c['conversions']:.1f}</td>"
            f"<td>{roas_str}</td></tr>"
        )
    table_rows_html = "".join(table_rows)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audit Report - Search Term Triage Engine (PS-01)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f8fafc; padding: 40px; }}
  .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
  .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-start; }}
  h1 {{ margin: 0; color: #0c1322; font-size: 26px; }}
  .sub {{ color: #0284c7; font-weight: 600; margin: 5px 0 0; }}
  .date {{ font-size: 13px; color: #64748b; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
  .card {{ background: #f1f5f9; padding: 16px; border-radius: 8px; text-align: center; }}
  .card .num {{ font-size: 24px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
  .card .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
  .promote {{ color: #10b981 !important; }}
  .block {{ color: #ef4444 !important; }}
  .review {{ color: #f59e0b !important; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
  .callout {{ background: #eff6ff; border-left: 4px solid #0284c7; padding: 16px; border-radius: 4px; margin: 25px 0; font-size: 14px; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Search Term Triage Engine — Audit Report</h1>
      <div class="sub">Problem Statement: PS-01 • Explainable Search Intelligence</div>
      <p style="margin: 4px 0 0; font-size: 13px; color: #475569;">Dataset: <strong>{dataset_name}</strong></p>
    </div>
    <div class="date">
      Generated: {date_str}<br>
      Status: Complete
    </div>
  </div>

  <h2>1. Executive Summary</h2>
  <div class="grid">
    <div class="card">
      <div class="label">Total Processed</div>
      <div class="num">{total_processed:,}</div>
    </div>
    <div class="card">
      <div class="label">PROMOTE</div>
      <div class="num promote">{decision_counts.get('PROMOTE', 0):,}</div>
    </div>
    <div class="card">
      <div class="label">BLOCK (Negatives)</div>
      <div class="num block">{decision_counts.get('BLOCK', 0):,}</div>
    </div>
    <div class="card">
      <div class="label">HUMAN REVIEW</div>
      <div class="num review">{decision_counts.get('HUMAN REVIEW', 0):,}</div>
    </div>
  </div>

  <h2>2. Financial & Spend Intelligence</h2>
  <p>Historical spend evaluated: <strong>${spend_intel.get('total_spend', 0):,.2f}</strong>. Potentially avoidable budget identified: <strong>${spend_intel.get('estimated_avoidable_spend', 0):,.2f}</strong> ({spend_intel.get('avoidable_spend_percentage', 0):.1f}%).</p>
  
  <div class="callout">
    <strong>Model Assumptions & Methodology:</strong>
    <ul style="margin: 8px 0 0; padding-left: 20px;">
      {assumption_items}
    </ul>
  </div>

  <h2>3. Campaign Breakdown</h2>
  <table>
    <thead>
      <tr>
        <th>Campaign</th>
        <th>Queries</th>
        <th>Total Spend</th>
        <th>Blocked Spend</th>
        <th>Conversions</th>
        <th>ROAS</th>
      </tr>
    </thead>
    <tbody>
      {table_rows_html}
    </tbody>
  </table>

  <h2>4. Data Quality & Limitations</h2>
  <p>Processed valid rows: <strong>{total_processed:,}</strong> | Rejected / Malformed rows: <strong>{total_rejected:,}</strong>.</p>
  <p style="font-size: 13px; color: #64748b;">
    Note: Heuristic confidence scores quantify metric completeness and sample size variance. Zero conversion counts are never treated as definitive proof of irrelevance without intent corroboration.
  </p>

  <div class="footer">
    Generated by Search Term Triage Engine (PS-01) • Local Explainable Architecture
  </div>
</div>
</body>
</html>"""
    return html_content
