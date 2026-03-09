'use client';

import { useQuery } from '@tanstack/react-query';
import { Database, Clock, CheckCircle, XCircle, HardDrive, BarChart3 } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export default function IngestStatusPage() {
  const { data: seasons } = useQuery({
    queryKey: ['ingest-seasons'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/seasons');
      return res.json();
    },
  });

  const seasonMin = Array.isArray(seasons) && seasons.length ? Math.min(...seasons) : null;
  const seasonMax = Array.isArray(seasons) && seasons.length ? Math.max(...seasons) : null;
  const seasonRange = seasonMin && seasonMax ? `${seasonMin}-${seasonMax}` : 'season range varies';

  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ['ingest-logs'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/ingest/logs?limit=20');
      return res.json();
    },
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['ingest-summary'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/ingest/summary');
      return res.json();
    },
  });

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['ingest-status'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/ingest/status');
      return res.json();
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'failed':
        return 'text-red-400';
      case 'running':
        return 'text-blue-400';
      case 'cancelled':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-900/30 border-green-700/50';
      case 'failed':
        return 'bg-red-900/30 border-red-700/50';
      case 'running':
        return 'bg-blue-900/30 border-blue-700/50';
      case 'cancelled':
        return 'bg-yellow-900/30 border-yellow-700/50';
      default:
        return 'bg-gray-800/30 border-gray-700/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-400" size={20} />;
      case 'failed':
        return <XCircle className="text-red-400" size={20} />;
      case 'running':
        return <div className="animate-spin"><Clock className="text-blue-400" size={20} /></div>;
      default:
        return <Clock className="text-gray-400" size={20} />;
    }
  };

  return (
    <div className="space-y-12">
      {/* Hero Header */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-cyan-600 via-cyan-700 to-cyan-800 p-12 md:p-20 animate-slide-down">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full mix-blend-screen blur-3xl"></div>
        </div>
        <div className="relative z-10">
          <div className="inline-block bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-semibold text-white mb-4">
            💾 DATA INGESTION STATUS
          </div>
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">Ingestion Monitor</h1>
          <p className="text-xl text-cyan-100 max-w-2xl">Track data ingestion history, storage location, and real-time ingestion status.</p>
        </div>
      </section>

      {/* Storage Info */}
      <section className="space-y-6">
        <h2 className="text-3xl font-bold">📁 Data Storage</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Database Location */}
          <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 border border-purple-700/50 rounded-xl p-8 hover-lift">
            <div className="flex items-start gap-4">
              <Database className="text-purple-400 flex-shrink-0 mt-1" size={32} />
              <div>
                <h3 className="text-xl font-bold mb-2">Primary Database</h3>
                <p className="text-gray-400 mb-3">SQLite database containing all ingested F1 data</p>
                <div className="bg-gray-900/40 rounded-lg p-4 font-mono text-sm text-gray-300 break-all">
                  /Users/mohitunecha/F1/backend/f1.db
                </div>
              </div>
            </div>
          </div>

          {/* Ingest Logs Location */}
          <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-700/50 rounded-xl p-8 hover-lift">
            <div className="flex items-start gap-4">
              <HardDrive className="text-blue-400 flex-shrink-0 mt-1" size={32} />
              <div>
                <h3 className="text-xl font-bold mb-2">Ingestion Logs</h3>
                <p className="text-gray-400 mb-3">Stored in database ingest_logs table</p>
                <div className="bg-gray-900/40 rounded-lg p-4 font-mono text-sm text-gray-300">
                  Table: ingest_logs
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Current Status */}
      {status && !statusLoading && (
        <section className="space-y-6">
          <h2 className="text-3xl font-bold">⚡ Current Status</h2>
          
          <div className={`${getStatusBg(status.status)} border rounded-xl p-8 hover-lift`}>
            <div className="flex items-start gap-4">
              {getStatusIcon(status.status)}
              <div className="flex-1">
                <h3 className={`text-2xl font-bold mb-2 capitalize ${getStatusColor(status.status)}`}>
                  {status.status}
                </h3>
                <p className="text-gray-300 mb-4">{status.message}</p>
                
                {status.completed_at && (
                  <div className="text-sm text-gray-400">
                    Last ingestion completed: {new Date(status.completed_at).toLocaleString()}
                  </div>
                )}
                
                {status.duration_seconds && (
                  <div className="text-sm text-gray-400">
                    Duration: {status.duration_seconds.toFixed(2)} seconds
                  </div>
                )}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-700">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">{status.events_ingested || 0}</div>
                <div className="text-xs text-gray-500">Events</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{status.drivers_ingested || 0}</div>
                <div className="text-xs text-gray-500">Drivers</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-400">{status.sessions_ingested || 0}</div>
                <div className="text-xs text-gray-500">Sessions</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-400">{status.seasons_ingested || 0}</div>
                <div className="text-xs text-gray-500">Seasons</div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Summary Statistics */}
      {summary && !summaryLoading && (
        <section className="space-y-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="text-orange-400" size={32} />
            <h2 className="text-3xl font-bold">📊 All-Time Summary</h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Total Runs</div>
              <div className="text-3xl font-bold text-blue-400">{summary.total_runs}</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Successful</div>
              <div className="text-3xl font-bold text-green-400">{summary.successful_runs}</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Failed</div>
              <div className="text-3xl font-bold text-red-400">{summary.failed_runs}</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Total Events</div>
              <div className="text-3xl font-bold text-yellow-400">{summary.total_events_ingested}</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Total Drivers</div>
              <div className="text-3xl font-bold text-purple-400">{summary.total_drivers_ingested}</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center hover-lift">
              <div className="text-sm text-gray-400 mb-2">Avg Duration</div>
              <div className="text-3xl font-bold text-green-400">{summary.avg_duration_seconds?.toFixed(1) || 0}s</div>
            </div>
          </div>
        </section>
      )}

      {/* Ingestion History */}
      {logs && !logsLoading && logs.length > 0 && (
        <section className="space-y-6">
          <h2 className="text-3xl font-bold">📜 Ingestion History</h2>

          <div className="space-y-4">
            {logs.map((log: any, idx: number) => (
              <div
                key={log.id}
                className={`${getStatusBg(log.status)} border rounded-lg p-6 hover-lift stagger-item`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3 flex-1">
                    {getStatusIcon(log.status)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`font-bold capitalize ${getStatusColor(log.status)}`}>
                          {log.status}
                        </span>
                        <span className="text-xs text-gray-500">
                          • {new Date(log.started_at).toLocaleDateString()} {new Date(log.started_at).toLocaleTimeString()}
                        </span>
                      </div>
                      {log.source && (
                        <div className="text-sm text-gray-400">Source: {log.source}</div>
                      )}
                    </div>
                  </div>
                  {log.duration_seconds && (
                    <div className="text-right">
                      <div className="text-sm font-bold">{log.duration_seconds.toFixed(2)}s</div>
                      <div className="text-xs text-gray-500">Duration</div>
                    </div>
                  )}
                </div>

                {/* Data counts */}
                <div className="grid grid-cols-4 gap-2 text-xs bg-black/30 rounded p-3">
                  <div className="text-center">
                    <div className="font-bold text-yellow-400">{log.events_ingested}</div>
                    <div className="text-gray-500">Events</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-green-400">{log.drivers_ingested}</div>
                    <div className="text-gray-500">Drivers</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-blue-400">{log.sessions_ingested}</div>
                    <div className="text-gray-500">Sessions</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-purple-400">{log.seasons_ingested}</div>
                    <div className="text-gray-500">Seasons</div>
                  </div>
                </div>

                {log.error_message && (
                  <div className="mt-3 text-sm text-red-300 bg-red-900/30 rounded p-2">
                    Error: {log.error_message}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Info Section */}
      <section className="bg-cyan-900/20 border border-cyan-700/50 rounded-xl p-8">
        <h3 className="text-xl font-bold mb-4">ℹ️ About Data Storage</h3>
        <div className="space-y-3 text-gray-300">
          <p>
            <strong>Database:</strong> All ingested F1 data is stored in a SQLite database at <code className="bg-gray-900/50 px-2 py-1 rounded">/Users/mohitunecha/F1/backend/f1.db</code>
          </p>
          <p>
            <strong>Ingestion Logs:</strong> Every ingestion run is tracked in the <code className="bg-gray-900/50 px-2 py-1 rounded">ingest_logs</code> table, including timestamp, status, data counts, and error messages if any.
          </p>
          <p>
            <strong>Tables Created:</strong> Events, Sessions, Drivers, Standings, Predictions, and Ingest Logs
          </p>
          <p>
            <strong>Data Source:</strong> Primary ingestion uses FastF1, with supplemental external endpoints (OpenF1/Jolpica) for additional coverage.
          </p>
          <p>
            <strong>Current Data:</strong> {summary?.total_events_ingested || 0} events across {summary?.total_drivers_ingested || 0} drivers from {Array.isArray(seasons) ? seasons.length : 0} seasons ({seasonRange})
          </p>
        </div>
      </section>
    </div>
  );
}
