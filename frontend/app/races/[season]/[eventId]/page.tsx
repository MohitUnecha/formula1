'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Trophy, Flag, MapPin, Calendar, ChevronLeft, Users } from 'lucide-react';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { getTeamColor } from '@/lib/tracks';
import { DriverSession } from '@/lib/types';

export default function EventPage() {
  const params = useParams();
  const season = parseInt(params.season as string);
  const eventId = parseInt(params.eventId as string);

  // Try to find the event — eventId could be either round or event_id
  const { data: events } = useQuery({
    queryKey: ['events', season],
    queryFn: () => api.getEvents(season),
    enabled: !!season,
  });

  // Support both event_id and round-based routing
  const event = events?.find((e: any) => e.event_id === eventId) 
    || events?.find((e: any) => e.round === eventId);

  // Fetch sessions for this event
  const { data: sessions } = useQuery({
    queryKey: ['sessions', event?.event_id],
    queryFn: () => api.getSessions(event!.event_id),
    enabled: !!event?.event_id,
  });

  const raceSession = sessions?.find((s: any) => s.session_type === 'R');
  const sprintSession = sessions?.find((s: any) => {
    const sessionType = String(s.session_type || '').toUpperCase();
    return ['S', 'SPRINT', 'SPRINT RACE'].includes(sessionType);
  });

  // Fetch driver results for the race session
  const { data: raceDrivers } = useQuery<DriverSession[]>({
    queryKey: ['session-drivers', raceSession?.session_id],
    queryFn: () => api.getSessionDrivers(raceSession!.session_id),
    enabled: !!raceSession?.session_id,
  });

  const { data: sprintDrivers } = useQuery<DriverSession[]>({
    queryKey: ['session-drivers', sprintSession?.session_id],
    queryFn: () => api.getSessionDrivers(sprintSession!.session_id),
    enabled: !!sprintSession?.session_id,
  });

  const hasSprintWeekend = !!event?.has_sprint || String(event?.event_format || '').toLowerCase().includes('sprint');

  const sortedRaceDrivers = (raceDrivers || []).slice().sort((a, b) => {
    const aPos = typeof a.position === 'number' ? a.position : 999;
    const bPos = typeof b.position === 'number' ? b.position : 999;
    if (aPos !== bPos) return aPos - bPos;
    const aGrid = typeof a.grid === 'number' ? a.grid : 999;
    const bGrid = typeof b.grid === 'number' ? b.grid : 999;
    return aGrid - bGrid;
  });

  const sortedSprintDrivers = (sprintDrivers || []).slice().sort((a, b) => {
    const aPos = typeof a.position === 'number' ? a.position : 999;
    const bPos = typeof b.position === 'number' ? b.position : 999;
    if (aPos !== bPos) return aPos - bPos;
    const aGrid = typeof a.grid === 'number' ? a.grid : 999;
    const bGrid = typeof b.grid === 'number' ? b.grid : 999;
    return aGrid - bGrid;
  });

  const raceGrid = sortedRaceDrivers
    .filter((d) => typeof d.grid === 'number')
    .sort((a, b) => (a.grid as number) - (b.grid as number));

  const ordinalLabel = (position?: number) => {
    if (position === 1) return '1st';
    if (position === 2) return '2nd';
    if (position === 3) return '3rd';
    if (!position) return null;
    const lastTwo = position % 100;
    if (lastTwo >= 11 && lastTwo <= 13) return `${position}th`;
    const last = position % 10;
    if (last === 1) return `${position}st`;
    if (last === 2) return `${position}nd`;
    if (last === 3) return `${position}rd`;
    return `${position}th`;
  };

  const renderSessionResults = (
    title: string,
    session: any,
    drivers: DriverSession[],
    replayHref?: string,
  ) => {
    const hasPositions = drivers.some((d) => typeof d.position === 'number' && !d.dnf);
    const showGridMode = season === 2026 && !hasPositions;

    return (
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold">
            <Trophy size={28} className="inline text-yellow-400 mr-2" />
            {title}
          </h2>
          {session && replayHref && (
            <Link
              href={replayHref}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-bold transition text-sm"
            >
              <Flag size={16} />
              Watch Replay
            </Link>
          )}
        </div>

        {drivers.length > 0 ? (
          <div className="space-y-3">
            {drivers.map((result, idx) => (
              <Link
                href={`/drivers/${result.driver_code.toLowerCase()}`}
                key={`${title}-${result.driver_code}`}
                className="block bg-gray-800/50 border border-gray-700 rounded-xl p-5 hover:bg-gray-800 hover:border-gray-600 transition-all group cursor-pointer"
                style={{ animationDelay: `${idx * 0.05}s` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6">
                    <div className={`text-center min-w-[60px] ${
                      result.position === 1 ? 'text-yellow-400' :
                      result.position === 2 ? 'text-gray-300' :
                      result.position === 3 ? 'text-orange-400' :
                      'text-white'
                    }`}>
                      <div className="text-4xl font-black">
                        {showGridMode
                          ? `P${result.grid ?? '—'}`
                          : result.dnf
                            ? 'DNF'
                            : (result.position ?? '—')}
                      </div>
                      {!showGridMode && typeof result.position === 'number' && !result.dnf && (
                        <div className={`text-xs font-bold mt-1 ${
                          result.position === 1 ? 'text-yellow-400' :
                          result.position === 2 ? 'text-gray-300' :
                          result.position === 3 ? 'text-orange-400' :
                          'text-gray-500'
                        }`}>
                          {result.position <= 3 && (
                            <span className="mr-1">
                              {result.position === 1 ? '🥇' : result.position === 2 ? '🥈' : '🥉'}
                            </span>
                          )}
                          {ordinalLabel(result.position)}
                        </div>
                      )}
                    </div>

                    <div
                      className="w-1 h-14 rounded-full"
                      style={{ backgroundColor: getTeamColor(result.team_name) }}
                    ></div>

                    <div>
                      <div className="flex items-baseline gap-3 mb-1">
                        <div className="text-2xl font-black group-hover:text-red-400 transition-colors">{result.driver_code}</div>
                        <div className="text-lg font-semibold text-gray-300 group-hover:text-white transition-colors">{result.driver_name}</div>
                      </div>
                      <div className="text-sm text-gray-400">{result.team_name}</div>
                    </div>
                  </div>

                  <div className="text-right">
                    {!showGridMode && (
                      <div className="text-2xl font-bold mb-1">
                        {typeof result.points === 'number' && result.points > 0 ? `${result.points} pts` : ''}
                      </div>
                    )}
                    <div className="text-sm text-gray-400">
                      Grid: P{result.grid ?? '—'}
                      {!showGridMode && typeof result.grid === 'number' && typeof result.position === 'number' && !result.dnf && (
                        <span className={`ml-2 ${
                          result.grid - result.position > 0 ? 'text-green-400' :
                          result.grid - result.position < 0 ? 'text-red-400' : 'text-gray-400'
                        }`}>
                          {result.grid - result.position > 0 ? `↑${result.grid - result.position}` :
                           result.grid - result.position < 0 ? `↓${Math.abs(result.grid - result.position)}` : '→'}
                        </span>
                      )}
                    </div>
                    {result.dnf && !showGridMode && (
                      <div className="text-sm text-red-400 font-bold">{result.status}</div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 bg-gray-800/30 border border-gray-700 rounded-xl">
            <div className="text-5xl mb-4">📊</div>
            <h3 className="text-xl font-bold mb-2">
              {season === 2026 ? 'Session Grid Not Available Yet' : 'Loading Results...'}
            </h3>
            <p className="text-gray-400">
              {season === 2026
                ? 'Grid and results will appear as weekend data becomes available'
                : 'Session results will appear here'}
            </p>
          </div>
        )}
      </section>
    );
  };

  if (!event) {
    return (
      <div className="text-center py-20">
        <div className="text-6xl mb-4">🏁</div>
        <h1 className="text-3xl font-bold mb-2">Race Not Found</h1>
        <p className="text-gray-400 mb-6">Event {eventId} in {season} season</p>
        <Link 
          href={`/races/${season}`}
          className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-bold transition"
        >
          <ChevronLeft size={20} />
          Back to {season} Calendar
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-gray-800 via-gray-900 to-black p-8 md:p-12 animate-slide-down">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-0 right-1/4 w-96 h-96 bg-red-500 rounded-full mix-blend-screen blur-3xl"></div>
        </div>
        <div className="relative z-10">
          <Link 
            href={`/races/${season}`}
            className="inline-flex items-center gap-2 text-red-400 hover:text-red-300 mb-4 transition"
          >
            <ChevronLeft size={18} />
            <span className="font-semibold">Back to {season} Calendar</span>
          </Link>
          
          <div className="inline-block bg-red-600/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-bold text-red-400 mb-4">
            ROUND {event.round}
          </div>
          {hasSprintWeekend && (
            <div className="inline-block ml-3 bg-orange-500/20 border border-orange-500/40 backdrop-blur-sm px-3 py-1.5 rounded-full text-xs font-bold text-orange-300 mb-4">
              SPRINT WEEKEND
            </div>
          )}
          
          <h1 className="text-4xl md:text-5xl font-black text-white mb-4">
            {event.event_name}
          </h1>
          
          <div className="flex flex-wrap items-center gap-4 text-gray-300">
            <div className="flex items-center gap-2">
              <MapPin size={18} className="text-red-400" />
              <span className="font-semibold">{event.location}, {event.country}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-red-400" />
              <span className="font-semibold">{formatDate(event.event_date)}</span>
            </div>
            {raceSession && (
              <div className="flex items-center gap-2">
                <Users size={18} className="text-red-400" />
                <span className="font-semibold">{raceSession.driver_count} Drivers</span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Sprint first, then Race */}
      {hasSprintWeekend && renderSessionResults(
        'Sprint Weekend Stats',
        sprintSession,
        sortedSprintDrivers,
        sprintSession ? `/races/${season}/${event.event_id}/${sprintSession.session_id}` : undefined,
      )}

      {renderSessionResults(
        'Race Stats',
        raceSession,
        sortedRaceDrivers,
        raceSession ? `/replay?season=${season}&event=${event.event_id}` : undefined,
      )}

      {season === 2026 && raceGrid.length > 0 && (
        <section>
          <h2 className="text-3xl font-bold mb-6">2026 Starting Grid</h2>
          <div className="bg-gray-800/40 border border-gray-700 rounded-xl overflow-hidden">
            {raceGrid.map((driver, idx) => (
              <Link
                href={`/drivers/${driver.driver_code.toLowerCase()}`}
                key={`grid-${driver.driver_code}`}
                className="flex items-center justify-between px-5 py-3 border-b border-gray-700/50 last:border-b-0 hover:bg-gray-700/50 transition-colors group cursor-pointer"
                style={{ animationDelay: `${idx * 0.03}s` }}
              >
                <div className="flex items-center gap-4">
                  <div className="text-xl font-black text-red-400 w-12">P{driver.grid}</div>
                  <div className="w-1 h-8 rounded-full" style={{ backgroundColor: getTeamColor(driver.team_name) }} />
                  <div>
                    <div className="font-bold text-lg group-hover:text-red-400 transition-colors">{driver.driver_code}</div>
                    <div className="text-xs text-gray-400 group-hover:text-white transition-colors">{driver.driver_name}</div>
                  </div>
                </div>
                <div className="text-sm text-gray-400">{driver.team_name}</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Quick Stats */}
      {raceSession && sortedRaceDrivers.length > 0 && (
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
            <div className="text-sm text-gray-400 mb-1">Winner</div>
            <div className="text-2xl font-bold text-yellow-400">
              {sortedRaceDrivers.find(d => d.position === 1)?.driver_code || 'N/A'}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              {sortedRaceDrivers.find(d => d.position === 1)?.driver_name || ''}
            </div>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
            <div className="text-sm text-gray-400 mb-1">Total Laps</div>
            <div className="text-2xl font-bold">{raceSession.total_laps || '-'}</div>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
            <div className="text-sm text-gray-400 mb-1">Starters</div>
            <div className="text-2xl font-bold">{sortedRaceDrivers.length || 0}</div>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
            <div className="text-sm text-gray-400 mb-1">DNFs</div>
            <div className="text-2xl font-bold text-red-400">
              {sortedRaceDrivers.filter(d => d.dnf).length || 0}
            </div>
          </div>
        </section>
      )}

      {/* View Full Session Details */}
      {raceSession && (
        <section className="text-center">
          <Link
            href={`/races/${season}/${event.event_id}/${raceSession.session_id}`}
            className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-8 rounded-xl transition"
          >
            View Full Session Details
            <ChevronLeft size={18} className="rotate-180" />
          </Link>
        </section>
      )}
    </div>
  );
}
