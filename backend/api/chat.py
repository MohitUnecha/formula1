"""
Crofty — F1 AI Chatbot Endpoint
Powered by Groq (llama-3.3-70b-versatile) with full access to:
  - SQL database (events, results, drivers, constructors, laps, pit stops)
  - FastF1 historical knowledge baked into system prompt
  - Prediction awareness with redirect hints
"""
from __future__ import annotations

import re
import json
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from config import settings
from database import get_db

router = APIRouter()

# ─── Pydantic schemas ────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    suggest_predictions: bool = False
    prediction_context: Optional[str] = None  # e.g. "2026 Australian GP"


# ─── DB context helper ───────────────────────────────────────────────────────

def _build_db_context(question: str, db: Session) -> str:
    """
    Query the database for facts relevant to the user's question.
    Returns a compact text block injected into the system prompt.
    """
    rows_collected: List[str] = []

    q_lower = question.lower()

    # --- Recent race results ---
    try:
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', question)
        year_filter = int(year_match.group(1)) if year_match else None

        if year_filter:
            result = db.execute(text("""
                SELECT e.season, e.round, e.event_name, e.country,
                       d.first_name || ' ' || d.last_name AS driver_name,
                       d.driver_code, dr.team_name,
                       ds.position, ds.points, ds.status
                FROM driver_sessions ds
                JOIN sessions s ON s.session_id = ds.session_id
                JOIN events e ON e.event_id = s.event_id
                JOIN drivers d ON d.driver_id = ds.driver_id
                LEFT JOIN drivers dr ON dr.driver_id = ds.driver_id
                WHERE s.session_type = 'R'
                  AND e.season = :year
                  AND ds.position IS NOT NULL
                ORDER BY e.round, ds.position
                LIMIT 200
            """), {"year": year_filter})
            rows = result.fetchall()
            if rows:
                rows_collected.append(f"=== {year_filter} Race Results ===")
                current_event = None
                count = 0
                for row in rows:
                    if row.event_name != current_event:
                        if count >= 3 and current_event:
                            rows_collected.append("  ...")
                        current_event = row.event_name
                        rows_collected.append(f"\n  [{row.round}] {row.event_name} ({row.country}):")
                        count = 0
                    if count < 5:  # top 5 per race
                        rows_collected.append(
                            f"    P{row.position}: {row.driver_name} ({row.driver_code}) - {row.team_name} [{row.status}]"
                        )
                    count += 1

    except Exception as exc:
        rows_collected.append(f"[DB year query error: {exc}]")

    # --- Driver standings / info ---
    try:
        result = db.execute(text("""
            SELECT d.first_name || ' ' || d.last_name AS driver_name,
                   d.driver_code, d.nationality, d.team_name,
                   SUM(ds.points) AS total_points,
                   COUNT(CASE WHEN ds.position = 1 THEN 1 END) AS wins
            FROM drivers d
            LEFT JOIN driver_sessions ds ON ds.driver_id = d.driver_id
            LEFT JOIN sessions s ON s.session_id = ds.session_id AND s.session_type = 'R'
            GROUP BY d.driver_id
            ORDER BY total_points DESC
            LIMIT 30
        """))
        rows = result.fetchall()
        if rows:
            rows_collected.append("\n=== All-Time Driver Stats (DB) ===")
            for row in rows:
                rows_collected.append(
                    f"  {row.driver_name} ({row.driver_code}) | {row.team_name} | {row.nationality} | "
                    f"Points: {row.total_points or 0} | Wins: {row.wins or 0}"
                )
    except Exception as exc:
        rows_collected.append(f"[DB driver query error: {exc}]")

    # --- Recent seasons list ---
    try:
        result = db.execute(text("""
            SELECT DISTINCT season FROM events ORDER BY season DESC LIMIT 10
        """))
        seasons_available = [str(r.season) for r in result.fetchall()]
        if seasons_available:
            rows_collected.append(f"\n=== Seasons in DB: {', '.join(seasons_available)} ===")
    except Exception:
        pass

    # --- Champion per season (P1 in last race of season) ---
    try:
        result = db.execute(text("""
            SELECT e.season,
                   d.first_name || ' ' || d.last_name AS champion,
                   d.team_name,
                   SUM(ds.points) AS season_points
            FROM driver_sessions ds
            JOIN sessions s ON s.session_id = ds.session_id AND s.session_type = 'R'
            JOIN events e ON e.event_id = s.event_id
            JOIN drivers d ON d.driver_id = ds.driver_id
            GROUP BY e.season, d.driver_id
            ORDER BY e.season DESC, season_points DESC
        """))
        season_champs: Dict[int, str] = {}
        for row in result.fetchall():
            if row.season not in season_champs:
                season_champs[row.season] = f"{row.champion} ({row.team_name}, {row.season_points} pts)"
        if season_champs:
            rows_collected.append("\n=== Season Champions (by points) ===")
            for yr in sorted(season_champs.keys(), reverse=True):
                rows_collected.append(f"  {yr}: {season_champs[yr]}")
    except Exception as exc:
        rows_collected.append(f"[DB champion query error: {exc}]")

    return "\n".join(rows_collected) if rows_collected else "No specific DB data found for this query."


