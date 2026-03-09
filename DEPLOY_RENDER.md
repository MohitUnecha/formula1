# Deploy on Render (Free Tier, Non-Vercel, No-Compromise Baseline)

This deploy path uses Render Web Services for both backend and frontend.
It keeps your stack intact (FastAPI + Next.js) and avoids Vercel limits.

## 1. Prerequisites

- A GitHub repo containing this project.
- A free Render account.
- Required for production-quality persistence: Neon Postgres (free tier is fine).

## 2. Push this project to GitHub

From project root:

```bash
git init
git add .
git commit -m "Render deployment setup"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 3. Create services in Render using Blueprint

1. In Render dashboard, click `New` -> `Blueprint`.
2. Select your GitHub repo.
3. Render will detect `render.yaml` at project root and create:
   - `f1-backend` (Python web service)
   - `f1-frontend` (Node web service)

## 4. Set required environment variables

### Backend (`f1-backend`)

- `DATABASE_URL`
  - Use Neon Postgres URL (required for persistent production data)
- `CORS_ORIGINS`
  - Must be explicit JSON list, for example:
  - `["https://<your-frontend-service>.onrender.com"]`
- `GROQ_API_KEY` (optional)
- `GEMINI_API_KEY` (optional)
- `TAVILY_API_KEY` (optional)
- `DEEPSEEK_API_KEY` (optional)

### Frontend (`f1-frontend`)

- `NEXT_PUBLIC_API_URL` = `https://<your-backend-service>.onrender.com`

## 5. Redeploy frontend after API URL is set

After backend URL is known and set in frontend env vars, trigger manual redeploy for `f1-frontend`.

## 6. Seed initial data

Once backend is live, run:

```bash
curl -X POST "https://<your-backend-service>.onrender.com/api/ingest/run/season/2026"

# optional: seed one historical season for richer analytics
curl -X POST "https://<your-backend-service>.onrender.com/api/ingest/run/season/2025"
```

## 7. Turn on live ingest loop

```bash
curl -X POST "https://<your-backend-service>.onrender.com/api/ingest/live/start?season=2026&interval_seconds=120"
```

## 8. Verify

```bash
curl "https://<your-backend-service>.onrender.com/health"
curl "https://<your-backend-service>.onrender.com/api/seasons"
curl -H "Origin: https://<your-frontend-service>.onrender.com" -I "https://<your-backend-service>.onrender.com/api/seasons"
```

Open frontend URL:

- `https://<your-frontend-service>.onrender.com`

## Notes on free tier

- Free services may sleep when idle and wake on first request.
- Free services are acceptable for MVP, but may pause ingest loops while sleeping.
- This blueprint is optimized to preserve current product behavior on free infrastructure.

## Production Gate (Do Not Skip)

Before sharing the URL publicly, confirm all checks pass:

1. Backend health returns `200` and DB is `healthy`.
2. `/api/seasons` returns seeded seasons (not empty).
3. Browser calls from frontend domain do not fail CORS.
4. `/api/ingest/live/status` shows `running=true` after start call.
5. Frontend `Live` and `Replay` pages load data from backend URL (not localhost).
