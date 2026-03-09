'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { Trophy, Users, Play, BarChart3, TrendingUp, Timer, Layers, Activity, Flag, Award, Brain, ArrowRight, Sparkles, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { useState, useEffect } from 'react';
import { getCurrentOrUpcomingEvent } from '@/lib/utils';
import { F1CarAnimation } from '@/components/F1CarAnimation';

/* ─── GlassCard ───────────────────────────────────────────────── */
function GlassCard({ children, className = '', hover = true }: { children: React.ReactNode; className?: string; hover?: boolean }) {
  return (
    <div className={`bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] rounded-2xl ${hover ? 'hover:border-white/10 hover:bg-white/[0.05] transition-all duration-300' : ''} ${className}`}>
      {children}
    </div>
  );
}

/* ─── Animated counter ────────────────────────────────────────── */
function AnimatedNumber({ target, duration = 1500 }: { target: number; duration?: number }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = target / (duration / 16);
    const id = setInterval(() => {
      start += step;
      if (start >= target) { setVal(target); clearInterval(id); }
      else setVal(Math.floor(start));
    }, 16);
    return () => clearInterval(id);
  }, [target, duration]);
  return <>{val.toLocaleString()}</>;
}

/* ─── Team color helper ───────────────────────────────────────── */
const TC: Record<string, string> = {
  'Red Bull': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2', 'McLaren': '#FF8000',
  'Aston Martin': '#229971', 'Alpine': '#FF87BC', 'Williams': '#64C4FF', 'Haas': '#B6BABD',
  'Kick Sauber': '#52E252', 'Audi': '#990000', 'RB': '#6692FF', 'Racing Bulls': '#6692FF', 'Cadillac': '#C4A747',
};
function teamColor(name: string) {
  for (const [k, v] of Object.entries(TC)) if (name?.toLowerCase().includes(k.toLowerCase())) return v;
  return '#888';
}

