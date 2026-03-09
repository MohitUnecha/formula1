'use client';
import { useQuery } from '@tanstack/react-query';
import { Code2, Database, Brain, Gauge, Globe, Mail, ExternalLink, Cpu, Layers, BarChart3, Zap, Heart, Github, BookOpen } from 'lucide-react';
import api from '@/lib/api';

const TECH_STACK = [
  {
    category: 'Frontend',
    color: '#3b82f6',
    items: [
      { name: 'Next.js 14', desc: 'React framework with App Router, server components, and optimized rendering', icon: '⚡' },
      { name: 'React 18', desc: 'Component-based UI with hooks, suspense, and concurrent features', icon: '⚛️' },
      { name: 'TypeScript', desc: 'Type-safe JavaScript for robust, maintainable code', icon: '🔷' },
      { name: 'TailwindCSS', desc: 'Utility-first CSS framework for rapid, responsive styling', icon: '🎨' },
      { name: 'React Query', desc: 'Server state management with automatic caching and refetching', icon: '🔄' },
      { name: 'Lucide Icons', desc: 'Beautiful, consistent icon library for the entire UI', icon: '✨' },
    ],
  },
  {
    category: 'Backend',
    color: '#10b981',
    items: [
      { name: 'FastAPI', desc: 'High-performance async Python API framework with automatic OpenAPI docs', icon: '🚀' },
      { name: 'SQLAlchemy', desc: 'Python ORM for database modeling and queries', icon: '🗃️' },
      { name: 'SQLite', desc: 'Lightweight, file-based relational database for local deployment', icon: '💾' },
      { name: 'FastF1', desc: 'Community-maintained Python library for F1 timing, telemetry, and session data', icon: '🏎️' },
      { name: 'Python 3.11+', desc: 'Core language for data processing and API logic', icon: '🐍' },
    ],
  },
  {
    category: 'Data & ML',
    color: '#a855f7',
    items: [
      { name: 'Gradient Boosting', desc: 'Machine learning model for race outcome predictions', icon: '🧠' },
      { name: 'scikit-learn', desc: 'ML library for model training, evaluation, and feature engineering', icon: '📊' },
      { name: 'FastF1 Telemetry', desc: 'Real car telemetry data: speed, throttle, brake, gear, DRS', icon: '📡' },
      { name: 'SHAP', desc: 'Explainable AI: understand why models make specific predictions', icon: '🔍' },
    ],
  },
  {
    category: 'AI & LLM',
    color: '#f59e0b',
    items: [
      { name: 'Multi-AI Consensus', desc: 'Multi-provider LLM ensemble for race context and analysis', icon: '🤖' },
      { name: 'Groq LPU', desc: 'Ultra-fast inference for real-time AI analysis', icon: '⚡' },
      { name: 'Tavily Search', desc: 'Real-time web search for latest F1 news and context', icon: '🔍' },
    ],
  },
];

const DATA_SOURCES = [
  {
    name: 'FastF1',
    url: 'https://github.com/theOehrly/Fast-F1',
    desc: 'The primary data source for telemetry, timing, and session data. FastF1 is an open-source Python library that provides access to F1 timing data and telemetry.',
    author: 'theOehrly',
    icon: '🏎️',
  },
  {
    name: 'F1 Race Replay',
    url: 'https://github.com/recursivecurry/f1-race-replay',
    desc: 'Inspiration and reference for race replay visualization, tyre degradation modeling, and Bayesian tyre analysis. A fantastic open-source project for F1 data visualization.',
    author: 'recursivecurry',
    icon: '🔄',
  },
  {
    name: 'OpenF1 API',
    url: 'https://openf1.org',
    desc: 'Real-time and historical F1 data API providing live timing, car data, and session information.',
    author: 'OpenF1 Community',
    icon: '📡',
  },
  {
    name: 'Jolpica F1 API',
    url: 'https://github.com/jolpica/jolpica-f1',
    desc: 'Comprehensive F1 results database API, successor to the Ergast API. Used for historical race results, standings, and driver/constructor data.',
    author: 'Jolpica',
    icon: '📊',
  },
  {
    name: 'Formula 1 Media',
    url: 'https://formula1.com',
    desc: 'Formula 1 website and media references used for public driver/team/circuit context.',
    author: 'Formula One Management',
    icon: '🏁',
  },
];

const FEATURES = [
  { icon: <Gauge size={20} />, title: 'Race Replay', desc: 'Animated replay of any race with driver positions, weather, tyre strategy, and DRS zones on real circuit layouts' },
  { icon: <BarChart3 size={20} />, title: 'Deep Analytics', desc: 'Lap times, position changes, tyre strategy, and telemetry visualization across ingested seasons' },
  { icon: <Brain size={20} />, title: 'ML Predictions', desc: 'Gradient Boosting model predicts race outcomes using qualifying data, historical performance, and circuit characteristics' },
  { icon: <Layers size={20} />, title: 'Driver & Team Comparison', desc: 'Head-to-head stats comparison between any two drivers or constructors across seasons' },
  { icon: <Database size={20} />, title: 'Dataset Coverage', desc: 'Coverage depends on your ingested seasons and available source data' },
  { icon: <Zap size={20} />, title: 'Sprint Races', desc: 'Full sprint race support with separate session handling and results' },
];

