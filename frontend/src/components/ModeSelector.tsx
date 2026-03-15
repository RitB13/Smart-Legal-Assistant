import React from 'react';
import { MessageCircle, TrendingUp, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/**
 * ModeSelector Component
 * 
 * Three-button UI for selecting analysis mode:
 * - CHAT: Legal advice and questions about existing situations
 * - PREDICT: Case outcome prediction based on facts
 * - SIMULATE: Consequence analysis for planned actions
 */

interface ModeSelectorProps {
  selectedMode: string | null;
  onModeSelect: (mode: 'chat' | 'predict' | 'simulate') => void;
  recommendedMode?: string;
}

const ModeSelector: React.FC<ModeSelectorProps> = ({
  selectedMode,
  onModeSelect,
  recommendedMode,
}) => {
  const modes = [
    {
      id: 'chat',
      label: 'Chat',
      icon: MessageCircle,
      description: 'Ask about existing legal situations',
      color: 'bg-blue-50 hover:bg-blue-100 border-blue-200',
      textColor: 'text-blue-700',
      bgColor: 'bg-blue-100',
    },
    {
      id: 'predict',
      label: 'Predict',
      icon: TrendingUp,
      description: 'Predict case outcomes based on facts',
      color: 'bg-purple-50 hover:bg-purple-100 border-purple-200',
      textColor: 'text-purple-700',
      bgColor: 'bg-purple-100',
    },
    {
      id: 'simulate',
      label: 'Simulate',
      icon: Zap,
      description: 'See consequences of planned actions',
      color: 'bg-amber-50 hover:bg-amber-100 border-amber-200',
      textColor: 'text-amber-700',
      bgColor: 'bg-amber-100',
    },
  ];

  return (
    <Card className="p-4">
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Analysis Mode
          </label>
          {recommendedMode && (
            <p className="text-xs text-gray-500 mb-3">
              💡 System recommends: <span className="font-semibold">{recommendedMode}</span>
            </p>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3">
          {modes.map((mode) => {
            const Icon = mode.icon;
            const isSelected = selectedMode === mode.id;
            const isRecommended = recommendedMode === mode.id;

            return (
              <Button
                key={mode.id}
                onClick={() => onModeSelect(mode.id as 'chat' | 'predict' | 'simulate')}
                variant={isSelected ? 'default' : 'outline'}
                className={`h-auto flex flex-col items-center justify-center py-3 gap-2 transition-all ${
                  isSelected
                    ? `${mode.bgColor} text-white border-2`
                    : `${mode.color} border-2 ${mode.textColor}`
                } ${
                  isRecommended && !isSelected ? 'ring-2 ring-offset-2 ring-green-500' : ''
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs font-medium text-center">{mode.label}</span>
                <span className="text-xs text-center opacity-75 font-normal">
                  {mode.description.split(' ').slice(0, 2).join(' ')}
                </span>
              </Button>
            );
          })}
        </div>

        {/* Mode Descriptions */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-3 gap-3 text-xs text-gray-600">
            <div>
              <p className="font-medium text-gray-900 mb-1">Chat Mode</p>
              <p>Discuss existing legal issues and get advice</p>
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Predict Mode</p>
              <p>Estimate case outcomes and win probabilities</p>
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Simulate Mode</p>
              <p>Explore consequences before taking action</p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default ModeSelector;