/* ─── MAIN ────────────────────────────────────────────────────── */
export default function Home() {
  const [selectedSeason, setSelectedSeason] = useState<number>(2026);
  const [showAnimation, setShowAnimation] = useState(false);
  const [animationComplete, setAnimationComplete] = useState(false);

  useEffect(() => {
    // Only show animation on hard refresh / first load of the session.
    // Once it has played, skip it for any subsequent navigation.
    const alreadyPlayed = sessionStorage.getItem('f1_intro_played');
    if (alreadyPlayed) {
      setShowAnimation(false);
      setAnimationComplete(true);
    } else {
      setShowAnimation(true);
    }

    const failSafe = setTimeout(() => {
      setShowAnimation(false);
      setAnimationComplete(true);
      sessionStorage.setItem('f1_intro_played', '1');
    }, 8000);

    return () => clearTimeout(failSafe);
  }, []);

  const handleAnimationComplete = () => {
    setShowAnimation(false);
    setAnimationComplete(true);
    sessionStorage.setItem('f1_intro_played', '1');
  };

  const { data: seasons } = useQuery({ queryKey: ['seasons'], queryFn: () => api.getSeasons(), staleTime: 3600000 });
  const { data: events } = useQuery({ queryKey: ['events', selectedSeason], queryFn: () => api.getEvents(selectedSeason), enabled: !!selectedSeason });
  const { data: standings } = useQuery({ queryKey: ['standings', selectedSeason], queryFn: () => api.getStandings(selectedSeason), staleTime: 1800000 });
  const { data: constructorStandings } = useQuery({ queryKey: ['constructors-standings', selectedSeason], queryFn: () => api.getConstructorStandings(selectedSeason), staleTime: 1800000 });
  const { data: ingestSummary } = useQuery({
    queryKey: ['ingest-summary-home'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/ingest/summary');
      return res.json();
    },
    staleTime: 120000,
  });
  const { data: drivers } = useQuery({ queryKey: ['drivers-home'], queryFn: () => api.getDrivers(), staleTime: 300000 });

  const topDrivers = standings?.slice(0, 10) || [];
  const topTeams = constructorStandings?.slice(0, 5) || [];
  const maxPts = topDrivers[0]?.total_points || 1;
  const seasonMin = seasons?.length ? Math.min(...seasons) : null;
  const seasonMax = seasons?.length ? Math.max(...seasons) : null;
  const seasonRangeText = seasonMin && seasonMax ? `${seasonMin} to ${seasonMax}` : 'all ingested seasons';

  /* ── Find the upcoming/current GP (first future event or last event) ── */
  const upcomingGP = getCurrentOrUpcomingEvent(events as any[]);
  const isCurrentRaceDay = upcomingGP ? new Date(upcomingGP.event_date).toDateString() === new Date().toDateString() : false;

  return (
    <>
      {/* F1 Car Intro Animation */}
      {showAnimation && (
        <F1CarAnimation
          onComplete={handleAnimationComplete}
          durationMs={5200}
        />
      )}
      
      <div className={`transition-opacity duration-700 ease-out ${animationComplete ? 'opacity-100' : 'opacity-0'}`}>
      {/* ══════════ HERO — FULL SCREEN ══════════ */}
      <section className="relative overflow-hidden min-h-[100vh] flex items-center -mx-4 sm:-mx-6 lg:-mx-8 -mt-20">
        {/* BG layers */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0f0a0a] via-[#0c0d18] to-[#080c14]" />
        <div className="absolute inset-0">
          <div className="absolute top-[-20%] right-[-10%] w-[50vw] h-[50vw] bg-red-600/8 rounded-full blur-[160px]" />
          <div className="absolute bottom-[-10%] left-[-5%] w-[35vw] h-[35vw] bg-blue-600/5 rounded-full blur-[120px]" />
        </div>
        {/* Grid overlay */}
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
        
        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 animate-bounce">
          <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Scroll</span>
          <svg width="16" height="24" viewBox="0 0 16 24" fill="none" className="text-gray-500">
            <path d="M8 4L8 18M8 18L14 12M8 18L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>

        <div className="relative z-10 w-full max-w-7xl mx-auto px-8 md:px-16 py-20">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/20 px-4 py-1.5 rounded-full text-xs font-bold text-red-400 mb-6">
                <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" /> SEASON {selectedSeason} {selectedSeason === 2026 ? '• CURRENT' : ''}
              </div>
              <h1 className="text-5xl md:text-7xl font-black text-white leading-[0.95] tracking-tight mb-6">
                Every Lap.<br />
                <span
                  style={{
                    display: 'inline-block',
                    background: 'linear-gradient(to right, #ef4444, #dc2626)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  Analyzed.
                </span>
              </h1>
              <p className="text-lg text-gray-400 max-w-lg mb-10 leading-relaxed">
                Race replay with telemetry, machine learning predictions, and live race tooling across {seasonRangeText}.
              </p>
              
              <div className="flex flex-wrap gap-3">
                <Link href="/replay" className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white font-bold py-3 px-7 rounded-xl transition-all shadow-lg shadow-red-500/20 text-sm">
                  <Play size={16} /> Race Replay
                </Link>
                <Link href="/predictions" className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/15 text-white font-bold py-3 px-7 rounded-xl transition-all text-sm border border-white/10">
                  <Brain size={16} /> Predictions
                </Link>
                <Link href="/live" className="inline-flex items-center gap-2 bg-white/5 hover:bg-white/10 text-gray-300 font-bold py-3 px-7 rounded-xl transition-all text-sm">
                  <Activity size={16} /> Live Data
                </Link>
              </div>
            </div>

            {/* Right: Live Standings Mini */}
            <div className="hidden md:block">
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Driver Standings</h3>
                  <span className="text-xs text-gray-500">{selectedSeason}</span>
                </div>
                {topDrivers.length > 0 ? (
                  topDrivers.slice(0, 5).map((d: any, i: number) => (
                    <Link href={`/drivers/${d.driver_code?.toLowerCase()}`} key={d.driver_code} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0 hover:bg-white/[0.03] -mx-2 px-2 rounded-lg transition-colors group">
                      <span className={`w-5 text-xs font-black ${i === 0 && d.total_points > 0 ? 'text-yellow-400' : i === 1 && d.total_points > 0 ? 'text-gray-300' : i === 2 && d.total_points > 0 ? 'text-amber-600' : 'text-gray-500'}`}>
                        {i + 1}
                      </span>
                      <div className="w-1 h-5 rounded-full" style={{ backgroundColor: teamColor(d.team_name || d.constructor_name || '') }} />
                      <span className="font-bold text-sm flex-1 group-hover:text-white transition-colors">{d.driver_code}</span>
                      {maxPts > 0 ? (
                        <div className="flex-1">
                          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${(d.total_points / maxPts) * 100}%`, backgroundColor: teamColor(d.team_name || d.constructor_name || '') }} />
                          </div>
                        </div>
                      ) : (
                        <span className="text-[10px] text-gray-600 flex-1">{d.team_name || '-'}</span>
                      )}
                      <span className="text-xs font-mono text-gray-400 w-10 text-right">{d.total_points}</span>
                    </Link>
                  ))
                ) : (
                  <div className="text-gray-600 text-sm py-4 text-center">Loading standings...</div>
                )}
                <Link href="/drivers" className="flex items-center gap-1 text-xs text-red-400 font-bold mt-3 hover:text-red-300 transition-colors">
                  Full Standings <ArrowRight size={12} />
                </Link>
              </GlassCard>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════ Content below hero ══════════ */}
      <div className="space-y-14 pt-14">

      {/* ══════════ UPCOMING GP BANNER ══════════ */}
      {upcomingGP && (
        <section>
          <GlassCard className="p-6 bg-gradient-to-r from-red-600/10 via-transparent to-blue-600/10 border-red-500/10">
            <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-red-600/20 rounded-xl flex items-center justify-center border border-red-500/20">
                  <Flag size={24} className="text-red-400" />
                </div>
                <div>
                  <div className="text-[10px] text-red-400 font-bold uppercase tracking-widest">
                    {isCurrentRaceDay ? 'Current Race Weekend' : 'Next Race'}
                  </div>
                  <h3 className="text-xl font-black">{upcomingGP.event_name}</h3>
                  <div className="text-xs text-gray-500">
                    Round {upcomingGP.round} • {upcomingGP.location}, {upcomingGP.country} •{' '}
                    {new Date(upcomingGP.event_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 md:ml-auto">
                <Link href="/predictions" className="inline-flex items-center gap-1.5 bg-red-600 hover:bg-red-500 text-white font-bold py-2 px-5 rounded-lg text-xs transition-all">
                  <Brain size={14} /> Predict Winner
                </Link>
                <Link href="/live" className="inline-flex items-center gap-1.5 bg-white/10 hover:bg-white/15 text-white font-bold py-2 px-5 rounded-lg text-xs transition-all border border-white/10">
                  <Activity size={14} /> Live Data
                </Link>
                <Link href="/replay" className="inline-flex items-center gap-1.5 bg-white/5 hover:bg-white/10 text-gray-300 font-bold py-2 px-5 rounded-lg text-xs transition-all">
                  <Play size={14} /> Replay
                </Link>
              </div>
            </div>
          </GlassCard>
        </section>
      )}

      {/* ══════════ STATS BAR ══════════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Events', value: ingestSummary?.total_events_ingested || 0, icon: <Flag size={18} /> },
          { label: 'Sessions', value: ingestSummary?.total_sessions_ingested || 0, icon: <Timer size={18} /> },
          { label: 'Drivers', value: drivers?.length || 0, icon: <Users size={18} /> },
          { label: 'Seasons', value: seasons?.length || 0, icon: <Trophy size={18} /> },
        ].map(s => (
          <GlassCard key={s.label} className="p-5 text-center">
            <div className="text-gray-500 mb-2 flex justify-center">{s.icon}</div>
            <div className="text-2xl md:text-3xl font-black">
              <AnimatedNumber target={s.value} />
            </div>
            <div className="text-xs text-gray-500 font-semibold mt-1 uppercase tracking-wider">{s.label}</div>
          </GlassCard>
        ))}
      </div>

      {/* ══════════ FASTF1 DISCLAIMER ══════════ */}
      {selectedSeason < 2018 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-amber-400 mt-0.5 shrink-0" />
          <div>
            <div className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-1">Data Limitation</div>
            <p className="text-sm text-gray-400 leading-relaxed">
              FastF1 detailed telemetry (lap times, car data, tyre compounds) is only available from <strong className="text-white">2018 onwards</strong>. 
              For the {selectedSeason} season, data is sourced from Jolpica-F1 and includes race results, standings, and basic timing only.
            </p>
          </div>
        </div>
      )}

      {/* ══════════ SEASON EXPLORER ══════════ */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-3xl font-black">Season Explorer</h2>
            <p className="text-gray-500 text-sm mt-1">Every race. Every champion. {seasonRangeText}.</p>
          </div>
        </div>

        {/* Season pills */}
        <div className="flex flex-wrap gap-1.5 mb-8">
          {(seasons || []).map((s: number) => (
            <button key={s} onClick={() => setSelectedSeason(s)}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                s === selectedSeason ? 'bg-red-600 text-white shadow-lg shadow-red-500/20' : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-white'
              }`}>
              {s}
            </button>
          ))}
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Champion card */}
          <GlassCard className="p-6 md:col-span-1 bg-gradient-to-br from-yellow-500/5 to-transparent border-yellow-500/10">
            <div className="flex items-center gap-2 mb-4">
              <Trophy size={18} className="text-yellow-400" />
              <span className="text-xs font-bold text-yellow-400 uppercase tracking-wider">Champion</span>
            </div>
            {topDrivers[0] ? (
              topDrivers[0]?.total_points > 0 ? (
                <>
                  <div className="text-4xl font-black text-yellow-400 mb-1">{topDrivers[0]?.driver_code}</div>
                  <div className="text-sm text-gray-400 mb-3">{topDrivers[0]?.team_name || '-'}</div>
                  <div className="text-2xl font-black">{topDrivers[0]?.total_points} <span className="text-sm text-gray-500 font-normal">pts</span></div>
                </>
              ) : (
                <>
                  <div className="text-3xl font-black text-gray-500 mb-1">TBD</div>
                  <div className="text-sm text-gray-500 mb-3">Season not started</div>
                  <div className="text-xs text-gray-600">{topDrivers.length} drivers on the grid</div>
                </>
              )
            ) : (
              <div className="text-gray-600 text-sm">Loading...</div>
            )}
          </GlassCard>

          {/* Constructor champion */}
          <GlassCard className="p-6 md:col-span-1 bg-gradient-to-br from-orange-500/5 to-transparent border-orange-500/10">
            <div className="flex items-center gap-2 mb-4">
              <Award size={18} className="text-orange-400" />
              <span className="text-xs font-bold text-orange-400 uppercase tracking-wider">Constructors</span>
            </div>
            {topTeams[0] ? (
              (topTeams[0]?.points || topTeams[0]?.total_points) > 0 ? (
                <>
                  <div className="text-2xl font-black mb-1">{topTeams[0]?.constructor_name}</div>
                  <div className="text-2xl font-black mt-3" style={{ color: teamColor(topTeams[0]?.constructor_name) }}>
                    {topTeams[0]?.points || topTeams[0]?.total_points} <span className="text-sm text-gray-500 font-normal">pts</span>
                  </div>
                  <div className="mt-3 space-y-1.5">
                    {topTeams.slice(1, 4).map((t: any, i: number) => (
                      <div key={t.constructor_name} className="flex items-center gap-2 text-xs">
                        <span className="text-gray-500 w-3">{i + 2}</span>
                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: teamColor(t.constructor_name) }} />
                        <span className="text-gray-400 flex-1">{t.constructor_name}</span>
                        <span className="font-mono text-gray-500">{t.points || t.total_points}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <div className="text-xl font-black text-gray-500 mb-2">Season Not Started</div>
                  <div className="mt-3 space-y-1.5">
                    {topTeams.slice(0, 5).map((t: any, i: number) => (
                      <div key={t.constructor_name} className="flex items-center gap-2 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: teamColor(t.constructor_name) }} />
                        <span className="text-gray-400 flex-1">{t.constructor_name}</span>
                        <span className="font-mono text-gray-600">0</span>
                      </div>
                    ))}
                  </div>
                </>
              )
            ) : (
              <div className="text-gray-600 text-sm">Loading...</div>
            )}
          </GlassCard>

          {/* Races list */}
          <GlassCard className="p-6 md:col-span-1">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Flag size={18} className="text-red-400" />
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">{selectedSeason} Races</span>
              </div>
              <span className="text-xs text-gray-600">{events?.length || 0} rounds</span>
            </div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 scrollbar-thin">
              {(events || []).slice(0, 10).map((e: any, i: number) => (
                <div key={e.event_name || i} className="flex items-center gap-2 text-xs py-1 border-b border-white/5 last:border-0">
                  <span className="text-gray-600 w-4 font-mono">{i + 1}</span>
                  <span className="text-gray-300 flex-1 truncate">{e.event_name}</span>
                  {e.has_sprint && <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded font-bold">SPRINT</span>}
                </div>
              ))}
            </div>
            <Link href="/races" className="flex items-center gap-1 text-xs text-red-400 font-bold mt-3 hover:text-red-300 transition-colors">
              All Races <ArrowRight size={12} />
            </Link>
          </GlassCard>
        </div>
      </section>

      {/* ══════════ FEATURE GRID ══════════ */}
      <section>
        <div className="text-center mb-10">
          <h2 className="text-3xl font-black">Platform Features</h2>
          <p className="text-gray-500 text-sm mt-2">Everything you need to analyze, predict, and relive F1</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            { icon: <Play size={22} />, title: 'Race Replay', desc: 'Animated replay with driver positions, weather, tyre strategy, and DRS zones on real circuit layouts.', href: '/replay', colorClass: 'text-purple-400', ctaClass: 'text-purple-400', gradient: 'from-purple-500/10 to-purple-900/5' },
            { icon: <Activity size={22} />, title: 'Live Data from Race', desc: 'Lap-by-lap race data with ML predictions updating in real-time as the race unfolds.', href: '/live', colorClass: 'text-red-400', ctaClass: 'text-red-400', gradient: 'from-red-500/10 to-red-900/5' },
            { icon: <Brain size={22} />, title: 'ML Predictions', desc: 'Gradient Boosting + Groq/Gemini AI + Tavily web context for current race predictions.', href: '/predictions', colorClass: 'text-green-400', ctaClass: 'text-green-400', gradient: 'from-green-500/10 to-green-900/5' },
            { icon: <BarChart3 size={22} />, title: 'Deep Analytics', desc: 'Lap times, position changes, tyre strategy, and telemetry — custom SVG visualizations.', href: '/analytics', colorClass: 'text-cyan-400', ctaClass: 'text-cyan-400', gradient: 'from-cyan-500/10 to-cyan-900/5' },
            { icon: <Users size={22} />, title: 'Head-to-Head', desc: 'Compare any two drivers or constructors — points, wins, podiums, and career stats.', href: '/compare', colorClass: 'text-blue-400', ctaClass: 'text-blue-400', gradient: 'from-blue-500/10 to-blue-900/5' },
            { icon: <Trophy size={22} />, title: 'Constructor Standings', desc: 'Team championship across ingested seasons with driver breakdowns and points distribution.', href: '/constructors', colorClass: 'text-yellow-400', ctaClass: 'text-yellow-400', gradient: 'from-yellow-500/10 to-yellow-900/5' },
          ].map(f => (
            <Link key={f.title} href={f.href}>
              <GlassCard className={`p-6 h-full bg-gradient-to-br ${f.gradient} group cursor-pointer`}>
                <div className={`${f.colorClass} mb-3 group-hover:scale-110 transition-transform inline-block`}>{f.icon}</div>
                <h3 className="font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
                <div className={`flex items-center gap-1 text-xs font-bold ${f.ctaClass} mt-4 opacity-0 group-hover:opacity-100 transition-opacity`}>
                  Explore <ArrowRight size={12} />
                </div>
              </GlassCard>
            </Link>
          ))}
        </div>
      </section>

      {/* ══════════ DRIVER STANDINGS TABLE ══════════ */}
      {topDrivers.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-black">Driver Standings — {selectedSeason}</h2>
            <Link href="/drivers" className="text-xs text-red-400 font-bold hover:text-red-300 flex items-center gap-1">
              Full Standings <ArrowRight size={12} />
            </Link>
          </div>
          <GlassCard className="overflow-hidden" hover={false}>
            <div className="grid grid-cols-[40px_1fr_100px_60px] md:grid-cols-[50px_1fr_200px_80px_80px] gap-2 px-5 py-2.5 bg-white/5 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
              <div>#</div><div>Driver</div><div className="hidden md:block">Points Bar</div><div className="text-right">Pts</div><div className="text-right hidden md:block">Wins</div>
            </div>
            {topDrivers.map((d: any, i: number) => {
              const color = teamColor(d.constructor_name || '');
              return (
                <Link href={`/drivers/${d.driver_code?.toLowerCase()}`} key={d.driver_code} className="grid grid-cols-[40px_1fr_100px_60px] md:grid-cols-[50px_1fr_200px_80px_80px] gap-2 px-5 py-3 items-center border-t border-white/5 hover:bg-white/[0.04] transition-colors group cursor-pointer">
                  <div className={`text-xs font-black ${i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-600' : 'text-gray-600'}`}>
                    {i < 3 ? ['🥇','🥈','🥉'][i] : i + 1}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg overflow-hidden relative flex-shrink-0 bg-gray-800 flex items-center justify-center">
                      <Image
                        src={`/images/drivers/${d.driver_code}.png`}
                        alt={d.driver_code}
                        fill
                        className="object-cover object-top"
                        unoptimized
                        onError={(e: any) => { e.target.style.display = 'none'; e.target.parentElement.innerHTML = `<span class="text-xs font-bold text-gray-500">${d.driver_code?.slice(0,2) || '??'}</span>`; }}
                      />
                    </div>
                    <div className="w-1 h-6 rounded-full" style={{ backgroundColor: color }} />
                    <div>
                      <div className="font-bold text-sm group-hover:text-white transition-colors">{d.driver_code}</div>
                      <div className="text-[10px] text-gray-500">{d.constructor_name || ''}</div>
                    </div>
                  </div>
                  <div className="hidden md:block">
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${(d.total_points / maxPts) * 100}%`, backgroundColor: color }} />
                    </div>
                  </div>
                  <div className="text-right font-black text-sm" style={{ color }}>{d.total_points}</div>
                  <div className="text-right text-xs text-gray-500 hidden md:block">{d.wins || 0}</div>
                </Link>
              );
            })}
          </GlassCard>
        </section>
      )}

      {/* ══════════ CTA FOOTER ══════════ */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-red-600/20 via-[#111] to-blue-600/20 border border-white/5 p-6 md:p-12 text-center">
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-48 h-48 bg-red-500/10 rounded-full blur-[80px]" />
          <div className="absolute bottom-0 right-1/4 w-48 h-48 bg-blue-500/10 rounded-full blur-[80px]" />
        </div>
        <div className="relative z-10">
          <h2 className="text-3xl font-black mb-3">Start Exploring</h2>
          <p className="text-gray-400 max-w-lg mx-auto mb-8">Ingested seasons at your fingertips. Replay races, predict outcomes, and dive into analytics that actually match your live database.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/replay" className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white font-bold py-3 px-6 rounded-xl text-sm transition-all shadow-lg shadow-red-500/20">
              <Play size={16} /> Watch Race Replay
            </Link>
            <Link href="/about" className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/15 text-white font-bold py-3 px-6 rounded-xl text-sm transition-all">
              How It Was Built <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      </div>{/* end content space-y-14 */}
    </div>
    </>
  );
}
