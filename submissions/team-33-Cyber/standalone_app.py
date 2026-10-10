import http.server
import socketserver
import json
import urllib.parse
import csv
import os
import time
import re
import io


from csv_processor import CSVProcessor
from decision_engine import DecisionEngine
from data_generator import generate_synthetic_dataset

PORT = 8505

# Global in-memory session store
SESSION = {
    "records": None,
    "dataset_name": "None",
    "is_synthetic": False,
    "csv_summary": None,
    "processed_records": None,
    "human_reviews": {},
    "context_config": {
        "business_name": "Ecommerce Laptop & Tech Store",
        "product_description": "Direct sales of high-performance laptops and accessories",
        "relevant_intents": ["buy laptop", "laptop deals", "price", "store near me", "order online"],
        "irrelevant_intents": ["free wallpaper", "teardown", "repair manual", "salary", "jobs"],
        "negative_keywords": ["free", "torrent", "crack", "hack", "teardown", "repair manual", "salary", "jobs", "wikipedia", "cardboard", "diy", "schematic"],
        "min_clicks_threshold": 10,
        "min_cost_threshold": 15.0,
        "target_cpa_threshold": 50.0,
        "roas_threshold": 1.0
    }
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SearchSense AI — Search Term Triage Engine</title>
    <style>
        :root {
            --bg-dark: #0b0f19;
            --surface-dark: #0f172a;
            --card-dark: #1e293b;
            --border-color: #334155;
            --accent-cyan: #38bdf8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            margin: 0;
            display: flex;
            height: 100vh;
        }
        .sidebar {
            width: 260px;
            background-color: var(--surface-dark);
            border-right: 1px solid var(--border-color);
            padding: 24px 18px;
            display: flex;
            flex-direction: column;
        }
        .sidebar h2 { color: var(--accent-cyan); margin: 0 0 4px 0; font-size: 1.4rem; }
        .sidebar p { color: var(--text-muted); font-size: 0.85rem; margin-top: 0; }
        .nav-item {
            padding: 10px 14px;
            margin: 4px 0;
            border-radius: 8px;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .nav-item:hover, .nav-item.active {
            background-color: var(--card-dark);
            color: var(--accent-cyan);
            border-left: 3px solid var(--accent-cyan);
        }
        .main-content {
            flex: 1;
            padding: 30px 40px;
            overflow-y: auto;
        }
        .workflow-bar {
            display: flex;
            justify-content: space-between;
            background: var(--surface-dark);
            padding: 12px 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-bottom: 25px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
        }
        .wf-step.active { color: var(--accent-cyan); border-bottom: 2px solid var(--accent-cyan); }
        .wf-step.completed { color: var(--accent-green); }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 15px;
        }
        .stat-title { color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-value { font-size: 1.8rem; font-weight: 700; margin-top: 4px; }
        
        .btn {
            background: linear-gradient(135deg, #0891b2 0%, #0284c7 100%);
            color: white;
            border: 1px solid var(--accent-cyan);
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
            transition: all 0.2s;
        }
        .btn:hover { box-shadow: 0 0 18px rgba(6, 182, 212, 0.5); }
        
        .badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            display: inline-block;
        }
        .badge-PROMOTE { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; }
        .badge-BLOCK { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; }
        .badge-IGNORE { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid #94a3b8; }
        .badge-REVIEW { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 0.88rem;
        }
        th, td {
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        th { background-color: var(--surface-dark); color: var(--text-muted); }
        tr:hover { background-color: rgba(255,255,255,0.02); }
        
        .banner-synthetic {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid var(--accent-amber);
            color: #fbbf24;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .banner-official {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--accent-green);
            color: #34d399;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 600;
            margin-bottom: 20px;
        }

        .filter-control {
            background-color: var(--surface-dark);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: 6px;
            margin-right: 10px;
        }

        .tab-page { display: none; }
        .tab-page.active { display: block; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🔍 SearchSense AI</h2>
        <p>Explainable Triage Engine</p>
        <hr style="border-color: var(--border-color); margin: 15px 0;">
        <div class="nav-item active" onclick="showTab('overview')">1. Overview</div>
        <div class="nav-item" onclick="showTab('data_studio')">2. Data Studio</div>
        <div class="nav-item" onclick="showTab('analysis')">3. Triage Analysis</div>
        <div class="nav-item" onclick="showTab('review')">4. Human Review Queue</div>
        <div class="nav-item" onclick="showTab('export')">5. Export Centre</div>
        <div class="nav-item" onclick="showTab('about')">6. About & Methodology</div>
    </div>

    <div class="main-content">
        <div class="workflow-bar">
            <span class="wf-step active">STEP 1 — CHOOSE DATA</span>
            <span class="wf-step">STEP 2 — CONFIGURE CONTEXT</span>
            <span class="wf-step">STEP 3 — VALIDATE</span>
            <span class="wf-step">STEP 4 — ANALYSE</span>
            <span class="wf-step">STEP 5 — REVIEW</span>
            <span class="wf-step">STEP 6 — EXPORT</span>
        </div>

        <!-- OVERVIEW TAB -->
        <div id="tab-overview" class="tab-page active">
            <h1>Search Intelligence, Made Explainable</h1>
            <p style="color: var(--text-muted); font-size: 1.1rem;">Turn raw Google Ads search-term data into evidence-backed, explainable triage decisions.</p>

            <div class="stat-grid" style="grid-template-columns: 1fr 1fr;">
                <div class="stat-card">
                    <h3>⚡ Quick Demo Dataset</h3>
                    <p style="color: var(--text-muted);">Load the 25,000 synthetic search-term dataset instantly into session.</p>
                    <button class="btn" onclick="loadDemoDataset()">Load 25,000 Synthetic Rows</button>
                </div>
                <div class="stat-card">
                    <h3>📂 Custom CSV / Excel Upload</h3>
                    <p style="color: var(--text-muted);">Upload official hackathon CSV/Excel or compatible search report.</p>
                    <button class="btn" onclick="showTab('data_studio')">Go to Data Studio Upload</button>
                </div>
            </div>

            <h3 style="margin-top: 30px;">📊 Active Dataset Overview</h3>
            <div id="overview-metrics" class="stat-grid">
                <div class="stat-card"><div class="stat-title">Loaded Records</div><div class="stat-value" id="val-loaded">0</div></div>
                <div class="stat-card"><div class="stat-title">Promote</div><div class="stat-value" style="color:var(--accent-green);" id="val-promote">-</div></div>
                <div class="stat-card"><div class="stat-title">Block</div><div class="stat-value" style="color:var(--accent-red);" id="val-block">-</div></div>
                <div class="stat-card"><div class="stat-title">Ignore</div><div class="stat-value" style="color:var(--text-muted);" id="val-ignore">-</div></div>
                <div class="stat-card"><div class="stat-title">Human Review</div><div class="stat-value" style="color:var(--accent-amber);" id="val-review">-</div></div>
            </div>
        </div>

        <!-- DATA STUDIO TAB -->
        <div id="tab-data_studio" class="tab-page">
            <h2>📂 Data Studio — Flexible CSV & Excel Upload</h2>
            <p style="color: var(--text-muted);">Upload your Google Ads Search Term report (.csv, .xls, or .xlsx) or inspect loaded dataset schema.</p>
            
            <div class="stat-card" style="margin-bottom: 20px;">
                <h3>Upload Worksheet / CSV File</h3>
                <p style="color: var(--text-muted); font-size: 0.85rem;">Supported formats: Legacy Excel (.xls via xlrd), Modern Excel (.xlsx via openpyxl), and CSV (.csv)</p>
                <input type="file" id="csvFileInput" accept=".csv, .xls, .xlsx" style="margin: 10px 0; color: white;">
                <button class="btn" onclick="uploadCSVFile()">Upload & Parse File</button>
            </div>


            <div id="synthetic-banner-div" class="banner-synthetic" style="display:none;">
                SYNTHETIC DEMONSTRATION DATA ACTIVE — NOT OFFICIAL HACKATHON DATA
            </div>
            <div id="official-banner-div" class="banner-official" style="display:none;">
                OFFICIAL / USER SUPPLIED DATASET LOADED
            </div>

            <h3>Data Preview (First 50 Rows)</h3>
            <div id="data-preview-table" style="overflow-x: auto;"></div>
        </div>

        <!-- TRIAGE ANALYSIS TAB -->
        <div id="tab-analysis" class="tab-page">
            <h2>⚙️ Triage Analysis & Decision Engine</h2>
            <p style="color: var(--text-muted);">Configure business rules and execute explainable triage pipeline.</p>
            
            <div class="stat-card" style="margin-bottom: 20px;">
                <button class="btn" style="font-size: 1.1rem; padding: 14px 28px;" onclick="runAnalysis()">🚀 ANALYSE SEARCH TERMS NOW</button>
                <span id="analysis-status" style="margin-left: 20px; color: var(--accent-cyan); font-weight: 600;"></span>
            </div>

            <div class="stat-card">
                <h3>🔍 Filter & Search Results</h3>
                <input type="text" id="search-query-input" placeholder="Search query text..." class="filter-control" onkeyup="filterResults()">
                <select id="filter-decision-select" class="filter-control" onchange="filterResults()">
                    <option value="ALL">All Decisions</option>
                    <option value="PROMOTE">PROMOTE</option>
                    <option value="BLOCK">BLOCK</option>
                    <option value="IGNORE">IGNORE</option>
                    <option value="HUMAN REVIEW">HUMAN REVIEW</option>
                </select>
                <span id="result-count-label" style="color: var(--text-muted); margin-left: 10px;"></span>
            </div>

            <h3>Results Explorer</h3>
            <div id="results-table-container" style="overflow-x: auto;"></div>
            <div id="results-pagination" style="margin-top: 15px; display: flex; gap: 10px; align-items: center;"></div>
        </div>

        <!-- HUMAN REVIEW TAB -->
        <div id="tab-review" class="tab-page">
            <h2>🙋 Human Review Workspace</h2>
            <p style="color: var(--text-muted);">Inspect and override low-confidence, ambiguous, or high-spend search terms.</p>
            <div id="review-queue-container"></div>
        </div>

        <!-- EXPORT TAB -->
        <div id="tab-export" class="tab-page">
            <h2>📥 Export Centre</h2>
            <p style="color: var(--text-muted);">Download full analysis CSV or specific decision action lists (includes reviewer overrides).</p>
            
            <div class="stat-grid" style="grid-template-columns: 1fr 1fr;">
                <div class="stat-card">
                    <h3>1. Complete Triage CSV</h3>
                    <button class="btn" onclick="downloadCSV('/api/export?type=full')">Download Complete Results CSV</button>
                </div>
                <div class="stat-card">
                    <h3>2. Negative Keyword Blocklist</h3>
                    <button class="btn" onclick="downloadCSV('/api/export?type=block')">Download Negative Keywords (BLOCK)</button>
                </div>
                <div class="stat-card">
                    <h3>3. Promotion Targets</h3>
                    <button class="btn" onclick="downloadCSV('/api/export?type=promote')">Download Target Keywords (PROMOTE)</button>
                </div>
                <div class="stat-card">
                    <h3>4. Human Review Queue & Overrides</h3>
                    <button class="btn" onclick="downloadCSV('/api/export?type=review')">Download Human Review Exports</button>
                </div>
            </div>
        </div>

        <!-- ABOUT TAB -->
        <div id="tab-about" class="tab-page">
            <h2>📖 About SearchSense AI & Methodology</h2>
            <p><strong>Official Problem Statement:</strong> PS-01 — Search Term Triage Engine.</p>
            <p><strong>Core Architectural Principles:</strong></p>
            <ul>
                <li><strong>Transparent Rules:</strong> Every decision is backed by explicit text relevance and performance evidence.</li>
                <li><strong>Cautious Uncertainty Routing:</strong> Low-confidence or conflicting metrics route safely to <strong>HUMAN REVIEW</strong>.</li>
                <li><strong>100% Offline Local Execution:</strong> Zero third-party API key requirements or external data transmissions.</li>
            </ul>
        </div>
    </div>

    <script>
        let allProcessedRecords = [];
        let filteredRecords = [];
        let currentPage = 1;
        const pageSize = 50;

        function showTab(tabId) {
            document.querySelectorAll('.tab-page').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            event.target.classList.add('active');
            refreshState();
        }

        async function refreshState() {
            let res = await fetch('/api/state');
            let data = await res.json();
            
            document.getElementById('val-loaded').innerText = data.total_records.toLocaleString();
            if (data.analysis_done) {
                document.getElementById('val-promote').innerText = data.decision_counts.PROMOTE || 0;
                document.getElementById('val-block').innerText = data.decision_counts.BLOCK || 0;
                document.getElementById('val-ignore').innerText = data.decision_counts.IGNORE || 0;
                document.getElementById('val-review').innerText = data.decision_counts['HUMAN REVIEW'] || 0;
            }

            if (data.is_synthetic) {
                document.getElementById('synthetic-banner-div').style.display = 'block';
                document.getElementById('official-banner-div').style.display = 'none';
            } else if (data.total_records > 0) {
                document.getElementById('synthetic-banner-div').style.display = 'none';
                document.getElementById('official-banner-div').style.display = 'block';
            }

            renderPreview(data.preview_records);
            
            if (data.analysis_done && allProcessedRecords.length === 0) {
                fetchFullProcessed();
            }
            renderReviewQueue(data.review_queue);
        }

        async function fetchFullProcessed() {
            let res = await fetch('/api/get_full_processed');
            let data = await res.json();
            allProcessedRecords = data.records;
            filterResults();
        }

        async function loadDemoDataset() {
            let res = await fetch('/api/load_demo');
            let data = await res.json();
            alert('Loaded ' + data.count.toLocaleString() + ' synthetic 25,000 records!');
            allProcessedRecords = [];
            refreshState();
        }

        async function runAnalysis() {
            document.getElementById('analysis-status').innerText = 'Analyzing queries...';
            let res = await fetch('/api/analyze');
            let data = await res.json();
            document.getElementById('analysis-status').innerText = 'Analyzed ' + data.count.toLocaleString() + ' records successfully!';
            fetchFullProcessed();
            refreshState();
        }

        function filterResults() {
            let search = document.getElementById('search-query-input').value.toLowerCase();
            let decision = document.getElementById('filter-decision-select').value;

            filteredRecords = allProcessedRecords.filter(r => {
                let matchSearch = !search || r.query_text.toLowerCase().includes(search);
                let matchDec = (decision === 'ALL') || (r.decision === decision);
                return matchSearch && matchDec;
            });

            currentPage = 1;
            renderPaginatedResults();
        }

        function renderPaginatedResults() {
            let container = document.getElementById('results-table-container');
            let countLabel = document.getElementById('result-count-label');
            
            if (!filteredRecords || filteredRecords.length === 0) {
                container.innerHTML = '<p style="color:var(--text-muted)">No matching analysis records found.</p>';
                countLabel.innerText = 'Displaying 0 of ' + allProcessedRecords.length.toLocaleString() + ' records';
                document.getElementById('results-pagination').innerHTML = '';
                return;
            }

            let start = (currentPage - 1) * pageSize;
            let end = start + pageSize;
            let pageRecords = filteredRecords.slice(start, end);
            let totalPages = Math.ceil(filteredRecords.length / pageSize);

            countLabel.innerText = `Displaying ${start + 1} - ${Math.min(end, filteredRecords.length)} of ${filteredRecords.length.toLocaleString()} filtered records (Total: ${allProcessedRecords.length.toLocaleString()})`;

            let html = '<table><thead><tr><th>Row ID</th><th>Query Text</th><th>Campaign</th><th>Clicks</th><th>Cost ($)</th><th>Convs</th><th>Decision</th><th>Confidence</th><th>Explanation</th></tr></thead><tbody>';
            pageRecords.forEach(r => {
                let badgeClass = 'badge-' + (r.decision === 'HUMAN REVIEW' ? 'REVIEW' : r.decision);
                html += `<tr><td>${r.source_row_id}</td><td>${r.query_text}</td><td>${r.campaign}</td><td>${r.clicks ?? 0}</td><td>$${(r.cost ?? 0).toFixed(2)}</td><td>${r.conversions ?? 0}</td><td><span class="badge ${badgeClass}">${r.decision}</span></td><td>${r.confidence}</td><td>${r.explanation}</td></tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;

            // Pagination Controls
            let pagHtml = `<button class="btn" style="padding:6px 14px;" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(-1)">Previous</button>`;
            pagHtml += `<span style="color:var(--text-muted)">Page ${currentPage} of ${totalPages}</span>`;
            pagHtml += `<button class="btn" style="padding:6px 14px;" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(1)">Next</button>`;
            document.getElementById('results-pagination').innerHTML = pagHtml;
        }

        function changePage(delta) {
            currentPage += delta;
            renderPaginatedResults();
        }

        function renderPreview(records) {
            if (!records || records.length === 0) {
                document.getElementById('data-preview-table').innerHTML = '<p style="color:var(--text-muted)">No data loaded yet.</p>';
                return;
            }
            let html = '<table><thead><tr><th>ID</th><th>Query Text</th><th>Campaign</th><th>Ad Group</th><th>Clicks</th><th>Cost ($)</th><th>Conversions</th></tr></thead><tbody>';
            records.forEach(r => {
                html += `<tr><td>${r.source_row_id}</td><td>${r.query_text}</td><td>${r.campaign}</td><td>${r.ad_group}</td><td>${r.clicks ?? 0}</td><td>$${(r.cost ?? 0).toFixed(2)}</td><td>${r.conversions ?? 0}</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('data-preview-table').innerHTML = html;
        }

        function renderReviewQueue(queue) {
            let container = document.getElementById('review-queue-container');
            if (!queue || queue.length === 0) {
                container.innerHTML = '<div class="stat-card"><h3>✅ No Items Pending Review</h3><p style="color:var(--text-muted)">All records passed automated decision thresholds or analysis has not been executed.</p></div>';
                return;
            }

            let html = `<p style="color:var(--text-muted)">Showing <strong>${queue.length.toLocaleString()}</strong> records flagged for human review</p>`;
            queue.slice(0, 30).forEach(r => {
                html += `
                <div class="stat-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0;">[${r.source_row_id}] Query: "${r.query_text}"</h3>
                        <span class="badge badge-REVIEW">HUMAN REVIEW</span>
                    </div>
                    <p style="margin:8px 0; color:var(--text-muted);">Campaign: ${r.campaign} | Clicks: ${r.clicks ?? 0} | Cost: $${(r.cost ?? 0).toFixed(2)} | Convs: ${r.conversions ?? 0}</p>
                    <p><strong>System Explanation:</strong> ${r.explanation}</p>
                    <p><strong>Recommended Action:</strong> ${r.recommended_action}</p>
                    <div style="margin-top:12px; display:flex; gap:10px; align-items:center;">
                        <select id="rev-choice-${r.source_row_id}" class="filter-control">
                            <option value="HUMAN REVIEW" ${r.reviewer_decision === 'HUMAN REVIEW' ? 'selected' : ''}>HUMAN REVIEW (Default)</option>
                            <option value="PROMOTE" ${r.reviewer_decision === 'PROMOTE' ? 'selected' : ''}>PROMOTE (Override)</option>
                            <option value="BLOCK" ${r.reviewer_decision === 'BLOCK' ? 'selected' : ''}>BLOCK (Override)</option>
                            <option value="IGNORE" ${r.reviewer_decision === 'IGNORE' ? 'selected' : ''}>IGNORE (Override)</option>
                        </select>
                        <input type="text" id="rev-note-${r.source_row_id}" placeholder="Reviewer note..." value="${r.reviewer_note || ''}" class="filter-control" style="flex:1;">
                        <button class="btn" onclick="saveReviewOverride('${r.source_row_id}')">Save Decision</button>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        async function saveReviewOverride(rowId) {
            let choice = document.getElementById('rev-choice-' + rowId).value;
            let note = document.getElementById('rev-note-' + rowId).value;

            let res = await fetch('/api/save_review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row_id: rowId, reviewer_decision: choice, reviewer_note: note })
            });
            let data = await res.json();
            alert('Review decision saved for ' + rowId);
            refreshState();
        }

        function downloadCSV(url) {
            window.location.href = url;
        }

        async function uploadCSVFile() {
            let input = document.getElementById('csvFileInput');
            if (input.files.length === 0) { alert('Select a CSV file first'); return; }
            let formData = new FormData();
            formData.append('file', input.files[0]);
            let res = await fetch('/api/upload', { method: 'POST', body: formData });
            let data = await res.json();
            alert('Uploaded ' + data.count.toLocaleString() + ' records!');
            allProcessedRecords = [];
            refreshState();
        }

        refreshState();
    </script>
</body>
</html>
"""

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            return

        elif path == "/api/state":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            recs = SESSION["records"] or []
            p_recs = SESSION["processed_records"] or []

            counts = {}
            review_queue = []

            if p_recs:
                for r in p_recs:
                    d = r.get("decision", "UNKNOWN")
                    counts[d] = counts.get(d, 0) + 1
                    if d == "HUMAN REVIEW":
                        # Attach existing reviewer override if present
                        rev_info = SESSION["human_reviews"].get(r["source_row_id"], {})
                        r_copy = dict(r)
                        r_copy["reviewer_decision"] = rev_info.get("reviewer_decision", "HUMAN REVIEW")
                        r_copy["reviewer_note"] = rev_info.get("reviewer_note", "")
                        review_queue.append(r_copy)

            data = {
                "total_records": len(recs),
                "is_synthetic": SESSION["is_synthetic"],
                "analysis_done": SESSION["processed_records"] is not None,
                "decision_counts": counts,
                "preview_records": recs[:50],
                "review_queue": review_queue
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        elif path == "/api/get_full_processed":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            p_recs = SESSION["processed_records"] or []
            self.wfile.write(json.dumps({"records": p_recs}).encode('utf-8'))
            return

        elif path == "/api/load_demo":
            if not os.path.exists("data/sample_search_terms_25000.csv"):
                generate_synthetic_dataset()
            
            records, summary = CSVProcessor.load_and_standardize_csv("data/sample_search_terms_25000.csv")
            SESSION["records"] = records
            SESSION["dataset_name"] = "sample_search_terms_25000.csv"
            SESSION["is_synthetic"] = True
            SESSION["csv_summary"] = summary
            SESSION["processed_records"] = None

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"count": len(records)}).encode('utf-8'))
            return

        elif path == "/api/analyze":
            if not SESSION["records"]:
                self.send_response(400)
                self.end_headers()
                return

            engine = DecisionEngine(SESSION["context_config"])
            p_records = engine.process_records(SESSION["records"])
            SESSION["processed_records"] = p_records

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"count": len(p_records)}).encode('utf-8'))
            return

        elif path == "/api/export":
            query_params = urllib.parse.parse_qs(parsed.query)
            exp_type = query_params.get("type", ["full"])[0]

            p_recs = SESSION["processed_records"] or []
            
            # Enrich records with human overrides
            enriched_records = []
            for r in p_recs:
                r_copy = dict(r)
                rev_info = SESSION["human_reviews"].get(r["source_row_id"], {})
                r_copy["final_decision"] = rev_info.get("reviewer_decision", r.get("decision"))
                r_copy["reviewer_note"] = rev_info.get("reviewer_note", "")
                enriched_records.append(r_copy)

            if exp_type == "block":
                export_data = [r for r in enriched_records if r.get("final_decision") == "BLOCK" or r.get("decision") == "BLOCK"]
            elif exp_type == "promote":
                export_data = [r for r in enriched_records if r.get("final_decision") == "PROMOTE" or r.get("decision") == "PROMOTE"]
            elif exp_type == "review":
                export_data = [r for r in enriched_records if r.get("decision") == "HUMAN REVIEW" or r.get("reviewer_note")]
            else:
                export_data = enriched_records

            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header("Content-Disposition", f"attachment; filename=searchsense_{exp_type}.csv")
            self.end_headers()

            if export_data:
                fieldnames = list(export_data[0].keys())
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_data)
                self.wfile.write(output.getvalue().encode('utf-8'))
            else:
                self.wfile.write(b"No data available for export.")
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if self.path == "/api/save_review":
            req_data = json.loads(body.decode('utf-8'))
            row_id = req_data.get("row_id")
            reviewer_decision = req_data.get("reviewer_decision")
            reviewer_note = req_data.get("reviewer_note")

            SESSION["human_reviews"][row_id] = {
                "reviewer_decision": reviewer_decision,
                "reviewer_note": reviewer_note,
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "row_id": row_id}).encode('utf-8'))
            return

        elif self.path == "/api/upload":
            content_type = self.headers.get('Content-Type')
            boundary = content_type.split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)
            file_data = None
            filename = "uploaded_file.csv"
            
            for part in parts:
                if b'filename=' in part:
                    header, file_bytes = part.split(b'\r\n\r\n', 1)
                    file_data = file_bytes.rsplit(b'\r\n', 1)[0]
                    # Extract original filename
                    header_str = header.decode('utf-8', errors='ignore')
                    match = re.search(r'filename="([^"]+)"', header_str)
                    if match:
                        filename = match.group(1)
                    break

            if file_data:
                try:
                    records, summary = CSVProcessor.load_and_standardize_file(file_data, filename)
                    SESSION["records"] = records
                    SESSION["dataset_name"] = filename
                    SESSION["is_synthetic"] = False
                    SESSION["csv_summary"] = summary
                    SESSION["processed_records"] = None

                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "count": len(records),
                        "filename": filename,
                        "sheet_names": summary.get("sheet_names", []),
                        "selected_sheet": summary.get("selected_sheet", "")
                    }).encode('utf-8'))
                    return
                except Exception as e:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                    return

        self.send_response(400)
        self.end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"SearchSense AI Web Server running live at http://localhost:{PORT}")
        httpd.serve_forever()
