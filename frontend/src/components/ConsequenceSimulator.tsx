import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Zap, TrendingUp, Send, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ModeSelector from '@/components/ModeSelector';
import SimulationResults from '@/components/SimulationResults';
import ModeRecommendation from '@/components/ModeRecommendation';
import QueryHistory from '@/components/QueryHistory';

/**
 * ConsequenceSimulator Component
 * 
 * Main interactive interface for the Legal Consequence Simulator feature.
 * Allows users to:
 * - Describe planned legal actions
 * - Get automatic mode detection (chat/predict/simulate)
 * - See legal consequences and risk analysis
 * - Track analysis history per session
 * 
 * Integrates with Phases 1-4:
 * - Phase 1: Backend consequence analysis
 * - Phase 2: Multilingual detection
 * - Phase 3: Smart mode routing
 * - Phase 4: Database persistence
 */
interface SimulationResponse {
  query_id?: string;
  session_id?: string;
  suggested_mode?: string;
  mode_confidence?: number;
  mode_reasoning?: string;
  response?: string;
  risk_level?: string;
  risk_score?: number;
  consequences?: string[];
  applicable_laws?: string[];
  prevention_suggestions?: string[];
  processing_time_ms?: number;
  error?: string;
}

interface QueryRecord {
  query_id: string;
  query_text: string;
  detected_mode: string;
  response_summary: string;
  risk_level?: string;
  risk_score?: number;
  timestamp: string;
  user_feedback?: number;
}

