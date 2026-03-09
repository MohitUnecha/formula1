/**
 * TypeScript type definitions
 */

export interface Season {
  season: number;
  total_events: number;
}

export interface Driver {
  driver_id: number;
  driver_code: string;
  driver_number?: number;
  first_name: string;
  last_name: string;
  nationality?: string;
  team_name?: string;
  photo_url?: string;
  biography?: string;
}

export interface DriverStanding {
  driver_code: string;
  driver_name: string;
  photo_url?: string;
  team_name?: string;
  total_points: number;
  wins: number;
  podiums: number;
  dnfs: number;
}

export interface Event {
  event_id: number;
  season: number;
  round: number;
  event_name: string;
  event_date: string;
  event_format: string;
  country: string;
  location: string;
  circuit_key: string;
  session_count: number;
  has_sprint?: boolean;
}

export interface Session {
  session_id: number;
  event_id: number;
  event_name: string;
  session_type: string;
  session_date: string;
  total_laps: number;
  track_length_km: number;
  driver_count: number;
}

export interface DriverSession {
  driver_code: string;
  driver_name: string;
  team_name: string;
  grid?: number;
  position?: number;
  points?: number;
  dnf: boolean;
  fastest_lap?: number;
  status?: string;
}

export interface Prediction {
  driver_code: string;
  driver_name: string;
  team_name: string;
  win_probability: number;
  podium_probability: number;
  top10_probability: number;
  expected_position: number;
  dnf_probability: number;
  expected_pit_stops?: number;
  prediction_confidence: number;
  groq?: {
    probability?: number;
    explanation?: string;
    raw?: string;
    error?: string;
  };
}

export interface ExplainabilityFactor {
  feature: string;
  shap_value: number;
  feature_value: number;
  direction: string;
  explanation: string;
}

export interface Explainability {
  driver_code: string;
  predictions: {
    win_probability: number;
    podium_probability: number;
    expected_position: number;
  };
  top_factors: ExplainabilityFactor[];
}

export interface TrackLayout {
  circuit_key: string;
  rotation: number;
  corners: Array<{ x: number; y: number }>;
  width: number;
  height: number;
}

export interface DriverFrame {
  code: string;
  position: number;
  x: number;
  y: number;
  speed: number;
  tyre: string;
  tyre_age: number;
  gap_to_leader: number;
  gap_to_ahead: number;
  team_color: string;
}

export interface ReplayFrame {
  lap: number;
  time_elapsed: number;
  drivers: DriverFrame[];
  track_status: string;
  flags: string[];
}

export interface ReplayMetadata {
  session_id: number;
  event_name: string;
  season: number;
  total_laps: number;
  total_frames: number;
  fps: number;
  drivers: Array<{
    code: string;
    name: string;
    team: string;
    color: string;
    grid: number;
    position: number;
    status: string;
  }>;
  track_layout: TrackLayout;
}

export interface RaceEvent {
  lap: number;
  time: number;
  type: string;
  driver?: string;
  details: string;
}

export interface DriverProfile {
  driver_code: string;
  driver_number?: number;
  first_name: string;
  last_name: string;
  full_name: string;
  nationality?: string;
  team_name?: string;
  team_color?: string;
  photo_url?: string;
  biography?: string;
  career_stats: {
    total_races: number;
    total_points: number;
    wins: number;
    podiums: number;
    poles: number;
    fastest_laps: number;
    dnfs: number;
    best_finish?: number;
    avg_finish?: number;
    avg_grid?: number;
    win_rate: number;
    podium_rate: number;
  };
  season_history: Array<{
    season: number;
    team?: string;
    team_color?: string;
    races: number;
    points: number;
    wins: number;
    podiums: number;
    best_finish?: number;
    avg_finish?: number;
    position?: number;
  }>;
  recent_results: Array<{
    event_name: string;
    season: number;
    round: number;
    country?: string;
    position?: number;
    grid?: number;
    points: number;
    status?: string;
    dnf: boolean;
    positions_gained: number;
  }>;
  elo?: {
    rating: number;
    peak_rating: number;
    tier: string;
    races_completed: number;
  };
  teammate_comparison?: {
    teammate_code: string;
    teammate_name: string;
    races_compared: number;
    wins: number;
    losses: number;
  };
}

export interface ConstructorProfile {
  constructor_id: number;
  constructor_key?: string;
  constructor_name: string;
  full_name: string;
  team_color?: string;
  nationality?: string;
  founded?: number;
  headquarters?: string;
  team_principal?: string;
  power_unit?: string;
  history?: string;
  logo_url?: string;
  career_stats: {
    total_races: number;
    total_points: number;
    wins: number;
    podiums: number;
    poles: number;
    seasons: number;
  };
  season_history: Array<{
    season: number;
    points: number;
    wins: number;
    podiums: number;
    poles: number;
    races: number;
  }>;
  current_drivers: Array<{
    driver_id: number;
    driver_code: string;
    first_name: string;
    last_name: string;
    full_name: string;
    nationality?: string;
    driver_number?: number;
    points: number;
    wins: number;
    podiums: number;
  }>;
  notable_drivers: Array<{
    driver_code: string;
    name: string;
    points: number;
    wins: number;
  }>;
}
