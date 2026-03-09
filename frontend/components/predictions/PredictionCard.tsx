'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import api from '@/lib/api';
import { Prediction, Explainability } from '@/lib/types';
import { formatProbability, getPositionColor } from '@/lib/utils';

interface PredictionCardProps {
  prediction: Prediction;
  sessionId: number;
}

export default function PredictionCard({ prediction, sessionId }: PredictionCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [showExplainability, setShowExplainability] = useState(false);

  const { data: explainability, isLoading: explainabilityLoading } = useQuery<Explainability>({
    queryKey: ['explainability', sessionId, prediction.driver_code],
    queryFn: () => api.getExplainability(sessionId, prediction.driver_code),
    enabled: showExplainability,
  });

  const getProbabilityColor = (prob: number) => {
    if (prob > 0.7) return 'bg-green-500';
    if (prob > 0.4) return 'bg-yellow-500';
    if (prob > 0.2) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="driver-card">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-2xl font-bold">{prediction.driver_code}</h3>
          <p className="text-sm text-gray-400">{prediction.driver_name}</p>
          <p className="text-xs text-gray-500">{prediction.team_name}</p>
        </div>
        <div className={`text-3xl font-bold ${getPositionColor(Math.round(prediction.expected_position))}`}>
          P{Math.round(prediction.expected_position)}
        </div>
      </div>

      {/* Main probabilities */}
      <div className="space-y-3 mb-4">
        {/* Win */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Win</span>
            <span className="font-semibold">{formatProbability(prediction.win_probability)}</span>
          </div>
          <div className="prediction-bar">
            <div 
              className={`prediction-fill ${getProbabilityColor(prediction.win_probability)}`}
              style={{ width: `${prediction.win_probability * 100}%` }}
            />
          </div>
        </div>

        {/* Podium */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Podium</span>
            <span className="font-semibold">{formatProbability(prediction.podium_probability)}</span>
          </div>
          <div className="prediction-bar">
            <div 
              className={`prediction-fill ${getProbabilityColor(prediction.podium_probability)}`}
              style={{ width: `${prediction.podium_probability * 100}%` }}
            />
          </div>
        </div>

        {/* Top 10 */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Top 10</span>
            <span className="font-semibold">{formatProbability(prediction.top10_probability)}</span>
          </div>
          <div className="prediction-bar">
            <div 
              className={`prediction-fill ${getProbabilityColor(prediction.top10_probability)}`}
              style={{ width: `${prediction.top10_probability * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Details toggle */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full flex items-center justify-between py-2 text-sm text-gray-400 hover:text-white transition"
      >
        <span>More Details</span>
        {showDetails ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {/* Expanded details */}
      {showDetails && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">DNF Probability:</span>
            <span className={prediction.dnf_probability > 0.15 ? 'text-red-400' : 'text-green-400'}>
              {formatProbability(prediction.dnf_probability)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Confidence:</span>
            <span className="font-semibold">
              {formatProbability(prediction.prediction_confidence)}
            </span>
          </div>

          {/* Explainability button */}
          <button
            onClick={() => setShowExplainability(!showExplainability)}
            className="w-full mt-4 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg transition text-sm font-semibold"
          >
            {showExplainability ? 'Hide' : 'Show'} Explanation
          </button>

          {/* Explainability */}
          {showExplainability && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              {explainabilityLoading ? (
                <div className="flex justify-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-red-500"></div>
                </div>
              ) : explainability ? (
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-gray-300">Top Contributing Factors:</h4>
                  {explainability.top_factors.slice(0, 5).map((factor, idx) => (
                    <div key={idx} className="bg-gray-900/50 rounded p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-gray-400">
                          {factor.feature}
                        </span>
                        <div className="flex items-center gap-1">
                          {factor.direction === 'positive' ? (
                            <TrendingUp className="text-green-400" size={14} />
                          ) : factor.direction === 'negative' ? (
                            <TrendingDown className="text-red-400" size={14} />
                          ) : (
                            <Minus className="text-gray-400" size={14} />
                          )}
                          <span className="text-xs font-semibold">
                            {factor.shap_value > 0 ? '+' : ''}{factor.shap_value.toFixed(3)}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400">{factor.explanation}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400 text-center py-4">
                  No explanation available
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