# ─── Crofty system prompt ─────────────────────────────────────────────────────

CROFTY_SYSTEM_PROMPT = """You are CROFTY, the AI F1 expert chatbot for this platform — named after David Croft, the legendary Sky Sports F1 commentator. You embody his enthusiastic, knowledgeable, and entertaining style.

PERSONALITY:
- Passionate, energetic, and deeply knowledgeable about Formula 1
- Use Crofty-style exclamations: "AND IT'S LIGHTS OUT AND AWAY WE GO!", "That's MEGA!", "Ohhh, that's a big one!"
- Reference iconic moments, drivers, and teams naturally in conversation
- Occasionally say "IT'S LIGHTS OUT!" when you get excited
- Be warm, engaging, and occasionally humorous — like talking to a friend who happens to know everything about F1
- Use British English spelling and expressions

═══════════════════════════════════════════════════
PLATFORM GUIDE — KNOW THE WEBSITE INSIDE OUT
═══════════════════════════════════════════════════

This platform is a full-stack F1 analytics and predictions hub covering 2000–2026.
Dataset: 527+ race weekends, 195,000+ laps, 101 drivers, 40+ constructors, 26 seasons.
Tech: Next.js frontend, FastAPI + Python backend, SQLite DB, FastF1 telemetry, ML models (Gradient Boosting), multi-AI consensus (Groq, Gemini, DeepSeek, NVIDIA Nemotron).

PAGES & FEATURES:

🏠 HOME  (/):
- Season overview with live championship standings
- Current/upcoming race event card with countdown
- Recent race winners, championship leaders
- Quick-access cards to all major features

🏎️ RACES  (/races and /races/{season}/{eventId}/{sessionId}):
- Browse every race from 2000–2026 by season
- Click any race for full results: starting grid, finishing positions, fastest laps, DNFs
- Per-driver lap-by-lap data, pit stops, tyre strategies
- Sprint race support included
- Direct links to session replays and analytics

📊 ANALYTICS  (/analytics):
- Deep dive into lap times, sector analysis, position changes across races
- Tyre degradation curves, pit stop timing
- 25 years of F1 data visualized

⚡ LIVE  (/live):
- Live-style session replay for any stored race
- RACE mode: lap-by-lap position predictions updating in real time as race progresses
- TIMING mode (for Practice & Qualifying sessions): timing tower showing best laps, sector times, gaps to leader, tyre compounds, Q1/Q2/Q3 cut lines
- Session picker: FP1, FP2, FP3, Qualifying, Sprint Qualifying, and Race
- Works for 2024 and 2025 seasons (2026 as data becomes available)
- Lap slider + auto-play to replay any point in the session
- Use this page to relive qualifying battles or watch a race unfold lap by lap

🔮 PREDICTIONS  (/predictions):
- ML-powered race winner predictions using Gradient Boosting
- Multi-AI consensus: 6 AI models (Groq, Gemini, DeepSeek, NVIDIA Nemotron) vote on outcomes
- Win probability %, podium chance %, DNF risk per driver
- Based on qualifying times, historical performance, circuit characteristics, weather
- Updated for every upcoming race weekend

🏆 DRIVERS  (/drivers and /drivers/{code}):
- Full profile for every F1 driver: career stats, wins, podiums, points, DNFs
- Head-to-head comparison between any two drivers
- Season-by-season breakdown
- Team history per driver

🏗️ CONSTRUCTORS  (/constructors and /constructors/{id}):
- Constructor profiles with championship history
- Team performance across seasons
- Driver lineup history

🔄 REPLAY  (/replay):
- Animated race replay on real circuit SVG layouts
- Watch every car move lap by lap around the track
- Shows: tyre compounds, DRS zones, pit stops, weather conditions
- Inspired by professional F1 broadcast graphics

📈 COMPARE  (/compare):
- Side-by-side stats comparison: any two drivers or teams
- Pick any season and metric

ℹ️ ABOUT  (/about):
- Platform tech stack details
- Data sources: FastF1, OpenF1, Jolpica F1 API, Official F1 Media
- Credits and open-source acknowledgements

NAVIGATION TIPS:
- If someone asks "how do I see Hamilton vs Verstappen stats" → direct them to /compare
- If someone asks "who will win" → direct them to /predictions
- If someone asks about a specific race → direct them to /races
- If someone wants to watch a qualifying session → direct them to /live, select the season/event/session type
- If someone wants to see live timing -> /live, select FP or Qualifying session, use the lap slider

═══════════════════════════════════════════════════
F1 KNOWLEDGE BASE
═══════════════════════════════════════════════════

Full F1 history from the 1950s to 2026 including:
- All race winners, world champions, constructors champions
- Circuit histories, lap records, legendary moments
- Technical regulations, tyre rules (P Zero compounds: Soft/Medium/Hard/Inter/Wet)
- DRS zones, Safety Car rules, VSC, red flags
- Current 2026 season (Australian GP just happened in March 2026)
- 2026 reg changes: new power unit regs (1.6L V6 hybrid, equal electrical/ICE split), active aerodynamics, new teams (Audi/Cadillac joining)

HISTORICAL F1 CHAMPIONS:
- 2000 WDC: Michael Schumacher (Ferrari) — won 9 races
- 2001 WDC: Michael Schumacher (Ferrari)
- 2002 WDC: Michael Schumacher (Ferrari) — dominant
- 2003 WDC: Michael Schumacher (Ferrari, tight battle with Raikkonen/Montoya)
- 2004 WDC: Michael Schumacher (Ferrari) — record 13 wins
- 2005 WDC: Fernando Alonso (Renault) — youngest champion at the time
- 2006 WDC: Fernando Alonso (Renault)
- 2007 WDC: Kimi Räikkönen (Ferrari) — by just ONE point!
- 2008 WDC: Lewis Hamilton (McLaren) — last lap drama in Brazil!
- 2009 WDC: Jenson Button (Brawn GP) — fairy tale season
- 2010 WDC: Sebastian Vettel (Red Bull) — youngest ever champion at the time
- 2011 WDC: Sebastian Vettel (Red Bull)
- 2012 WDC: Sebastian Vettel (Red Bull) — Interlagos drama
- 2013 WDC: Sebastian Vettel (Red Bull) — 9 consecutive wins
- 2014 WDC: Lewis Hamilton (Mercedes) — dominant hybrid era begins
- 2015 WDC: Lewis Hamilton (Mercedes)
- 2016 WDC: Nico Rosberg (Mercedes) — then retired the week after!
- 2017 WDC: Lewis Hamilton (Mercedes)
- 2018 WDC: Lewis Hamilton (Mercedes)
- 2019 WDC: Lewis Hamilton (Mercedes)
- 2020 WDC: Lewis Hamilton (Mercedes) — equalled Schumacher's record 7 titles
- 2021 WDC: Max Verstappen (Red Bull) — Abu Dhabi last-lap drama!
- 2022 WDC: Max Verstappen (Red Bull) — dominant season
- 2023 WDC: Max Verstappen (Red Bull) — record-breaking 19 wins in a season
- 2024 WDC: Max Verstappen (Red Bull) — 4th consecutive title
- 2025 WDC: Lando Norris (McLaren) — first championship, incredible season
- 2026: Season in progress, Australian GP done, McLaren vs Ferrari vs Red Bull battle

NOTABLE RACES:
- 2021 Abu Dhabi GP: Verstappen overtook Hamilton on the last lap after controversial SC restart
- 2008 Brazilian GP: Hamilton secured title on last corner of last lap
- 2016 Monaco GP: Ricciardo pit stop disaster cost him a certain win
- 2005 European GP: Alonso vs Schumacher masterclass at the Nürburgring
- 2012 season: 7 different winners in first 7 races

═══════════════════════════════════════════════════
PREDICTION GUIDANCE
═══════════════════════════════════════════════════
When asked "who will win" or prediction questions:
- Give your Crofty-style enthusiastic analysis
- ALWAYS mention the Predictions page at /predictions for full ML + multi-AI analysis
- Set suggest_predictions: true so the UI shows the button
- In prediction_context, name the relevant GP if identifiable

DATABASE CONTEXT (live from platform SQL):
{DB_CONTEXT}

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
- Always be accurate; use DB data for specific season questions
- If unsure, say so honestly with Crofty flair — never fabricate results
- Keep answers focused and energetic — max 3-4 paragraphs
- When directing users to a page, mention the page name AND the URL path
- End prediction answers by suggesting the Predictions tool on the platform

RESPONSE FORMAT — always valid JSON:
{
  "reply": "your Crofty-style response here",
  "suggest_predictions": true/false,
  "prediction_context": "GP name if relevant, otherwise null"
}
"""


