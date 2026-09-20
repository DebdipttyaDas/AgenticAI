# HireFlow Cloud Deployment Guide

This guide provides end-to-end instructions for deploying the **HireFlow** AI Screening & Interview Intelligence application to **Vercel** (Serverless Python) and **Render** (Cloud Web Service / Docker).

---

## ⚡ Quick Architecture Overview

| Feature | Vercel | Render |
|---|---|---|
| **Deployment Model** | Serverless Functions (`@vercel/python`) | Long-running Web Service / Container |
| **Config File** | `vercel.json` | `render.yaml` / `Dockerfile` |
| **Entrypoint** | `api/index.py` | `hireflow.api.routes:app` |
| **Start Command** | Handled by Vercel ASGI runtime | `uvicorn hireflow.api.routes:app --host 0.0.0.0 --port $PORT` |
| **UI & API** | Unified React SPA + REST API | Unified React SPA + REST API |
| **Health Check** | `/health` / `/api/v1/health` | `/health` / `/api/v1/health` |

---

## 🚀 Option 1: Deploy to Vercel

Vercel deploys HireFlow as a serverless ASGI application using the `@vercel/python` builder defined in `vercel.json`.

### Method A: One-Click / GitHub Integration (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Add Vercel and Render deployment configurations"
   git push origin main
   ```

2. **Import Project into Vercel:**
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your Git repository (`AgenticAI`).
   - Vercel will automatically detect `vercel.json` and `requirements.txt`.
   - Leave **Framework Preset** as *Other*.

3. **Configure Environment Variables:**
   - In the **Environment Variables** section, optionally add:
     - `ANTHROPIC_API_KEY`: Your Anthropic API Key (e.g. `sk-ant-...`). *If omitted, HireFlow runs in deterministic heuristic matching mode.*
     - `HIREFLOW_PRIMARY_MODEL`: `claude-3-5-sonnet-20241022` (Optional)
     - `HIREFLOW_FAST_MODEL`: `claude-3-5-haiku-20241022` (Optional)

4. **Click Deploy:**
   - Vercel will build the serverless package and deploy.
   - Your live dashboard will be accessible at: `https://<your-project-name>.vercel.app/`

---

### Method B: Deploy Using the Vercel CLI

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy preview
vercel

# 4. Deploy to production
vercel --prod
```

---

## 🚀 Option 2: Deploy to Render

HireFlow is configured for Render via `render.yaml` (Infrastructure as Code) or standard Python / Docker web services.

### Method A: Render Blueprint Deployment (1-Click)

1. **Push your repository to GitHub / GitLab.**
2. Go to the [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** $\rightarrow$ **Blueprint**.
4. Connect your repository.
5. Render will detect `render.yaml` and configure:
   - **Service Type:** Web Service
   - **Runtime:** Python 3.11.9
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn hireflow.api.routes:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
6. Under **Environment Variables**, set `ANTHROPIC_API_KEY` (if using live LLM features).
7. Click **Apply**. Render will automatically provision and deploy your service.

---

### Method B: Manual Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ **New +** $\rightarrow$ **Web Service**.
2. Connect your repository.
3. Configure the following settings:
   - **Name:** `hireflow`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn hireflow.api.routes:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
4. In **Advanced $\rightarrow$ Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `ANTHROPIC_API_KEY`: `your_key_here` (Optional)
5. Click **Create Web Service**.

---

### Method C: Deploy via Docker on Render

Render also supports native Docker deployments using the included `Dockerfile`:

1. In Render, select **New +** $\rightarrow$ **Web Service**.
2. Connect your repository.
3. Choose **Docker** as the Environment runtime.
4. Render will automatically build the image from `Dockerfile` and start the server.

---

## 🧪 Local Testing Before Deployment

### 1. Test Server Locally
```bash
# Using uvicorn
uvicorn hireflow.api.routes:app --host 127.0.0.1 --port 8000 --reload
```
Open `http://127.0.0.1:8000` to verify the React dashboard and click **"Load Sample Dataset"**.

### 2. Test Docker Container Locally
```bash
# Build image
docker build -t hireflow:latest .

# Run container
docker run -p 8000:8000 -e ANTHROPIC_API_KEY="your-key" hireflow:latest
```
Check health: `curl http://localhost:8000/health`

### 3. Run Automated Tests
```bash
# Run pytest with dev dependencies
uv run --extra dev pytest tests/ -v
```

---

## 🔍 Health Checks & API Verification

Once deployed on either platform, verify the deployment:

- **Web Dashboard:** `https://<your-app-url>/`
- **Health Check:** `https://<your-app-url>/health`
- **API Docs (Swagger UI):** `https://<your-app-url>/docs`
- **Demo Dataset Ingestion:** `POST https://<your-app-url>/api/v1/demo/load`
- **Candidate Pool:** `GET https://<your-app-url>/api/v1/pool`
