'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import Link from 'next/link';
import api from '@/lib/api';
import { Trophy, Users, Zap, ChevronDown, ChevronUp, ChevronRight } from 'lucide-react';

const TC: Record<string, string> = {
  'Red Bull': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2', 'McLaren': '#FF8000',
  'Aston Martin': '#229971', 'Alpine': '#FF87BC', 'Williams': '#64C4FF', 'Haas': '#B6BABD',
  'Kick Sauber': '#52E252', 'RB': '#6692FF', 'Racing Bulls': '#6692FF', 'Cadillac': '#C4A747',
  'Audi': '#990000', 'Racing Point': '#F596C8', 'Force India': '#F596C8', 'Renault': '#FFF500',
  'Toro Rosso': '#469BFF', 'Lotus': '#FFB800', 'Brawn': '#D2FF00',
  'Manor': '#ED1A3B', 'Caterham': '#005030', 'Jordan': '#FFD700', 'Jaguar': '#005030',
};
function gc(name: string) {
  if (!name) return '#888';
  for (const [k, v] of Object.entries(TC)) if (name.toLowerCase().includes(k.toLowerCase())) return v;
  return '#888';
}

export default function ConstructorsPage() {
  const [selectedSeason, setSelectedSeason] = useState(2026);
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null);

  const { data: seasons } = useQuery({ queryKey: ['seasons'], queryFn: () => api.getSeasons() });
  const { data: standings, isLoading } = useQuery({
    queryKey: ['constructorStandings', selectedSeason],
    queryFn: () => api.getConstructorStandings(selectedSeason),
    enabled: !!selectedSeason,
  });

  const pts = (t: any) => t?.total_points || t?.points || 0;
  const maxPoints = pts(standings?.[0]) || 1;
  const totalPoints = standings?.reduce((s: number, t: any) => s + pts(t), 0) || 0;

  return (
    <div className="space-y-10">
      {/* ══════ HERO ══════ */}
      <section className="relative overflow-hidden rounded-3xl">
        <div className="absolute inset-0 bg-gradient-to-br from-[#15002a] via-[#0d1020] to-[#080a0f]" />
        <div className="absolute top-[-30%] right-[-10%] w-[50vw] h-[50vw] bg-red-600/[0.06] rounded-full blur-[180px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[40vw] h-[40vw] bg-blue-600/[0.06] rounded-full blur-[140px]" />
        <div className="relative z-10 px-5 py-8 md:px-16 md:py-20">
          <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase mb-4">Formula 1</div>
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-black tracking-tight text-white mb-3">
            Constructor<br />Standings
          </h1>
          <p className="text-gray-500 text-lg max-w-xl">
            Every team. Every point. Track the constructor championship across 26 seasons of modern F1.
          </p>
        </div>
      </section>

      {/* ══════ SEASON SELECTOR ══════ */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-[10px] font-black tracking-[0.2em] text-gray-600 uppercase">Season</span>
        <div className="flex flex-wrap gap-1">
          {(seasons || []).slice().sort((a: number, b: number) => b - a).map((s: number) => (
            <button key={s} onClick={() => { setSelectedSeason(s); setExpandedTeam(null); }}
              className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                s === selectedSeason
                  ? 'bg-red-600 text-white shadow-lg shadow-red-600/25'
                  : 'bg-white/[0.04] text-gray-500 hover:bg-white/[0.08] hover:text-white border border-transparent hover:border-white/[0.06]'
              }`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ══════ SUMMARY CARDS ══════ */}
      {standings && standings.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Champion', value: standings[0]?.constructor_name, sub: `${pts(standings[0])} pts`, accent: true },
            { label: 'Teams', value: standings.length, sub: `${selectedSeason} grid` },
            { label: 'Total Points', value: totalPoints.toLocaleString(), sub: 'across all teams' },
            { label: 'Season', value: selectedSeason, sub: 'championship' },
          ].map(c => (
            <div key={c.label} className={`rounded-2xl p-5 border ${c.accent ? 'bg-gradient-to-br from-red-600/10 to-red-900/5 border-red-500/20' : 'bg-white/[0.02] border-white/[0.06]'}`}>
              <div className={`text-[10px] font-black tracking-[0.2em] uppercase mb-2 ${c.accent ? 'text-red-400' : 'text-gray-500'}`}>{c.label}</div>
              <div className="text-2xl font-black">{c.value}</div>
              {c.sub && <div className="text-xs text-gray-600 mt-1">{c.sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* ══════ LOADING ══════ */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* ══════ STANDINGS TABLE ══════ */}
      {standings && standings.length > 0 && (
        <div className="rounded-2xl border border-white/[0.06] overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[36px_1fr_60px] md:grid-cols-[56px_1fr_160px_100px_100px_90px] gap-2 px-3 md:px-5 py-3 bg-white/[0.03] border-b border-white/[0.06]">
            <div className="text-[10px] font-black tracking-[0.15em] text-gray-600">#</div>
            <div className="text-[10px] font-black tracking-[0.15em] text-gray-600">CONSTRUCTOR</div>
            <div className="text-[10px] font-black tracking-[0.15em] text-gray-600 text-right">POINTS</div>
            <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">WINS</div>
            <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">PODIUMS</div>
            <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">DRIVERS</div>
          </div>

          {/* Rows */}
          {standings.map((team: any, idx: number) => {
            const color = gc(team.constructor_name);
            const pct = (pts(team) / maxPoints) * 100;
            const isExpanded = expandedTeam === team.constructor_name;
            const teamSlug = team.constructor_name.toLowerCase().replace(/\s+/g, '-');
            return (
              <div key={team.constructor_name} className="border-t border-white/[0.04] first:border-t-0">
                <div
                  className="grid grid-cols-[36px_1fr_60px] md:grid-cols-[56px_1fr_160px_100px_100px_90px] gap-2 px-3 md:px-5 py-4 items-center hover:bg-white/[0.02] cursor-pointer transition-all group"
                  onClick={() => setExpandedTeam(isExpanded ? null : team.constructor_name)}
                >
                  {/* Position */}
                  <div>
                    <span className={`text-sm font-black ${
                      idx === 0 ? 'text-yellow-400' : idx === 1 ? 'text-gray-400' : idx === 2 ? 'text-amber-600' : 'text-gray-600'
                    }`}>
                      {idx + 1}
                    </span>
                  </div>

                  {/* Team name with color bar */}
                  <div className="flex items-center gap-3">
                    <div className="w-1 h-10 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <div className="min-w-0">
                      <Link href={`/constructors/${teamSlug}`} onClick={(e) => e.stopPropagation()} className="font-black text-sm group-hover:text-white transition-colors hover:underline">{team.constructor_name}</Link>
                      <div className="h-1 rounded-full bg-white/[0.04] w-24 mt-1.5 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${pct}%`, backgroundColor: color }} />
                      </div>
                    </div>
                  </div>

                  {/* Points */}
                  <div className="text-right">
                    <span className="text-lg font-black" style={{ color }}>{pts(team)}</span>
                  </div>

                  {/* Wins */}
                  <div className="hidden md:block text-center font-bold text-sm">{team.wins || 0}</div>

                  {/* Podiums */}
                  <div className="hidden md:block text-center font-bold text-sm">{team.podiums || 0}</div>

                  {/* Drivers + Link to team profile */}
                  <div className="hidden md:flex text-center text-sm text-gray-500 items-center justify-center gap-1.5">
                    <Users size={12} />
                    {team.drivers_count || team.driver_count || 0}
                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />}
                    <Link href={`/constructors/${teamSlug}`} onClick={(e) => e.stopPropagation()} className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <ChevronRight size={14} className="text-gray-400 hover:text-white" />
                    </Link>
                  </div>
                </div>

                {/* Expanded driver detail */}
                {isExpanded && team.drivers && Array.isArray(team.drivers) && (
                  <div className="px-6 pb-5 bg-white/[0.01]">
                    <div className="flex items-center justify-between mb-3 ml-0 md:ml-14">
                      <span className="text-xs text-gray-500">Team Drivers</span>
                      <Link href={`/constructors/${teamSlug}`} className="text-xs font-bold hover:underline" style={{ color }}>
                        View Team Profile →
                      </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 ml-0 md:ml-14">
                      {team.drivers.map((drv: any) => (
                        <Link key={drv.driver_code} href={`/drivers/${drv.driver_code.toLowerCase()}`} className="flex items-center gap-3 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 hover:bg-white/[0.05] hover:border-white/[0.1] transition group/driver">
                          <div className="w-10 h-10 rounded-xl overflow-hidden relative flex-shrink-0 bg-black/30 border border-white/[0.06]">
                            <Image src={`/images/drivers/${drv.driver_code}.png`} alt={drv.driver_code} fill className="object-cover object-top" unoptimized />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-bold text-sm group-hover/driver:text-white transition">{drv.driver_name || drv.driver_code}</div>
                            <div className="text-[11px] text-gray-500">
                              P{drv.position || '?'} — {drv.points || 0} pts — {drv.wins || 0} wins
                            </div>
                          </div>
                          <ChevronRight size={14} className="text-gray-600 group-hover/driver:text-white transition opacity-0 group-hover/driver:opacity-100" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ══════ POINTS DISTRIBUTION ══════ */}
      {standings && standings.length > 0 && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 md:p-8">
          <div className="flex items-center gap-2 mb-6">
            <Zap size={16} className="text-red-400" />
            <h3 className="text-sm font-black tracking-[0.1em] uppercase text-gray-400">Points Distribution</h3>
          </div>
          <div className="space-y-3">
            {standings.map((team: any) => {
              const color = gc(team.constructor_name);
              const pct = totalPoints > 0 ? (pts(team) / totalPoints) * 100 : 0;
              return (
                <div key={team.constructor_name} className="flex items-center gap-4">
                  <div className="w-28 text-right text-xs font-bold text-gray-500 truncate">{team.constructor_name}</div>
                  <div className="flex-1 h-8 bg-white/[0.03] rounded-xl overflow-hidden">
                    <div className="h-full rounded-xl flex items-center px-3 transition-all duration-1000"
                      style={{ width: `${Math.max(pct, 3)}%`, backgroundColor: color }}>
                      {pct > 10 && <span className="text-[10px] font-black text-black/80">{pts(team)} pts</span>}
                    </div>
                  </div>
                  <div className="w-14 text-right text-xs font-mono text-gray-500">{pct.toFixed(1)}%</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && (!standings || standings.length === 0) && (
        <div className="text-center py-20">
          <Trophy size={40} className="mx-auto text-gray-700 mb-4" />
          <p className="text-gray-500">No constructor standings for {selectedSeason}</p>
        </div>
      )}
    </div>
  );
}
