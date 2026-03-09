# Every Lap. — Product Management Document

**Product:** F1 Analytics Platform ("Every Lap.")  
**PM:** Mohit Unecha  
**Last Updated:** March 3, 2026  
**Current Season:** 2026 (Active)

---

## 1. Product Vision

> Give any F1 fan the same depth of race intelligence that a team engineer has — packaged in a fast, beautiful interface they'd actually use on race weekend.

Every Lap is a self-hosted F1 intelligence platform that blends 25 years of historical race data with real-time telemetry, ML predictions, and AI-assisted analysis. The product is designed as a personal platform first, with a path to broader audiences.

---

## 2. Target Users

| Segment | Description | Priority |
|---------|-------------|----------|
| Power F1 fan | Watches every session, wants data beyond broadcast TV | P0 |
| Data hobbyist | Interested in F1 as a ML/analytics playground | P0 |
| Self-hoster | Developer who wants a personal F1 dashboard | P1 |
| Casual fan | Watches races, occasionally wants context | P2 |

---

## 3. Core User Jobs-to-Be-Done

1. **"I want to know who's going to win before the race starts"** — Predictions page with ML probabilities + AI narrative
2. **"I want to replay what happened in that race"** — Race replay with real telemetry, positions, tyres
3. **"I want to understand a driver or team's full history"** — Profile pages with career stats and lineage
4. **"I want live lap times and weather during the race"** — Live data page with OpenF1 integration
5. **"I want to compare two drivers lap-by-lap"** — Compare and telemetry views

---

## 4. Feature Inventory (Current State)

### Shipped — Core

| Feature | Status | Notes |
|---------|--------|-------|
| Race predictions (ML) | ✅ Live | XGBoost + LightGBM + CatBoost ensemble |
| AI predictions overlay | ✅ Live | Groq + Gemini consensus |
| Weather in AI predictions | ✅ Live | Air temp, track temp, humidity, wind from OpenF1 |
| Race replay | ✅ Live | Canvas-based, real telemetry |
| Driver profiles | ✅ Live | Career stats, ELO rating |
| Constructor profiles | ✅ Live | With lineage system |
| Constructor lineage | ✅ Live | Racing Bulls traces back to Toro Rosso (2006) |
| Audi profile (2026) | ✅ Live | New team — zero fake history |
| Cadillac profile (2026) | ✅ Live | New team — zero fake history |
| Audi / Cadillac logos | ✅ Live | Local SVGs (custom designed) |
| Live session data | ✅ Live | OpenF1 real-time integration |
| Analytics / telemetry | ✅ Live | Speed, throttle, brake, gear |
| Driver comparison | ✅ Live | Head-to-head lap/telemetry |
| Champions bar | ✅ Live | Timeline of champions |
| 2026 season defaults | ✅ Live | All pages default to 2026 |
| Sprint data | ✅ Live | Ingested via Jolpica-F1 |
| Jolpica-F1 consolidated | ✅ Live | `/api/external/jolpica-f1/{season}` |

### Shipped — UX / Quality

| Feature | Status | Notes |
|---------|--------|-------|
| Intro animation | ✅ Live | Lights + car flyby + reveal slam |
| Animation session gate | ✅ Live | `sessionStorage` — hard refresh only, not on nav |
| Audio unlock (mobile) | ✅ Live | Three-tier: autoplay → muted trick → tap listener |
| "Tap to hear audio" hint | ✅ Live | Fades in during lights phase if audio blocked |
| Text anti-glitch | ✅ Live | `will-change` + `translateZ(0)` on reveal text |
| Graceful image fallback | ✅ Live | No broken image states |
| Pre-2018 data disclaimer | ✅ Live | FastF1 limitation noted |
| No Docker dependency | ✅ Live | Pure venv + npm |

### In Progress / Planned

| Feature | Priority | Notes |
|---------|----------|-------|
| Live weather forecast for upcoming races | P1 | OpenF1 only covers past sessions |
| AI source badge in prediction UI | P1 | Show "Groq" vs "Gemini" on cards |
| Official Audi / Cadillac logo assets | P2 | Need licensing |
| 2026 driver roster confirmation | P1 | Verify Hadjar: Racing Bulls or Red Bull? |
| Automated prediction fallback tests | P2 | Integration test for Gemini → Groq chain |

---

## 5. Roadmap

### Now (Active Sprint — March 2026)

- [x] Animation gate + audio unlock (mobile-safe)
- [x] Cadillac & Audi clean new-team profiles
- [x] Racing Bulls 20-season lineage
- [x] Notable driver deduplication
- [x] Weather fully wired into AI prediction stack
- [x] Local SVG logos for Audi + Cadillac
- [x] README + PRODUCT_SPEC updated
- [x] PM Doc created

