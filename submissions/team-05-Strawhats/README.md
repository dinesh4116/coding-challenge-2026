# MatchProof AI — Ad-to-Landing-Page Message Match Auditor

**Verify advertising promises against landing-page evidence.**

MatchProof AI is a hackathon MVP that compares advertising claims with supplied landing-page text. It produces a heuristic message-match score, claim-level findings, explanations, and recommended fixes.

## Features

- Enter advertisement text and landing-page text.
- Analyze message match using the FastAPI backend.
- View a heuristic score and claim-level findings.
- Review evidence quotes, explanations, and recommended fixes.
- Test matching and mismatching examples.
- Handle recorded HTTP 404 responses without assigning a misleading score.

## Technology Stack

- **Frontend:** React, Vite, JavaScript, CSS
- **Backend:** Python, FastAPI
- **API server:** Uvicorn
- **Version control:** Git and GitHub

## Project Architecture

1. The user enters advertisement and landing-page text.
2. The frontend sends the input to the backend's `/analyze` endpoint.
3. The backend analyzes the supplied content.
4. The frontend displays the score, findings, explanations, and recommendations.

## Run Locally on Windows

### 1. Start the backend

Open a VS Code terminal and run:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal running.

- API: `http://127.0.0.1:8000`
- Swagger documentation: `http://127.0.0.1:8000/docs`

### 2. Start the frontend

Open a second terminal at the project root:

```powershell
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173/`.

Keep both terminals running.

## API

**Endpoint:** `POST http://127.0.0.1:8000/analyze`

Example request:

```json
{
  "ad_text": "Get 30% off your first order.",
  "landing_page_text": "Get 30% off your first order. Shop today and save."
}
```

The backend returns analysis fields such as `score`, `score_type`, `summary`, `counts`, `findings`, and `limitations`.

## Demo Workflow

1. Click **Load example**.
2. Click **Analyze message match**.
3. Review the score and findings.
4. Change the landing-page text so that it no longer supports the advertised offer.
5. Analyze again and compare the results.

## Responsible AI and Limitations

- The score is heuristic, not a validated probability or guarantee of truth.
- Missing supporting evidence does not prove that an advertising claim is false.
- Keyword overlap alone does not prove semantic support.
- Human review is recommended before acting on findings.
- The application analyzes supplied content; do not assume it automatically fetches arbitrary live URLs.
- A recorded HTTP 404 response indicates an inaccessible-page scenario, not proof that the advertising claim is false.

## Team and Repository

Developed collaboratively by a three-member hackathon team.

GitHub: https://github.com/Hariharan-VS-18/hackathon-psg

## Conclusion

MatchProof AI helps reviewers identify potential gaps between advertising promises and landing-page evidence. Its core principle is simple: **report what the available evidence supports, and never invent proof.**
