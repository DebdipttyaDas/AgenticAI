# HireFlow: AI Candidate Screening & Interview Intelligence Agent

**HireFlow** is an enterprise-grade AI candidate screening, competency matching, and interview intelligence system built with **Python 3.11+**, **FastAPI**, **Pydantic v2**, and the **Anthropic Claude SDK**.

---

## 🚀 Key Capabilities & Modules

1. **Multi-Format Ingestion & Semantic Chunking (`hireflow/ingestion`)**
   - Ingests `.pdf`, `.docx`, `.txt`, and `.md` files for both job descriptions and resumes.
   - Preserves granular character offsets `(start_char, end_char)` and section headers (`summary`, `experience`, `education`, `skills`, `projects`).
   - Normalizes timelines, dates, and offers automated PII redaction for blind screening.

2. **Extraction & Anomaly Gap Detection (`hireflow/extraction`)**
   - Extracts structured candidate profiles (education, roles, durations, achievements, skills, and projects).
   - Detects **Career Gaps** (>6 months unaccounted for), **Missing Metrics** on major claims, and **Vague / Unsubstantiated Skills**.
   - Generates targeted validation probes for each detected anomaly.

3. **Multi-Tier Competency Matching & Weighted Scoring (`hireflow/matching`)**
   - Evaluates evidence against hard must-haves and nice-to-haves using a weighted multi-factor scoring formula.
   - Categorizes candidates into actionable tiers:
     - 🟢 **Tier 1 (Shortlist / Strong Match):** $\ge 85\%$ score, zero missing must-haves.
     - 🔵 **Tier 2 (Contender):** $70-84\%$ score, $\le 1$ minor must-have gap.
     - 🟡 **Tier 3 (Specialist / Skill-Gapped):** High domain match with core criteria gaps.
     - 🔴 **Tier 4 (Unmatched):** $< 70\%$ score or critical deficits.

4. **Interview Intelligence & Adaptive Probe Trees (`hireflow/intelligence`)**
   - Produces role-tailored technical questions anchored directly to resume claims.
   - Builds dynamic conditional follow-up trees (`if_vague`, `if_overclaimed`, `if_strong`, `if_shallow`).
   - Evaluates post-interview interviewer notes and calculates **Evaluation Coverage Ratio**.
   - Identifies **Blind Spots & Unanswered Areas** required for subsequent interview rounds.

5. **Natural Language Candidate Pool Query Engine (`hireflow/query`)**
   - Allows recruiters to search, rank, and compare candidates using natural language prompts.
   - Combines structured metadata filters (years of experience, match scores, tiers) with semantic matching.

6. **Audit Provenance & Citation Ledger (`hireflow/core/provenance.py`)**
   - Maintains an immutable audit record for every score, claim, and question.
   - Verifies quotes directly against source text chunks to ensure zero ungrounded hallucinations.

---

## 🛠️ Installation & Setup

```bash
# Clone repository
git clone <repo_url>
cd AgenticAI

# Install dependencies
pip install fastapi uvicorn anthropic pypdf python-docx pydantic rich pytest jinja2

# Set Anthropic API Key (Optional for Claude Live Mode; heuristic fallback included)
export ANTHROPIC_API_KEY="your-anthropic-key"
```

---

## 🖥️ CLI Usage Guide

### 1. Screen Resumes Against a Job Description
```bash
python -m hireflow.api.cli screen \
  --jd fixtures/jd_senior_distributed_systems.md \
  --resumes fixtures/resume_alex_chen.md fixtures/resume_maya_patel.md fixtures/resume_jordan_lee.md fixtures/resume_taylor_smith.md \
  --out output
```

### 2. View Tailored Interview Plan & Probe Trees
```bash
python -m hireflow.api.cli interview-plan \
  --candidate-report output/cand_001_report.json
```

### 3. Audit Post-Interview Notes for Coverage Blind Spots
```bash
python -m hireflow.api.cli evaluate-interview \
  --jd fixtures/jd_senior_distributed_systems.md \
  --candidate output/cand_002_report.json \
  --notes fixtures/interview_notes_maya_patel.md
```

### 4. Query Candidate Pool with Natural Language
```bash
python -m hireflow.api.cli query \
  --pool output \
  --prompt "Find candidates with experience in Go and distributed systems"
```

---

## 🌐 Full-Stack Web Application & REST API

Launch the unified Web Application and API server:
```bash
python -m hireflow.api.cli serve --host 127.0.0.1 --port 8000
```

Open your browser at **`http://127.0.0.1:8000`** to access the **HireFlow React + Tailwind CSS Web Dashboard**:
- **Interactive Leaderboard:** Filter candidates by Tier, minimum match score, and skills.
- **Scorecard Explorer:** Real-time competency breakdown matrices and gap anomaly flags.
- **Interview Guide Viewer:** Branching adaptive probe trees (`[if_vague]`, `[if_overclaimed]`).
- **Live Notes Coverage Auditor:** Paste interview notes and instantly compute requirement coverage ratios and Round 2 blind spots.
- **Natural Language Talent Console:** Run recruiter queries across the entire pool with direct evidence citations.
- **One-Click Demo Loader:** Instant test dataset ingestion.

### Key REST API Endpoints
- `GET /` — Interactive React Single-Page Application Dashboard.
- `GET /health` — Health check endpoint for uptime and cloud deployment monitoring.
- `POST /api/v1/demo/load` — One-click loader for sample dataset (4 candidates + JD).
- `GET /api/v1/pool` — Retrieve active candidate pool, leaderboard, and tier distribution.
- `POST /api/v1/screen` — Upload JD and multiple resumes for batch screening.
- `POST /api/v1/evaluate-interview-raw` — Audit raw text interview notes against requirements.
- `POST /api/v1/query` — Execute natural language queries over the candidate pool.
- `GET /api/v1/candidates/{candidate_id}/scorecard.html` — Interactive recruiter HTML scorecard.
- `GET /api/v1/candidates/{candidate_id}/provenance` — Full immutable audit provenance records.

---

## ☁️ Cloud Deployment (Vercel & Render)

HireFlow is configured for one-click and automated CI/CD deployments to both **Vercel** and **Render**.

### 1. Deploying to Vercel (Serverless Python)
- **Config:** `vercel.json` and `api/index.py`.
- Push to GitHub and connect repository to [Vercel](https://vercel.com/new).
- Set `ANTHROPIC_API_KEY` under Project Environment Variables (optional).
- Or deploy via CLI: `vercel --prod`.

### 2. Deploying to Render (Web Service / Blueprint)
- **Config:** `render.yaml` and `Dockerfile`.
- In [Render Dashboard](https://dashboard.render.com/), create a **Blueprint** or **Web Service**.
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn hireflow.api.routes:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

> 📘 For comprehensive step-by-step instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 🧪 Running Unit & Integration Tests

```bash
# Run test suite
uv run --extra dev pytest tests/ -v
# or standard pytest
pytest tests/ -v
```
