'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Users, Trophy, Crown, AlertTriangle, Info, ChevronRight, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import type { Driver, DriverStanding } from '@/lib/types';
import { getTeamColor } from '@/lib/tracks';

export default function DriversPage() {
  const [selectedSeason, setSelectedSeason] = useState(2026);
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});

  const getDriverImage = (driver: Driver) => {
    if (brokenImages[driver.driver_code]) {
      const name = `${driver.first_name || ''} ${driver.last_name || driver.driver_code}`.trim();
      return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=111827&color=ffffff&size=256`;
    }
    return driver.photo_url || `/images/drivers/${driver.driver_code}.png`;
  };

  const { data: seasons } = useQuery({
    queryKey: ['seasons'],
    queryFn: () => api.getSeasons(),
  });

  const { data: drivers, isLoading: driversLoading } = useQuery({
    queryKey: ['drivers', selectedSeason],
    queryFn: () => api.getDrivers(selectedSeason),
    enabled: !!selectedSeason,
  });

  const { data: standings } = useQuery({
    queryKey: ['standings', selectedSeason],
    queryFn: () => api.getStandings(selectedSeason),
    enabled: !!selectedSeason,
  });

  const driversWithStats = drivers?.map((driver: Driver) => {
    const standing = standings?.find((s: DriverStanding) => s.driver_code === driver.driver_code);
    return { ...driver, standing };
  }) || [];

  const sortedDrivers = [...driversWithStats].sort((a, b) => {
    if (a.standing && b.standing) return (b.standing.total_points ?? 0) - (a.standing.total_points ?? 0);
    if (a.standing) return -1;
    if (b.standing) return 1;
    return (a.last_name || '').localeCompare(b.last_name || '');
  });

  const driverCount = drivers?.length || 0;
  const topPoints = standings?.[0]?.total_points || 1;

  return (
    <div className="space-y-10">
      {/* ══════ HERO ══════ */}
      <section className="relative overflow-hidden rounded-3xl">
        <div className="absolute inset-0 bg-gradient-to-br from-[#15002a] via-[#0d1020] to-[#080a0f]" />
        <div className="absolute top-[-30%] right-[-10%] w-[50vw] h-[50vw] bg-purple-600/[0.07] rounded-full blur-[180px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[40vw] h-[40vw] bg-red-600/[0.05] rounded-full blur-[140px]" />
        <div className="relative z-10 px-5 py-8 md:px-16 md:py-20">
          <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase mb-4">Formula 1</div>
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-black tracking-tight text-white mb-3">
            F1 Drivers<br />{selectedSeason}
          </h1>
          <p className="text-gray-500 text-lg max-w-xl">
            {driverCount > 0
              ? `${driverCount} drivers competing in the ${selectedSeason} season`
              : `Loading drivers for ${selectedSeason}...`}
          </p>
        </div>
      </section>

      {/* ══════ SEASON PICKER ══════ */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-[10px] font-black tracking-[0.2em] text-gray-600 uppercase">Season</span>
        {seasons ? (
          <div className="flex flex-wrap gap-1">
            {[...seasons].sort((a: number, b: number) => b - a).map((s: number) => (
              <button key={s} onClick={() => setSelectedSeason(s)}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  selectedSeason === s
                    ? 'bg-red-600 text-white shadow-lg shadow-red-600/25'
                    : 'bg-white/[0.04] text-gray-500 hover:bg-white/[0.08] hover:text-white border border-transparent hover:border-white/[0.06]'
                }`}>
                {s}
              </button>
            ))}
          </div>
        ) : (
          <div className="animate-pulse h-8 w-48 bg-white/[0.04] rounded-xl" />
        )}
      </div>

      {/* ══════ DISCLAIMERS ══════ */}
      <section className="space-y-2">
        {selectedSeason === 2026 && (
          <div className="flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <Info size={16} className="mt-0.5 flex-shrink-0" />
            <p>
              2026 roster and profile images are shown from public data/media sources. Championship standings populate as race sessions are completed.
            </p>
          </div>
        )}
        {selectedSeason < 2018 && (
          <div className="flex items-start gap-2 rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-200">
            <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
            <p>
              FastF1 detailed telemetry is limited before 2018. Historical driver data is provided with best-available archive coverage.
            </p>
          </div>
        )}
      </section>

      {/* ══════ CHAMPIONSHIP STANDINGS ══════ */}
      {standings && standings.length > 0 && (
        <section className="space-y-5">
          <div>
            <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase mb-1">Championship</div>
            <h2 className="text-2xl font-black tracking-tight">Driver Standings</h2>
          </div>

          <div className="rounded-2xl border border-white/[0.06] overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-[36px_1fr_60px] md:grid-cols-[52px_1fr_120px_80px_80px_60px_40px] gap-2 px-3 md:px-5 py-3 bg-white/[0.03] border-b border-white/[0.06]">
              <div className="text-[10px] font-black tracking-[0.15em] text-gray-600">POS</div>
              <div className="text-[10px] font-black tracking-[0.15em] text-gray-600">DRIVER</div>
              <div className="text-[10px] font-black tracking-[0.15em] text-gray-600 text-right">POINTS</div>
              <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">WINS</div>
              <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">PODS</div>
              <div className="hidden md:block text-[10px] font-black tracking-[0.15em] text-gray-600 text-center">DNF</div>
              <div className="hidden md:block"></div>
            </div>

            {/* Rows */}
            {standings.map((driver: DriverStanding, index: number) => {
              const teamColor = getTeamColor(driver.team_name || '');
              const pointsPct = topPoints > 0 ? ((driver.total_points ?? 0) / topPoints) * 100 : 0;
              return (
                <Link href={`/drivers/${driver.driver_code.toLowerCase()}`} key={driver.driver_code}
                  className="grid grid-cols-[36px_1fr_60px] md:grid-cols-[52px_1fr_120px_80px_80px_60px_40px] gap-2 px-3 md:px-5 py-3.5 items-center border-t border-white/[0.04] first:border-t-0 hover:bg-white/[0.04] transition-all duration-200 group cursor-pointer">
                  {/* Position */}
                  <div>
                    <span className={`text-sm font-black ${
                      index === 0 ? 'text-yellow-400' : index === 1 ? 'text-gray-400' : index === 2 ? 'text-amber-600' : 'text-gray-600'
                    }`}>
                      {index + 1}
                    </span>
                  </div>

                  {/* Driver with photo */}
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl overflow-hidden relative flex-shrink-0 bg-black/30 border border-white/[0.08]"
                      style={{ borderColor: teamColor + '30' }}>
                      <img
                        src={driver.photo_url || `/images/drivers/${driver.driver_code}.png`}
                        alt={driver.driver_name || driver.driver_code}
                        className="w-full h-full object-cover object-top"
                        onError={(e) => {
                          const fallback = `https://ui-avatars.com/api/?name=${encodeURIComponent(driver.driver_name || driver.driver_code)}&background=111827&color=ffffff&size=128`;
                          if (e.currentTarget.src !== fallback) e.currentTarget.src = fallback;
                        }}
                      />
                    </div>
                    <div className="w-1 h-8 rounded-full flex-shrink-0" style={{ backgroundColor: teamColor }} />
                    <div className="min-w-0">
                      <div className="font-black text-sm truncate group-hover:text-white transition-colors">{driver.driver_name}</div>
                      <div className="text-[10px] text-gray-600">{driver.team_name}</div>
                    </div>
                  </div>

                  {/* Points with bar */}
                  <div className="text-right">
                    <div className="inline-flex flex-col items-end">
                      <span className="font-black text-yellow-400">{driver.total_points ?? 0}</span>
                      <div className="w-16 h-1 rounded-full bg-white/[0.04] mt-1 overflow-hidden">
                        <div className="h-full rounded-full bg-yellow-500/50 transition-all duration-700" style={{ width: `${pointsPct}%` }} />
                      </div>
                    </div>
                  </div>

                  {/* Wins */}
                  <div className="hidden md:block text-center font-bold text-green-400 text-sm">{driver.wins ?? 0}</div>

                  {/* Podiums */}
                  <div className="hidden md:block text-center font-bold text-blue-400 text-sm">{driver.podiums ?? 0}</div>

                  {/* DNFs */}
                  <div className="hidden md:block text-center text-gray-600 text-sm">{driver.dnfs ?? 0}</div>

                  {/* Arrow indicator */}
                  <div className="hidden md:flex items-center justify-end">
                    <ChevronRight size={14} className="text-gray-600 group-hover:text-white group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* ══════ DRIVER GRID ══════ */}
      {driversLoading ? (
        <div className="flex items-center justify-center min-h-[30vh]">
          <div className="w-10 h-10 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : sortedDrivers.length > 0 ? (
        <section className="space-y-5">
          <div>
            <div className="text-[11px] font-black tracking-[0.25em] text-red-500 uppercase mb-1">All Drivers</div>
            <h2 className="text-2xl font-black tracking-tight">Driver Profiles</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {sortedDrivers.map((driver: Driver & { standing?: DriverStanding }, idx: number) => {
              const teamColor = getTeamColor(driver.team_name || '');
              return (
                <Link href={`/drivers/${driver.driver_code.toLowerCase()}`} key={driver.driver_code}
                  className="group relative overflow-hidden rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.15] hover:bg-white/[0.04] hover:scale-[1.02] transition-all duration-300 cursor-pointer">
                  {/* Team color top bar */}
                  <div className="h-1 w-full" style={{ backgroundColor: teamColor }} />

                  <div className="p-5 relative">
                    {/* Photo + Name row */}
                    <div className="flex items-start gap-3 mb-4">
                      <div className="relative w-14 h-14 rounded-xl overflow-hidden flex-shrink-0 bg-black/30 border border-white/[0.08]"
                        style={{ borderColor: teamColor + '30' }}>
                        <img
                          src={getDriverImage(driver)}
                          alt={`${driver.first_name} ${driver.last_name}`}
                          className="w-full h-full object-cover object-top"
                          onError={() => setBrokenImages((prev) => ({ ...prev, [driver.driver_code]: true }))}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-gray-500">{driver.first_name}</div>
                        <div className="text-lg font-black tracking-tight truncate" style={{ color: teamColor }}>{driver.last_name}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: teamColor }} />
                          <span className="text-[10px] font-bold text-gray-600">{driver.team_name}</span>
                        </div>
                      </div>
                      {driver.driver_number && (
                        <div className="text-2xl font-black text-gray-800">{driver.driver_number}</div>
                      )}
                    </div>

                    {/* Stats */}
                    {driver.standing && (
                      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-white/[0.05]">
                        <div className="text-center">
                          <div className="text-yellow-400 font-black">{driver.standing.total_points ?? 0}</div>
                          <div className="text-[9px] text-gray-600 font-black tracking-widest">PTS</div>
                        </div>
                        <div className="text-center">
                          <div className="text-green-400 font-black">{driver.standing.wins ?? 0}</div>
                          <div className="text-[9px] text-gray-600 font-black tracking-widest">WINS</div>
                        </div>
                        <div className="text-center">
                          <div className="text-blue-400 font-black">{driver.standing.podiums ?? 0}</div>
                          <div className="text-[9px] text-gray-600 font-black tracking-widest">PODS</div>
                        </div>
                      </div>
                    )}

                    {/* Top 3 crown */}
                    {driver.standing && idx < 3 && (
                      <div className="absolute top-3 right-4">
                        <Crown size={14} className={idx === 0 ? 'text-yellow-400' : idx === 1 ? 'text-gray-400' : 'text-amber-600'} />
                      </div>
                    )}

                    {/* View profile indicator */}
                    <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="flex items-center gap-1 text-[10px] font-bold text-gray-400">
                        <span>View Profile</span>
                        <ChevronRight size={12} />
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      ) : (
        <div className="text-center py-20">
          <Users size={40} className="mx-auto text-gray-700 mb-4" />
          <p className="text-gray-300 font-semibold">No drivers found for {selectedSeason}</p>
          <p className="text-gray-500 text-sm mt-1">Try another season or run data ingestion for this year.</p>
        </div>
      )}
    </div>
  );
}
