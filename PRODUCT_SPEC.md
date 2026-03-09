# F1 Analytics Platform — Product Specification

**Version:** 2.0  
**Date:** 2026-03-03  
**Owner:** Product + Engineering  
**Status:** Live (implementation-aligned, current as of v2.0)

---

## 1) Product Overview

F1 Analytics is a full-stack platform for race insights, predictions, live race data, historical analysis, and replay tooling.

### Core Value
- Provide a single interface for current-season race intelligence and historical F1 analysis.
- Blend structured motorsport data (FastF1, Jolpica-F1, OpenF1) with AI-assisted prediction context.
- Keep the system resilient with graceful fallbacks when external APIs are unavailable.

---

## 2) Goals and Non-Goals

### Goals
- Default user flows to **2026 season** across backend + frontend.
- Expose a consolidated **`jolpica-f1`** API endpoint integrated with FastF1 context.
- Enhance predictions with **Tavily** (current season only) and **Gemini + Groq fallback**.
- Improve UX clarity (rename Live to **Live Data from Race**, upcoming GP highlight, data disclaimers).
- Ensure local-first developer workflow without Docker dependency.

### Non-Goals
- No redesign of the entire UI system.
- No change to core ML model architecture in this phase.
- No new database engine migration.

---

## 3) Users and Use Cases

### Primary Users
- F1 fans and analysts
- Data-savvy hobbyists
- Internal engineering/product team

### Key Use Cases
- View current season events and compare driver/constructor trends.
- Request AI-assisted race predictions with explainable context.
- Access historical race/sprint/standings data when live telemetry is limited.
- Analyze live or simulated race state by lap progression.

---

## 4) Functional Requirements

### 4.1 Season Defaults
- All major UI pages default to **2026**.
- Backend fallbacks that inferred 2025 now infer **2026**.

### 4.2 External Data Aggregation
- Add consolidated endpoint:
  - `GET /api/external/jolpica-f1/{season}`
  - `GET /api/external/jolpica-f1/{season}/{round}`
- Endpoint returns schedule, race results, sprint results, standings, and data availability metadata.

### 4.3 Prediction Intelligence
- Tavily integration for **current season events only**.
- Gemini integration as secondary LLM.
- Automatic fallback behavior:
  1. Try Gemini (rate-limited)
  2. On failure/rate-limit, fallback to Groq
- Response metadata should indicate AI source and Tavily enhancement status.

### 4.4 UX and Content
- Rename nav/labels from “Live” to **“Live Data” / “Live Data from Race”**.
- Homepage must show:
  - upcoming GP focus state (Australian GP as initial emphasis)
  - live data section entry point
  - graceful image fallback when assets are missing
- Show FastF1 limitations disclaimer for pre-2018 seasons.

### 4.5 Sprint Data Coverage
- Sprint ingestion logic must include 2026 season mappings (projected until official finalization).
- Historical and current-year sprint weekend processing should not hard-skip 2026.

### 4.6 Developer Experience
- Docker artifacts removed from repo-level workflow.
- Simple local startup path via Python venv + Next.js scripts.

---

## 5) Non-Functional Requirements

- **Reliability:** External API failures must not break prediction endpoints.
- **Performance:** Prediction responses should remain responsive under normal local development use.
- **Observability:** Log fallback reasons (Gemini disable/rate limits, external API failures).
- **Maintainability:** Keep modular API routers and service clients, minimal coupling.

---

## 6) System Architecture (Current)

### Backend (FastAPI)
- API routers in `backend/api/*`
- Services in `backend/services/*`
- Data via SQLAlchemy + SQLite (local)
- Integrations:
  - FastF1
  - Jolpica-F1
  - OpenF1
  - Tavily
  - Gemini
  - Groq

### Frontend (Next.js)
- App router pages in `frontend/app/*`
- Shared API client in `frontend/lib/api.ts`
- React Query-driven data fetching

---

## 7) API Contract Additions

### New Consolidated Routes
- `GET /api/external/jolpica-f1/{season}`
- `GET /api/external/jolpica-f1/{season}/{round}`

