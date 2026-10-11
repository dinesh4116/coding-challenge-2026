/* Browser-only CSV and decision engine. No uploaded data leaves this device. */
(function (root) {
  const REQUIRED = ["Search term", "Clicks", "Impressions", "Cost", "Conversions"];
  const ALIASES = {
    "search term": "Search term", "search terms": "Search term", query: "Search term",
    clicks: "Clicks", "impr.": "Impressions", impr: "Impressions", impressions: "Impressions",
    cost: "Cost", "cost (inr)": "Cost", conversions: "Conversions",
    campaign: "Campaign", "campaign name": "Campaign", "ad group": "Ad group", "ad group name": "Ad group",
    "row id": "Row ID", "match type": "Match type", "conversion value": "Conversion value"
  };

  function parseCsv(text) {
    text = String(text || "").replace(/^\uFEFF/, "");
    const rows = [];
    let row = [], field = "", quoted = false;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
        else if (ch === '"') quoted = false;
        else field += ch;
      } else if (ch === '"' && field.length === 0) quoted = true;
      else if (ch === ",") { row.push(field); field = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i += 1;
        row.push(field); field = "";
        if (row.some((cell) => String(cell).trim() !== "")) rows.push(row);
        row = [];
      } else field += ch;
    }
    if (quoted) throw new Error("The CSV has an unclosed quoted field. Re-export it as a standard CSV and try again.");
    if (field.length || row.length) { row.push(field); if (row.some((cell) => String(cell).trim() !== "")) rows.push(row); }
    if (rows.length < 2) throw new Error("The CSV needs a header row and at least one search-term row.");
    const headers = rows[0].map((value) => String(value).trim());
    const mapped = headers.map((header) => ALIASES[header.toLowerCase().replace(/\uFEFF/g, "").replace(/_/g, " ").replace(/\s+/g, " ")] || header);
    const missing = REQUIRED.filter((name) => !mapped.includes(name));
    if (missing.length) throw new Error(`Missing required columns: ${missing.join(", ")}. Include search term, clicks, impressions, cost, and conversions.`);
    const data = [];
    let emptyTerms = 0;
    for (let i = 1; i < rows.length; i += 1) {
      const cells = rows[i], record = { _rowId: data.length };
      for (let j = 0; j < headers.length; j += 1) record[mapped[j]] = cells[j] ?? "";
      record["Search term"] = String(record["Search term"] || "").trim();
      if (!record["Search term"]) { emptyTerms += 1; continue; }
      for (const name of ["Clicks", "Impressions", "Cost", "Conversions", "Conversion value"]) {
        if (name in record) record[name] = numeric(record[name]);
      }
      record.Campaign = String(record.Campaign || "").trim();
      record["Ad group"] = String(record["Ad group"] || "").trim();
      data.push(record);
    }
    if (!data.length) throw new Error("No non-empty search terms were found.");
    data.forEach((record, index) => { record._rowId = index; });
    return { rows: data, emptyTerms, columns: headers };
  }

  function numeric(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    const cleaned = String(value ?? "").trim().replace(/,/g, "").replace(/[^\d.\-]/g, "");
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function decide(row, policy) {
    const clicks = row.Clicks, conversions = row.Conversions, cost = row.Cost;
    const value = row["Conversion value"] || 0;
    let decision, confidence = "Low", reason;
    if (conversions === 0 && value > 0) {
      decision = "REVIEW";
      reason = `Conversion value ${value} is recorded with zero conversions; reconcile the source data before acting.`;
    } else if (clicks >= policy.promoteClicks && conversions >= policy.promoteConversions) {
      decision = "PROMOTE";
      confidence = conversions >= 4 && clicks >= 30 ? "High" : "Medium";
      reason = `${conversions} conversions across ${clicks} clicks meet the configured minimum (${policy.promoteConversions} conversions, ${policy.promoteClicks} clicks); verify intent and value.`;
      if (value > 0) reason += ` Recorded conversion value is ${value}.`;
    } else if (clicks >= policy.blockClicks && conversions === 0 && cost > 0) {
      decision = "BLOCK";
      confidence = clicks >= 50 ? "High" : clicks >= 35 ? "Medium" : "Low";
      reason = `${clicks} clicks and ${formatNumber(cost)} spend with no conversions indicate likely wasted spend; check attribution lag.`;
    } else if (clicks < policy.reviewBelowClicks && conversions > 0) {
      decision = "REVIEW";
      reason = `Only ${clicks} clicks support ${conversions} conversion(s); thin data, so review before promoting.`;
    } else if (clicks < policy.reviewBelowClicks) {
      decision = "REVIEW";
      reason = `Only ${clicks} clicks; insufficient evidence for a reliable promote or block decision.`;
    } else if (conversions > 0) {
      decision = "REVIEW";
      reason = `${conversions} conversion(s) but below the ${policy.promoteConversions}-conversion and ${policy.promoteClicks}-click promotion thresholds; human review required.`;
    } else {
      decision = "IGNORE";
      reason = `${clicks} clicks and no conversions; below the evidence threshold for blocking, so monitor.`;
    }
    return { decision, confidence, reason };
  }

  function analyze(rows, policy) {
    const normalized = new Map();
    const output = rows.map((row) => {
      const result = decide(row, policy);
      const query = row["Search term"].toLocaleLowerCase().normalize("NFKC").replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
      normalized.set(query, (normalized.get(query) || 0) + 1);
      return { ...row, Decision: result.decision, Confidence: result.confidence, Reason: result.reason, "Normalized query": query };
    });
    for (const row of output) row["Duplicate group size"] = normalized.get(row["Normalized query"]);
    return output;
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value) || 0);
  }

  function csvText(rows, columns) {
    const escape = (value) => {
      const text = value == null ? "" : String(value);
      return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    return "\uFEFF" + [columns.map(escape).join(","), ...rows.map((row) => columns.map((col) => escape(row[col])).join(","))].join("\r\n");
  }

  const api = { REQUIRED, parseCsv, numeric, decide, analyze, csvText, formatNumber };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.TriageEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
