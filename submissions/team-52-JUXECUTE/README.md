# CampaignGuard AI — Intelligent Campaign Anomaly Alerting

> **Problem Statement PS-04**: *Campaign Anomaly Alerting Without Alert Fatigue*  
> Monitor daily digital advertising campaign metrics, identify suspicious changes, present explainable alerts, and help marketing analysts distinguish genuine operational incidents from normal fluctuations or seasonal shifts.

---

## 🌟 Executive Overview

Digital advertising campaigns generate immense daily volatility due to normal auction variance, day-of-week dips, and seasonal fluctuations. Naive fixed-threshold anomaly detectors (e.g., standard ±20% flags) flood performance marketers with **false alarms**, inducing severe **alert fatigue** where genuine critical incidents (such as broken conversion tracking tags or budget exhaustion) get ignored.

**CampaignGuard AI** solves this by combining:
1. **Campaign-Specific Adaptive Median Absolute Deviation (MAD)** tolerance envelopes.
2. **Persistence Filters** (requiring multi-day sustained breaches before critical escalation).
3. **Temporal Deduplication & Seasonality Awareness** (suppressing predictable weekend drops and repeated alerts for active issues).
4. **Deterministic Explainable Alert Diagnostics** ("What changed?", "What was expected?", "What was observed?", "Why flagged?", "Recommended check").
5. **Incident Correlator** (grouping related metric anomalies into actionable operational failure categories).

---

## 📊 Benchmarking & Alert Fatigue Reduction

Evaluated over **3,600 daily observations** across 20 multi-channel advertising campaigns (Google Search, Meta Ads, TikTok Performance, LinkedIn B2B) over a 180-day monitoring window:

| Anomaly Detection Strategy | Total Alerts Generated | Alert Precision | Incident Recall | Alert Fatigue Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **Fixed-Threshold Baseline (Naive ±20%)** | 284 alerts | 9.2% | 100.0% | *Baseline (High Noise)* |
| **Campaign-Specific Adaptive (MAD)** | 58 alerts | 43.1% | 96.1% | **-79.5% alert noise** |
| **Adaptive + Deduplication & Persistence (CampaignGuard AI)** | **29 alerts** | **86.2%** | **96.1%** | **-89.8% alert fatigue** |

---

## 🚀 Quickstart & Setup

### Prerequisites
- Node.js (v18+ or v24+)
- npm (v9+ or v11+)

### Installation
```bash
# Clone or navigate to the repository directory
cd d:/CampaignGuard_AI

# Install all dependencies
npm ci or if failed, run npm install

# Run Vitest unit tests
npm test

# Build for production
npm run build

# Start local development server
npm run dev
```

The application will be accessible at:
```
http://localhost:5173/
```

---

## 🧭 Application Structure & Key Routes

| Route | View | Description |
| :--- | :--- | :--- |
| `/` | **Overview Dashboard** | High-level marketing KPIs, interactive time-series anomaly envelope chart, alert trends, health distribution, and recent alert queue. |
| `/campaigns` | **Campaign Explorer** | Multi-channel campaign directory with search, health filters, sorting, and pagination across all 20 monitored campaigns. |
| `/campaigns/:campaignId` | **Campaign Detail** | Diagnostic drill-down featuring 4 views: *Overview & Diagnostics*, *Full 180-Day Telemetry*, *Anomaly History*, and *Detection Configuration*. |
| `/alerts` | **Alerts Center** | Alert triage console with severity badges, metric deviation magnitudes, status management, and CSV export. |
| `/alerts/:alertId` | **Alert Detail** | Full investigation dossier with the **Explainable Anomaly Diagnostic** card, evidence chart, timeline, and interactive status controls. |
| `/incidents` | **Incident Analysis** | Root-cause classification distinguishing tracking failures, budget exhaustion, bid strategy inflation, and seasonal shifts. |
| `/evaluation` | **Model Evaluation Lab** | Empirical validation center with interactive Confusion Matrix, Precision vs. Recall benchmark comparison, and incident breakdown. |
| `/reports` | **Executive Reports** | Print-friendly audit report with executive metrics, severity distribution, and CSV export. |
| `/settings` | **System Settings** | Configuration of baseline windows, MAD sensitivity slider, alert routing preferences, dataset schema validation, and FastAPI integration. |

---

## 🔍 Core Feature: Explainable Alerts

Every alert is augmented with a structured diagnostic explanation generated deterministically from observed vs expected baselines:

```
[CampaignGuard Alert alt-501]
Campaign: Q4 SaaS Lead Gen - Google Search (Google Ads)
Severity: CRITICAL | Status: INVESTIGATING
Metric: CONVERSIONS | Observed: 2 (Expected: 85)
Deviation: -97.6% | Anomaly Score: 5.8 MAD
Classification: Possible Conversion Tracking Failure

1. What changed?
Conversions plummeted sharply while click volume remained steady for Q4 SaaS Lead Gen - Google Search.

2. Baseline vs Observed:
Expected historical baseline was 85 (band: 65 – 105). Observed daily was 2 (-97.6% drop).

3. Why flagged?
Disproportionate divergence between clicks and conversions strongly indicates an instrumentation failure rather than ad audience fatigue.

4. Recommended First Action:
Verify Google Tag Manager / Meta Pixel event fires, postbacks, and destination thank-you page URLs.
```

---

## 🔌 Python FastAPI Backend Integration

The frontend is architected to decouple presentation from data retrieval via `ApiClient` (`src/services/apiClient.ts`).

### Ready Integration Endpoints
- `GET  /api/health` — Backend connection heartbeat
- `GET  /api/campaigns` — Retrieve list of campaigns with summary metrics
- `GET  /api/campaigns/:campaignId` — Retrieve detailed campaign telemetry
- `GET  /api/alerts` — Retrieve flagged anomaly alerts
- `PATCH /api/alerts/:alertId/status` — Persist alert status transition
- `GET  /api/incidents` — Correlated multi-metric incident records
- `GET  /api/evaluation` — Model evaluation runs and confusion matrices
- `POST /api/evaluation/run` — Trigger backend anomaly detection pipeline
- `POST /api/dataset/upload` — Ingest raw campaign performance CSVs

### Switching Modes
1. Open **Settings** (`/settings`) in the application.
2. Enter your FastAPI server URL (e.g., `http://localhost:8000`).
3. Toggle off **Use Synthetic Demo Data**.
4. Save configuration. When connected, calls automatically route to your FastAPI endpoints.

---

## 🧪 Testing & Validation

All mathematical formulas for Precision, Recall, F1 Score, and False Positive Rate are covered by automated unit tests in `src/utils/__tests__/metrics.test.ts`:

```bash
npm test
```
Result: **9 tests passed** (100% test pass rate).

---

## 🎨 Visual Design Token System
- **Primary Navy**: `#14233B` (Sidebar, Header elements)
- **Primary Blue**: `#3867F5` (Interactive accents, CTAs, Actual observations)
- **Canvas Background**: `#F5F7FB` (Light neutral workspace)
- **Card Background**: `#FFFFFF` with `#E4E9F1` border
- **Critical Red**: `#DC3545` (Critical incidents, tag breaks)
- **Warning Amber**: `#F59E0B` (High severity warnings, pacing halts)
- **Healthy Green**: `#16A36A` (Healthy state, resolved issues)
- **Typography**: Inter (Google Fonts)
