# Deploy: Vercel Frontend + Railway API/Worker + Neon Postgres

This is the recommended production architecture for this project.

## Architecture

- Frontend: Vercel (`frontend/`)
- Backend API: Railway service (`backend/`, web process)
- Ingestion Worker: Railway service (`backend/`, worker process)
- Database: Neon Postgres

## 1. Neon setup

1. Create Neon project/database.
2. Copy connection string:

```text
postgresql://<user>:<password>@<host>/<db>?sslmode=require
```

## 2. Railway services (from same repo)

Create two Railway services from this repo:

### A) `f1-backend-api`

- Root directory: `backend`
- Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

- Variables:
  - `DATABASE_URL=<NEON_URL>`
  - `CORS_ORIGINS=["https://<your-vercel-app>.vercel.app"]`
  - optional: `GROQ_API_KEY`, `GEMINI_API_KEY`, `TAVILY_API_KEY`, `DEEPSEEK_API_KEY`

### B) `f1-backend-worker`

- Root directory: `backend`
- Start command:

```bash
python -m services.live_ingest_worker
```

- Variables:
  - `DATABASE_URL=<NEON_URL>`
  - `LIVE_INGEST_INTERVAL_SECONDS=120`
  - `LIVE_INGEST_SEASON=2026` (or omit to auto-use current/latest)
  - optional AI keys if needed by downstream services

## 3. Seed initial data

Run once against API service:

```bash
curl -X POST "https://<railway-api-domain>/api/ingest/run/season/2026"
```

Optional historical seed:

```bash
curl -X POST "https://<railway-api-domain>/api/ingest/run/season/2025"
```

## 4. Deploy frontend on Vercel

Deploy `frontend/` and set:

- `NEXT_PUBLIC_API_URL=https://<railway-api-domain>`
- `NEXT_PUBLIC_ENABLE_CLIENT_INGEST_TRIGGER=false`

## 5. Validation checklist

```bash
curl "https://<railway-api-domain>/health"
curl "https://<railway-api-domain>/api/seasons"
curl "https://<railway-api-domain>/api/ingest/status"
curl "https://<railway-api-domain>/api/ingest/live/status"
```

Browser validation:

- Home page loads standings/events without CORS errors.
- Live page returns `/api/live/status` and session/timing/simulate data.
- Replay page loads metadata/frames/events.

## Notes

- Worker service is the source of truth for live ingestion continuity.
- Frontend-triggered ingestion is disabled by default to avoid duplicated ingest calls.
- If using Railway free/dev plans, expect possible sleep behavior depending on plan policy.