### Frontend Client Methods
- `getJolpicaF1SeasonData(season)`
- `getJolpicaF1RoundData(season, round)`

### Prediction Metadata Expectations
- `ai_source`: `gemini` or `groq`
- `tavily_enhanced`: boolean where applicable

---

## 8) Security and Configuration

### Required Environment Variables
- `GROQ_API_KEY`
- `TAVILY_API_KEY`
- `GEMINI_API_KEY`

### Operational Safeguards
- Gemini request throttling and auto-disable after repeated failures.
- Tavily use constrained to current-season prediction enrichment.
- Fallback paths prevent endpoint hard failures when AI provider is unavailable.

---

## 9) Rollout Plan (Phase-by-Phase)

## Phase 1 — Foundation and Environment
**Objective:** Ensure stable local runtime and dependencies.

**Steps**
1. Confirm active backend virtual environment.
2. Install/verify core dependencies and AI SDKs.
3. Validate backend startup (`/health`, `/`).

**Exit Criteria**
- Backend healthy and reachable on port 8000.
- Frontend reachable on port 3000.

---

## Phase 2 — Data and API Expansion
**Objective:** Add consolidated Jolpica-F1 data access.

**Steps**
1. Implement season and round-level `jolpica-f1` routes.
2. Add pre-2018 FastF1 data limitation disclaimers.
3. Validate payload structure for schedule/results/sprints/standings.

**Exit Criteria**
- Both new endpoints return 200 with expected keys.
- Pre-2018 response includes data disclaimer.

---

## Phase 3 — AI Prediction Enrichment
**Objective:** Improve prediction quality and resilience.

**Steps**
1. Add Tavily client with controlled usage policy.
2. Add Gemini client with rate limiting.
3. Integrate Gemini-first + Groq fallback logic in prediction flow.
4. Add response metadata (`ai_source`, `tavily_enhanced`).

**Exit Criteria**
- Predictions complete successfully even if Gemini fails.
- Current season prediction path can show Tavily enhancement.

---

## Phase 4 — UX Alignment and Season Standardization
**Objective:** Align product UI with 2026-first experience.

**Steps**
1. Set season defaults to 2026 in major pages.
2. Rename Live labels to Live Data from Race.
3. Add upcoming GP emphasis and image fallback logic.
4. Display FastF1 historical limitation disclaimer where relevant.

**Exit Criteria**
- No major UI flow defaults to 2025.
- Live navigation and page labels reflect new naming.

---

## Phase 5 — Sprint and Historical Integrity
**Objective:** Ensure sprint coverage includes current season assumptions.

**Steps**
1. Extend sprint mapping to include 2026 projected rounds.
2. Remove hard skip logic for 2026 sprint ingest.
3. Validate ingest scripts include season range through 2026.

**Exit Criteria**
- Sprint ingestion pipeline processes 2026 entries.
- Season list includes 2026 in API responses.

---

## Phase 6 — Delivery, Cleanup, and Audit
**Objective:** Finalize operations and remove obsolete workflow paths.

**Steps**
1. Remove Docker files from workflow.
2. Keep local startup scripts and documentation clean.
3. Run endpoint smoke tests and TypeScript problem checks.

**Exit Criteria**
- No Docker dependency required for local run.
- Core API + UI smoke tests pass.

---

## 10) Acceptance Criteria

- [ ] Backend starts cleanly with configured venv.
- [ ] Frontend starts and loads default 2026 views.
- [ ] `jolpica-f1` season + round routes return valid data.
- [ ] Pre-2018 disclaimer is visible in data response/UI context.
- [ ] Predictions complete with fallback behavior under provider failure.
- [ ] Tavily enrichment appears for current season predictions.
- [ ] Sprint ingestion supports 2026 mappings.
- [ ] No runtime TypeScript errors on modified frontend files.

---

## 11) Risks and Mitigations

- **Risk:** External AI provider rate limits  
  **Mitigation:** Auto-disable and fallback to Groq with logged reason.

- **Risk:** Early-season 2026 data incompleteness  
  **Mitigation:** Use projected sprint mapping with clear comments and update process.

- **Risk:** Frontend/backend environment mismatch  
  **Mitigation:** Pin requirements and enforce venv-based startup scripts.

