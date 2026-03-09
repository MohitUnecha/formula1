'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import {
  BarChart3, TrendingUp, Timer, Gauge, Fuel, Flag,
  Activity, Layers, Zap, Target,
  Trophy, Clock, ArrowUpRight, ArrowDownRight, Minus,
  Users, Wind,
} from 'lucide-react';
import api from '@/lib/api';
import { getTeamColor } from '@/lib/tracks';

/* ── Tyre compound images ── */
const TYRE_IMG: Record<string, string> = {
  SOFT: '/images/tyres/0.0.png', MEDIUM: '/images/tyres/1.0.png', HARD: '/images/tyres/2.0.png',
  INTERMEDIATE: '/images/tyres/3.0.png', WET: '/images/tyres/4.0.png',
};

/* ── Tyre compound colors ── */
const TYRE_COLORS: Record<string, string> = {
  SOFT: '#FF3333',
  MEDIUM: '#FFC800',
  HARD: '#FFFFFF',
  INTERMEDIATE: '#43B02A',
  WET: '#0067AD',
};

const TYRE_SHORT: Record<string, string> = {
  SOFT: 'S',
  MEDIUM: 'M',
  HARD: 'H',
  INTERMEDIATE: 'I',
  WET: 'W',
};

function isValidLap(seconds: number | null | undefined): boolean {
  return !!seconds && seconds > 0 && seconds < 300;
}

function fmtLap(seconds: number | null | undefined): string {
  if (!isValidLap(seconds)) return '—';
  const m = Math.floor(seconds! / 60);
  const s = seconds! % 60;
  return `${m}:${s.toFixed(3).padStart(6, '0')}`;
}

