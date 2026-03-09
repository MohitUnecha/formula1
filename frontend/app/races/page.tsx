'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Calendar, MapPin, Users, AlertCircle, Search, Flag, ChevronDown, Trophy, TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import { Event } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export default function RacesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSeason, setSelectedSeason] = useState<number>(2026);

  const isSprintWeekend = (event: Event) =>
    Boolean(event.has_sprint || event.event_format?.toLowerCase().includes('sprint'));

  const { data: seasons, isLoading: seasonsLoading } = useQuery({
    queryKey: ['seasons'],
    queryFn: () => api.getSeasons(),
  });

  const { data: events, isLoading: eventsLoading, error: eventsError } = useQuery<Event[]>({
    queryKey: ['events', selectedSeason],
    queryFn: () => api.getEvents(selectedSeason),
    enabled: !!selectedSeason,
  });

  const filteredEvents = events?.filter(event =>
    event.event_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    event.country.toLowerCase().includes(searchTerm.toLowerCase()) ||
    event.location.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const sprintCount = events?.filter(isSprintWeekend).length || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#111318] to-[#0a0c10] border border-white/[0.06] p-5 md:p-12">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.12),transparent_60%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div className="relative z-10">
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-bold mb-2 text-white">Race Calendar</h1>
          <p className="text-xl text-gray-400 mb-6">
            Complete {selectedSeason} season schedule with full race details
          </p>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-4 top-3 text-gray-500" size={20} />
            <input
              type="text"
              placeholder="Search by race name, location, or country..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white/[0.05] border border-white/10 rounded-lg px-12 py-3 text-white placeholder-gray-500 backdrop-blur-sm focus:outline-none focus:border-blue-500/50"
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="absolute right-4 top-3 text-gray-400 hover:text-white transition">
                ✕
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Season Selector */}
      <section className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-gray-400 font-bold mr-1">SEASON:</span>
        {seasonsLoading ? (
          <div className="animate-pulse h-9 w-48 bg-gray-700 rounded-lg" />
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {/* Decade groups */}
            {seasons && (() => {
              const sorted = [...seasons].sort((a, b) => b - a);
              return sorted.map((s: number) => (
                <button
                  key={s}
                  onClick={() => setSelectedSeason(s)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${
                    selectedSeason === s
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  {s}
                </button>
              ));
            })()}
          </div>
        )}
      </section>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Races', value: events?.length || 0, color: 'text-blue-400' },
          { label: 'Matching', value: filteredEvents.length, color: 'text-blue-400' },
          { label: 'Sprint Races', value: sprintCount, color: 'text-orange-400' },
          { label: 'Season', value: selectedSeason, color: 'text-green-400' },
        ].map(s => (
          <div key={s.label} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Events grid */}
      {eventsLoading ? (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4" />
            <p className="text-gray-400">Loading races for {selectedSeason}...</p>
          </div>
        </div>
      ) : eventsError ? (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 flex gap-4">
          <AlertCircle className="text-red-500 flex-shrink-0" size={24} />
          <div>
            <h3 className="font-bold text-red-400 mb-2">Error Loading Events</h3>
            <p className="text-gray-300">{String(eventsError)}</p>
          </div>
        </div>
      ) : filteredEvents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredEvents.map((event) => (
            <Link
              key={event.event_id}
              href={`/races/${event.season}/${event.event_id}`}
              className="group relative overflow-hidden rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-blue-500/40 transition-all hover:shadow-xl hover:shadow-blue-600/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-transparent opacity-0 group-hover:opacity-100 transition" />
              <div className="relative p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="inline-block bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-xs font-bold mb-3">
                      ROUND {event.round}
                    </div>
                    <h3 className="text-2xl font-bold group-hover:text-blue-400 transition mb-1">
                      {event.event_name}
                    </h3>
                  </div>
                  <Flag className="text-blue-500 flex-shrink-0 mt-1" size={24} />
                </div>
                {isSprintWeekend(event) && (
                  <div className="inline-block bg-orange-500/20 text-orange-400 px-2 py-1 rounded text-xs font-bold mb-4 border border-orange-500/50">
                    SPRINT WEEKEND
                  </div>
                )}
                <div className="space-y-3 text-sm text-gray-400 mb-6">
                  <div className="flex items-center gap-2">
                    <MapPin size={16} className="text-blue-400 flex-shrink-0" />
                    <span className="font-medium">{event.location}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar size={16} className="text-blue-400 flex-shrink-0" />
                    <span>{formatDate(event.event_date)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Users size={16} className="text-blue-400 flex-shrink-0" />
                    <span>{event.session_count} sessions</span>
                  </div>
                  <div className="text-xs text-gray-500 pt-2">
                    {event.country}
                  </div>
                </div>
                <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition">
                  View Details →
                </button>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-12 text-center">
          <p className="text-xl text-gray-400 mb-4">
            {searchTerm ? 'No races match your search' : `No race data for ${selectedSeason}`}
          </p>
          <p className="text-gray-500 text-sm mb-6">
            {searchTerm ? 'Try adjusting your search term' : 'This season may not have been ingested yet'}
          </p>
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg transition">
              Clear Search
            </button>
          )}
        </div>
      )}
    </div>
  );
}
