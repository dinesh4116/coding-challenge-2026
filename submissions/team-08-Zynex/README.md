# AdMatch AI 🚀

### Find the Gap Between Your Ad and Your Landing Page

AdMatch AI is a web application that helps identify mismatches between an advertisement and its landing page. It compares ad copy with the available landing-page text, highlights claims that are missing or only partially supported, and suggests ways to make the messaging more consistent.

The idea is simple: when an ad promises something, the landing page should help visitors understand that promise. AdMatch AI makes it easier to spot when that connection is unclear.

This project is being developed with **React, Vite, Python, and FastAPI**, using a deterministic, evidence-based analysis engine.

> **Current status:** MVP — actively being developed
> **Analysis approach:** Rule-based text matching, not an LLM-based evaluator.

---

## 💡 Why AdMatch AI?

Imagine an advertisement says, *"Learn practical AI skills through hands-on projects."* However, the landing page only mentions learning AI without explaining the projects.

A visitor might not find enough information to understand the original promise.

AdMatch AI compares the two pieces of content and highlights where the wording matches, where support is incomplete, and where information appears to be missing.

The goal is to help marketers and content creators review their messaging before publishing a campaign.

## ✨ What Can It Do?

### 📝 Analyze advertisement copy

Provide the main details of an advertising campaign:

* Headline and body copy
* Call-to-action (CTA)
* Landing-page URL
* Target audience
* Campaign goal
* Industry
* Landing-page text

### 🔍 Compare ad claims with landing-page content

The current analysis engine checks the supplied landing-page text for wording related to the advertisement's claims. It identifies claims that are not found and claims that have only partial textual support.

### 📊 Generate consistency scores

Each audit includes an overall score and three analysis dimensions:

* **Message consistency** — checks wording overlap between the advertisement and landing-page content.
* **Promise fulfillment** — evaluates how the available text supports the claims being checked.
* **CTA alignment** — checks the wording alignment between the call to action and the page content.

These scores are indicators produced by the current rules. They are not conversion-rate predictions or proof that an advertising claim is true.

### 🧾 Show findings and evidence

Instead of returning only a score, the audit report can include the claim being checked, its evidence classification, supporting text when available, and an explanation of the result.

### 💡 Suggest improvements

Each finding can include a suggested fix, an explanation, a priority label, and replacement wording to help guide the next revision.

### 📚 Keep track of audits

The application includes a dashboard, audit history, individual audit reports, and settings. The backend provides endpoints for creating, retrieving, and deleting audits.

Audit persistence depends on the active backend storage implementation.

### 🧪 Switch between demo and live modes

**Demo mode** uses browser-side sample behavior and keyword matching. It stores demo data in the browser and does not fetch websites in the documented demo workflow.

**Live mode** sends audit requests to the configured FastAPI backend and uses the response returned by that service.

The two modes follow different execution paths, so demo results should not be confused with live backend results.

---

## 🖥️ Application Pages

| Page          | What it does                                             |
| ------------- | -------------------------------------------------------- |
| Dashboard     | Shows an overview of message-match audits                |
| New Audit     | Collects ad details and landing-page content             |
| Audit History | Lets users revisit previous audits                       |
| Audit Report  | Displays scores, findings, evidence, and recommendations |
| Settings      | Provides access to application mode and backend settings |

---

## 🛠️ Built With

| Technology     | Role                                          |
| -------------- | --------------------------------------------- |
| React          | Frontend user interface                       |
| Vite           | Frontend development and build tooling        |
| React Router   | Page navigation                               |
| Lucide React   | Interface icons                               |
| Python         | Backend implementation                        |
| FastAPI        | REST API                                      |
| Uvicorn        | Local API server                              |
| Pydantic       | Request validation                            |
| CSV and HTML   | Advertisement data and landing-page snapshots |
| Git and GitHub | Version control and project hosting           |

---

## 🏗️ How It Works

```text
User enters ad details and landing-page text
                    |
                    v
             React Frontend
                    |
                    v
           FastAPI Backend
                    |
                    v
       Deterministic Analysis Engine
                    |
          +---------+---------+
          |         |         |
          v         v         v
       Scoring   Findings   Evidence
          |         |         |
          +---------+---------+
                    |
                    v
          Recommendations
                    |
                    v
           Audit Report UI
```