/* ═══════════════════════════════════════════ */
export default function AnalyticsPage() {
  const [selectedSeason, setSelectedSeason] = useState(2026);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'laptimes' | 'positions' | 'tyres' | 'telemetry'>('overview');
  const [selectedDrivers, setSelectedDrivers] = useState<string[]>([]);
  const [telemetryDriver, setTelemetryDriver] = useState('');

  /* ── Base queries ── */
  const { data: seasons } = useQuery({
    queryKey: ['seasons'],
    queryFn: () => api.getSeasons(),
    staleTime: 1000 * 60 * 60,
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

  /* ── Analysis queries ── */
  const { data: lapTimeData, isLoading: lapLoading } = useQuery({
    queryKey: ['lap-times', raceSession?.session_id],
    queryFn: () => api.getLapTimeAnalysis(raceSession!.session_id),
    enabled: !!raceSession,
  });

  const { data: positionData, isLoading: posLoading } = useQuery({
    queryKey: ['positions', raceSession?.session_id],
    queryFn: () => api.getPositionChanges(raceSession!.session_id),
    enabled: !!raceSession,
  });

  const { data: tyreData, isLoading: tyreLoading } = useQuery({
    queryKey: ['tyre-strategy', raceSession?.session_id],
    queryFn: () => api.getTyreStrategy(raceSession!.session_id),
    enabled: !!raceSession,
  });

  const { data: telemetryData, isLoading: telLoading } = useQuery({
    queryKey: ['telemetry', raceSession?.session_id, telemetryDriver],
    queryFn: () => api.getTelemetry(raceSession!.session_id, telemetryDriver),
    enabled: !!raceSession && activeTab === 'telemetry' && !!telemetryDriver,
  });

  const { data: weatherData } = useQuery({
    queryKey: ['replay-weather', raceSession?.session_id],
    queryFn: () => api.getSessionWeather(raceSession!.session_id),
    enabled: !!raceSession,
  });

  /* ── Auto-select ── */
  const currentEvent = events?.find((e: any) => e.event_id === selectedEventId);
  const drivers = lapTimeData?.drivers || [];
  const posDrivers = positionData?.drivers || {};
  const strategies = tyreData?.strategies || [];
  const tLaps = telemetryData?.laps || [];
  const weather = weatherData?.weather ?? null;

  const handleSeasonChange = (s: number) => {
    setSelectedSeason(s);
    setSelectedEventId(null);
    setSelectedDrivers([]);
    setTelemetryDriver('');
  };

  const handleEventChange = (id: number) => {
    setSelectedEventId(id);
    setSelectedDrivers([]);
    setTelemetryDriver('');
  };

  /* ── Computed race stats ── */
  const raceStats = useMemo(() => {
    if (!drivers.length) return null;
    const validDrivers = drivers.filter((d: any) => isValidLap(d.best_lap_time));
    const sorted = [...validDrivers].sort((a: any, b: any) => a.best_lap_time - b.best_lap_time);
    const fastest = sorted[0];
    const totalLaps = drivers.reduce((s: number, d: any) => s + (d.total_laps || 0), 0);
    const dnfCount = drivers.filter((d: any) => !isValidLap(d.best_lap_time) && d.total_laps > 0).length;
    const dnsCount = drivers.filter((d: any) => d.total_laps === 0).length;
    const finishers = drivers.length - dnfCount - dnsCount;
    const avgPitStops = strategies.length > 0
      ? (strategies.reduce((s: number, d: any) => s + (d.total_pit_stops || 0), 0) / strategies.length).toFixed(1)
      : '—';

    return { fastest, totalLaps, dnfCount, dnsCount, finishers, avgPitStops, sorted };
  }, [drivers, strategies]);

  /* ═══════════════════ RENDER ═══════════════════ */
  return (
    <div className="space-y-6">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1a0a2e] via-[#16213e] to-[#0a1628] p-5 md:p-10 lg:p-14 border border-purple-900/30">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-80 h-80 bg-purple-500 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 left-0 w-60 h-60 bg-cyan-500 rounded-full blur-[100px]" />
        </div>
        <div className="absolute top-4 right-4 flex gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" style={{ animationDelay: '0.3s' }} />
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" style={{ animationDelay: '0.6s' }} />
        </div>
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-bold text-purple-300 mb-4 border border-purple-500/20">
            <Activity size={14} />
            RACE ANALYTICS ENGINE
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white mb-3 tracking-tight">
            {currentEvent ? currentEvent.event_name : 'Race Analytics'}
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl">
            {currentEvent
              ? `Round ${currentEvent.round} · ${selectedSeason} Season`
              : 'Lap times, position changes, tyre strategies, and telemetry from every race.'}
          </p>
        </div>
      </section>

      {/* Controls */}
      <section className="bg-[#111318] border border-gray-800 rounded-xl p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-purple-400 font-bold mb-2">Season</label>
            <select
              className="w-full bg-[#0a0c10] border border-gray-800 rounded-lg px-4 py-2.5 text-white font-bold focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500/20 transition"
              value={selectedSeason}
              onChange={(e) => handleSeasonChange(parseInt(e.target.value))}
            >
              {seasons
                ? [...seasons].sort((a: number, b: number) => b - a).map((s: number) => (
                    <option key={s} value={s}>{s}</option>
                  ))
                : <option value={2025}>2025</option>
              }
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-purple-400 font-bold mb-2">Grand Prix</label>
            <select
              className="w-full bg-[#0a0c10] border border-gray-800 rounded-lg px-4 py-2.5 text-white font-bold focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500/20 transition"
              value={selectedEventId ?? ''}
              onChange={(e) => handleEventChange(parseInt(e.target.value))}
            >
              <option value="">Select a race...</option>
              {events?.map((e: any) => (
                <option key={e.event_id} value={e.event_id}>
                  R{e.round}: {e.event_name}{(e.has_sprint || String(e.event_format || '').toLowerCase().includes('sprint')) ? ' • Sprint Weekend' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {!selectedEventId && (
        <div className="bg-[#111318] border border-gray-800 rounded-xl p-16 text-center">
          <div className="w-20 h-20 bg-purple-900/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <BarChart3 size={36} className="text-purple-500" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Select a Grand Prix</h2>
          <p className="text-gray-500 max-w-md mx-auto">Choose a season and race above to unlock detailed race analytics</p>
        </div>
      )}

      {selectedEventId && raceSession && (
        <>
          {/* Tab Bar */}
          <div className="flex gap-0.5 bg-[#0a0c10] p-1 rounded-xl border border-gray-800">
            {([
              { key: 'overview', label: 'Overview', icon: Trophy },
              { key: 'laptimes', label: 'Lap Times', icon: Timer },
              { key: 'positions', label: 'Positions', icon: TrendingUp },
              { key: 'tyres', label: 'Strategy', icon: Layers },
              { key: 'telemetry', label: 'Telemetry', icon: Activity },
            ] as const).map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg font-bold text-xs transition-all ${
                  activeTab === key
                    ? 'bg-gradient-to-r from-purple-600 to-cyan-600 text-white shadow-lg shadow-purple-600/20'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
                }`}
              >
                <Icon size={14} />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>

          {/* ═══ OVERVIEW TAB ═══ */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {lapLoading ? (
                <LoadingState text="Loading race overview..." />
              ) : raceStats ? (
                <>
                  {/* Key stats grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <GlassCard
                      icon={<Trophy size={18} className="text-yellow-400" />}
                      label="Fastest Lap"
                      value={fmtLap(raceStats.fastest?.best_lap_time)}
                      sub={raceStats.fastest?.driver_code}
                      accent="yellow"
                    />
                    <GlassCard
                      icon={<Users size={18} className="text-green-400" />}
                      label="Finishers"
                      value={`${raceStats.finishers}/${drivers.length}`}
                      sub={raceStats.dnfCount > 0 ? `${raceStats.dnfCount} DNF` : 'All finished'}
                      accent="green"
                    />
                    <GlassCard
                      icon={<Flag size={18} className="text-cyan-400" />}
                      label="Total Laps"
                      value={String(raceStats.totalLaps)}
                      sub={`${raceSession.total_laps} race laps`}
                      accent="cyan"
                    />
                    <GlassCard
                      icon={<Fuel size={18} className="text-orange-400" />}
                      label="Avg Pit Stops"
                      value={raceStats.avgPitStops}
                      sub="per driver"
                      accent="orange"
                    />
                  </div>

                  {/* Weather + Race info side by side */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {weather && (
                      <div className="bg-[#111318] border border-gray-800 rounded-xl p-5">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
                          <Wind size={14} className="text-blue-400" />
                          Race Day Weather
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                          <WeatherStat label="Air Temp" value={`${weather.air_temp}°C`} />
                          <WeatherStat label="Track Temp" value={`${weather.track_temp}°C`} />
                          <WeatherStat label="Humidity" value={`${weather.humidity}%`} />
                          <WeatherStat label="Wind" value={`${weather.wind_speed} km/h`} />
                          <div className="col-span-2">
                            <WeatherStat
                              label="Conditions"
                              value={weather.conditions === 'WET' ? 'Wet' : 'Dry'}
                              highlight={weather.conditions === 'WET' ? 'blue' : 'green'}
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Top 5 fastest laps */}
                    <div className="bg-[#111318] border border-gray-800 rounded-xl p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
                        <Zap size={14} className="text-purple-400" />
                        Fastest Laps
                      </h3>
                      <div className="space-y-2">
                        {raceStats.sorted.slice(0, 5).map((d: any, i: number) => {
                          const tc = getTeamColor(d.team || '');
                          const delta = d.best_lap_time - raceStats.fastest.best_lap_time;
                          return (
                            <div key={d.driver_code} className="flex items-center gap-3">
                              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-black ${
                                i === 0 ? 'bg-purple-500 text-white' : 'bg-gray-800 text-gray-400'
                              }`}>{i + 1}</span>
                              <div className="w-1 h-5 rounded-full" style={{ backgroundColor: tc }} />
                              <span className="font-bold text-sm w-10" style={{ color: tc }}>{d.driver_code}</span>
                              <span className="font-mono text-sm text-gray-300 flex-1">{fmtLap(d.best_lap_time)}</span>
                              <span className="text-xs font-mono text-gray-600">
                                {i === 0 ? '' : `+${delta.toFixed(3)}s`}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Biggest movers */}
                  {Object.keys(posDrivers).length > 0 && (
                    <div className="bg-[#111318] border border-gray-800 rounded-xl p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
                        <Target size={14} className="text-cyan-400" />
                        Biggest Movers
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {(() => {
                          const movers = Object.keys(posDrivers)
                            .map((code) => {
                              const d = posDrivers[code];
                              return { code, ...d, change: (d.grid || 20) - (d.finish || 20) };
                            })
                            .sort((a: any, b: any) => Math.abs(b.change) - Math.abs(a.change))
                            .slice(0, 6);

                          return movers.map((d: any) => {
                            const tc = getTeamColor(d.team || '');
                            return (
                              <div key={d.code} className="flex items-center gap-3 bg-[#0a0c10] rounded-lg p-3 border border-gray-800/50">
                                <div className="w-1 h-8 rounded-full" style={{ backgroundColor: tc }} />
                                <span className="font-bold text-sm w-10" style={{ color: tc }}>{d.code}</span>
                                <span className="text-xs text-gray-500 flex-1">P{d.grid} → P{d.finish}</span>
                                <div className={`flex items-center gap-1 font-black text-sm ${
                                  d.change > 0 ? 'text-green-400' : d.change < 0 ? 'text-red-400' : 'text-gray-600'
                                }`}>
                                  {d.change > 0 ? <ArrowUpRight size={14} /> : d.change < 0 ? <ArrowDownRight size={14} /> : <Minus size={14} />}
                                  {Math.abs(d.change) || '—'}
                                </div>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    </div>
                  )}

                  {/* Mini strategy overview */}
                  {strategies.length > 0 && (
                    <div className="bg-[#111318] border border-gray-800 rounded-xl p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
                        <Layers size={14} className="text-orange-400" />
                        Strategy Overview — Top 10
                      </h3>
                      <div className="space-y-1.5">
                        {[...strategies]
                          .sort((a: any, b: any) => (a.position || 99) - (b.position || 99))
                          .slice(0, 10)
                          .map((d: any) => {
                            const tc = getTeamColor(d.team || '');
                            const maxLap = Math.max(...strategies.flatMap((s: any) =>
                              s.stints?.map((st: any) => st.end_lap) || [0]
                            ), 1);
                            return (
                              <div key={d.driver_code} className="flex items-center gap-2">
                                <span className="text-[10px] font-bold w-7 text-right text-gray-600">P{d.position}</span>
                                <span className="text-[10px] font-bold w-8" style={{ color: tc }}>{d.driver_code}</span>
                                <div className="flex-1 h-5 bg-[#0a0c10] rounded overflow-hidden flex">
                                  {d.stints?.map((stint: any, i: number) => {
                                    const width = (stint.laps / maxLap) * 100;
                                    const bg = TYRE_COLORS[stint.compound] || '#888';
                                    return (
                                      <div key={i} className="h-full flex items-center justify-center border-r border-[#111318]"
                                        style={{ width: `${width}%`, backgroundColor: bg + '60' }}
                                        title={`${stint.compound}: ${stint.laps} laps`}>
                                        {stint.laps >= 8 && (
                                          <span className="text-[8px] font-bold text-white/80">{TYRE_SHORT[stint.compound]}{stint.laps}</span>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                                <span className="text-[10px] text-gray-600 w-10 text-right">{d.total_pit_stops}st</span>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <EmptyState text="No race data available" />
              )}
            </div>
          )}

          {/* ═══ LAP TIMES TAB ═══ */}
          {activeTab === 'laptimes' && (
            <div className="space-y-6">
              {lapLoading ? (
                <LoadingState text="Analyzing lap times..." />
              ) : drivers.length > 0 ? (
                <>
                  <div className="bg-[#111318] border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-6 flex items-center gap-2">
                      <Timer className="text-purple-400" size={16} />
                      Best Lap Time Comparison
                    </h3>
                    {(() => {
                      const valid = drivers.filter((d: any) => isValidLap(d.best_lap_time));
                      const invalid = drivers.filter((d: any) => !isValidLap(d.best_lap_time));
                      const sorted = [...valid].sort((a: any, b: any) => a.best_lap_time - b.best_lap_time);
                      const fastest = sorted[0]?.best_lap_time || 1;
                      const slowest = sorted[sorted.length - 1]?.best_lap_time || fastest + 5;
                      const range = slowest - fastest;

                      return (
                        <div className="space-y-1">
                          {sorted.map((d: any, i: number) => {
                            const tc = getTeamColor(d.team || '');
                            const delta = d.best_lap_time - fastest;
                            const pct = range > 0 ? (delta / range) : 0;
                            return (
                              <div key={d.driver_code} className="flex items-center gap-2 group hover:bg-gray-800/30 rounded px-1 py-0.5 transition">
                                <span className="text-[10px] font-bold w-4 text-gray-600 text-right">{i + 1}</span>
                                <div className="w-1 h-5 rounded-full" style={{ backgroundColor: tc }} />
                                <span className="text-[10px] font-bold w-8" style={{ color: tc }}>{d.driver_code}</span>
                                <div className="flex-1 h-6 bg-[#0a0c10] rounded-md relative overflow-hidden">
                                  <div className="h-full rounded-md flex items-center px-2 transition-all duration-700"
                                    style={{
                                      width: `${Math.max(15, 100 - pct * 70)}%`,
                                      background: `linear-gradient(90deg, ${tc}CC, ${tc}44)`,
                                    }}>
                                    <span className="text-[10px] font-mono font-bold text-white whitespace-nowrap drop-shadow">{fmtLap(d.best_lap_time)}</span>
                                  </div>
                                </div>
                                <span className="text-[10px] font-mono text-gray-600 w-14 text-right">
                                  {i === 0 ? <span className="text-purple-400">FASTEST</span> : `+${delta.toFixed(3)}`}
                                </span>
                              </div>
                            );
                          })}
                          {invalid.length > 0 && (
                            <>
                              <div className="border-t border-gray-800 my-2" />
                              {invalid.map((d: any) => {
                                const tc = getTeamColor(d.team || '');
                                return (
                                  <div key={d.driver_code} className="flex items-center gap-2 opacity-40">
                                    <span className="text-[10px] font-bold w-4 text-gray-700 text-right">—</span>
                                    <div className="w-1 h-5 rounded-full" style={{ backgroundColor: tc }} />
                                    <span className="text-[10px] font-bold w-8" style={{ color: tc }}>{d.driver_code}</span>
                                    <div className="flex-1 h-6 bg-[#0a0c10] rounded-md relative overflow-hidden">
                                      <div className="h-full rounded-md flex items-center px-2"
                                        style={{ width: '100%', background: `repeating-linear-gradient(135deg, ${tc}11, ${tc}11 8px, transparent 8px, transparent 16px)` }}>
                                        <span className="text-[10px] font-mono text-gray-600">{d.total_laps === 0 ? 'DNS' : 'DNF'}</span>
                                      </div>
                                    </div>
                                    <span className="text-[10px] font-mono text-gray-700 w-14 text-right">{d.total_laps === 0 ? 'DNS' : `${d.total_laps}L`}</span>
                                  </div>
                                );
                              })}
                            </>
                          )}
                        </div>
                      );
                    })()}
                  </div>

                  {/* Detailed table */}
                  <div className="bg-[#111318] border border-gray-800 rounded-xl overflow-hidden">
                    <div className="px-5 py-4 border-b border-gray-800">
                      <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                        <Gauge className="text-purple-400" size={16} />
                        Lap Time Statistics
                      </h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-[#0a0c10] border-b border-gray-800">
                          <tr>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-gray-600">Pos</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-gray-600">Driver</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-gray-600">Team</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase tracking-wider text-purple-400">Best</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase tracking-wider text-yellow-400">Avg</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase tracking-wider text-gray-500">Median</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase tracking-wider text-red-400">Worst</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase tracking-wider text-gray-600">Laps</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-gray-600">Tyres</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800/50">
                          {[...drivers]
                            .sort((a: any, b: any) => (a.position || 99) - (b.position || 99))
                            .map((d: any) => {
                              const tc = getTeamColor(d.team || '');
                              return (
                                <tr key={d.driver_code} className="hover:bg-gray-800/20 transition">
                                  <td className="px-3 py-2.5 font-bold text-xs">P{d.position}</td>
                                  <td className="px-3 py-2.5">
                                    <div className="flex items-center gap-2">
                                      <div className="w-0.5 h-5 rounded-full" style={{ backgroundColor: tc }} />
                                      <span className="font-bold text-xs">{d.driver_code}</span>
                                      <span className="text-[10px] text-gray-600 hidden md:inline">{d.driver_name}</span>
                                    </div>
                                  </td>
                                  <td className="px-3 py-2.5 text-[10px] text-gray-500">{d.team}</td>
                                  <td className="px-3 py-2.5 text-center font-mono text-xs text-purple-400 font-bold">{fmtLap(d.best_lap_time)}</td>
                                  <td className="px-3 py-2.5 text-center font-mono text-xs text-yellow-400">{fmtLap(d.avg_lap_time)}</td>
                                  <td className="px-3 py-2.5 text-center font-mono text-xs text-gray-500">{fmtLap(d.median_lap_time)}</td>
                                  <td className="px-3 py-2.5 text-center font-mono text-xs text-red-400">{fmtLap(d.worst_lap_time)}</td>
                                  <td className="px-3 py-2.5 text-center font-bold text-xs">{d.total_laps}</td>
                                  <td className="px-3 py-2.5">
                                    <div className="flex gap-0.5">
                                      {d.tyre_compounds?.map((t: string, i: number) => (
                                        TYRE_IMG[t] ? (
                                          <Image key={i} src={TYRE_IMG[t]} alt={t} width={18} height={18} className="object-contain" title={t} />
                                        ) : (
                                          <span key={i} className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold"
                                            style={{ backgroundColor: TYRE_COLORS[t] || '#888', color: t === 'HARD' ? '#000' : '#fff' }}>
                                            {TYRE_SHORT[t] || '?'}
                                          </span>
                                        )
                                      ))}
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState text="No lap time data available for this session" />
              )}
            </div>
          )}

          {/* ═══ POSITION CHANGES TAB ═══ */}
          {activeTab === 'positions' && (
            <div className="space-y-6">
              {posLoading ? (
                <LoadingState text="Loading position data..." />
              ) : Object.keys(posDrivers).length > 0 ? (
                <>
                  <div className="bg-[#111318] border border-gray-800 rounded-xl p-6 overflow-x-auto">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-6 flex items-center gap-2">
                      <TrendingUp className="text-purple-400" size={16} />
                      Race Position Chart
                    </h3>
                    {(() => {
                      const driverCodes = Object.keys(posDrivers);
                      const totalDrivers = driverCodes.length;
                      const allPositions = driverCodes.flatMap((c) => posDrivers[c].positions || []);
                      const maxLap = Math.max(...allPositions.map((p: any) => p.lap), 1);

                      const chartW = Math.max(900, maxLap * 14);
                      const chartH = totalDrivers * 26 + 60;
                      const padL = 42, padT = 20, padR = 50, padB = 30;
                      const plotW = chartW - padL - padR;
                      const plotH = chartH - padT - padB;
                      const xScale = (lap: number) => padL + (lap / maxLap) * plotW;
                      const yScale = (pos: number) => padT + ((pos - 1) / (totalDrivers - 1 || 1)) * plotH;

                      return (
                        <svg viewBox={`0 0 ${chartW} ${chartH}`} className="w-full" style={{ minWidth: '900px' }}>
                          {Array.from({ length: totalDrivers }, (_, i) => i + 1).map((p) => (
                            <g key={`grid-${p}`}>
                              <line x1={padL} y1={yScale(p)} x2={chartW - padR} y2={yScale(p)} stroke="#1a1a1a" strokeWidth={1} />
                              <text x={padL - 6} y={yScale(p) + 3} textAnchor="end" fill="#333" fontSize="9" fontFamily="monospace">P{p}</text>
                            </g>
                          ))}
                          {Array.from({ length: Math.floor(maxLap / 10) }, (_, i) => (i + 1) * 10).map((lap) => (
                            <g key={`lap-${lap}`}>
                              <line x1={xScale(lap)} y1={padT} x2={xScale(lap)} y2={chartH - padB} stroke="#1a1a1a" strokeWidth={1} />
                              <text x={xScale(lap)} y={chartH - padB + 14} textAnchor="middle" fill="#333" fontSize="8" fontFamily="monospace">L{lap}</text>
                            </g>
                          ))}
                          {driverCodes.map((code) => {
                            const d = posDrivers[code];
                            const tc = getTeamColor(d.team || '') || '#888';
                            const positions = d.positions || [];
                            if (positions.length === 0) return null;
                            const isActive = selectedDrivers.length === 0 || selectedDrivers.includes(code);
                            const sorted = [...positions].sort((a: any, b: any) => a.lap - b.lap);
                            const pathData = sorted.map((p: any, i: number) => `${i === 0 ? 'M' : 'L'} ${xScale(p.lap)} ${yScale(p.position)}`).join(' ');
                            const lastPos = sorted[sorted.length - 1];
                            return (
                              <g key={code} opacity={isActive ? 1 : 0.08}>
                                <path d={pathData} fill="none" stroke={tc} strokeWidth={isActive ? 2 : 1} strokeLinejoin="round" />
                                <rect x={xScale(lastPos.lap) + 4} y={yScale(lastPos.position) - 6} width={28} height={12} rx={3} fill={tc} opacity={isActive ? 0.9 : 0.3} />
                                <text x={xScale(lastPos.lap) + 18} y={yScale(lastPos.position) + 3} textAnchor="middle" fill="#000" fontSize="7" fontWeight="bold" fontFamily="monospace">{code}</text>
                              </g>
                            );
                          })}
                        </svg>
                      );
                    })()}

                    <div className="flex flex-wrap gap-1 mt-4 pt-4 border-t border-gray-800">
                      <button onClick={() => setSelectedDrivers([])}
                        className={`px-2.5 py-1 rounded-md text-[10px] font-bold transition ${selectedDrivers.length === 0 ? 'bg-purple-600 text-white' : 'bg-gray-800/50 text-gray-500 hover:text-white'}`}>All</button>
                      {Object.keys(posDrivers).map((code) => {
                        const tc = getTeamColor(posDrivers[code].team || '');
                        const active = selectedDrivers.includes(code);
                        return (
                          <button key={code}
                            onClick={() => setSelectedDrivers((prev) => prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code])}
                            className={`px-2 py-1 rounded-md text-[10px] font-bold transition border ${active ? 'text-white' : 'text-gray-600 hover:text-white border-gray-800'}`}
                            style={active ? { backgroundColor: tc + '30', borderColor: tc, color: tc } : {}}
                          >{code}</button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="bg-[#111318] border border-gray-800 rounded-xl p-5">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
                      <Target className="text-purple-400" size={16} />
                      Position Changes
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {Object.keys(posDrivers)
                        .map((code) => {
                          const d = posDrivers[code];
                          return { code, ...d, change: (d.grid || 20) - (d.finish || 20) };
                        })
                        .sort((a: any, b: any) => b.change - a.change)
                        .map((d: any) => {
                          const tc = getTeamColor(d.team || '');
                          return (
                            <div key={d.code} className="flex items-center gap-3 bg-[#0a0c10] rounded-lg p-2.5 border border-gray-800/50">
                              <div className="w-0.5 h-8 rounded-full" style={{ backgroundColor: tc }} />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-xs" style={{ color: tc }}>{d.code}</span>
                                  <span className="text-[10px] text-gray-600 truncate">{d.driver_name}</span>
                                </div>
                                <div className="text-[10px] text-gray-600">P{d.grid} → P{d.finish}</div>
                              </div>
                              <div className={`text-sm font-black ${d.change > 0 ? 'text-green-400' : d.change < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                                {d.change > 0 ? `+${d.change}` : d.change === 0 ? '—' : String(d.change)}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState text="No position data available for this session" />
              )}
            </div>
          )}

          {/* ═══ TYRE STRATEGY TAB ═══ */}
          {activeTab === 'tyres' && (
            <div className="space-y-6">
              {tyreLoading ? (
                <LoadingState text="Loading tyre strategies..." />
              ) : strategies.length > 0 ? (
                <>
                  <div className="bg-[#111318] border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-6 flex items-center gap-2">
                      <Layers className="text-purple-400" size={16} />
                      Tyre Strategy
                    </h3>
                    <div className="space-y-1.5">
                      {[...strategies]
                        .sort((a: any, b: any) => (a.position || 99) - (b.position || 99))
                        .map((d: any) => {
                          const tc = getTeamColor(d.team || '');
                          const maxLap = Math.max(...strategies.flatMap((s: any) => s.stints?.map((st: any) => st.end_lap) || [0]), 1);
                          return (
                            <div key={d.driver_code} className="flex items-center gap-2 group">
                              <span className="text-[10px] font-bold w-7 text-right text-gray-600">P{d.position}</span>
                              <div className="w-0.5 h-6 rounded-full" style={{ backgroundColor: tc }} />
                              <span className="text-[10px] font-bold w-8" style={{ color: tc }}>{d.driver_code}</span>
                              <div className="flex-1 h-7 bg-[#0a0c10] rounded-lg overflow-hidden flex relative">
                                {d.stints?.map((stint: any, i: number) => {
                                  const width = (stint.laps / maxLap) * 100;
                                  const bg = TYRE_COLORS[stint.compound] || '#888';
                                  return (
                                    <div key={i} className="h-full flex items-center justify-center relative border-r border-[#111318]/50"
                                      style={{ width: `${width}%`, backgroundColor: bg + '70' }}
                                      title={`${stint.compound}: Lap ${stint.start_lap}-${stint.end_lap} (${stint.laps} laps)`}>
                                      {stint.laps >= 5 && (
                                        <span className="text-[9px] font-bold text-white/90 drop-shadow">{TYRE_SHORT[stint.compound]}{stint.laps}</span>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                              <span className="text-[10px] text-gray-600 w-10 text-right">{d.total_pit_stops}st</span>
                            </div>
                          );
                        })}
                    </div>
                    <div className="flex gap-4 mt-5 pt-4 border-t border-gray-800 justify-center">
                      {Object.entries(TYRE_COLORS).map(([compound, color]) => (
                        <div key={compound} className="flex items-center gap-1.5">
                          {TYRE_IMG[compound] ? (
                            <Image src={TYRE_IMG[compound]} alt={compound} width={16} height={16} className="object-contain" />
                          ) : (
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          )}
                          <span className="text-[10px] text-gray-500 font-bold">{compound}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#111318] border border-gray-800 rounded-xl overflow-hidden">
                    <div className="px-5 py-4 border-b border-gray-800">
                      <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                        <Fuel className="text-purple-400" size={16} />
                        Pit Stop Summary
                      </h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-[#0a0c10] border-b border-gray-800">
                          <tr>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase text-gray-600">Pos</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase text-gray-600">Driver</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase text-gray-600">Team</th>
                            <th className="px-3 py-2.5 text-center text-[10px] font-bold uppercase text-purple-400">Stops</th>
                            <th className="px-3 py-2.5 text-left text-[10px] font-bold uppercase text-gray-600">Stints</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800/50">
                          {[...strategies]
                            .sort((a: any, b: any) => (a.position || 99) - (b.position || 99))
                            .map((d: any) => {
                              const tc = getTeamColor(d.team || '');
                              return (
                                <tr key={d.driver_code} className="hover:bg-gray-800/20 transition">
                                  <td className="px-3 py-2.5 font-bold text-xs">P{d.position}</td>
                                  <td className="px-3 py-2.5">
                                    <div className="flex items-center gap-2">
                                      <div className="w-0.5 h-5 rounded-full" style={{ backgroundColor: tc }} />
                                      <span className="font-bold text-xs">{d.driver_code}</span>
                                    </div>
                                  </td>
                                  <td className="px-3 py-2.5 text-[10px] text-gray-500">{d.team}</td>
                                  <td className="px-3 py-2.5 text-center font-bold text-purple-400">{d.total_pit_stops}</td>
                                  <td className="px-3 py-2.5">
                                    <div className="flex gap-1 items-center flex-wrap">
                                      {d.stints?.map((stint: any, i: number) => (
                                        <div key={i} className="flex items-center gap-0.5">
                                          {TYRE_IMG[stint.compound] ? (
                                            <Image src={TYRE_IMG[stint.compound]} alt={stint.compound} width={18} height={18} className="object-contain" title={stint.compound} />
                                          ) : (
                                            <span className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold"
                                              style={{ backgroundColor: TYRE_COLORS[stint.compound] || '#888', color: stint.compound === 'HARD' ? '#000' : '#fff' }}>
                                              {TYRE_SHORT[stint.compound] || '?'}
                                            </span>
                                          )}
                                          <span className="text-[9px] text-gray-600">{stint.laps}L</span>
                                          {i < (d.stints?.length || 0) - 1 && <span className="text-gray-700 text-[9px] mx-0.5">→</span>}
                                        </div>
                                      ))}
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState text="No tyre strategy data available" />
              )}
            </div>
          )}

          {/* ═══ TELEMETRY TAB ═══ */}
          {activeTab === 'telemetry' && (
            <div className="space-y-6">
              <div className="bg-[#111318] border border-gray-800 rounded-xl p-4">
                <label className="block text-[10px] uppercase tracking-widest text-purple-400 font-bold mb-2">Select Driver</label>
                <div className="flex flex-wrap gap-1">
                  {drivers.length > 0
                    ? [...drivers]
                        .sort((a: any, b: any) => (a.position || 99) - (b.position || 99))
                        .map((d: any) => {
                          const tc = getTeamColor(d.team || '');
                          return (
                            <button key={d.driver_code} onClick={() => setTelemetryDriver(d.driver_code)}
                              className={`px-2.5 py-1 rounded-md text-[10px] font-bold transition border ${
                                telemetryDriver === d.driver_code ? 'text-white' : 'text-gray-600 hover:text-white border-gray-800'
                              }`}
                              style={telemetryDriver === d.driver_code ? { backgroundColor: tc + '30', borderColor: tc, color: tc } : {}}>
                              {d.driver_code}
                            </button>
                          );
                        })
                    : <span className="text-gray-600 text-xs">Load overview first</span>
                  }
                </div>
              </div>

              {!telemetryDriver && <EmptyState text="Select a driver to view telemetry" />}
              {telemetryDriver && telLoading && <LoadingState text={`Loading ${telemetryDriver}...`} />}

              {telemetryDriver && !telLoading && tLaps.length > 0 && (
                <>
                  <div className="bg-[#111318] border border-gray-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                        <Clock className="text-purple-400" size={16} />
                        {telemetryDriver} — Lap Times
                      </h3>
                      <span className="text-[10px] bg-purple-600/20 text-purple-400 px-2 py-0.5 rounded font-bold">{tLaps.length} LAPS</span>
                    </div>

                    {(() => {
                      const validLaps = tLaps.filter((l: any) => l.lap_time && l.lap_time > 0 && l.lap_time < 300);
                      if (validLaps.length === 0) return <div className="text-gray-600 text-sm">No valid lap times</div>;

                      const minTime = Math.min(...validLaps.map((l: any) => l.lap_time));
                      const maxTime = Math.max(...validLaps.map((l: any) => l.lap_time));
                      const range = maxTime - minTime || 1;
                      const chartW = 800, chartH = 220, padL = 55, padR = 15, padT = 15, padB = 25;
                      const xScale = (i: number) => padL + (i / (validLaps.length - 1 || 1)) * (chartW - padL - padR);
                      const yScale = (t: number) => padT + ((t - minTime) / range) * (chartH - padT - padB);

                      return (
                        <svg viewBox={`0 0 ${chartW} ${chartH}`} className="w-full">
                          <defs>
                            <linearGradient id="lapGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#a855f7" stopOpacity={0.3} />
                              <stop offset="100%" stopColor="#a855f7" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          {[0, 0.25, 0.5, 0.75, 1].map((f, i) => {
                            const t = minTime + range * f;
                            return (
                              <g key={i}>
                                <line x1={padL} y1={yScale(t)} x2={chartW - padR} y2={yScale(t)} stroke="#1a1a1a" strokeWidth={1} />
                                <text x={padL - 4} y={yScale(t) + 3} textAnchor="end" fill="#333" fontSize="8" fontFamily="monospace">{fmtLap(t)}</text>
                              </g>
                            );
                          })}
                          <polygon
                            points={`${xScale(0)},${chartH - padB} ${validLaps.map((l: any, i: number) => `${xScale(i)},${yScale(l.lap_time)}`).join(' ')} ${xScale(validLaps.length - 1)},${chartH - padB}`}
                            fill="url(#lapGrad)" />
                          <polyline
                            points={validLaps.map((l: any, i: number) => `${xScale(i)},${yScale(l.lap_time)}`).join(' ')}
                            fill="none" stroke="#a855f7" strokeWidth={1.5} />
                          {validLaps.map((l: any, i: number) => (
                            <circle key={i} cx={xScale(i)} cy={yScale(l.lap_time)} r={2.5}
                              fill={TYRE_COLORS[l.tyre_compound] || '#a855f7'} stroke="#000" strokeWidth={0.5}>
                              <title>Lap {l.lap_number}: {fmtLap(l.lap_time)} ({l.tyre_compound})</title>
                            </circle>
                          ))}
                          {validLaps.filter((l: any) => l.pit_in || l.pit_out).map((l: any, i: number) => {
                            const idx = validLaps.indexOf(l);
                            return (
                              <g key={`pit-${i}`}>
                                <line x1={xScale(idx)} y1={padT} x2={xScale(idx)} y2={chartH - padB} stroke="#3b82f6" strokeWidth={0.5} strokeDasharray="3,3" opacity={0.5} />
                                <text x={xScale(idx)} y={padT - 3} textAnchor="middle" fill="#3b82f6" fontSize="7" fontWeight="bold">PIT</text>
                              </g>
                            );
                          })}
                          {validLaps.filter((_: any, i: number) => i % Math.max(1, Math.floor(validLaps.length / 8)) === 0).map((l: any) => {
                            const idx = validLaps.indexOf(l);
                            return (
                              <text key={idx} x={xScale(idx)} y={chartH - padB + 12} textAnchor="middle" fill="#333" fontSize="8" fontFamily="monospace">L{l.lap_number}</text>
                            );
                          })}
                        </svg>
                      );
                    })()}
                  </div>

                  <div className="bg-[#111318] border border-gray-800 rounded-xl overflow-hidden">
                    <div className="px-5 py-4 border-b border-gray-800">
                      <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                        <Zap className="text-purple-400" size={16} />
                        Sector Times — {telemetryDriver}
                      </h3>
                    </div>
                    <div className="overflow-x-auto max-h-[500px]">
                      <table className="w-full">
                        <thead className="bg-[#0a0c10] border-b border-gray-800 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left text-[10px] font-bold uppercase text-gray-600">Lap</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-purple-400">Time</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-yellow-400">S1</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-cyan-400">S2</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-green-400">S3</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-gray-600">Pos</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-gray-600">Tyre</th>
                            <th className="px-3 py-2 text-center text-[10px] font-bold uppercase text-gray-600">Age</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800/30">
                          {tLaps.map((l: any) => {
                            const isPB = l.is_personal_best;
                            return (
                              <tr key={l.lap_number} className={`hover:bg-gray-800/20 transition ${isPB ? 'bg-purple-900/10' : ''}`}>
                                <td className="px-3 py-2 font-bold text-xs">{l.lap_number}</td>
                                <td className={`px-3 py-2 text-center font-mono text-xs ${isPB ? 'text-purple-400 font-bold' : 'text-gray-300'}`}>
                                  {fmtLap(l.lap_time)}{isPB && <span className="ml-1 text-[8px] text-purple-500">PB</span>}
                                </td>
                                <td className="px-3 py-2 text-center font-mono text-[10px] text-yellow-400">{l.sector1 ? l.sector1.toFixed(3) : '—'}</td>
                                <td className="px-3 py-2 text-center font-mono text-[10px] text-cyan-400">{l.sector2 ? l.sector2.toFixed(3) : '—'}</td>
                                <td className="px-3 py-2 text-center font-mono text-[10px] text-green-400">{l.sector3 ? l.sector3.toFixed(3) : '—'}</td>
                                <td className="px-3 py-2 text-center font-bold text-xs">P{l.position}</td>
                                <td className="px-3 py-2 text-center">
                                  {TYRE_IMG[l.tyre_compound] ? (
                                    <Image src={TYRE_IMG[l.tyre_compound]} alt={l.tyre_compound} width={18} height={18} className="object-contain inline-block" title={l.tyre_compound} />
                                  ) : (
                                    <span className="inline-block w-4 h-4 rounded-full text-[8px] font-bold leading-4 text-center"
                                      style={{ backgroundColor: TYRE_COLORS[l.tyre_compound] || '#888', color: l.tyre_compound === 'HARD' ? '#000' : '#fff' }}>
                                      {TYRE_SHORT[l.tyre_compound] || '?'}
                                    </span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-center text-[10px] text-gray-600">{l.tyre_age}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Reusable components ── */

function GlassCard({ icon, label, value, sub, accent = 'purple' }: {
  icon: React.ReactNode; label: string; value: string; sub?: string; accent?: string;
}) {
  const borderColor = accent === 'yellow' ? 'border-yellow-800/30' : accent === 'green' ? 'border-green-800/30' : accent === 'cyan' ? 'border-cyan-800/30' : accent === 'orange' ? 'border-orange-800/30' : 'border-purple-800/30';
  return (
    <div className={`bg-[#111318] border ${borderColor} rounded-xl p-4 relative overflow-hidden`}>
      <div className="flex items-center gap-2 mb-2">{icon}<span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">{label}</span></div>
      <div className="text-2xl font-black font-mono text-white">{value}</div>
      {sub && <div className="text-[10px] text-gray-600 mt-1">{sub}</div>}
    </div>
  );
}

function WeatherStat({ label, value, highlight }: { label: string; value: string; highlight?: string }) {
  const color = highlight === 'blue' ? 'text-blue-400' : highlight === 'green' ? 'text-green-400' : 'text-white';
  return (
    <div>
      <div className="text-[10px] text-gray-600 uppercase tracking-wider">{label}</div>
      <div className={`text-sm font-bold font-mono ${color}`}>{value}</div>
    </div>
  );
}

function LoadingState({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center min-h-[30vh]">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-gray-500 text-sm">{text}</p>
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="bg-[#111318] border border-gray-800 rounded-xl p-12 text-center">
      <div className="w-14 h-14 bg-gray-800/50 rounded-xl flex items-center justify-center mx-auto mb-3">
        <BarChart3 size={24} className="text-gray-600" />
      </div>
      <p className="text-gray-500">{text}</p>
    </div>
  );
}