export default function AboutPage() {
  const { data: ingestSummary } = useQuery({
    queryKey: ['ingest-summary-about'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/api/ingest/summary');
      return res.json();
    },
  });

  const { data: seasons } = useQuery({
    queryKey: ['seasons-about'],
    queryFn: () => api.getSeasons(),
  });

  const { data: drivers } = useQuery({
    queryKey: ['drivers-about'],
    queryFn: () => api.getDrivers(),
  });

  const seasonMin = seasons?.length ? Math.min(...seasons) : null;
  const seasonMax = seasons?.length ? Math.max(...seasons) : null;
  const seasonRange = seasonMin && seasonMax ? `${seasonMin}–${seasonMax}` : 'Ingested range';

  const STATS = [
    { label: 'Events', value: String(ingestSummary?.total_events_ingested || 0), sub: 'Ingested events' },
    { label: 'Runs', value: String(ingestSummary?.total_runs || 0), sub: 'Ingestion runs' },
    { label: 'Drivers', value: String(drivers?.length || 0), sub: 'Tracked in DB' },
    { label: 'Seasons', value: String(seasons?.length || 0), sub: seasonRange },
  ];

  return (
    <div className="space-y-10 max-w-5xl mx-auto">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#0a0015] via-[#0d1a2d] to-[#0a192f] p-5 md:p-10 border border-white/5">
        <div className="absolute inset-0 opacity-15">
          <div className="absolute top-0 right-12 w-72 h-72 bg-red-600 rounded-full blur-[140px]" />
          <div className="absolute bottom-0 left-12 w-56 h-56 bg-blue-600 rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10">
          <h1 className="text-4xl font-black tracking-tight mb-4 bg-gradient-to-r from-red-500 via-white to-blue-400 bg-clip-text text-transparent">
            About F1 Analytics
          </h1>
          <p className="text-gray-400 text-lg max-w-3xl leading-relaxed">
            A full-stack Formula 1 analytics and prediction platform, built from scratch with real telemetry data, 
            machine learning models, and a passion for motorsport. Every lap time, every pit stop, every overtake — analyzed and visualized.
          </p>
        </div>
      </section>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STATS.map(s => (
          <div key={s.label} className="bg-[#0d1117] rounded-xl border border-white/5 p-5 text-center group hover:border-red-500/30 transition-colors">
            <div className="text-3xl font-black text-white group-hover:text-red-400 transition-colors">{s.value}</div>
            <div className="text-sm font-bold text-gray-300 mt-1">{s.label}</div>
            <div className="text-xs text-gray-500">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* How It Works */}
      <section className="bg-[#0d1117] rounded-2xl border border-white/5 p-4 md:p-8">
        <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
          <Cpu size={22} className="text-blue-400" /> How It Was Built
        </h2>
        <div className="space-y-6 text-gray-300 leading-relaxed">
          <div className="flex gap-4">
            <div className="w-8 h-8 shrink-0 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 font-black text-sm">1</div>
            <div>
              <h3 className="font-bold text-white mb-1">Data Ingestion</h3>
              <p className="text-sm text-gray-400">
                Telemetry and timing data is ingested from FastF1 with supplemental sources where available.
                Coverage depends on the seasons loaded into this deployment, with richer telemetry typically in the modern era.
                This includes lap times, sector splits, pit stops, tyre compounds, weather conditions, and race control events.
                Sprint races are handled as separate sessions with their own data pipeline.
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-8 h-8 shrink-0 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-black text-sm">2</div>
            <div>
              <h3 className="font-bold text-white mb-1">Circuit Mapping</h3>
              <p className="text-sm text-gray-400">
                All 24 modern F1 circuits were generated as SVG paths from real telemetry data — actual car GPS traces, 
                not approximations. DRS detection zones, pit lane positions, and sector boundaries were computed by 
                mapping circuit-specific fractions along the interpolated track paths.
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-8 h-8 shrink-0 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 font-black text-sm">3</div>
            <div>
              <h3 className="font-bold text-white mb-1">Machine Learning</h3>
              <p className="text-sm text-gray-400">
                A Gradient Boosting classifier was trained on historical race data to predict finishing positions. 
                Features include qualifying position, recent form, circuit type, weather, and team performance trends. 
                SHAP explainability shows which factors drive each prediction.
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-8 h-8 shrink-0 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 font-black text-sm">4</div>
            <div>
              <h3 className="font-bold text-white mb-1">Interactive Frontend</h3>
              <p className="text-sm text-gray-400">
                The frontend was built with Next.js 14 and React to deliver a fast, responsive experience. 
                Custom SVG visualizations render analytics charts, circuit maps, and animated race replays entirely on the client — 
                no charting libraries needed. TailwindCSS handles the dark, glassmorphic F1-inspired design system.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section>
        <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
          <Zap size={22} className="text-yellow-400" /> Platform Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FEATURES.map(f => (
            <div key={f.title} className="bg-[#0d1117] rounded-xl border border-white/5 p-5 hover:border-white/10 transition-colors">
              <div className="flex items-center gap-3 mb-2">
                <div className="text-red-400">{f.icon}</div>
                <h3 className="font-bold">{f.title}</h3>
              </div>
              <p className="text-sm text-gray-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section>
        <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
          <Code2 size={22} className="text-green-400" /> Technology Stack
        </h2>
        <div className="space-y-6">
          {TECH_STACK.map(cat => (
            <div key={cat.category} className="bg-[#0d1117] rounded-xl border border-white/5 overflow-hidden">
              <div className="px-5 py-3 border-b border-white/5 flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cat.color }} />
                <h3 className="font-bold text-sm uppercase tracking-wider" style={{ color: cat.color }}>{cat.category}</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-white/5">
                {cat.items.map(item => (
                  <div key={item.name} className="bg-[#0d1117] p-4 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">{item.icon}</span>
                      <span className="font-bold text-sm">{item.name}</span>
                    </div>
                    <p className="text-xs text-gray-500">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Data Sources & Credits */}
      <section>
        <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
          <Heart size={22} className="text-red-400" /> Data Sources & Credits
        </h2>
        <p className="text-gray-400 text-sm mb-6">
          This project would not be possible without the amazing open-source community and data providers. 
          Special thanks to all the developers and organizations who make F1 data accessible.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {DATA_SOURCES.map(source => (
            <a 
              key={source.name}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group bg-[#0d1117] rounded-xl border border-white/5 p-5 hover:border-white/20 hover:bg-white/[0.02] transition-all"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{source.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-white group-hover:text-red-400 transition-colors">{source.name}</h3>
                    <ExternalLink size={12} className="text-gray-600 group-hover:text-red-400 transition-colors" />
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{source.desc}</p>
                  <div className="flex items-center gap-1 text-xs text-gray-600">
                    <Github size={12} />
                    <span>{source.author}</span>
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Special Thanks */}
      <section className="bg-[#0d1117] rounded-xl border border-white/5 p-6">
        <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
          <BookOpen size={18} className="text-blue-400" /> Special Thanks
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-400">
          <div>
            <h4 className="font-bold text-white mb-2">F1 Race Replay Project</h4>
            <p>
              The race replay visualization was inspired by the excellent <a href="https://github.com/recursivecurry/f1-race-replay" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">f1-race-replay</a> project. 
              Key concepts like tyre degradation modeling, Bayesian tyre analysis, and telemetry visualization were adapted from this project.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-2">FastF1 Community</h4>
            <p>
              Many thanks to <a href="https://github.com/theOehrly" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">theOehrly</a> and all contributors to the FastF1 library. 
              Without their work making F1 telemetry data accessible, this project wouldn't exist.
            </p>
          </div>
        </div>
      </section>

      {/* About Me / Contact */}
      <section className="bg-gradient-to-br from-red-500/10 via-[#0d1117] to-blue-500/10 rounded-2xl border border-white/5 p-8">
        <h2 className="text-2xl font-black mb-4 flex items-center gap-2">
          <Globe size={22} className="text-blue-400" /> About the Creator
        </h2>
        <p className="text-gray-400 leading-relaxed mb-6">
          Built by <span className="text-white font-bold">Mohit Unecha</span> — a developer and F1 enthusiast who wanted 
          to combine data engineering, machine learning, and motorsport into one platform. Every feature was designed to 
          bring the depth of F1 data closer to fans who want more than just watching races.
        </p>
        <div className="flex flex-wrap gap-4">
          <a href="https://mohitunecha.com" target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-red-700 text-white font-bold text-sm hover:brightness-110 transition-all shadow-lg shadow-red-500/20">
            <Globe size={16} /> mohitunecha.com <ExternalLink size={12} />
          </a>
          <a href="mailto:contact@mohitunecha.com"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/10 text-white font-bold text-sm hover:bg-white/15 transition-all">
            <Mail size={16} /> Get In Touch
          </a>
        </div>
      </section>

      {/* Footer attribution */}
      <div className="text-center text-xs text-gray-600 pb-4 space-y-2">
        <p>Data sourced from FastF1, OpenF1, Jolpica API & Formula 1 Media</p>
        <p>Race replay inspired by <a href="https://github.com/recursivecurry/f1-race-replay" className="text-blue-500 hover:underline">f1-race-replay</a></p>
        <p>Built with Next.js, FastAPI, and SQLite • &copy; {new Date().getFullYear()} Mohit Unecha</p>
      </div>
    </div>
  );
}
