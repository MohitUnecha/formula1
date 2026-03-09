# F1 Analytics Frontend

Production-ready Next.js frontend for F1 race predictions and analytics.

## Features

- **Race Calendar**: Browse all F1 races by season with event details
- **Race Predictions**: ML-powered predictions with win/podium/top-10 probabilities
- **Race Replay**: Interactive Canvas-based race visualization with playback controls
- **SHAP Explainability**: Understand what drives each prediction
- **Responsive Design**: Works on desktop, tablet, and mobile

## Tech Stack

- Next.js 14 with App Router
- React 18 with TypeScript
- TailwindCSS for styling
- React Query for data fetching
- Headless UI for accessible components
- Lucide React for icons
- Canvas API for race visualization

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running (see backend README)

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local

# Edit .env.local with your API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/                       # Next.js 14 App Router
│   ├── layout.tsx            # Root layout with navigation
│   ├── page.tsx              # Homepage
│   ├── providers.tsx         # React Query provider
│   ├── globals.css           # Global styles
│   ├── races/                # Race pages
│   │   ├── page.tsx          # Race calendar
│   │   └── [season]/[eventId]/[sessionId]/
│   │       └── page.tsx      # Session details with predictions & replay
│   ├── drivers/              # Driver pages
│   │   └── page.tsx
│   └── compare/              # Comparison pages
│       └── page.tsx
├── components/               # React components
│   ├── predictions/
│   │   └── PredictionCard.tsx  # Prediction display with explainability
│   └── replay/
│       └── TrackCanvas.tsx     # Race replay visualization
├── lib/                      # Utilities
│   ├── api.ts               # API client for backend
│   ├── types.ts             # TypeScript type definitions
│   └── utils.ts             # Helper functions
└── public/                   # Static assets

```

## API Client

The `lib/api.ts` file provides a typed API client:

```typescript
import api from '@/lib/api';

// Get seasons
const seasons = await api.getSeasons();

// Get predictions
const predictions = await api.getPredictions(sessionId);

// Get replay data
const metadata = await api.getReplayMetadata(sessionId);
const frames = await api.getReplayFrames(sessionId, 1, 10, 5);
```

## Components

### PredictionCard

Displays driver predictions with:
- Win/Podium/Top-10 probabilities
- Expected position
- DNF probability
- SHAP explainability (expandable)

### TrackCanvas

Interactive race replay with:
- Canvas-based rendering (60 FPS)
- Playback controls (play/pause/skip)
- Speed adjustment (0.5x - 4x)
- Driver positions with team colors
- Gap information
- Race events (pit stops, safety car)

## Styling

TailwindCSS with custom theme:
- F1 red gradient (`from-red-600 to-red-400`)
- Dark theme optimized
- Custom component classes (`.driver-card`, `.prediction-bar`)

## Data Flow

1. User navigates to `/races`
2. React Query fetches seasons from API
3. User selects race → fetches events
4. User selects session → fetches predictions & replay data
5. Components render with real-time data

## Environment Variables

```
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

## Troubleshooting

**API connection errors:**
- Ensure backend is running on port 8000
- Check NEXT_PUBLIC_API_URL in .env.local
- Verify CORS is enabled in backend

**Build errors:**
- Run `npm install` to ensure all dependencies are installed
- Clear Next.js cache: `rm -rf .next`
- Check TypeScript errors: `npm run type-check`

**Predictions not loading:**
- Ensure data ingestion has been run on backend
- Check if models are trained
- Try computing predictions via the UI button

## Future Enhancements

- [ ] Driver statistics page
- [ ] Team comparisons
- [ ] Advanced telemetry charts
- [ ] Mobile app version
- [ ] Real-time race tracking
- [ ] User authentication
- [ ] Favorite drivers/teams

## Performance

- Server-side rendering for SEO
- Automatic code splitting
- Image optimization
- React Query caching (1 min stale time)
- Canvas rendering for smooth animations

## License

Part of the F1 Analytics Platform project.
