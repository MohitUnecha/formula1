'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Calendar, MapPin, Trophy, ChevronRight } from 'lucide-react';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import ChampionsBar from '@/components/ChampionsBar';

export default function SeasonRacesPage() {
  const params = useParams();
  const season = parseInt(params.season as string);

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['events', season],
    queryFn: () => api.getEvents(season),
    enabled: !!season,
  });

  const { data: standings } = useQuery({
    queryKey: ['standings', season],
    queryFn: () => api.getStandings(season),
    enabled: !!season,
  });

  const { data: constructorStandings } = useQuery({
    queryKey: ['constructors-standings', season],
    queryFn: () => api.getConstructorStandings(season),
    enabled: !!season,
  });

  const driverChampion = standings?.[0];
  const constructorChampion = constructorStandings?.[0];

  if (eventsLoading) {
    return (
      <div className="space-y-6">
        <div className="h-32 bg-gray-800/50 rounded-xl animate-pulse"></div>
        <div className="grid gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-gray-800/50 rounded-xl animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-red-600 via-red-700 to-black p-12 animate-slide-down">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-1/3 w-96 h-96 bg-white rounded-full mix-blend-screen blur-3xl animate-pulse"></div>
        </div>
        <div className="relative z-10">
          <div className="inline-block bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-bold text-white mb-4">
            🏁 {season} SEASON
          </div>
          <h1 className="text-5xl md:text-6xl font-black text-white mb-3">
            {season} Calendar
          </h1>
          <p className="text-xl text-red-100">
            {events?.length || 0} races • Champions crowned • Historic season
          </p>
        </div>
      </section>

      {/* Champions Bar */}
      {(driverChampion || constructorChampion) && (
        <ChampionsBar
          season={season}
          driverChampion={driverChampion ? {
            name: driverChampion.driver_name,
            code: driverChampion.driver_code,
            points: driverChampion.total_points || 0
          } : undefined}
          constructorChampion={constructorChampion ? {
            name: constructorChampion.constructor_name,
            points: constructorChampion.total_points || 0
          } : undefined}
        />
      )}

      {/* Race Calendar */}
      <section>
        <h2 className="text-3xl font-bold mb-6">Race Calendar</h2>
        
        {events?.length === 0 ? (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-12 text-center">
            <Calendar className="mx-auto mb-4 text-gray-500" size={48} />
            <p className="text-xl text-gray-400">No races found for {season}</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {events?.map((event: any, idx: number) => (
              <Link
                key={event.event_id}
                href={`/races/${season}/${event.event_id}`}
                className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800 hover:border-red-600/50 transition-all group"
                style={{ animationDelay: `${idx * 0.05}s` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6">
                    {/* Round Badge */}
                    <div className="bg-red-600 text-white font-black text-2xl rounded-lg w-16 h-16 flex items-center justify-center">
                      {event.round}
                    </div>

                    {/* Race Info */}
                    <div>
                      <h3 className="text-2xl font-bold mb-2 group-hover:text-red-400 transition">
                        {event.event_name}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-400">
                        <div className="flex items-center gap-1">
                          <MapPin size={14} />
                          <span>{event.location}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar size={14} />
                          <span>{formatDate(event.event_date)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Arrow Icon */}
                  <ChevronRight className="text-gray-500 group-hover:text-red-400 group-hover:translate-x-1 transition" size={28} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