---

## 12) Open Items (Next Iteration)

1. Move Gemini integration from deprecated SDK references to only latest package usage everywhere.
2. Add explicit UI indicator when AI feedback source changes (Gemini vs Groq).
3. Add automated integration tests for prediction fallback chain.
4. Add docs page for API key setup and troubleshooting.

---

## 13) Definition of Done

The release is done when all acceptance criteria pass and the product can be run locally end-to-end (frontend + backend), with 2026 defaults, enriched predictions, consolidated Jolpica-F1 access, and documented phase-based delivery steps.

---

## 14) Version 2.0 — Implemented Features (March 2026)

This section documents all features built and shipped in the v2.0 cycle.

### 14.1 Intro Animation System
- **Splash animation** on hard refresh only — `sessionStorage('f1_intro_played')` gate prevents replay on client navigation.
- **Three-tier audio unlock**: (1) immediate unmuted autoplay, (2) muted→unmute browser trick, (3) global `click`/`touchstart`/`keydown` listener for mobile Safari/Chrome.
- **"TAP ANYWHERE TO HEAR AUDIO"** hint displayed during lights phase when audio hasn't unlocked yet.
- **Anti-glitch rendering**: `will-change: opacity, transform, filter` and `transform: translateZ(0)` applied to all animated reveal elements.
- Component: `frontend/components/F1CarAnimation.tsx`

### 14.2 Constructor Lineage System
- `CONSTRUCTOR_LINEAGE` dict maps current team slugs to all historical predecessor constructor IDs.
- Example: `racing_bulls → [rb, alphatauri, toro_rosso]` — unlocks full 20-season history (2006–2025).
- Career/season stats query uses `Driver.constructor_id.in_(lineage_ids)` instead of single ID.
- New-entry teams (Audi, Cadillac, founded ≥ 2025) use `Event.season >= founded_year` filter — zero fake historical stats.
- Implemented in `backend/api/drivers.py` → `get_constructor_profile()`

### 14.3 2026 Constructor Profiles

**Racing Bulls (slug: `racing-bulls`)**
- Current drivers: Isack Hadjar (HAD), Jack Doohan (LIN fallback) / Oliver Bearman
- Full 20-season lineage from Toro Rosso
- Notable drivers: Vettel, Ricciardo, Sainz, Gasly, Albon, Tsunoda, Lawson, Kvyat, Alguersuari

**Audi F1 (slug: `audi`)**
- Debut season: 2026
- Current drivers: Nico Hülkenberg, Gabriel Bortoleto
- Zero historical seasons — correctly shown as new entry
- Name variants: `["Audi", "Audi F1 Team", "Audi Revolut"]` (Sauber explicitly excluded to prevent history bleed)
- Logo: local SVG at `/images/teams/audi.svg` (four rings, red)

**Cadillac F1 (slug: `cadillac`)**
- Debut season: 2026
- Current drivers: per 2026 team mapping
- Zero historical seasons — correctly shown as new entry
- Logo: local SVG at `/images/teams/cadillac.svg` (shield/crest with gold gradient)

### 14.4 Weather Integration in AI Predictions
- BOOST 7 (weather) now collects from both DB `Weather` model and OpenF1 `get_weather()`:
  - `air_temp`, `track_temp`, `humidity`, `wind_speed`, `rain_probability`
- `weather_detail_str` assembled as: `"Weather: Air 28.0C, Track 45.0C, Humidity 62.0%, Wind 8.0km/h, DRY"`
- Context assembly moved to **after** all boosts execute (fixed regression where context was assembled with empty variables).
- Weather context injected into:
  - Groq system prompt (`groq_client.py`)
  - Multi-AI consensus prompt (`multi_ai_client.py`)
  - Per-driver Groq analysis prompt (`predictions.py`)
  - Fallback `attach_groq_feedback` prompt
- Wet-specialist driver knowledge included (e.g., Verstappen, Alonso, Hamilton wet performance flags).

### 14.5 Notable Drivers Deduplication
- `current_driver_codes_set` computed from 2026 team mapping.
- Notable drivers query subtracts current drivers — no duplicate appearance across `current_drivers` and `notable_drivers` arrays.

