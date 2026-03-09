'use client';

import { useState, useEffect, useRef, useMemo, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import Link from 'next/link';
import {
  Play, Pause, SkipBack, SkipForward, Rewind, FastForward,
  Cloud, Droplets, Wind, Thermometer, Flag, EyeOff,
  Gauge, Timer, Zap,
  HelpCircle, X, Tag, Settings, Loader2,
} from 'lucide-react';
import api from '@/lib/api';
import type {
  ReplayMetadata, ReplayFrame, RaceEvent, DriverFrame,
} from '@/lib/types';
import { getTrackLayout, getTeamColor } from '@/lib/tracks';
import { getCurrentOrUpcomingEvent } from '@/lib/utils';

const TYRE_IMG: Record<string, string> = {
  SOFT: '/images/tyres/0.0.png', MEDIUM: '/images/tyres/1.0.png', HARD: '/images/tyres/2.0.png',
  INTERMEDIATE: '/images/tyres/3.0.png', WET: '/images/tyres/4.0.png',
};

/* ═══════════════════ HELPERS ═══════════════════ */

const fmtTime = (totalSec: number) => {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = Math.floor(totalSec % 60);
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

const fmtLapTime = (seconds?: number | null) => {
  if (!seconds || seconds <= 0 || seconds > 300) return '--:--.---';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toFixed(3).padStart(6, '0')}`;
};

const compoundColor = (c?: string) => {
  switch (c?.toUpperCase()) {
    case 'SOFT': return '#FF3333';
    case 'MEDIUM': return '#FFC800';
    case 'HARD': return '#FFFFFF';
    case 'INTERMEDIATE': return '#43B02A';
    case 'WET': return '#0067AD';
    default: return '#888';
  }
};

const compoundLabel = (c?: string) => {
  switch (c?.toUpperCase()) {
    case 'SOFT': return 'S';
    case 'MEDIUM': return 'M';
    case 'HARD': return 'H';
    case 'INTERMEDIATE': return 'I';
    case 'WET': return 'W';
    default: return '?';
  }
};

/** Estimate tyre health (0-100) based on age and compound */
const tyreDegradation = (compound?: string, age?: number): number => {
  if (!age || age <= 0) return 100;
  const maxLife: Record<string, number> = { SOFT: 18, MEDIUM: 28, HARD: 40, INTERMEDIATE: 25, WET: 30 };
  const max = maxLife[compound?.toUpperCase() ?? ''] ?? 30;
  return Math.max(0, Math.min(100, Math.round((1 - age / max) * 100)));
};

const healthColor = (health: number): string => {
  if (health >= 75) return '#22c55e';
  if (health >= 50) return '#eab308';
  if (health >= 25) return '#f97316';
  return '#ef4444';
};

const windDirection = (deg?: number | null) => {
  if (deg == null) return '';
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(((deg % 360) / 45)) % 8];
};

/* ════════════════════════════════════════════════ */
function ReplayPageContent() {
  const searchParams = useSearchParams();
  const urlSeason = searchParams.get('season');
  const urlEvent = searchParams.get('event');

  /* ── selection state ── */
  const [selectedSeason, setSelectedSeason] = useState(() => {
    if (urlSeason) return parseInt(urlSeason, 10);
    return 2026;
  });
  const [selectedEventId, setSelectedEventId] = useState<number | null>(() => {
    if (urlEvent) return parseInt(urlEvent, 10);
    return null;
  });

  /* ── playback state ── */
  const [isPlaying, setIsPlaying] = useState(false);
  const SPEED_STEPS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const speedUp = () => {
    const idx = SPEED_STEPS.indexOf(playbackSpeed);
    if (idx < SPEED_STEPS.length - 1) setPlaybackSpeed(SPEED_STEPS[idx + 1]);
    else if (idx === -1) setPlaybackSpeed(SPEED_STEPS.find(s => s > playbackSpeed) || 32);
  };
  const speedDown = () => {
    const idx = SPEED_STEPS.indexOf(playbackSpeed);
    if (idx > 0) setPlaybackSpeed(SPEED_STEPS[idx - 1]);
    else if (idx === -1) setPlaybackSpeed([...SPEED_STEPS].reverse().find(s => s < playbackSpeed) || 0.25);
  };
  const [currentLap, setCurrentLap] = useState(1);
  const [subLapProgress, setSubLapProgress] = useState(0);

  /* ── UI toggles (inspired by reference project) ── */
  const [focusedDrivers, setFocusedDrivers] = useState<string[]>([]);
  const [showDriverLabels, setShowDriverLabels] = useState(false);
  const [showDrsZones, setShowDrsZones] = useState(true);
  const isDrsEra = selectedSeason < 2026; // App mode: DRS overlays shown for pre-2026 seasons.
  const [gapMode, setGapMode] = useState<'off' | 'leader' | 'interval'>('off');
  const [showHelp, setShowHelp] = useState(false);
  const [showWeather, setShowWeather] = useState(true);
  const [showTelemetry, setShowTelemetry] = useState(true);

  /* ── "start" gate — hide everything until user presses play ── */
  const [hasStarted, setHasStarted] = useState(false);

  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);
  /* Use state-based ref so DRS recomputes when SVG path mounts */
  const [trackPathEl, setTrackPathEl] = useState<SVGPathElement | null>(null);
  const trackPathRef = useCallback((node: SVGPathElement | null) => {
    setTrackPathEl(node);
  }, []);

  /* ── data queries ── */
  const { data: seasons } = useQuery({
    queryKey: ['seasons'],
    queryFn: () => api.getSeasons(),
  });

  const { data: events } = useQuery({
    queryKey: ['events', selectedSeason],
    queryFn: () => api.getEvents(selectedSeason),
    enabled: !!selectedSeason,
  });

  const { data: sessions } = useQuery({
    queryKey: ['sessions', selectedEventId],
    queryFn: () => api.getSessions(selectedEventId!),
    enabled: !!selectedEventId,
  });

  const raceSession = useMemo(
    () => sessions?.find((s: any) => s.session_type === 'R'),
    [sessions],
  );

  const { data: metadata, isLoading: metaLoading } = useQuery<ReplayMetadata>({
    queryKey: ['replay-meta', raceSession?.session_id],
    queryFn: () => api.getReplayMetadata(raceSession!.session_id),
    enabled: !!raceSession,
  });

  const { data: framesData, isLoading: framesLoading } = useQuery<{
    frames: ReplayFrame[];
    total_laps: number;
    session_id: number;
  }>({
    queryKey: ['replay-frames', raceSession?.session_id],
    queryFn: () =>
      api.getReplayFrames(raceSession!.session_id, 1, 999, 2) as any,
    enabled: !!raceSession,
  });

  const { data: eventsData } = useQuery<{ events: RaceEvent[] }>({
    queryKey: ['replay-events', raceSession?.session_id],
    queryFn: () => api.getRaceEvents(raceSession!.session_id) as any,
    enabled: !!raceSession,
  });

  const { data: weatherData } = useQuery({
    queryKey: ['replay-weather', raceSession?.session_id],
    queryFn: () => api.getSessionWeather(raceSession!.session_id),
    enabled: !!raceSession,
  });

  /* ── derived data ── */
  const totalLaps = framesData?.total_laps ?? metadata?.total_laps ?? 0;
  const allFrames = framesData?.frames ?? [];
  const allEvents = eventsData?.events ?? (eventsData as any) ?? [];
  const weather = weatherData?.weather ?? null;
  const weatherSource = weatherData?.source ?? null;

  const currentFrame = useMemo<ReplayFrame | null>(() => {
    if (!allFrames.length) return null;
    return allFrames.find((f) => f.lap === currentLap) ?? allFrames[0];
  }, [allFrames, currentLap]);

  const leaderboard = useMemo(() => {
    if (!currentFrame?.drivers) return [];
    return [...currentFrame.drivers].sort(
      (a, b) => (a.position ?? 99) - (b.position ?? 99),
    );
  }, [currentFrame]);

  const recentEvents = useMemo(() => {
    if (!Array.isArray(allEvents)) return [];
    return (allEvents as RaceEvent[]).filter(
      (e) => e.lap <= currentLap && e.lap >= currentLap - 5,
    );
  }, [allEvents, currentLap]);

  const eventName =
    metadata?.event_name ??
    events?.find((e: any) => e.event_id === selectedEventId)?.event_name ??
    '';

  const eventCountry =
    events?.find((e: any) => e.event_id === selectedEventId)?.country ?? '';

  const track = useMemo(
    () => getTrackLayout(eventName, eventCountry),
    [eventName, eventCountry],
  );

  /* ── DRS zone sub-paths (rendered along the track curve) ── */
  const drsSubPaths = useMemo(() => {
    if (!trackPathEl || !isDrsEra || !track.drsZones.length) return [];
    const totalLen = trackPathEl.getTotalLength();

    const findNearest = (tx: number, ty: number): number => {
      let best = 0;
      let bestDist = Infinity;
      const steps = 500;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const p = trackPathEl.getPointAtLength(t * totalLen);
        const d = (p.x - tx) ** 2 + (p.y - ty) ** 2;
        if (d < bestDist) { bestDist = d; best = t; }
      }
      const step2 = 1 / (steps * 10);
      for (let t = Math.max(0, best - 5 / steps); t <= Math.min(1, best + 5 / steps); t += step2) {
        const p = trackPathEl.getPointAtLength(t * totalLen);
        const d = (p.x - tx) ** 2 + (p.y - ty) ** 2;
        if (d < bestDist) { bestDist = d; best = t; }
      }
      return best;
    };

    return track.drsZones.map((zone) => {
      const t0 = findNearest(zone.start.x, zone.start.y);
      const t1 = findNearest(zone.end.x, zone.end.y);
      const tStart = Math.min(t0, t1);
      const tEnd = Math.max(t0, t1);

      const pts: string[] = [];
      const segments = 60;
      for (let i = 0; i <= segments; i++) {
        const t = tStart + (tEnd - tStart) * (i / segments);
        const p = trackPathEl.getPointAtLength(t * totalLen);
        pts.push(`${p.x},${p.y}`);
      }
      const midT = (tStart + tEnd) / 2;
      const midP = trackPathEl.getPointAtLength(midT * totalLen);
      return { points: pts.join(' '), mid: midP, startP: trackPathEl.getPointAtLength(tStart * totalLen), endP: trackPathEl.getPointAtLength(tEnd * totalLen) };
    });
  }, [trackPathEl, track.path, isDrsEra, track.drsZones]);

  /* ── Pit lane path (curved line between pit entry and exit via offset) ── */
  const pitLanePath = useMemo(() => {
    const pe = track.pitEntry;
    const px = track.pitExit;
    if (!pe || !px) return '';

    const midX = (pe.x + px.x) / 2;
    const midY = (pe.y + px.y) / 2;
    const dx = px.x - pe.x;
    const dy = px.y - pe.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 1) return '';
    const nx = -dy / len;
    const ny = dx / len;
    const offset = len * 0.25;
    const cx = track.width / 2;
    const cy = track.height / 2;
    const cp1a = { x: midX + nx * offset, y: midY + ny * offset };
    const cp1b = { x: midX - nx * offset, y: midY - ny * offset };
    const distA = (cp1a.x - cx) ** 2 + (cp1a.y - cy) ** 2;
    const distB = (cp1b.x - cx) ** 2 + (cp1b.y - cy) ** 2;
    const cp = distA > distB ? cp1a : cp1b;

    return `M ${pe.x},${pe.y} Q ${cp.x},${cp.y} ${px.x},${px.y}`;
  }, [track]);

  /* ── effects ── */
  // Sync from URL params when they change
  useEffect(() => {
    if (urlSeason) {
      const parsed = parseInt(urlSeason, 10);
      if (!isNaN(parsed) && parsed !== selectedSeason) setSelectedSeason(parsed);
    }
    if (urlEvent) {
      const parsed = parseInt(urlEvent, 10);
      if (!isNaN(parsed) && parsed !== selectedEventId) setSelectedEventId(parsed);
    }
  }, [urlSeason, urlEvent]);

  useEffect(() => {
    // Only auto-select if no URL param was provided
    if (events?.length && !selectedEventId && !urlEvent) {
      const targetEvent = getCurrentOrUpcomingEvent(events as any[]);
      if (targetEvent) setSelectedEventId(targetEvent.event_id);
    }
  }, [events, selectedEventId, urlEvent]);

  useEffect(() => {
    const start = async () => {
      try {
        await api.startLiveIngest(selectedSeason, 120);
      } catch (error) {
        // Non-blocking: replay should still work if ingest trigger fails.
        console.warn('Failed to start live ingest:', error);
      }
    };

    start();
  }, [selectedSeason]);

  useEffect(() => {
    setCurrentLap(1);
    setSubLapProgress(0);
    setIsPlaying(false);
    setHasStarted(false);
    setFocusedDrivers([]);
  }, [selectedEventId]);

  // Smooth animation loop using requestAnimationFrame
  useEffect(() => {
    if (!isPlaying || !allFrames.length) {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      return;
    }

    const animate = (timestamp: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp;
      const delta = timestamp - lastTimeRef.current;
      lastTimeRef.current = timestamp;

      const lapDuration = 1500 / playbackSpeed;
      const progressIncrement = delta / lapDuration;

      setSubLapProgress((prev) => {
        const next = prev + progressIncrement;
        if (next >= 1.0) {
          setCurrentLap((lap) => {
            if (lap >= totalLaps) {
              setIsPlaying(false);
              return lap;
            }
            return lap + 1;
          });
          return next - 1.0;
        }
        return next;
      });

      animFrameRef.current = requestAnimationFrame(animate);
    };

    lastTimeRef.current = 0;
    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isPlaying, playbackSpeed, totalLaps, allFrames.length]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (!hasStarted) setHasStarted(true);
          setIsPlaying((p) => !p);
          break;
        case 'ArrowRight':
          e.preventDefault();
          setCurrentLap((p) => Math.min(totalLaps, p + 5));
          setSubLapProgress(0);
          break;
        case 'ArrowLeft':
          e.preventDefault();
          setCurrentLap((p) => Math.max(1, p - 5));
          setSubLapProgress(0);
          break;
        case 'ArrowUp':
          e.preventDefault();
          speedUp();
          break;
        case 'ArrowDown':
          e.preventDefault();
          speedDown();
          break;
        case 'r':
        case 'R':
          setCurrentLap(1);
          setSubLapProgress(0);
          setIsPlaying(false);
          break;
        case 'd':
        case 'D':
          if (isDrsEra) setShowDrsZones((p) => !p);
          break;
        case 'l':
        case 'L':
          setShowDriverLabels((p) => !p);
          break;
        case 'h':
        case 'H':
          setShowHelp((p) => !p);
          break;
        case 'w':
        case 'W':
          setShowWeather((p) => !p);
          break;
        case 'g':
        case 'G':
          setGapMode((p) => p === 'off' ? 'leader' : p === 'leader' ? 'interval' : 'off');
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [totalLaps]);

  /* ── helpers ── */
  const driverMeta = useCallback(
    (code: string) => metadata?.drivers?.find((d) => d.code === code),
    [metadata],
  );

  const toggleFocus = (code: string) => {
    setFocusedDrivers((prev) =>
      prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code].slice(0, 4),
    );
  };

  const isDriverOut = (code: string) => {
    const m = driverMeta(code);
    if (!m) return false;
    return m.status && m.status !== 'Finished' && !m.status.startsWith('+') && m.status !== '';
  };

  /* ── SVG path driver positioning ── */
  const getDriverPos = useCallback(
    (df: DriverFrame, allDrivers: DriverFrame[]): { x: number; y: number } => {
      if (!trackPathEl) return { x: df.x || 400, y: df.y || 300 };

      const total = allDrivers.length || 20;
      const pos = df.position || 20;

      // Leader is at subLapProgress around the track
      // Each position behind is spread by ~4% of track length
      const positionGap = 0.85 / Math.max(total - 1, 1);
      const offset = (pos - 1) * positionGap;
      const progress = ((subLapProgress - offset) % 1 + 1) % 1;

      const len = trackPathEl.getTotalLength();
      const pt = trackPathEl.getPointAtLength(progress * len);
      return { x: pt.x, y: pt.y };
    },
    [subLapProgress, trackPathEl],
  );

  /** Compute gaps for leaderboard display */
  const getGapText = (df: DriverFrame, idx: number) => {
    if (gapMode === 'off') return null;
    if (gapMode === 'leader') {
      if (df.position === 1) return 'LEAD';
      return df.gap_to_leader > 0 ? `+${df.gap_to_leader.toFixed(1)}s` : '—';
    }
    if (idx === 0) return '—';
    const ahead = leaderboard[idx - 1];
    if (!ahead) return '—';
    const gap = (df.gap_to_leader ?? 0) - (ahead.gap_to_leader ?? 0);
    return gap > 0 ? `+${gap.toFixed(1)}s` : '—';
  };

  /* ── flag segments ── */
  const flagSegments = useMemo(() => {
    if (!Array.isArray(allEvents) || !totalLaps) return [];
    const segs: { lap: number; color: string; label: string }[] = [];
    for (const ev of allEvents as RaceEvent[]) {
      const t = ev.type?.toLowerCase() ?? '';
      const d = ev.details?.toLowerCase() ?? '';
      if (t.includes('safety') || d.includes('safety car')) segs.push({ lap: ev.lap, color: '#FFA500', label: 'SC' });
      else if (t.includes('vsc') || d.includes('virtual')) segs.push({ lap: ev.lap, color: '#FFD700', label: 'VSC' });
      else if (t === 'red_flag') segs.push({ lap: ev.lap, color: '#FF0000', label: 'Red' });
      else if (t === 'dnf' || t === 'retirement') segs.push({ lap: ev.lap, color: '#FFFF00', label: 'DNF' });
    }
    return segs;
  }, [allEvents, totalLaps]);

  /* ════════════════════ RENDER ════════════════════ */
  const loading = metaLoading || framesLoading;

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0a] text-white overflow-hidden select-none">
      {/* TOP BAR */}
      <header className="flex flex-wrap items-center justify-between gap-2 bg-[#111] border-b border-gray-800 px-3 md:px-4 py-2 shrink-0">
        <div className="flex items-center gap-3">
          <div>
            <div className="text-lg md:text-2xl font-black tracking-tight">
              LAP <span className="text-red-500">{currentLap}</span>
              <span className="text-gray-500">/{totalLaps || '—'}</span>
            </div>
          <div className="text-xs text-gray-500 font-mono">
            {currentFrame ? fmtTime(currentFrame.time_elapsed) : '0:00:00'} &middot; {playbackSpeed}x
          </div>
        </div>
        </div>

        {/* Session Info Center */}
        <div className="text-center hidden md:block">
          <div className="text-lg font-bold text-red-500 tracking-wide flex items-center justify-center gap-2">
            <span>🏁</span>
            {eventName || 'Select a Race'}
          </div>
          <div className="text-xs text-gray-500 flex items-center justify-center gap-2">
            <span>📅 {selectedSeason} Season</span>
            {metadata?.season && (
              <>
                <span className="text-gray-700">&middot;</span>
                <span>{totalLaps} Laps</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={selectedSeason}
            onChange={(e) => { setSelectedSeason(+e.target.value); setSelectedEventId(null); }}
            className="bg-[#1a1a1a] border border-gray-700 rounded-md px-2 md:px-3 py-1.5 text-sm focus:outline-none focus:border-red-500 flex-shrink-0"
          >
            {seasons?.map((s: number) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={selectedEventId ?? ''}
            onChange={(e) => setSelectedEventId(+e.target.value)}
            className="bg-[#1a1a1a] border border-gray-700 rounded-md px-2 md:px-3 py-1.5 text-sm max-w-[160px] md:max-w-[240px] flex-1 min-w-0 focus:outline-none focus:border-red-500"
          >
            {events?.map((e: any) => (
              <option key={e.event_id} value={e.event_id}>
                R{e.round}: {e.event_name}{(e.has_sprint || String(e.event_format || '').toLowerCase().includes('sprint')) ? ' • Sprint Weekend' : ''}
              </option>
            ))}
          </select>
          <button onClick={() => setShowHelp(!showHelp)}
            className="p-1.5 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 transition"
            title="Toggle Controls Help (H)">
            <HelpCircle size={16} />
          </button>
        </div>
      </header>

      {/* MAIN 3-COLUMN */}
      <div className="flex flex-1 min-h-0 relative">
        {/* LEFT SIDEBAR - Weather + Telemetry Cards */}
        <aside className="hidden md:block w-72 bg-[#0d0d0d] border-r border-gray-800 overflow-y-auto p-3 space-y-3 shrink-0">

          {/* Weather Panel with real data */}
          {showWeather && (
            <div className="bg-[#151515] rounded-lg p-3 border border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Weather</h3>
                  {weatherSource === 'typical' && (
                    <span className="text-[8px] bg-yellow-600/20 text-yellow-500 px-1.5 py-0.5 rounded font-bold uppercase">Typical</span>
                  )}
                  {weatherSource === 'live' && (
                    <span className="text-[8px] bg-green-600/20 text-green-500 px-1.5 py-0.5 rounded font-bold uppercase">Live</span>
                  )}
                </div>
                <button onClick={() => setShowWeather(false)} className="text-gray-600 hover:text-gray-400">
                  <EyeOff size={12} />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-1.5">
                  <Thermometer size={13} className="text-orange-400" />
                  <span className="text-gray-300">Track</span>
                  <span className="ml-auto font-mono font-bold">{weather?.track_temp ?? '—'}°C</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Thermometer size={13} className="text-blue-400" />
                  <span className="text-gray-300">Air</span>
                  <span className="ml-auto font-mono font-bold">{weather?.air_temp ?? '—'}°C</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Droplets size={13} className="text-blue-500" />
                  <span className="text-gray-300">Humid</span>
                  <span className="ml-auto font-mono font-bold">{weather?.humidity ?? '—'}%</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Wind size={13} className="text-gray-400" />
                  <span className="text-gray-300">Wind</span>
                  <span className="ml-auto font-mono font-bold">
                    {weather?.wind_speed ?? '—'} km/h {windDirection(weather?.wind_direction)}
                  </span>
                </div>
                <div className="col-span-2 flex items-center gap-1.5">
                  <Cloud size={13} className="text-gray-400" />
                  <span className="text-gray-300">Conditions</span>
                  <span className={`ml-auto font-bold ${
                    weather?.conditions === 'WET' ? 'text-blue-400' : 'text-green-400'
                  }`}>{weather?.conditions ?? 'DRY'}</span>
                </div>
                {weather?.pressure && (
                  <div className="col-span-2 flex items-center gap-1.5">
                    <Gauge size={13} className="text-gray-500" />
                    <span className="text-gray-300">Pressure</span>
                    <span className="ml-auto font-mono font-bold text-gray-400">{weather.pressure} hPa</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Track Status Banner */}
          {currentFrame?.track_status && currentFrame.track_status !== 'Green' && (
            <div className={`rounded-lg p-2 text-center text-sm font-bold animate-pulse ${
              currentFrame.track_status === 'Yellow' ? 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/40'
              : currentFrame.track_status === 'Red' ? 'bg-red-600/20 text-red-400 border border-red-600/40'
              : 'bg-blue-600/20 text-blue-400 border border-blue-600/40'
            }`}>⚠ {currentFrame.track_status} Flag</div>
          )}

          {/* Driver Telemetry Cards (enhanced) */}
          {showTelemetry && focusedDrivers.map((code) => {
            const df = currentFrame?.drivers?.find((d) => d.code === code);
            const dm = driverMeta(code);
            const color = dm?.color ?? getTeamColor(dm?.team ?? '');
            const out = isDriverOut(code);
            const health = tyreDegradation(df?.tyre, df?.tyre_age);
            const hColor = healthColor(health);
            const posIdx = leaderboard.findIndex(d => d.code === code);
            const ahead = posIdx > 0 ? leaderboard[posIdx - 1] : null;
            const behind = posIdx < leaderboard.length - 1 ? leaderboard[posIdx + 1] : null;

            return (
              <div key={code} className="rounded-lg overflow-hidden border bg-[#151515] border-gray-800"
                style={{ opacity: out ? 0.4 : 1 }}>
                <div className="px-3 py-1.5 flex items-center justify-between" style={{ backgroundColor: color }}>
                  <span className="text-sm font-black text-black tracking-wide">{code}</span>
                  <button onClick={() => toggleFocus(code)} className="text-black/60 hover:text-black">
                    <X size={14} />
                  </button>
                </div>

                {out ? (
                  <div className="text-center text-red-500 font-bold text-sm py-4 px-3">RETIRED — {dm?.status}</div>
                ) : (
                  <div className="p-3 space-y-2">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase">Speed</div>
                        <div className="text-lg font-black font-mono">{df?.speed ? Math.round(df.speed) : '—'}</div>
                        <div className="text-[9px] text-gray-600">km/h</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase">Gear</div>
                        <div className="text-lg font-black font-mono">{df?.speed ? Math.min(8, Math.max(1, Math.ceil((df.speed || 0) / 40))) : '—'}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase">{isDrsEra ? 'DRS' : 'MOM'}</div>
                        <div className="text-sm font-black text-gray-600">{isDrsEra ? 'OFF' : 'N/A'}</div>
                      </div>
                    </div>

                    <div className="bg-[#1a1a1a] rounded p-2 space-y-0.5 text-[10px]">
                      <div className="flex justify-between text-gray-500">
                        <span>Position</span>
                        <span className="font-bold text-white text-sm">P{df?.position ?? '—'}</span>
                      </div>
                      {ahead && (
                        <div className="flex justify-between text-gray-500">
                          <span>Ahead ({ahead.code})</span>
                          <span className="font-mono text-gray-300">
                            +{((df?.gap_to_leader ?? 0) - (ahead.gap_to_leader ?? 0)).toFixed(2)}s
                          </span>
                        </div>
                      )}
                      {behind && (
                        <div className="flex justify-between text-gray-500">
                          <span>Behind ({behind.code})</span>
                          <span className="font-mono text-gray-300">
                            +{((behind.gap_to_leader ?? 0) - (df?.gap_to_leader ?? 0)).toFixed(2)}s
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Tyre health bar */}
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1.5">
                          {TYRE_IMG[df?.tyre?.toUpperCase() ?? ''] ? (
                            <Image src={TYRE_IMG[df?.tyre?.toUpperCase() ?? '']} alt={df?.tyre ?? 'tyre'} width={22} height={22} className="object-contain" />
                          ) : (
                            <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border border-gray-600"
                              style={{ backgroundColor: compoundColor(df?.tyre), color: df?.tyre?.toUpperCase() === 'HARD' ? '#000' : '#fff' }}>
                              {compoundLabel(df?.tyre)}
                            </span>
                          )}
                          <span className="text-[10px] text-gray-400">{df?.tyre ?? '?'}</span>
                        </div>
                        <span className="text-[10px] text-gray-500 font-mono">{df?.tyre_age ?? 0} laps</span>
                      </div>
                      <div className="w-full h-2.5 bg-[#2a2a2a] rounded-full overflow-hidden border border-gray-700">
                        <div className="h-full rounded-full transition-all duration-300"
                          style={{ width: `${health}%`, backgroundColor: hColor }} />
                      </div>
                      <div className="flex justify-between mt-0.5">
                        <span className="text-[9px]" style={{ color: hColor }}>{health}% health</span>
                        <span className="text-[9px] text-gray-600">
                          {health > 50 ? 'Good' : health > 25 ? 'Degrading' : 'Critical'}
                        </span>
                      </div>
                    </div>

                    <div className="text-center bg-[#1a1a1a] rounded py-1.5">
                      <span className="text-[10px] text-gray-500">Lap Time: </span>
                      <span className="font-mono font-bold text-sm">{fmtLapTime((df as any)?.lap_time)}</span>
                    </div>

                    {/* Throttle / Brake bars */}
                    <div className="flex items-end gap-2 justify-center">
                      <div className="text-center">
                        <div className="w-7 h-14 bg-[#1a1a1a] rounded overflow-hidden relative border border-gray-800">
                          <div className="absolute bottom-0 w-full bg-green-500 transition-all duration-150"
                            style={{ height: `${Math.min(100, Math.max(0, ((df?.speed ?? 0) / 350) * 100))}%` }} />
                        </div>
                        <div className="text-[8px] text-gray-600 mt-0.5">THR</div>
                      </div>
                      <div className="text-center">
                        <div className="w-7 h-14 bg-[#1a1a1a] rounded overflow-hidden relative border border-gray-800">
                          <div className="absolute bottom-0 w-full bg-red-500 transition-all duration-150"
                            style={{ height: `${Math.max(0, 100 - ((df?.speed ?? 0) / 350) * 100)}%` }} />
                        </div>
                        <div className="text-[8px] text-gray-600 mt-0.5">BRK</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {focusedDrivers.length === 0 && (
            <div className="text-center text-gray-600 text-xs py-6">
              Click a driver in the leaderboard<br />to view detailed telemetry<br />
              <span className="text-gray-700">(up to 4 drivers)</span>
            </div>
          )}

          {recentEvents.length > 0 && (
            <div className="bg-[#151515] rounded-lg p-3 border border-gray-800">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">Race Feed</h3>
              <div className="space-y-1">
                {recentEvents.slice(-5).reverse().map((ev, i) => (
                  <div key={i} className={`text-[11px] px-2 py-1 rounded ${
                    ev.type === 'dnf' ? 'bg-red-900/30 text-red-300'
                    : ev.type === 'pit_stop' ? 'bg-blue-900/30 text-blue-300'
                    : ev.type === 'overtake' ? 'bg-green-900/30 text-green-300'
                    : 'bg-gray-800/50 text-gray-400'
                  }`}>
                    <span className="font-bold">L{ev.lap}</span> {ev.details}
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* CENTER: Track Map */}
        <main className="flex-1 relative bg-[#0a0a0a] overflow-hidden">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <div className="text-gray-400">Loading race data...</div>
              </div>
            </div>
          ) : !currentFrame ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Flag size={48} className="mx-auto mb-3 opacity-30" />
                <div className="text-lg font-bold">No Race Data</div>
                <div className="text-sm">Select a season and event to start the replay</div>
              </div>
            </div>
          ) : !hasStarted ? (
            /* ── PRE-START SCREEN — hidden until play is pressed ── */
            <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[#0a0a0a] via-[#111] to-[#0a0a0a]">
              <div className="text-center space-y-6">
                <div className="text-6xl animate-pulse">🏁</div>
                <div className="text-3xl font-black tracking-tight text-white">
                  {eventName}
                </div>
                <div className="text-gray-500 text-sm">
                  {selectedSeason} Season &middot; {totalLaps} Laps
                </div>
                <button
                  onClick={() => { setHasStarted(true); setIsPlaying(true); }}
                  className="px-8 py-4 bg-red-600 hover:bg-red-700 rounded-2xl text-xl font-bold tracking-wide transition-all shadow-xl shadow-red-900/40 active:scale-95 hover:scale-105"
                >
                  <Play size={28} className="inline mr-2 -mt-1" />
                  START RACE
                </button>
                <div className="text-gray-600 text-xs">
                  or press <kbd className="bg-gray-800 px-2 py-0.5 rounded text-gray-400 border border-gray-700">SPACE</kbd> to begin
                </div>
              </div>
            </div>
          ) : (
            <svg viewBox={`0 0 ${track.width} ${track.height}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
              <defs>
                {/* Track surface gradient */}
                <linearGradient id="trackSurface" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#2d2d2d" />
                  <stop offset="100%" stopColor="#1e1e1e" />
                </linearGradient>
                {/* DRS zone glow */}
                <filter id="drsGlow">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
                {/* Kerb pattern red/white */}
                <pattern id="kerbPattern" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
                  <rect width="4" height="8" fill="#e00" />
                  <rect x="4" width="4" height="8" fill="#fff" />
                </pattern>
              </defs>

              {/* Grass/runoff area beneath track */}
              <path d={track.path} fill="none" stroke="#1a2618" strokeWidth={42} strokeLinecap="round" strokeLinejoin="round" opacity={0.4} />

              {/* Outer edge (kerb/barrier line) */}
              <path d={track.path} fill="none" stroke="#444" strokeWidth={30} strokeLinecap="round" strokeLinejoin="round" />

              {/* Track surface */}
              <path d={track.path} fill="none" stroke="url(#trackSurface)" strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" />

              {/* Inner white edge lines */}
              <path d={track.path} fill="none" stroke="#555" strokeWidth={23} strokeLinecap="round" strokeLinejoin="round" opacity={0.3} />
              <path d={track.path} fill="none" stroke="#1e1e1e" strokeWidth={20} strokeLinecap="round" strokeLinejoin="round" />

              {/* Measurement path (invisible) */}
              <path ref={trackPathRef} d={track.path} fill="none" stroke="transparent" strokeWidth={0} />

              {/* Center dashed line */}
              <path d={track.path} fill="none" stroke="#444" strokeWidth={0.8} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="6,10" />

              {/* DRS zones rendered along the track curve — hidden for 2026+ */}
              {isDrsEra && showDrsZones && drsSubPaths.map((drs, i) => (
                <g key={`drs-${i}`} filter="url(#drsGlow)">
                  {/* Wide glow along the track */}
                  <polyline points={drs.points} fill="none"
                    stroke="#00cc44" strokeWidth={24} opacity={0.12} strokeLinecap="round" strokeLinejoin="round" />
                  {/* Bright edge lines following the curve */}
                  <polyline points={drs.points} fill="none"
                    stroke="#00ff55" strokeWidth={2.5} opacity={0.7} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="8,4" />
                  {/* DRS label at midpoint */}
                  <text x={drs.mid.x} y={drs.mid.y - 16}
                    textAnchor="middle" fill="#00ff55" fontSize="9" fontWeight="bold" opacity={0.8}>
                    DRS ZONE {i + 1}
                  </text>
                  {/* Activation marker (green) */}
                  <circle cx={drs.startP.x} cy={drs.startP.y} r={5} fill="#00ff55" opacity={0.7} />
                  <text x={drs.startP.x} y={drs.startP.y - 10} textAnchor="middle" fill="#00ff55" fontSize="6" opacity={0.6}>OPEN</text>
                  {/* Deactivation marker (red) */}
                  <circle cx={drs.endP.x} cy={drs.endP.y} r={5} fill="#ff4444" opacity={0.7} />
                  <text x={drs.endP.x} y={drs.endP.y - 10} textAnchor="middle" fill="#ff4444" fontSize="6" opacity={0.6}>CLOSE</text>
                </g>
              ))}

              {/* Corner markers with kerb styling */}
              {track.corners.map((c) => (
                <g key={`c-${c.number}`}>
                  {/* Kerb indicator */}
                  <circle cx={c.x} cy={c.y} r={12} fill="none" stroke="#d32f2f" strokeWidth={1.5} opacity={0.3} strokeDasharray="3,3" />
                  <circle cx={c.x} cy={c.y} r={9} fill="#181818" stroke="#555" strokeWidth={0.8} />
                  <text x={c.x} y={c.y + 3.5} textAnchor="middle" fill="#aaa" fontSize="8" fontWeight="bold" fontFamily="monospace">{c.number}</text>
                  {c.name && (
                    <text x={c.x} y={c.y - 16} textAnchor="middle" fill="#666" fontSize="7" fontWeight="500">
                      {c.name}
                    </text>
                  )}
                </g>
              ))}

              {/* Start/finish line — professional checkered marker */}
              <g>
                <line x1={track.startFinish.x - 18} y1={track.startFinish.y}
                  x2={track.startFinish.x + 18} y2={track.startFinish.y}
                  stroke="white" strokeWidth={3} opacity={0.6} />
                <rect x={track.startFinish.x - 12} y={track.startFinish.y - 12} width={24} height={24}
                  rx={3} fill="#111" stroke="#fff" strokeWidth={1.5} opacity={0.9} />
                {[0, 1, 2, 3].map(row => [0, 1, 2, 3].map(col => (
                  <rect key={`sf-${row}-${col}`}
                    x={track.startFinish.x - 10 + col * 5} y={track.startFinish.y - 10 + row * 5}
                    width={5} height={5}
                    fill={(row + col) % 2 === 0 ? 'white' : '#111'} opacity={0.85} />
                )))}
                <text x={track.startFinish.x} y={track.startFinish.y + 24} textAnchor="middle"
                  fill="#ccc" fontSize="7" fontWeight="bold" letterSpacing="1">S/F</text>
              </g>

              {/* Sector boundary markers */}
              {track.sectorBoundaries.map((sec, i) => (
                <g key={`sec-${i}`}>
                  <line x1={sec.x - 10} y1={sec.y - 10} x2={sec.x + 10} y2={sec.y + 10}
                    stroke={i === 0 ? '#FFD700' : '#FF6B00'} strokeWidth={1.5} opacity={0.5} />
                  <circle cx={sec.x} cy={sec.y} r={3} fill={i === 0 ? '#FFD700' : '#FF6B00'} opacity={0.6} />
                  <text x={sec.x + 14} y={sec.y + 4} fill={i === 0 ? '#FFD700' : '#FF6B00'} fontSize="7" fontWeight="bold" opacity={0.7}>S{i + 2}</text>
                </g>
              ))}

              {/* Pit lane — accurate curved path */}
              {pitLanePath && (
                <g>
                  {/* Pit lane surface */}
                  <path d={pitLanePath} fill="none" stroke="#1a3050" strokeWidth={8} strokeLinecap="round" opacity={0.5} />
                  {/* Pit lane center line */}
                  <path d={pitLanePath} fill="none" stroke="#3388cc" strokeWidth={1.5} strokeDasharray="6,4" opacity={0.5} />
                  {/* Pit lane edge lines */}
                  <path d={pitLanePath} fill="none" stroke="#1a5fb4" strokeWidth={9} strokeLinecap="round" opacity={0.15} />
                </g>
              )}
              <g>
                <circle cx={track.pitEntry.x} cy={track.pitEntry.y} r={6} fill="#1a5fb4" opacity={0.6} stroke="#3388cc" strokeWidth={1} />
                <text x={track.pitEntry.x} y={track.pitEntry.y - 12} textAnchor="middle" fill="#4488cc" fontSize="7" fontWeight="bold">PIT IN</text>
              </g>
              <g>
                <circle cx={track.pitExit.x} cy={track.pitExit.y} r={6} fill="#1a5fb4" opacity={0.6} stroke="#3388cc" strokeWidth={1} />
                <text x={track.pitExit.x} y={track.pitExit.y - 12} textAnchor="middle" fill="#4488cc" fontSize="7" fontWeight="bold">PIT OUT</text>
              </g>

              {/* Track name watermark */}
              <text x={track.width / 2} y={track.height - 12} textAnchor="middle"
                fill="#222" fontSize="10" fontWeight="bold" letterSpacing="2"
                fontFamily="monospace" opacity={0.5}>
                {track.name.toUpperCase()}
              </text>

              {/* DRIVER DOTS enhanced */}
              {leaderboard.map((df) => {
                const dm = driverMeta(df.code);
                const color = dm?.color ?? getTeamColor(dm?.team ?? '');
                const isFocused = focusedDrivers.includes(df.code);
                const out = isDriverOut(df.code);
                const pos = getDriverPos(df, leaderboard);

                return (
                  <g key={df.code} className="cursor-pointer" onClick={() => toggleFocus(df.code)} opacity={out ? 0.25 : 1}>
                    {isFocused && (
                      <>
                        <circle cx={pos.x} cy={pos.y} r={18} fill="none" stroke={color} strokeWidth={2} opacity={0.7}>
                          <animate attributeName="r" values="16;20;16" dur="2s" repeatCount="indefinite" />
                        </circle>
                        <circle cx={pos.x} cy={pos.y} r={14} fill={color} opacity={0.15} />
                      </>
                    )}
                    <circle cx={pos.x} cy={pos.y} r={isFocused ? 13 : 10} fill={color}
                      stroke={isFocused ? '#fff' : '#000'} strokeWidth={isFocused ? 2.5 : 1.5} />
                    <text x={pos.x} y={pos.y + 3.5} textAnchor="middle" fill="#fff"
                      fontSize={isFocused ? '8' : '7'} fontWeight="bold" fontFamily="monospace"
                      style={{ pointerEvents: 'none' }}>{df.code}</text>
                    {isFocused && (
                      <text x={pos.x} y={pos.y - 18} textAnchor="middle" fill={color} fontSize="9" fontWeight="bold">
                        P{df.position}
                      </text>
                    )}
                    {showDriverLabels && !isFocused && (
                      <text x={pos.x} y={pos.y - 14} textAnchor="middle" fill="#999" fontSize="7"
                        style={{ pointerEvents: 'none' }}>{df.code}</text>
                    )}
                    {df.tyre && !out && (
                      <circle cx={pos.x + 10} cy={pos.y - 8} r={3.5}
                        fill={compoundColor(df.tyre)} stroke="#000" strokeWidth={0.5} />
                    )}
                  </g>
                );
              })}
            </svg>
          )}

          {/* Overlays */}
          <div className="absolute top-3 right-3 bg-red-600/90 backdrop-blur-sm text-white px-4 py-1.5 rounded-lg">
            <span className="text-xl font-black">LAP {currentLap}</span>
            <span className="text-gray-200 text-sm"> / {totalLaps}</span>
          </div>

          {currentFrame?.track_status && currentFrame.track_status !== 'Green' && (
            <div className="absolute top-3 left-3 bg-yellow-600/90 backdrop-blur-sm text-black px-3 py-1.5 rounded-lg font-bold text-sm animate-pulse">
              ⚠ {currentFrame.track_status}
            </div>
          )}

          {/* Toggle buttons overlay */}
          <div className="absolute bottom-3 left-3 flex flex-col gap-1">
            {isDrsEra ? (
              <button onClick={() => setShowDrsZones(!showDrsZones)}
                className={`flex items-center gap-1 text-[9px] px-2 py-1 rounded transition ${
                  showDrsZones ? 'bg-green-600/30 text-green-400 border border-green-600/40' : 'bg-gray-800/60 text-gray-500 border border-gray-700'
                }`}>
                <Zap size={10} /> DRS Zones [D]
              </button>
            ) : (
              <div className="flex items-center gap-1 text-[9px] px-2 py-1 rounded bg-gray-800/60 text-gray-500 border border-gray-700 cursor-default" title="DRS overlay is disabled for 2026+ in this replay mode">
                <Zap size={10} /> DRS Overlay Off (2026+)
              </div>
            )}
            <button onClick={() => setShowDriverLabels(!showDriverLabels)}
              className={`flex items-center gap-1 text-[9px] px-2 py-1 rounded transition ${
                showDriverLabels ? 'bg-blue-600/30 text-blue-400 border border-blue-600/40' : 'bg-gray-800/60 text-gray-500 border border-gray-700'
              }`}>
              <Tag size={10} /> Labels [L]
            </button>
            <button onClick={() => setShowWeather(!showWeather)}
              className={`flex items-center gap-1 text-[9px] px-2 py-1 rounded transition ${
                showWeather ? 'bg-cyan-600/30 text-cyan-400 border border-cyan-600/40' : 'bg-gray-800/60 text-gray-500 border border-gray-700'
              }`}>
              <Cloud size={10} /> Weather [W]
            </button>
            <button onClick={() => setGapMode(g => g === 'off' ? 'leader' : g === 'leader' ? 'interval' : 'off')}
              className={`flex items-center gap-1 text-[9px] px-2 py-1 rounded transition ${
                gapMode !== 'off' ? 'bg-purple-600/30 text-purple-400 border border-purple-600/40' : 'bg-gray-800/60 text-gray-500 border border-gray-700'
              }`}>
              <Timer size={10} /> Gaps: {gapMode === 'off' ? 'Off' : gapMode === 'leader' ? 'Leader' : 'Interval'} [G]
            </button>
          </div>
        </main>

        {/* RIGHT: Leaderboard (enhanced) */}
        <aside className="hidden lg:block w-60 bg-[#0d0d0d] border-l border-gray-800 overflow-y-auto shrink-0">
          <div className="sticky top-0 bg-[#0d0d0d] z-10 px-3 py-2 border-b border-gray-800">
            <div className="flex items-center justify-between">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Leaderboard</h3>
              <div className="flex gap-1">
                <button onClick={() => setGapMode(g => g === 'interval' ? 'off' : 'interval')}
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold border transition ${
                    gapMode === 'interval' ? 'bg-green-600/50 border-green-500 text-white' : 'bg-gray-700 border-gray-600 text-gray-400'
                  }`} title="Interval gaps">I</button>
                <button onClick={() => setGapMode(g => g === 'leader' ? 'off' : 'leader')}
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold border transition ${
                    gapMode === 'leader' ? 'bg-green-600/50 border-green-500 text-white' : 'bg-gray-700 border-gray-600 text-gray-400'
                  }`} title="Leader gaps">L</button>
              </div>
            </div>
          </div>

          {leaderboard.map((df, idx) => {
            const dm = driverMeta(df.code);
            const color = dm?.color ?? getTeamColor(dm?.team ?? '');
            const out = isDriverOut(df.code);
            const isFocused = focusedDrivers.includes(df.code);
            const health = tyreDegradation(df.tyre, df.tyre_age);
            const gapText = getGapText(df, idx);

            return (
              <div key={df.code} onClick={() => toggleFocus(df.code)}
                className={`flex items-center gap-1.5 px-2 py-1.5 cursor-pointer border-b border-gray-800/50 transition-colors ${
                  isFocused ? 'bg-gray-800/60' : 'hover:bg-gray-800/30'} ${out ? 'opacity-40' : ''}`}>
                <span className="text-xs font-bold w-5 text-right text-gray-500 font-mono">{df.position}</span>
                <div className="w-1 h-5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                <span className="font-bold text-sm flex-1" style={{ color: isFocused ? color : '#ccc' }}>{df.code}</span>

                {df.tyre && !out && (
                  <div className="flex items-center gap-0.5">
                    <span className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold shrink-0"
                      style={{
                        backgroundColor: compoundColor(df.tyre),
                        color: df.tyre?.toUpperCase() === 'HARD' ? '#000' : '#fff',
                        opacity: 0.3 + (health / 100) * 0.7,
                      }}>
                      {compoundLabel(df.tyre)}
                    </span>
                    {df.tyre_age > 0 && (
                      <span className="text-[8px] text-gray-600 font-mono w-3">{df.tyre_age}</span>
                    )}
                  </div>
                )}

                {out ? (
                  <span className="text-[10px] font-bold text-red-500 w-14 text-right">OUT</span>
                ) : gapText ? (
                  <span className="text-[10px] text-gray-500 font-mono w-14 text-right">{gapText}</span>
                ) : (
                  <span className="text-[10px] text-gray-500 font-mono w-14 text-right">
                    {df.position === 1 ? 'LEAD' : df.gap_to_leader > 0 ? `+${df.gap_to_leader.toFixed(1)}s` : '—'}
                  </span>
                )}
              </div>
            );
          })}

          {currentLap === 1 && leaderboard.length > 0 && (
            <div className="text-center text-yellow-500/70 text-[10px] py-2 px-3">
              ⚠ May be inaccurate during Lap 1
            </div>
          )}
        </aside>

        {/* CONTROLS HELP POPUP */}
        {showHelp && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={() => setShowHelp(false)}>
            <div className="bg-[#1a1a1a] border border-gray-700 rounded-xl p-5 w-[90vw] max-w-[380px] shadow-2xl"
              onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Settings size={18} /> Controls
                </h2>
                <button onClick={() => setShowHelp(false)} className="text-gray-500 hover:text-white">
                  <X size={18} />
                </button>
              </div>
              <div className="space-y-2">
                {[
                  ['SPACE', 'Pause / Resume'],
                  ['← / →', 'Jump back / forward 5 laps'],
                  ['↑ / ↓', 'Speed increase / decrease'],
                  ['R', 'Restart race'],
                  ['D', isDrsEra ? 'Toggle DRS Zones' : 'DRS overlay disabled for 2026+'],
                  ['L', 'Toggle Driver Labels'],
                  ['W', 'Toggle Weather Panel'],
                  ['G', 'Cycle Gap Mode (Off → Leader → Interval)'],
                  ['H', 'Toggle this Help Popup'],
                ].map(([key, desc]) => (
                  <div key={key} className="flex items-center gap-3">
                    <kbd className="bg-gray-800 text-gray-300 px-2 py-0.5 rounded text-sm font-mono font-bold min-w-[60px] text-center border border-gray-700">
                      {key}
                    </kbd>
                    <span className="text-gray-400 text-sm">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* BOTTOM: Progress Bar + Controls */}
      <footer className="bg-[#111] border-t border-gray-800 px-4 py-2 shrink-0">
        <div className="relative h-6 bg-[#1a1a1a] rounded-full mb-2 cursor-pointer overflow-hidden group"
          onClick={(e) => {
            if (!totalLaps) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const frac = (e.clientX - rect.left) / rect.width;
            setCurrentLap(Math.max(1, Math.min(totalLaps, Math.round(frac * totalLaps))));
            setSubLapProgress(0);
          }}>
          {flagSegments.map((seg, i) => (
            <div key={i} className="absolute top-0 h-full" style={{
              left: `${((seg.lap - 1) / Math.max(totalLaps, 1)) * 100}%`,
              width: `${Math.max(0.5, (1 / Math.max(totalLaps, 1)) * 100)}%`,
              backgroundColor: seg.color, opacity: 0.4,
            }} />
          ))}
          <div className="h-full bg-gradient-to-r from-red-600 to-red-500 rounded-full relative"
            style={{ width: `${((currentLap - 1 + subLapProgress) / Math.max(totalLaps, 1)) * 100}%`, transition: 'none' }}>
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg border-2 border-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          {totalLaps <= 80 && Array.from({ length: Math.floor(totalLaps / 10) }, (_, i) => (i + 1) * 10).map((lap) => (
            <div key={lap} className="absolute top-0 h-full w-px bg-gray-700" style={{ left: `${(lap / totalLaps) * 100}%` }}>
              <span className="absolute -bottom-3.5 left-1/2 -translate-x-1/2 text-[8px] text-gray-600">{lap}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-center md:justify-between gap-2">
          <div className="flex gap-3 text-[9px] text-gray-600 hidden md:flex w-40">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-500"></span> Yellow</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500"></span> Red</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-orange-500"></span> SC</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-300"></span> VSC</span>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={() => { setCurrentLap(Math.max(1, currentLap - 5)); setSubLapProgress(0); }}
              className="p-2 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 transition active:scale-95" title="Rewind 5 laps">
              <Rewind size={16} />
            </button>
            <button onClick={() => { setCurrentLap(Math.max(1, currentLap - 1)); setSubLapProgress(0); }}
              className="p-2 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 transition active:scale-95" title="Previous lap">
              <SkipBack size={16} />
            </button>
            <button onClick={() => setIsPlaying(!isPlaying)}
              className="p-3 rounded-full bg-red-600 hover:bg-red-700 transition shadow-lg shadow-red-900/30 active:scale-95"
              title={isPlaying ? 'Pause' : 'Play'}>
              {isPlaying ? <Pause size={20} /> : <Play size={20} />}
            </button>
            <button onClick={() => { setCurrentLap(Math.min(totalLaps || 999, currentLap + 1)); setSubLapProgress(0); }}
              className="p-2 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 transition active:scale-95" title="Next lap">
              <SkipForward size={16} />
            </button>
            <button onClick={() => { setCurrentLap(Math.min(totalLaps || 999, currentLap + 5)); setSubLapProgress(0); }}
              className="p-2 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 transition active:scale-95" title="Forward 5 laps">
              <FastForward size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1.5 justify-end flex-wrap">
            <button onClick={speedDown}
              className="w-7 h-7 rounded bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 text-sm font-bold transition active:scale-95">−</button>
            {SPEED_STEPS.slice(0, 5).map((s) => (
              <button key={s} onClick={() => setPlaybackSpeed(s)}
                className={`hidden sm:block px-1.5 py-1 rounded text-[10px] font-bold transition ${
                  playbackSpeed === s ? 'bg-red-600 text-white' : 'bg-[#1a1a1a] text-gray-500 hover:text-white border border-gray-800'
                }`}>{s}x</button>
            ))}
            <span className="text-sm font-mono font-bold w-10 text-center text-red-400">{playbackSpeed}x</span>
            <button onClick={speedUp}
              className="w-7 h-7 rounded bg-[#1a1a1a] hover:bg-[#252525] border border-gray-800 text-sm font-bold transition active:scale-95">+</button>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* Loading fallback for Suspense */
function ReplayLoading() {
  return (
    <div className="min-h-screen bg-[#080a0f] flex items-center justify-center">
      <div className="text-center">
        <Loader2 size={48} className="animate-spin text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Loading Race Replay</h2>
        <p className="text-gray-500 text-sm">Preparing telemetry data...</p>
      </div>
    </div>
  );
}

/* Export with Suspense boundary for useSearchParams */
export default function ReplayPage() {
  return (
    <Suspense fallback={<ReplayLoading />}>
      <ReplayPageContent />
    </Suspense>
  );
}
