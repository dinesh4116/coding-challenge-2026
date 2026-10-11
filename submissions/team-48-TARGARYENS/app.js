(() => {
  const E = window.TriageEngine;
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const PAGE_SIZE = 8;
  const state = {
    rows: [], analyzed: [], columns: [], emptyTerms: 0, fileName: "", corrections: new Map(),
    tab: "overview", reviewPage: 1, termsPage: 1,
    policy: { promoteClicks: 20, promoteConversions: 2, blockClicks: 25, reviewBelowClicks: 8 }
  };
  const money = (number) => `₹${E.formatNumber(number)}`;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
  const query = (row) => String(row["Search term"] || "");
  const finalDecision = (row) => state.corrections.get(row._rowId)?.decision || row.Decision;
  const notice = (message, kind = "error") => {
    const box = $("#notice"); box.textContent = message; box.className = `notice ${kind}`;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  };
  const clearNotice = () => { $("#notice").className = "notice hidden"; };

  $("#today-label").textContent = new Intl.DateTimeFormat("en", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).format(new Date()).toUpperCase();

  function getPolicy() {
    for (const [id, key, min, max] of [["promote-clicks", "promoteClicks", 1, 500], ["promote-conversions", "promoteConversions", 2, 50], ["block-clicks", "blockClicks", 1, 500], ["review-clicks", "reviewBelowClicks", 1, 100]]) {
      const input = $(`#${id}`), value = Math.max(min, Math.min(max, Math.round(Number(input.value) || min)));
      input.value = value; state.policy[key] = value;
    }
  }
  function refreshAnalysis() {
    if (!state.rows.length) return;
    getPolicy();
    state.analyzed = E.analyze(state.rows, state.policy);
    renderDashboard();
  }

  async function loadFile(file) {
    if (!file || !/\.csv$/i.test(file.name) && file.type !== "text/csv") {
      notice("Choose a CSV report to continue."); return;
    }
    clearNotice();
    try {
      const text = new TextDecoder("utf-8").decode(await file.arrayBuffer());
      const parsed = E.parseCsv(text);
      state.rows = parsed.rows; state.columns = parsed.columns.map((header) => header.trim().replace(/\uFEFF/g, "").replace(/_/g, " ").replace(/\s+/g, " ")).map((header) => {
        const map = { "search terms": "Search term", "search term": "Search term", query: "Search term", clicks: "Clicks", "impr.": "Impressions", impr: "Impressions", impressions: "Impressions", cost: "Cost", "cost (inr)": "Cost", conversions: "Conversions", campaign: "Campaign", "campaign name": "Campaign", "ad group": "Ad group", "ad group name": "Ad group", "row id": "Row ID", "match type": "Match type", "conversion value": "Conversion value" };
        return map[header.toLowerCase()] || header;
      }).filter((name, index, names) => names.indexOf(name) === index);
      state.emptyTerms = parsed.emptyTerms; state.fileName = file.name; state.corrections.clear();
      $("#hero").classList.add("compact");
      $("#upload-panel").classList.add("hidden"); $("#dashboard").classList.remove("hidden");
      $("#file-title").textContent = file.name; $("#file-subtitle").textContent = `${E.formatNumber(state.rows.length)} valid search terms · ${E.formatNumber(state.emptyTerms)} blank rows skipped · browser-only session`;
      refreshAnalysis(); clearNotice();
      $("#dashboard").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { notice(error.message || "Could not read this CSV. Check the file and try again."); }
  }

  $("#csv-file").addEventListener("change", (event) => loadFile(event.target.files?.[0]));
  $("#change-file").addEventListener("click", () => $("#csv-file").click());
  const dropzone = $("#dropzone");
  for (const eventName of ["dragenter", "dragover"]) dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.add("dragging"); });
  for (const eventName of ["dragleave", "drop"]) dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.remove("dragging"); });
  dropzone.addEventListener("drop", (event) => loadFile(event.dataTransfer.files?.[0]));

  function activateTab(tab) {
    state.tab = tab;
    $$("[data-tab]").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    $$("[data-pane]").forEach((pane) => pane.classList.toggle("hidden", pane.dataset.pane !== tab));
    if (tab === "review") renderReview();
    if (tab === "terms") renderTerms();
    if (tab === "clusters") renderClusters();
    if (tab === "campaigns") renderCampaigns();
    if (tab === "exports") renderExports();
  }
  $$("[data-tab]").forEach((button) => button.addEventListener("click", () => activateTab(button.dataset.tab)));
  $$("[data-jump]").forEach((button) => button.addEventListener("click", () => { activateTab(button.dataset.jump); $(".workspace-panel").scrollIntoView({ behavior: "smooth", block: "start" }); }));

  function metricCard(title, value, foot, accent = false) {
    return `<article class="metric-card ${accent ? "accent" : ""}"><small>${esc(title)}</small><strong>${esc(value)}</strong><em>${esc(foot)}</em></article>`;
  }
  function renderDashboard() {
    const finalCounts = { PROMOTE: 0, BLOCK: 0, REVIEW: 0, IGNORE: 0 };
    const finalCosts = { PROMOTE: 0, BLOCK: 0, REVIEW: 0, IGNORE: 0 };
    let totalSpend = 0, pendingReview = 0, corrected = 0;
    for (const row of state.analyzed) {
      const decision = finalDecision(row); finalCounts[decision] = (finalCounts[decision] || 0) + 1;
      finalCosts[decision] = (finalCosts[decision] || 0) + row.Cost; totalSpend += row.Cost;
      if (row.Decision === "REVIEW" && !state.corrections.has(row._rowId)) pendingReview += 1;
      if (state.corrections.has(row._rowId)) corrected += 1;
    }
    $("#metrics").innerHTML = [
      metricCard("SEARCH TERMS", E.formatNumber(state.analyzed.length), `${E.formatNumber(state.emptyTerms)} blank rows skipped`),
      metricCard("PROMOTE", E.formatNumber(finalCounts.PROMOTE), "current action plan"),
      metricCard("BLOCK", E.formatNumber(finalCounts.BLOCK), "negative candidates"),
      metricCard("HUMAN REVIEW", E.formatNumber(pendingReview), `${E.formatNumber(corrected)} decisions corrected`, true),
      metricCard("TOTAL REPORTED SPEND", money(totalSpend), "historical report cost")
    ].join("");
    const maxSpend = Math.max(...Object.values(finalCosts), 1);
    $("#spend-bars").innerHTML = ["PROMOTE", "BLOCK", "REVIEW", "IGNORE"].map((kind) => `<div class="hbar" data-kind="${kind}"><span>${kind === "REVIEW" ? "HUMAN REVIEW" : kind}</span><div class="hbar-track"><div class="hbar-fill" style="width:${Math.max(0, finalCosts[kind] / maxSpend * 100)}%"></div></div><b>${money(finalCosts[kind])}</b></div>`).join("");
    const countMax = Math.max(...Object.values(finalCounts), 1);
    $("#decision-mix").innerHTML = ["PROMOTE", "BLOCK", "REVIEW", "IGNORE"].map((kind) => `<div class="mix-row" data-kind="${kind}"><span>${kind}</span><div class="mix-track"><i style="width:${finalCounts[kind] / countMax * 100}%"></i></div><b>${E.formatNumber(finalCounts[kind])}</b></div>`).join("");
    $("#review-badge").textContent = E.formatNumber(pendingReview); $("#review-tab-count").textContent = E.formatNumber(pendingReview);
    const warning = $("#review-warning");
    if (pendingReview) { warning.textContent = `${E.formatNumber(pendingReview)} terms have mixed or thin evidence. Review them before taking action; one conversion alone never auto-promotes a term.`; warning.classList.remove("hidden"); }
    else { warning.classList.add("hidden"); }
    const uncertain = state.analyzed.filter((row) => row.Decision === "REVIEW" && !state.corrections.has(row._rowId)).sort((a, b) => b.Cost - a.Cost)[0];
    $("#next-action-title").textContent = uncertain ? `Start with “${query(uncertain)}”.` : "Your review queue is clear.";
    $("#next-action-text").textContent = uncertain ? `${money(uncertain.Cost)} reported spend · ${uncertain.Clicks} clicks · ${uncertain.Conversions} conversion(s). ${uncertain.Reason}` : "New high-impact uncertainty will appear here as you review this report.";
    if (state.tab === "review") renderReview();
    if (state.tab === "terms") renderTerms();
    if (state.tab === "clusters") renderClusters();
    if (state.tab === "campaigns") renderCampaigns();
  }

  function renderReview() {
    const search = $("#review-search").value.trim().toLocaleLowerCase(), confidence = $("#review-confidence").value;
    const matches = state.analyzed.filter((row) => row.Decision === "REVIEW" && !state.corrections.has(row._rowId) && (!search || query(row).toLocaleLowerCase().includes(search)) && (confidence === "All" || row.Confidence === confidence)).sort((a, b) => b.Cost - a.Cost);
    const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE)); state.reviewPage = Math.min(state.reviewPage, pageCount);
    const pageRows = matches.slice((state.reviewPage - 1) * PAGE_SIZE, state.reviewPage * PAGE_SIZE);
    const list = $("#review-list");
    if (!pageRows.length) { list.innerHTML = `<div class="empty-state">${state.analyzed.length ? "No terms match those filters. Clear the search or confidence filter to see more." : "Upload a search terms report to start the review queue."}</div>`; }
    else list.innerHTML = pageRows.map((row) => {
      const note = state.corrections.get(row._rowId)?.note || "";
      const context = [row.Campaign, row["Ad group"], row["Match type"]].filter(Boolean).join(" · ");
      return `<article class="review-card" data-review-id="${row._rowId}"><div><div class="review-query">${esc(query(row))}</div><span class="decision-chip">HUMAN REVIEW · ${esc(row.Confidence.toUpperCase())} CONFIDENCE</span><p class="review-reason">${esc(row.Reason)}</p>${context ? `<div class="review-context">${esc(context)}</div>` : ""}<div class="review-stats"><span><small>IMPRESSIONS</small><b>${E.formatNumber(row.Impressions)}</b></span><span><small>CLICKS</small><b>${E.formatNumber(row.Clicks)}</b></span><span><small>COST</small><b>${money(row.Cost)}</b></span><span><small>CONVERSIONS</small><b>${E.formatNumber(row.Conversions)}</b></span></div></div><div class="review-control"><label>Human decision<select class="correction-choice"><option value="">Use recommendation</option><option>PROMOTE</option><option>BLOCK</option><option>IGNORE</option></select></label><label>Reviewer note (optional)<input class="correction-note" value="${esc(note)}" placeholder="Why are you changing it?" /></label><button class="button primary save-correction">Save decision</button></div></article>`;
    }).join("");
    $$(".save-correction", list).forEach((button) => button.addEventListener("click", () => {
      const card = button.closest("[data-review-id]"), id = Number(card.dataset.reviewId), choice = $(".correction-choice", card).value, note = $(".correction-note", card).value.trim();
      if (!choice && !note) { notice("Choose a human decision before saving the correction."); return; }
      if (choice) state.corrections.set(id, { decision: choice, note }); else state.corrections.set(id, { decision: "REVIEW", note });
      renderDashboard(); notice("Human decision saved in this browser session and included in the audit export.", "success");
    }));
    renderPagination($("#review-pagination"), state.reviewPage, pageCount, `${matches.length} terms to review`, (page) => { state.reviewPage = page; renderReview(); });
  }

  function renderPagination(container, page, pages, summary, onPage) {
    container.innerHTML = `<button ${page <= 1 ? "disabled" : ""} data-page="${page - 1}">← Previous</button><span>${esc(summary)} · page ${page} of ${pages}</span><button ${page >= pages ? "disabled" : ""} data-page="${page + 1}">Next →</button>`;
    $$('button[data-page]', container).forEach((button) => button.addEventListener("click", () => onPage(Number(button.dataset.page))));
  }

  function renderTerms() {
    const search = $("#terms-search").value.trim().toLocaleLowerCase(), decision = $("#terms-decision").value;
    const matches = state.analyzed.filter((row) => (!search || query(row).toLocaleLowerCase().includes(search)) && (decision === "All" || finalDecision(row) === decision));
    const pageCount = Math.max(1, Math.ceil(matches.length / 50)); state.termsPage = Math.min(state.termsPage, pageCount);
    const pageRows = matches.slice((state.termsPage - 1) * 50, state.termsPage * 50);
    $("#terms-body").innerHTML = pageRows.map((row) => `<tr><td>${esc(query(row))}</td><td><span class="decision-badge ${finalDecision(row).toLowerCase()}">${esc(finalDecision(row))}</span></td><td>${E.formatNumber(row.Clicks)}</td><td>${money(row.Cost)}</td><td>${E.formatNumber(row.Conversions)}</td><td>${esc(row.Confidence)} confidence · ${esc(state.corrections.get(row._rowId)?.note || row.Reason)}</td></tr>`).join("");
    renderPagination($("#terms-pagination"), state.termsPage, pageCount, `${E.formatNumber(matches.length)} terms`, (page) => { state.termsPage = page; renderTerms(); });
  }

  function renderClusters() {
    const groups = new Map();
    for (const row of state.analyzed) {
      if (row["Duplicate group size"] <= 1) continue;
      const key = row["Normalized query"];
      if (!groups.has(key)) groups.set(key, { key, terms: new Set(), rows: [], clicks: 0, cost: 0, conversions: 0 });
      const group = groups.get(key); group.terms.add(query(row)); group.rows.push(row); group.clicks += row.Clicks; group.cost += row.Cost; group.conversions += row.Conversions;
    }
    const sorted = [...groups.values()].sort((a, b) => b.cost - a.cost);
    const repeatedRows = sorted.reduce((sum, group) => sum + group.rows.length, 0);
    $("#cluster-summary").textContent = `${E.formatNumber(repeatedRows)} repeated rows · ${E.formatNumber(sorted.length)} groups`;
    $("#cluster-list").innerHTML = sorted.length ? sorted.slice(0, 50).map((group) => `<article class="cluster-card"><div><div class="cluster-query">${esc(group.key)}</div><div class="cluster-variants">${group.terms.size} wording variant(s) · ${group.rows.map((row) => esc(row.Campaign || "No campaign")).filter((value, index, all) => all.indexOf(value) === index).slice(0, 3).join(" · ")}</div></div><div class="cluster-numbers"><span><small>ROWS</small><b>${group.rows.length}</b></span><span><small>CLICKS</small><b>${E.formatNumber(group.clicks)}</b></span><span><small>SPEND</small><b>${money(group.cost)}</b></span><span><small>CONV.</small><b>${E.formatNumber(group.conversions)}</b></span></div></article>`).join("") : `<div class="empty-state">No repeated normalized queries in this upload.</div>`;
  }

  function renderCampaigns() {
    const campaigns = new Map();
    for (const row of state.analyzed) {
      if (!row.Campaign) continue;
      if (!campaigns.has(row.Campaign)) campaigns.set(row.Campaign, { name: row.Campaign, cost: 0, counts: { PROMOTE: 0, BLOCK: 0, REVIEW: 0, IGNORE: 0 }, spend: { PROMOTE: 0, BLOCK: 0, REVIEW: 0, IGNORE: 0 } });
      const campaign = campaigns.get(row.Campaign), decision = finalDecision(row);
      campaign.cost += row.Cost; campaign.counts[decision] += 1; campaign.spend[decision] += row.Cost;
    }
    const sorted = [...campaigns.values()].sort((a, b) => b.cost - a.cost).slice(0, 50), kinds = ["PROMOTE", "BLOCK", "REVIEW", "IGNORE"];
    $("#campaign-list").innerHTML = sorted.length ? sorted.map((campaign) => {
      const width = campaign.cost || 1;
      const bars = kinds.map((kind) => `<i class="${kind.toLowerCase()}" style="width:${campaign.spend[kind] / width * 100}%" title="${kind}: ${money(campaign.spend[kind])}"></i>`).join("");
      const legend = kinds.map((kind) => `<span><i class="${kind.toLowerCase()}"></i>${kind} ${campaign.counts[kind]}</span>`).join("");
      return `<article class="campaign-card"><div class="campaign-head"><strong>${esc(campaign.name)}</strong><span>${money(campaign.cost)} historical spend</span></div><div class="stacked-track">${bars}</div><div class="campaign-legend">${legend}</div></article>`;
    }).join("") : `<div class="empty-state">No campaign values were found. Add a Campaign column to compare spend by campaign.</div>`;
  }

  function exportRows(kind) {
    const rows = state.analyzed.map((row) => {
      const correction = state.corrections.get(row._rowId) || {};
      return { ...row, "Recommended decision": row.Decision, "Human decision": correction.decision === row.Decision ? "" : correction.decision || "", "Reviewer note": correction.note || "", "Final decision": finalDecision(row) };
    });
    if (kind === "promote") return {
      name: "promote_candidates.csv", columns: ["Keyword", "Match type", "Campaign", "Ad group", "Confidence", "Reason"],
      rows: rows.filter((row) => row["Final decision"] === "PROMOTE").map((row) => ({ Keyword: row["Search term"], "Match type": "Exact", Campaign: row.Campaign, "Ad group": row["Ad group"], Confidence: row.Confidence, Reason: row.Reason }))
    };
    if (kind === "block") return {
      name: "negative_candidates.csv", columns: ["Keyword", "Match type", "Level", "Campaign", "Ad group", "Confidence", "Reason"],
      rows: rows.filter((row) => row["Final decision"] === "BLOCK").map((row) => ({ Keyword: `[${row["Search term"]}]`, "Match type": "Negative exact", Level: row["Ad group"] ? "Ad group" : "Campaign", Campaign: row.Campaign, "Ad group": row["Ad group"], Confidence: row.Confidence, Reason: row.Reason }))
    };
    const columns = [...state.columns, "Recommended decision", "Human decision", "Reviewer note", "Final decision", "Confidence", "Reason", "Duplicate group size"];
    return { name: "search_term_triage.csv", columns: [...new Set(columns)], rows };
  }
  function download(kind) {
    const pack = exportRows(kind), blob = new Blob([E.csvText(pack.rows, pack.columns)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = pack.name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  $("#export-audit").addEventListener("click", () => download("audit"));
  $("#export-promote").addEventListener("click", () => download("promote"));
  $("#export-block").addEventListener("click", () => download("block"));
  function renderExports() {
    const promote = state.analyzed.filter((row) => finalDecision(row) === "PROMOTE").length;
    const block = state.analyzed.filter((row) => finalDecision(row) === "BLOCK").length;
    $("#export-promote").innerHTML = `Download ${E.formatNumber(promote)} rows <span>↓</span>`;
    $("#export-block").innerHTML = `Download ${E.formatNumber(block)} rows <span>↓</span>`;
  }

  for (const id of ["promote-clicks", "promote-conversions", "block-clicks", "review-clicks"]) $(`#${id}`).addEventListener("change", refreshAnalysis);
  $("#review-search").addEventListener("input", () => { state.reviewPage = 1; renderReview(); });
  $("#review-confidence").addEventListener("change", () => { state.reviewPage = 1; renderReview(); });
  $("#terms-search").addEventListener("input", () => { state.termsPage = 1; renderTerms(); });
  $("#terms-decision").addEventListener("change", () => { state.termsPage = 1; renderTerms(); });
  activateTab("overview");
})();
