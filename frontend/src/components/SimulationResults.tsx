import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, AlertCircle, Scale, BookOpen, Lightbulb, MessageSquare } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

/**
 * SimulationResults Component
 * 
 * Displays the analysis results from the simulator including:
 * - Risk level and score
 * - Legal consequences
 * - Applicable laws
 * - Prevention suggestions
 * - User feedback collection
 */

interface SimulationResultsProps {
  result: {
    query_id?: string;
    session_id?: string;
    suggested_mode?: string;
    mode_confidence?: number;
    response?: string;
    risk_level?: string;
    risk_score?: number;
    consequences?: string[];
    applicable_laws?: string[];
    prevention_suggestions?: string[];
    processing_time_ms?: number;
  };
  onSaveFeedback?: (rating: number, comment: string) => Promise<void>;
}

const SimulationResults: React.FC<SimulationResultsProps> = ({
  result,
  onSaveFeedback,
}) => {
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  /**
   * Get risk level styling
   */
  const getRiskColor = (riskLevel?: string): string => {
    switch (riskLevel?.toLowerCase()) {
      case 'very low':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'low':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'very high':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  /**
   * Get risk icon based on level
   */
  const getRiskIcon = (riskLevel?: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'very low':
      case 'low':
        return <CheckCircle2 className="w-5 h-5" />;
      case 'medium':
        return <AlertCircle className="w-5 h-5" />;
      case 'high':
      case 'very high':
        return <AlertTriangle className="w-5 h-5" />;
      default:
        return <AlertCircle className="w-5 h-5" />;
    }
  };

  /**
   * Handle feedback submission
   */
  const handleSubmitFeedback = async () => {
    if (feedbackRating === null) return;

    setIsSubmittingFeedback(true);
    try {
      if (onSaveFeedback) {
        await onSaveFeedback(feedbackRating, feedbackComment);
      }
      setFeedbackSubmitted(true);
      setTimeout(() => {
        setFeedbackSubmitted(false);
        setFeedbackRating(null);
        setFeedbackComment('');
      }, 2000);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      {/* Risk Assessment */}
      <Card className={`p-4 border-2 flex items-start gap-4 ${getRiskColor(result.risk_level)}`}>
        <div className="flex-shrink-0 mt-1">
          {getRiskIcon(result.risk_level)}
        </div>
        <div className="flex-grow">
          <h3 className="font-semibold text-lg mb-2">Risk Assessment</h3>
          <div className="flex items-baseline gap-4">
            <div>
              <p className="text-sm opacity-80">Risk Level</p>
              <p className="text-xl font-bold">{result.risk_level || 'Unknown'}</p>
            </div>
            <div>
              <p className="text-sm opacity-80">Risk Score</p>
              <div className="flex items-baseline gap-1">
                <p className="text-2xl font-bold">{result.risk_score ?? 0}</p>
                <p className="text-sm opacity-80">/100</p>
              </div>
            </div>
          </div>

          {/* Risk Score Bar */}
          <div className="mt-3 bg-black/10 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all ${
                (result.risk_score ?? 0) < 30
                  ? 'bg-green-500'
                  : (result.risk_score ?? 0) < 50
                  ? 'bg-yellow-500'
                  : (result.risk_score ?? 0) < 70
                  ? 'bg-orange-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${result.risk_score ?? 0}%` }}
            />
          </div>
        </div>
      </Card>

      {/* Main Response */}
      {result.response && (
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-blue-600" />
            Analysis Summary
          </h3>
          <p className="text-gray-700 leading-relaxed text-sm">
            {result.response}
          </p>
          {result.processing_time_ms && (
            <p className="text-xs text-gray-500 mt-2">
              Analysis completed in {result.processing_time_ms.toFixed(0)}ms
            </p>
          )}
        </Card>
      )}

      {/* Consequences */}
      {result.consequences && result.consequences.length > 0 && (
        <Card className="p-4 border-red-200 bg-red-50">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            Potential Consequences
          </h3>
          <ul className="space-y-2">
            {result.consequences.map((consequence, idx) => (
              <li key={idx} className="flex gap-3 text-sm text-gray-700">
                <span className="text-red-600 font-bold">•</span>
                <span>{consequence}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Applicable Laws */}
      {result.applicable_laws && result.applicable_laws.length > 0 && (
        <Card className="p-4 border-purple-200 bg-purple-50">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Scale className="w-5 h-5 text-purple-600" />
            Applicable Laws & Regulations
          </h3>
          <div className="flex flex-wrap gap-2">
            {result.applicable_laws.map((law, idx) => (
              <Badge key={idx} variant="secondary" className="bg-purple-200 text-purple-800">
                {law}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Prevention Suggestions */}
      {result.prevention_suggestions && result.prevention_suggestions.length > 0 && (
        <Card className="p-4 border-green-200 bg-green-50">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            How to Stay Compliant
          </h3>
          <ul className="space-y-2">
            {result.prevention_suggestions.map((suggestion, idx) => (
              <li key={idx} className="flex gap-3 text-sm text-gray-700">
                <span className="text-green-600 font-bold">✓</span>
                <span>{suggestion}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Feedback Section */}
      <Card className="p-4 border-blue-200 bg-blue-50">
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-600" />
          Was this analysis helpful?
        </h3>

        {feedbackSubmitted ? (
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm">Thank you for your feedback!</span>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Star Rating */}
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setFeedbackRating(star)}
                  className={`text-2xl transition-all ${
                    feedbackRating && star <= feedbackRating ? '⭐' : '☆'
                  } ${feedbackRating && star <= feedbackRating ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'}`}
                >
                  {feedbackRating && star <= feedbackRating ? '★' : '☆'}
                </button>
              ))}
            </div>

            {/* Comment */}
            <textarea
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="Any additional comments? (optional)"
              className="w-full p-2 bg-white border border-blue-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={2}
            />

            {/* Submit Button */}
            <Button
              onClick={handleSubmitFeedback}
              disabled={feedbackRating === null || isSubmittingFeedback}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmittingFeedback ? 'Saving...' : 'Submit Feedback'}
            </Button>
          </div>
        )}
      </Card>

      {/* Additional Info */}
      <Alert className="bg-blue-50 border-blue-200 text-blue-900">
        <BookOpen className="w-4 h-4" />
        <AlertDescription className="text-sm">
          This analysis is for informational purposes. Always consult with a qualified legal professional for personalized legal advice.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default SimulationResults;
