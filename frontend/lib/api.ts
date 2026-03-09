/**
 * API Client for F1 Analytics Backend
 */

import type {
  Season,
  Event,
  Session,
  DriverSession,
  Prediction,
  Explainability,
  ReplayMetadata,
  ReplayFrame,
  RaceEvent,
  Driver,
  DriverStanding,
  DriverProfile,
  ConstructorProfile,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Seasons
  async getSeasons(): Promise<number[]> {
    return this.request<number[]>('/api/seasons');
  }

  async getSeasonDetails(season: number): Promise<Season> {
    return this.request<Season>(`/api/seasons/${season}`);
  }

  // Events
  async getEvents(season: number): Promise<Event[]> {
    return this.request<Event[]>(`/api/seasons/${season}/events`);
  }

  async getEvent(eventId: number): Promise<Event> {
    return this.request<Event>(`/api/events/${eventId}`);
  }

  // Sessions
  async getSessions(eventId: number): Promise<Session[]> {
    return this.request<Session[]>(`/api/events/${eventId}/sessions`);
  }

  async getSession(sessionId: number): Promise<Session> {
    return this.request<Session>(`/api/sessions/${sessionId}`);
  }

  async getSessionDrivers(sessionId: number): Promise<DriverSession[]> {
    return this.request<DriverSession[]>(`/api/sessions/${sessionId}/drivers`);
  }

  // Drivers
  async getDrivers(season?: number): Promise<Driver[]> {
    const params = season ? `?season=${season}` : '';
    return this.request<Driver[]>(`/api/drivers${params}`);
  }

  async getDriver(driverCode: string): Promise<Driver> {
    return this.request<Driver>(`/api/drivers/${driverCode}`);
  }

  async getStandings(season: number): Promise<DriverStanding[]> {
    return this.request<DriverStanding[]>(`/api/standings/${season}`);
  }

  async getConstructorStandings(season: number): Promise<any[]> {
    return this.request<any[]>(`/api/constructors/standings/${season}`);
  }

  async getConstructors(season: number): Promise<any[]> {
    return this.request<any[]>(`/api/constructors/${season}`);
  }

  async getConstructorProfile(constructorId: string): Promise<ConstructorProfile> {
    return this.request<ConstructorProfile>(`/api/constructors/${constructorId}/profile`);
  }

  async getDriverStats(driverCode: string, season: number): Promise<any> {
    return this.request<any>(`/api/drivers/${driverCode}/stats/${season}`);
  }

  async getDriverProfile(driverCode: string): Promise<DriverProfile> {
    return this.request<DriverProfile>(`/api/drivers/${driverCode}/profile`);
  }

  // Predictions
  async getPredictions(sessionId: number, modelVersion?: string): Promise<Prediction[]> {
    const params = modelVersion ? `?model_version=${modelVersion}` : '';
    return this.request<Prediction[]>(`/api/predictions/${sessionId}${params}`);
  }

  async computePredictions(sessionId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/predictions/${sessionId}/compute`, {
      method: 'POST',
    });
  }

  async getExplainability(sessionId: number, driverCode: string): Promise<Explainability> {
    return this.request<Explainability>(`/api/predictions/${sessionId}/${driverCode}/explainability`);
  }

  // Replay
  async getReplayMetadata(sessionId: number): Promise<ReplayMetadata> {
    return this.request<ReplayMetadata>(`/api/replay/${sessionId}/metadata`);
  }

  async getReplayFrames(sessionId: number, startLap: number = 1, endLap: number = 1, fps: number = 5): Promise<ReplayFrame[]> {
    return this.request<ReplayFrame[]>(`/api/replay/${sessionId}/frames?start_lap=${startLap}&end_lap=${endLap}&fps=${fps}`);
  }

  async getRaceEvents(sessionId: number): Promise<RaceEvent[]> {
    return this.request<RaceEvent[]>(`/api/replay/${sessionId}/events`);
  }

  async getSessionWeather(sessionId: number): Promise<any> {
    return this.request<any>(`/api/replay/${sessionId}/weather`);
  }

  // Analysis & Telemetry
  async getLapTimeAnalysis(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/lap-times/${sessionId}`);
  }

  async getPositionChanges(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/position-changes/${sessionId}`);
  }

  async getTyreStrategy(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/tyre-strategy/${sessionId}`);
  }

  async getTelemetry(sessionId: number, driverCode: string): Promise<any> {
    return this.request<any>(`/api/telemetry/${sessionId}/${driverCode}`);
  }

  // Health
  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  // News & Sentiment
  async getLatestNews(limit: number = 30, driver?: string): Promise<any> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (driver) params.set('driver', driver);
    return this.request<any>(`/api/news/latest?${params}`);
  }

  async getDriverSentiments(): Promise<any> {
    return this.request<any>('/api/news/sentiment/drivers');
  }

  async getTeamSentiments(): Promise<any> {
    return this.request<any>('/api/news/sentiment/teams');
  }

  async getPredictionContext(season: number, round: number = 1): Promise<any> {
    return this.request<any>(`/api/news/prediction-context?season=${season}&round=${round}`);
  }

  // Live Predictions
  async getLiveStatus(): Promise<any> {
    return this.request<any>('/api/live/status');
  }

  async getLiveSimulation(sessionId: number, currentLap: number): Promise<any> {
    return this.request<any>(`/api/live/simulate/${sessionId}?current_lap=${currentLap}`);
  }

  async getSessionTiming(sessionId: number, upToLap?: number): Promise<any> {
    const q = upToLap ? `?up_to_lap=${upToLap}` : '';
    return this.request<any>(`/api/live/session/${sessionId}/timing${q}`);
  }

  async startLiveIngest(season: number, intervalSeconds: number = 300): Promise<any> {
    return this.request<any>(`/api/ingest/live/start?season=${season}&interval_seconds=${intervalSeconds}`, {
      method: 'POST',
    });
  }

  // External Data — Jolpica-F1 (Historical Backup)
  async getJolpicaResults(season: number, round?: number): Promise<any> {
    const path = round ? `/api/external/jolpica/results/${season}?round=${round}` : `/api/external/jolpica/results/${season}`;
    return this.request<any>(path);
  }

  async getJolpicaSprints(season: number, round?: number): Promise<any> {
    const path = round ? `/api/external/jolpica/sprints/${season}?round=${round}` : `/api/external/jolpica/sprints/${season}`;
    return this.request<any>(path);
  }

  async getJolpicaDriverStandings(season: number): Promise<any> {
    return this.request<any>(`/api/external/jolpica/standings/drivers/${season}`);
  }

  async getJolpicaConstructorStandings(season: number): Promise<any> {
    return this.request<any>(`/api/external/jolpica/standings/constructors/${season}`);
  }

  async getJolpicaCareerStats(driverId: string): Promise<any> {
    return this.request<any>(`/api/external/jolpica/career/${driverId}`);
  }

  async getJolpicaCircuitHistory(circuitId: string): Promise<any> {
    return this.request<any>(`/api/external/jolpica/circuit-history/${circuitId}`);
  }

  // External Data — OpenF1 (Real-Time Backup)
  async getOpenF1Sessions(year: number, sessionType?: string): Promise<any> {
    const params = sessionType ? `?session_type=${sessionType}` : '';
    return this.request<any>(`/api/external/openf1/sessions?year=${year}${params ? '&' + params.slice(1) : ''}`);
  }

  async getOpenF1Laps(sessionKey: number, driverNumber?: number): Promise<any> {
    const params = driverNumber ? `?driver_number=${driverNumber}` : '';
    return this.request<any>(`/api/external/openf1/laps/${sessionKey}${params}`);
  }

  // Team Radio (Voice Feature)
  async getTeamRadio(sessionKey: number, driverNumber?: number): Promise<any> {
    const params = driverNumber ? `?driver_number=${driverNumber}` : '';
    return this.request<any>(`/api/external/openf1/team-radio/${sessionKey}${params}`);
  }

  async getTeamRadioSummary(sessionKey: number): Promise<any> {
    return this.request<any>(`/api/external/openf1/team-radio-summary/${sessionKey}`);
  }

  async getOpenF1Weather(sessionKey: number): Promise<any> {
    return this.request<any>(`/api/external/openf1/weather/${sessionKey}`);
  }

  async getOpenF1SessionSummary(sessionKey: number): Promise<any> {
    return this.request<any>(`/api/external/openf1/session-summary/${sessionKey}`);
  }

  // OpenF1 — Newly exposed endpoints
  async getOpenF1CarData(sessionKey: number, driverNumber?: number): Promise<any> {
    const params = driverNumber ? `?driver_number=${driverNumber}` : '';
    return this.request<any>(`/api/external/openf1/car-data/${sessionKey}${params}`);
  }

  async getOpenF1Positions(sessionKey: number): Promise<any> {
    return this.request<any>(`/api/external/openf1/positions/${sessionKey}`);
  }

  async getOpenF1Intervals(sessionKey: number): Promise<any> {
    return this.request<any>(`/api/external/openf1/intervals/${sessionKey}`);
  }

  // Prediction — Elo & Boosts
  async getEloRankings(top: number = 30): Promise<any> {
    return this.request<any>(`/api/predictions/elo-rankings?top=${top}`);
  }

  async getEloHeadToHead(driverA: string, driverB: string): Promise<any> {
    return this.request<any>(`/api/predictions/elo-head-to-head?driver_a=${driverA}&driver_b=${driverB}`);
  }

  async getBoostsInfo(): Promise<any> {
    return this.request<any>(`/api/predictions/boosts-info`);
  }

  // Analysis — Enriched endpoints
  async getSpeedTraps(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/speed-traps/${sessionId}`);
  }

  async getRaceIntervals(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/intervals/${sessionId}`);
  }

  async getWeatherCorrelation(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/weather-correlation/${sessionId}`);
  }

  async getPitPerformance(sessionId: number): Promise<any> {
    return this.request<any>(`/api/analysis/pit-performance/${sessionId}`);
  }

  async getDriverComparison(driverA: string, driverB: string, season: number = 2026): Promise<any> {
    return this.request<any>(`/api/analysis/driver-comparison?driver_a=${driverA}&driver_b=${driverB}&season=${season}`);
  }

  // Jolpica-F1 Consolidated Endpoints (integrated with FastF1)
  async getJolpicaF1SeasonData(season: number): Promise<any> {
    return this.request<any>(`/api/external/jolpica-f1/${season}`);
  }

  async getJolpicaF1RoundData(season: number, round: number): Promise<any> {
    return this.request<any>(`/api/external/jolpica-f1/${season}/${round}`);
  }
}

export const api = new ApiClient();
export default api;