### 14.6 Static Assets
- Created `frontend/public/images/teams/` directory.
- `audi.svg`: Four-ring SVG, stroke color `#990000`.
- `cadillac.svg`: Shield crest with gold gradient, `#B8962E` / `#F5D782`, inner quadrant design.
- Both served directly by Next.js from `/images/teams/...`.

---

## 15) Crofty — AI F1 Chatbot

**Added:** 2026-03-05  
**Status:** Live

### Overview
CROFTY is an AI-powered F1 chatbot embedded as a global floating panel across the entire platform. Named after Sky Sports F1 lead commentator David Croft, it delivers expert F1 knowledge in his iconic enthusiastic, larger-than-life style.

### Architecture

```
User → ChatbotPanel.tsx (floating UI)
     → POST /api/chat (FastAPI)
     → SQL DB context builder (race results, champions, driver stats)
     → Groq Chat Completions (llama-3.3-70b-versatile)
     → JSON response: { reply, suggest_predictions, prediction_context }
     → ChatbotPanel renders reply + optional Predictions CTA button
```

#### Backend: `backend/api/chat.py`
- **Endpoint:** `POST /api/chat`
- **Model:** `llama-3.3-70b-versatile` via Groq API
- **DB Context:** Dynamically queries SQLite for:
  - Race results by year (winners, top 5 per GP)
  - Driver all-time stats (wins, points)
  - Season champions
  - Available seasons in database
- **System prompt:** Full F1 historical knowledge 1950–2026, champions list, 2026 season context, prediction guidance, Crofty personality rules
- **Response format:** JSON `{ reply, suggest_predictions, prediction_context }` enforced via Groq JSON mode

#### Frontend: `frontend/components/ChatbotPanel.tsx`
- Floating red button (bottom-right) with pulse animation and unread badge
- Slide-up / fade-in panel (370px wide, 70vh max height)
- Conversation history (last 8 turns sent to backend)
- Suggestion chips on first open (quick-start questions)
- **Prediction redirect:** When `suggest_predictions: true`, a "Open Predictions Tool" button appears inline below the reply → navigates to `/predictions`
- Auto-scroll to newest message
- Keyboard shortcut: Enter to send, Shift+Enter for newline

### Personality Rules (Crofty)
- Uses David Croft catchphrases: "IT'S LIGHTS OUT AND AWAY WE GO!", "That's MEGA!", "Ohhh, that's a big one!"
- Enthusiastic, knowledgeable, warm British F1 commentator tone
- Checks live DB data first, then baked-in historical knowledge
- Never fabricates race results; says so honestly with Crofty flair if unknown
- For prediction questions: gives analysis then always suggests Predictions Tool

### Key Behaviours
| User question | Crofty behaviour |
|---|---|
| "Who won the 2000 Australian GP?" | Queries DB; if not found, uses historical knowledge → Michael Schumacher |
| "Who is the 2025 World Champion?" | Knows Lando Norris (McLaren) |
| "Who will win the next race?" | Gives analysis + sets `suggest_predictions: true` → CTA button |
| General F1 trivia | Enthusiastic encyclopedic answer |

---

## 16) Open Items (v3.0 Candidates)

1. **Racing Bulls 2026 driver confirmation** — Verify if Hadjar is Racing Bulls or Red Bull per official 2026 announcement; update `team_mapping.py` accordingly.
2. **Live weather for upcoming races** — OpenF1 weather only available for past sessions; integrate forecast API (e.g., OpenWeatherMap) for pre-race prediction enrichment.
3. **Audi/Cadillac actual logos** — Replace hand-drawn SVGs with official licensed assets when available.
4. **AI source indicator in UI** — Show Gemini vs Groq badge on prediction cards.
5. **Automated prediction tests** — Integration tests for fallback chain (Gemini fail → Groq).
6. **iOS Safari audio notes** — Audio requires gesture on iOS; current tap-listener solution handles this but should be regression-tested.
7. **Constructor lineage gaps** — Williams, McLaren, Ferrari don't need lineage (consistent branding), but verify Haas and Alpine subtleties.

