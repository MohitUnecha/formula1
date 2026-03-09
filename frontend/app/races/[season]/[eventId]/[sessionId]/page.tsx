'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Trophy, TrendingUp, Activity, Play } from 'lucide-react';
import { Tab } from '@headlessui/react';
import api from '@/lib/api';
import { Session, Prediction, DriverSession } from '@/lib/types';
import PredictionCard from '@/components/predictions/PredictionCard';

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = parseInt(params.sessionId as string);
  const eventId = parseInt(params.eventId as string);
  const season = parseInt(params.season as string);

  const { data: session, isLoading: sessionLoading } = useQuery<Session>({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSession(sessionId),
  });

  const { data: predictions, isLoading: predictionsLoading } = useQuery<Prediction[]>({
    queryKey: ['predictions', sessionId],
    queryFn: () => api.getPredictions(sessionId),
    retry: false,
  });

  const { data: drivers } = useQuery<DriverSession[]>({
    queryKey: ['session-drivers', sessionId],
    queryFn: () => api.getSessionDrivers(sessionId),
  });

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-red-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading session...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <p className="text-xl text-gray-400">Session not found</p>
      </div>
    );
  }

  const isRace = session.session_type === 'R';

  return (
    <div className="space-y-8">
      {/* Back button */}
      <Link
        href={`/races/${params.season}/${eventId}`}
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition"
      >
        <ArrowLeft size={20} />
        Back to Event
      </Link>

      {/* Session header */}
      <div className="bg-gradient-to-r from-red-900/30 to-gray-800/30 border border-gray-700 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">{session.event_name}</h1>
            <p className="text-gray-400">{session.session_type === 'R' ? 'Race' : session.session_type}</p>
          </div>
          {isRace && (
            <Trophy className="text-yellow-400" size={48} />
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tab.Group>
        <Tab.List className="flex space-x-2 bg-gray-800/50 p-1 rounded-lg border border-gray-700">
          <Tab className={({ selected }) =>
            `flex-1 py-3 px-4 rounded-lg font-semibold transition ${
              selected
                ? 'bg-red-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`
          }>
            <div className="flex items-center justify-center gap-2">
              <TrendingUp size={20} />
              Predictions
            </div>
          </Tab>
          {isRace && (
            <Tab className={({ selected }) =>
              `flex-1 py-3 px-4 rounded-lg font-semibold transition ${
                selected
                  ? 'bg-red-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`
            }>
              <div className="flex items-center justify-center gap-2">
                <Activity size={20} />
                Race Replay
              </div>
            </Tab>
          )}
          <Tab className={({ selected }) =>
            `flex-1 py-3 px-4 rounded-lg font-semibold transition ${
              selected
                ? 'bg-red-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`
          }>
            <div className="flex items-center justify-center gap-2">
              <Trophy size={20} />
              Results
            </div>
          </Tab>
        </Tab.List>

        <Tab.Panels className="mt-8">
          {/* Predictions Panel */}
          <Tab.Panel>
            {predictionsLoading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-red-500"></div>
              </div>
            ) : predictions && predictions.length > 0 ? (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold">Race Predictions</h2>
                  <div className="text-sm text-gray-400">
                    Powered by Ensemble ML (XGBoost + LightGBM + CatBoost)
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {predictions.map((prediction) => (
                    <PredictionCard key={prediction.driver_code} prediction={prediction} sessionId={sessionId} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-12 text-center">
                <p className="text-xl text-gray-400 mb-4">No predictions available</p>
                <p className="text-gray-500 mb-6">
                  Predictions need to be computed for this session
                </p>
                <button
                  onClick={async () => {
                    try {
                      await api.computePredictions(sessionId);
                      window.location.reload();
                    } catch (error) {
                      alert('Failed to compute predictions. Make sure models are trained.');
                    }
                  }}
                  className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg transition"
                >
                  Compute Predictions
                </button>
              </div>
            )}
          </Tab.Panel>

          {/* Race Replay Panel */}
          {isRace && (
            <Tab.Panel>
              <div className="text-center py-16">
                <div className="text-6xl mb-6">🏎️</div>
                <h2 className="text-3xl font-bold mb-4">Full Race Replay</h2>
                <p className="text-gray-400 mb-8 max-w-md mx-auto">
                  Experience the complete race with animated driver positions, weather data, 
                  tyre strategy, pit stops, and DRS zones on an accurate circuit layout.
                </p>
                <button
                  onClick={() => router.push(`/replay?season=${season}&event=${eventId}`)}
                  className="inline-flex items-center gap-3 bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-8 rounded-xl transition-all shadow-lg shadow-red-900/30 text-lg"
                >
                  <Play size={24} />
                  Open Race Replay
                </button>
                <p className="text-gray-500 text-sm mt-4">
                  Opens in full-screen replay mode with all telemetry and controls
                </p>
              </div>
            </Tab.Panel>
          )}

          {/* Results Panel */}
          <Tab.Panel>
            {drivers && drivers.length > 0 ? (
              <div>
                <h2 className="text-2xl font-bold mb-6">Session Results</h2>
                <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-900/50 border-b border-gray-700">
                      <tr>
                        <th className="px-6 py-4 text-left text-sm font-semibold">Pos</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold">Driver</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold">Team</th>
                        <th className="px-6 py-4 text-right text-sm font-semibold">Grid</th>
                        <th className="px-6 py-4 text-right text-sm font-semibold">Points</th>
                        <th className="px-6 py-4 text-right text-sm font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {drivers
                        .sort((a, b) => (a.position || 99) - (b.position || 99))
                        .map((driver, idx) => (
                          <tr key={driver.driver_code} className="border-b border-gray-700 hover:bg-gray-800/50 transition">
                            <td className="px-6 py-4 font-bold">{driver.position || '-'}</td>
                            <td className="px-6 py-4">
                              <div className="font-semibold">{driver.driver_code}</div>
                              <div className="text-sm text-gray-400">{driver.driver_name}</div>
                            </td>
                            <td className="px-6 py-4 text-gray-300">{driver.team_name}</td>
                            <td className="px-6 py-4 text-right text-gray-400">{driver.grid || '-'}</td>
                            <td className="px-6 py-4 text-right font-semibold">{driver.points || 0}</td>
                            <td className="px-6 py-4 text-right">
                              {driver.dnf ? (
                                <span className="text-red-400">DNF</span>
                              ) : (
                                <span className="text-green-400">Finished</span>
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-12 text-center">
                <p className="text-xl text-gray-400">No results available</p>
              </div>
            )}
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
