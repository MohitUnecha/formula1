'use client';

import { Trophy } from 'lucide-react';

interface Champion {
  name: string;
  code?: string;
  points: number;
}

interface ChampionsBarProps {
  driverChampion?: Champion;
  constructorChampion?: Champion;
  season: number;
  className?: string;
}

export default function ChampionsBar({ 
  driverChampion, 
  constructorChampion, 
  season,
  className = '' 
}: ChampionsBarProps) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 ${className}`}>
      {/* Driver Champion */}
      <div className="bg-gradient-to-br from-yellow-600/20 to-yellow-900/20 border-2 border-yellow-600/30 rounded-xl p-6 hover-lift backdrop-blur-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-yellow-600/20 rounded-lg">
            <Trophy className="text-yellow-400" size={28} />
          </div>
          <div>
            <div className="text-sm text-yellow-400/70 font-semibold">DRIVERS' CHAMPION</div>
            <div className="text-xs text-gray-400">{season} Season</div>
          </div>
        </div>
        {driverChampion ? (
          <div>
            <div className="flex items-baseline gap-2 mb-2">
              {driverChampion.code && (
                <div className="text-5xl font-black text-yellow-400">
                  {driverChampion.code}
                </div>
              )}
              <div className="text-2xl font-bold text-yellow-300">
                {driverChampion.name}
              </div>
            </div>
            <div className="text-3xl font-black text-white">
              {driverChampion.points} pts
            </div>
          </div>
        ) : (
          <div className="text-gray-400 italic">Season in progress...</div>
        )}
      </div>

      {/* Constructor Champion */}
      <div className="bg-gradient-to-br from-orange-600/20 to-orange-900/20 border-2 border-orange-600/30 rounded-xl p-6 hover-lift backdrop-blur-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-orange-600/20 rounded-lg">
            <Trophy className="text-orange-400" size={28} />
          </div>
          <div>
            <div className="text-sm text-orange-400/70 font-semibold">CONSTRUCTORS' CHAMPION</div>
            <div className="text-xs text-gray-400">{season} Season</div>
          </div>
        </div>
        {constructorChampion ? (
          <div>
            <div className="text-2xl font-bold text-orange-300 mb-2">
              {constructorChampion.name}
            </div>
            <div className="text-3xl font-black text-white">
              {constructorChampion.points} pts
            </div>
          </div>
        ) : (
          <div className="text-gray-400 italic">Season in progress...</div>
        )}
      </div>
    </div>
  );
}
