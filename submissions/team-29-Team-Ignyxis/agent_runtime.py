"""Dataset-grounded agent tools for the PS-01 Search Term Triage Engine.

The agent only inspects the active uploaded dataset and generates recommendations.
It never changes a live advertising account.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd

DISPLAY_COLUMNS = [
    c for c in [
        "row_id", "search_term", "campaign", "ad_group", "match_type",
        "impressions", "clicks", "cost", "conversions", "conversion_value",
        "ctr", "conversion_rate", "cpa", "roas", "intent_category",
        "triage_decision", "confidence", "human_review", "reason",
    ]
]


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _safe_records(df: pd.DataFrame, columns: list[str] | None = None, limit: int = 12) -> list[dict[str, Any]]:
    use_cols = [c for c in (columns or DISPLAY_COLUMNS) if c in df.columns]
    if not use_cols:
        return []
    out = df[use_cols].head(max(0, min(int(limit), 50))).copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(4)
    out = out.astype(object).where(pd.notna(out), None)
    return [{k: _json_safe(v) for k, v in row.items()} for row in out.to_dict(orient="records")]


def dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    d = df
    spend = float(_num(d.get("cost", pd.Series(dtype=float))).sum()) if "cost" in d else 0.0
    value = float(_num(d.get("conversion_value", pd.Series(dtype=float))).sum()) if "conversion_value" in d else 0.0
    clicks = float(_num(d.get("clicks", pd.Series(dtype=float))).sum()) if "clicks" in d else 0.0
    impressions = float(_num(d.get("impressions", pd.Series(dtype=float))).sum()) if "impressions" in d else 0.0
    conversions = float(_num(d.get("conversions", pd.Series(dtype=float))).sum()) if "conversions" in d else 0.0
    dec_counts = d["triage_decision"].value_counts().to_dict() if "triage_decision" in d else {}
    review_n = int(d["human_review"].fillna(False).astype(bool).sum()) if "human_review" in d else 0
    campaigns = int(d["campaign"].nunique(dropna=True)) if "campaign" in d else 0
    return {
        "rows": int(len(d)),
        "campaigns": campaigns,
        "spend": round(spend, 2),
        "conversion_value": round(value, 2),
        "clicks": int(clicks),
        "impressions": int(impressions),
        "conversions": int(conversions),
        "aggregate_roas": round(value / spend, 4) if spend > 0 else None,
        "aggregate_ctr": round(clicks / impressions, 6) if impressions > 0 else None,
        "decision_counts": {str(k): int(v) for k, v in dec_counts.items()},
        "human_review_rows": review_n,
        "note": "Human-review flags overlap with decision categories; do not add them as a fourth decision category."
    }


def find_search_terms(
    df: pd.DataFrame,
    query: str = "",
    decision: str = "ALL",
    min_spend: float | None = None,
    min_clicks: int | None = None,
    min_conversions: int | None = None,
    review_only: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    view = df.copy()
    if query and query.strip():
        q = query.strip().lower()
        mask = pd.Series(False, index=view.index)
        for col in ["search_term", "campaign", "ad_group", "reason", "intent_category"]:
            if col in view.columns:
                mask |= view[col].fillna("").astype(str).str.lower().str.contains(re.escape(q), na=False)
        view = view[mask]
    decision = (decision or "ALL").upper()
    if decision in {"PROMOTE", "BLOCK", "IGNORE"} and "triage_decision" in view:
        view = view[view["triage_decision"].astype(str).str.upper() == decision]
    if min_spend is not None and "cost" in view:
        view = view[_num(view["cost"]) >= float(min_spend)]
    if min_clicks is not None and "clicks" in view:
        view = view[_num(view["clicks"]) >= int(min_clicks)]
    if min_conversions is not None and "conversions" in view:
        view = view[_num(view["conversions"]) >= int(min_conversions)]
    if review_only and "human_review" in view:
        view = view[view["human_review"].fillna(False).astype(bool)]
    if "cost" in view:
        view = view.assign(_agent_cost=_num(view["cost"])).sort_values("_agent_cost", ascending=False)
    total = int(len(view))
    total_spend = round(float(_num(view["cost"]).sum()), 2) if "cost" in view else 0
    total_conversions = int(_num(view["conversions"]).sum()) if "conversions" in view else 0
    selected = view.drop(columns=["_agent_cost"], errors="ignore")
    return {
        "matching_rows": total,
        "total_matching_spend": total_spend,
        "total_matching_conversions": total_conversions,
        "rows": _safe_records(selected, limit=limit),
        "truncated": total > min(max(int(limit), 0), 50),
    }


def compare_campaigns(df: pd.DataFrame, metric: str = "roas", descending: bool = True, limit: int = 10) -> dict[str, Any]:
    if "campaign" not in df:
        return {"error": "The uploaded dataset has no campaign column."}
    d = df.copy()
    for col in ["impressions", "clicks", "cost", "conversions", "conversion_value"]:
        if col in d:
            d[col] = _num(d[col])
    agg = d.groupby("campaign", dropna=False).agg(
        rows=("campaign", "size"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        spend=("cost", "sum"),
        conversions=("conversions", "sum"),
        conversion_value=("conversion_value", "sum"),
    ).reset_index()
    agg["roas"] = agg["conversion_value"].div(agg["spend"].where(agg["spend"] > 0))
    agg["ctr"] = agg["clicks"].div(agg["impressions"].where(agg["impressions"] > 0))
    agg["conversion_rate"] = agg["conversions"].div(agg["clicks"].where(agg["clicks"] > 0))
    agg["cpa"] = agg["spend"].div(agg["conversions"].where(agg["conversions"] > 0))
    metric_aliases = {"spend": "spend", "cost": "spend", "roas": "roas", "return": "roas", "conversion_value": "conversion_value", "revenue": "conversion_value", "conversions": "conversions", "clicks": "clicks", "ctr": "ctr", "conversion_rate": "conversion_rate", "cpa": "cpa", "impressions": "impressions"}
    chosen = metric_aliases.get((metric or "roas").lower(), "roas")
    agg = agg.sort_values(chosen, ascending=not bool(descending), na_position="last")
    return {
        "sorted_by": chosen,
        "direction": "descending" if descending else "ascending",
        "campaign_count": int(len(agg)),
        "campaigns": _safe_records(agg, columns=["campaign", "rows", "spend", "clicks", "conversions", "conversion_value", "roas", "ctr", "conversion_rate", "cpa"], limit=limit),
        "note": "ROAS is aggregated conversion value divided by aggregated spend. Correlation does not establish causation."
    }


def investigate_term(df: pd.DataFrame, search_term: str, limit: int = 8) -> dict[str, Any]:
    if not search_term or not search_term.strip():
        return {"error": "Provide a search-term phrase to inspect."}
    q = search_term.strip().lower()
    if "search_term" not in df:
        return {"error": "The uploaded dataset has no search_term column."}
    exact = df[df["search_term"].fillna("").astype(str).str.lower() == q]
    matches = exact if not exact.empty else df[df["search_term"].fillna("").astype(str).str.lower().str.contains(re.escape(q), na=False)]
    return {
        "query": search_term,
        "match_type": "exact" if not exact.empty else "substring / partial" if not matches.empty else "none",
        "matching_rows": int(len(matches)),
        "rows": _safe_records(matches, limit=limit),
        "guidance": "Explain the existing rule output using these fields. Do not call a rule-based confidence label a probability. If rows conflict or are ambiguous, recommend human review."
    }


def export_search_terms(
    df: pd.DataFrame,
    query: str = "",
    decision: str = "ALL",
    min_spend: float | None = None,
    min_clicks: int | None = None,
    min_conversions: int | None = None,
    review_only: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    filtered = find_search_terms(
        df, query=query, decision=decision, min_spend=min_spend,
        min_clicks=min_clicks, min_conversions=min_conversions,
        review_only=review_only, limit=0,
    )
    view = df.copy()
    if query and query.strip():
        q = query.strip().lower()
        mask = pd.Series(False, index=view.index)
        for col in ["search_term", "campaign", "ad_group", "reason", "intent_category"]:
            if col in view.columns:
                mask |= view[col].fillna("").astype(str).str.lower().str.contains(re.escape(q), na=False)
        view = view[mask]
    decision = (decision or "ALL").upper()
    if decision in {"PROMOTE", "BLOCK", "IGNORE"} and "triage_decision" in view:
        view = view[view["triage_decision"].astype(str).str.upper() == decision]
    if min_spend is not None and "cost" in view:
        view = view[_num(view["cost"]) >= float(min_spend)]
    if min_clicks is not None and "clicks" in view:
        view = view[_num(view["clicks"]) >= int(min_clicks)]
    if min_conversions is not None and "conversions" in view:
        view = view[_num(view["conversions"]) >= int(min_conversions)]
    if review_only and "human_review" in view:
        view = view[view["human_review"].fillna(False).astype(bool)]
    return view.copy(), {"export_rows": int(len(view)), "filters": {"query": query, "decision": decision, "min_spend": min_spend, "min_clicks": min_clicks, "min_conversions": min_conversions, "review_only": review_only}}


TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "get_dataset_summary", "description": "Summarize the currently uploaded and triaged dataset, including row count, decision counts, spend, conversions, aggregate ROAS and review count.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "find_search_terms", "description": "Find and filter search-term records by phrase, campaign, decision, spend, clicks, conversions or human-review flag. Returns actual matched records and totals.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Phrase to search in search term, campaign, ad group, reason or intent category; empty for all records."}, "decision": {"type": "string", "enum": ["ALL", "PROMOTE", "BLOCK", "IGNORE"]}, "min_spend": {"type": ["number", "null"]}, "min_clicks": {"type": ["integer", "null"]}, "min_conversions": {"type": ["integer", "null"]}, "review_only": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["query", "decision", "min_spend", "min_clicks", "min_conversions", "review_only", "limit"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "compare_campaigns", "description": "Compare and rank campaigns using a dataset metric such as ROAS, spend, conversions, clicks, CTR or CPA.", "parameters": {"type": "object", "properties": {"metric": {"type": "string", "enum": ["roas", "spend", "conversions", "clicks", "ctr", "conversion_rate", "cpa", "conversion_value", "impressions"]}, "descending": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["metric", "descending", "limit"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "investigate_term", "description": "Inspect a specific search phrase and return the actual uploaded rows, triage decisions, confidence, reasons and metrics.", "parameters": {"type": "object", "properties": {"search_term": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["search_term", "limit"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "export_search_terms", "description": "Prepare a downloadable CSV from the active dataset filtered by query, decision, minimum spend/clicks/conversions or human-review flag. Use this when the user asks to export or download records.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "decision": {"type": "string", "enum": ["ALL", "PROMOTE", "BLOCK", "IGNORE"]}, "min_spend": {"type": ["number", "null"]}, "min_clicks": {"type": ["integer", "null"]}, "min_conversions": {"type": ["integer", "null"]}, "review_only": {"type": "boolean"}}, "required": ["query", "decision", "min_spend", "min_clicks", "min_conversions", "review_only"], "additionalProperties": False}}},
]


def execute_tool(name: str, args: dict[str, Any], df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame | None]:
    """Execute a permitted, read-only dataset tool. Returns (JSON result, export df if requested)."""
    args = args or {}
    if name == "get_dataset_summary":
        return dataset_summary(df), None
    if name == "find_search_terms":
        return find_search_terms(df, **args), None
    if name == "compare_campaigns":
        return compare_campaigns(df, **args), None
    if name == "investigate_term":
        return investigate_term(df, **args), None
    if name == "export_search_terms":
        out, meta = export_search_terms(df, **args)
        return meta, out
    return {"error": f"Unknown tool: {name}"}, None


def run_openai_agent(question: str, df: pd.DataFrame, api_key: str, history: list[dict[str, str]] | None = None, model: str = "gpt-4o-mini") -> tuple[str, pd.DataFrame | None]:
    """Run a tool-using agent via OpenAI API. Requires network access, API key and permission."""
    from openai import OpenAI  # imported only when user opts into API mode

    client = OpenAI(api_key=api_key)
    system_prompt = f"""You are the Search Term Triage Agent for a hackathon project. Help the user analyse only the currently uploaded triaged dataset and the advertiser's known product policy. Use tools to inspect actual data before making data-specific claims. Never invent figures, rows, quotes, or results. If data is insufficient, say so. Distinguish correlation from causation. Explain that PROMOTE/BLOCK/IGNORE are recommendations, not live account changes. Human-review flags overlap the 3 decision categories. When a user asks to export or download, call export_search_terms; the UI will expose a download button. Do not claim to modify or upload anything outside the app. Keep answers concise and practical. Current dataset rows: {len(df)}. Available data columns: {', '.join(map(str, df.columns))}."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if history:
        for m in history[-8:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": str(m["content"])[:6000]})
    messages.append({"role": "user", "content": question})
    last_export: pd.DataFrame | None = None
    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.1,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            return (msg.content or "I couldn't create a response for that request."), last_export
        messages.append(msg.model_dump(exclude_none=True))
        for tool_call in msg.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments or "{}")
                payload, export_df = execute_tool(tool_call.function.name, args, df)
                if export_df is not None:
                    last_export = export_df
            except Exception as exc:
                payload = {"error": f"Tool execution failed: {exc}"}
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(payload, ensure_ascii=False, default=str)[:18000]})
    return "I reached the maximum number of tool steps for this turn. Please narrow the request and try again.", last_export