# ─── Groq chat call ──────────────────────────────────────────────────────────

async def _call_groq_chat(
    messages: List[Dict[str, str]],
    api_key: str,
) -> str:
    """Call Groq Chat Completions and return the assistant message text."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error {resp.status_code}: {resp.text[:300]}",
        )
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ─── Route ───────────────────────────────────────────────────────────────────

@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Crofty AI chatbot — answers F1 questions using DB + historical knowledge."""
    api_key = settings.groq_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="Groq API key not configured")

    # Build DB context from live data
    db_context = _build_db_context(req.message, db)

    # Inject DB context into system prompt
    system_prompt = CROFTY_SYSTEM_PROMPT.replace("{DB_CONTEXT}", db_context)

    # Build message list for Groq
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Attach conversation history (last 8 turns max)
    for msg in req.history[-8:]:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current user message
    messages.append({"role": "user", "content": req.message})

    # Call Groq
    raw = await _call_groq_chat(messages, api_key)

    # Parse JSON response
    try:
        parsed = json.loads(raw)
        reply = parsed.get("reply", raw)
        suggest_predictions = bool(parsed.get("suggest_predictions", False))
        prediction_context = parsed.get("prediction_context") or None
    except (json.JSONDecodeError, ValueError):
        # Fallback: return raw text
        reply = raw
        suggest_predictions = any(
            kw in req.message.lower()
            for kw in ["who will win", "predict", "who do you think", "going to win", "favourite", "favorite"]
        )
        prediction_context = None

    return ChatResponse(
        reply=reply,
        suggest_predictions=suggest_predictions,
        prediction_context=prediction_context,
    )
