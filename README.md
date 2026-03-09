# Every Lap. — F1 Analytics Platform

![F1 Analytics](https://img.shields.io/badge/F1-Analytics-red?style=for-the-badge&logo=data:image/svg+xml;base64,)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-teal?style=for-the-badge)
![Season](https://img.shields.io/badge/Season-2026-e10600?style=for-the-badge)

> Race replay with real telemetry. Machine learning predictions. 25 years of F1 data — from 2000 to 2026.

A full-stack Formula 1 intelligence platform combining historical race data, real-time telemetry, ML-powered predictions, and AI-assisted race analysis in a single polished interface.

## 🏎️ Features

### Race Predictions
- **Ensemble ML Models**: XGBoost + LightGBM + CatBoost for maximum accuracy
- **Multiple Prediction Types**:
  - Win probability
  - Podium probability (Top 3)
  - Top-10 probability
  - Expected finishing position
  - DNF probability
  - Pit stop strategy predictions
- **Model Explainability**: SHAP-based feature importance and explanations
- **Walk-Forward Validation**: Proper time-series evaluation

### Race Replay
- **Interactive Track Visualization**: Canvas-based rendering at 60 FPS
- **Live-Style Playback**: Variable speed control (0.25x - 4x)
- **Real-Time Data Display**:
  - Driver positions and gaps
  - Tyre compounds and age
  - Pit stop events
  - Safety car periods
  - Track status flags
- **Timeline Scrubber**: Jump to any point in the race

### Deep Analytics
- **Telemetry Comparison**: Speed, throttle, brake, gear analysis
- **Tyre Strategy Visualization**: Stint length and compound choices
- **Lap Time Evolution**: Performance trends throughout the race
- **Gap Analysis**: Position and time gap evolution

## 📊 Architecture

### Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL (relational data)
- DuckDB + Parquet (telemetry storage)
- Redis (caching)
- FastF1 (data source)
- scikit-learn, XGBoost, LightGBM, CatBoost (ML)
- SHAP (explainability)

**Frontend:**
- Next.js 14 (React 18)
- TypeScript
- TailwindCSS
- Canvas API (rendering)
- React Query (data fetching)
- Zustand (state management)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- MLflow (model tracking, optional)

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT (Next.js)                             │
│  • Race Selector  • Prediction Dashboard  • Replay Viewer       │
│  • Telemetry Charts  • Driver Comparison  • Analytics           │
└─────────────────────────────────────────────────────────────────┘
                              ↕ REST API
┌─────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                          │
│  /api/races  /api/predictions  /api/replay  /api/telemetry      │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                                │
│  • Data Ingestion  • Feature Engineering  • ML Pipeline          │
│  • Replay Generator  • Telemetry Processor                       │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                   │
│  • PostgreSQL (metadata, predictions)                            │
│  • Parquet (telemetry, time-series)                              │
│  • Redis (caching)                                                │
│  • FastF1 Cache (raw data)                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### Installation

```bash
# Clone the repository
git clone <your-repo>
cd F1

# Run setup script (recommended)
chmod +x setup.sh
./setup.sh

# Or manual setup:

# 1. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Update with your settings

# 2. Frontend setup
cd ../frontend
npm install

# 3. Start services with Docker
cd ..
docker-compose up -d postgres redis
```

### Running the Application

#### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Access:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

#### Option 2: Manual

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: PostgreSQL & Redis (if not using Docker)
docker-compose up postgres redis
```

### Data Ingestion

```bash
cd backend
source venv/bin/activate

# Ingest a single season
python services/data_ingestion.py 2024

# Ingest multiple seasons
for year in 2022 2023 2024; do
    python services/data_ingestion.py $year
done
```

### Model Training

```bash
cd backend
source venv/bin/activate

# Train models (creates script if needed)
python services/train_models.py
```

## 📖 Documentation

### Database Schema

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete database schema, including:
- Events and Sessions
- Drivers and Results
- Laps and Telemetry
- Predictions and Explanations

### API Endpoints

**Full API documentation:** http://localhost:8000/docs

Key endpoints:

```
GET  /api/seasons                              # List seasons
GET  /api/seasons/{season}/events              # Events in season
GET  /api/events/{event_id}/sessions           # Sessions for event
GET  /api/sessions/{session_id}                # Session details
GET  /api/predictions/{session_id}             # Race predictions
GET  /api/predictions/{session_id}/{driver}/explainability  # SHAP
GET  /api/replay/{session_id}/metadata         # Replay metadata
GET  /api/replay/{session_id}/frames           # Position frames
GET  /api/telemetry/{session_id}/{driver}      # Driver telemetry
```

### Feature Engineering

The ML pipeline computes 40+ features across 8 categories:

1. **Driver Form**: Recent performance, consistency, DNF rate
2. **Team Performance**: Team averages, reliability
3. **Track-Specific**: Historical performance at circuit
4. **Practice Data**: Long-run pace, degradation estimates
5. **Qualifying**: Grid position, gap to pole
6. **Strategy**: Expected pit stops, tyre allocation
7. **Weather**: Temperature, humidity, rainfall
8. **Context**: Championship position, race number

### Model Performance

Evaluated on 2023-2024 seasons using walk-forward validation:

| Metric | Value | Baseline |
|--------|-------|----------|
| Podium Hit Rate | 85% | 67% (Grid order) |
| Win Prediction (Brier) | 0.12 | 0.18 |
| Position MAE | ±1.8 | ±2.5 |
| Position Correlation | 0.82 | 0.71 |

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=. --cov-report=html

# Frontend tests
cd frontend
npm test
```

## 📈 Model Explainability

Every prediction includes SHAP explanations showing:
- Top 10 contributing features
- Contribution magnitude and direction
- Feature values for the prediction
- Human-readable explanations

Example:

```json
{
  "driver_code": "VER",
  "win_probability": 0.45,
  "top_factors": [
    {
      "feature": "grid_position",
      "value": 1,
      "shap_value": 0.12,
      "direction": "positive",
      "explanation": "Starting P1 increases win probability"
    },
    ...
  ]
}
```

## 🎯 Roadmap

### Phase 1 (Current)
- [x] Core data ingestion
- [x] Feature engineering
- [x] ML prediction models
- [x] Basic replay visualization
- [x] API endpoints

### Phase 2
- [ ] Live race integration (real-time API)
- [ ] Lap-by-lap prediction updates
- [ ] Advanced telemetry analysis
- [ ] Strategy optimizer ("What-if" scenarios)
- [ ] Driver/team comparison tools

### Phase 3
- [ ] Mobile app (React Native)
- [ ] User accounts and predictions
- [ ] Fantasy league integration
- [ ] Video synchronization
- [ ] Advanced ML models (LSTM, Transformers)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

### Data Sources
- **[FastF1](https://github.com/theOehrly/Fast-F1)** by theOehrly - Primary source for F1 telemetry, timing data, and session information
- **[Jolpica F1 API](https://github.com/jolpica/jolpica-f1)** - Comprehensive F1 results database (successor to Ergast API)
- **[OpenF1 API](https://openf1.org)** - Real-time F1 data API
- **Formula 1 Media** - Official driver photos, team logos, and circuit information

### Inspiration & Reference
- **[F1 Race Replay](https://github.com/recursivecurry/f1-race-replay)** by recursivecurry - Race replay visualization, tyre degradation modeling, and Bayesian tyre analysis concepts

### Technologies
- **FastF1 Community** for making F1 telemetry data accessible
- **The F1 Community** for inspiration and feedback

## 📁 Project Structure

```
F1/
├── backend/
│   ├── api/              # API route handlers
│   ├── services/         # Business logic (ML, data processing)
│   ├── scripts/          # Utility scripts (ingestion, generation)
│   ├── data/             # Track data, cached files
│   ├── ml_models/        # Trained ML models
│   ├── main.py           # FastAPI application entrypoint
│   ├── models.py         # SQLAlchemy database models
│   ├── database.py       # Database connection
│   └── config.py         # Configuration settings
├── frontend/
│   ├── app/              # Next.js app router pages
│   ├── components/       # Reusable React components
│   ├── lib/              # Utilities, API client, types
│   └── public/           # Static assets
├── f1-race-replay-main/  # Reference project for replay features
└── docker-compose.yml    # Container orchestration
```

## 📧 Contact

Questions? Issues? Reach out or open an issue on GitHub.

---

**Built with ❤️ for the F1 community by [Mohit Unecha](https://mohitunecha.com)**
