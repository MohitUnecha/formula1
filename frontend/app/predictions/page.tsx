'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Brain, Trophy, Zap, AlertCircle, Loader2, TrendingUp, Layers, Star, ChevronDown, ChevronUp, Shield, Timer, Fuel, Clock } from 'lucide-react';
import api from '@/lib/api';
import Image from 'next/image';

// Rate limit error type
interface RateLimitError {
  error: string;
  message: string;
  reset_time: string | null;
  reset_time_readable: string;
}

/* ─── GlassCard ─────────────────────────────────────────────── */
function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white/[0.03] border border-white/[0.06] rounded-2xl ${className}`}>{children}</div>;
}

const TC: Record<string, string> = {
  'Red Bull': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2', 'McLaren': '#FF8000',
  'Aston Martin': '#229971', 'Alpine': '#FF87BC', 'Williams': '#64C4FF', 'Haas': '#B6BABD',
  'Kick Sauber': '#52E252', 'RB': '#6692FF', 'Racing Bulls': '#6692FF', 'Cadillac': '#1E3A5F',
};
function tc(name: string) { for (const [k, v] of Object.entries(TC)) if (name?.toLowerCase().includes(k.toLowerCase())) return v; return '#888'; }

const TYRE_IMG: Record<string, string> = { SOFT: '/images/tyres/0.0.png', MEDIUM: '/images/tyres/1.0.png', HARD: '/images/tyres/2.0.png', INTERMEDIATE: '/images/tyres/3.0.png', WET: '/images/tyres/4.0.png' };
const TYRE_COLOR: Record<string, string> = { SOFT: '#ff3333', MEDIUM: '#ffd700', HARD: '#ffffff', INTERMEDIATE: '#43b02a', WET: '#0067ff' };
const TYRE_BG: Record<string, string> = { SOFT: 'rgba(255,51,51,0.12)', MEDIUM: 'rgba(255,215,0,0.12)', HARD: 'rgba(255,255,255,0.08)', INTERMEDIATE: 'rgba(67,176,42,0.12)', WET: 'rgba(0,103,255,0.12)' };

const TIER_COLORS: Record<string, string> = {
  ELITE: '#ffd700', TOP: '#c0c0c0', STRONG: '#cd7f32', MID: '#6692FF', DEVELOPING: '#888',
};
const BOOST_LABELS: Record<string, { name: string; icon: string }> = {
  news: { name: 'News', icon: '📰' },
  circuit: { name: 'Circuit', icon: '🏎️' },
  quali_pace: { name: 'Quali', icon: '⏱️' },
  elo: { name: 'Elo', icon: '♟️' },
  constructor: { name: 'Team', icon: '🏗️' },
  pressure: { name: 'Pressure', icon: '🎯' },
  weather: { name: 'Weather', icon: '🌧️' },
  pit_stops: { name: 'Pits', icon: '🔧' },
};

type SubTab = 'race' | 'strategy' | 'tyres' | 'elo';

/* ─── Loading overlay ────────────────────────────────────────── */
function LoadingOverlay() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="relative">
        <div className="w-20 h-20 border-4 border-green-500/20 rounded-full" />
        <div className="absolute inset-0 w-20 h-20 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
        <Brain size={28} className="absolute inset-0 m-auto text-green-400" />
      </div>
      <div className="mt-6 text-center">
        <h3 className="text-lg font-bold text-white mb-1">Running Prediction Model</h3>
        <p className="text-sm text-gray-500">Analyzing qualifying data, historical performance, and circuit characteristics...</p>
      </div>
      <div className="flex gap-1 mt-4">
        {[0, 1, 2].map(i => (
          <div key={i} className="w-2 h-2 rounded-full bg-green-500 animate-bounce" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
    </div>
  );
}

/* ─── Stat Box ───────────────────────────────────────────────── */
function StatBox({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{label}</div>
      <div className="text-lg font-black mt-1" style={color ? { color } : {}}>{value}</div>
      {sub && <div className="text-[10px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function PredictionsPage() {
  const [selectedSeason, setSelectedSeason] = useState(2026);
  const [selectedRound, setSelectedRound] = useState(1);
  const [sessionType, setSessionType] = useState('R');
  const [subTab, setSubTab] = useState<SubTab>('race');
  const [expandedDriver, setExpandedDriver] = useState<string | null>(null);

  const { data: seasons } = useQuery({ queryKey: ['seasons'], queryFn: () => api.getSeasons() });
  const { data: events } = useQuery({ queryKey: ['events', selectedSeason], queryFn: () => api.getEvents(selectedSeason), enabled: !!selectedSeason });

  const { data: predictionData, refetch: refetchPredictions, isFetching, isError, error } = useQuery({
    queryKey: ['predictions', selectedSeason, selectedRound, sessionType],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/predictions/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ season: selectedSeason, round: selectedRound, session_type: sessionType }),
      });
      if (response.status === 429) {
        // Rate limit exceeded - parse the detailed error
        const errorData = await response.json();
        const err = new Error(errorData.detail?.message || 'Rate limit exceeded') as Error & { rateLimitInfo?: RateLimitError };
        err.rateLimitInfo = errorData.detail;
        throw err;
      }
      if (!response.ok) throw new Error('Prediction failed');
      return response.json();
    },
    enabled: false,
    retry: 1,
  });

  const predictions = predictionData?.predictions || [];
  const hasPredictions = predictions.length > 0;
  const boostsActive = predictionData?.boosts_active || [];
  const eloRankings = predictionData?.elo_rankings || [];

  const { data: eloData } = useQuery({
    queryKey: ['elo-rankings'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/predictions/elo-rankings?top=30`);
      if (!response.ok) return null;
      return response.json();
    },
  });

  const { data: boostsInfo } = useQuery({
    queryKey: ['boosts-info'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/predictions/boosts-info`);
      if (!response.ok) return null;
      return response.json();
    },
  });

  // AI Providers info
  const { data: aiProviders } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/predictions/ai-providers`);
      if (!response.ok) return null;
      return response.json();
    },
  });

  // Strategy data fetches automatically when season/round changes
  const { data: strategyData, isFetching: strategyLoading } = useQuery({
    queryKey: ['strategy', selectedSeason, selectedRound],
    queryFn: async () => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/strategy/strategy?season=${selectedSeason}&round=${selectedRound}`
      );
      if (!response.ok) return null;
      return response.json();
    },
  });

  const circuitProfile = strategyData?.circuit_profile;
  const teamCompounds = strategyData?.team_compounds || [];
  const driverStrategies = strategyData?.driver_strategies || [];
  const dataQuality = strategyData?.data_quality || 'no_data';

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#001a0d] via-[#0d1a15] to-[#0a192f] p-5 md:p-10 border border-white/5">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-12 w-56 h-56 bg-green-500 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 left-8 w-40 h-40 bg-emerald-500 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <Brain size={22} className="text-white" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Race Predictions</h1>
          </div>
          <p className="text-gray-400 max-w-2xl">ML-powered race outcome predictions with circuit-specific tyre strategy analysis based on your ingested historical data.</p>
          <p className="text-[11px] text-gray-500 mt-2 flex items-center gap-1.5">
            <Clock size={12} />
            <span>Rate limited to 3 predictions per 3 hours to conserve AI API credits.</span>
          </p>
          {/* Multi-AI System Banner */}
          {aiProviders && (
            <div className="mt-6 bg-white/[0.03] rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-3">
                <Zap size={16} className="text-yellow-400" />
                <span className="text-sm font-bold text-white">Powered by Multi-AI Consensus Engine</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {aiProviders.providers?.map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-1.5 bg-white/[0.05] rounded-lg px-3 py-1.5 border border-white/10">
                    <span className="text-sm">{p.icon}</span>
                    <div>
                      <span className="text-xs font-bold text-white">{p.name}</span>
                      <span className="text-[10px] text-gray-500 ml-1">({p.role})</span>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-gray-500 mt-2">
                Our predictions combine 5 specialized AI models: 2× Gemini Pro, 1× DeepSeek, 2× Groq Mixtral — each analyzing different aspects of race outcomes.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Config Panel */}
      <GlassCard className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase">Season</label>
            <select value={selectedSeason} onChange={e => { setSelectedSeason(+e.target.value); setSelectedRound(1); }}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm font-bold focus:outline-none focus:border-green-500">
              {(seasons || []).sort((a: number, b: number) => b - a).map((s: number) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase">Race</label>
            <select value={selectedRound} onChange={e => setSelectedRound(+e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm font-bold focus:outline-none focus:border-green-500">
              {events?.map((ev: any) => (
                <option key={ev.round} value={ev.round}>
                  R{ev.round}: {ev.event_name}{(ev.has_sprint || String(ev.event_format || '').toLowerCase().includes('sprint')) ? ' • Sprint Weekend' : ''}
                </option>
              )) || <option value={1}>Round 1</option>}
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase">Session</label>
            <div className="grid grid-cols-4 gap-1">
              {[{ k: 'R', l: 'Race' }, { k: 'Q', l: 'Qual' }, { k: 'S', l: 'Sprint' }, { k: 'P', l: 'FP' }].map(t => (
                <button key={t.k} onClick={() => setSessionType(t.k)}
                  className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                    sessionType === t.k ? 'bg-green-600 text-white shadow-lg shadow-green-500/20' : 'bg-white/5 text-gray-500 hover:text-white hover:bg-white/10'
                  }`}>{t.l}</button>
              ))}
            </div>
          </div>
        </div>
        <button onClick={() => refetchPredictions()} disabled={isFetching}
          className="mt-5 bg-gradient-to-r from-green-600 to-emerald-600 hover:brightness-110 disabled:opacity-50 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg shadow-green-500/20 flex items-center gap-2 text-sm">
          {isFetching ? <><Loader2 size={16} className="animate-spin" /> Running Model...</> : <><BarChart3 size={16} /> Run Prediction</>}
        </button>
      </GlassCard>

      {/* Sub-tabs */}
      <div className="flex bg-white/5 rounded-xl p-1 border border-white/5 w-full md:w-fit overflow-x-auto">
        {([
          { key: 'race', label: 'Race Winner', icon: <Trophy size={14} /> },
          { key: 'elo', label: 'Elo Ratings', icon: <Star size={14} /> },
          { key: 'strategy', label: 'Pit Strategy', icon: <Timer size={14} /> },
          { key: 'tyres', label: 'Tyre Prediction', icon: <Layers size={14} /> },
        ] as { key: SubTab; label: string; icon: React.ReactNode }[]).map(t => (
          <button key={t.key} onClick={() => setSubTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
              subTab === t.key ? 'bg-white/10 text-white shadow' : 'text-gray-500 hover:text-white'
            }`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {isFetching && <LoadingOverlay />}

      {isError && !isFetching && (
        <GlassCard className="p-6 border-red-500/20">
          <div className="flex items-center gap-3">
            {(error as any)?.rateLimitInfo ? (
              <>
                <Clock className="text-yellow-400" size={20} />
                <div>
                  <h3 className="font-bold text-yellow-400">Rate Limit Reached</h3>
                  <p className="text-sm text-gray-400 mt-1">{(error as any).rateLimitInfo.message}</p>
                  {(error as any).rateLimitInfo.reset_time_readable && (
                    <p className="text-xs text-gray-500 mt-2">
                      <Timer size={12} className="inline mr-1" />
                      Resets at: {(error as any).rateLimitInfo.reset_time_readable}
                    </p>
                  )}
                  <p className="text-[10px] text-gray-600 mt-2 italic">
                    Rate limiting helps us conserve AI API credits to keep this service free for everyone.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="text-red-400" size={20} />
                <div>
                  <h3 className="font-bold text-red-400">Prediction Error</h3>
                  <p className="text-sm text-gray-400 mt-1">{(error as Error)?.message || 'Failed to run prediction model.'}</p>
                </div>
              </>
            )}
          </div>
        </GlassCard>
      )}

      {/* ═══════════ RACE WINNER TAB ═══════════ */}
      {!isFetching && subTab === 'race' && (
        <>
          {!hasPredictions && (
            <div className="text-center py-16">
              <Brain size={48} className="mx-auto text-gray-700 mb-4" />
              <h3 className="text-lg font-bold mb-2">No Predictions Yet</h3>
              <p className="text-gray-500 text-sm">Select a race and click &quot;Run Prediction&quot; to generate ML predictions.</p>
            </div>
          )}
          {hasPredictions && (
            <div className="space-y-3">
              {boostsActive.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-2 px-2">
                  <Shield size={14} className="text-green-400" />
                  <span className="text-xs text-gray-400 font-bold">Active Boosts:</span>
                  {boostsActive.map((b: string) => (
                    <span key={b} className="text-[10px] font-bold px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20">
                      {BOOST_LABELS[b]?.icon || '⚡'} {BOOST_LABELS[b]?.name || b}
                    </span>
                  ))}
                </div>
              )}
              {predictions.map((pred: any, idx: number) => {
                const color = tc(pred.team || pred.constructor_name || '');
                const isActual = pred.confidence === 'actual_result';
                const pct = isActual ? (100 - idx * 8) : ((pred.probability || 0) * 100);
                const isExpanded = expandedDriver === pred.driver_code;
                const hasBoosts = pred.boosts && Object.keys(pred.boosts).length > 0;
                return (
                  <GlassCard key={pred.driver_code} className="p-5 hover:border-white/10 transition-all">
                    <div className="flex items-center gap-4 cursor-pointer" onClick={() => setExpandedDriver(isExpanded ? null : pred.driver_code)}>
                      <div className="w-8 text-center">
                        {idx === 0 ? <span className="text-yellow-400 text-lg">🥇</span> :
                         idx === 1 ? <span className="text-gray-300 text-lg">🥈</span> :
                         idx === 2 ? <span className="text-amber-600 text-lg">🥉</span> :
                         <span className="text-gray-600 font-bold text-sm">{idx + 1}</span>}
                      </div>
                      <div className="w-1 h-10 rounded-full" style={{ backgroundColor: color }} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{pred.driver_name || pred.driver_code}</span>
                          {pred.elo_tier && (
                            <span className="text-[9px] font-black px-1.5 py-0.5 rounded border"
                              style={{ color: TIER_COLORS[pred.elo_tier] || '#888', borderColor: (TIER_COLORS[pred.elo_tier] || '#888') + '44' }}>
                              {pred.elo_tier}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span>{pred.team || pred.constructor_name || ''}</span>
                          {pred.elo_rating && (
                            <span className="text-[10px]" style={{ color: TIER_COLORS[pred.elo_tier] || '#888' }}>
                              ♟️ {pred.elo_rating}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex items-center gap-2">
                        {isActual ? (
                          <span className="text-2xl font-black text-blue-400">P{idx + 1}</span>
                        ) : (
                          <span className="text-2xl font-black" style={{ color }}>{pct.toFixed(0)}%</span>
                        )}
                        {hasBoosts && (isExpanded ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />)}
                      </div>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full mt-3 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: isActual ? '#3b82f6' : color }} />
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      {!isActual && pred.confidence && (
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          pred.confidence === 'high' ? 'bg-green-500/10 text-green-400' :
                          pred.confidence === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                          'bg-red-500/10 text-red-400'
                        }`}>{String(pred.confidence).toUpperCase()}</span>
                      )}
                      {pred.groq?.ai_source === 'multi_ai_consensus' ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1">
                          <Zap size={10} /> Multi-AI {pred.groq.confidence_score ? `(${Math.round(pred.groq.confidence_score * 100)}% conf)` : ''}
                        </span>
                      ) : pred.groq?.probability && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                          {pred.groq.ai_source || 'AI'} {Math.round((pred.groq.probability || 0) * 100)}%
                        </span>
                      )}
                      {pred.groq?.explanation && (
                        <span className="text-[10px] text-gray-400 truncate max-w-[220px]">
                          {pred.groq.explanation}
                        </span>
                      )}
                      {hasBoosts && !isExpanded && (
                        <div className="flex gap-1 ml-auto">
                          {Object.entries(pred.boosts as Record<string, number>).map(([key, val]) => (
                            <span key={key} className={`text-[9px] px-1 rounded ${Number(val) > 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                              {BOOST_LABELS[key]?.icon || '⚡'}{Number(val) > 0 ? '+' : ''}{(Number(val) * 100).toFixed(1)}%
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {isExpanded && hasBoosts && (
                      <div className="mt-3 pt-3 border-t border-white/5 space-y-2">
                        <div className="text-[10px] text-gray-500 font-bold uppercase mb-2">Boost Breakdown</div>
                        {Object.entries(pred.boosts as Record<string, number>).map(([key, val]) => {
                          const pctVal = Number(val) * 100;
                          const isPositive = pctVal > 0;
                          return (
                            <div key={key} className="flex items-center gap-2">
                              <span className="text-xs w-6">{BOOST_LABELS[key]?.icon || '⚡'}</span>
                              <span className="text-xs text-gray-400 w-16">{BOOST_LABELS[key]?.name || key}</span>
                              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden relative">
                                <div className="absolute inset-y-0 left-1/2 w-px bg-gray-600" />
                                {isPositive ? (
                                  <div className="absolute inset-y-0 left-1/2 bg-green-500 rounded-r-full" style={{ width: `${Math.min(pctVal * 8, 50)}%` }} />
                                ) : (
                                  <div className="absolute inset-y-0 right-1/2 bg-red-500 rounded-l-full" style={{ width: `${Math.min(Math.abs(pctVal) * 8, 50)}%` }} />
                                )}
                              </div>
                              <span className={`text-xs font-bold w-14 text-right ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                {isPositive ? '+' : ''}{pctVal.toFixed(2)}%
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                    {/* Multi-AI Consensus Breakdown */}
                    {isExpanded && pred.groq?.ai_source === 'multi_ai_consensus' && pred.groq?.explanations && (
                      <div className="mt-3 pt-3 border-t border-white/5 space-y-2">
                        <div className="text-[10px] text-gray-500 font-bold uppercase mb-2 flex items-center gap-2">
                          <Zap size={12} className="text-purple-400" /> AI Analysis Breakdown
                        </div>
                        {Object.entries(pred.groq.explanations as Record<string, string>).map(([role, explanation]) => (
                          <div key={role} className="bg-white/[0.02] rounded-lg p-2 border border-white/5">
                            <div className="text-[10px] font-bold text-purple-400 mb-1">
                              {role.includes('Strategy') ? '🎯' : role.includes('Data') ? '📊' : role.includes('Reasoning') ? '🧠' : '⚡'} {role}
                            </div>
                            <div className="text-[11px] text-gray-400 leading-relaxed">
                              {String(explanation).slice(0, 200)}{String(explanation).length > 200 ? '...' : ''}
                            </div>
                          </div>
                        ))}
                        {pred.groq?.providers && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            <span className="text-[9px] text-gray-600">Providers:</span>
                            {(pred.groq.providers as string[]).map((p, i) => (
                              <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300">
                                {p}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </GlassCard>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ═══════════ ELO RATINGS TAB ═══════════ */}
      {!isFetching && subTab === 'elo' && (
        <GlassCard className="p-6">
          <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
            <Star size={18} className="text-yellow-400" /> F1 Elo Ratings
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Chess-inspired Elo system: every driver starts at 1500. Winning against higher-rated drivers earns more points.
          </p>
          <div className="flex flex-wrap gap-3 mb-6">
            {Object.entries(TIER_COLORS).map(([tier, color]) => (
              <div key={tier} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-[10px] font-black" style={{ color }}>{tier}</span>
                <span className="text-[9px] text-gray-600">
                  {tier === 'ELITE' ? '1800+' : tier === 'TOP' ? '1650+' : tier === 'STRONG' ? '1500+' : tier === 'MID' ? '1350+' : '<1350'}
                </span>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {(eloData?.rankings || eloRankings || []).slice(0, 20).map((d: any, i: number) => {
              const tierColor = TIER_COLORS[d.tier] || '#888';
              const ratingPct = ((d.rating - 1200) / 800) * 100;
              return (
                <div key={d.driver_code || d.code} className="flex items-center gap-3 py-2.5 px-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-all border border-white/[0.03]">
                  <span className="text-xs font-bold text-gray-600 w-6 text-center">{d.rank || i + 1}</span>
                  <div className="w-1 h-8 rounded-full" style={{ backgroundColor: tierColor }} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold">{d.driver_code || d.code}</span>
                      <span className="text-[9px] font-black px-1.5 py-0.5 rounded border" style={{ color: tierColor, borderColor: tierColor + '44' }}>{d.tier}</span>
                    </div>
                    <div className="text-[10px] text-gray-500">{d.races || d.races_completed} races · {d.wins} wins</div>
                  </div>
                  <div className="w-32">
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(ratingPct, 100)}%`, backgroundColor: tierColor }} />
                    </div>
                  </div>
                  <div className="text-right w-16">
                    <div className="text-sm font-black" style={{ color: tierColor }}>{d.rating}</div>
                    <div className="text-[9px] text-gray-600">peak {d.peak || d.peak_rating}</div>
                  </div>
                </div>
              );
            })}
          </div>
          {(!eloData?.rankings && !eloRankings?.length) && (
            <div className="text-center py-12">
              <Star size={36} className="mx-auto text-gray-700 mb-3" />
              <p className="text-gray-500 text-sm">Run a prediction first to see Elo ratings.</p>
            </div>
          )}
        </GlassCard>
      )}

      {/* ═══════════ PIT STRATEGY TAB ═══════════ */}
      {!isFetching && subTab === 'strategy' && (
        <>
          {strategyLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-blue-400 mr-3" />
              <span className="text-gray-400">Analyzing historical pit data...</span>
            </div>
          )}

          {!strategyLoading && !circuitProfile && (
            <div className="text-center py-16">
              <Timer size={48} className="mx-auto text-gray-700 mb-4" />
              <h3 className="text-lg font-bold mb-2">No Strategy Data</h3>
              <p className="text-gray-500 text-sm">Select a race to see circuit-specific pit strategy predictions.</p>
            </div>
          )}

          {!strategyLoading && circuitProfile && (
            <div className="space-y-6">
              {/* Circuit Profile Header */}
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold flex items-center gap-2">
                      <Timer size={18} className="text-blue-400" /> {circuitProfile.circuit_name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      Based on {circuitProfile.historical_races_analyzed} historical races · {circuitProfile.total_laps} laps
                    </p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                    dataQuality === 'rich' ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                    dataQuality === 'moderate' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                    'bg-orange-500/10 text-orange-400 border border-orange-500/20'
                  }`}>
                    {dataQuality === 'rich' ? 'HIGH CONFIDENCE' : dataQuality === 'moderate' ? 'MODERATE' : 'LIMITED DATA'}
                  </span>
                </div>

                {/* Key Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatBox label="Avg Pit Stops" value={String(circuitProfile.avg_pit_stops)} sub="per driver" color="#3b82f6" />
                  <StatBox label="Race Length" value={`${circuitProfile.total_laps} laps`} sub="full distance" />
                  {circuitProfile.typical_pit_windows?.[0] && (
                    <StatBox label="1st Pit Window" value={`Lap ${circuitProfile.typical_pit_windows[0].window_start}-${circuitProfile.typical_pit_windows[0].window_end}`} sub={`avg lap ${circuitProfile.typical_pit_windows[0].avg_lap}`} color="#f59e0b" />
                  )}
                  {circuitProfile.typical_pit_windows?.[1] && (
                    <StatBox label="2nd Pit Window" value={`Lap ${circuitProfile.typical_pit_windows[1].window_start}-${circuitProfile.typical_pit_windows[1].window_end}`} sub={`avg lap ${circuitProfile.typical_pit_windows[1].avg_lap}`} color="#f59e0b" />
                  )}
                </div>

                {/* Pit Window Timeline */}
                <div className="mt-5">
                  <div className="text-[10px] text-gray-500 font-bold uppercase mb-2">Pit Stop Windows</div>
                  <div className="relative h-8 bg-gray-800/50 rounded-lg overflow-hidden border border-white/5">
                    {[...Array(Math.ceil(circuitProfile.total_laps / 10))].map((_, i) => (
                      <div key={i} className="absolute top-0 bottom-0 w-px bg-white/5" style={{ left: `${(i * 10 / circuitProfile.total_laps) * 100}%` }}>
                        <span className="absolute -bottom-4 text-[8px] text-gray-600 -translate-x-1/2">{i * 10}</span>
                      </div>
                    ))}
                    {(circuitProfile.typical_pit_windows || []).map((pw: any, i: number) => {
                      const colors = ['#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'];
                      return (
                        <div key={i} className="absolute top-1 bottom-1 rounded-md flex items-center justify-center"
                          style={{
                            left: `${(pw.window_start / circuitProfile.total_laps) * 100}%`,
                            width: `${Math.max(((pw.window_end - pw.window_start) / circuitProfile.total_laps) * 100, 4)}%`,
                            backgroundColor: colors[i % colors.length] + '33',
                            border: `1px solid ${colors[i % colors.length]}55`,
                          }}>
                          <span className="text-[9px] font-bold" style={{ color: colors[i % colors.length] }}>Stop {pw.stop_number}</span>
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex justify-between mt-5 text-[8px] text-gray-600">
                    <span>Lap 0</span>
                    <span>Lap {circuitProfile.total_laps}</span>
                  </div>
                </div>
              </GlassCard>

              {/* Driver Strategies */}
              <GlassCard className="p-6">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Fuel size={14} className="text-blue-400" /> Predicted Strategy per Driver
                </h3>
                <div className="space-y-2">
                  {driverStrategies.map((drv: any) => {
                    const totalLaps = drv.predicted_stints.reduce((s: number, st: any) => s + st.avg_laps, 0) || 1;
                    return (
                      <div key={drv.driver_code} className="flex items-center gap-3 py-2.5 px-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.03] transition-all">
                        <div className="w-1 h-8 rounded-full" style={{ backgroundColor: drv.team_color }} />
                        <div className="w-20 shrink-0">
                          <div className="text-sm font-bold">{drv.driver_code}</div>
                          <div className="text-[9px] text-gray-600 truncate">{drv.team}</div>
                        </div>
                        <div className="flex-1 flex h-7 rounded-lg overflow-hidden border border-white/5">
                          {drv.predicted_stints.map((stint: any, si: number) => (
                            <div key={si} className="flex items-center justify-center gap-1 text-[9px] font-bold"
                              style={{
                                width: `${(stint.avg_laps / totalLaps) * 100}%`,
                                backgroundColor: TYRE_BG[stint.compound] || 'rgba(255,255,255,0.05)',
                                color: TYRE_COLOR[stint.compound] || '#888',
                                borderRight: si < drv.predicted_stints.length - 1 ? '1px solid rgba(255,255,255,0.1)' : 'none',
                              }}>
                              <span>{stint.compound.charAt(0)}</span>
                              <span className="opacity-70">{Math.round(stint.avg_laps)}L</span>
                            </div>
                          ))}
                        </div>
                        <div className="text-right w-24 shrink-0">
                          <div className="text-xs font-bold text-gray-300">{drv.predicted_stops} stop{drv.predicted_stops !== 1 ? 's' : ''}</div>
                          <div className="text-[9px] text-gray-600">{drv.pit_laps.length > 0 ? `Lap ${drv.pit_laps.join(', ')}` : ''}</div>
                        </div>
                        <div className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                          drv.confidence === 'high' ? 'bg-green-500/10 text-green-400' :
                          drv.confidence === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                          'bg-gray-500/10 text-gray-500'
                        }`}>
                          {drv.confidence.charAt(0).toUpperCase() + drv.confidence.slice(1)}
                        </div>
                      </div>
                    );
                  })}
                </div>
                {driverStrategies.length === 0 && (
                  <p className="text-gray-500 text-sm text-center py-8">No strategy data for this circuit.</p>
                )}
              </GlassCard>
            </div>
          )}
        </>
      )}

      {/* ═══════════ TYRE PREDICTION TAB ═══════════ */}
      {!isFetching && subTab === 'tyres' && (
        <>
          {strategyLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-yellow-400 mr-3" />
              <span className="text-gray-400">Analyzing historical tyre data...</span>
            </div>
          )}

          {!strategyLoading && !circuitProfile && (
            <div className="text-center py-16">
              <Layers size={48} className="mx-auto text-gray-700 mb-4" />
              <h3 className="text-lg font-bold mb-2">No Tyre Data</h3>
              <p className="text-gray-500 text-sm">Select a race to see circuit-specific tyre compound predictions.</p>
            </div>
          )}

          {!strategyLoading && circuitProfile && (
            <div className="space-y-6">
              {/* Compound Usage Overview */}
              <GlassCard className="p-6">
                <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
                  <Layers size={18} className="text-yellow-400" /> Circuit Tyre Profile — {circuitProfile.circuit_name}
                </h3>
                <p className="text-xs text-gray-500 mb-5">
                  Compound usage from {circuitProfile.historical_races_analyzed} historical races
                </p>

                {/* Compound bars */}
                <div className="space-y-3 mb-6">
                  {Object.entries(circuitProfile.compound_usage as Record<string, number>)
                    .filter(([comp]) => ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'].includes(comp))
                    .sort(([, a], [, b]) => b - a)
                    .map(([compound, pct]) => (
                      <div key={compound} className="flex items-center gap-3">
                        <div className="w-8 h-8 relative shrink-0">
                          {TYRE_IMG[compound] && <Image src={TYRE_IMG[compound]} alt={compound} width={32} height={32} className="object-contain" />}
                        </div>
                        <span className="text-xs font-bold w-24 shrink-0" style={{ color: TYRE_COLOR[compound] || '#888' }}>{compound}</span>
                        <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${pct}%`, backgroundColor: TYRE_COLOR[compound] || '#888' }} />
                        </div>
                        <span className="text-sm font-bold w-14 text-right text-gray-300">{pct.toFixed(1)}%</span>
                      </div>
                    ))}
                </div>

                {/* Stint + Degradation */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white/[0.02] rounded-xl p-4 border border-white/5">
                    <h4 className="text-sm font-bold text-gray-400 mb-3">Average Stint Length</h4>
                    <div className="space-y-2.5">
                      {Object.entries(circuitProfile.avg_stint_lengths as Record<string, number>)
                        .filter(([comp]) => ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'].includes(comp))
                        .sort(([, a], [, b]) => b - a)
                        .map(([compound, avgLaps]) => (
                          <div key={compound} className="flex items-center gap-2">
                            <div className="w-5 h-5 relative shrink-0">
                              {TYRE_IMG[compound] && <Image src={TYRE_IMG[compound]} alt={compound} width={20} height={20} className="object-contain" />}
                            </div>
                            <span className="text-xs font-bold w-16" style={{ color: TYRE_COLOR[compound] }}>{compound}</span>
                            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${(avgLaps / circuitProfile.total_laps) * 100}%`, backgroundColor: TYRE_COLOR[compound] }} />
                            </div>
                            <span className="text-xs text-gray-400 w-14 text-right font-mono">{avgLaps.toFixed(0)} laps</span>
                          </div>
                        ))}
                    </div>
                  </div>
                  <div className="bg-white/[0.02] rounded-xl p-4 border border-white/5">
                    <h4 className="text-sm font-bold text-gray-400 mb-3">Estimated Degradation</h4>
                    <div className="space-y-2.5">
                      {Object.entries(circuitProfile.degradation_rates as Record<string, number>)
                        .filter(([comp]) => ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'].includes(comp))
                        .sort(([, a], [, b]) => b - a)
                        .map(([compound, deg]) => (
                          <div key={compound} className="flex items-center gap-2">
                            <div className="w-5 h-5 relative shrink-0">
                              {TYRE_IMG[compound] && <Image src={TYRE_IMG[compound]} alt={compound} width={20} height={20} className="object-contain" />}
                            </div>
                            <span className="text-xs font-bold w-16" style={{ color: TYRE_COLOR[compound] }}>{compound}</span>
                            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${(deg / 2) * 100}%`, backgroundColor: TYRE_COLOR[compound] }} />
                            </div>
                            <span className="text-xs text-gray-400 w-16 text-right font-mono">{deg.toFixed(1)}%/lap</span>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              </GlassCard>

              {/* Team Compound Predictions */}
              <GlassCard className="p-6">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Zap size={14} className="text-yellow-400" /> Team Compound Predictions
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {teamCompounds.map((team: any) => (
                    <div key={team.team} className="bg-white/[0.02] rounded-xl p-4 border border-white/5 hover:border-white/10 transition-all">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-1.5 h-6 rounded-full" style={{ backgroundColor: team.team_color }} />
                        <div className="flex-1">
                          <div className="text-sm font-bold">{team.team}</div>
                          <div className="text-[9px] text-gray-600">{team.drivers.join(' · ')}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] text-gray-500 w-12">Start:</span>
                        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md" style={{ backgroundColor: TYRE_BG[team.most_likely_start] }}>
                          <div className="w-4 h-4 relative">
                            {TYRE_IMG[team.most_likely_start] && <Image src={TYRE_IMG[team.most_likely_start]} alt={team.most_likely_start} width={16} height={16} className="object-contain" />}
                          </div>
                          <span className="text-[11px] font-bold" style={{ color: TYRE_COLOR[team.most_likely_start] }}>{team.most_likely_start}</span>
                        </div>
                        <span className="text-[10px] text-gray-500 ml-auto">{(team.start_probability * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-500 w-12">Strategy:</span>
                        <div className="flex items-center gap-1">
                          {team.most_likely_strategy.split(' → ').map((comp: string, i: number, arr: string[]) => (
                            <span key={i} className="flex items-center gap-0.5">
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: TYRE_BG[comp] || 'rgba(255,255,255,0.05)', color: TYRE_COLOR[comp] || '#888' }}>{comp}</span>
                              {i < arr.length - 1 && <span className="text-gray-600 text-[10px] mx-0.5">→</span>}
                            </span>
                          ))}
                        </div>
                        <span className="text-[10px] text-gray-500 ml-auto">{(team.strategy_probability * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex h-1.5 rounded-full overflow-hidden mt-3">
                        {Object.entries(team.compound_distribution as Record<string, number>)
                          .filter(([comp]) => ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'].includes(comp))
                          .sort(([, a], [, b]) => b - a)
                          .map(([comp, pct]) => (
                            <div key={comp} style={{ width: `${pct}%`, backgroundColor: TYRE_COLOR[comp] || '#888' }} />
                          ))}
                      </div>
                    </div>
                  ))}
                </div>
                {teamCompounds.length === 0 && (
                  <p className="text-gray-500 text-sm text-center py-8">No team data for this circuit.</p>
                )}
              </GlassCard>
            </div>
          )}
        </>
      )}

      {/* Model Info */}
      <GlassCard className="p-6">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap size={14} className="text-green-400" /> Model Information
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Algorithm', value: 'GBM + Elo', sub: '9-Boost Engine' },
            { label: 'Training Data', value: 'Ingested DB', sub: 'Coverage depends on loaded seasons' },
            { label: 'Boost Layers', value: '9 active', sub: 'Max ±27.5%' },
            { label: 'Version', value: predictionData?.model_version || 'v2.0 + Elo', sub: 'Latest' },
          ].map(m => (
            <div key={m.label} className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
              <div className="text-[10px] text-gray-500 font-bold uppercase">{m.label}</div>
              <div className="text-sm font-bold mt-1">{m.value}</div>
              <div className="text-[10px] text-gray-600">{m.sub}</div>
            </div>
          ))}
        </div>
        {boostsInfo?.boosts && (
          <div className="space-y-2">
            <div className="text-[10px] text-gray-500 font-bold uppercase mb-2">All Prediction Boosts</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {boostsInfo.boosts.map((b: any) => (
                <div key={b.id} className="flex items-start gap-2 bg-white/[0.02] rounded-lg p-3 border border-white/5">
                  <span className="text-sm">{BOOST_LABELS[b.id]?.icon || '⚡'}</span>
                  <div>
                    <div className="text-xs font-bold">{b.name}</div>
                    <div className="text-[10px] text-gray-500">{b.description}</div>
                    <div className="text-[9px] text-green-400 font-bold mt-0.5">{b.max_impact}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
