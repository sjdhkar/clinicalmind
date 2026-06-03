# ClinicalMind — Deployment Guide

## Live Demo URLs (after following steps below)

| Service | URL |
|---------|-----|
| Angular frontend | `https://sjdhkar.github.io/clinicalmind/` |
| Demo API | `https://clinicalmind-demo-api.onrender.com` |

---

## Step 1 — Deploy the demo API to Render (10 minutes, free)

1. Go to **https://render.com** → sign up with GitHub
2. Click **New → Web Service**
3. Connect repo: `sjdhkar/clinicalmind`
4. Configure:
   - **Root directory:** `services/demo-api`
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free
5. Add environment variables (under **Environment** tab):
   ```
   AZURE_OPENAI_ENDPOINT  = https://your-resource.openai.azure.com/
   AZURE_OPENAI_KEY       = your_key_here
   AZURE_OPENAI_DEPLOYMENT = gpt-4o-mini
   ```
6. Click **Deploy** — takes ~2 minutes
7. Note your URL: `https://clinicalmind-demo-api.onrender.com`

> **No Azure OpenAI key?** The demo API still works — it returns
> pre-written realistic clinical responses. Add the key later for
> real GPT-4o-mini responses.

---

## Step 2 — Update the API URL in the Angular app (2 minutes)

Edit `apps/web/src/environments/environment.prod.ts`:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://clinicalmind-demo-api.onrender.com',  // your Render URL
};
```

Commit and push:
```bash
git add apps/web/src/environments/environment.prod.ts
git commit -m "config: set production API URL"
git push origin main
```

---

## Step 3 — Enable GitHub Pages (3 minutes)

1. Go to `github.com/sjdhkar/clinicalmind` → **Settings** → **Pages**
2. Under **Source**, select: **GitHub Actions**
3. The `deploy-pages.yml` workflow will trigger automatically on the next push
4. After ~2 minutes: **https://sjdhkar.github.io/clinicalmind/**

> The workflow is already in `.github/workflows/deploy-pages.yml`
> — no additional setup needed.

---

## Step 4 — Verify everything works

1. Open `https://sjdhkar.github.io/clinicalmind/`
2. You should see the ward dashboard with 4 patients
3. Click **J. Smith** (high risk, NEWS2 = 7)
4. Type: *"What is the patient's deterioration risk?"*
5. Watch the AI response stream token by token with citation badges

---

## Demo script (for interviews / recruiter calls)

**Opening (30 seconds):**
> "This is ClinicalMind — an AI platform that monitors clinical observation streams
> and surfaces real-time deterioration risk. Let me show you a live ward dashboard."

**Show the ward (30 seconds):**
- Point out the colour-coded NEWS2 risk scores
- Point out S. Jones in red (critical, NEWS2 = 9) vs M. Patel in green (low, NEWS2 = 2)

**AI chat demo (60 seconds):**
- Click J. Smith → type "What is this patient's NEWS2 score and what action is needed?"
- Watch tokens stream in with citation badges
- Click a citation badge to show source evidence
- Point out model name, agents used in the metadata footer

**Eval dashboard (30 seconds):**
- Click **Eval Dashboard** in the nav
- Show RAGAS metrics (faithfulness 0.91, hallucination 2.8%)
- "This is the key differentiator — I have a quantified evaluation pipeline running in CI"

**Close (15 seconds):**
> "Full source at github.com/sjdhkar/clinicalmind — 131 files,
> LangGraph agents, hybrid RAG, .NET 10 gateway, RAGAS eval in CI."

---

## Local demo (Docker Compose)

To run the full stack locally:
```bash
cp .env.example .env
# Add your Azure OpenAI key to .env

docker compose up -d
cd packages/clinical-eval && python seed_demo_data.py

open http://localhost:4200
```

---

## Troubleshooting

**GitHub Pages shows blank page:**
- Check that `base-href: /clinicalmind/` is set in the deploy workflow
- The `404.html` file handles Angular routing — check it was copied

**Render API cold start (30 second delay on first request):**
- Free tier spins down after inactivity — first request takes ~30s
- Warn interviewers: "free tier, first request warms up"
- Upgrade to Render Starter ($7/mo) for zero cold start

**CORS errors in browser console:**
- The demo API allows all origins (`*`) — should not get CORS errors
- If deploying a custom domain, update the `allow_origins` list in `main.py`
