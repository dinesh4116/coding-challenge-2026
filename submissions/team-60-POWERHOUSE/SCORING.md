# Message Match Scoring Specification

This document details the exact mathematical formula, claim weighting, penalties, and threshold boundaries implemented by the PS-03 Message Match Auditor.

---

## 1. Mathematical Scoring Formula

$$\text{Base Score} = \left( \frac{\max\left(0, \sum_{i=1}^{N} \text{Status Value}_i \times \text{Weight}_i\right)}{\sum_{i=1}^{N} \text{Max Possible Points}_i} \right) \times 100$$

$$\text{Raw Score} = \text{Base Score} - \text{Total Penalties}$$

$$\text{Final Score} = \begin{cases} 
\min(40.0, \max(0.0, \text{Raw Score})) & \text{if any claim is Contradicted (Hard Cap 40)} \\
\max(0.0, \min(100.0, \text{Raw Score})) & \text{otherwise}
\end{cases}$$

> **Rule 4: Incomplete Analysis Handling**
> When page extraction fails, network times out, or the page contains insufficient content (e.g. empty JavaScript shells), the score is strictly returned as `null` (`None`). It is displayed in the UI as **"Score unavailable"**, explicitly distinguished from a computed score of `0.0`.

---

## 2. Status Base Values

Each claim status maps to a discrete value reflecting factual alignment:

| Match Status | Status Base Value | Meaning |
|---|---|---|
| **Supported** | `1.0` (100%) | Exact or near-exact match confirmed with verified substring quote & confirmed figures. |
| **Partial Match** | `0.5` (50%) | Core topic present, but secondary metrics or qualifying details diverge. |
| **Uncertain** | `0.25` (25%) | Vague thematic relation (40%–60% similarity); insufficient evidence to confirm or deny. |
| **Not Found** | `0.0` (0%) | **Absence of evidence**. Topic is omitted on the page. (Never marked as Contradicted). |
| **Contradicted** | `-0.5` (-50%) | Page explicitly asserts conflicting terms (e.g. ad promises "Free trial", page states "Paid only"). |

---

## 3. Claim Weighting (Material vs. Standard)

Claims are weighted based on their direct influence on ad conversion and visitor trust:

- **Material Claims (`Weight = 2.0x`)**:
  - `Offer / Pricing` claims (e.g., "$49 Exam", "50% Off", "Free Trial", "No Credit Card Required", "Money-Back Guarantee")
  - `Headline` core assertions (the primary reason the visitor clicked the ad)
- **Standard Claims (`Weight = 1.0x`)**:
  - `Feature / Benefit` claims
  - `Social Proof / Trust` claims
  - `Audience / Scope` claims

$$\text{Max Possible Points}_i = 1.0 \times \text{Weight}_i$$

---

## 4. Penalties & Hard Cap 40

1. **Contradiction Penalty**: Each contradicted claim incurs an additional deduction of `-15.0 points`.
2. **CTA Action Friction Penalty**: If the ad promises an immediate self-serve action (e.g. "Start Free Trial Now") but the landing page demands a gated sales barrier (e.g. "Schedule an Enterprise Sales Demo"), an additional `-10.0 points` friction penalty is applied.
3. **Hard Cap 40**: If **any** claim is `Contradicted`, the final score is strictly capped at `40.0`, regardless of how many standard claims are supported. Factual deception destroys visitor trust.

---

## 5. Letter Grade Presentation Aid

Letter grades and radar charts are provided solely as **presentation aids derived from the numerical score**:

- **Grade A (90.0 – 100.0)**: *Excellent Message Match* — Complete continuity across headline, core offer, and primary CTA.
- **Grade B (80.0 – 89.9)**: *Good Match* — Clear continuity with minor phrasing or nuance differences.
- **Grade C (65.0 – 79.9)**: *Moderate Match* — Noticeable gaps in secondary promises or unconfirmed metrics.
- **Grade D (45.0 – 64.9)**: *Weak Match* — High bounce risk; material offers or CTAs are absent.
- **Grade F (< 45.0)**: *Critical Mismatch* — Contradictions detected or headline promise completely missing.
