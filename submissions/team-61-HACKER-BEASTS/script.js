
const headlineInput = document.getElementById("headline");
const descriptionInput = document.getElementById("description");
const ctaInput = document.getElementById("cta");
const urlInput = document.getElementById("pageUrl");
const pageTextInput = document.getElementById("pageText");

const results = document.getElementById("results");
const scoreOutput = document.getElementById("score");
const summaryOutput = document.getElementById("summary");
const findingsOutput = document.getElementById("findings");

let latestReport = null;

function normalize(text) {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

function loadExample() {
  headlineInput.value = "Get Your Loan Approved in 24 Hours!";
  descriptionInput.value = "Apply today for fast loan approval.";
  ctaInput.value = "Apply Now";
  urlInput.value = "https://example.com/personal-loans";

  pageTextInput.value =
    "Personal Loans Made Simple. " +
    "Apply online for a personal loan. " +
    "Submit your documents for review. " +
    "Approval times may vary.";

  results.hidden = true;
}

function auditMessage() {
  const headline = headlineInput.value.trim();
  const description = descriptionInput.value.trim();
  const cta = ctaInput.value.trim();
  const pageText = pageTextInput.value.trim();

  const adText = [headline, description, cta]
    .filter(Boolean)
    .join(". ");

  if (!adText || !pageText) {
    alert("Please enter the ad text and landing page text.");
    return;
  }

  const ad = normalize(adText);
  const page = normalize(pageText);
  const findings = [];

  // Check for a time promise and a possible disclaimer.
  const timePromise =
    /\b(within\s+\d+\s+(hours?|days?)|in\s+\d+\s+(hours?|days?)|same[- ]day|instant approval)\b/i.test(ad);

  const timeDisclaimer =
    /\b(approval times may vary|times may vary|subject to approval|approval is not guaranteed)\b/i.test(page);

  if (timePromise && timeDisclaimer) {
    findings.push({
      status: "Potential conflict",
      level: "review",
      claim: "Fast approval promise",
      evidence: pageText.match(
        /[^.!?\n]*(?:approval times may vary|times may vary|subject to approval|approval is not guaranteed)[^.!?\n]*[.!?]?/i
      )?.[0] || "",
      suggestion:
        "Review whether the 24-hour promise is supported by clear conditions on the landing page."
    });
  } else if (timePromise) {
    const promise = adText.match(
      /\b(?:within\s+\d+\s+(?:hours?|days?)|in\s+\d+\s+(?:hours?|days?)|same[- ]day|instant approval)\b/i
    )?.[0] || "Fast approval";

    findings.push({
      status: page.includes(normalize(promise))
        ? "Matching phrase found"
        : "Needs verification",
      level: page.includes(normalize(promise)) ? "ok" : "review",
      claim: "Time or speed promise",
      evidence: pageText.match(/[^.!?\n]*(approval|hours?|days?)[^.!?\n]*[.!?]?/i)?.[0] || "",
      suggestion:
        "Verify the promised time using reliable page evidence. A missing phrase does not by itself prove a mismatch."
    });
  }

  // Check whether the ad's main topic appears in the page.
  const importantWords = normalize(headline)
    .split(/[^a-z0-9]+/)
    .filter(word =>
      word.length > 3 &&
      !["your", "with", "from", "that", "this", "hours"].includes(word)
    );

  const uniqueWords = [...new Set(importantWords)];
  const matchedWords = uniqueWords.filter(word => page.includes(word));

  if (uniqueWords.length > 0) {
    const ratio = matchedWords.length / uniqueWords.length;

    findings.push({
      status: ratio >= 0.4
        ? "Some topic words match"
        : "Possible topic mismatch",
      level: ratio >= 0.4 ? "ok" : "review",
      claim: "Advertisement topic",
      evidence: matchedWords.length
        ? "Matching words: " + matchedWords.join(", ")
        : "",
      suggestion:
        "Check whether the landing page offers the same product and fulfills the ad's main promise."
    });
  }

  // Warn about ad promises that the simple rules cannot evaluate.
  if (findings.length === 0) {
    findings.push({
      status: "Needs manual review",
      level: "review",
      claim: "No specific rule matched",
      evidence: "",
      suggestion:
        "Review the ad and page manually. This prototype cannot understand every advertising claim."
    });
  }

  const reviewCount = findings.filter(
    item => item.level === "review"
  ).length;

  const score = Math.round(
    100 * (findings.length - reviewCount * 0.5) / findings.length
  );

  latestReport = {
    project: "Message Match Auditor",
    url: urlInput.value.trim(),
    advertisement: {
      headline,
      description,
      callToAction: cta
    },
    landingPageText: pageText,
    score,
    findings,
    limitation:
      "Rule-based prototype. The score is not a verified accuracy measurement."
  };

  displayResults(score, findings);
}

function displayResults(score, findings) {
  scoreOutput.textContent = "Preliminary score: " + score + "/100";

  summaryOutput.textContent =
    "This is a rule-based estimate. Review the evidence before deciding whether a real mismatch exists.";

  findingsOutput.replaceChildren();

  findings.forEach(finding => {
    const card = document.createElement("article");
    card.className = "finding";

    const status = document.createElement("p");
    status.className = "status " + finding.level;
    status.textContent = finding.status;

    const title = document.createElement("h3");
    title.textContent = finding.claim;

    const evidenceTitle = document.createElement("strong");
    evidenceTitle.textContent = "Evidence from supplied page text:";

    const quote = document.createElement("blockquote");
    quote.textContent = finding.evidence ||
      "No matching evidence quote was identified.";

    const suggestion = document.createElement("p");
    suggestion.textContent = "Next step: " + finding.suggestion;

    card.append(status, title, evidenceTitle, quote, suggestion);
    findingsOutput.appendChild(card);
  });

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth" });
}

function clearForm() {
  headlineInput.value = "";
  descriptionInput.value = "";
  ctaInput.value = "";
  urlInput.value = "";
  pageTextInput.value = "";

  results.hidden = true;
  latestReport = null;
}

function downloadReport() {
  if (!latestReport) {
    alert("Run an audit before downloading the report.");
    return;
  }

  const blob = new Blob(
    [JSON.stringify(latestReport, null, 2)],
    { type: "application/json" }
  );

  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = downloadUrl;
  link.download = "message-match-report.json";
  link.click();

  URL.revokeObjectURL(downloadUrl);
}

document.getElementById("exampleBtn").addEventListener("click", loadExample);
document.getElementById("auditBtn").addEventListener("click", auditMessage);
document.getElementById("clearBtn").addEventListener("click", clearForm);
document.getElementById("downloadBtn").addEventListener("click", downloadReport);