def run_local_agent(question: str, df: pd.DataFrame) -> tuple[str, pd.DataFrame | None]:
    """No-key local mode for common tasks. It is intentionally not presented as a general LLM."""
    q = question.strip()
    low = q.lower()
    if not q:
        return "Ask me about the uploaded search-term dataset.", None
    if any(k in low for k in ["help", "what can you do", "examples", "capabilities"]):
        return ("**Local tool mode** can answer common dataset tasks without an API key. Try:\n\n"
                "- `Summarize this dataset`\n- `Which campaign has the highest ROAS?`\n"
                "- `Show blocked terms with spend above $100`\n- `Why was personal loan blocked?`\n"
                "- `Export BLOCK terms with spend above $100`\n\n"
                "For flexible, open-ended natural-language requests, configure an approved OpenAI API key in the sidebar. External API use may incur charges and should only be used if organisers permit it."), None
    if any(k in low for k in ["summary", "summarize", "summarise", "how many rows", "total spend", "decision counts", "dataset overview"]):
        s = dataset_summary(df)
        counts = s["decision_counts"]
        return (f"**Dataset summary**\n\n- Rows: **{s['rows']:,}**\n- Campaigns: **{s['campaigns']}**\n- Spend: **${s['spend']:,.2f}**\n- Conversion value: **${s['conversion_value']:,.2f}**\n- Conversions: **{s['conversions']:,}**\n- Aggregate ROAS: **{s['aggregate_roas'] if s['aggregate_roas'] is not None else 'N/A'}**\n- Decisions: PROMOTE **{counts.get('PROMOTE',0):,}**, BLOCK **{counts.get('BLOCK',0):,}**, IGNORE **{counts.get('IGNORE',0):,}**\n- Human review: **{s['human_review_rows']:,}** (overlaps decisions)."), None
    if any(k in low for k in ["campaign", "roas", "highest spend", "top campaign", "rank campaign", "compare campaign"]):
        metric = "spend" if "spend" in low or "cost" in low else "conversions" if "conversion" in low or "sales" in low else "ctr" if "ctr" in low or "click-through" in low else "cpa" if "cpa" in low else "roas"
        desc = not any(k in low for k in ["lowest", "least", "smallest", "ascending"])
        comp = compare_campaigns(df, metric=metric, descending=desc, limit=10)
        camp_rows = comp.get("campaigns", [])
        if not camp_rows:
            return "No campaign rows were available to compare.", None
        lines = [f"**Campaign ranking by {comp['sorted_by'].upper()}**"]
        for idx, row in enumerate(camp_rows, 1):
            val = row.get(comp["sorted_by"])
            sval = "N/A" if val is None else (f"${val:,.2f}" if comp["sorted_by"] in ["spend", "conversion_value", "cpa"] else f"{val:.2f}x" if comp["sorted_by"] == "roas" else f"{val:.2%}" if comp["sorted_by"] in ["ctr", "conversion_rate"] else f"{val:,.0f}")
            lines.append(f"{idx}. **{row.get('campaign')}** — {sval}; spend ${row.get('spend',0):,.2f}; conversions {row.get('conversions',0)}")
        lines.append("\nROAS is conversion value divided by spend; rankings are descriptive, not proof of causation.")
        return "\n".join(lines), None
    if "export" in low or "download" in low or "csv" in low:
        decision = next((x for x in ["PROMOTE", "BLOCK", "IGNORE"] if x.lower() in low), "ALL")
        spend_match = re.search(r"(?:above|over|greater than|more than|exceed(?:ing)?)\s*\$?\s*(\d+(?:\.\d+)?)", low)
        clicks_match = re.search(r"(?:at least|minimum|more than|over)\s*(\d+)\s*clicks?", low)
        query = ""
        if "personal loan" in low:
            query = "personal loan"
        elif "grant" in low:
            query = "grant"
        elif "working capital" in low:
            query = "working capital"
        out, meta = export_search_terms(df, query=query, decision=decision, min_spend=float(spend_match.group(1)) if spend_match else None, min_clicks=int(clicks_match.group(1)) if clicks_match else None, review_only="review" in low)
        return f"Prepared a CSV with **{len(out):,} rows** using filters: {meta['filters']}. Use the download button below this reply to save it.", out
    if any(k in low for k in ["block", "blocked", "negative keyword", "highest spend", "wasted spend", "waste money"]) and not any(k in low for k in ["why was", "why is", "explain", "inspect", "investigate", "decision for"]):
        decision = "BLOCK" if any(k in low for k in ["block", "blocked", "negative keyword"]) else "ALL"
        spend_match = re.search(r"(?:above|over|greater than|more than)\s*\$?\s*(\d+(?:\.\d+)?)", low)
        min_spend = float(spend_match.group(1)) if spend_match else None
        res = find_search_terms(df, decision=decision, min_spend=min_spend, limit=10)
        lines = [f"**Found {res['matching_rows']:,} matching rows** with total spend **${res['total_matching_spend']:,.2f}** and conversions **{res['total_matching_conversions']:,}**."]
        for r in res["rows"][:8]:
            lines.append(f"- `{r.get('search_term','')}` — {r.get('triage_decision','')}, spend ${float(r.get('cost') or 0):,.2f}; {r.get('reason','')}")
        if res["truncated"]:
            lines.append("\nShowing the first matching rows. Ask to export the matching terms for the complete list.")
        return "\n".join(lines), None
    quoted = re.search(r"[\"'`](.+?)[\"'`]", q)
    if quoted:
        term = quoted.group(1)
    else:
        term = ""
        for pattern in [r"(?:why was|why is|explain|investigate|inspect|details for|decision for|show me|search for|find)\s+(?:the\s+)?(?:term\s+)?(.+?)(?:\?|$)"]:
            match = re.search(pattern, low)
            if match:
                term = match.group(1)
                term = re.sub(r"\b(blocked|promoted|ignored|recommended|decision|search term|term|please|in dataset)\b", "", term).strip(" ?.!\"")
                break
    if term:
        res = investigate_term(df, term, limit=6)
        if res["matching_rows"]:
            lines = [f"**Search: `{term}`** — {res['matching_rows']:,} matching row(s) ({res['match_type']})."]
            for r in res["rows"]:
                lines.append(f"- Decision: **{r.get('triage_decision','N/A')}**; confidence **{r.get('confidence','N/A')}**; clicks {r.get('clicks','N/A')}; spend ${float(r.get('cost') or 0):,.2f}; conversions {r.get('conversions','N/A')}.\n  Reason: {r.get('reason','No reason recorded.')}")
            return "\n".join(lines), None
    return ("I’m in **local tool mode** (no API key), so I can handle common dataset tasks but not arbitrary free-form reasoning yet. Try `Summarize this dataset`, `Which campaign has the highest ROAS?`, `Show blocked terms with spend above $100`, `Why was 'personal loan' blocked?`, or `Export BLOCK terms with spend above $100`. If permitted, enter an OpenAI API key in the sidebar for more flexible tool-using conversations."), None
