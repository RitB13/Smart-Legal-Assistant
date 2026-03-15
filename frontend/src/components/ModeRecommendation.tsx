import React from 'react';
import { Lightbulb } from 'lucide-react';
import { Card } from '@/components/ui/card';

/**
 * ModeRecommendation Component
 * 
 * Displays AI-recommended analysis mode based on user input
 * Shows confidence level and reasoning for the recommendation
 */

interface ModeRecommendationProps {
  suggestedMode: string;
  confidence: number;
  reasoning: string;
}

const ModeRecommendation: React.FC<ModeRecommendationProps> = ({
  suggestedMode,
  confidence,
  reasoning,
}) => {
  /**
   * Get mode color styling
   */
  const getModeColor = (mode: string): { bg: string; text: string; badge: string } => {
    switch (mode.toLowerCase()) {
      case 'chat':
        return { bg: 'bg-blue-50', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-800' };
      case 'predict':
        return { bg: 'bg-purple-50', text: 'text-purple-700', badge: 'bg-purple-100 text-purple-800' };
      case 'simulate':
        return { bg: 'bg-amber-50', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' };
      default:
        return { bg: 'bg-gray-50', text: 'text-gray-700', badge: 'bg-gray-100 text-gray-800' };
    }
  };

  /**
   * Get confidence display
   */
  const getConfidenceLabel = (conf: number): string => {
    if (conf >= 0.85) return 'Very High';
    if (conf >= 0.75) return 'High';
    if (conf >= 0.60) return 'Medium';
    if (conf >= 0.50) return 'Low';
    return 'Very Low';
  };

  const colors = getModeColor(suggestedMode);
  const confidenceLabel = getConfidenceLabel(confidence);

  return (
    <div className={`p-3 rounded-lg border border-gray-200 ${colors.bg}`}>
      <div className="flex items-start gap-2">
        <Lightbulb className={`w-4 h-4 flex-shrink-0 mt-0.5 ${colors.text}`} />
        <div className="flex-grow">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-gray-600">AI Recommendation</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors.badge}`}>
              {suggestedMode}
            </span>
            <span className="text-xs text-gray-500">
              {(confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          
          {/* Confidence Bar */}
          <div className="flex items-center gap-2 mb-2">
            <div className="flex-grow bg-gray-200 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full transition-all ${
                  confidence >= 0.85
                    ? 'bg-green-500'
                    : confidence >= 0.75
                    ? 'bg-green-400'
                    : confidence >= 0.60
                    ? 'bg-yellow-400'
                    : 'bg-orange-400'
                }`}
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-600 whitespace-nowrap">
              {confidenceLabel}
            </span>
          </div>

          {/* Reasoning */}
          {reasoning && (
            <p className="text-xs text-gray-700">
              {reasoning}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModeRecommendation;