const ConsequenceSimulator: React.FC = () => {
  // State Management
  const [queryText, setQueryText] = useState('');
  const [sessionId, setSessionId] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<'chat' | 'predict' | 'simulate' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryRecord[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [modeRecommendation, setModeRecommendation] = useState<{
    suggested_mode: string;
    confidence: number;
    reasoning: string;
  } | null>(null);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initialize session on component mount
  useEffect(() => {
    initializeSession();
  }, []);

  // Auto-detect mode when query text changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (queryText.trim()) {
        detectMode();
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [queryText]);

  /**
   * Initialize a new session with the database
   */
  const initializeSession = async () => {
    try {
      const response = await fetch('/db/session/create?language=en', {
        method: 'POST',
      });
      const data = await response.json();
      if (data.session_id) {
        setSessionId(data.session_id);
        console.log('Session initialized:', data.session_id);
      }
    } catch (err) {
      console.error('Failed to initialize session:', err);
      // Generate a client-side session ID if backend fails
      setSessionId(`session_${Date.now()}`);
    }
  };

  /**
   * Detect the appropriate mode (chat/predict/simulate) for user input
   */
  const detectMode = async () => {
    if (!queryText.trim()) return;

    try {
      const response = await fetch('/chatbot/detect-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          session_id: sessionId,
          language: 'en',
        }),
      });
      
      const data = await response.json();
      if (data.suggested_mode) {
        setModeRecommendation({
          suggested_mode: data.suggested_mode,
          confidence: data.mode_confidence || 0,
          reasoning: data.mode_reasoning || '',
        });
      }
    } catch (err) {
      console.error('Mode detection failed:', err);
    }
  };

  /**
   * Process the query using selected or recommended mode
   */
  const handleAnalyze = async () => {
    if (!queryText.trim()) {
      setError('Please enter your query or planned action');
      return;
    }

    const mode = selectedMode || modeRecommendation?.suggested_mode || 'simulate';
    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      let endpoint = '/chatbot/query';
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          session_id: sessionId,
          language: 'en',
          mode: mode,
        }),
      });

      const data: SimulationResponse = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
        
        // Save to database
        if (data.query_id) {
          saveQueryToDatabase(data);
        }

        // Add to local history
        addToHistory({
          query_id: data.query_id || `${Date.now()}`,
          query_text: queryText,
          detected_mode: mode,
          response_summary: data.response || '',
          risk_level: data.risk_level,
          risk_score: data.risk_score,
          timestamp: new Date().toISOString(),
        });
      }
    } catch (err) {
      setError('Failed to analyze query. Please try again.');
      console.error('Analysis error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Save query result to database via Phase 4 API
   */
  const saveQueryToDatabase = async (result: SimulationResponse) => {
    try {
      await fetch('/db/query/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: result.query_id,
          session_id: sessionId,
          query_text: queryText,
          response_summary: result.response,
          detected_mode: selectedMode || modeRecommendation?.suggested_mode || 'simulate',
          mode_confidence: modeRecommendation?.confidence || 0,
          processing_time_ms: result.processing_time_ms || 0,
          applicable_laws: result.applicable_laws,
          severity_level: result.risk_level,
        }),
      });
      console.log('Query saved to database');
    } catch (err) {
      console.error('Failed to save to database:', err);
    }
  };

  /**
   * Add query to local history
   */
  const addToHistory = (query: QueryRecord) => {
    setQueryHistory((prev) => [query, ...prev]);
  };

  /**
   * Load query history from database for current session
   */
  const loadSessionHistory = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`/db/session/${sessionId}/queries?limit=20`, {
        method: 'GET',
      });
      const data = await response.json();
      if (data.queries) {
        setQueryHistory(data.queries);
        setShowHistory(true);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  /**
   * Handle keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        handleAnalyze();
      }
    };
    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [queryText, selectedMode]);

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Zap className="w-8 h-8 text-amber-500" />
          Legal Consequence Simulator
        </h1>
        <p className="text-gray-600">
          Describe your planned legal action and understand the potential consequences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Input Section */}
        <div className="lg:col-span-2 space-y-4">
          {/* Input Area */}
          <Card className="p-4">
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Describe your planned action or question
              </label>
              <textarea
                ref={inputRef}
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="E.g., 'I want to record a phone call with my business partner without their consent' or 'What happens if I don't pay my property taxes?'"
                className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
              
              {/* Mode Recommendation Display */}
              {modeRecommendation && (
                <ModeRecommendation
                  suggestedMode={modeRecommendation.suggested_mode}
                  confidence={modeRecommendation.confidence}
                  reasoning={modeRecommendation.reasoning}
                />
              )}

              {/* Error Alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={handleAnalyze}
                  disabled={isLoading || !queryText.trim()}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 mr-2" />
                      Analyze Consequences
                    </>
                  )}
                </Button>

                <Button
                  onClick={loadSessionHistory}
                  variant="outline"
                  className="px-4"
                  title="View query history from this session"
                >
                  <MessageCircle className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>

          {/* Mode Selector */}
          <ModeSelector
            selectedMode={selectedMode}
            onModeSelect={setSelectedMode}
            recommendedMode={modeRecommendation?.suggested_mode}
          />

          {/* Results Section */}
          {result && (
            <SimulationResults
              result={result}
              onSaveFeedback={async (rating, comment) => {
                try {
                  await fetch(`/db/query/${result.query_id}/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating, comment }),
                  });
                  console.log('Feedback saved');
                } catch (err) {
                  console.error('Failed to save feedback:', err);
                }
              }}
            />
          )}
        </div>

        {/* Sidebar - Query History */}
        <div className="space-y-4">
          <Card className="p-4 sticky top-4">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Session History</h3>
            </div>

            {queryHistory.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {queryHistory.slice(0, 10).map((query) => (
                  <div
                    key={query.query_id}
                    className="p-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors text-sm"
                    onClick={() => {
                      setQueryText(query.query_text);
                      setSelectedMode(query.detected_mode as any);
                    }}
                  >
                    <div className="font-medium text-gray-900 truncate">
                      {query.query_text.substring(0, 50)}...
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                        {query.detected_mode}
                      </span>
                      {query.risk_score && (
                        <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded">
                          Risk: {query.risk_score}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No queries yet</p>
            )}
          </Card>

          {/* Stats Card */}
          <Card className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
            <h4 className="font-semibold text-gray-900 mb-3">Tips</h4>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>✓ Be specific about your planned action</li>
              <li>✓ Include jurisdiction (India/USA)</li>
              <li>✓ Mention if you need legal advice</li>
              <li>✓ System will suggest appropriate mode</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ConsequenceSimulator;