The frontend collects the campaign details and sends them to the backend in live mode. The backend processes the request and returns a structured audit result that the application can display.

The current engine relies on deterministic text-matching and evidence-classification rules rather than a generative AI model.

---

## 📂 Dataset

The project uses advertisement records and landing-page snapshots for testing and development.

The expected dataset structure is:

```text
backend/
└── data/
    └── dataset/
        ├── ads.csv
        ├── README.md
        └── landing_page_snapshots/
            ├── ...
            └── ...
```

* **`ads.csv`** contains advertisement records and associated metadata.
* **`landing_page_snapshots/`** contains HTML snapshots intended for local testing.
* **`README.md`** can document the dataset structure and record mapping.

The dataset supplied during development was described as containing 60 HTML snapshots. The actual number of usable files and their mapping to advertisement records should be verified in the repository.

Some sample URLs may use the reserved `.example` domain. These are illustrative addresses, so their corresponding local snapshots should be used for testing rather than expecting them to behave like public websites.

---

## ⚙️ Getting Started

Follow these steps to run AdMatch AI locally.

### Prerequisites

Install:

* Python 3.11 or a version supported by the project
* Node.js and npm
* Git
* Visual Studio Code (recommended)

### 1. Clone the repository

Replace the placeholder with your actual GitHub repository URL.

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd admatch-ai
```

### 2. Start the backend

Open a terminal in the project directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it in **Windows PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Start FastAPI:

```bash
python -m uvicorn app.main:app --reload
```

If your backend uses a different entry point, adjust the command to match the actual project structure.

### 3. Check the backend

Open these URLs in your browser:

* [Swagger API documentation](http://127.0.0.1:8000/docs)
* [Backend root](http://127.0.0.1:8000/)
* [Dataset status](http://127.0.0.1:8000/api/dataset)

Swagger lets you inspect the available endpoints and send test requests.

### 4. Start the frontend

Open a **second terminal** and navigate to the frontend:

```bash
cd frontend
```

Install the packages:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite. It is commonly:

http://localhost:5173

Keep both servers running while testing the live application.

---

## 🔌 Backend API

The following endpoints are available in the current Swagger documentation.

Base URL:

```text
http://127.0.0.1:8000
```

| Method   | Endpoint                 | Purpose                   |
| -------- | ------------------------ | ------------------------- |
| `POST`   | `/api/audits`            | Create a new audit        |
| `GET`    | `/api/audits/{audit_id}` | Retrieve a specific audit |
| `DELETE` | `/api/audits/{audit_id}` | Delete one audit          |
| `DELETE` | `/api/audits`            | Delete all audits         |
| `GET`    | `/`                      | Access the root endpoint  |
| `GET`    | `/api/dataset`           | Check dataset status      |

### Create an audit

**Request:** `POST /api/audits`

Example JSON body:

```json
{
  "headline": "Upgrade Your Skills with AI",
  "body": "Learn practical AI skills through hands-on projects.",
  "cta": "Start Learning Today",
  "url": "https://example.com/ai-course",
  "audience": "College students",
  "goal": "Increase sign-ups",
  "industry": "Education",
  "landingPageText": "Learn AI through practical projects and build your portfolio."
}
```

A successful request returns a structured audit record. Depending on the current implementation, the response includes the audit ID, creation time, status, submitted input, landing-page information, scores, findings, evidence, recommendations, and analysis metadata.

### Retrieve an audit

**Request:** `GET /api/audits/{audit_id}`

Use the ID returned by the create-audit endpoint. Do not substitute a finding ID or recommendation ID for the audit ID.

For example:

```text
GET /api/audits/fbe198bc-07f1-4204-9cff-171689876b7e
```

The ID above is an example from a development test. Your request should use the ID returned by your own audit creation.

A `404 Audit not found` response means the requested audit could not be located in the backend's current store.

### Delete an audit

**Request:** `DELETE /api/audits/{audit_id}`

Deletes a specific audit, if it exists.

### Delete all audits

**Request:** `DELETE /api/audits`

This operation is destructive. Use it only when you intend to clear the stored audits.

### Check the dataset

**Request:** `GET /api/dataset`

Use this endpoint to inspect the dataset status returned by the backend.

---

## 📊 Example Audit

During development, a sample request returned the following result:

| Metric                     | Example value |
| -------------------------- | ------------: |
| Overall score              |            18 |
| Message consistency        |            25 |
| Promise fulfillment        |            18 |
| CTA alignment              |             0 |
| Claims assessed            |             3 |
| Missing claims             |             2 |
| Partially supported claims |             1 |

These numbers are from a single test run, not a benchmark.

In that example, two claims were not found in the supplied landing-page text, while one had partial wording overlap. This illustrates how the current engine reports potential messaging gaps.

A missing claim does not automatically mean the advertisement is false. The information may simply be absent from the text provided for analysis.

---

## 🧪 Testing the Application

To check the basic end-to-end workflow:

1. Start the backend and frontend.
2. Open the Swagger documentation.
3. Submit a sample request through `POST /api/audits`.
4. Confirm that the API returns a successful response.
5. Copy the returned audit ID.
6. Use `GET /api/audits/{audit_id}` to retrieve the record.
7. Inspect the score, dimensions, findings, evidence, and recommendations.
8. Open the frontend and verify that the audit result is displayed correctly in live mode.
9. Test the history and report pages with available audit records.
10. Test delete operations carefully, especially the endpoint that removes all audits.

For dataset testing, make sure the corresponding local HTML snapshots exist.

---

## ⚠️ Current Limitations

AdMatch AI is an MVP, and there are a few important limitations to keep in mind:

* **Rule-based analysis:** The current engine does not use an LLM to interpret claims.
* **Limited semantic understanding:** Similar wording does not necessarily mean two statements have the same meaning.
* **Incomplete evidence:** A claim not found in the supplied text may still be supported elsewhere on the actual website.
* **No conversion prediction:** The score does not predict clicks, sales, or conversion rates.
* **No legal verification:** The application does not establish whether an advertisement complies with advertising laws or regulations.
* **Website extraction:** Website fetching and extraction of dynamically rendered or protected content are not guaranteed.
* **Dataset coverage:** The quality of results depends on the supplied text and available dataset records.
* **Storage behavior:** Audit persistence depends on the backend's current storage implementation.
* **Production readiness:** Security, authentication, monitoring, deployment, and broader testing require further work before production use.

---

## 🛣️ What's Next?

Some improvements I would like to explore as the project develops:

* [ ] Add semantic claim comparison using an LLM.
* [ ] Improve website fetching and HTML content extraction.
* [ ] Show exactly where supporting evidence appears on a landing page.
* [ ] Expand the dataset and evaluate the engine against more examples.
* [ ] Improve scoring and severity classification.
* [ ] Make audit history search and filtering more useful.
* [ ] Add automated tests for the API and frontend.
* [ ] Introduce authentication and access control.
* [ ] Improve error handling, logging, and monitoring.
* [ ] Prepare deployment workflows and CI checks.

These are planned improvements, not features currently claimed as complete.

---

## 🔐 Security Notes

* Keep API keys and other secrets out of source control.
* Exclude virtual environments and unnecessary generated files from Git.
* Validate user-submitted content before processing it.
* Treat externally sourced website content as untrusted.
* Be careful when testing endpoints that delete data.
* Review audit findings manually before making advertising decisions.

---

## 🤝 Contributions

Suggestions, bug reports, and contributions are welcome.

1. Fork the repository.
2. Create a branch for your changes.
3. Make your changes and test them.
4. Open a pull request explaining what changed and why.

Please include relevant reproduction steps when reporting a bug.

---

## 📄 License

A license has not yet been specified. Add a `LICENSE` file and update this section once the project's licensing terms have been decided.

---

## 👨‍💻 About the Project

AdMatch AI is a project exploring how evidence-based text analysis can help people review the consistency between advertising copy and landing-page content.

It is being built with a React frontend and FastAPI backend, with a focus on clear audit results, traceable findings, and practical suggestions for improving campaign messaging.

If you find the project interesting, feel free to explore the code, try the application, or share feedback.

⭐ **Thanks for checking out AdMatch AI!**