### Next (Q1 2026 — March/April)

| Item | Owner | Priority |
|------|-------|----------|
| Forecast weather for pre-race predictions | Engineering | P1 |
| AI badge on prediction cards | Engineering | P1 |
| 2026 Australian GP live replay | Engineering | P0 — First race of season |
| Confirm 2026 driver lineups post-official announcement | PM | P0 |
| Performance: prediction response time < 3s | Engineering | P1 |

### Later (Q2 2026)

- Mobile-optimized layout (current is desktop-first)
- Race weekend notification / countdown
- Personal prediction history (local storage)
- Shareable prediction links
- Driver vs driver ELO head-to-head page

---

## 6. Metrics & Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Prediction accuracy (podium hit rate) | ~78–85% | >85% |
| Prediction response time | ~2–5s | <3s |
| Replay playback start time | <2s | <1.5s |
| Mobile audio unlock rate | Via tap fallback | 100% (user needs to tap once) |
| Pages defaulting to 2026 | All | All |
| Broken constructor profiles | 0 | 0 |

---

## 7. Known Issues / Bugs

| Issue | Severity | Status |
|-------|----------|--------|
| iOS Safari audio autoplay blocked | Medium | Mitigated — tap listener handles it |
| OpenF1 weather N/A for future races | Medium | Open — need forecast API |
| Racing Bulls 2026 driver uncertainty (Hadjar placement) | High | Open — need official 2026 confirmation |
| Audi/Cadillac logos are custom SVGs, not official | Low | Open — waiting for licensing |
| Pre-2018 telemetry limited by FastF1 | Low | Known, documented in UI |

---

## 8. Technical Decisions Log

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| Feb 2026 | SQLite over PostgreSQL | Zero-infra local dev | PostgreSQL (adds Docker dep) |
| Feb 2026 | Constructor lineage dict | DB has separate constructor_id per rebrand | JOIN across rename table |
| Mar 2026 | sessionStorage animation gate | Plays once per hard refresh, not every nav | localStorage (too persistent), always-show (annoying) |
| Mar 2026 | Weather in AI prompts | Significantly impacts strategy/performance model | Weather-only page (siloed) |
| Mar 2026 | Multi-AI consensus | Blends Groq + Gemini for better accuracy | Single AI (less robust) |
| Mar 2026 | Local SVG logos | Wikipedia links were 404; licensing unclear | External CDN link |

---

## 9. API Dependencies & Health

| Service | Purpose | Fallback |
|---------|---------|---------|
| OpenF1 | Live timing, weather | Graceful degradation, DB Weather model |
| Jolpica-F1 | Race results, standings | Cached DB data |
| FastF1 | Telemetry, session data | Local cache (`data/fastf1_cache/`) |
| Groq | AI race analysis | Gemini fallback |
| Gemini | Secondary AI layer | Groq fallback |
| Tavily | News enrichment | Skipped (non-blocking) |

---

## 10. Open Decisions

| # | Question | Options | Due By |
|---|----------|---------|--------|
| 1 | Is Hadjar at Racing Bulls or Red Bull in 2026? | (a) Racing Bulls [current], (b) Red Bull | Before Australian GP |
| 2 | Use official Audi/Cadillac logos or keep SVGs? | (a) Custom SVGs [current], (b) Official assets when licensed | Q2 2026 |
| 3 | Weather forecast API for pre-race predictions? | (a) OpenWeatherMap, (b) WeatherAPI.com, (c) Skip | Next sprint |
| 4 | Personal prediction history feature? | (a) localStorage, (b) Server session, (c) Defer | Q2 2026 |

---

## 11. Stakeholders

| Role | Person | Involvement |
|------|--------|-------------|
| Product + Engineering | Mohit Unecha | Full ownership |
| End users | F1 fans, personal use | Feedback via direct use |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **Constructor lineage** | System that maps a team to its predecessor names (e.g., Racing Bulls → AlphaTauri → Toro Rosso) for historical stat aggregation |
| **Animation gate** | `sessionStorage`-based mechanism that prevents the intro animation from replaying on every page navigation |
| **Multi-AI consensus** | Pipeline that averages Groq and Gemini prediction outputs for improved accuracy |
| **BOOST** | Internal prediction system term for context enhancement steps (weather = BOOST 7, news = BOOST 1, etc.) |
| **ELO rating** | Relative driver skill rating computed from historical head-to-head race performance |
| **New-entry team** | Constructor with `founded_year >= 2025` (Audi, Cadillac) — uses `Event.season >= founded_year` filter to prevent fake historical data |
