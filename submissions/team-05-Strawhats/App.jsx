
import { useState } from "react";
import "./App.css";

const examples = {
  headline: "Get 30% Off Your First Order",
  description: "Shop today and save 30% on your first purchase.",
  
landing:
  "Get 30% off your first order. Shop today and save 30% on your first purchase. New customers can enjoy free shipping on eligible orders. Browse our products and find something you love.",

};

function App() {
  const [headline, setHeadline] = useState("");
  const [description, setDescription] = useState("");
  const [landing, setLanding] = useState("");
  const [result, setResult] = useState(null);

  function loadExample() {
    setHeadline(examples.headline);
    setDescription(examples.description);
    setLanding(examples.landing);
    setResult(null);
  }

  
  async function analyze() {
    if (!headline.trim() || !landing.trim()) {
      alert("Please enter an ad headline and landing-page text.");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ad_text: `${headline}\n${description}`.trim(),
          landing_page_text: landing,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }

      const data = await response.json();

      
const issues = (data.findings ?? [])
  .filter((finding) => finding.status !== "supported")
  .map((finding) => ({
    severity: finding.severity ?? "Medium",
    title: finding.claim ?? "Claim to review",
    evidence: finding.evidence_quote ?? "",
    detail:
      finding.explanation ??
      "Review this claim against the landing-page content.",
    
fix:
  finding.recommended_fix ??
  (finding.status === "contradicted"
    ? "Review the conflicting claim and correct the ad or landing-page content."
    : finding.status === "missing_support"
    ? "Add clear evidence for this advertised claim to the landing page."
    : "Verify this claim manually before making a decision."),

  }));


      setResult({
        score: data.score ?? null,
        issues,
        note:
          data.score_status === "unavailable"
            ? "A match score is unavailable because the destination page could not be assessed."
            : "Backend analysis completed. Verify findings against the full landing page.",
      });
    } catch (error) {
      console.error("Analysis failed:", error);
      alert(
        `Could not analyze the page: ${error.message}\n\nCheck that the backend is running and allows requests from localhost:5173.`
      );
    }
  }


  const issueCount = result?.issues.length ?? 0;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">M</div>
          <div>
            <h2>MatchProof</h2>
            <span>AI AUDITOR</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active">▦ &nbsp; Dashboard</div>
        <div className="nav-item">⌕ &nbsp; Message Auditor</div>
        <div className="nav-item">▤ &nbsp; Reports</div>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          Prototype workspace
          <p>Ad message consistency checker</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace / </span>
            <strong>Message Auditor</strong>
          </div>
          <div className="profile">
            <div className="avatar">MP</div>
            <span>Demo workspace</span>
          </div>
        </header>

        <section className="page-heading">
          <div>
            <div className="eyebrow">CAMPAIGN INTELLIGENCE</div>
            <h1>Ad Message Match Auditor</h1>
            <p>
              Check whether your landing page supports the promises made
              in your advertisement.
            </p>
          </div>
          <button className="secondary-button" onClick={loadExample}>
            Load example
          </button>
        </section>

        <div className="workflow">
          <div className="step active-step"><span>1</span> Add content</div>
          <div className="step-line" />
          <div className="step"><span>2</span> Analyze match</div>
          <div className="step-line" />
          <div className="step"><span>3</span> Review findings</div>
        </div>

        <section className="input-grid">
          <div className="panel">
            <div className="panel-heading">
              <div className="panel-icon purple">↗</div>
              <div>
                <h3>Advertisement</h3>
                <p>What are you promising your audience?</p>
              </div>
              <span className="required">REQUIRED</span>
            </div>

            <label htmlFor="headline">Ad headline *</label>
            <input
              id="headline"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              placeholder="e.g. Get 30% off your first order"
            />

            <label htmlFor="description">Ad description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter the supporting ad copy..."
              rows={4}
            />
            <div className="field-hint">
              Include important offers, benefits and claims.
            </div>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div className="panel-icon blue">▤</div>
              <div>
                <h3>Landing page</h3>
                <p>Paste the supplied page snapshot text.</p>
              </div>
              <span className="required">REQUIRED</span>
            </div>

            <label htmlFor="landing">Landing-page content *</label>
            <textarea
              id="landing"
              className="landing-input"
              value={landing}
              onChange={(e) => setLanding(e.target.value)}
              placeholder="Paste the landing-page text here..."
              rows={8}
            />
            <div className="field-hint">
              Use the supplied offline snapshot or extracted page text.
            </div>
          </div>
        </section>

        <div className="analyze-row">
          <div className="privacy-note">
            <span>ⓘ</span> Analyze the content provided for this demo.
          </div>
          <button className="analyze-button" onClick={analyze}>
            ✦ &nbsp; Analyze message match <span>→</span>
          </button>
        </div>

        {result && (
          <section className="results">
            <div className="results-heading">
              <div>
                <div className="eyebrow">ANALYSIS REPORT</div>
                <h2>Message match results</h2>
              </div>
              <span className="demo-badge">Backend Analysis</span>
            </div>

            <div className="metrics">
              <div className="metric-card">
                <span>Match indicator</span>
                <strong>{result.score}<small>/100</small></strong>
                <p>Heuristic message-match score</p>
              </div>
              <div className="metric-card">
                <span>Potential issues</span>
                <strong>{issueCount}</strong>
                <p>Claims needing review</p>
              </div>
              <div className="metric-card">
                <span>Review status</span>
                <strong className="review-status">
                  {issueCount ? "Review" : "Check"}
                </strong>
                <p>Human verification recommended</p>
              </div>
            </div>

            <div className="panel findings-panel">
              <h3>Findings & recommendations</h3>
              {result.issues.length === 0 ? (
                <div className="empty-result">
                  <div className="success-icon">✓</div>
                  <div>
                    <strong>No configured rule was triggered</strong>
                    <p>
                      This does not prove every ad claim is supported.
                      Review all promises against the full landing page.
                    </p>
                  </div>
                </div>
              ) : (
                result.issues.map((issue, index) => (
                  <article className="finding" key={index}>
                    <div className="finding-top">
                      <span className={`severity ${issue.severity.toLowerCase()}`}>
                        {issue.severity}
                      </span>
                      <strong>{issue.title}</strong>
                    </div>
                    <p className="evidence">{issue.evidence}</p>
                    <p>{issue.detail}</p>
                    <div className="recommendation">
                      <strong>Suggested fix</strong>
                      <p>{issue.fix}</p>
                    </div>
                  </article>
                ))
              )}
              <p className="disclaimer">{result.note}</p>
            </div>
          </section>
        )}

        <footer>
          <span>MatchProof AI · Hackathon prototype</span>
          <span>Evidence-led message consistency</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
