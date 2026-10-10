# System Architecture

PS-03 Message Match Auditor is organized into decoupled layers: Core, Schemas, Services, API, and Frontend.

```
                      ┌────────────────────────────┐
                      │    React + Vite Client     │
                      │  Dashboard / New / Results │
                      └─────────────┬──────────────┘
                                    │ HTTP / JSON / Multipart
                                    ▼
                      ┌────────────────────────────┐
                      │    FastAPI HTTP Router     │
                      │  /api/audit, /api/export   │
                      └──────┬──────────────┬──────┘
                             │              │
              ┌──────────────▼───┐     ┌────▼──────────────┐
              │ Live URL Fetch   │     │ HTML Snapshot     │
              │ (SSRF Protected) │     │ (Validated Plain) │
              └──────────────┬───┘     └────┬──────────────┘
                             │              │
                             ▼              ▼
                      ┌────────────────────────────┐
                      │  Extraction Service        │
                      │  • Passive BS4 / lxml      │
                      │  • Hidden text removal     │
                      │  • JS shell validation     │
                      └─────────────┬──────────────┘
                                    │ Normalized Text + Elements
                                    ▼
                      ┌────────────────────────────┐
                      │  Claims & Matching Service │
                      │  • Atomic claim extraction │
                      │  • Entity comparison       │
                      │  • verify_quote() check    │
                      └─────────────┬──────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
       ┌───────────────────────────┐ ┌───────────────────────────┐
       │   Explainable Scoring     │ │     CTA Analysis &        │
       │   • Material weights 2.0x │ │   Action Friction Check   │
       │   • Cap 40 if contradicted│ └───────────────────────────┘
       └─────────────┬─────────────┘
                     ▼
       ┌───────────────────────────┐
       │ Export & Report Service   │
       │ HTML / CSV (Escaped)      │
       └───────────────────────────┘
```

---

## Modular Separation

1. `backend/app/core/`:
   - `config.py`: Thresholds and limits.
   - `security.py`: SSRF validation, IPv4-mapped IPv6, DNS resolution checking.
2. `backend/app/schemas/`:
   - `audit.py`: Pydantic v2 schemas (`AuditRequest`, `AuditResponse`, `ClaimAudit`, `ClaimContribution`, `CtaComparison`, `ScoreBreakdown`).
3. `backend/app/services/`:
   - `extraction.py`: Safe network fetching and passive DOM text extraction.
   - `claims.py`: Atomic clause splitting and categorization.
   - `evidence.py`: Deterministic substring quote verification (`verify_quote()`).
   - `matching.py`: Rapidfuzz comparison, contradiction heuristics, CTA analysis.
   - `scoring.py`: Documented mathematical scoring formula and per-claim contribution table.
   - `recommendations.py`: Prioritized copy improvement suggestions.
   - `export.py`: Self-contained HTML report, CSV formula injection mitigation, and JSON formatting.
   - `demo_data.py`: 7 real synthetic scenarios backed by `sample_data/pages/`.
4. `frontend/`:
   - React Router navigation (`/`, `/audit/new`, `/audit/result`).
   - Clean light theme with navy accents and WCAG AA contrast.
   - Accessible metric cards, quote inspector, and formula explanation.
