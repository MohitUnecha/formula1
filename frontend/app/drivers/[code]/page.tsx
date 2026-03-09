'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronLeft, Trophy, Flag, Calendar, TrendingUp, TrendingDown, Award, Zap, Target, Users } from 'lucide-react';
import api from '@/lib/api';
import type { DriverProfile } from '@/lib/types';

// ELO tier colors and labels
const ELO_TIERS: Record<string, { color: string; bg: string; label: string }> = {
  GOAT: { color: '#FFD700', bg: 'from-yellow-600/20 to-amber-900/30', label: '🐐 GOAT' },
  ELITE: { color: '#E5E4E2', bg: 'from-gray-300/20 to-gray-600/30', label: '⭐ Elite' },
  TOP: { color: '#CD7F32', bg: 'from-orange-600/20 to-orange-900/30', label: '🏆 Top Tier' },
  MID: { color: '#60A5FA', bg: 'from-blue-600/20 to-blue-900/30', label: '📊 Midfield' },
  LOW: { color: '#9CA3AF', bg: 'from-gray-500/20 to-gray-800/30', label: '🔧 Developing' },
};

export default function DriverProfilePage() {
  const params = useParams();
  const driverCode = (params.code as string).toUpperCase();

  const { data: profile, isLoading, error } = useQuery<DriverProfile>({
    queryKey: ['driverProfile', driverCode],
    queryFn: () => api.getDriverProfile(driverCode),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading driver profile...</p>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-20">
        <div className="text-6xl mb-4">🏎️</div>
        <h1 className="text-3xl font-bold mb-2">Driver Not Found</h1>
        <p className="text-gray-400 mb-6">Could not find driver with code: {driverCode}</p>
        <Link 
          href="/drivers"
          className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-bold transition"
        >
          <ChevronLeft size={20} />
          Back to Drivers
        </Link>
      </div>
    );
  }

  const teamColor = profile.team_color || '#888';
  const eloTier = profile.elo?.tier ? ELO_TIERS[profile.elo.tier] || ELO_TIERS.MID : null;

  return (
    <div className="space-y-8 pb-12">
      {/* ═══ HERO HEADER ═══ */}
      <section className="relative overflow-hidden rounded-3xl">
        <div 
          className="absolute inset-0 opacity-30"
          style={{ background: `linear-gradient(135deg, ${teamColor}40 0%, transparent 60%)` }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0d1020] via-[#0a0a0a] to-[#0d1020]" />
        <div className="absolute top-[-20%] right-[-10%] w-[40vw] h-[40vw] rounded-full blur-[150px]" style={{ backgroundColor: `${teamColor}15` }} />
        
        <div className="relative z-10 px-8 py-12 md:px-12 md:py-16">
          <Link href="/drivers" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition group">
            <ChevronLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
            <span className="font-medium">Back to Drivers</span>
          </Link>
          
          <div className="flex flex-col md:flex-row items-start gap-8">
            {/* Driver Photo */}
            <div className="relative">
              <div className="w-36 h-36 md:w-44 md:h-44 rounded-2xl overflow-hidden border-4 shadow-2xl bg-gray-900" style={{ borderColor: `${teamColor}50` }}>
                <Image 
                  src={profile.photo_url || `/images/drivers/${profile.driver_code}.png`}
                  alt={profile.full_name}
                  fill
                  className="object-cover object-top"
                  unoptimized
                  onError={(e) => {
                    // Fallback to team color gradient if image fails to load
                    const target = e.currentTarget as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
                {/* Fallback gradient - always present under image */}
                <div className="absolute inset-0 flex items-center justify-center text-5xl font-black opacity-30" style={{ background: `linear-gradient(135deg, ${teamColor}40, ${teamColor}80)` }}>
                  {profile.driver_code}
                </div>
              </div>
              {profile.driver_number && (
                <div className="absolute -bottom-3 -right-3 w-14 h-14 rounded-xl flex items-center justify-center text-xl font-black shadow-lg" 
                     style={{ backgroundColor: teamColor, color: teamColor === '#FFFFFF' || teamColor === '#27F4D2' ? '#000' : '#fff' }}>
                  {profile.driver_number}
                </div>
              )}
            </div>
            
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <span className="px-3 py-1 rounded-full text-sm font-bold" style={{ backgroundColor: `${teamColor}30`, color: teamColor }}>
                  {profile.driver_code}
                </span>
                {eloTier && profile.elo && (
                  <span className={`px-3 py-1 rounded-full text-sm font-bold bg-gradient-to-r ${eloTier.bg} border`} style={{ borderColor: `${eloTier.color}40`, color: eloTier.color }}>
                    {eloTier.label} • {Math.round(profile.elo.rating)}
                  </span>
                )}
              </div>
              
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-white mb-3">
                {profile.first_name} <span style={{ color: teamColor }}>{profile.last_name}</span>
              </h1>
              
              <div className="flex flex-wrap items-center gap-4 text-lg">
                <Link href={`/constructors/${(profile.team_name || '').toLowerCase().replace(/\s+/g, '-')}`} className="font-semibold hover:underline" style={{ color: teamColor }}>
                  {profile.team_name || 'Free Agent'}
                </Link>
                {profile.nationality && (
                  <>
                    <span className="text-gray-600">•</span>
                    <span className="text-gray-400">{profile.nationality}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ CAREER STATS GRID ═══ */}
      <section>
        <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
          <Trophy className="text-yellow-500" size={24} />
          Career Statistics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Races', value: profile.career_stats.total_races, icon: Flag, color: 'text-white' },
            { label: 'Wins', value: profile.career_stats.wins, icon: Trophy, color: 'text-yellow-400' },
            { label: 'Podiums', value: profile.career_stats.podiums, icon: Award, color: 'text-orange-400' },
            { label: 'Poles', value: profile.career_stats.poles, icon: Zap, color: 'text-purple-400' },
            { label: 'Points', value: profile.career_stats.total_points.toLocaleString(), icon: Target, color: 'text-green-400' },
            { label: 'DNFs', value: profile.career_stats.dnfs, icon: TrendingDown, color: 'text-red-400' },
            { label: 'Win Rate', value: `${profile.career_stats.win_rate}%`, icon: TrendingUp, color: 'text-blue-400' },
            { label: 'Avg Finish', value: profile.career_stats.avg_finish?.toFixed(1) || '-', icon: Target, color: 'text-cyan-400' },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 hover:bg-white/[0.05] transition">
              <div className="flex items-center gap-2 mb-2">
                <stat.icon size={16} className={stat.color} />
                <span className="text-[11px] font-bold tracking-wider text-gray-500 uppercase">{stat.label}</span>
              </div>
              <div className={`text-3xl font-black ${stat.color}`}>{stat.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ TEAMMATE COMPARISON ═══ */}
      {profile.teammate_comparison && (
        <section className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-white/[0.08] rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Users size={20} className="text-blue-400" />
            Head-to-Head vs {profile.teammate_comparison.teammate_name}
          </h3>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-green-400 font-bold">{profile.driver_code} Wins: {profile.teammate_comparison.wins}</span>
                <span className="text-red-400 font-bold">Losses: {profile.teammate_comparison.losses}</span>
              </div>
              <div className="h-3 bg-gray-800 rounded-full overflow-hidden flex">
                <div className="bg-green-500 h-full transition-all" style={{ width: `${(profile.teammate_comparison.wins / profile.teammate_comparison.races_compared) * 100}%` }} />
                <div className="bg-red-500 h-full transition-all" style={{ width: `${(profile.teammate_comparison.losses / profile.teammate_comparison.races_compared) * 100}%` }} />
              </div>
              <p className="text-xs text-gray-500 mt-2">Based on {profile.teammate_comparison.races_compared} races together</p>
            </div>
          </div>
        </section>
      )}

      {/* ═══ RECENT RESULTS ═══ */}
      {profile.recent_results && profile.recent_results.length > 0 && (
        <section>
          <h2 className="text-2xl font-black mb-5 flex items-center gap-2">
            <Flag className="text-red-500" size={24} />
            Recent Results
          </h2>
          <div className="space-y-2">
            {profile.recent_results.map((result) => (
              <div key={`${result.season}-${result.round}`} className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4 hover:bg-white/[0.04] transition flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-black text-lg ${
                    result.position === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                    result.position === 2 ? 'bg-gray-400/20 text-gray-300' :
                    result.position === 3 ? 'bg-orange-500/20 text-orange-400' :
                    result.position && result.position <= 10 ? 'bg-green-500/20 text-green-400' :
                    result.dnf ? 'bg-red-500/20 text-red-400' :
                    'bg-gray-700/30 text-gray-400'
                  }`}>
                    {result.dnf ? 'DNF' : result.position ? `P${result.position}` : '-'}
                  </div>
                  <div>
                    <div className="font-bold">{result.event_name}</div>
                    <div className="text-sm text-gray-500">{result.season} • Round {result.round}</div>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-right">
                    <div className="text-gray-500">Grid</div>
                    <div className="font-bold">P{result.grid || '-'}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-gray-500">Points</div>
                    <div className="font-bold text-green-400">+{result.points}</div>
                  </div>
                  <div className={`font-bold ${result.positions_gained > 0 ? 'text-green-400' : result.positions_gained < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                    {result.positions_gained > 0 ? `↑${result.positions_gained}` : result.positions_gained < 0 ? `↓${Math.abs(result.positions_gained)}` : '—'}
                  </div>
                </div>
              </div>
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
                  <th className="pb-3 pr-4">Team</th>
                  <th className="pb-3 pr-4 text-center">Races</th>
                  <th className="pb-3 pr-4 text-center">Wins</th>
                  <th className="pb-3 pr-4 text-center">Podiums</th>
                  <th className="pb-3 pr-4 text-right">Points</th>
                  <th className="pb-3 text-right">Avg Finish</th>
                </tr>
              </thead>
              <tbody>
                {profile.season_history.map((season) => (
                  <tr key={season.season} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition">
                    <td className="py-3 pr-4 font-bold text-lg">{season.season}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="w-1 h-6 rounded-full" style={{ backgroundColor: season.team_color || '#888' }} />
                        <span className="font-medium">{season.team || 'Unknown'}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-center text-gray-400">{season.races}</td>
                    <td className="py-3 pr-4 text-center font-bold text-yellow-400">{season.wins}</td>
                    <td className="py-3 pr-4 text-center font-bold text-orange-400">{season.podiums}</td>
                    <td className="py-3 pr-4 text-right font-bold text-green-400">{season.points}</td>
                    <td className="py-3 text-right text-gray-400">{season.avg_finish?.toFixed(1) || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ═══ ELO RATING DETAILS ═══ */}
      {profile.elo && (
        <section className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border border-white/[0.08] rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <TrendingUp size={20} className="text-purple-400" />
            ELO Rating
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-500 mb-1">Current Rating</div>
              <div className="text-3xl font-black" style={{ color: eloTier?.color }}>{Math.round(profile.elo.rating)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">Peak Rating</div>
              <div className="text-3xl font-black text-yellow-400">{Math.round(profile.elo.peak_rating)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">Tier</div>
              <div className="text-2xl font-bold" style={{ color: eloTier?.color }}>{eloTier?.label || profile.elo.tier}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">Races Completed</div>
              <div className="text-3xl font-black text-white">{profile.elo.races_completed}</div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
