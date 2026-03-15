import { AlertCircle, TrendingUp, Clock, Shield } from "lucide-react";

interface ImpactScoreData {
  overall_score: number;
  financial_risk_score: number;
  legal_exposure_score: number;
  long_term_impact_score: number;
  rights_lost_score: number;
  risk_level: string;
  breakdown: {
    financial_risk: string;
    legal_exposure: string;
    long_term_impact: string;
    rights_lost: string;
  };
  key_factors: string[];
  mitigating_factors: string[];
  recommendation: string;
}

interface ImpactScoreDisplayProps {
  score: ImpactScoreData;
  className?: string;
}

const ImpactScoreDisplay = ({ score, className = "" }: ImpactScoreDisplayProps) => {
  const getRiskColor = (level: string) => {
    if (level.includes("Critical")) return "#dc2626"; // red
    if (level.includes("High")) return "#ea580c"; // orange
    if (level.includes("Medium")) return "#eab308"; // yellow
    return "#16a34a"; // green
  };

  const getRiskBgColor = (level: string) => {
    if (level.includes("Critical")) return "bg-red-50 border-red-200";
    if (level.includes("High")) return "bg-orange-50 border-orange-200";
    if (level.includes("Medium")) return "bg-yellow-50 border-yellow-200";
    return "bg-green-50 border-green-200";
  };

  const getSubscoreColor = (score: number) => {
    if (score >= 75) return "text-red-600";
    if (score >= 60) return "text-orange-600";
    if (score >= 40) return "text-yellow-600";
    return "text-green-600";
  };

  const getProgressBarColor = (score: number) => {
    if (score >= 75) return "bg-red-500";
    if (score >= 60) return "bg-orange-500";
    if (score >= 40) return "bg-yellow-500";
    return "bg-green-500";
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Main Score Card */}
      <div
        className={`border-2 rounded-xl p-6 ${getRiskBgColor(
          score.risk_level
        )}`}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              Legal Impact Score
            </h3>
            <p className="text-sm text-muted-foreground">
              Comprehensive assessment of legal risk
            </p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold" style={{ color: getRiskColor(score.risk_level) }}>
              {score.overall_score}
            </div>
            <p className="text-xs text-muted-foreground mt-1">/100</p>
          </div>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${getProgressBarColor(
              score.overall_score
            )}`}
            style={{ width: `${score.overall_score}%` }}
          ></div>
        </div>

        <p className="text-sm font-semibold">{score.risk_level}</p>
      </div>

      {/* Subscores Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-border rounded-lg p-4 bg-card">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center">
              <TrendingUp className="h-4 w-4 mr-2" />
              Financial Risk
            </label>
            <span className={`font-bold ${getSubscoreColor(score.financial_risk_score)}`}>
              {score.financial_risk_score}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressBarColor(score.financial_risk_score)}`}
              style={{ width: `${score.financial_risk_score}%` }}
            ></div>
          </div>
        </div>

        <div className="border border-border rounded-lg p-4 bg-card">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center">
              <Shield className="h-4 w-4 mr-2" />
              Legal Exposure
            </label>
            <span className={`font-bold ${getSubscoreColor(score.legal_exposure_score)}`}>
              {score.legal_exposure_score}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressBarColor(score.legal_exposure_score)}`}
              style={{ width: `${score.legal_exposure_score}%` }}
            ></div>
          </div>
        </div>

        <div className="border border-border rounded-lg p-4 bg-card">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center">
              <Clock className="h-4 w-4 mr-2" />
              Long-term Impact
            </label>
            <span className={`font-bold ${getSubscoreColor(score.long_term_impact_score)}`}>
              {score.long_term_impact_score}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressBarColor(score.long_term_impact_score)}`}
              style={{ width: `${score.long_term_impact_score}%` }}
            ></div>
          </div>
        </div>

        <div className="border border-border rounded-lg p-4 bg-card">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Rights Lost
            </label>
            <span className={`font-bold ${getSubscoreColor(score.rights_lost_score)}`}>
              {score.rights_lost_score}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressBarColor(score.rights_lost_score)}`}
              style={{ width: `${score.rights_lost_score}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Key Factors */}
      {score.key_factors.length > 0 && (
        <div className="border border-border rounded-lg p-4 bg-card">
          <h4 className="font-semibold text-foreground mb-3 text-sm">
            🚨 Key Risk Factors
          </h4>
          <ul className="space-y-2">
            {score.key_factors.map((factor, idx) => (
              <li key={idx} className="text-sm text-muted-foreground flex items-start">
                <span className="text-primary mr-2">•</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Mitigating Factors */}
      {score.mitigating_factors.length > 0 && (
        <div className="border border-green-200 rounded-lg p-4 bg-green-50">
          <h4 className="font-semibold text-green-900 mb-3 text-sm">
            ✅ Mitigating Factors (Reduce Risk)
          </h4>
          <ul className="space-y-2">
            {score.mitigating_factors.map((factor, idx) => (
              <li key={idx} className="text-sm text-green-700 flex items-start">
                <span className="text-green-600 mr-2">✓</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation */}
      <div className="border border-border rounded-lg p-4 bg-blue-50 border-blue-200">
        <h4 className="font-semibold text-blue-900 mb-2 text-sm">💡 Recommendation</h4>
        <p className="text-sm text-blue-800">{score.recommendation}</p>
      </div>

      {/* Breakdown Details */}
      <details className="border border-border rounded-lg p-4 bg-card cursor-pointer">
        <summary className="font-semibold text-foreground select-none hover:text-primary transition-colors">
          📋 Detailed Breakdown
        </summary>
        <div className="mt-4 space-y-3 text-sm">
          {Object.entries(score.breakdown).map(([key, value]) => (
            <div key={key} className="text-muted-foreground">
              <p className="font-medium text-foreground capitalize mb-1">
                {key.replace(/_/g, " ")}
              </p>
              <p>{value}</p>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
};

export default ImpactScoreDisplay;
