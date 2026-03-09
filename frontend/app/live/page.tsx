'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import Link from 'next/link';
import { Activity, Trophy, Timer, Users, Play, Pause, SkipBack, SkipForward, Flag, Clock } from 'lucide-react';
import api from '@/lib/api';
import { getCurrentOrUpcomingEvent } from '@/lib/utils';
import { getTeamColor } from '@/lib/tracks';

const TYRE_IMG: Record<string, string> = {
  SOFT: '/images/tyres/0.0.png', MEDIUM: '/images/tyres/1.0.png', HARD: '/images/tyres/2.0.png',
  INTERMEDIATE: '/images/tyres/3.0.png', WET: '/images/tyres/4.0.png',
};

const SESSION_LABELS: Record<string, string> = {
  FP1: 'Practice 1', FP2: 'Practice 2', FP3: 'Practice 3',
  Q: 'Qualifying', SQ: 'Sprint Qualifying', S: 'Sprint', R: 'Race',
};
const SESSION_ORDER = ['FP1', 'FP2', 'FP3', 'SQ', 'Q', 'S', 'R'];
const TIMING_TYPES = new Set(['FP1', 'FP2', 'FP3', 'Q', 'SQ']);

const GlassCard = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-white/[0.03] border border-white/[0.06] rounded-2xl ${className}`}>{children}</div>
);

const teamColor = (team: string) => getTeamColor(team) || '#666';

export default function LivePage() {
  const [selectedSeason, setSelectedSeason] = useState(2026);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedSessionType, setSelectedSessionType] = useState('R');
  const [currentLap, setCurrentLap] = useState(1);
  const [autoAdvance, setAutoAdvance] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const { data: seasons } = useQuery({ queryKey: ['seasons'], queryFn: () => api.getSeasons() });
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

  useEffect(() => {
    if (events?.length && !selectedEventId) {
      const target = getCurrentOrUpcomingEvent(events as any[]);
      if (target) setSelectedEventId(target.event_id);
    }
  }, [events, selectedEventId]);

  useEffect(() => {
    if (!events?.length || !seasons?.length) return;

    const hasAnySessionData = events.some((e: any) => (e.session_count || 0) > 0);
    if (hasAnySessionData) return;

    const fallbackSeason = [...seasons]
      .sort((a: number, b: number) => b - a)
      .find((s: number) => s < selectedSeason);

    if (fallbackSeason) {
      setSelectedSeason(fallbackSeason);
      setSelectedEventId(null);
      setCurrentLap(1);
    }
  }, [events, seasons, selectedSeason]);

  useEffect(() => {
    const start = async () => {
      try {
        await api.startLiveIngest(selectedSeason, 120);
      } catch (error) {
        // Non-blocking: page should still render even if ingest start fails.
        console.warn('Failed to start live ingest:', error);
      }
    };

    start();
  }, [selectedSeason]);

  const sortedSessions = useMemo(() => {
    if (!sessions?.length) return [];
    return [...sessions].sort((a: any, b: any) => SESSION_ORDER.indexOf(a.session_type) - SESSION_ORDER.indexOf(b.session_type));
  }, [sessions]);

  useEffect(() => {
    if (sortedSessions.length) {
      const race = sortedSessions.find((s: any) => s.session_type === 'R');
      setSelectedSessionType(race?.session_type || sortedSessions[0].session_type);
      setCurrentLap(1);
    }
  }, [sortedSessions]);

  const activeSession = useMemo(
    () => sessions?.find((s: any) => s.session_type === selectedSessionType),
    [sessions, selectedSessionType]
  );

  const isTimingMode = TIMING_TYPES.has(selectedSessionType);

  const { data: livePredictions, isLoading: predLoading } = useQuery({
    queryKey: ['live-pred', activeSession?.session_id, currentLap],
    queryFn: () => api.getLiveSimulation(activeSession!.session_id, currentLap),
    enabled: !!activeSession?.session_id && !isTimingMode,
    refetchOnWindowFocus: false,
  });

  const { data: timingData, isLoading: timingLoading } = useQuery({
    queryKey: ['timing', activeSession?.session_id, currentLap],
    queryFn: () => api.getSessionTiming(activeSession!.session_id, currentLap),
    enabled: !!activeSession?.session_id && isTimingMode,
    refetchOnWindowFocus: false,
  });

  const totalLaps = isTimingMode ? (timingData?.total_laps_in_session || 20) : (livePredictions?.total_laps || 60);
  const progress = Math.min(100, Math.round((currentLap / Math.max(1, totalLaps)) * 100));

  useEffect(() => {
    if (!autoAdvance) return;
    intervalRef.current = setInterval(() => {
      setCurrentLap((prev) => {
        if (prev >= totalLaps) {
          setAutoAdvance(false);
          return prev;
        }
        return prev + 1;
      });
    }, isTimingMode ? 900 : 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoAdvance, totalLaps, isTimingMode]);

  const loading = isTimingMode ? timingLoading : predLoading;
  const predictions = livePredictions?.predictions || [];
  const timing = timingData?.timing || [];

  return (
    <div className="min-h-screen bg-[#0a0c10] text-white pb-12">
      <div className="max-w-7xl mx-auto px-4 pt-10 pb-8">
        <div className="flex items-center gap-3 mb-2">
          <Activity className="text-red-500" size={26} />
          <h1 className="text-3xl font-black tracking-tight">{isTimingMode ? 'LIVE TIMING' : 'LIVE DATA FROM RACE'}</h1>
          <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold border border-red-500/40 text-red-400 bg-red-600/20">
            {autoAdvance ? 'Live' : 'Ready'}
          </span>
        </div>
        <p className="text-gray-500 text-sm">
          {isTimingMode ? 'Practice/Qualifying lap timing tower (2026 only)' : 'Race predictions that update lap-by-lap'}
        </p>
      </div>

      <div className="max-w-7xl mx-auto px-4 space-y-6">
        <GlassCard className="p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 block">Season</label>
              <select
                value={selectedSeason}
                onChange={(e) => {
                  setSelectedSeason(+e.target.value);
                  setSelectedEventId(null);
                  setCurrentLap(1);
                }}
                className="bg-[#111318] border border-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                {seasons?.map((s: number) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="flex-1 min-w-[220px]">
              <label className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 block">Event</label>
              <select
                value={selectedEventId ?? ''}
                onChange={(e) => { setSelectedEventId(+e.target.value); setCurrentLap(1); }}
                className="w-full bg-[#111318] border border-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Select event...</option>
                {events?.map((e: any) => <option key={e.event_id} value={e.event_id}>{e.event_name}</option>)}
              </select>
            </div>

            <div className="flex-1 min-w-[220px]">
              <label className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 block">Lap {currentLap}/{totalLaps}</label>
              <input type="range" min={1} max={totalLaps} value={currentLap} onChange={(e) => setCurrentLap(+e.target.value)} className="w-full accent-red-500" />
            </div>

            <div className="flex gap-2">
              <button onClick={() => setCurrentLap(Math.max(1, currentLap - 3))} className="p-2 bg-gray-800 rounded-lg"><SkipBack size={16} /></button>
              <button onClick={() => setAutoAdvance((p) => !p)} className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 ${autoAdvance ? 'bg-red-600' : 'bg-green-600'}`}>
                {autoAdvance ? <><Pause size={14} />Pause</> : <><Play size={14} />Play</>}
              </button>
              <button onClick={() => setCurrentLap(Math.min(totalLaps, currentLap + 3))} className="p-2 bg-gray-800 rounded-lg"><SkipForward size={16} /></button>
            </div>
          </div>

          {sortedSessions.length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/[0.06] flex flex-wrap gap-1.5">
              {sortedSessions.map((s: any) => {
                const active = selectedSessionType === s.session_type;
                return (
                  <button
                    key={s.session_id}
                    onClick={() => { setSelectedSessionType(s.session_type); setCurrentLap(1); }}
                    className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border flex items-center gap-1 ${
                      active ? 'bg-red-600 border-red-500 text-white' : 'bg-[#111318] border-gray-700 text-gray-400'
                    }`}
                  >
                    {SESSION_LABELS[s.session_type] || s.session_type}
                  </button>
                );
              })}
            </div>
          )}

          <div className="mt-4 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div className={`h-full ${isTimingMode ? 'bg-purple-500' : 'bg-red-500'}`} style={{ width: `${progress}%` }} />
          </div>
        </GlassCard>

        {!activeSession ? (
          <GlassCard className="p-12 text-center">
            <Flag size={42} className="mx-auto mb-3 text-gray-600" />
            <h2 className="text-xl font-bold text-gray-400">Select an event and session</h2>
          </GlassCard>
        ) : loading ? (
          <GlassCard className="p-12 text-center">
            <div className="inline-block w-10 h-10 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
          </GlassCard>
        ) : isTimingMode ? (
          <GlassCard className="overflow-hidden">
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                <Clock size={16} className="text-purple-400" /> {SESSION_LABELS[selectedSessionType]} Timing
              </h3>
              <span className="text-[11px] text-purple-300">Session Replay</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                    <th className="px-4 py-3 text-left">P</th>
                    <th className="px-4 py-3 text-left">Driver</th>
                    <th className="px-4 py-3 text-left">Team</th>
                    <th className="px-4 py-3 text-center">Best</th>
                    <th className="px-4 py-3 text-center">Gap</th>
                    <th className="px-4 py-3 text-center">Tyre</th>
                    <th className="px-4 py-3 text-center">Laps</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/30">
                  {timing.map((row: any) => (
                    <tr key={row.driver_code} className="hover:bg-white/[0.03]">
                      <td className="px-4 py-3 font-black">{row.position ?? '—'}</td>
                      <td className="px-4 py-3 font-bold">{row.driver_code}</td>
                      <td className="px-4 py-3 text-[11px] text-gray-500">{row.team}</td>
                      <td className="px-4 py-3 text-center font-mono">{row.best_lap_time_fmt}</td>
                      <td className="px-4 py-3 text-center font-mono text-xs text-gray-400">{row.position === 1 ? 'Leader' : (row.gap_to_leader != null ? `+${row.gap_to_leader.toFixed(3)}` : '—')}</td>
                      <td className="px-4 py-3 text-center text-xs text-gray-400">{row.current_tyre || '—'} {row.tyre_age != null ? `(${row.tyre_age}L)` : ''}</td>
                      <td className="px-4 py-3 text-center text-xs text-gray-400">{row.laps_completed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <GlassCard className="p-4"><div className="text-[10px] text-gray-500 uppercase">Leader</div><div className="text-2xl font-black">{predictions[0]?.driver_code || '—'}</div></GlassCard>
              <GlassCard className="p-4"><div className="text-[10px] text-gray-500 uppercase">Win %</div><div className="text-2xl font-black">{((predictions[0]?.win_probability || 0) * 100).toFixed(1)}%</div></GlassCard>
              <GlassCard className="p-4"><div className="text-[10px] text-gray-500 uppercase">Lap</div><div className="text-2xl font-black">{currentLap}/{totalLaps}</div></GlassCard>
              <GlassCard className="p-4"><div className="text-[10px] text-gray-500 uppercase">Drivers</div><div className="text-2xl font-black">{predictions.length}</div></GlassCard>
            </div>

            <GlassCard className="overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06]">
                <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500">Live Prediction Board</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                      <th className="px-4 py-3 text-left">Pos</th>
                      <th className="px-4 py-3 text-left">Driver</th>
                      <th className="px-4 py-3 text-left">Team</th>
                      <th className="px-4 py-3 text-center">Grid</th>
                      <th className="px-4 py-3 text-center">Tyre</th>
                      <th className="px-4 py-3 text-right">Win %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/30">
                    {predictions.map((p: any) => {
                      const compound = p.tyre_compound?.toUpperCase();
                      return (
                        <tr key={p.driver_code} className="hover:bg-white/[0.03]">
                          <td className="px-4 py-3 font-black">P{p.current_position}</td>
                          <td className="px-4 py-3 font-bold">
                            <Link href={`/drivers/${p.driver_code?.toLowerCase()}`}>{p.driver_code}</Link>
                          </td>
                          <td className="px-4 py-3 text-[11px] text-gray-500">{p.team}</td>
                          <td className="px-4 py-3 text-center text-xs text-gray-400">P{p.grid_position}</td>
                          <td className="px-4 py-3 text-center">
                            {compound && TYRE_IMG[compound]
                              ? <Image src={TYRE_IMG[compound]} alt={compound} width={16} height={16} className="inline-block" />
                              : <span className="text-xs text-gray-600">—</span>}
                          </td>
                          <td className="px-4 py-3 text-right font-mono font-bold" style={{ color: teamColor(p.team) }}>
                            {(p.win_probability * 100).toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </>
        )}
      </div>
    </div>
  );
}
