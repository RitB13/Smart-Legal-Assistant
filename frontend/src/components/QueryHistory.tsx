import React, { useState, useEffect } from 'react';
import { Trash2, ExternalLink, Clock, BarChart3 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/**
 * QueryHistory Component
 * 
 * Displays session query history with:
 * - Query text preview
 * - Detection mode badge
 * - Risk score visualization
 * - Timestamp
 * - Click to reload query
 */

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

interface QueryHistoryProps {
  sessionId?: string;
  onSelectQuery?: (query: QueryRecord) => void;
}

const QueryHistory: React.FC<QueryHistoryProps> = ({
  sessionId,
  onSelectQuery,
}) => {
  const [queries, setQueries] = useState<QueryRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  /**
   * Load session queries from database
   */
  useEffect(() => {
    if (sessionId) {
      loadQueries();
    }
  }, [sessionId]);

  const loadQueries = async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`/db/session/${sessionId}/queries?limit=50`, {
        method: 'GET',
      });
      const data = await response.json();
      if (data.queries) {
        setQueries(data.queries);
      }
    } catch (err) {
      setError('Failed to load query history');
      console.error('Error loading history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get mode color styling
   */
  const getModeColor = (mode?: string): string => {
    switch (mode?.toLowerCase()) {
      case 'chat':
        return 'bg-blue-100 text-blue-800';
      case 'predict':
        return 'bg-purple-100 text-purple-800';
      case 'simulate':
        return 'bg-amber-100 text-amber-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  /**
   * Get risk color styling
   */
  const getRiskColor = (riskLevel?: string): string => {
    switch (riskLevel?.toLowerCase()) {
      case 'very low':
        return 'bg-green-100 text-green-800';
      case 'low':
        return 'bg-green-50 text-green-700';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'very high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-50 text-gray-700';
    }
  };

  /**
   * Format timestamp
   */
  const formatTime = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  };

  /**
   * Delete query from local history
   */
  const handleDeleteQuery = (queryId: string) => {
    setQueries(queries.filter((q) => q.query_id !== queryId));
  };

  return (
    <Card className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-600" />
          <h3 className="font-semibold text-gray-900">Query History</h3>
          {queries.length > 0 && (
            <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
              {queries.length}
            </span>
          )}
        </div>
        <Button
          onClick={loadQueries}
          disabled={isLoading}
          variant="ghost"
          size="sm"
          className="text-xs"
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {queries.length === 0 && !isLoading && !error && (
          <div className="text-center py-6 text-gray-500">
            <p className="text-sm">No queries yet</p>
            <p className="text-xs mt-1">Your analysis history will appear here</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-4">
            <p className="text-sm text-gray-500">Loading history...</p>
          </div>
        )}

        {queries.map((query) => (
          <div
            key={query.query_id}
            className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200 cursor-pointer group"
            onClick={() => onSelectQuery?.(query)}
          >
            {/* Query Text */}
            <p className="text-sm font-medium text-gray-900 line-clamp-2 mb-2">
              {query.query_text}
            </p>

            {/* Badges Row */}
            <div className="flex flex-wrap gap-2 mb-2">
              <span className={`text-xs px-2 py-1 rounded font-medium ${getModeColor(query.detected_mode)}`}>
                {query.detected_mode || 'Unknown'}
              </span>

              {query.risk_score !== undefined && (
                <span className={`text-xs px-2 py-1 rounded font-medium ${getRiskColor(query.risk_level)}`}>
                  Risk: {query.risk_score}/100
                </span>
              )}

              {query.user_feedback && (
                <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-800 font-medium">
                  {'★'.repeat(query.user_feedback)}
                </span>
              )}
            </div>

            {/* Footer Row */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>{formatTime(query.timestamp)}</span>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Copy to clipboard
                    navigator.clipboard.writeText(query.query_text);
                  }}
                  className="p-1 hover:bg-gray-300 rounded"
                  title="Copy query"
                >
                  <ExternalLink className="w-3 h-3" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteQuery(query.query_id);
                  }}
                  className="p-1 hover:bg-red-200 rounded"
                  title="Remove from history"
                >
                  <Trash2 className="w-3 h-3 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Stats Footer */}
      {queries.length > 0 && (
        <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="flex items-center gap-4 text-xs text-gray-600">
            <div className="flex items-center gap-1">
              <BarChart3 className="w-4 h-4" />
              <span>{queries.length} total queries</span>
            </div>
            {queries.filter((q) => q.risk_score !== undefined).length > 0 && (
              <div>
                Avg risk: 
                <span className="font-semibold ml-1">
                  {(
                    queries
                      .filter((q) => q.risk_score !== undefined)
                      .reduce((sum, q) => sum + (q.risk_score || 0), 0) /
                    queries.filter((q) => q.risk_score !== undefined).length
                  ).toFixed(0)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};

export default QueryHistory;
