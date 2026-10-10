import React from 'react'
import {
  HelpCircle,
  TrendingDown,
  TrendingUp,
  Target,
  Search,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'
import { Alert } from '../../types/alert'
import { Badge } from '../ui/Badge'
import { formatPercent } from '../../utils/formatters'

interface ExplainableAlertCardProps {
  alert: Alert
  compact?: boolean
}

export const ExplainableAlertCard: React.FC<ExplainableAlertCardProps> = ({
  alert,
  compact = false,
}) => {
  const { explanation } = alert
  const isNegative = alert.relativeDeviation < 0

  return (
    <div className="bg-slate-50/70 border border-[#E4E9F1] rounded-xl p-4 sm:p-5 relative overflow-hidden">
      {/* Header with Title and Confidence */}
      <div className="flex items-center justify-between gap-3 pb-3 mb-3 border-b border-slate-200/80">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-100 text-[#3867F5] flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Explainable Anomaly Diagnostic
            </h4>
            <span className="text-[11px] text-slate-500">
              Deterministic Root Cause Signature • {alert.category}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="purple" size="sm">
            Confidence: {formatPercent(explanation.confidence, 0)}
          </Badge>
          <Badge variant="neutral" size="sm">
            {alert.detectionMethod.split('+')[0]}
          </Badge>
        </div>
      </div>

      {/* Grid of Explainability Dimensions */}
      <div className={`grid ${compact ? 'grid-cols-1 gap-2.5' : 'grid-cols-1 md:grid-cols-2 gap-3.5'}`}>
        {/* 1. What changed */}
        <div className="p-3 bg-white rounded-lg border border-slate-200/70">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
            {isNegative ? (
              <TrendingDown className="w-3.5 h-3.5 text-rose-600" />
            ) : (
              <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
            )}
            <span>1. What changed?</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">{explanation.whatChanged}</p>
        </div>

        {/* 2. What was expected vs observed */}
        <div className="p-3 bg-white rounded-lg border border-slate-200/70">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
            <Target className="w-3.5 h-3.5 text-emerald-600" />
            <span>2. Baseline vs Observed</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed mb-1">
            {explanation.whatExpected}
          </p>
          <p className="text-xs font-medium text-slate-900">{explanation.whatObserved}</p>
        </div>

        {/* 3. Why was it flagged */}
        <div className="p-3 bg-white rounded-lg border border-slate-200/70">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
            <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
            <span>3. Why was this flagged?</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">{explanation.whyFlagged}</p>
          <div className="mt-1.5 text-[11px] font-mono text-slate-500">
            Deviation Magnitude: {explanation.deviationMagnitude} (Score: {alert.anomalyScore} MAD)
          </div>
        </div>

        {/* 4. What should user check first */}
        <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-200">
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#1E40AF] mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#3867F5]" />
            <span>4. Recommended First Action</span>
          </div>
          <p className="text-xs text-[#1E3A8A] leading-relaxed font-medium">
            {explanation.recommendedFirstStep}
          </p>
        </div>
      </div>
    </div>
  )
}
