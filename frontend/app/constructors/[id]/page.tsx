'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronLeft, Trophy, Flag, Calendar, Users, Building2, MapPin, Wrench, Zap } from 'lucide-react';
import api from '@/lib/api';
import type { ConstructorProfile } from '@/lib/types';

export default function ConstructorProfilePage() {
  const params = useParams();
  const constructorId = params.id as string;

  const { data: profile, isLoading, error } = useQuery<ConstructorProfile>({
    queryKey: ['constructorProfile', constructorId],
    queryFn: () => api.getConstructorProfile(constructorId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading team profile...</p>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-20">
        <div className="text-6xl mb-4">🏎️</div>
        <h1 className="text-3xl font-bold mb-2">Team Not Found</h1>
        <p className="text-gray-400 mb-6">Could not find constructor: {constructorId}</p>
        <Link 
          href="/constructors"
          className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-bold transition"
        >
          <ChevronLeft size={20} />
          Back to Constructors
        </Link>
      </div>
    );
  }

  const teamColor = profile.team_color || '#888';

  return (
    <div className="space-y-8 pb-12">
      {/* ═══ HERO HEADER ═══ */}
      <section className="relative overflow-hidden rounded-3xl">
        <div 
          className="absolute inset-0 opacity-40"
          style={{ background: `linear-gradient(135deg, ${teamColor}50 0%, transparent 60%)` }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0d1020] via-[#0a0a0a] to-[#0d1020]" />
        <div className="absolute top-[-20%] right-[-10%] w-[50vw] h-[50vw] rounded-full blur-[180px]" style={{ backgroundColor: `${teamColor}20` }} />
        
        <div className="relative z-10 px-8 py-12 md:px-12 md:py-16">
          <Link href="/constructors" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition group">
            <ChevronLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
            <span className="font-medium">Back to Constructors</span>
          </Link>
          
          <div className="flex flex-col md:flex-row items-start gap-8">
            {/* Team Logo */}
            <div className="w-36 h-36 md:w-44 md:h-44 rounded-2xl flex items-center justify-center shadow-2xl border-4 overflow-hidden bg-white" 
                 style={{ borderColor: `${teamColor}50` }}>
              {profile.logo_url ? (
                <img 
                  src={profile.logo_url} 
                  alt={`${profile.constructor_name} logo`}
                  className="w-full h-full object-contain p-4"
                  onError={(e) => {
                    // Fallback to team color circle if image fails
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent) {
                      const fallback = document.createElement('div');
                      fallback.className = 'w-20 h-20 rounded-full';
                      fallback.style.backgroundColor = teamColor;
                      parent.appendChild(fallback);
                    }
                  }}
                />
              ) : (
                <div className="w-20 h-20 rounded-full" style={{ backgroundColor: teamColor }} />
              )}
            </div>
            
            <div className="flex-1">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-white mb-3">
                {profile.constructor_name}
              </h1>
              <p className="text-xl font-medium mb-4" style={{ color: teamColor }}>
                {profile.full_name}
              </p>
              
              <div className="flex flex-wrap items-center gap-6 text-gray-400">
                {profile.headquarters && (
                  <div className="flex items-center gap-2">
                    <MapPin size={16} style={{ color: teamColor }} />
                    <span>{profile.headquarters}</span>
                  </div>
                )}
                {profile.founded && (
                  <div className="flex items-center gap-2">
                    <Calendar size={16} style={{ color: teamColor }} />
                    <span>Founded {profile.founded}</span>
                  </div>
                )}
                {profile.power_unit && (
                  <div className="flex items-center gap-2">
                    <Wrench size={16} style={{ color: teamColor }} />
                    <span>{profile.power_unit}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ TEAM INFO ═══ */}
      {(profile.team_principal || profile.power_unit) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {profile.team_principal && (
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Users size={16} className="text-blue-400" />
                <span className="text-[11px] font-bold tracking-wider text-gray-500 uppercase">Team Principal</span>
              </div>
              <div className="text-xl font-bold">{profile.team_principal}</div>
            </div>
          )}
          {profile.power_unit && (
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Zap size={16} className="text-yellow-400" />
                <span className="text-[11px] font-bold tracking-wider text-gray-500 uppercase">Power Unit</span>
              </div>
              <div className="text-xl font-bold">{profile.power_unit}</div>
            </div>
          )}
          {profile.headquarters && (
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Building2 size={16} className="text-green-400" />
                <span className="text-[11px] font-bold tracking-wider text-gray-500 uppercase">Headquarters</span>
              </div>
              <div className="text-xl font-bold">{profile.headquarters}</div>
            </div>
          )}
        </div>
      )}

      {/* ═══ TEAM HISTORY ═══ */}
      {profile.history && (
        <section className="bg-gradient-to-r from-gray-900/50 to-transparent border border-white/[0.06] rounded-2xl p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Calendar className="text-red-500" size={20} />
            Team History
          </h2>
          <p className="text-gray-300 leading-relaxed text-lg">{profile.history}</p>
        </section>
      )}

      {/* ═══ CAREER STATS GRID ═══ */}
      <section>
        <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
          <Trophy className="text-yellow-500" size={24} />
          All-Time Statistics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: 'Seasons', value: profile.career_stats.seasons, color: 'text-white' },
            { label: 'Races', value: profile.career_stats.total_races, color: 'text-white' },
            { label: 'Wins', value: profile.career_stats.wins, color: 'text-yellow-400' },
            { label: 'Podiums', value: profile.career_stats.podiums, color: 'text-orange-400' },
            { label: 'Poles', value: profile.career_stats.poles, color: 'text-purple-400' },
            { label: 'Points', value: profile.career_stats.total_points.toLocaleString(), color: 'text-green-400' },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 text-center hover:bg-white/[0.05] transition">
              <div className="text-[11px] font-bold tracking-wider text-gray-500 uppercase mb-2">{stat.label}</div>
              <div className={`text-3xl font-black ${stat.color}`}>{stat.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ CURRENT DRIVERS ═══ */}
      {profile.current_drivers && profile.current_drivers.length > 0 && (
        <section>
          <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
            <Users className="text-blue-500" size={24} />
            Current Drivers
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.current_drivers.map((driver) => (
              <Link 
                key={driver.driver_code}
                href={`/drivers/${driver.driver_code.toLowerCase()}`}
                className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-6 hover:bg-white/[0.06] hover:border-white/[0.1] transition group flex items-center gap-5"
              >
                <div className="w-20 h-20 rounded-xl overflow-hidden border-2 flex-shrink-0" style={{ borderColor: `${teamColor}50` }}>
                  <Image 
                    src={`/images/drivers/${driver.driver_code}.png`}
                    alt={driver.full_name}
                    width={80}
                    height={80}
                    className="object-cover object-top w-full h-full"
                    unoptimized
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xl font-black group-hover:text-white transition">{driver.full_name}</span>
                    {driver.driver_number && (
                      <span className="px-2 py-0.5 rounded text-sm font-bold" style={{ backgroundColor: `${teamColor}30`, color: teamColor }}>
                        #{driver.driver_number}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">{driver.nationality}</div>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span className="text-green-400 font-bold">{driver.points} pts</span>
                    <span className="text-yellow-400">{driver.wins} wins</span>
                    <span className="text-orange-400">{driver.podiums} podiums</span>
                  </div>
                </div>
                <ChevronLeft size={20} className="text-gray-600 group-hover:text-white rotate-180 transition" />
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ═══ NOTABLE DRIVERS ═══ */}
      {profile.notable_drivers && profile.notable_drivers.length > 0 && (
        <section>
          <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
            <Trophy className="text-yellow-500" size={24} />
            Notable Drivers (All-Time)
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {profile.notable_drivers.map((driver, idx) => (
              <Link
                key={driver.driver_code}
                href={`/drivers/${driver.driver_code.toLowerCase()}`}
                className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4 hover:bg-white/[0.05] transition text-center group"
              >
                <div className={`text-2xl font-black mb-1 ${idx === 0 ? 'text-yellow-400' : idx === 1 ? 'text-gray-300' : idx === 2 ? 'text-orange-400' : 'text-white'}`}>
                  {driver.driver_code}
                </div>
                <div className="text-sm text-gray-400 truncate group-hover:text-white transition">{driver.name}</div>
                <div className="text-xs text-gray-600 mt-1">{driver.points.toLocaleString()} pts • {driver.wins} wins</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ═══ SEASON HISTORY ═══ */}
      {profile.season_history && profile.season_history.length > 0 && (
        <section>
          <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
            <Calendar className="text-blue-500" size={24} />
            Season History
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-white/[0.06]">
                  <th className="pb-3 pr-4">Season</th>
                  <th className="pb-3 pr-4 text-center">Races</th>
                  <th className="pb-3 pr-4 text-center">Wins</th>
                  <th className="pb-3 pr-4 text-center">Podiums</th>
                  <th className="pb-3 pr-4 text-center">Poles</th>
                  <th className="pb-3 text-right">Points</th>
                </tr>
              </thead>
              <tbody>
                {profile.season_history.map((season) => (
                  <tr key={season.season} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition">
                    <td className="py-3 pr-4">
                      <Link href={`/races/${season.season}`} className="font-bold text-lg hover:underline" style={{ color: teamColor }}>
                        {season.season}
                      </Link>
                    </td>
                    <td className="py-3 pr-4 text-center text-gray-400">{season.races}</td>
                    <td className="py-3 pr-4 text-center font-bold text-yellow-400">{season.wins}</td>
                    <td className="py-3 pr-4 text-center font-bold text-orange-400">{season.podiums}</td>
                    <td className="py-3 pr-4 text-center font-bold text-purple-400">{season.poles}</td>
                    <td className="py-3 text-right font-bold text-green-400">{season.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
