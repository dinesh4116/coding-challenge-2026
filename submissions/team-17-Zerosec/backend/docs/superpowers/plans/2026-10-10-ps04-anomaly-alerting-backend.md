# PS-04 Campaign Anomaly Alerting Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend that reads daily campaign metrics from a CSV and flags anomalies using bands built from each campaign's own history. Each alert carries a plain-English explanation. Repeat alerts are grouped and suppressed. Breakages are kept separate from seasonality. The backend reports the total number of alerts fired and measures precision and recall against the seeded incidents.

**Architecture:** The CSV goes through five pure-function stages:
1. **loader:** normalizes the CSV to a canonical schema.
2. **features:** adds derived ratios such as CTR and CVR.
3. **detector:** compares each day with a rolling median/MAD band built from that campaign's past days only.
4. **alert manager:** groups anomalies by campaign and day, flags portfolio-wide (seasonal) shifts, then turns daily findings into alert episodes with cooldown, escalation and reopen rules.
5. **evaluation:** compares alerts with the incident labels and with a naive "±30%" baseline.

FastAPI routes and a CLI are thin wrappers around one `pipeline.analyze_*` function. No database: every request is analyzed from scratch and gives the same result each time.

**Tech Stack:** Python 3.14 (any 3.11+ works), FastAPI, Uvicorn, pandas 3, NumPy, Pydantic v2, python-multipart, pytest, httpx (needed by FastAPI's TestClient). All of these are already installed on this machine.

**Spec:** `docs/superpowers/specs/2026-10-10-ps04-spec.md`

## Global Constraints

- Project root is `D:\backend` (run every command from there). The package is `app/`. Start the server with `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- No dependencies beyond: fastapi, uvicorn, pandas, numpy, pydantic, python-multipart, pytest, httpx.
- No database, no external API and no ML model. Nothing in memory is expected to survive a restart, and nothing should claim to.
- Uploaded files are processed in memory and never written to disk. Row-level data is never logged.
- Responses never contain NaN or Infinity. Missing or undefined numbers are `null`.
- The anomaly score is a robust z-score. Docs and API field descriptions must call it a "heuristic score, not a probability".
- Causes are always worded as possibilities ("may indicate", "possible"). The words "confirmed" and "caused by" never appear in generated text.
- Synthetic data is labeled SYNTHETIC wherever it appears: the API response, `data/README.md` and the main README.
- CORS origins come from the `CORS_ORIGINS` environment variable (comma-separated). The default is `http://localhost:5173,http://127.0.0.1:5173`. Never use `*`.
- Detection defaults (shared by the API, the CLI and the docs): `window_days=28`, `min_history=14`, `z_threshold=3.5`, `high_z=6.0`, `critical_z=10.0`, `rel_floor=0.02`, `min_pct_change=0.05`, `cooldown_days=3`, `portfolio_share=0.5`, `portfolio_min_pct=0.15`, `min_portfolio_campaigns=5`, `match_tolerance_days=2`.
- Upload limits: `MAX_UPLOAD_MB=10` and `MAX_ROWS=200000`, both overridable by environment variable.
- The user must be able to explain every module. Prefer plain loops and named helpers to clever pandas one-liners. Every module starts with a docstring of 3 to 6 lines saying what it does and why.

## Review Focus

- **The official CSV uses different header names** (`Campaign`, `Day`, `Cost`, `Conv.`). It should load through the alias map rather than be rejected. Tested in Task 3.
- **Excel-formatted numbers** (`"$1,234.50"`, `"1,200"`). They should parse as numbers rather than becoming NaN. Tested in Task 3.
- **A CSV saved by Excel** with a UTF-8 BOM and `;` delimiters. It should load normally. Tested in Task 3.
- **Campaign IDs with leading zeros** (`007`). They must stay strings, so `007` does not become `7` and merge with another campaign. Tested in Task 3.
- **A portfolio with fewer than 5 campaigns.** The seasonality rule must not fire: three campaigns moving together are not evidence of a market-wide shift. Tested in Task 7.

---

## File Structure

```
D:\backend
├── app/
│   ├── __init__.py
│   ├── config.py            # Settings from env (CORS, upload limits, app name/version)
│   ├── main.py              # FastAPI app factory, CORS, router include
│   ├── schemas.py           # Pydantic response models (the frontend contract)
│   ├── cli.py               # `python -m app.cli file.csv` → prints total alerts + P/R
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # /api/health, /api/demo-data, /api/analyze, /api/analyze/demo
│   └── services/
│       ├── __init__.py
│       ├── data_loader.py   # CSV bytes → canonical daily frame + warnings
│       ├── features.py      # derived ratio metrics with min-denominator guard
│       ├── detector.py      # rolling median/MAD scoring → Anomaly list + score table
│       ├── diagnosis.py     # pattern → alert_type, explanation, causes, first steps
│       ├── alert_manager.py # grouping, seasonality, episodes, cooldown, escalation, routing
│       ├── evaluation.py    # precision/recall vs labels, naive ±30% baseline
│       └── pipeline.py      # orchestrates the stages → AnalysisResponse
├── scripts/
│   ├── __init__.py
│   └── generate_demo_data.py  # deterministic SYNTHETIC dataset with seeded incidents
├── data/
│   ├── demo_campaigns.csv   # generated, SYNTHETIC
│   ├── README.md            # says it is synthetic + lists seeded incidents
│   └── official/            # (empty; drop the official CSV here when provided)
├── tests/
│   ├── conftest.py          # make_campaign_df helper, TestClient fixture
│   ├── test_api.py
│   ├── test_demo_data.py
│   ├── test_data_loader.py
│   ├── test_features.py
│   ├── test_detector.py
│   ├── test_diagnosis.py
│   ├── test_alert_manager.py
│   ├── test_evaluation.py
│   └── test_cli.py
├── docs/CODE_WALKTHROUGH.md # presenter's guide: module-by-module + likely judge Q&A
├── pytest.ini
├── requirements.txt
└── README.md
```

---

### Task 1: Scaffold, config, health endpoint, CORS

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `app/__init__.py`, `app/config.py`, `app/main.py`, `app/api/__init__.py`, `app/api/routes.py`, `app/services/__init__.py`, `scripts/__init__.py`, `data/official/.gitkeep`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_api.py`

**Interfaces:**
- Produces:
  - `app.config.Settings`: a frozen dataclass with `app_name: str = "PS-04 Campaign Anomaly Alerting"`, `version: str = "0.1.0"`, `cors_origins: list[str]`, `max_upload_bytes: int`, `max_rows: int`.
  - `app.config.get_settings() -> Settings`: reads the `CORS_ORIGINS`, `MAX_UPLOAD_MB` and `MAX_ROWS` environment variables.
  - `app.main.create_app() -> FastAPI` and the module-level `app = create_app()`.
  - `app.api.routes.router: APIRouter`, mounted with `prefix="/api"`.
  - `tests/conftest.py` fixture `client` (a TestClient around `create_app()`).

- [ ] **Step 1: Initialize the repository.** Run `git init`. Write `.gitignore` with `__pycache__/`, `.venv/`, `.pytest_cache/` and `*.pyc`. Write `requirements.txt` with these lines: `fastapi>=0.110`, `uvicorn>=0.29`, `pandas>=2.2`, `numpy>=1.26`, `pydantic>=2.6`, `python-multipart>=0.0.9`, `pytest>=8`, `httpx>=0.27`. Write `pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 2: Write the failing tests** in `tests/test_api.py`:

```python
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "app": "PS-04 Campaign Anomaly Alerting", "version": "0.1.0"}

def test_cors_allows_vite_origin(client):
    r = client.options("/api/health", headers={"Origin": "http://localhost:5173",
                                               "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_rejects_unknown_origin(client):
    r = client.options("/api/health", headers={"Origin": "http://evil.example",
                                               "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers

def test_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    from app.config import get_settings
    assert get_settings().cors_origins == ["http://a.test", "http://b.test"]
```

- [ ] **Step 3: Run the tests and confirm they fail.** Run `python -m pytest tests/test_api.py -v`. Expected: an ImportError or collection error for `app`.

- [ ] **Step 4: Implement the config, the app factory and the health route.** `create_app()` reads `get_settings()` when it is called, not at import time, so tests can change the environment. It adds `CORSMiddleware` with the configured origins, `allow_methods=["GET","POST","OPTIONS"]` and `allow_headers=["*"]`, then includes the router. The health route returns `{"status":"ok","app":settings.app_name,"version":settings.version}`.

- [ ] **Step 5: Run the tests and confirm they pass.** Run `python -m pytest tests/test_api.py -v`. Expected: 4 passed.

- [ ] **Step 6: Commit.** `git add -A && git commit -m "feat: scaffold FastAPI app with health endpoint and env-driven CORS"`

---

### Task 2: Synthetic demo dataset with seeded incidents

There is no official dataset in the repo, so this task builds a SYNTHETIC stand-in that mirrors the problem statement: 20 campaigns, 180 days, and the four seeded situations. The CSV includes label columns so evaluation can be tested end to end.

**Files:**
- Create: `scripts/generate_demo_data.py`, `data/demo_campaigns.csv` (generated), `data/README.md`, `tests/test_demo_data.py`

**Interfaces:**
- Produces:
  - `scripts.generate_demo_data.generate(seed: int = 42) -> pd.DataFrame` with columns `date, campaign_id, campaign_name, channel, impressions, clicks, spend, conversions, revenue, is_incident, incident_type`.
  - `main()` writes `data/demo_campaigns.csv`. Run it with `python -m scripts.generate_demo_data`.
  - Fixed facts that later tasks rely on:
    - Campaign IDs are `C01` to `C20`.
    - Dates run from 2026-01-01 to 2026-06-29.
    - `incident_type` is `""` on normal rows.
    - `is_incident` is 0 or 1.

**Generation recipe.** Draw every random number from `numpy.random.default_rng(seed)`.
- Each campaign gets a log-uniform base of 2,000 to 2,000,000 daily impressions, a CTR of 0.5%–4%, a CVR of 1%–8%, a CPC of $0.30–$3.00 and an average order value of $20–$150.
- Force C18, C19 and C20 to be tiny, with about 1–3 conversions a day. These cover the problem statement's "single conversion swings the numbers" case.
- Daily values:
  - impressions = base × weekday factor (Saturday and Sunday 0.85) × lognormal(0, 0.08)
  - clicks = Poisson(impressions × CTR)
  - conversions = Poisson(clicks × CVR)
  - spend = clicks × CPC × lognormal(0, 0.05)
  - revenue = conversions × AOV × lognormal(0, 0.10)
- Round spend and revenue to 2 decimal places.

**Seeded situations.** The label applies to the rows in each window.

| incident_type | campaign | window | effect | is_incident |
|---|---|---|---|---|
| `tracking_break` | C05 | 2026-02-20 → 02-26 | conversions & revenue × 0.05, clicks unchanged | 1 |
| `budget_exhausted` | C12 | 2026-03-19 → 03-31 | impressions, clicks, spend, conversions, revenue × 0.02 | 1 |
| `bid_strategy_change` | C03 | effect from 2026-04-15 to end; **label** 04-15 → 04-21 | CPC × 1.6, clicks × 0.9, conversions × 0.95 | 1 |
| `spend_spike` | C09 | 2026-05-08 → 05-09 | CPC × 2.5 (spend up, clicks unchanged) | 1 |
| `seasonal_shift` | all | 2026-05-20 → 06-02 | all volume metrics × 1.4, ratios unchanged | 0 |

- [ ] **Step 1: Write the failing tests** in `tests/test_demo_data.py`:

```python
from scripts.generate_demo_data import generate

def test_shape_and_dates():
    df = generate(42)
    assert len(df) == 3600 and df["campaign_id"].nunique() == 20
    assert str(df["date"].min())[:10] == "2026-01-01" and str(df["date"].max())[:10] == "2026-06-29"

def test_deterministic():
    assert generate(42).equals(generate(42))

def test_labels():
    df = generate(42)
    types = set(df["incident_type"]) - {""}
    assert types == {"tracking_break", "budget_exhausted", "bid_strategy_change", "spend_spike", "seasonal_shift"}
    assert (df.loc[df.incident_type == "seasonal_shift", "is_incident"] == 0).all()
    assert (df.loc[df.incident_type.isin(types - {"seasonal_shift"}), "is_incident"] == 1).all()

def test_tracking_break_keeps_clicks():
    df = generate(42); c = df[df.campaign_id == "C05"].set_index("date")
    window = c.loc["2026-02-20":"2026-02-26"]; before = c.loc["2026-01-23":"2026-02-19"]
    assert window.conversions.median() < 0.2 * before.conversions.median()
    assert 0.8 < window.clicks.median() / before.clicks.median() < 1.2

def test_has_low_volume_campaigns():
    df = generate(42)
    assert (df.groupby("campaign_id").conversions.median() <= 3).sum() >= 3
```

- [ ] **Step 2: Run the tests and confirm they fail.** Run `python -m pytest tests/test_demo_data.py -v`. Expected: ImportError.
- [ ] **Step 3: Implement `generate()` and `main()`** following the recipe and table above.
- [ ] **Step 4: Run the tests and confirm they pass.** Then run `python -m scripts.generate_demo_data` and check that `data/demo_campaigns.csv` has 3,601 lines (3,600 rows plus the header).
- [ ] **Step 5: Write `data/README.md`.** It opens with "**SYNTHETIC DATA** — generated by `scripts/generate_demo_data.py` (seed 42). Not the official hackathon dataset." It includes the seeded-situations table above and the line "Put the official CSV in `data/official/`."
- [ ] **Step 6: Commit.** `git commit -m "feat: synthetic demo dataset with seeded incidents and labels"`

---

### Task 3: CSV ingestion and validation

**Files:**
- Create: `app/services/data_loader.py`, `tests/test_data_loader.py`

**Interfaces:**
- Produces:
  - `CANONICAL_METRICS = ("impressions", "clicks", "spend", "conversions", "revenue")`
  - `COLUMN_ALIASES: dict[str, str]`, which maps a normalized header to its canonical name.
  - `class DataValidationError(ValueError)`. Its message is shown to the user as-is.
  - `@dataclass LoadResult` with these fields:
    - `frame: pd.DataFrame`
    - `metrics: list[str]` (present canonical metrics, in `CANONICAL_METRICS` order)
    - `has_labels: bool`
    - `warnings: list[str]`
    - `input_rows: int`
    - `valid_rows: int`
  - `load_csv_bytes(content: bytes, max_rows: int) -> LoadResult`
  - `normalize_frame(raw: pd.DataFrame) -> LoadResult`
  - `LoadResult.frame` contract, which every later task depends on:
    - Columns `campaign_id` (str), `date` (datetime64, midnight), one float column per entry in `metrics`, and `row_present` (bool; False for filled-in missing days).
    - Optional columns `campaign_name` (str), `is_incident` (int 0/1) and `incident_type` (str, `""` when blank).
    - One row per campaign per calendar day, from that campaign's first date to its last.
    - Sorted by `campaign_id`, then `date`, with a RangeIndex.

**Decisions:**
- **Headers.** Strip a BOM, then strip whitespace and lowercase. Turn every run of non-alphanumeric characters into `_`, then strip `_` from the ends. This makes `"Conv."` become `"conv"`.
- **Aliases:**
  - `campaign_id`: campaign_id, campaign, campaignid, campaign_name (used as the ID only when no ID column exists)
  - `date`: date, day, report_date, ds, timestamp
  - `impressions`: impressions, impr, imps
  - `clicks`: clicks
  - `spend`: spend, cost, amount_spent, ad_spend
  - `conversions`: conversions, conv, convs, purchases, results
  - `revenue`: revenue, conversion_value, conv_value, purchase_value, sales
  - `is_incident`: is_incident, is_anomaly, anomaly, label, incident
  - `incident_type`: incident_type, anomaly_type
- **Reading the CSV.** Use `pd.read_csv(io.BytesIO(content), sep=None, engine="python", dtype=str, encoding="utf-8-sig")`. If that fails with `UnicodeDecodeError`, retry with `latin-1`. If the CSV has a parser error, raise `DataValidationError("Could not parse CSV: …")`.
- **Required columns.** The file must have `campaign_id`, `date` and at least one canonical metric. Otherwise raise `DataValidationError` and name what is missing.
- **Row limit.** If `len(raw) > max_rows`, raise `DataValidationError(f"File has {n} rows; the limit is {max_rows}.")`.
- **Dates.** Parse with `pd.to_datetime(errors="coerce")`, then `.dt.normalize()`. Drop rows with an invalid date or a blank campaign ID, and add the warning `"{k} row(s) dropped: invalid or missing date/campaign_id."`.
- **Numbers.** Remove `$`, `,`, spaces and currency symbols, then `pd.to_numeric(errors="coerce")`. A value that is not numeric becomes NaN and gets the warning `"spend: {k} non-numeric value(s) treated as missing."`. A negative value becomes NaN and gets the warning `"spend: {k} negative value(s) treated as missing."`.
- **Duplicates.**
  1. Drop rows that are exact duplicates and warn with the count.
  2. Rows that still share a `(campaign_id, date)` are summed (metrics use `sum(min_count=1)`, `is_incident` uses max, `incident_type` takes the first non-empty value). Warn: "treated as sub-campaign breakdown rows and summed."
- **Missing days.** Reindex each campaign to a daily date range, giving filled rows `row_present=False` and NaN metrics. Warn `"{campaign_id}: {k} missing day(s) filled as gaps (not scored)."`, but only for campaigns that have gaps. Warnings never include metric values.
- **No valid rows.** If no valid rows remain, raise `DataValidationError("The file contains no valid records after validation.")`. The same error covers a file with only a header row.

- [ ] **Step 1: Write the failing tests** in `tests/test_data_loader.py`. The helper `load(text, max_rows=1000) = load_csv_bytes(text.encode(), max_rows)` is used throughout.

```python
def test_aliases_mapped():
    r = load("Campaign,Day,Cost,Conv.,Clicks\nA,2026-01-01,10,1,5\n")
    assert r.metrics == ["clicks", "spend", "conversions"]
    assert {"campaign_id", "date"} <= set(r.frame.columns)

def test_formatted_numbers():
    r = load('campaign_id,date,spend,impressions\nA,2026-01-01,"$1,234.50","1,200"\n')
    assert r.frame.spend[0] == 1234.5 and r.frame.impressions[0] == 1200

def test_bom_and_semicolon():
    r = load_csv_bytes(b"\xef\xbb\xbfdate;campaign_id;spend\n2026-01-01;A;10\n", 1000)
    assert r.frame.spend[0] == 10

def test_leading_zero_ids_preserved():
    r = load("campaign_id,date,spend\n007,2026-01-01,1\n7,2026-01-01,2\n")
    assert sorted(r.frame.campaign_id.unique()) == ["007", "7"]

def test_invalid_dates_dropped_with_warning():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,not-a-date,2\nA,2026-01-02,3\n")
    assert r.valid_rows == 2 and any("1 row(s) dropped" in w for w in r.warnings)

def test_non_numeric_and_negative_become_missing():
    r = load("campaign_id,date,spend\nA,2026-01-01,abc\nA,2026-01-02,-5\nA,2026-01-03,4\n")
    assert r.frame.spend.isna().sum() == 2
    assert any("non-numeric" in w for w in r.warnings) and any("negative" in w for w in r.warnings)

def test_duplicates_dropped_or_summed():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,2026-01-01,1\nA,2026-01-02,2\nA,2026-01-02,3\n")
    assert list(r.frame.spend) == [1.0, 5.0] and len(r.warnings) == 2

def test_missing_days_filled():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,2026-01-04,1\n")
    assert len(r.frame) == 4 and r.frame.row_present.sum() == 2
    assert any("2 missing day(s)" in w for w in r.warnings)

def test_missing_required_columns():
    with pytest.raises(DataValidationError, match="campaign"): load("date,spend\n2026-01-01,1\n")
    with pytest.raises(DataValidationError, match="metric"): load("campaign_id,date,foo\nA,2026-01-01,1\n")

@pytest.mark.parametrize("text", ["", "campaign_id,date,spend\n", "campaign_id,date,spend\nA,bad,1\n"])
def test_no_valid_records(text):
    with pytest.raises(DataValidationError, match="no valid records|Could not parse"): load(text)

def test_row_limit():
    with pytest.raises(DataValidationError, match="limit"): load("campaign_id,date,spend\n" + "A,2026-01-01,1\n" * 3, max_rows=2)

def test_label_column_detected_and_not_a_metric():
    r = load("campaign_id,date,spend,is_anomaly\nA,2026-01-01,1,1\n")
    assert r.has_labels and r.frame.is_incident[0] == 1 and "is_incident" not in r.metrics
```

- [ ] **Step 2: Run the tests and confirm they fail.** Run `python -m pytest tests/test_data_loader.py -v`. Expected: ImportError.
- [ ] **Step 3: Implement `data_loader.py`** following the decisions above. Use one small private helper per decision (`_normalize_headers`, `_apply_aliases`, `_parse_dates`, `_parse_numeric`, `_handle_duplicates`, `_fill_missing_days`) so each rule is easy to point at.
- [ ] **Step 4: Run the tests and confirm they pass.** Also run `python -c "from app.services.data_loader import load_csv_bytes; r=load_csv_bytes(open('data/demo_campaigns.csv','rb').read(),200000); print(r.valid_rows, r.metrics, r.has_labels, r.warnings)"`. Expected: `3600 ['impressions','clicks','spend','conversions','revenue'] True []`.
- [ ] **Step 5: Commit.** `git commit -m "feat: CSV ingestion with alias mapping, validation and data-quality warnings"`

---

### Task 4: Derived metrics

**Files:**
- Create: `app/services/features.py`, `tests/test_features.py`

**Interfaces:**
- Consumes: `LoadResult.frame` and `LoadResult.metrics` (Task 3).
- Produces:
  - `DERIVED_METRICS: dict[str, tuple[str, str]]` (metric → (numerator, denominator)):
    - `"ctr": ("clicks", "impressions")`
    - `"cvr": ("conversions", "clicks")`
    - `"cpc": ("spend", "clicks")`
    - `"cpa": ("spend", "conversions")`
    - `"roas": ("revenue", "spend")`
  - `MIN_DENOMINATOR = {"ctr": 500, "cvr": 30, "cpc": 30, "cpa": 3, "roas": 20.0}`
  - `add_derived_metrics(frame: pd.DataFrame, metrics: list[str]) -> tuple[pd.DataFrame, list[str]]`. It returns a new frame and the list of derived metrics it added, in the dict's order. A ratio is added only when both of its inputs are in `metrics`. A ratio is NaN where the denominator is NaN or below `MIN_DENOMINATOR`, which also covers zero. This minimum is the low-volume guard for ratios.

- [ ] **Step 1: Write the failing tests:**

```python
def frame(**cols): return pd.DataFrame({"campaign_id": "A", "date": pd.date_range("2026-01-01", periods=len(next(iter(cols.values())))), **cols})

def test_ratios_computed():
    f, added = add_derived_metrics(frame(impressions=[1000.], clicks=[50.], spend=[100.], conversions=[5.], revenue=[400.]),
                                   ["impressions", "clicks", "spend", "conversions", "revenue"])
    assert added == ["ctr", "cvr", "cpc", "cpa", "roas"]
    assert f.ctr[0] == 0.05 and f.cvr[0] == 0.1 and f.cpc[0] == 2.0 and f.cpa[0] == 20.0 and f.roas[0] == 4.0

def test_zero_and_small_denominators_are_nan_not_inf():
    f, _ = add_derived_metrics(frame(impressions=[0., 100.], clicks=[0., 5.]), ["impressions", "clicks"])
    assert f.ctr.isna().all() and not np.isinf(f.select_dtypes("number")).any().any()

def test_only_available_inputs():
    _, added = add_derived_metrics(frame(clicks=[50.], spend=[10.]), ["clicks", "spend"])
    assert added == ["cpc"]
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement** with `numerator / denominator.where(denominator >= MIN_DENOMINATOR[m])`.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat: derived ratio metrics with minimum-denominator guard"`

---

### Task 5: Robust per-campaign anomaly detector

**Files:**
- Create: `app/services/detector.py`, `tests/test_detector.py`
- Create: `tests/helpers.py`, which holds `make_campaign_df`. Tests import it with `from tests.helpers import make_campaign_df`.

**Interfaces:**
- Consumes: the frame contract (Task 3) and `add_derived_metrics` (Task 4).
- Produces:
  - `VOLUME_METRICS = ("impressions","clicks","spend","conversions","revenue")`
  - `COUNT_METRICS = ("impressions","clicks","conversions")`
  - `SEVERITY_RANK = {"medium": 1, "high": 2, "critical": 3}`
  - `@dataclass(frozen=True) DetectorConfig`: `window_days=28, min_history=14, z_threshold=3.5, high_z=6.0, critical_z=10.0, rel_floor=0.02, min_pct_change=0.05`
  - `@dataclass(frozen=True) Anomaly`: `campaign_id: str, date: pd.Timestamp, metric: str, observed: float, expected: float, lower: float, upper: float, score: float, pct_change: float, direction: str ("up"|"down"), severity: str, history_points: int, method: str = "rolling_median_mad"`
  - `@dataclass DetectionResult`: `anomalies: list[Anomaly]` and `scores: pd.DataFrame`. `scores` has one row per (campaign_id, date, metric) with columns `campaign_id, date, metric, observed, expected, lower, upper, score, pct_change, history_points, is_anomaly`.
  - `score_series(values: pd.Series, metric: str, cfg: DetectorConfig) -> pd.DataFrame`, with columns `expected, lower, upper, score, pct_change, history_points` aligned to `values.index`.
  - `classify_severity(score: float, pct_change: float, metric: str, cfg: DetectorConfig) -> str`
  - `detect(frame: pd.DataFrame, metrics: list[str], cfg: DetectorConfig) -> DetectionResult`. Here `metrics` means the raw metrics plus the derived ones.
  - Test helper `make_campaign_df(campaign_id="C1", days=60, start="2026-01-01", seed=0, impressions=10000, clicks=300, spend=300.0, conversions=18, revenue=900.0) -> pd.DataFrame`. It returns frame-contract columns. Counts are Poisson around the given levels. Spend and revenue are level × lognormal(0, 0.05). `row_present` is True.

**Algorithm.** This is the one block in the plan that the tests cannot pin down on their own:

```
hist      = values.shift(1)                                      # past days only → no future leakage
roll      = hist.rolling(window_days, min_periods=min_history)   # NaN days don't count as history
expected  = roll.median()
mad       = roll.apply(lambda w: nanmedian(|w - nanmedian(w)|), raw=True)
scale     = max(1.4826*mad, rel_floor*|expected|, sqrt(expected) if metric in COUNT_METRICS else 0, 1e-9)
              # MAD = campaign's own volatility; rel_floor handles zero-MAD/constant history;
              # sqrt(expected) = Poisson noise floor → tiny campaigns get wide bands
score     = (observed - expected) / scale                         # robust z-score (heuristic, not a probability)
lower     = max(expected - z_threshold*scale, 0);  upper = expected + z_threshold*scale
pct       = (observed - expected) / expected   (NaN if expected <= 0)
history_points = roll.count()
is_anomaly = observed notna & expected > 0 & |score| >= z_threshold & |pct| >= min_pct_change
```

**Severity.** The result is `critical` if |score| ≥ `critical_z`, or if the metric is in `VOLUME_METRICS` and pct ≤ −0.90 (a collapse toward zero). Otherwise it is `high` if |score| ≥ `high_z`, and `medium` for anything else.

`detect` loops over each campaign and each metric, calling `score_series` on that campaign's rows. The loop is plain Python for readability; 20 × 10 series is fast.

- [ ] **Step 1: Write the failing tests** in `tests/test_detector.py`. Every test uses `cfg = DetectorConfig()`, and `anoms(df, metric)` filters `detect(...).anomalies` by metric.

```python
def test_stable_campaign_has_no_anomalies():
    assert detect(make_campaign_df(days=60), RAW, cfg).anomalies == []

def test_conversion_drop_with_stable_clicks():
    df = make_campaign_df(days=60); df.loc[50, "conversions"] = 2
    [a] = [a for a in detect(df, RAW, cfg).anomalies if a.metric == "conversions"]
    assert a.direction == "down" and 14 <= a.expected <= 22 and a.severity in ("high", "critical")
    assert not [x for x in detect(df, RAW, cfg).anomalies if x.metric == "clicks" and x.date == df.date[50]]

def test_spend_spike():
    df = make_campaign_df(days=60); df.loc[50, "spend"] *= 3
    assert [a.direction for a in anoms(df, "spend")] == ["up"]

def test_spend_drop_is_critical():
    df = make_campaign_df(days=60); df.loc[50, "spend"] *= 0.1
    [a] = anoms(df, "spend"); assert a.direction == "down" and a.severity == "critical"

def test_insufficient_history_not_scored():
    df = make_campaign_df(days=20); df.loc[5, "spend"] *= 5      # only 5 prior days
    res = detect(df, RAW, cfg)
    assert res.anomalies == [] and res.scores[res.scores.date <= df.date[13]].expected.isna().all()

def test_low_volume_single_conversion_swing_is_quiet_but_large_10pct_drift_alerts():
    small = make_campaign_df(days=60, conversions=2); small.loc[50, "conversions"] = 0
    assert anoms(small, "conversions") == []
    large = make_campaign_df(days=60, conversions=2000, seed=1); large.loc[50, "conversions"] = 1800
    assert [a.direction for a in anoms(large, "conversions")] == ["down"]

def test_constant_history_zero_mad():
    df = make_campaign_df(days=40); df["spend"] = 100.0; df.loc[39, "spend"] = 130.0
    res = detect(df, ["spend"], cfg)
    assert [a.date for a in res.anomalies] == [df.date[39]]
    assert np.isfinite(res.scores.score.dropna()).all()

def test_no_future_leakage():
    df = make_campaign_df(days=60); before = detect(df, RAW, cfg).scores
    df.loc[55, "spend"] *= 10; after = detect(df, RAW, cfg).scores
    early = lambda s: s[s.date < df.date[55]].reset_index(drop=True)
    pd.testing.assert_frame_equal(early(before), early(after))

def test_missing_days_skipped():
    df = make_campaign_df(days=60); df.loc[40:42, RAW] = np.nan; df.loc[40:42, "row_present"] = False
    res = detect(df, RAW, cfg)
    assert res.anomalies == [] and res.scores[res.scores.date == df.date[45]].expected.notna().all()

def test_zero_day_is_safe_and_flagged():
    df = make_campaign_df(days=60); df.loc[50, RAW] = 0
    f, derived = add_derived_metrics(df, RAW)
    res = detect(f, RAW + derived, cfg)
    assert {"spend", "impressions", "clicks"} <= {a.metric for a in res.anomalies}
    assert np.isfinite(res.scores.select_dtypes("number").fillna(0)).all().all()

def test_severity_thresholds():
    assert classify_severity(4.0, -0.2, "spend", cfg) == "medium"
    assert classify_severity(7.0, -0.2, "spend", cfg) == "high"
    assert classify_severity(-4.0, -0.95, "spend", cfg) == "critical"
    assert classify_severity(-4.0, -0.95, "cvr", cfg) == "medium"
```

- [ ] **Step 2: Run the tests and confirm they fail.** Run `python -m pytest tests/test_detector.py -v`.
- [ ] **Step 3: Implement `detector.py`** following the algorithm block. Put `make_campaign_df` in `tests/helpers.py`.
- [ ] **Step 4: Run the tests and confirm they pass.** If the large-campaign 10% test is borderline because of the seed, change the seed in the test, not the algorithm, and note the change in the commit message.
- [ ] **Step 5: Commit.** `git commit -m "feat: per-campaign rolling median/MAD detector with Poisson low-volume floor"`

---

### Task 6: Diagnosis and plain-English explanations

**Files:**
- Create: `app/services/diagnosis.py`, `tests/test_diagnosis.py`

**Interfaces:**
- Consumes: `Anomaly` (Task 5).
- Produces:
  - `@dataclass Diagnosis`: `alert_type: str, title: str, explanation: str, possible_causes: list[str], diagnostic_steps: list[str]`
  - `METRIC_LABELS: dict[str, str]`, e.g. `"cvr": "Conversion rate"` and `"cpa": "Cost per acquisition"`.
  - `format_value(metric: str, value: float) -> str`. Counts are integers with thousands separators. spend, revenue, cpc and cpa use 2 decimals and no currency symbol, because the currency is unknown. ctr and cvr are percentages with 2 decimals. roas is shown as `"3.20x"`.
  - `describe_anomaly(a: Anomaly) -> str`. It returns `"{Label} {rose|fell} to {obs}, compared with a baseline of {exp} (median of the previous {history_points} days; normal range {lower}–{upper}). That is {abs pct:.0f}% {above|below} baseline (robust z-score {score:+.1f})."`
  - `diagnose(anomalies: list[Anomaly], day_scores: dict[str, dict]) -> Diagnosis`. `anomalies` is sorted with the primary anomaly first. `day_scores` maps metric to `{"observed","expected","score"}` for that campaign and day, including metrics that were not anomalous.

**Rules.** The first match wins. "Normal" means |score| < 2.5.

| alert_type | condition | first diagnostic step |
|---|---|---|
| `tracking_issue` | conversions or cvr anomalous **down** AND clicks normal | "Verify the conversion tag is firing (tag manager / test conversion) and check for recent site or checkout deploys." |
| `delivery_drop` | spend **down** AND (impressions or clicks anomalous down) | "Check campaign status, daily/monthly budget caps and billing; confirm the budget was not exhausted." |
| `cost_efficiency_shift` | cpc or cpa anomalous **up**, or roas anomalous **down** | "Review the change history for bid strategy, target CPA/ROAS or bid changes around this date." |
| `spend_spike` | spend anomalous **up** | "Check for budget increases, bid changes or broad-match/targeting expansion; consider a temporary cap." |
| `volume_change` | anything else | "Check whether traffic volume or data completeness changed for this campaign on this date." |

The explanation is built as: `describe_anomaly(primary)`, then context sentences, then `"This may indicate {cause 1} or {cause 2}."`, then `"Suggested first check: {step 1}"`.
- For `tracking_issue`, the context sentence is `"Clicks stayed within their normal range ({obs} vs baseline {exp})."`.
- The other types list the related anomalous metrics in one sentence: `"Related changes: Impressions −97%, Clicks −98%."`.

Each type has 2 or 3 `possible_causes`, worded as hypotheses. Each also has 2 or 3 `diagnostic_steps`, with the table's step first.

- [ ] **Step 1: Write the failing tests:**

```python
def A(metric, obs, exp, score, direction): ...  # builds an Anomaly with lower/upper around exp, history_points=28

def test_tracking_issue_explanation_uses_measured_values():
    d = diagnose([A("conversions", 2, 18, -8.0, "down")],
                 {"conversions": {"observed": 2, "expected": 18, "score": -8.0},
                  "clicks": {"observed": 300, "expected": 310, "score": -0.3}})
    assert d.alert_type == "tracking_issue"
    assert d.explanation.startswith("Conversions fell to 2, compared with a baseline of 18")
    assert "Clicks stayed within their normal range" in d.explanation
    assert d.diagnostic_steps[0].startswith("Verify the conversion tag")

def test_delivery_drop():
    d = diagnose([A("spend", 5, 300, -20, "down"), A("impressions", 200, 10000, -30, "down")], {...})
    assert d.alert_type == "delivery_drop" and "budget" in d.diagnostic_steps[0]

def test_cost_shift_beats_spend_spike():
    assert diagnose([A("spend", 450, 300, 6, "up"), A("cpc", 1.6, 1.0, 7, "up")], {}).alert_type == "cost_efficiency_shift"

def test_spend_spike(): assert diagnose([A("spend", 900, 300, 12, "up")], {}).alert_type == "spend_spike"

def test_conversion_drop_with_clicks_also_down_is_not_tracking():
    d = diagnose([A("conversions", 2, 18, -8, "down")], {"clicks": {"observed": 30, "expected": 300, "score": -9}})
    assert d.alert_type != "tracking_issue"

@pytest.mark.parametrize("case", ALL_TYPE_CASES)
def test_language_is_hedged(case):
    text = diagnose(*case).explanation.lower()
    assert "may" in text and "confirmed" not in text and "caused by" not in text

def test_format_value():
    assert format_value("conversions", 1234) == "1,234" and format_value("cvr", 0.021) == "2.10%"
    assert format_value("roas", 3.2) == "3.20x" and format_value("spend", 12.5) == "12.50"
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `diagnosis.py`.** Keep the rule table as a module-level list of rules so the presenter can point at it.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat: rule-based diagnosis with hedged plain-English explanations"`

---

### Task 7: Alert manager (grouping, seasonality, cooldown, escalation, reopen, routing)

**Files:**
- Create: `app/services/alert_manager.py`, `tests/test_alert_manager.py`

**Interfaces:**
- Consumes: `Anomaly`, `DetectionResult`, `SEVERITY_RANK` (Task 5), `diagnose`, `Diagnosis` (Task 6).
- Produces:
  - `@dataclass(frozen=True) AlertConfig`: `cooldown_days=3, portfolio_share=0.5, portfolio_min_pct=0.15, min_portfolio_campaigns=5`
  - `@dataclass Finding`, one per campaign-day:
    - `campaign_id`, `date`
    - `primary: Anomaly`, `related: list[Anomaly]`
    - `severity: str`, `diagnosis: Diagnosis`
    - `category: str ("incident"|"seasonality")`
    - `status: str = ""` (set to new|reopened|escalated|suppressed)
  - `@dataclass Alert`, one per episode:
    - `alert_id`, `campaign_id`, `alert_type`, `category`, `severity`, `routing ("immediate"|"digest")`
    - `first_date`, `last_date`
    - `findings: list[Finding]`, `notifications: list[tuple[pd.Timestamp, str]]`
    - `reopened_from: str | None`
    - Property `suppressed_count`.
  - `@dataclass AlertSummary`: `anomalies_detected, duplicates_removed, findings, grouped_alerts, new_alerts, reopened_alerts, escalated_alerts, suppressed_alerts, notifications_sent, immediate_notifications, digest_notifications, alerts_total`
  - `find_portfolio_shifts(scores: pd.DataFrame, cfg: AlertConfig) -> dict[tuple[pd.Timestamp, str, str], tuple[int, int]]`, keyed by `(date, metric, direction)` and returning `(campaigns_moving, campaigns_scored)`.
  - `build_findings(detection: DetectionResult, cfg: AlertConfig) -> tuple[list[Finding], int]`, returning the findings and `duplicates_removed`.
  - `route(severity: str, category: str) -> str`
  - `manage_alerts(findings: list[Finding], cfg: AlertConfig) -> list[Alert]`. It sets `Finding.status`.
  - `summarize(anomalies_detected: int, duplicates_removed: int, findings: list[Finding], alerts: list[Alert]) -> AlertSummary`

**Decisions:**
- **Dedupe.** Anomalies with the same `(campaign_id, date, metric)` are kept once and counted in `duplicates_removed`.
- **Grouping.**
  - All anomalies for one campaign-day form one Finding.
  - The primary anomaly has the highest `SEVERITY_RANK`, with ties broken by |score|. The others go in `related`.
  - The finding's severity is the primary anomaly's severity.
  - `grouped_alerts = anomalies_detected − duplicates_removed − findings`.
- **Portfolio shift (seasonality).** For each date and metric, look at the campaigns with a non-null `pct_change`. Count those moving the same way by at least `portfolio_min_pct`. It is a shift when there are at least `min_portfolio_campaigns` scored campaigns and the moving share is at least `portfolio_share`.
  - A finding whose **primary** metric and direction match a shift that day becomes `category="seasonality"` and `alert_type="portfolio_shift"`.
  - Its explanation gets this sentence: `"{k} of {n} campaigns saw {metric} move more than {pct}% in the same direction on this date, so this looks like a market-wide or seasonal shift rather than a fault in this campaign."`
  - A finding whose primary metric moves against the portfolio stays `incident`.
- **Routing.** `immediate` when category is `incident` and severity is `high` or `critical`. Otherwise `digest`.
- **Episodes.** Process findings sorted by `(date, campaign_id)`. The key is `(campaign_id, alert_type)`.
  - **No open episode, or the gap since `last_date` is more than `cooldown_days`:** open a new Alert. The finding's status is `reopened` if this key had an earlier episode (set `reopened_from` to that `alert_id`), otherwise `new`. Record a notification.
  - **Inside the cooldown, with severity rank above the episode's current severity:** status `escalated`. Raise the episode's severity, recompute its routing and record a notification.
  - **Otherwise:** status `suppressed`. The finding is appended to the episode as evidence and no notification is sent.
  - `alert_id = f"{campaign_id}:{alert_type}:{first_date:%Y-%m-%d}"`.

- [ ] **Step 1: Write the failing tests.** These helpers are local to `test_alert_manager.py`:
  - `A(campaign, day, metric, score, severity=None)` builds an Anomaly. It derives `direction` from the sign of `score` and `severity` from `classify_severity` when none is given.
  - `F(campaign, day, alert_type="tracking_issue", severity="medium", category="incident")` builds a Finding directly. `day` is an int offset from 2026-01-01.
  - `det(anoms, scores_rows)` builds a DetectionResult.

```python
def test_related_metrics_same_day_grouped():
    findings, dups = build_findings(det([A("C1",10,"conversions",-8), A("C1",10,"revenue",-6), A("C1",10,"cvr",-7)]), cfg)
    assert len(findings) == 1 and findings[0].primary.metric == "conversions" and len(findings[0].related) == 2

def test_duplicates_removed():
    _, dups = build_findings(det([A("C1",10,"spend",5), A("C1",10,"spend",5)]), cfg); assert dups == 1

def test_repeats_within_cooldown_suppressed_but_kept():
    fs = [F("C1", d) for d in range(5)]; [alert] = manage_alerts(fs, cfg)
    assert [f.status for f in fs] == ["new"] + ["suppressed"] * 4
    assert len(alert.notifications) == 1 and alert.suppressed_count == 4 and len(alert.findings) == 5

def test_escalation_not_hidden_by_cooldown():
    fs = [F("C1", 0), F("C1", 1), F("C1", 2, severity="critical")]; [alert] = manage_alerts(fs, cfg)
    assert [f.status for f in fs] == ["new", "suppressed", "escalated"]
    assert alert.severity == "critical" and alert.routing == "immediate" and len(alert.notifications) == 2

def test_reopen_after_recovery():
    fs = [F("C1", 0), F("C1", 1), F("C1", 10)]; a1, a2 = manage_alerts(fs, cfg)
    assert fs[2].status == "reopened" and a2.reopened_from == a1.alert_id

def test_different_types_are_separate_alerts():
    assert len(manage_alerts([F("C1", 0), F("C1", 0, alert_type="spend_spike")], cfg)) == 2

def test_portfolio_shift_routed_as_seasonality():
    # 6 campaigns, clicks pct_change +0.4 on day 30; 4 of them anomalous
    findings, _ = build_findings(portfolio_detection(n_campaigns=6, anomalous=4), cfg)
    assert {f.category for f in findings} == {"seasonality"}
    assert all(f.diagnosis.alert_type == "portfolio_shift" and "of 6 campaigns" in f.diagnosis.explanation for f in findings)
    assert {a.routing for a in manage_alerts(findings, cfg)} == {"digest"}

def test_small_portfolio_never_called_seasonal():
    findings, _ = build_findings(portfolio_detection(n_campaigns=3, anomalous=3), cfg)
    assert {f.category for f in findings} == {"incident"}

def test_campaign_specific_drop_during_surge_stays_incident():
    # 6 campaigns surge +40% clicks; C1 conversions drop -90% that same day
    ...; assert c1_finding.category == "incident"

def test_summary_invariants():
    det_ = ...  # mix of grouped, duplicate, repeated, escalated anomalies
    findings, dups = build_findings(det_, cfg); alerts = manage_alerts(findings, cfg)
    s = summarize(len(det_.anomalies), dups, findings, alerts)
    assert s.anomalies_detected == s.duplicates_removed + s.findings + s.grouped_alerts
    assert s.findings == s.new_alerts + s.reopened_alerts + s.escalated_alerts + s.suppressed_alerts
    assert s.notifications_sent == s.new_alerts + s.reopened_alerts + s.escalated_alerts
    assert s.notifications_sent == s.immediate_notifications + s.digest_notifications

def test_route():
    assert route("high", "incident") == "immediate" and route("medium", "incident") == "digest"
    assert route("critical", "seasonality") == "digest"
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `alert_manager.py`.** Write the episode loop as one explicit `for` loop with the three branches commented, because this is the core of "without alert fatigue" and will be explained live.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat: alert manager with grouping, seasonality routing, cooldown, escalation and reopen"`

---

### Task 8: Evaluation against labels and a naive baseline

**Files:**
- Create: `app/services/evaluation.py`, `tests/test_evaluation.py`

**Interfaces:**
- Consumes: the frame contract (Task 3) and `Alert` (Task 7).
- Produces:
  - `@dataclass Incident`: `campaign_id, start: pd.Timestamp, end: pd.Timestamp, incident_type: str`
  - `extract_windows(frame) -> tuple[list[Incident], list[Incident]]`. The first list holds real incidents: contiguous runs of `is_incident == 1` per campaign. The second holds known non-incident windows: contiguous runs where `is_incident == 0` and `incident_type` is not empty, such as `seasonal_shift`.
  - `evaluate(frame, alerts: list[Alert], has_labels: bool, tolerance_days: int = 2) -> dict`, with keys:
    - `available`, `reason`
    - `precision`, `recall`, `f1_score`
    - `alerts_evaluated`, `true_positive_alerts`, `false_positive_alerts`, `false_positive_alert_ids`
    - `incidents_total`, `incidents_detected`, `detected_incidents`, `missed_incidents`
    - `non_incident_windows`
    - `matching_rule`, `notes`
  - `naive_threshold_baseline(frame, incidents: list[Incident], pct: float = 0.30, metrics=("spend","conversions"), tolerance_days: int = 2) -> dict`, with keys `rule, alerts_fired, precision, recall`.

**Matching rule.** Copy this text verbatim into `matching_rule`:
"An incident is a contiguous run of labeled days for one campaign. An alert is a true positive if it is an incident-category alert for the same campaign with any occurrence dated from the incident's first day to its last day plus 2 days. An incident counts as detected if at least one alert matches it. Precision = true-positive alerts / incident-category alerts. Recall = detected incidents / labeled incidents. Seasonality-routed alerts are excluded from precision and reported separately."

**Other output details:**
- `detected_incidents` items include `first_alert_date` and `days_to_detect`.
- `non_incident_windows` items: `{incident_type, campaign_id, start, end, alerts_immediate, alerts_digest, alerts_seasonality}`. Only alerts for that window's own campaign count.
- `notes` always contains: "Detector thresholds were chosen while looking at this same dataset, so these numbers are optimistic. Treat them as a sanity check, not an out-of-sample result."
- **Undefined metrics:** `precision` is `None` when `alerts_evaluated == 0`, and `recall` is `None` when `incidents_total == 0`. `f1_score` is `None` if either one is `None`, or if both are 0. Never substitute 0.
- **Without labels:** `available=False`, all metrics `None`, `reason="No ground-truth label column (is_incident / is_anomaly / label) found, so precision and recall are not computed."`
- **Naive baseline:** fires once per campaign-day when any listed metric changes by more than 30% versus the previous day, where the previous value is above 0. Precision is computed at the campaign-day level against incident days, using the same tolerance. Recall is computed at the incident level.

- [ ] **Step 1: Write the failing tests:**

```python
def test_no_labels():
    ev = evaluate(frame_without_labels, [], has_labels=False)
    assert ev["available"] is False and ev["precision"] is None and "No ground-truth" in ev["reason"]

def test_precision_recall_f1():
    # incident on A days 10-12; alerts: A day 11 (TP), B day 20 (FP)
    ev = evaluate(labeled_frame, [alert("A", 11), alert("B", 20)], has_labels=True)
    assert ev["precision"] == 0.5 and ev["recall"] == 1.0 and round(ev["f1_score"], 4) == 0.6667
    assert ev["detected_incidents"][0]["days_to_detect"] == 1 and len(ev["false_positive_alert_ids"]) == 1

def test_missed_incident_listed():
    ev = evaluate(labeled_frame, [], has_labels=True)
    assert ev["recall"] == 0.0 and ev["missed_incidents"][0]["campaign_id"] == "A" and ev["precision"] is None

@pytest.mark.parametrize("day,hit", [(14, True), (15, False)])
def test_tolerance(day, hit):
    assert (evaluate(labeled_frame, [alert("A", day)], True)["incidents_detected"] == 1) is hit

def test_seasonality_alerts_excluded_and_reported():
    ev = evaluate(frame_with_seasonal_window, [alert("A", 40, category="seasonality")], True)
    assert ev["alerts_evaluated"] == 0 and ev["non_incident_windows"][0]["alerts_seasonality"] == 1

def test_naive_baseline_counts_30pct_moves():
    nb = naive_threshold_baseline(frame_with_two_40pct_jumps, incidents=[])
    assert nb["alerts_fired"] == 2
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `evaluation.py`.**
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat: precision/recall evaluation with documented matching rule and naive ±30% baseline"`

---

### Task 9: Pipeline, response schemas, analyze and demo endpoints

**Files:**
- Create: `app/services/pipeline.py`, `app/schemas.py`
- Modify: `app/api/routes.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `@dataclass(frozen=True) AnalysisConfig`: `detector: DetectorConfig, alerts: AlertConfig, match_tolerance_days: int = 2`
  - `analyze_load_result(load: LoadResult, config: AnalysisConfig) -> AnalysisResponse`
  - `analyze_csv(content: bytes, config: AnalysisConfig, max_rows: int) -> AnalysisResponse`. It raises `DataValidationError`.
  - `DEMO_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_campaigns.csv"`
  - `clean_number(x) -> float | None`. It returns `None` for None, NaN or ±inf, and otherwise `round(float(x), 4)`.
  - Pydantic models in `app/schemas.py`. **These are the frontend contract; the names are fixed:**

```
HealthResponse      {status, app, version}
Summary             {campaigns_analyzed, records_analyzed, input_rows, date_start, date_end, days_covered,
                     anomalies_detected, duplicates_removed, findings, grouped_alerts, new_alerts, reopened_alerts,
                     escalated_alerts, suppressed_alerts, notifications_sent, immediate_notifications,
                     digest_notifications, alerts_total}
AnomalyOut          {metric, observed, expected, lower, upper, score, pct_change, direction, severity, history_points, method}
OccurrenceOut       {date, status, severity, explanation, primary: AnomalyOut, related: list[AnomalyOut]}
NotificationOut     {date, kind}                       # kind: new | reopened | escalated
AlertOut            {alert_id, campaign_id, campaign_name|None, alert_type, title, category, severity, routing,
                     first_date, last_date, explanation, possible_causes, diagnostic_steps,
                     primary: AnomalyOut, occurrences: list[OccurrenceOut], notifications: list[NotificationOut],
                     suppressed_count, reopened_from|None, suppression_eligible: bool}
TimelinePoint       {date, values: dict[str, float|None], expected: dict[...], lower: dict[...], upper: dict[...],
                     anomaly_metrics: list[str]}
CampaignTimeline    {campaign_id, campaign_name|None, points: list[TimelinePoint]}
EvaluationOut       {available, reason|None, precision|None, recall|None, f1_score|None, ... all keys from Task 8,
                     naive_baseline: dict|None}
AnalysisResponse    {summary, config: dict, metrics_analyzed: list[str], alerts: list[AlertOut],
                     timeline: list[CampaignTimeline], warnings: list[str], evaluation: EvaluationOut,
                     score_note: str}
DemoDataResponse    {synthetic: bool, notice, columns, total_records, records: list[dict]}
```

**Field rules:**
- Dates are `YYYY-MM-DD` strings. Floats go through `clean_number`.
- An AlertOut's top-level `explanation` and `primary` come from the occurrence that sent the alert's latest notification.
- `suppression_eligible` is `category == "incident" and severity != "critical"`.
- `score_note` is "score is a robust z-score: how many robust standard deviations the value sits from the campaign's own recent median. It is a heuristic score, not a probability."
- `alerts` are sorted by routing (immediate first), then severity rank (descending), then `first_date`.
- Warnings also include one line per campaign with fewer than `min_history + 1` valid days: `"{campaign}: only {n} valid day(s); needs {min_history} days of history before it can be scored."`

**Routes.** All of these go in `routes.py`. The analysis parameters are **query** parameters, validated by FastAPI:
- `window_days: int = Query(28, ge=7, le=90)`
- `min_history: int = Query(14, ge=5, le=60)`
- `z_threshold: float = Query(3.5, ge=2.0, le=10.0)`, documented as "sensitivity: lower = more alerts"
- `cooldown_days: int = Query(3, ge=0, le=30)`

If `min_history > window_days`, return 422.

| Route | Behavior |
|---|---|
| `GET /api/health` | from Task 1 |
| `POST /api/analyze` | `file: UploadFile = File(...)`. Return 400 `"Only .csv files are accepted."` if the filename doesn't end in `.csv` (case-insensitive). Read up to `max_upload_bytes + 1` bytes and return 413 if more. Return 400 `"Uploaded file is empty."` for 0 bytes. A `DataValidationError` becomes 422 `{"detail": msg}`. Otherwise 200 with `AnalysisResponse`. |
| `POST /api/analyze/demo` | Same query parameters. Analyzes `DEMO_CSV_PATH`. Lets the frontend demo without an upload. |
| `GET /api/demo-data?limit=50` (`ge=1, le=5000`) | `DemoDataResponse` with `synthetic=True` and `notice="SYNTHETIC demo data generated by scripts/generate_demo_data.py — not official hackathon data."` |

- [ ] **Step 1: Write the failing tests** in `tests/test_api.py`:

```python
DEMO = Path("data/demo_campaigns.csv").read_bytes()
def strict_json(r): return json.loads(r.text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))

def test_analyze_demo_upload(client):
    r = client.post("/api/analyze", files={"file": ("demo.csv", DEMO, "text/csv")})
    assert r.status_code == 200; body = strict_json(r)
    s = body["summary"]
    assert s["campaigns_analyzed"] == 20 and s["records_analyzed"] == 3600
    assert s["notifications_sent"] < s["anomalies_detected"]
    assert body["evaluation"]["available"] is True and body["evaluation"]["naive_baseline"]["alerts_fired"] > 0
    assert all(a["explanation"] and a["diagnostic_steps"] for a in body["alerts"])
    assert len(body["timeline"]) == 20

def test_analyze_demo_endpoint_matches_upload(client):
    a = client.post("/api/analyze/demo").json(); b = client.post("/api/analyze", files={"file": ("d.csv", DEMO)}).json()
    assert a["summary"] == b["summary"]

def test_rejects_non_csv(client):
    assert client.post("/api/analyze", files={"file": ("x.txt", b"a")}).status_code == 400

def test_rejects_empty(client):
    assert client.post("/api/analyze", files={"file": ("x.csv", b"")}).status_code == 400

def test_rejects_too_large(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0.0001")
    c = TestClient(create_app())
    assert c.post("/api/analyze", files={"file": ("x.csv", b"a" * 1000)}).status_code == 413

def test_no_valid_records_is_422(client):
    r = client.post("/api/analyze", files={"file": ("x.csv", b"campaign_id,date,spend\nA,bad,1\n")})
    assert r.status_code == 422 and "no valid records" in r.json()["detail"]

def test_bad_params_422(client):
    assert client.post("/api/analyze/demo?z_threshold=0").status_code == 422
    assert client.post("/api/analyze/demo?window_days=10&min_history=20").status_code == 422

def test_no_labels_means_null_metrics(client):
    csv = make_campaign_df(days=40).drop(columns=["row_present"]).to_csv(index=False).encode()
    ev = client.post("/api/analyze", files={"file": ("x.csv", csv)}).json()["evaluation"]
    assert ev["available"] is False and ev["precision"] is None

def test_demo_data_is_labeled_synthetic(client):
    body = client.get("/api/demo-data?limit=5").json()
    assert body["synthetic"] is True and "SYNTHETIC" in body["notice"] and len(body["records"]) == 5

OFFICIAL = sorted(Path("data/official").glob("*.csv"))
@pytest.mark.skipif(not OFFICIAL, reason="official dataset not provided yet")
def test_official_dataset_sample(client):
    r = client.post("/api/analyze", files={"file": (OFFICIAL[0].name, OFFICIAL[0].read_bytes())})
    assert r.status_code == 200 and strict_json(r)["summary"]["records_analyzed"] > 0
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `schemas.py`, `pipeline.py` and the routes.** `MAX_UPLOAD_MB` accepts floats; parse it with `float()`. The pipeline order is: load → `add_derived_metrics` → `detect` → `build_findings` → `manage_alerts` → `summarize` → `evaluate` (plus the naive baseline when labels exist) → build the timeline → build the response.
- [ ] **Step 4: Run the whole test suite and confirm it passes.** Run `python -m pytest -v`. Expected: all pass, with the official test skipped.
- [ ] **Step 5: Smoke-test the real server.**
  - Start it: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (in the background).
  - Check health: `curl http://127.0.0.1:8000/api/health`.
  - Check an upload: `curl -F "file=@data/demo_campaigns.csv" "http://127.0.0.1:8000/api/analyze?cooldown_days=3"`. Expect HTTP 200.
  - Open `http://127.0.0.1:8000/docs` and confirm it loads, then stop the server.
- [ ] **Step 6: Commit.** `git commit -m "feat: analysis pipeline, response schemas and /api/analyze endpoints"`

---

### Task 10: CLI, demo-data run, honest results, README and code walkthrough

**Files:**
- Create: `app/cli.py`, `tests/test_cli.py`, `README.md`, `docs/CODE_WALKTHROUGH.md`

**Interfaces:**
- Consumes: `analyze_csv`, `AnalysisConfig` (Task 9) and `get_settings` (Task 1).
- Produces: `app.cli.main(argv: list[str] | None = None) -> int`. Run it with `python -m app.cli <csv> [--window-days N] [--z-threshold X] [--cooldown-days N] [--json OUT]`.

The CLI prints:
- `Total alerts fired over {days_covered} days: {notifications_sent} ({immediate} immediate, {digest} digest)`. This line is the problem statement's minimum bar.
- `Anomalies detected: … / grouped: … / suppressed: …`
- `Precision / Recall / F1: …`, or `n/a — {reason}`.
- One line per missed incident.
- `Naive ±30% day-over-day rule would have fired: {n} alerts`.

On `DataValidationError` it prints the message and returns 2.

- [ ] **Step 1: Write the failing test:**

```python
def test_cli_on_demo(capsys):
    assert main(["data/demo_campaigns.csv"]) == 0
    out = capsys.readouterr().out
    assert "Total alerts fired over 180 days" in out and "Naive ±30%" in out

def test_cli_bad_file(tmp_path, capsys):
    p = tmp_path / "x.csv"; p.write_text("campaign_id,date,spend\nA,bad,1\n")
    assert main([str(p)]) == 2
```

- [ ] **Step 2: Run it and confirm it fails. Then implement `cli.py`, run it and confirm it passes.**
- [ ] **Step 3: Run the demo data through the CLI and review it honestly.** Run `python -m app.cli data/demo_campaigns.csv --json %TEMP%\demo_result.json`.
  1. Read every false-positive alert ID and every missed incident.
  2. If a default is clearly mis-set (for example, the seasonal window not routed as seasonality because too few small campaigns move 15%), change **one** default in `DetectorConfig` or `AlertConfig`.
  3. Update the Global Constraints defaults in this plan, re-run the full test suite, and write down what changed and why.
  4. Limit this to two tuning rounds. Do not tune toward a perfect score: misses and false positives are reported, not hidden.
- [ ] **Step 4: Write `README.md`.** Use the sections the spec lists:
  - what it does
  - an architecture diagram (ASCII pipeline)
  - prerequisites
  - Windows PowerShell setup (`python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`)
  - the start command
  - the docs URL `http://127.0.0.1:8000/docs`
  - the endpoint table
  - the CSV schema and aliases
  - curl and PowerShell example requests (`Invoke-RestMethod -Form @{file=Get-Item data\demo_campaigns.csv}`)
  - how detection works (the algorithm block from Task 5 in plain words)
  - how grouping and suppression work (status definitions and count invariants)
  - how to run tests
  - **Results on SYNTHETIC demo data**, pasted from the actual CLI output: total alerts versus the naive baseline, P/R/F1, and missed incidents, with the tuning disclosure
  - limitations: no persistence across requests; no day-of-week model; seasonality detection needs ≥5 campaigns; the score is not a probability; the synthetic data is not official
  - the frontend contract: base URL `http://127.0.0.1:8000/api`, multipart field `file`, query parameters, the `AnalysisResponse` shape with an abbreviated real example, and `CORS_ORIGINS`
- [ ] **Step 5: Write `docs/CODE_WALKTHROUGH.md` for the presenter.**
  - One section per module, in pipeline order. Each section gives 3–5 sentences of plain English on what the module does, the key function to point at, and why it was designed that way.
  - Then a "Likely judge questions" Q&A. Each answer is 2–4 sentences:
    - Why median/MAD and not mean/std?
    - How do you avoid alerting on tiny campaigns? (the Poisson floor and minimum denominators)
    - How do you catch a 10% drift on a big campaign?
    - How do you know it's seasonality?
    - What is the score?
    - What did you miss and why?
    - What would you do with more time? (day-of-week baselines, persistence, feedback loop on muted alerts)
- [ ] **Step 6: Run final verification.** Run `python -m pytest -v` and paste the real pass/skip counts into the README. Start uvicorn once more and hit `/api/health`.
- [ ] **Step 7: Commit.** `git commit -m "feat: CLI report, README with real demo results, and code walkthrough"`

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| Read daily metrics, plain-English alerts, total alert count over 180 days | 2, 6, 9, 10 (CLI line + `summary.notifications_sent`) |
| Bands from each campaign's own volatility | 5 |
| Precision/recall incl. misses, honest false positives | 8, 10 |
| Broken vs seasonality, routed differently | 7 |
| First diagnostic step per alert type | 6 |
| Digest vs immediate by severity | 7 |
| CSV validation, aliases, duplicates, missing/invalid values | 3 |
| Derived metrics, zero-denominator safety | 4 |
| No leakage, min history, zero MAD, low-volume, missing days | 5 |
| Dedupe, grouping, cooldown, escalation, reopen, counts | 7 |
| health / demo-data / analyze endpoints, CORS, JSON-safe output | 1, 9 |
| The 12 required test cases | 3 (7, 11), 5 (1–6, 8), 7 (9, 10), 9 (11, 12) |
| README, Windows instructions, frontend contract | 10 |
| Synthetic data clearly labeled | 2, 9, 10 |
