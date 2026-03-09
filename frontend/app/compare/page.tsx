'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import { Trophy, Zap, Users, Award, Crown, Shield } from 'lucide-react';
import api from '@/lib/api';
import { Driver, DriverStanding } from '@/lib/types';
import { getTeamColor } from '@/lib/tracks';

const TC: Record<string, string> = {
  'Red Bull': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2', 'McLaren': '#FF8000',
  'Aston Martin': '#229971', 'Alpine': '#FF87BC', 'Williams': '#64C4FF', 'Haas': '#B6BABD',
  'Kick Sauber': '#52E252', 'RB': '#6692FF', 'Racing Bulls': '#6692FF', 'Cadillac': '#FFD700',
  'Audi': '#990000', 'Racing Point': '#F596C8', 'Force India': '#F596C8', 'Renault': '#FFF500',
  'Toro Rosso': '#469BFF', 'Lotus': '#FFB800', 'Brawn': '#D2FF00',
};
function tc(name: string) {
  if (!name) return '#888';
  for (const [k, v] of Object.entries(TC)) if (name.toLowerCase().includes(k.toLowerCase())) return v;
  return getTeamColor(name) || '#888';
}

type Mode = 'drivers' | 'constructors';

export default function ComparePage() {
  const [mode, setMode] = useState<Mode>('drivers');
  const [season, setSeason] = useState<number>(2025);
  const [driverA, setDriverA] = useState('');
  const [driverB, setDriverB] = useState('');
  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');

  const { data: seasons } = useQuery({ queryKey: ['seasons'], queryFn: () => api.getSeasons() });
  const { data: drivers, isLoading: driversLoading } = useQuery({
    queryKey: ['drivers', season], queryFn: () => api.getDrivers(season), enabled: !!season,
  });
  const { data: standings, isLoading: standingsLoading } = useQuery<DriverStanding[]>({
    queryKey: ['standings', season], queryFn: () => api.getStandings(season), enabled: !!season,
  });
  const { data: constructorStandings } = useQuery({
    queryKey: ['constructorStandings', season], queryFn: () => api.getConstructorStandings(season), enabled: !!season,
  });

  const driverOptions = useMemo(() => {
    if (!drivers) return [];
    return [...drivers].sort((a, b) => {
      const sa = standings?.find(s => s.driver_code === a.driver_code);
      const sb = standings?.find(s => s.driver_code === b.driver_code);
      if (sa && sb) return (sb.total_points ?? 0) - (sa.total_points ?? 0);
      if (sa) return -1; if (sb) return 1;
      return (a.last_name || '').localeCompare(b.last_name || '');
    });
  }, [drivers, standings]);

  const handleSeasonChange = (s: number) => { setSeason(s); setDriverA(''); setDriverB(''); setTeamA(''); setTeamB(''); };

  const selA = driverOptions.find(d => d.driver_code === driverA);
  const selB = driverOptions.find(d => d.driver_code === driverB);
  const stdA = standings?.find(s => s.driver_code === driverA);
  const stdB = standings?.find(s => s.driver_code === driverB);
  const cA = constructorStandings?.find((t: any) => t.constructor_name === teamA);
  const cB = constructorStandings?.find((t: any) => t.constructor_name === teamB);

  const colorA = selA ? tc(selA.team_name || '') : '#3b82f6';
  const colorB = selB ? tc(selB.team_name || '') : '#ef4444';

  const pts = (t: any) => t?.total_points || t?.points || 0;

  return (
    <div className="space-y-10">
      {/* ══════ HERO ══════ */}
      <section className="relative overflow-hidden rounded-3xl">
        <div className="absolute inset-0 bg-gradient-to-br from-[#15002a] via-[#0d1020] to-[#080a0f]" />
        <div className="absolute top-[-30%] left-[-10%] w-[50vw] h-[50vw] bg-orange-600/[0.06] rounded-full blur-[180px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[40vw] h-[40vw] bg-blue-600/[0.06] rounded-full blur-[140px]" />
        <div className="relative z-10 px-5 py-8 md:px-16 md:py-20">
          <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase mb-4">Formula 1</div>
          <h1 className="text-5xl md:text-6xl font-black tracking-tight text-white mb-3">
            Head-to-<br />Head
          </h1>
          <p className="text-gray-500 text-lg max-w-xl">
            The ultimate showdown. Pick two rivals and see who dominates.
          </p>
        </div>
      </section>

      {/* ══════ CONTROLS ══════ */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex bg-white/[0.03] rounded-2xl p-1 border border-white/[0.06]">
          {(['drivers', 'constructors'] as Mode[]).map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-5 py-2 rounded-xl text-xs font-black tracking-wide transition-all uppercase ${
                mode === m ? 'bg-red-600 text-white shadow-lg shadow-red-600/25' : 'text-gray-500 hover:text-white'
              }`}>
              {m}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 bg-white/[0.03] rounded-2xl px-4 py-2 border border-white/[0.06]">
          <span className="text-[10px] text-gray-600 font-black tracking-[0.2em]">SEASON</span>
          <select value={season} onChange={e => handleSeasonChange(+e.target.value)}
            className="bg-transparent text-white text-sm font-black focus:outline-none cursor-pointer">
            {seasons?.slice().sort((a: number, b: number) => b - a).map((s: number) => (
              <option key={s} value={s} className="bg-gray-900">{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ══════ DRIVER MODE ══════ */}
      {mode === 'drivers' && (
        <>
          {/* Selectors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { label: 'Driver A', value: driverA, set: setDriverA, exclude: driverB },
              { label: 'Driver B', value: driverB, set: setDriverB, exclude: driverA },
            ].map(sel => {
              const d = driverOptions.find(d => d.driver_code === sel.value);
              const c = d ? tc(d.team_name || '') : '#555';
              return (
                <div key={sel.label}>
                  <label className="block text-[10px] font-black tracking-[0.2em] mb-2 uppercase" style={{ color: c }}>{sel.label}</label>
                  <select value={sel.value} onChange={e => sel.set(e.target.value)}
                    className="w-full bg-white/[0.03] border-2 rounded-2xl px-5 py-3.5 text-sm font-bold focus:outline-none transition-all"
                    style={{ borderColor: sel.value ? c + '40' : 'rgba(255,255,255,0.06)' }}
                    disabled={driversLoading || standingsLoading}>
                    <option value="">Select driver...</option>
                    {driverOptions.filter(d => d.driver_code !== sel.exclude).map(d => (
                      <option key={d.driver_code} value={d.driver_code} className="bg-gray-900">{d.first_name} {d.last_name} — {d.team_name}</option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>

          {/* VS Cards */}
          {(selA || selB) && (
            <div className="grid grid-cols-1 md:grid-cols-[1fr_80px_1fr] gap-4 items-stretch">
              <DriverVSCard driver={selA} standing={stdA} season={season} />
              <div className="hidden md:flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-red-600 flex items-center justify-center shadow-2xl shadow-red-600/30 border-4 border-[#080a0f]">
                  <span className="text-xl font-black text-white">VS</span>
                </div>
              </div>
              <DriverVSCard driver={selB} standing={stdB} season={season} />
            </div>
          )}

          {/* Stat Bars */}
          {selA && selB && stdA && stdB && (
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 md:p-8 space-y-6 md:space-y-8">
              <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase">Statistical Breakdown</div>
              <div className="space-y-6">
                {[
                  { label: 'Points', a: stdA.total_points || 0, b: stdB.total_points || 0 },
                  { label: 'Wins', a: stdA.wins || 0, b: stdB.wins || 0 },
                  { label: 'Podiums', a: stdA.podiums || 0, b: stdB.podiums || 0 },
                  { label: 'DNFs', a: stdA.dnfs || 0, b: stdB.dnfs || 0 },
                ].map(m => {
                  const max = Math.max(m.a, m.b, 1);
                  const aWins = m.label === 'DNFs' ? m.a < m.b : m.a > m.b;
                  const bWins = m.label === 'DNFs' ? m.b < m.a : m.b > m.a;
                  return (
                    <div key={m.label}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {aWins && <Crown size={12} style={{ color: colorA }} />}
                          <span className={`text-lg font-black ${aWins ? '' : 'text-gray-700'}`} style={aWins ? { color: colorA } : {}}>{m.a}</span>
                        </div>
                        <span className="text-[10px] font-black tracking-[0.2em] text-gray-600 uppercase">{m.label}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-lg font-black ${bWins ? '' : 'text-gray-700'}`} style={bWins ? { color: colorB } : {}}>{m.b}</span>
                          {bWins && <Crown size={12} style={{ color: colorB }} />}
                        </div>
                      </div>
                      <div className="flex gap-0.5 h-5 rounded-full overflow-hidden">
                        <div className="flex-1 bg-white/[0.04] rounded-l-full overflow-hidden flex justify-end">
                          <div className="h-full rounded-l-full transition-all duration-1000"
                            style={{
                              width: `${(m.a / max) * 100}%`,
                              background: `linear-gradient(90deg, ${colorA}20, ${colorA})`,
                              boxShadow: aWins ? `0 0 20px ${colorA}40` : 'none',
                            }} />
                        </div>
                        <div className="flex-1 bg-white/[0.04] rounded-r-full overflow-hidden">
                          <div className="h-full rounded-r-full transition-all duration-1000"
                            style={{
                              width: `${(m.b / max) * 100}%`,
                              background: `linear-gradient(90deg, ${colorB}, ${colorB}20)`,
                              boxShadow: bWins ? `0 0 20px ${colorB}40` : 'none',
                            }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 border-t border-white/[0.05]">
                {[
                  { label: 'Pts Gap', value: Math.abs((stdA.total_points || 0) - (stdB.total_points || 0)), sub: ((stdA.total_points || 0) >= (stdB.total_points || 0) ? selA.driver_code : selB.driver_code) + ' leads', accent: 'text-yellow-400', border: 'border-yellow-500/15', bg: 'from-yellow-500/5' },
                  { label: 'Win Gap', value: Math.abs((stdA.wins || 0) - (stdB.wins || 0)), sub: ((stdA.wins || 0) >= (stdB.wins || 0) ? selA.driver_code : selB.driver_code) + ' leads', accent: 'text-green-400', border: 'border-green-500/15', bg: 'from-green-500/5' },
                  { label: 'Podiums', value: `${stdA.podiums || 0} — ${stdB.podiums || 0}`, sub: '', accent: 'text-blue-400', border: 'border-blue-500/15', bg: 'from-blue-500/5' },
                  { label: 'DNFs', value: `${stdA.dnfs || 0} — ${stdB.dnfs || 0}`, sub: '', accent: 'text-red-400', border: 'border-red-500/15', bg: 'from-red-500/5' },
                ].map(t => (
                  <div key={t.label} className={`bg-gradient-to-br ${t.bg} to-transparent border ${t.border} rounded-2xl p-4 text-center`}>
                    <div className={`text-[10px] ${t.accent} font-black tracking-[0.15em] uppercase`}>{t.label}</div>
                    <div className="text-xl font-black mt-1.5">{t.value}</div>
                    {t.sub && <div className="text-[10px] text-gray-600 mt-1">{t.sub}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ══════ CONSTRUCTOR MODE ══════ */}
      {mode === 'constructors' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { label: 'Team A', value: teamA, set: setTeamA, exclude: teamB },
              { label: 'Team B', value: teamB, set: setTeamB, exclude: teamA },
            ].map(sel => {
              const c = sel.value ? tc(sel.value) : '#555';
              return (
                <div key={sel.label}>
                  <label className="block text-[10px] font-black tracking-[0.2em] mb-2 uppercase" style={{ color: c }}>{sel.label}</label>
                  <select value={sel.value} onChange={e => sel.set(e.target.value)}
                    className="w-full bg-white/[0.03] border-2 rounded-2xl px-5 py-3.5 text-sm font-bold focus:outline-none transition-all"
                    style={{ borderColor: sel.value ? c + '40' : 'rgba(255,255,255,0.06)' }}>
                    <option value="">Select constructor...</option>
                    {(constructorStandings || []).filter((t: any) => t.constructor_name !== sel.exclude).map((t: any) => (
                      <option key={t.constructor_name} value={t.constructor_name} className="bg-gray-900">{t.constructor_name} — {pts(t)} pts</option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>

          {/* Constructor VS Cards */}
          {(cA || cB) && (
            <div className="grid grid-cols-1 md:grid-cols-[1fr_80px_1fr] gap-4 items-stretch">
              <TeamVSCard team={cA} />
              <div className="hidden md:flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-red-600 flex items-center justify-center shadow-2xl shadow-red-600/30 border-4 border-[#080a0f]">
                  <span className="text-xl font-black text-white">VS</span>
                </div>
              </div>
              <TeamVSCard team={cB} />
            </div>
          )}

          {/* Constructor Bars */}
          {cA && cB && (
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 md:p-8 space-y-6 md:space-y-8">
              <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase">Constructor Battle</div>
              <div className="space-y-6">
                {[
                  { label: 'Points', a: pts(cA), b: pts(cB) },
                  { label: 'Wins', a: cA.wins || 0, b: cB.wins || 0 },
                  { label: 'Podiums', a: cA.podiums || 0, b: cB.podiums || 0 },
                ].map(m => {
                  const max = Math.max(m.a, m.b, 1);
                  const cAC = tc(cA.constructor_name);
                  const cBC = tc(cB.constructor_name);
                  const aW = m.a > m.b;
                  const bW = m.b > m.a;
                  return (
                    <div key={m.label}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {aW && <Crown size={12} style={{ color: cAC }} />}
                          <span className={`text-lg font-black ${aW ? '' : 'text-gray-700'}`} style={aW ? { color: cAC } : {}}>{m.a}</span>
                        </div>
                        <span className="text-[10px] font-black tracking-[0.2em] text-gray-600 uppercase">{m.label}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-lg font-black ${bW ? '' : 'text-gray-700'}`} style={bW ? { color: cBC } : {}}>{m.b}</span>
                          {bW && <Crown size={12} style={{ color: cBC }} />}
                        </div>
                      </div>
                      <div className="flex gap-0.5 h-6 rounded-full overflow-hidden">
                        <div className="flex-1 bg-white/[0.04] rounded-l-full overflow-hidden flex justify-end">
                          <div className="h-full rounded-l-full transition-all duration-1000"
                            style={{ width: `${(m.a / max) * 100}%`, background: `linear-gradient(90deg, ${cAC}20, ${cAC})`, boxShadow: aW ? `0 0 24px ${cAC}40` : 'none' }} />
                        </div>
                        <div className="flex-1 bg-white/[0.04] rounded-r-full overflow-hidden">
                          <div className="h-full rounded-r-full transition-all duration-1000"
                            style={{ width: `${(m.b / max) * 100}%`, background: `linear-gradient(90deg, ${cBC}, ${cBC}20)`, boxShadow: bW ? `0 0 24px ${cBC}40` : 'none' }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Dominance bar */}
              {(() => {
                const total = pts(cA) + pts(cB);
                const pA = total > 0 ? Math.round((pts(cA) / total) * 100) : 50;
                const pB = 100 - pA;
                return (
                  <div className="pt-6 border-t border-white/[0.05]">
                    <div className="text-[10px] font-black tracking-[0.2em] text-gray-600 uppercase text-center mb-3">Points Dominance</div>
                    <div className="flex h-10 rounded-2xl overflow-hidden">
                      <div className="flex items-center justify-center text-sm font-black transition-all duration-1000"
                        style={{ width: `${pA}%`, backgroundColor: tc(cA.constructor_name), color: '#000' }}>
                        {pA > 15 ? `${pA}%` : ''}
                      </div>
                      <div className="flex items-center justify-center text-sm font-black transition-all duration-1000"
                        style={{ width: `${pB}%`, backgroundColor: tc(cB.constructor_name), color: '#000' }}>
                        {pB > 15 ? `${pB}%` : ''}
                      </div>
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] font-bold text-gray-600">
                      <span>{cA.constructor_name}</span>
                      <span>{cB.constructor_name}</span>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {((mode === 'drivers' && !driverA && !driverB) || (mode === 'constructors' && !teamA && !teamB)) && (
        <div className="rounded-3xl border border-dashed border-white/[0.08] bg-white/[0.01] p-16 text-center">
          <div className="w-16 h-16 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-5 border border-white/[0.06]">
            {mode === 'drivers' ? <Users size={24} className="text-gray-600" /> : <Shield size={24} className="text-gray-600" />}
          </div>
          <h3 className="text-lg font-black mb-2">
            {mode === 'drivers' ? 'Choose your matchup' : 'Pick two constructors'}
          </h3>
          <p className="text-gray-600 text-sm max-w-md mx-auto">
            Select from {mode === 'drivers' ? driverOptions.length + ' drivers' : (constructorStandings?.length || 0) + ' constructors'} in the {season} season
          </p>
        </div>
      )}
    </div>
  );
}


/* ─── Driver VS Card ─── */
function DriverVSCard({ driver, standing, season }: { driver?: Driver; standing?: DriverStanding; season: number }) {
  if (!driver) return (
    <div className="rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.01] min-h-[280px] flex items-center justify-center">
      <span className="text-sm font-bold text-gray-700">Select a driver</span>
    </div>
  );
  const color = tc(driver.team_name || '');
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden hover:border-white/[0.1] transition-all">
      <div className="h-1 w-full" style={{ backgroundColor: color }} />
      <div className="p-6">
        <div className="flex items-start gap-4 mb-5">
          <div className="w-16 h-16 rounded-xl overflow-hidden relative flex-shrink-0 bg-black/30 border border-white/[0.08]"
            style={{ borderColor: color + '30' }}>
            <Image src={`/images/drivers/${driver.driver_code}.png`} alt={driver.last_name || ''} fill className="object-cover object-top" unoptimized />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-gray-600">{driver.first_name}</div>
            <div className="text-xl font-black truncate" style={{ color }}>{driver.last_name}</div>
            <div className="flex items-center gap-1.5 mt-1">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[10px] font-bold text-gray-500">{driver.team_name}</span>
            </div>
          </div>
          {driver.driver_number && (
            <div className="text-2xl font-black text-gray-800">{driver.driver_number}</div>
          )}
        </div>
        {standing ? (
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Points', value: standing.total_points ?? 0 },
              { label: 'Wins', value: standing.wins ?? 0 },
              { label: 'Podiums', value: standing.podiums ?? 0 },
              { label: 'DNFs', value: standing.dnfs ?? 0 },
            ].map(m => (
              <div key={m.label} className="bg-white/[0.03] rounded-xl p-3 border border-white/[0.04]">
                <div className="text-[10px] font-black text-gray-600 tracking-widest uppercase">{m.label}</div>
                <div className="text-xl font-black mt-0.5">{m.value}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-600 text-sm text-center py-4">No data for {season}</p>
        )}
      </div>
    </div>
  );
}

/* ─── Team VS Card ─── */
function TeamVSCard({ team }: { team: any }) {
  const pts = (t: any) => t?.total_points || t?.points || 0;
  if (!team) return (
    <div className="rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.01] min-h-[200px] flex items-center justify-center">
      <span className="text-sm font-bold text-gray-700">Select a team</span>
    </div>
  );
  const color = tc(team.constructor_name);
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden hover:border-white/[0.1] transition-all">
      <div className="h-1.5 w-full" style={{ backgroundColor: color }} />
      <div className="p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center border" style={{ borderColor: color + '30', backgroundColor: color + '10' }}>
            <Shield size={18} style={{ color }} />
          </div>
          <div className="text-xl font-black" style={{ color }}>{team.constructor_name}</div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Points', value: pts(team) },
            { label: 'Wins', value: team.wins || 0 },
            { label: 'Podiums', value: team.podiums || 0 },
          ].map(m => (
            <div key={m.label} className="bg-white/[0.03] rounded-xl p-3 border border-white/[0.04] text-center">
              <div className="text-xl font-black">{m.value}</div>
              <div className="text-[10px] font-black text-gray-600 tracking-widest uppercase mt-0.5">{m.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
